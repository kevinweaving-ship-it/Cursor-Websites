#!/usr/bin/env python3
"""Return full fleet after Cape race save; public codes as '15 DSQ'; JS ccr6."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr5"
new_js = "club-score-edit.js?v=ccr6"
if new_js in src:
    print("JS_ALREADY_CCR6")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR6")

old_fmt = '    return f"{pts}.0 {str(code or \'\').strip().upper()}"'
new_fmt = '    return f"{pts} {str(code or \'\').strip().upper()}"'
if new_fmt in src:
    print("FMT_ALREADY")
elif old_fmt not in src:
    raise SystemExit("ANCHOR_FMT_MISSING")
else:
    src = src.replace(old_fmt, new_fmt, 1)
    print("FMT_PATCHED")

old_out = '''        out = {
            "ok": True,
            "result_id": result_id,
            "block_id": str(block_id),
            "race_scores": rs_out,
            "total_points_raw": updated["total_points_raw"],
            "nett_points_raw": updated["nett_points_raw"],
            "rank": updated["rank"],
            "races_sailed": updated["races_sailed"],
            "discard_count": updated["discard_count"],
        }
'''
new_out = '''        fleet = []
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as fcur:
            fcur.execute(
                """
                SELECT result_id, rank, total_points_raw, nett_points_raw, race_scores
                FROM results
                WHERE block_id = %s
                ORDER BY rank NULLS LAST, result_id
                """,
                (block_id,),
            )
            for row in fcur.fetchall() or []:
                rs = row.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                fleet.append(
                    {
                        "result_id": row["result_id"],
                        "rank": row["rank"],
                        "total_points_raw": row["total_points_raw"],
                        "nett_points_raw": row["nett_points_raw"],
                        "race_scores": rs,
                    }
                )
        out = {
            "ok": True,
            "result_id": result_id,
            "block_id": str(block_id),
            "race_scores": rs_out,
            "total_points_raw": updated["total_points_raw"],
            "nett_points_raw": updated["nett_points_raw"],
            "rank": updated["rank"],
            "races_sailed": updated["races_sailed"],
            "discard_count": updated["discard_count"],
            "fleet": fleet,
        }
'''
if '"fleet": fleet' in src[src.find("def patch_race_score"): src.find("def patch_race_score") + 12000]:
    print("FLEET_ALREADY")
elif old_out not in src:
    raise SystemExit("ANCHOR_OUT_MISSING")
else:
    src = src.replace(old_out, new_out, 1)
    print("FLEET_PATCHED")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("ccr6", new_js in src)
