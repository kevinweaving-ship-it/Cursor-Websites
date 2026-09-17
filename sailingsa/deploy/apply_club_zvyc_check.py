#!/usr/bin/env python3
import urllib.request

HDRS = {"Host": "sailingsa.co.za", "X-Forwarded-Proto": "https"}
req = urllib.request.Request("http://127.0.0.1:8000/club/zvyc?cb=zvycx1", headers=HDRS)
with urllib.request.urlopen(req, timeout=60) as r:
    h = r.read().decode("utf-8", "replace")
checks = {
    "HOST": 'id="club-zvyc-live-media"' in h,
    "WX": 'id="ssa-regatta-slot-card"' in h,
    "CARDS": 'id="mmLiptonReels"' in h,
    "JS": "club-live-media.js" in h,
    "STORY": "club-story-identity" in h and "Events hosted" in h,
    "GOLD": "sa-home-regatta-card" in h and "club-upcoming-table" not in h,
}
print("LEN", len(h))
for k, v in checks.items():
    print(k, "OK" if v else "FAIL")
if not all(checks.values()):
    raise SystemExit(1)
print("ZVYC_EXTRAS_OK")
