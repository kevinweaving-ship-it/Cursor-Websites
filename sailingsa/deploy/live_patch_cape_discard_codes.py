#!/usr/bin/env python3
"""Cape Classic: discard only after 5 scored races; count every Rn including OCS. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_loop = """            res_races_sailed = len(
                [k for k in res_race_scores.keys() if str(k).startswith("R") and res_race_scores.get(k)]
            )

            res_scores_list = []
            for i in range(1, res_races_sailed + 1):"""

new_loop = """            max_key = 0
            for _k, _v in (res_race_scores or {}).items():
                _ku = str(_k or "").strip().upper()
                if (
                    _ku.startswith("R")
                    and _ku[1:].isdigit()
                    and str(_v or "").strip()
                ):
                    max_key = max(max_key, int(_ku[1:]))

            res_scores_list = []
            for i in range(1, max(max_key, 1) + 1):"""

old_cape = """        # Cape Classic: never hide R1 by shrinking races_sailed to 0.
        if str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
            cur.execute(
                "SELECT COALESCE(races_sailed, 0) AS rs FROM regatta_blocks WHERE block_id = %s",
                (block_id,),
            )
            existing_rs = int((cur.fetchone() or {}).get("rs") or 0)
            max_rs = max(int(max_rs or 0), existing_rs, 1)
            discard_count = max_rs // 5 if max_rs else 0
"""

new_cape = """        # Cape Classic: discard only after 5 races with scores. Empty R+ columns do not count.
        if str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
            scored = set()
            max_idx = 0
            for res in all_results:
                rs = res.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                if not isinstance(rs, dict):
                    continue
                for k, v in rs.items():
                    if not str(v or "").strip():
                        continue
                    ku = str(k or "").strip().upper()
                    if ku.startswith("R") and ku[1:].isdigit():
                        scored.add(ku)
                        max_idx = max(max_idx, int(ku[1:]))
            completed = len(scored)
            max_rs = max(int(max_idx or 0), 1)
            discard_count = completed // 5 if completed else 0
"""

old_js = "club-score-edit.js?v=ccr12"
new_js = "club-score-edit.js?v=ccr13"

if new_loop in src:
    print("LOOP_ALREADY")
elif old_loop not in src:
    raise SystemExit("ANCHOR_LOOP_MISSING")
else:
    src = src.replace(old_loop, new_loop, 1)
    print("LOOP_PATCHED")

if "discard only after 5 races with scores" in src:
    print("CAPE_ALREADY")
elif old_cape not in src:
    raise SystemExit("ANCHOR_CAPE_MISSING")
else:
    src = src.replace(old_cape, new_cape, 1)
    print("CAPE_PATCHED")

if new_js in src:
    print("JS_ALREADY_CCR13")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR13")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("loop", "max(max_key, 1) + 1" in src)
print("cape", "discard only after 5 races with scores" in src)
print("ccr13", new_js in src)
