#!/usr/bin/env python3
"""Midmar R4 finish places 1–5 only (not a lap). Rest to follow — do not invent RET/DNS/DNC."""
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

# Called places. Helm SAS already on live. Thomas = Gust Funke crew. Do not invent 6–11.
PLACES = [
    (729, "Luke Wagner", "1"),
    (8683, "Hayden Miller", "2"),
    (1218, "Paul Changuion", "3"),
    (1221, "Tony Cockerill", "4"),
    (21715, "Gust Funke", "5"),  # Thomas Funke crew
]
HOLD_SIDS = {177, 15579, 22984, 14193, 18659, 28155}


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

    thomas = by_sid[21715]
    crew = " ".join(str(thomas.get(k) or "") for k in ("crew_name", "crew2_name"))
    if "thomas" not in crew.casefold():
        raise SystemExit("REFUSE Thomas not on Gust boat: " + crew)
    print("THOMAS_5TH", thomas["helm_name"], thomas["sail_number"], thomas["boat_name"], crew)

    millar = by_sid[177]
    if str(millar["sail_number"] or "").strip() != "200":
        raise SystemExit("REFUSE Craig Millar sail not 200: " + str(millar["sail_number"]))
    print("SMOKE_OK", millar["sail_number"], millar["boat_name"])

    for sid in HOLD_SIDS:
        if sid not in by_sid:
            raise SystemExit("REFUSE hold boat missing SAS " + str(sid))
        print("HOLD_NO_R4", sid, by_sid[sid]["helm_name"], by_sid[sid]["sail_number"])

    entries = len(rows)
    entries_plus_one = entries + 1
    now = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(second=0, microsecond=0)

    scored_ids = set()
    for sid, name, place in PLACES:
        row = by_sid[sid]
        scores = load_scores(row["race_scores"])
        if RACE in scores and str(scores.get(RACE) or "").strip():
            print("R4_OVERWRITE", name, scores.get(RACE), "->", place)
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
            WHERE result_id = %s AND regatta_id = %s
            """,
            (psycopg2.extras.Json(scores), sailed, discard, total, nett, now, row["result_id"], RID),
        )
        scored_ids.add(row["result_id"])
        print("R4", row["helm_name"], "place", place, "tot", total, "nett", nett, "sailed", sailed)

    if len(scored_ids) != 5:
        raise SystemExit("REFUSE expected 5 R4 finishers, got " + str(len(scored_ids)))

    for sid in HOLD_SIDS:
        row = by_sid[sid]
        scores = load_scores(row["race_scores"])
        if RACE in scores and str(scores.get(RACE) or "").strip():
            raise SystemExit("REFUSE hold boat already has R4: " + str(row["helm_name"]) + " " + str(scores.get(RACE)))
        n_races = len([k for k in scores if str(k).upper().startswith("R") and scores[k]])
        discard = n_races // 5
        total, nett, sailed = score_totals(scores, discard, entries_plus_one)
        cur.execute(
            """
            UPDATE results
            SET races_sailed = %s,
                discard_count = %s,
                total_points_raw = %s,
                nett_points_raw = %s,
                result_status = 'Provisional',
                as_at_time = %s
            WHERE result_id = %s AND regatta_id = %s
            """,
            (sailed, discard, total, nett, now, row["result_id"], RID),
        )
        print("HOLD", row["helm_name"], "no R4 tot", total, "nett", nett, "sailed", sailed)

    # Partial R4: 4-race boats stay above unfinished 3-race boats.
    cur.execute(
        "SELECT result_id, race_scores, nett_points_raw, races_sailed FROM results WHERE regatta_id=%s",
        (RID,),
    )
    ranked = []
    for r in cur.fetchall():
        scores = load_scores(r["race_scores"])
        sailed = int(r["races_sailed"] or 0)
        ranked.append(
            (
                -sailed,
                float(r["nett_points_raw"] or 999998),
                last_race_val(scores, entries_plus_one),
                r["result_id"],
            )
        )
    ranked.sort()
    for i, (_neg_sailed, _nett, _last, rid) in enumerate(ranked, 1):
        cur.execute("UPDATE results SET rank=%s WHERE result_id=%s AND regatta_id=%s", (i, rid, RID))

    cur.execute(
        """
        UPDATE regatta_blocks
        SET races_sailed = 4,
            discard_count = 0,
            to_count = 4,
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
    for r in cur.fetchall():
        print(dict(r))
        scores = load_scores(r["race_scores"])
        sid = int(r["helm_sa_sailing_id"])
        if sid in HOLD_SIDS and RACE in scores and str(scores.get(RACE) or "").strip():
            raise SystemExit("REFUSE wrote R4 onto hold boat " + r["helm_name"])
        if sid not in HOLD_SIDS and str(scores.get(RACE) or "").strip() == "":
            raise SystemExit("REFUSE missing R4 on finisher " + r["helm_name"])
    print("AS_AT", now.isoformat())
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
