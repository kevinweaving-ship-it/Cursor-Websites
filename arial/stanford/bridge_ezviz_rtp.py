#!/opt/hikpoc/venv/bin/python
"""EZVIZ VTM RTP -> decrypted Annex-B HEVC on stdout. Usage: bridge_ezviz_rtp.py SERIAL

Reads EZVIZ_CODE_<SERIAL> from /opt/ezvizpoc/.env. Stanford cameras only.
Does not touch Hik-Connect, CBI, or other sites. Does not re-pair.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from Crypto.Cipher import AES
from pyezvizapi.client import EzvizClient
from pyezvizapi.cloud_stream import open_cloud_stream

START = b"\x00\x00\x00\x01"
ENV = Path("/opt/ezvizpoc/.env")
TOKEN = Path("/opt/ezvizpoc/token.json")
SERIAL = sys.argv[1]
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


def ecb(key: bytes, body: bytes, n: int | None = None) -> bytes:
    # 4096-only decrypt leaves 4K slices green after a sliver. Decrypt the whole NAL body.
    m = len(body) if n is None else min(n, len(body))
    m -= m % 16
    if m <= 0:
        return body
    return AES.new(key, AES.MODE_ECB).decrypt(body[:m]) + body[m:]


def dec_h265(key: bytes, nal: bytes) -> bytes:
    return nal[:2] + ecb(key, nal[2:]) if len(nal) >= 18 else nal


def stream_once(client: EzvizClient, key: bytes) -> None:
    # Always decrypt flagged NALs (proven clean 4K still). Hold stdout until
    # VPS+SPS+PPS+IDR so ffmpeg can use the same -f hevc flags as Voëlklip.
    cur = None
    last = time.monotonic()
    params: dict[int, bytes] = {}
    started = False

    def out_nal(nal: bytes, enc: bool) -> bytes:
        return dec_h265(key, nal) if enc else nal

    def write_nal(nal: bytes) -> None:
        W.write(START)
        W.write(nal)

    def emit(nal: bytes, enc: bool) -> None:
        nonlocal started
        n = out_nal(nal, enc)
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
            log("start IDR type=%s vps/sps/pps ok" % t)
            W.flush()
            return
        write_nal(n)

    with open_cloud_stream(client, SERIAL, timeout=25) as session:
        session.start()
        log("streaming hevc")
        for pkt in session.iter_packets():
            rp = rtp_parse(pkt.body or b"")
            if not rp or rp[0] != 96 or not rp[2]:
                continue
            _pt, enc, pay, _rts = rp
            t = (pay[0] >> 1) & 0x3F
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
                        emit(cur[0] + bytes(cur[1]), cur[2])
                        cur = None
                elif t == 48:
                    i = 2
                    while i + 2 <= len(pay):
                        sz = int.from_bytes(pay[i : i + 2], "big")
                        i += 2
                        if sz == 0 or i + sz > len(pay):
                            break
                        emit(pay[i : i + sz], enc)
                        i += sz
                else:
                    emit(pay, enc)
            except BrokenPipeError:
                return
            now = time.monotonic()
            if now - last > 0.2:
                try:
                    W.flush()
                except BrokenPipeError:
                    return
                last = now


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
            log("reconnect:", repr(exc)[:160])
            time.sleep(1.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
