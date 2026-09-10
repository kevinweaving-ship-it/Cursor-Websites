#!/usr/bin/env python3
"""Cape Classic: bump score JS ccr17 for busy-race sort. Do not replace api.py unless helpers exist."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

for old_js, new_js in (
    ("club-score-edit.js?v=ccr16", "club-score-edit.js?v=ccr17"),
    ("club-score-edit.js?v=ccr15", "club-score-edit.js?v=ccr17"),
):
    if "club-score-edit.js?v=ccr17" in src:
        print("JS_ALREADY_CCR17")
        break
    if old_js in src:
        src = src.replace(old_js, new_js, 1)
        print("JS_BUMPED", old_js)
        break
else:
    if "club-score-edit.js?v=ccr17" not in src:
        raise SystemExit("ANCHOR_JS_MISSING")

API.write_text(src, encoding="utf-8")
print("ccr17", "club-score-edit.js?v=ccr17" in src)
