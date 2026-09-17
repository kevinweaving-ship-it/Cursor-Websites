#!/usr/bin/env python3
import json, urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/regattas/with-counts?limit=20",
    headers={"Host": "sailingsa.co.za", "X-Forwarded-Proto": "https"},
)
with urllib.request.urlopen(req, timeout=40) as r:
    rows = json.loads(r.read().decode())
print("n", len(rows), "first", rows[0].get("regatta_id") if rows else None)
for d in rows:
    rid = str(d.get("regatta_id") or "")
    if "420" in rid or "420" in str(d.get("event_name") or ""):
        print("HIT", {
            "regatta_id": rid,
            "event_name": d.get("event_name"),
            "slug": d.get("slug"),
            "event_url": d.get("event_url"),
            "logo_url": d.get("logo_url"),
            "logo_catalogue_href": d.get("logo_catalogue_href"),
            "entries_count": d.get("entries_count"),
        })
        break
else:
    print("MISSING 420 on first", len(rows))
