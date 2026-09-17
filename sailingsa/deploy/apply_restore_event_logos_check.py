#!/usr/bin/env python3
from pathlib import Path
import json
import urllib.request

api = Path("/var/www/sailingsa/api/api.py").read_text()
print("MARK", "EVENT_LOGO_RULES_RESTORE_v1" in api)
print("RULES", "_CLUB_EVENT_LOGO_RULES" in api)
print("ATTACH", 'd["logo_url"] = lu' in api)

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/regattas/with-counts?limit=40",
    headers={"Host": "sailingsa.co.za", "X-Forwarded-Proto": "https"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    rows = json.loads(r.read().decode())
print("ROWS", len(rows))
needles = ("cape classic", "vulcan", "lipton", "j22", "kzn", "420")
for d in rows:
    name = str(d.get("event_name") or "")
    rid = str(d.get("regatta_id") or "")
    hay = f"{name} {rid}".lower()
    if any(n in hay for n in needles):
        print(f"CARD {rid!r} | {name!r} | {d.get('logo_url')!r}")
sa = sum(1 for d in rows if "sailingsa-logo" in str(d.get("logo_url") or "").lower())
named = sum(1 for d in rows if "/artwork/" in str(d.get("logo_url") or "").lower())
blank = sum(1 for d in rows if not d.get("logo_url"))
print(f"SUMMARY sa={sa} artwork={named} blank={blank}")
