#!/usr/bin/env python3
"""Cape Classic: reject plain n+1 and duplicate places. Bump JS ccr15. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_allow = "        if entries_n and 1 <= n <= max_pts:"
new_allow = "        if entries_n and 1 <= n <= entries_n:"
if new_allow in src and "1 <= n <= max_pts:" not in src:
    print("VALIDATE_ALREADY_ENTRIES_ONLY")
elif old_allow not in src:
    raise SystemExit("ANCHOR_VALIDATE_MISSING")
else:
    src = src.replace(old_allow, new_allow, 1)
    print("VALIDATE_ENTRIES_ONLY")

old_detail = '            detail=f"Use 1–{entries_n} for a place, or {max_pts} / OCS / DSQ for a code",'
new_detail = '            detail=f"Use 1–{entries_n} for a place, or OCS/DSQ (scores {max_pts})",'
if new_detail in src:
    print("DETAIL_ALREADY")
elif old_detail in src:
    src = src.replace(old_detail, new_detail, 1)
    print("DETAIL_UPDATED")
else:
    print("DETAIL_SKIP")

for old_js, new_js in (
    ("club-score-edit.js?v=ccr14", "club-score-edit.js?v=ccr15"),
    ("club-score-edit.js?v=ccr13", "club-score-edit.js?v=ccr15"),
    ("club-score-edit.js?v=ccr12", "club-score-edit.js?v=ccr15"),
):
    if "club-score-edit.js?v=ccr15" in src:
        print("JS_ALREADY_CCR15")
        break
    if old_js in src:
        src = src.replace(old_js, new_js, 1)
        print("JS_BUMPED", old_js, "->", new_js)
        break
else:
    if "club-score-edit.js?v=ccr15" not in src:
        raise SystemExit("ANCHOR_JS_MISSING")

API.write_text(src, encoding="utf-8")
print("ccr15", "club-score-edit.js?v=ccr15" in src)
print("entries_only", "1 <= n <= entries_n:" in src)
