#!/usr/bin/env python3
"""HYC NVR producer — isolated from Voelklip /opt/hikpoc camera fetch.

Same Hik-Connect account as Voelklip, different device:
  HYC DS-7608NI-K2/8P  serial D23413606  channel 5  (camera 5@D23413606)

Do not import or patch /opt/hikpoc/bridge_cam.py. Paths, session cache,
media key, and logs stay under /opt/hycnvr.

Usage: bridge_hyc.py [serial] [channel] [h264|hevc] [sub|main]
"""
import json
import os
import sys
import time
from pathlib import Path

from Crypto.Cipher import AES
from hikcloudstream import ClientConfig, Credentials, HikConnectClient
from hikcloudstream.models import Camera, StreamType
from hikcloudstream.stream.session import open_live_stream
from pyezvizapi.stream import VtmChannel

ROOT = Path("/opt/hycnvr")
ENV_PATH = ROOT / ".env"
SESSION_CACHE = str(ROOT / ".session_cache.json")
SESSION_MAX_AGE = 12 * 3600
START = b"\x00\x00\x00\x01"

SERIAL = sys.argv[1] if len(sys.argv) > 1 else "D23413606"
CH = int(sys.argv[2] if len(sys.argv) > 2 else "5")
CODEC = sys.argv[3] if len(sys.argv) > 3 else "hevc"
ST = (sys.argv[4] if len(sys.argv) > 4 else "main").lower()
W = sys.stdout.buffer


def log(*a):
    print("[hycnvr %s/%s]" % (SERIAL, CH), *a, file=sys.stderr, flush=True)


def load_env():
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v
    return env


def media_key_bytes(env):
    raw = (env.get("HIK_MEDIA_KEY") or env.get("HYC_NVR_PASSWORD") or "").encode("utf-8")
    if not raw:
        raise SystemExit("HIK_MEDIA_KEY / HYC_NVR_PASSWORD missing in /opt/hycnvr/.env")
    return raw.ljust(16, b"\0")[:16]


