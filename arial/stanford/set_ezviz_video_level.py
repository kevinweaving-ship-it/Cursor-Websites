#!/opt/hikpoc/venv/bin/python
"""Set Stanford EZVIZ videoLevel to Bing-class (lowest, never 4K).

Bing C8C gold is videoLevel 0. EB5 VIDEO_QUALITY lists 2,3,4,6 — 2 is the
only level that complies with docs/EZVIZ_BING_GOLD.md. Does not touch Bing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pyezvizapi.client import EzvizClient

ENV = Path("/opt/ezvizpoc/.env")
TOKEN = Path("/opt/ezvizpoc/token.json")
# Lowest listed option on these EB5s. 4 and 6 are 4K-class — forbidden.
LEVEL = 2
STANFORD = {
    "BF4277866": "Front Garage",
    "BF4277838": "EB5",
}


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def client() -> EzvizClient:
    env = load_env()
    tok = json.loads(TOKEN.read_text())
    return EzvizClient(token=tok, account=env.get("EZVIZ_ACCOUNT"), password=env.get("EZVIZ_PASSWORD"))


def current_levels(c: EzvizClient) -> dict[str, int]:
    pl = c.get_page_list() if hasattr(c, "get_page_list") else c._get_page_list()
    out: dict[str, int] = {}
    for r in pl.get("resourceInfos") or []:
        serial = str(r.get("deviceSerial") or "")
        if serial in STANFORD or serial == "BA3858958":
            out[f"{serial}:{r.get('localIndex')}"] = int(r.get("videoLevel") or -1)
    return out


def set_level(c: EzvizClient, serial: str, level: int) -> str:
    paths = (
        f"/v3/userdevices/{serial}/1/1/quality/{level}",
        f"/v3/userdevices/v1/cameras/{serial}/1/quality/{level}",
    )
    last = "no-attempt"
    for path in paths:
        try:
            resp = c._request_json("PUT", path, retry_401=True)
            meta = resp.get("meta") if isinstance(resp, dict) else None
            code = (meta or {}).get("code") if isinstance(meta, dict) else None
            if code in (200, 0, "200", None) or (isinstance(resp, dict) and resp.get("resultCode") in (0, "0")):
                return f"ok {path} code={code}"
            last = f"meta={code}"
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
    try:
        resp = c._request_json(
            "PUT",
            "/v3/userdevices/v1/cameras/videoQuality",
            data={"deviceSerial": serial, "channelNo": 1, "videoLevel": level, "streamType": 1},
            retry_401=True,
        )
        meta = resp.get("meta") if isinstance(resp, dict) else None
        code = (meta or {}).get("code") if isinstance(meta, dict) else None
        return f"body-put code={code}"
    except Exception as exc:  # noqa: BLE001
        return f"fail {last}/{type(exc).__name__}"


def main() -> int:
    if LEVEL >= 4:
        print("refusing: level >= 4 is 4K and violates EZVIZ Bing gold")
        return 2
    c = client()
    print("before", current_levels(c))
    for serial, name in STANFORD.items():
        print(name, serial[-4:], set_level(c, serial, LEVEL))
    print("after", current_levels(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
