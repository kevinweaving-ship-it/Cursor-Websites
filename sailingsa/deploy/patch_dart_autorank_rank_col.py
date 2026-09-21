#!/usr/bin/env python3
"""Surgical live patch: Dart/Cape club sheets must paint Rank after scores.

Does not replace api.py. Only the official-rank lock, live-fleets slug,
and empty-R1 fake ranks.
"""

from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OFFICIAL_OLD = """        try:
            _orank = r.get("rank")
            if _orank is not None and str(_orank).strip() != "":
                _tr_extra += f' data-official-rank="{html_module.escape(str(int(float(_orank))), quote=True)}"'
        except (TypeError, ValueError):
            pass
"""

OFFICIAL_NEW = """        try:
            _orank = r.get("rank")
            if (
                _orank is not None
                and str(_orank).strip() != ""
                and _fleet_has_race_scores
            ):
                _tr_extra += f' data-official-rank="{html_module.escape(str(int(float(_orank))), quote=True)}"'
        except (TypeError, ValueError):
            pass
"""

LIVE_OLD = '''@app.get("/api/regatta/{regatta_id}/cape-live-fleets")
def cape_live_fleets(regatta_id: str):
    """Cape Classic only: live rank/total/nett/race cells for open pages (no refresh)."""
    if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
        raise HTTPException(status_code=404, detail="not Cape Classic")
    import json

    with db_connection() as conn:
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
'''

LIVE_NEW = '''@app.get("/api/regatta/{regatta_id}/cape-live-fleets")
def cape_live_fleets(regatta_id: str):
    """Club live rank/total/nett/race cells for open pages (no refresh)."""
    rid = str(regatta_id or "")
    if not (
        rid.startswith("2026-09-13-zvyc-cape-classic")
        or rid.startswith("2026-09-24-hmyc-dart-18-nationals")
    ):
        raise HTTPException(status_code=404, detail="not a club-score event")
    import json

    with db_connection() as conn:
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
                (rid + "%", rid + "%"),
            )
'''

RANK_OLD = '''        fleet_for_rank = cur.fetchall() or []
        for i, row in enumerate(sort_result_rows_appendix_a(fleet_for_rank), 1):
            cur.execute(
                "UPDATE results SET rank = %s WHERE result_id = %s AND block_id = %s",
                (i, row["result_id"], block_id),
            )
'''

RANK_NEW = '''        fleet_for_rank = cur.fetchall() or []

        def _legacy_row_has_score(row):
            rs = row.get("race_scores") or {}
            if isinstance(rs, str):
                try:
                    rs = json.loads(rs)
                except Exception:
                    rs = {}
            if not isinstance(rs, dict):
                return False
            return any(str(v or "").strip() for v in rs.values())

        if not any(_legacy_row_has_score(row) for row in fleet_for_rank):
            cur.execute(
                "UPDATE results SET rank = NULL WHERE block_id = %s",
                (block_id,),
            )
        else:
            for i, row in enumerate(sort_result_rows_appendix_a(fleet_for_rank), 1):
                cur.execute(
                    "UPDATE results SET rank = %s WHERE result_id = %s AND block_id = %s",
                    (i, row["result_id"], block_id),
                )
'''


def main() -> int:
    text = API.read_text()
    for old, new, label in (
        (OFFICIAL_OLD, OFFICIAL_NEW, "official-rank"),
        (LIVE_OLD, LIVE_NEW, "cape-live-fleets"),
        (RANK_OLD, RANK_NEW, "empty-score ranks"),
    ):
        if new in text and old not in text:
            print("already", label)
            continue
        if old not in text:
            raise SystemExit(f"pattern not found: {label}")
        text = text.replace(old, new, 1)
        print("patched", label)
    text = text.replace("club-score-edit.js?v=ccr21", "club-score-edit.js?v=ccr23")
    text = text.replace("club-score-edit.js?v=ccr22", "club-score-edit.js?v=ccr23")
    API.write_text(text)
    print("ok", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
