#!/usr/bin/env python3
"""Midmar R1: Luke 1, Hayden 2, Paul 3. Appendix A low-point + auto rank.

Other boats stay unscored until the next update. No invented DNC/DNF.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
RACE = "R1"

# Places as given. Helm SAS IDs already checksummed on live.
PLACES = [
    (729, "Luke Wagner", "1"),
    (8683, "Hayden Miller", "2"),
    (1218, "Paul Changuion", "3"),
]


def parse_score(val, entries_plus_one):
    raw = str(val or "").strip()
    if not raw:
        return None
    is_br = raw.startswith("(") and raw.endswith(")")
    num = None
    import re

    m = re.search(r"[\d.]+", raw)
    if m:
        num = abs(float(m.group(0)))
    elif re.search(r"(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)", raw, re.I):
        num = float(entries_plus_one)
    return {"raw": raw, "val": num or 0.0, "is_br": is_br}


def score_totals(scores, discard_count, entries_plus_one):
    items = []
    for k, v in scores.items():
        if not (isinstance(k, str) and k.upper().startswith("R") and k[1:].isdigit()):
            continue
        parsed = parse_score(v, entries_plus_one)
        if parsed is None:
            continue
        items.append((int(k[1:]), k, parsed))
    items.sort(key=lambda x: x[0])
    total = sum(p["val"] for _, _, p in items)
    discard_idxs = set()
    if discard_count > 0 and items:
        ranked = sorted(range(len(items)), key=lambda i: items[i][2]["val"], reverse=True)
        for i in ranked[:discard_count]:
            discard_idxs.add(i)
    nett = total - sum(items[i][2]["val"] for i in discard_idxs)
    return total, nett, len(items)


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number, boat_name, race_scores
        FROM results WHERE regatta_id=%s ORDER BY result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    if not rows:
        raise SystemExit("NO_RESULTS")
    by_sid = {int(r["helm_sa_sailing_id"]): r for r in rows if r["helm_sa_sailing_id"] is not None}

    for sid, name, _place in PLACES:
        row = by_sid.get(sid)
        if not row:
            raise SystemExit(f"REFUSE missing helm SAS {sid} {name}")
        live = (row["helm_name"] or "").strip()
        if name.split()[0].casefold() not in live.casefold() or name.split()[-1].casefold() not in live.casefold():
            raise SystemExit(f"REFUSE name mismatch {sid} expected {name!r} got {live!r}")
        print("SAS_OK", sid, live, row["sail_number"], row["boat_name"])

    entries = len(rows)
    entries_plus_one = entries + 1
    now = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(second=0, microsecond=0)

    for sid, name, place in PLACES:
        row = by_sid[sid]
        scores = row["race_scores"] or {}
        if isinstance(scores, str):
            scores = json.loads(scores)
        scores = dict(scores)
        scores[RACE] = place
        n_races = len([k for k in scores if str(k).upper().startswith("R") and scores[k]])
        discard = n_races // 5
        total, nett, sailed = score_totals(scores, discard, entries_plus_one)
        cur.execute(
            """
            UPDATE results
            SET race_scores = %s,
                races_sailed = %s,
                discard_count = %s,
                total_points_raw = %s,
                nett_points_raw = %s,
                result_status = 'Provisional',
                as_at_time = %s
            WHERE result_id = %s
            """,
            (psycopg2.extras.Json(scores), sailed, discard, total, nett, now, row["result_id"]),
        )
        print("R1", name, "place", place, "tot", total, "nett", nett)

    # Unscored boats: no invented codes. Keep empty R1. Null nett ranks last.
    scored_sids = {sid for sid, _, _ in PLACES}
    for row in rows:
        sid = int(row["helm_sa_sailing_id"]) if row["helm_sa_sailing_id"] is not None else None
        if sid in scored_sids:
            continue
        scores = row["race_scores"] or {}
        if isinstance(scores, str):
            scores = json.loads(scores)
        if scores.get(RACE):
            continue
        cur.execute(
            """
            UPDATE results
            SET result_status = 'Provisional',
                as_at_time = %s
            WHERE result_id = %s
            """,
            (now, row["result_id"]),
        )

    # Auto rank: Appendix A by nett (0/null last), then result_id.
    cur.execute(
        """
        WITH ranked AS (
            SELECT result_id,
                   ROW_NUMBER() OVER (
                       ORDER BY COALESCE(NULLIF(nett_points_raw, 0), 999999) ASC,
                                result_id ASC
                   ) AS new_rank
            FROM results
            WHERE block_id = %s
        )
        UPDATE results r
        SET rank = ranked.new_rank
        FROM ranked
        WHERE r.result_id = ranked.result_id
        """,
        (BLOCK,),
    )
    print("RANK_ROWS", cur.rowcount)

    cur.execute(
        """
        UPDATE regatta_blocks
        SET races_sailed = 1,
            discard_count = 0,
            to_count = 1,
            scoring_system = 'Appendix A',
            entries_raced = %s
        WHERE block_id = %s
        """,
        (entries, BLOCK),
    )
    cur.execute(
        """
        UPDATE regattas
        SET result_status = 'Provisional',
            as_at_time = %s,
            scoring_system = 'Appendix A',
            scoring_mode = 'appendix_a_low_point',
            result_type = 'LOW_POINT'
        WHERE regatta_id = %s
        """,
        (now, RID),
    )

    conn.commit()
    cur.execute(
        """
        SELECT rank, helm_name, sail_number, race_scores, total_points_raw, nett_points_raw
        FROM results WHERE regatta_id=%s ORDER BY rank NULLS LAST, result_id
        """,
        (RID,),
    )
    print("===== RANKED =====")
    for r in cur.fetchall():
        print(dict(r))
    print("AS_AT", now.isoformat())
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