def ps_clear(env):
    raw = (env.get("HIK_PS_CLEAR") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


_env = None
_key = None
_ps_clear = True


def get_env():
    global _env, _key, _ps_clear
    if _env is None:
        _env = load_env()
        _key = media_key_bytes(_env)
        _ps_clear = ps_clear(_env)
    return _env


def ecb(body, n=4096):
    get_env()
    m = min(n, len(body))
    m -= m % 16
    if m <= 0:
        return body
    cipher = AES.new(_key, AES.MODE_ECB)
    return b"".join(cipher.decrypt(body[i : i + 16]) for i in range(0, m, 16)) + body[m:]


def rtp_parse(b):
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
    return b[1] & 0x7F, enc, b[off:], int.from_bytes(b[4:8], "big")


def dec_h264(nal):
    return ecb(nal[1:])


def dec_h265(nal):
    return nal[:2] + ecb(nal[2:]) if len(nal) >= 18 else nal


_clear_sig = {}
_au = [None, 0]


def _slice_idx(rts):
    if rts != _au[0]:
        _au[0] = rts
        _au[1] = 0
    k = _au[1]
    _au[1] += 1
    return k


def hevc_out(nal, enc, rts):
    t = (nal[0] >> 1) & 0x3F
    if t >= 32 or len(nal) < 6:
        if _ps_clear and t in (32, 33, 34):
            return nal
        return dec_h265(nal) if enc else nal
    key = (t, _slice_idx(rts))
    sig = nal[2:4]
    sigs = _clear_sig.setdefault(key, [])
    if not enc:
        if sig not in sigs:
            sigs.append(sig)
            if len(sigs) > 64:
                del sigs[0]
        return nal
    return nal if sig in sigs else dec_h265(nal)


def emit(nal):
    W.write(START)
    W.write(nal)


def stream_once(client):
    cam = Camera(
        index=37,
        name="camera 5@D23413606",
        device_serial=SERIAL,
        channel_no=CH,
        device_name="HYC DS-7608NI-K2/8P(D23413606)",
    )
    stype = StreamType.MAIN if ST == "main" else StreamType.SUB
    session = open_live_stream(client, cam, stream_type=stype, timeout=25)
    r = session.start().result
    if r not in (0, None):
        session.close()
        raise RuntimeError("negotiate %s" % r)
    log("streaming", CODEC, ST, "neg", r)
    cur = None
    last = time.monotonic()
    try:
        for pkt in session._client.iter_packets():
            if pkt.channel not in (VtmChannel.STREAM, VtmChannel.ENCRYPTED_STREAM):
                continue
            rp = rtp_parse(pkt.body or b"")
            if not rp or rp[0] != 96 or not rp[2]:
                continue
            _pt, enc, pay, rts = rp
            if CODEC == "hevc":
                t = (pay[0] >> 1) & 0x3F
                if t == 49:
                    fh = pay[2]
                    ft = fh & 0x3F
                    if fh & 0x80:
                        nh0 = (pay[0] & 0x81) | (ft << 1)
                        cur = [bytes([nh0, pay[1]]), bytearray(pay[3:]), enc]
                    elif cur:
                        cur[1] += pay[3:]
                    if (fh & 0x40) and cur:
                        n = cur[0] + bytes(cur[1])
                        emit(hevc_out(n, cur[2], rts))
                        cur = None
                elif t == 48:
                    i = 2
                    while i + 2 <= len(pay):
                        sz = int.from_bytes(pay[i : i + 2], "big")
                        i += 2
                        if sz == 0 or i + sz > len(pay):
                            break
                        s = pay[i : i + sz]
                        emit(hevc_out(s, enc, rts))
                        i += sz
                else:
                    emit(hevc_out(pay, enc, rts))
            else:
                t = pay[0] & 0x1F
                if t == 28:
                    fu = pay[1]
                    hdr = (pay[0] & 0xE0) | (fu & 0x1F)
                    if fu & 0x80:
                        cur = [bytearray([hdr]) + pay[2:], enc]
                    elif cur:
                        cur[0] += pay[2:]
                    if (fu & 0x40) and cur:
                        n = bytes(cur[0])
                        emit(dec_h264(n) if cur[1] else n)
                        cur = None
                elif t == 24:
                    i = 1
                    while i + 2 <= len(pay):
                        sz = int.from_bytes(pay[i : i + 2], "big")
                        i += 2
                        if sz == 0 or i + sz > len(pay):
                            break
                        s = pay[i : i + sz]
                        emit(dec_h264(s) if enc else s)
                        i += sz
                elif 1 <= t <= 23:
                    emit(dec_h264(pay) if enc else pay)
            now = time.monotonic()
            if now - last > 0.2:
                W.flush()
                last = now
    finally:
        session.close()


def fresh_login(client, env):
    client.login(Credentials(env["HIK_ACCOUNT"], env["HIK_PASSWORD"]))
    try:
        tmp = SESSION_CACHE + ".tmp"
        with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
            json.dump(
                {
                    "t": time.time(),
                    "sid": client.session_id,
                    "rsid": client.refresh_session_id,
                    "fc": client._feature_code,
                },
                f,
            )
        os.replace(tmp, SESSION_CACHE)
    except Exception as e:
        log("session cache write failed:", repr(e)[:80])
    log("logged in")


def cached_client(env):
    client = HikConnectClient(ClientConfig())
    try:
        c = json.load(open(SESSION_CACHE))
        if c.get("sid") and time.time() - c.get("t", 0) < SESSION_MAX_AGE:
            client.session_id = c["sid"]
            client.refresh_session_id = c.get("rsid")
            if c.get("fc"):
                client._feature_code = c["fc"]
            log("using cached session")
            return client, True
    except Exception:
        pass
    fresh_login(client, env)
    return client, False


def main():
    env = get_env()
    client, from_cache = cached_client(env)
    while True:
        try:
            stream_once(client)
        except BrokenPipeError:
            return
        except Exception as e:
            log("reconnect:", repr(e)[:140])
            if from_cache:
                from_cache = False
                try:
                    fresh_login(client, env)
                    continue
                except Exception as e2:
                    log("re-login failed:", repr(e2)[:100])
            time.sleep(2.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
