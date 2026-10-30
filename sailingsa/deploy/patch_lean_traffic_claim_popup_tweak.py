#!/usr/bin/env python3
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    t = API.read_text(encoding="utf-8", errors="replace")
    bak = Path(f"/root/backups/api.py.claim_popup2.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    start = t.find("def lean_traffic_api_claim_attempts")
    end = t.find("\n@app.get", start)
    if start < 0 or end < 0:
        raise SystemExit("fn bounds")
    chunk = t[start:end]
    if "claim_cta_impression" in chunk:
        chunk = chunk.replace("                'claim_cta_impression',\n", "", 1)
        print("removed impression")
    oldp = '''            if not sname and sid and sid.lower() != "probe":
                sname = "SAS " + sid
            if sid and sid.lower() == "probe":
                sname = "(test probe)"
'''
    newp = '''            if (row.get("stable_entity_id") or "").lower() == "probe" or (sid or "").lower() == "probe":
                sname = "(test probe)"
            elif not sname and sid:
                sname = "SAS " + sid
'''
    if oldp in chunk:
        chunk = chunk.replace(oldp, newp, 1)
        print("probe label fixed")
    else:
        print("probe block not exact; skip")
    t = t[:start] + chunk + t[end:]
    API.write_text(t, encoding="utf-8")
    print("OK")


if __name__ == "__main__":
    main()
