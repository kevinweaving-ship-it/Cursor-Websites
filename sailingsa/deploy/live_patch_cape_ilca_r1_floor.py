#!/usr/bin/env python3
"""Surgical live patch: keep Cape Classic R1 columns; bump club-score JS to ccr3."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_max = '''        discard_count = max_rs // 5 if max_rs else 0
        # Lipton Challenge Cup: Appendix A low-point, NO discards (any race count).
        if "lipton" in str(regatta_id or "").lower():
            discard_count = 0

        cur.execute(
            """
            UPDATE regatta_blocks
            SET races_sailed = %s,
                discard_count = %s
            WHERE block_id = %s
            """,
            (max_rs, discard_count, block_id),
        )
'''
new_max = '''        discard_count = max_rs // 5 if max_rs else 0
        # Lipton Challenge Cup: Appendix A low-point, NO discards (any race count).
        if "lipton" in str(regatta_id or "").lower():
            discard_count = 0

        # Cape Classic: never hide R1 by shrinking races_sailed to 0.
        if str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
            cur.execute(
                "SELECT COALESCE(races_sailed, 0) AS rs FROM regatta_blocks WHERE block_id = %s",
                (block_id,),
            )
            existing_rs = int((cur.fetchone() or {}).get("rs") or 0)
            max_rs = max(int(max_rs or 0), existing_rs, 1)
            discard_count = max_rs // 5 if max_rs else 0

        cur.execute(
            """
            UPDATE regatta_blocks
            SET races_sailed = %s,
                discard_count = %s
            WHERE block_id = %s
            """,
            (max_rs, discard_count, block_id),
        )
'''
if "Cape Classic: never hide R1" in src:
    print("FLOOR_ALREADY")
elif old_max not in src:
    raise SystemExit("ANCHOR_MAX_MISSING")
else:
    src = src.replace(old_max, new_max, 1)
    print("FLOOR_PATCHED")

old_js = "club-score-edit.js?v=ccr2"
new_js = "club-score-edit.js?v=ccr3"
if new_js in src:
    print("JS_ALREADY_CCR3")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR3")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("floor", "Cape Classic: never hide R1" in src)
print("ccr3", new_js in src)
