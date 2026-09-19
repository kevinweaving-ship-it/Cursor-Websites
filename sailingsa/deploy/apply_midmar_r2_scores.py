#!/usr/bin/env python3
"""Midmar R2 places 1–10 + 11th RET. Appendix A. Do not invent IDs."""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
RACE = "R2"

# Called places. Helm SAS already on live. Bryan = Paige 741. Craig Deverson = Shalin 748.
PLACES = [
    (8683, "Hayden Miller", "1"),
    (729, "Luke Wagner", "2"),
    (1221, "Tony Cockerill", "3"),
    (21715, "Gust Funke", "4"),
    (1218, "Paul Changuion", "5"),
    (177, "Craig Millar", "6"),
    (15579, "Daniela Cantarelli", "7"),
    (22984, "Paige Smith", "8"),  # Bryan Paxman crew
    (14193, "Shalin Naidoo", "9"),  # Craig Deverson boat
    (18659, "Penny Macpherson", "10"),
]
RET_SID = 28155  # Caitlin / Jethro 297 — no finish, RET for now


def parse_score(val, entries_plus_one):
    raw = str(val or "").strip()
    if not raw:
        return None
    is_br = raw.startswith("(") and raw.endswith(")")
    num = None
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


def last_race_key(scores):
    nums = []
    for k, v in (scores or {}).items():
        if isinstance(k, str) and k.upper().startswith("R") and k[1:].isdigit() and str(v or "").strip():
            nums.append(int(k[1:]))
    return max(nums) if nums else 0


def last_race_val(scores, entries_plus_one):
    key = last_race_key(scores)
    if key < 1:
        return 999
    parsed = parse_score(scores.get("R" + str(key)), entries_plus_one)
    if not parsed:
        return 999
    return parsed["val"]


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number, boat_name,
               crew_name, crew2_name, race_scores, validation_flag, entry_id
        FROM results WHERE regatta_id=%s ORDER BY result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    if len(rows) != 11:
        raise SystemExit("REFUSE expected 11 results, got " + str(len(rows)))
    by_sid = {int(r["helm_sa_sailing_id"]): r for r in rows if r["helm_sa_sailing_id"] is not None}

    for sid, name, _place in PLACES:
        row = by_sid.get(sid)
        if not row:
            raise SystemExit(f"REFUSE missing helm SAS {sid} {name}")
        live = (row["helm_name"] or "").strip()
        if name.split()[0].casefold() not in live.casefold() or name.split()[-1].casefold() not in live.casefold():
            raise SystemExit(f"REFUSE name mismatch {sid} expected {name!r} got {live!r}")
        print("SAS_OK", sid, live, row["sail_number"], row["boat_name"])

    bryan = by_sid[22984]
    if "bryan" not in " ".join(str(bryan.get(k) or "") for k in ("crew_name", "crew2_name")).casefold():
        raise SystemExit("REFUSE Bryan boat missing Bryan crew")
    print("BRYAN_8TH", bryan["helm_name"], bryan["sail_number"], bryan.get("crew_name"))

    deverson = by_sid[14193]
    print("DEVERSON_9TH", deverson["helm_name"], deverson["sail_number"], deverson["boat_name"])

    caitlin = by_sid.get(RET_SID)
    if not caitlin:
        raise SystemExit("REFUSE Caitlin SAS 28155 missing")
    if "caitlin" not in (caitlin["helm_name"] or "").casefold():
        raise SystemExit("REFUSE RET helm not Caitlin: " + str(caitlin["helm_name"]))
    if str(caitlin["sail_number"] or "").strip() != "297":
        raise SystemExit("REFUSE RET sail not 297: " + str(caitlin["sail_number"]))
    print("CAITLIN_RET", caitlin["helm_name"], caitlin["sail_number"])

    # 422 is not in this fleet. Dani 442 is the only nameless boat — Scout goes there.
    sails = {str(r["sail_number"] or "").strip(): r for r in rows}
    if "422" in sails:
        scout_row = sails["422"]
        print("SCOUT_ON_422", scout_row["result_id"], scout_row["helm_name"])
    elif "442" in sails and not (sails["442"]["boat_name"] or "").strip():
        scout_row = sails["442"]
        print("SCOUT_ON_442_NOT_422", scout_row["result_id"], scout_row["helm_name"], "no sail 422 in fleet")
    else:
        raise SystemExit("REFUSE no sail 422 and 442 is not a blank Scout target")

    essex = sails.get("2013")
    if not essex or (essex["boat_name"] or "").strip().casefold() != "essex girl":
        raise SystemExit("REFUSE Essex Girl 2013 missing")
    print("ESSEX_CONFIRM", essex["helm_name"], essex["sail_number"], essex["boat_name"])

    entries = len(rows)
    entries_plus_one = entries + 1
    now = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(second=0, microsecond=0)

    scored = []
    for sid, name, place in PLACES:
        scored.append((by_sid[sid], place))
    scored.append((caitlin, "RET"))

    scored_ids = set()
    for row, place in scored:
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
            WHERE result_id = %s AND regatta_id = %s
            """,
            (psycopg2.extras.Json(scores), sailed, discard, total, nett, now, row["result_id"], RID),
        )
        scored_ids.add(row["result_id"])
        print("R2", row["helm_name"], "place", place, "tot", total, "nett", nett)

    if len(scored_ids) != 11:
        raise SystemExit("REFUSE not all 11 boats scored R2")

    cur.execute(
        "UPDATE results SET boat_name=%s, validation_flag=NULL WHERE result_id=%s AND regatta_id=%s",
        ("Scout", scout_row["result_id"], RID),
    )
    if scout_row.get("entry_id"):
        cur.execute(
            "UPDATE entries SET boat_name=%s WHERE entry_id=%s AND regatta_id=%s",
            ("Scout", scout_row["entry_id"], RID),
        )
    print("SCOUT_WRITTEN", scout_row["sail_number"], scout_row["helm_name"])

    cur.execute(
        """
        UPDATE results
        SET validation_flag = NULL
        WHERE result_id=%s AND regatta_id=%s AND validation_flag='boat_name_temp'
        """,
        (essex["result_id"], RID),
    )
    print("ESSEX_FLAG_CLEARED", cur.rowcount)

    # Rank by nett ASC, last-race ASC, result_id. RET still uses 12 points.
    cur.execute(
        """
        SELECT result_id, race_scores, nett_points_raw
        FROM results WHERE regatta_id=%s
        """,
        (RID,),
    )
    live = cur.fetchall()
    ranked = []
    for r in live:
        scores = r["race_scores"] or {}
        if isinstance(scores, str):
            scores = json.loads(scores)
        ranked.append(
            (
                float(r["nett_points_raw"] or 999998),
                last_race_val(scores, entries_plus_one),
                r["result_id"],
            )
        )
    ranked.sort()
    for i, (_nett, _last, rid) in enumerate(ranked, 1):
        cur.execute("UPDATE results SET rank=%s WHERE result_id=%s AND regatta_id=%s", (i, rid, RID))

    cur.execute(
        """
        UPDATE regatta_blocks
        SET races_sailed = 2,
            discard_count = 0,
            to_count = 2,
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
        SELECT rank, helm_name, sail_number, boat_name, race_scores,
               total_points_raw, nett_points_raw, validation_flag
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
