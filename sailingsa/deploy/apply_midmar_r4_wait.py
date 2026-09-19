#!/usr/bin/env python3
"""Clear premature Midmar R4 scores. Lap 3 of 4 — wait for finish. Keep R1–R3."""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
RACE = "R4"

KEEP_R3 = {
    8683: ("Hayden Miller", "2", "1", "2"),
    729: ("Luke Wagner", "1", "2", "4"),
    1221: ("Tony Cockerill", "4", "3", "1"),
    21715: ("Gust Funke", "5", "4", "3"),
    1218: ("Paul Changuion", "3", "5", "7"),
    177: ("Craig Millar", "8", "6", "6"),
    15579: ("Daniela Cantarelli", "10", "7", "5"),
    22984: ("Paige Smith", "7", "8", "8"),
    14193: ("Shalin Naidoo", "6", "9", "9"),
    18659: ("Penny Macpherson", "9", "10", "10"),
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


def last_race_val(scores, entries_plus_one):
    nums = []
    for k, v in (scores or {}).items():
        if isinstance(k, str) and k.upper().startswith("R") and k[1:].isdigit() and str(v or "").strip():
            nums.append(int(k[1:]))
    if not nums:
        return 999
    key = max(nums)
    parsed = parse_score(scores.get("R" + str(key)), entries_plus_one)
    return parsed["val"] if parsed else 999


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
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number, boat_name, race_scores
        FROM results WHERE regatta_id=%s ORDER BY result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    if len(rows) != 11:
        raise SystemExit("REFUSE expected 11 results, got " + str(len(rows)))
    by_sid = {int(r["helm_sa_sailing_id"]): r for r in rows if r["helm_sa_sailing_id"] is not None}

    for sid, (name, r1, r2, r3) in KEEP_R3.items():
        row = by_sid.get(sid)
        if not row:
            raise SystemExit("REFUSE missing SAS " + str(sid))
        live = (row["helm_name"] or "").strip()
        if name.split()[0].casefold() not in live.casefold() or name.split()[-1].casefold() not in live.casefold():
            raise SystemExit(f"REFUSE name mismatch {sid} expected {name!r} got {live!r}")
        scores = load_scores(row["race_scores"])
        if str(scores.get("R1") or "").strip() != r1 or str(scores.get("R2") or "").strip() != r2:
            raise SystemExit(f"REFUSE R1/R2 changed {sid} {scores}")
        if str(scores.get("R3") or "").strip() != r3:
            raise SystemExit(f"REFUSE R3 changed {sid} {scores.get('R3')}")
        print("KEEP", sid, live, scores.get("R1"), scores.get("R2"), scores.get("R3"), "had_R4", scores.get(RACE))

    caitlin = by_sid.get(28155)
    if not caitlin or "caitlin" not in (caitlin["helm_name"] or "").casefold():
        raise SystemExit("REFUSE Caitlin missing")
    cait = load_scores(caitlin["race_scores"])
    if "RET" not in str(cait.get("R1") or "") or "DNS" not in str(cait.get("R2") or "") or "DNS" not in str(cait.get("R3") or ""):
        raise SystemExit("REFUSE Caitlin codes changed: " + str(cait))
    print("CAITLIN_KEEP", cait)

    entries = len(rows)
    entries_plus_one = entries + 1
    now = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(second=0, microsecond=0)
    cleared = 0

    for row in rows:
        scores = load_scores(row["race_scores"])
        if RACE in scores:
            scores.pop(RACE, None)
            cleared += 1
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
        print("CLEARED" if sailed == 3 else "ROW", row["helm_name"], "sailed", sailed, "nett", nett)

    if cleared != 5:
        raise SystemExit("REFUSE expected to clear R4 from 5 boats, got " + str(cleared))

    cur.execute(
        "SELECT result_id, race_scores, nett_points_raw FROM results WHERE regatta_id=%s",
        (RID,),
    )
    ranked = []
    for r in cur.fetchall():
        scores = load_scores(r["race_scores"])
        if RACE in scores and str(scores.get(RACE) or "").strip():
            raise SystemExit("REFUSE R4 still present")
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
        SELECT rank, helm_name, sail_number, boat_name, race_scores,
               races_sailed, total_points_raw, nett_points_raw
        FROM results WHERE regatta_id=%s ORDER BY rank NULLS LAST, result_id
        """,
        (RID,),
    )
    print("===== RANKED AFTER WAIT =====")
    for r in cur.fetchall():
        print(dict(r))
    print("AS_AT", now.isoformat())
    print("WAITING_R4_FINISH lap 3 of 4")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
