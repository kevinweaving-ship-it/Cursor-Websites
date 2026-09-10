#!/usr/bin/env python3
"""Cape Classic score boxes: free field, bump JS ccr14. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")
old_js = "club-score-edit.js?v=ccr13"
new_js = "club-score-edit.js?v=ccr14"
if new_js in src:
    print("JS_ALREADY_CCR14")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR14")
API.write_text(src, encoding="utf-8")
print("ccr14", new_js in src)
