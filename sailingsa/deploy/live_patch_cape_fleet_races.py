#!/usr/bin/env python3
"""Cape Classic club-admin R+/R− per fleet. JS ccr10. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr9"
new_js = "club-score-edit.js?v=ccr10"
if new_js in src:
    print("JS_ALREADY_CCR10")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR10")

endpoint = '''
@app.patch("/api/result/{result_id}/fleet-races")
def patch_fleet_races(request: Request, result_id: int, body: dict):
    """Club/Super Admin: add or remove the last race column for this Cape Classic fleet."""
    import json

    payload = body if isinstance(body, dict) else {}
    try:
        delta = int(payload.get("delta"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Use +1 or -1")

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT r.result_id, r.block_id, r.regatta_id,
                       rb.races_sailed
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE r.result_id = %s
                """,
                (result_id,),
            )
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Result not found")
            regatta_id = result.get("regatta_id")
            if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
                raise HTTPException(status_code=404, detail="not Cape Classic")

            token = (
                request.cookies.get("session")
                or (request.query_params.get("session") if request.query_params else None)
                or (payload.get("session") if isinstance(payload, dict) else None)
            )
            cur.execute(
                """
                SELECT ua.role, ua.admin_club_id
                FROM public.user_sessions s
                JOIN public.user_accounts ua ON ua.account_id = s.account_id
                WHERE s.session_id = %s AND s.expires_at > NOW()
                LIMIT 1
                """,
                (token,),
            )
            acct = cur.fetchone() or {}
            role_n = _normalize_account_role(acct.get("role"))
            if role_n not in ("super_admin", "superadmin", "club_admin", "clubadmin"):
                raise HTTPException(
                    status_code=403,
                    detail="Club admin can only enter scores for events hosted by their club",
                )
            if role_n in ("club_admin", "clubadmin"):
                cur.execute(
                    "SELECT host_club_id FROM public.regattas WHERE regatta_id = %s LIMIT 1",
                    (regatta_id,),
                )
                host_row = cur.fetchone() or {}
                host_id = host_row.get("host_club_id")
                club_id = acct.get("admin_club_id")
                if host_id is None or club_id is None or int(host_id) != int(club_id):
                    raise HTTPException(
                        status_code=403,
                        detail="Club admin can only enter scores for events hosted by their club",
                    )

            block_id = result["block_id"]
            current = max(int(result.get("races_sailed") or 0), 1)
            last_key = "R" + str(current)
            last_filled = False
            cur.execute("SELECT race_scores FROM results WHERE block_id = %s", (block_id,))
            for row in cur.fetchall() or []:
                rs = row.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                if str((rs or {}).get(last_key) or "").strip():
                    last_filled = True
                    break

            if delta > 0:
                nxt = min(current + 1, 20)
                if nxt == current:
                    raise HTTPException(status_code=400, detail="Maximum 20 races")
            elif delta < 0:
                if last_filled:
                    raise HTTPException(
                        status_code=400,
                        detail="Clear " + last_key + " first before removing that race",
                    )
                nxt = max(current - 1, 1)
                if nxt == current:
                    raise HTTPException(status_code=400, detail="Need at least R1")
            else:
                raise HTTPException(status_code=400, detail="Use +1 or -1")

            if nxt < current:
                cur.execute(
                    "SELECT result_id, race_scores FROM results WHERE block_id = %s",
                    (block_id,),
                )
                for row in cur.fetchall() or []:
                    rs = row.get("race_scores") or {}
                    if isinstance(rs, str):
                        rs = json.loads(rs)
                    if not isinstance(rs, dict):
                        rs = {}
                    changed = False
                    for drop_n in range(nxt + 1, current + 1):
                        if rs.pop("R" + str(drop_n), None) is not None:
                            changed = True
                    if changed:
                        cur.execute(
                            "UPDATE results SET race_scores = %s WHERE result_id = %s",
                            (json.dumps(rs), row["result_id"]),
                        )

            discard_count = nxt // 5
            to_count = max(0, nxt - discard_count)
            cur.execute(
                """
                UPDATE regatta_blocks
                SET races_sailed = %s,
                    discard_count = %s,
                    to_count = %s
                WHERE block_id = %s
                """,
                (nxt, discard_count, to_count, block_id),
            )

        _recalculate_fleet_block_scoring_and_ranks(conn, block_id, regatta_id)
        conn.commit()

        fleet = []
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT result_id, rank, total_points_raw, nett_points_raw, race_scores
                FROM results
                WHERE block_id = %s
                ORDER BY rank NULLS LAST, result_id
                """,
                (block_id,),
            )
            for row in cur.fetchall() or []:
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

    return {
        "ok": True,
        "result_id": result_id,
        "block_id": str(block_id),
        "races_sailed": nxt,
        "discard_count": discard_count,
        "to_count": to_count,
        "fleet": fleet,
    }


'''

anchor = '@app.post("/api/wc/super-admin/block/{block_id}/create-late-entry-result")'
if "def patch_fleet_races(" in src:
    print("EP_ALREADY")
elif anchor not in src:
    raise SystemExit("ANCHOR_EP_MISSING")
else:
    src = src.replace(anchor, endpoint + anchor, 1)
    print("EP_PATCHED")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("ccr10", new_js in src)
print("fleet_races", "def patch_fleet_races(" in src)
