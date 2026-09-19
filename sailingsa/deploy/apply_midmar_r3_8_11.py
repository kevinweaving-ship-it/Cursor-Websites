#!/usr/bin/env python3
"""Midmar R3 8th Bryan, 9th Craig Deverson, 10th Penny, DNS Jethro. Appendix A."""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
RACE = "R3"

# Called names. Helm SAS already on live. Bryan = Paige 741. Craig Deverson = Shalin 748. Jethro = Caitlin 297.
PLACES = [
    (22984, "Paige Smith", "8"),  # Bryan Paxman crew
    (14193, "Shalin Naidoo", "9"),  # Craig Deverson boat
    (18659, "Penny Macpherson", "10"),
]
DNS_SID = 28155  # Caitlin / Jethro Milne
KEEP_R3 = {
    1221: "1",
    8683: "2",
    21715: "3",
    729: "4",
    15579: "5",
    177: "6",
    1218: "7",
}


def parse_score(val, entries_plus_one):
    raw = str(val or "").strip()
    if not raw:
        return None
    num = None
    m = re.search(r"[\d.]+", raw)
    if m:
        num = abs(float(m.group(0)))
    elif re.search(r"(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)", raw, re.I):
        num = float(entries_plus_one)
    return {"raw": raw, "val": num or 0.0}


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


def load_scores(raw):
    scores = raw or {}
    if isinstance(scores, str):
        scores = json.loads(scores)
    return dict(scores)


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
    if str(bryan["sail_number"] or "").strip() != "741":
        raise SystemExit("REFUSE Bryan sail not 741: " + str(bryan["sail_number"]))
    print("BRYAN_8TH", bryan["helm_name"], bryan["sail_number"], bryan.get("crew_name"))

    deverson = by_sid[14193]
    if str(deverson["sail_number"] or "").strip() != "748":
        raise SystemExit("REFUSE Deverson sail not 748: " + str(deverson["sail_number"]))
    print("DEVERSON_9TH", deverson["helm_name"], deverson["sail_number"], deverson["boat_name"])

    penny = by_sid[18659]
    if "penny" not in (penny["helm_name"] or "").casefold():
        raise SystemExit("REFUSE Penny helm mismatch: " + str(penny["helm_name"]))
    print("PENNY_10TH", penny["helm_name"], penny["sail_number"])

    caitlin = by_sid.get(DNS_SID)
    if not caitlin or "caitlin" not in (caitlin["helm_name"] or "").casefold():
        raise SystemExit("REFUSE Caitlin SAS 28155 missing")
    if "jethro" not in " ".join(str(caitlin.get(k) or "") for k in ("crew_name", "crew2_name")).casefold():
        raise SystemExit("REFUSE Jethro boat missing Jethro crew")
    if str(caitlin["sail_number"] or "").strip() != "297":
        raise SystemExit("REFUSE DNS sail not 297: " + str(caitlin["sail_number"]))
    print("JETHRO_DNS", caitlin["helm_name"], caitlin["sail_number"], caitlin.get("crew_name"))

    for sid, place in KEEP_R3.items():
        row = by_sid.get(sid)
        if not row:
            raise SystemExit("REFUSE keep-R3 boat missing " + str(sid))
        scores = load_scores(row["race_scores"])
        if str(scores.get(RACE) or "").strip() != place:
            raise SystemExit(f"REFUSE R3 {sid} expected {place} got {scores.get(RACE)}")
        print("KEEP_R3", row["helm_name"], place)

    entries = len(rows)
    entries_plus_one = entries + 1
    now = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(second=0, microsecond=0)

    scored = [(by_sid[sid], place) for sid, _name, place in PLACES]
    scored.append((caitlin, "DNS"))

    scored_ids = set()
    for row, place in scored:
        scores = load_scores(row["race_scores"])
        store = place
        if place in ("RET", "DNS"):
            store = str(int(entries_plus_one)) + "\n" + place
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
        print("R3", row["helm_name"], "place", place, "tot", total, "nett", nett)

    if len(scored_ids) != 4:
        raise SystemExit("REFUSE expected 4 remaining R3 boats, got " + str(len(scored_ids)))

    # Full fleet now has R3. Rank nett ASC, last-race ASC.
    cur.execute(
        "SELECT result_id, race_scores, nett_points_raw FROM results WHERE regatta_id=%s",
        (RID,),
    )
    ranked = []
    for r in cur.fetchall():
        scores = load_scores(r["race_scores"])
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
        SET races_sailed = 3,
            discard_count = 0,
            to_count = 3,
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
        SELECT rank, helm_name, helm_sa_sailing_id, sail_number, boat_name, race_scores,
               races_sailed, total_points_raw, nett_points_raw
        FROM results WHERE regatta_id=%s ORDER BY rank NULLS LAST, result_id
        """,
        (RID,),
    )
    print("===== RANKED =====")
    have_r3 = 0
    for r in cur.fetchall():
        print(dict(r))
        scores = load_scores(r["race_scores"])
        if str(scores.get(RACE) or "").strip():
            have_r3 += 1
    if have_r3 != 11:
        raise SystemExit("REFUSE expected all 11 boats to have R3, got " + str(have_r3))
    print("AS_AT", now.isoformat())
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
