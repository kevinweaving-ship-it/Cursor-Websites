#!/usr/bin/env python3
"""Cape Classic live fleet poll (Lipton-style, no refresh). JS ccr9."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr8"
new_js = "club-score-edit.js?v=ccr9"
if new_js in src:
    print("JS_ALREADY_CCR9")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR9")

endpoint = '''
@app.get("/api/regatta/{regatta_id}/cape-live-fleets")
def cape_live_fleets(regatta_id: str):
    """Cape Classic only: live rank/total/nett/race cells for open pages (no refresh)."""
    if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
        raise HTTPException(status_code=404, detail="not Cape Classic")
    import json

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT r.result_id, r.block_id, r.rank,
                       r.total_points_raw, r.nett_points_raw, r.race_scores
                FROM results r
                WHERE r.block_id LIKE %s
                   OR CAST(r.regatta_id AS TEXT) LIKE %s
                ORDER BY r.block_id, r.rank NULLS LAST, r.result_id
                """,
                ("2026-09-13-zvyc-cape-classic%", "2026-09-13-zvyc-cape-classic%"),
            )
            fleets = {}
            for row in cur.fetchall() or []:
                bid = str(row.get("block_id") or "")
                if not bid:
                    continue
                rs = row.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                fleets.setdefault(bid, []).append(
                    {
                        "result_id": row["result_id"],
                        "rank": row["rank"],
                        "total_points_raw": row["total_points_raw"],
                        "nett_points_raw": row["nett_points_raw"],
                        "race_scores": rs,
                    }
                )
    return {"ok": True, "fleets": fleets}


'''

anchor = '@app.post("/api/wc/super-admin/block/{block_id}/create-late-entry-result")'
if "def cape_live_fleets(" in src:
    print("EP_ALREADY")
elif anchor not in src:
    raise SystemExit("ANCHOR_EP_MISSING")
else:
    src = src.replace(anchor, endpoint + anchor, 1)
    print("EP_PATCHED")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("ccr9", new_js in src)
