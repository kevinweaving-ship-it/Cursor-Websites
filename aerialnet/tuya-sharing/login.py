#!/opt/tuya-sharing/venv/bin/python
"""Smart Life QR login for the Aerialnet sharing worker.

This is the login written down in the Home Assistant Tuya flow and in
arial/cbi-sharing/poc.py before that collector was pointed at CBI Home:

  client id  HA_3y9q4ak7g4ephrvke
  schema     haauthorize
  QR text    tuyaSmart--qrLogin?token=...

The User Code comes from the Smart Life app (Me → Settings → Account and
Security → User Code). It is not the IoT Core access id. IoT Core on this
project is expired (28841002) and is not used here.

  login.py qr   USER_CODE     write state/qr.png
  login.py poll               wait for the scan, write state/session.json

Scan the PNG with the Smart Life app that owns "Aerial Networks HSK".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from tuya_sharing import LoginControl

TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
TUYA_SCHEMA = "haauthorize"
QR_FMT = "tuyaSmart--qrLogin?token={token}"

STATE = Path(os.getenv("TUYA_SHARING_STATE") or "/opt/tuya-sharing/state")
PENDING = STATE / "pending.json"
SESSION = STATE / "session.json"


def _write_private(path: Path, data: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _redact(tok: str) -> str:
    return f"len {len(tok)}" if tok else ""


def cmd_qr(args: argparse.Namespace) -> int:
    user_code = (args.user_code or os.getenv("TUYA_SHARING_USER_CODE") or "").strip()
    if not user_code:
        print("need the Smart Life User Code (app: Me → Settings → Account and Security → User Code)", file=sys.stderr)
        return 2
    resp = LoginControl().qr_code(TUYA_CLIENT_ID, TUYA_SCHEMA, user_code)
    print("success", bool(resp.get("success")), "code", resp.get("code"), "msg", resp.get("msg"))
    if not resp.get("success"):
        return 2
    token = str((resp.get("result") or {}).get("qrcode") or "")
    if not token:
        print("qr response had no token", file=sys.stderr)
        return 2
    _write_private(PENDING, {"user_code": user_code, "qr_token": token, "issued_at": int(time.time())})
    payload = QR_FMT.format(token=token)
    import qrcode

    img = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=8)
    out = STATE / "qr.png"
    img.save(out)
    os.chmod(out, 0o600)
    print("qr_png", out)
    print("qr_payload_len", len(payload))
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    pend = _load(PENDING)
    lc = LoginControl()
    deadline = time.time() + args.timeout
    n = 0
    while time.time() < deadline:
        n += 1
        ok, info = lc.login_result(pend["qr_token"], TUYA_CLIENT_ID, pend["user_code"])
        if ok:
            sess = {
                "user_code": pend["user_code"],
                "token_info": {k: info[k] for k in ("t", "uid", "expire_time", "access_token", "refresh_token")},
                "terminal_id": info["terminal_id"],
                "endpoint": info["endpoint"],
                "username": info.get("username"),
                "authorized_at": int(time.time()),
            }
            _write_private(SESSION, sess)
            print("AUTHORIZED polls", n, "username", sess["username"], "endpoint", sess["endpoint"])
            print("uid", info.get("uid"), "access", _redact(str(info.get("access_token") or "")))
            return 0
        code, msg = info.get("code"), info.get("msg")
        print(f"[{n}] not yet code={code} msg={msg}")
        if code in (1110, 1111) or "expire" in str(msg).lower():
            print("QR expired — run qr again")
            return 3
        time.sleep(args.interval)
    print("timed out waiting for the Smart Life scan")
    return 4


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("qr")
    q.add_argument("user_code", nargs="?", default="")
    q.set_defaults(func=cmd_qr)
    w = sub.add_parser("poll")
    w.add_argument("--timeout", type=int, default=180)
    w.add_argument("--interval", type=float, default=2.0)
    w.set_defaults(func=cmd_poll)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
