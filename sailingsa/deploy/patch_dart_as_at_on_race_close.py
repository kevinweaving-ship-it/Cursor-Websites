#!/usr/bin/env python3
"""Stamp Dart as_at_time on each race-score save / race-column change."""

from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

FN = '''def _touch_live_club_as_at(conn, regatta_id) -> None:
    """Dart club scoring: header as_at follows the last race close / score save."""
    rid = str(regatta_id or "").strip()
    if not rid.startswith("2026-09-24-hmyc-dart-18-nationals"):
        return
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.regattas SET as_at_time = NOW() WHERE regatta_id = %s",
            (rid,),
        )
        cur.execute(
            "UPDATE public.results SET as_at_time = NOW() WHERE regatta_id = %s",
            (rid,),
        )


'''

RECALC_DEF = "def _recalculate_fleet_block_scoring_and_ranks(conn, block_id: int, regatta_id: int) -> None:\n"

RACE_OLD = """        _recalculate_fleet_block_scoring_and_ranks(conn, block_id, regatta_id)
        conn.commit()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                \"\"\"
                SELECT r.*, rb.races_sailed, rb.race_column_labels, rb.discard_count
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE r.result_id = %s
                \"\"\",
                (result_id,),
            )
"""

RACE_NEW = """        _recalculate_fleet_block_scoring_and_ranks(conn, block_id, regatta_id)
        _touch_live_club_as_at(conn, regatta_id)
        conn.commit()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                \"\"\"
                SELECT r.*, rb.races_sailed, rb.race_column_labels, rb.discard_count
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE r.result_id = %s
                \"\"\",
                (result_id,),
            )
"""

FLEET_OLD = """            _recalculate_fleet_block_scoring_and_ranks(conn, block_id, regatta_id)
        conn.commit()
"""

FLEET_NEW = """            _recalculate_fleet_block_scoring_and_ranks(conn, block_id, regatta_id)
            _touch_live_club_as_at(conn, regatta_id)
        conn.commit()
"""

OUT_OLD = '''            "races_sailed": updated["races_sailed"],
            "discard_count": updated["discard_count"],
'''

OUT_NEW = '''            "races_sailed": updated["races_sailed"],
            "discard_count": updated["discard_count"],
'''

LIVE_OLD = '''    return {"ok": True, "fleets": fleets}
'''

LIVE_NEW = '''    as_at = None
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT as_at_time FROM public.regattas WHERE regatta_id = %s LIMIT 1",
                (rid,),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                as_at = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
    return {"ok": True, "fleets": fleets, "as_at_time": as_at}
'''


def _add_as_at_to_out(text: str) -> str:
    needle = '''            "races_sailed": updated["races_sailed"],
            "discard_count": updated["discard_count"],'''
    extra = '''            "races_sailed": updated["races_sailed"],
            "discard_count": updated["discard_count"],
            "as_at_time": None,'''
    if '"as_at_time": None' in text[text.find(needle) : text.find(needle) + 400] if needle in text else False:
        return text
    if needle not in text:
        return text
    # fill as_at after out = { is built — simpler: inject read before return out
    mark = "        if _regatta_slug_is_sa_pilot_standalone(str(regatta_id)):\n"
    inject = '''        try:
            with conn.cursor() as _atcur:
                _atcur.execute(
                    "SELECT as_at_time FROM public.regattas WHERE regatta_id = %s LIMIT 1",
                    (str(regatta_id),),
                )
                _atrow = _atcur.fetchone()
                if _atrow and _atrow[0] is not None:
                    out["as_at_time"] = (
                        _atrow[0].isoformat() if hasattr(_atrow[0], "isoformat") else str(_atrow[0])
                    )
        except Exception:
            pass
        if _regatta_slug_is_sa_pilot_standalone(str(regatta_id)):
'''
    if "out[\"as_at_time\"]" in text:
        return text
    if mark not in text:
        raise SystemExit("out inject mark not found")
    return text.replace(mark, inject, 1)


def main() -> int:
    text = API.read_text()
    if "def _touch_live_club_as_at" not in text:
        if RECALC_DEF not in text:
            raise SystemExit("recalc def not found")
        text = text.replace(RECALC_DEF, FN + RECALC_DEF, 1)
        print("added _touch_live_club_as_at")
    else:
        print("already fn")
    if RACE_OLD in text:
        text = text.replace(RACE_OLD, RACE_NEW, 1)
        print("patched race touch")
    else:
        print("skip race touch")
    if FLEET_OLD in text and "_touch_live_club_as_at(conn, regatta_id)" not in text.split("def patch_fleet_races")[1][:4000]:
        # only first fleet-races occurrence after dart-aware function
        text = text.replace(FLEET_OLD, FLEET_NEW, 1)
        print("patched fleet-races touch")
    elif "_touch_live_club_as_at(conn, regatta_id)" in text:
        print("fleet touch present or skip")
    text = _add_as_at_to_out(text)
    if LIVE_OLD in text and '"as_at_time": as_at}' not in text and '"fleets": fleets, "as_at_time"' not in text:
        text = text.replace(LIVE_OLD, LIVE_NEW, 1)
        print("patched live-fleets as_at")
    text = text.replace("club-score-edit.js?v=ccr25", "club-score-edit.js?v=ccr26")
    text = text.replace("club-score-edit.js?v=ccr24", "club-score-edit.js?v=ccr26")
    text = text.replace("club-score-edit.js?v=ccr23", "club-score-edit.js?v=ccr26")
    API.write_text(text)
    print("ok", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
