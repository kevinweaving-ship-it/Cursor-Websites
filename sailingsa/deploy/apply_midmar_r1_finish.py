#!/usr/bin/env python3
"""Midmar R1: 11 entries after Megan DNS/DNC arrival scratch.

Appendix A low-point. RET = entries+1, ranked last.
6th other Craig (Sheba), 8th Craig Millar. Bryan = Paige 741. Jethro = 297 RET.
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

# Places as called. Helm SAS IDs already checksummed on live.
PLACES = [
    (729, "Luke Wagner", "1"),
    (8683, "Hayden Miller", "2"),
    (1218, "Paul Changuion", "3"),
    (1221, "Tony Cockerill", "4"),
    (21715, "Gust Funke", "5"),
    (14193, "Shalin Naidoo", "6"),  # Craig Deverson boat — not Craig Millar
    (22984, "Paige Smith", "7"),  # Bryan Paxman boat
    (177, "Craig Millar", "8"),
    (18659, "Penny Macpherson", "9"),
    (15579, "Daniela Cantarelli", "10"),
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


def resolve_jethro_ret(rows, used_ids):
    hits = []
    for row in rows:
        if row["result_id"] in used_ids:
            continue
        blob = " ".join(
            str(row.get(k) or "")
            for k in ("helm_name", "crew_name", "crew2_name", "sail_number", "boat_name")
        ).casefold()
        sn = str(row.get("sail_number") or "").strip()
        if sn == "297" or "jethro" in blob:
            hits.append(row)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit("REFUSE Jethro/297 boat missing")
    raise SystemExit("REFUSE ambiguous Jethro boat: " + ", ".join(str(r["sail_number"]) for r in hits))


def resolve_sail_200(rows, used_ids):
    hits = []
    for row in rows:
        if row["result_id"] in used_ids:
            continue
        sn = str(row["sail_number"] or "").strip()
        if sn == "200" or sn == "2000":
            hits.append(row)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        return None
    raise SystemExit("REFUSE ambiguous sail 200: " + ", ".join(str(r["sail_number"]) for r in hits))


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number, boat_name,
               crew_name, crew2_name, race_scores
        FROM results WHERE regatta_id=%s ORDER BY result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    if not rows:
        raise SystemExit("NO_RESULTS")

    megan = [
        r
        for r in rows
        if int(r["helm_sa_sailing_id"] or 0) == 14790
        or (
            "megan" in (r["helm_name"] or "").casefold()
            and "gauld" in (r["helm_name"] or "").casefold()
        )
    ]
    if len(megan) != 1:
        raise SystemExit("REFUSE Megan Gauld row count " + str(len(megan)))
    mg = megan[0]
    live_m = (mg["helm_name"] or "").strip()
    if "megan" not in live_m.casefold() or "gauld" not in live_m.casefold():
        raise SystemExit("REFUSE Megan name mismatch " + live_m)
    cur.execute("DELETE FROM results WHERE result_id=%s AND regatta_id=%s", (mg["result_id"], RID))
    print("DELETED_RESULT", mg["result_id"], live_m, mg.get("sail_number"), cur.rowcount)
    try:
        cur.execute(
            "DELETE FROM entries WHERE regatta_id=%s AND helm_sas_id::text = '14790'",
            (RID,),
        )
        print("DELETED_ENTRY", cur.rowcount)
    except Exception as e:
        conn.rollback()
        print("ENTRY_DELETE_SKIP", type(e).__name__, e)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number, boat_name,
               crew_name, crew2_name, race_scores
        FROM results WHERE regatta_id=%s ORDER BY result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    print("ENTRIES_NOW", len(rows))
    if len(rows) != 11:
        raise SystemExit("REFUSE expected 11 results after Megan delete, got " + str(len(rows)))
    by_sid = {int(r["helm_sa_sailing_id"]): r for r in rows if r["helm_sa_sailing_id"] is not None}

    for sid, name, _place in PLACES:
        row = by_sid.get(sid)
        if not row:
            raise SystemExit(f"REFUSE missing helm SAS {sid} {name}")
        live = (row["helm_name"] or "").strip()
        if name.split()[0].casefold() not in live.casefold() or name.split()[-1].casefold() not in live.casefold():
            raise SystemExit(f"REFUSE name mismatch {sid} expected {name!r} got {live!r}")
        print("SAS_OK", sid, live, row["sail_number"], row["boat_name"])

    bryan_row = by_sid[22984]
    crew_blob = " ".join(
        str(bryan_row.get(k) or "") for k in ("crew_name", "crew2_name")
    ).casefold()
    if "bryan" not in crew_blob:
        raise SystemExit("REFUSE Bryan boat missing Bryan crew: " + crew_blob)
    print("BRYAN_BOAT", bryan_row["helm_name"], bryan_row["sail_number"])

    millar = by_sid[177]
    print("MILLAR_8TH", millar["helm_name"], millar["sail_number"], millar["boat_name"])

    sixth = by_sid[14193]
    sixth_blob = " ".join(
        str(sixth.get(k) or "") for k in ("helm_name", "crew_name", "crew2_name")
    ).casefold()
    if "craig" not in sixth_blob:
        other = []
        for row in rows:
            if int(row["helm_sa_sailing_id"] or 0) == 177:
                continue
            blob = " ".join(
                str(row.get(k) or "") for k in ("helm_name", "crew_name", "crew2_name")
            ).casefold()
            if "craig" in blob:
                other.append(row)
        print("SIXTH_NO_CRAIG_ON_SHALIN", sixth["helm_name"], sixth.get("crew_name"), sixth.get("crew2_name"))
        if len(other) == 1:
            sixth = other[0]
            print("SIXTH_OTHER_CRAIG", sixth["helm_name"], sixth["sail_number"])
        else:
            print("SIXTH_KEEP_SHALIN_748")
    else:
        print("SIXTH_CRAIG_BOAT", sixth["helm_name"], sixth["sail_number"], sixth.get("crew_name"), sixth.get("crew2_name"))

    places = []
    for sid, name, place in PLACES:
        if place == "6":
            sid = int(sixth["helm_sa_sailing_id"])
            name = (sixth["helm_name"] or name).strip()
            by_sid[sid] = sixth
        places.append((sid, name, place))
    used_ids = {by_sid[sid]["result_id"] for sid, _, _ in places}
    jethro = resolve_jethro_ret(rows, used_ids)
    jethro_sid = int(jethro["helm_sa_sailing_id"])
    by_sid[jethro_sid] = jethro
    places.append((jethro_sid, (jethro["helm_name"] or "Jethro").strip(), "RET"))
    print("JETHRO_RET", jethro["helm_name"], jethro["sail_number"], jethro["boat_name"])

    entries = len(rows)
    entries_plus_one = entries + 1
    now = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(second=0, microsecond=0)

    scored_ids = set()
    for sid, name, place in places:
        row = by_sid[sid]
        scores = row["race_scores"] or {}
        if isinstance(scores, str):
            scores = json.loads(scores)
        scores = dict(scores)
        store = place
        if place == "RET":
            store = str(int(entries_plus_one)) + "\nRET"
        scores[RACE] = store
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
        scored_ids.add(row["result_id"])
        print("R1", name, "place", place, "tot", total, "nett", nett)

    for row in rows:
        if row["result_id"] in scored_ids:
            continue
        scores = row["race_scores"] or {}
        if isinstance(scores, str):
            scores = json.loads(scores)
        scores = dict(scores)
        if scores.get(RACE):
            scores.pop(RACE, None)
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
                (
                    psycopg2.extras.Json(scores),
                    sailed or None,
                    discard,
                    total or None,
                    nett or None,
                    now,
                    row["result_id"],
                ),
            )
            print("R1_CLEARED", row["helm_name"])
        else:
            cur.execute(
                """
                UPDATE results
                SET result_status = 'Provisional',
                    as_at_time = %s
                WHERE result_id = %s
                """,
                (now, row["result_id"]),
            )

    cur.execute(
        """
        WITH ranked AS (
            SELECT result_id,
                   ROW_NUMBER() OVER (
                       ORDER BY CASE
                                    WHEN COALESCE(race_scores->>'R1', '') ~* 'RET' THEN 2
                                    WHEN nett_points_raw IS NULL OR nett_points_raw = 0 THEN 1
                                    ELSE 0
                                END ASC,
                                COALESCE(NULLIF(nett_points_raw, 0), 999998) ASC,
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
