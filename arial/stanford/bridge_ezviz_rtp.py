#!/opt/hikpoc/venv/bin/python
"""EZVIZ VTM RTP -> decrypted Annex-B HEVC on stdout. Usage: bridge_ezviz_rtp.py SERIAL

Stanford only. Same decrypt as /opt/hikpoc/bridge_cam.py (Voëlklip gold):
per-NAL AES-128-ECB, first 4096, RTP encrypt flag, clear-slice skip.
Requests EZVIZ substream (stream=2) so first frame is 640-class, not 4K main.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from Crypto.Cipher import AES
from pyezvizapi.client import EzvizClient
from pyezvizapi.cloud_stream import VtmStreamClient, get_cloud_stream_info
from pyezvizapi.stream import VtmChannel

START = b"\x00\x00\x00\x01"
ENV = Path("/opt/ezvizpoc/.env")
TOKEN = Path("/opt/ezvizpoc/token.json")
SERIAL = sys.argv[1]
STREAM = sys.argv[2] if len(sys.argv) > 2 else "2"
W = open(sys.stdout.fileno(), "wb", closefd=False, buffering=0)


def log(*a):
    print("[ezviz-rtp", SERIAL + "]", *a, file=sys.stderr, flush=True)


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def media_key(env: dict[str, str]) -> bytes:
    raw = env.get("EZVIZ_CODE_" + SERIAL) or env.get("EZVIZ_VERIFY") or ""
    if not raw:
        raise SystemExit("missing EZVIZ_CODE_" + SERIAL)
    return raw.encode().ljust(16, b"\0")[:16]


def rtp_parse(b: bytes):
    if len(b) < 12 or (b[0] >> 6) != 2:
        return None
    cc = b[0] & 0x0F
    ext = (b[0] >> 4) & 1
    off = 12 + cc * 4
    enc = False
    if ext:
        if off + 4 > len(b):
            return None
        el = int.from_bytes(b[off + 2 : off + 4], "big")
        if off + 4 < len(b):
            enc = bool(b[off + 4] & 0x80)
        off += 4 + el * 4
    if off > len(b):
        return None
    return b[1] & 0x7F, enc, b[off:], int.from_bytes(b[4:8], "big")


def ecb(key: bytes, body: bytes, n: int = 4096) -> bytes:
    m = min(n, len(body))
    m -= m % 16
    if m <= 0:
        return body
    return AES.new(key, AES.MODE_ECB).decrypt(body[:m]) + body[m:]


def dec_h265(key: bytes, nal: bytes) -> bytes:
    return nal[:2] + ecb(key, nal[2:]) if len(nal) >= 18 else nal


def with_stream(url: str, stream: str) -> str:
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["stream"] = stream
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


class HevcOut:
    def __init__(self, key: bytes):
        self.key = key
        self.clear_sig: dict[tuple[int, int], list[bytes]] = {}
        self.au = [None, 0]

    def _slice_idx(self, rts: int) -> int:
        if rts != self.au[0]:
            self.au[0] = rts
            self.au[1] = 0
        k = self.au[1]
        self.au[1] += 1
        return k

    def __call__(self, nal: bytes, enc: bool, rts: int) -> bytes:
        t = (nal[0] >> 1) & 0x3F
        if t >= 32 or len(nal) < 6:
            return dec_h265(self.key, nal) if enc else nal
        key = (t, self._slice_idx(rts))
        sig = nal[2:4]
        sigs = self.clear_sig.setdefault(key, [])
        if not enc:
            if sig not in sigs:
                sigs.append(sig)
                if len(sigs) > 64:
                    del sigs[0]
            return nal
        return nal if sig in sigs else dec_h265(self.key, nal)


def stream_once(client: EzvizClient, key: bytes) -> None:
    hevc_out = HevcOut(key)
    info = get_cloud_stream_info(client, SERIAL, refresh_vtm=True)
    url = with_stream(info["stream_url"], STREAM)
    cur = None
    last = time.monotonic()
    params: dict[int, bytes] = {}
    started = False
    pkts = 0

    def write_nal(nal: bytes) -> None:
        W.write(START)
        W.write(nal)

    def emit(nal: bytes, enc: bool, rts: int) -> None:
        nonlocal started
        n = hevc_out(nal, enc, rts)
        if len(n) < 2:
            return
        t = (n[0] >> 1) & 0x3F
        if t in (32, 33, 34):
            params[t] = n
            return
        if not started:
            if t not in (19, 20):
                return
            if not all(p in params for p in (32, 33, 34)):
                return
            for p in (32, 33, 34):
                write_nal(params[p])
            write_nal(n)
            started = True
            log("start IDR type=%s bytes=%s stream=%s" % (t, len(n), STREAM))
            W.flush()
            return
        write_nal(n)

    session = VtmStreamClient(url, timeout=25)
    with session:
        session.start()
        log("streaming hevc stream=%s" % STREAM)
        for pkt in session.iter_packets():
            if pkt.channel not in (VtmChannel.STREAM, VtmChannel.ENCRYPTED_STREAM):
                continue
            rp = rtp_parse(pkt.body or b"")
            if not rp or rp[0] != 96 or not rp[2]:
                continue
            _pt, enc, pay, rts = rp
            t = (pay[0] >> 1) & 0x3F
            pkts += 1
            try:
                if t == 49:
                    fh = pay[2]
                    ft = fh & 0x3F
                    if fh & 0x80:
                        nh0 = (pay[0] & 0x81) | (ft << 1)
                        cur = [bytes([nh0, pay[1]]), bytearray(pay[3:]), enc]
                    elif cur:
                        cur[1] += pay[3:]
                    if (fh & 0x40) and cur:
                        emit(cur[0] + bytes(cur[1]), cur[2], rts)
                        cur = None
                elif t == 48:
                    i = 2
                    while i + 2 <= len(pay):
                        sz = int.from_bytes(pay[i : i + 2], "big")
                        i += 2
                        if sz == 0 or i + sz > len(pay):
                            break
                        emit(pay[i : i + sz], enc, rts)
                        i += sz
                else:
                    emit(pay, enc, rts)
            except BrokenPipeError:
                return
            now = time.monotonic()
            if now - last > 0.2:
                try:
                    W.flush()
                except BrokenPipeError:
                    return
                last = now
    log("session ended packets=%s started=%s" % (pkts, started))


def main() -> None:
    env = load_env()
    key = media_key(env)
    tok = json.loads(TOKEN.read_text())
    client = EzvizClient(token=tok, account=env.get("EZVIZ_ACCOUNT"), password=env.get("EZVIZ_PASSWORD"))
    while True:
        try:
            stream_once(client, key)
        except BrokenPipeError:
            return
        except Exception as exc:  # noqa: BLE001
            log("reconnect:", type(exc).__name__)
            time.sleep(1.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
