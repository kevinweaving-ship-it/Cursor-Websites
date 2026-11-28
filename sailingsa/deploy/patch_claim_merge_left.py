#!/usr/bin/env python3
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
t = API.read_text(encoding="utf-8", errors="replace")
bak = Path(f"/root/backups/api.py.claim_merge.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(API, bak)
print("BACKUP", bak)
old = """        n_fail = sum(1 for x in attempts if x.get(\"outcome\") == \"failed\")
        n_left = sum(1 for x in attempts if x.get(\"outcome\") == \"left\")
        n_ok = sum(1 for x in attempts if x.get(\"outcome\") == \"succeeded\")
"""
# file uses normal quotes
old = """        n_fail = sum(1 for x in attempts if x.get("outcome") == "failed")
        n_left = sum(1 for x in attempts if x.get("outcome") == "left")
        n_ok = sum(1 for x in attempts if x.get("outcome") == "succeeded")
"""
new = """        # Merge same-sailor "left" noise (multiple visitor ids from one bounce)
        merged = []
        left_seen = {}
        for a in attempts:
            if a.get("outcome") != "left":
                merged.append(a)
                continue
            day = str(a.get("when") or "")[:10]
            mk = (a.get("sailor_sas_id") or a.get("sailor_name") or "") + "|" + day
            if mk in left_seen:
                continue
            left_seen[mk] = True
            merged.append(a)
        attempts = merged

        n_fail = sum(1 for x in attempts if x.get("outcome") == "failed")
        n_left = sum(1 for x in attempts if x.get("outcome") == "left")
        n_ok = sum(1 for x in attempts if x.get("outcome") == "succeeded")
"""
if old not in t:
    raise SystemExit("anchor missing")
API.write_text(t.replace(old, new, 1), encoding="utf-8")
print("OK")
