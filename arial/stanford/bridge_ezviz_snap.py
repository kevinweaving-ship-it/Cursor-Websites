#!/opt/hikpoc/venv/bin/python
"""One EZVIZ cloud snapshot → JPEG file. Same account as Bing dump. Usage:
  bridge_ezviz_snap.py SERIAL OUT.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pyezvizapi.client import EzvizClient

ENV = Path("/opt/ezvizpoc/.env")
TOKEN = Path("/opt/ezvizpoc/token.json")
SERIAL = sys.argv[1]
OUT = Path(sys.argv[2])


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main() -> None:
    env = load_env()
    tok = json.loads(TOKEN.read_text())
    client = EzvizClient(token=tok, account=env.get("EZVIZ_ACCOUNT"), password=env.get("EZVIZ_PASSWORD"))
    pic = client.capture_picture(SERIAL, 1)
    url = (pic.get("captureInfo") or {}).get("picUrl")
    if not url:
        raise SystemExit("no snapshot url")
    resp = client._session.get(url, timeout=25)
    resp.raise_for_status()
    if len(resp.content) < 800 or resp.content[:2] != b"\xff\xd8":
        raise SystemExit("snapshot is not a jpeg")
    OUT.write_bytes(resp.content)
    print("snap", SERIAL, "bytes", len(resp.content), file=sys.stderr)


if __name__ == "__main__":
    main()
