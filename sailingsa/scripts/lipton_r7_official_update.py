#!/usr/bin/env python3
"""Write official Lipton 2026 R1–R7 into results. Checksum vs Sailwave PDF.

Source: Overall after 7 races _updated.pdf
  Lipton Challenge Cup, Table Bay
  Sailed: 7, Discards: 0, To count: 7, Entries: 17, Appendix A
  Results are provisional as of 6:27 on August 29, 2026
  Display: Results are Provisional as at 29 August 2026 at 06:27

Does not invent GPS/Nett. Does not rename helm/crew.
Race 6 is the revised sheet (768 / 1167 / 763 = 18.0 DSQ).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import RealDictCursor

REGATTA = "2026-08-29-lipton-challenge-cup"
SAST = ZoneInfo("Africa/Johannesburg")
AS_AT = datetime(2026, 8, 29, 6, 27, tzinfo=SAST)
N_ENTRIES = 17
DSQ_PTS = float(N_ENTRIES + 1)  # Appendix A: DSQ = entries + 1 = 18

# sail -> club code already on the results row (do not invent names)
CLUB = {
    "1571": "HYC",
    "766": "RCYC",
    "774": "UCTYC",
    "1175": "SBYC",
    "173": "RCYC Academy",
    "768": "RNYC",
    "1169": "FBYC",
    "1277": "WBYC",
    "1116": "PYC",
    "1167": "LDYC",
    "763": "KYC",
    "185": "GLYC",
    "1139": "BYC",
    "771": "IZIVUNGUVUNGU",
    "1237": "LYC",
    "1239": "TSC",
    "1138": "WYAC",
}

# Official Sailwave scores. DSQ stored as "18.0 DSQ" so the sheet flags the penalty.
# R1 R2 R3 R4 R5 R6 R7  rank  nett
ROWS = {
    "1571": {"races": [2, 4, 1, 12, 2, 6, 4], "rank": 1, "nett": 31.0, "r6": "6.0"},
    "766": {"races": [1, 6, 6, 4, 1, 9, 8], "rank": 2, "nett": 35.0, "r6": "9.0"},
    "774": {"races": [6, 9, 5, 9, 5, 3, 3], "rank": 3, "nett": 40.0, "r6": "3.0"},
    "1175": {"races": [7, 8, 10, 5, 7, 4, 1], "rank": 4, "nett": 42.0, "r6": "4.0"},
    "173": {"races": [5, 10, 7, 7, 4, 2, 7], "rank": 5, "nett": 42.0, "r6": "2.0"},
    "768": {"races": [4, 2, 9, 2, 6, 18, 2], "rank": 6, "nett": 43.0, "r6": "18.0 DSQ", "r6_dsq": True},
    "1169": {"races": [8, 11, 2, 3, 10, 1, 10], "rank": 7, "nett": 45.0, "r6": "1.0"},
    "1277": {"races": [12, 1, 8, 1, 9, 8, 11], "rank": 8, "nett": 50.0, "r6": "8.0"},
    "1116": {"races": [3, 7, 11, 11, 8, 5, 6], "rank": 9, "nett": 51.0, "r6": "5.0"},
    "1167": {"races": [9, 3, 4, 10, 11, 18, 5], "rank": 10, "nett": 60.0, "r6": "18.0 DSQ", "r6_dsq": True},
    "763": {"races": [11, 5, 3, 8, 3, 18, 13], "rank": 11, "nett": 61.0, "r6": "18.0 DSQ", "r6_dsq": True},
    "185": {"races": [10, 17, 15, 6, 14, 7, 12], "rank": 12, "nett": 81.0, "r6": "7.0"},
    "1139": {"races": [16, 12, 12, 16, 13, 13, 9], "rank": 13, "nett": 91.0, "r6": "13.0"},
    "771": {"races": [14, 16, 13, 15, 12, 11, 14], "rank": 14, "nett": 95.0, "r6": "11.0"},
    "1237": {"races": [15, 15, 14, 13, 16, 10, 15], "rank": 15, "nett": 98.0, "r6": "10.0"},
    "1239": {"races": [13, 13, 16, 14, 15, 12, 16], "rank": 16, "nett": 99.0, "r6": "12.0"},
    "1138": {"races": [17, 14, 17, 17, 17, 14, 17], "rank": 17, "nett": 113.0, "r6": "14.0"},
}

# Revised Race 6 places (PDF). DSQ boats scored 18, not a finish place.
R6_PLACE = {
    "1169": 1,
    "173": 2,
    "774": 3,
    "1175": 4,
    "1116": 5,
    "1571": 6,
    "185": 7,
    "1277": 8,
    "766": 9,
    "1237": 10,
    "771": 11,
    "1239": 12,
    "1139": 13,
    "1138": 14,
}
R6_DSQ = ("768", "1167", "763")

R7_PLACE = {
    "1175": 1,
    "768": 2,
    "774": 3,
    "1571": 4,
    "1167": 5,
    "1116": 6,
    "173": 7,
    "766": 8,
    "1139": 9,
    "1169": 10,
    "1277": 11,
    "185": 12,
    "763": 13,
    "771": 14,
    "1237": 15,
    "1239": 16,
    "1138": 17,
}


def _num(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip().strip("()")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _has_dsq(val) -> bool:
    return bool(re.search(r"\bDSQ\b", str(val or ""), re.I))


def _scores_dict(raw) -> dict:
    scores = raw or {}
    if isinstance(scores, str):
        scores = json.loads(scores) if scores.strip() else {}
    if not isinstance(scores, dict):
        scores = {}
    return dict(scores)


def _cell(pts: float, dsq: bool = False) -> str:
    if dsq:
        return f"{pts:.1f} DSQ"
    if pts == int(pts):
        return f"{pts:.1f}"
    return str(pts)


def _want_scores(spec: dict) -> dict:
    races = spec["races"]
    out = {}
    for i, pts in enumerate(races, start=1):
        dsq = i == 6 and spec.get("r6_dsq")
        out[f"R{i}"] = _cell(float(pts), dsq=bool(dsq))
    return out


def checksum_rows(rows) -> list[str]:
    fails: list[str] = []
    seen = {str(r["sail_number"]) for r in rows}
    if seen != set(ROWS):
        fails.append(f"sail set mismatch db={sorted(seen)} pdf={sorted(ROWS)}")
    for r in rows:
        sail = str(r["sail_number"])
        spec = ROWS.get(sail)
        if not spec:
            fails.append(f"{sail} unexpected sail")
            continue
        scores = _scores_dict(r["race_scores"])
        want = _want_scores(spec)
        for i in range(1, 8):
            key = f"R{i}"
            got_n = _num(scores.get(key))
            want_n = _num(want[key])
            if got_n != want_n:
                fails.append(f"{sail} {key} want {want_n} got {scores.get(key)!r}")
            if i == 6:
                if spec.get("r6_dsq") and not _has_dsq(scores.get(key)):
                    fails.append(f"{sail} R6 want DSQ got {scores.get(key)!r}")
                if not spec.get("r6_dsq") and _has_dsq(scores.get(key)):
                    fails.append(f"{sail} R6 unexpected DSQ {scores.get(key)!r}")
        if int(r["rank"] or 0) != spec["rank"]:
            fails.append(f"{sail} rank want {spec['rank']} got {r['rank']}")
        if abs(float(r["nett_points_raw"]) - spec["nett"]) > 0.01:
            fails.append(f"{sail} nett want {spec['nett']} got {r['nett_points_raw']}")
        if abs(float(r["total_points_raw"]) - spec["nett"]) > 0.01:
            fails.append(f"{sail} total want {spec['nett']} got {r['total_points_raw']}")
        if int(r.get("races_sailed") or 0) != 7:
            fails.append(f"{sail} races_sailed want 7 got {r.get('races_sailed')}")
        sum_r = sum(spec["races"])
        if abs(sum_r - spec["nett"]) > 0.01:
            fails.append(f"{sail} PDF races sum {sum_r} != nett {spec['nett']}")
    # Race 6 / 7 place order (finishers only for R6; DSQ boats excluded from place list)
    r6_order = []
    for r in rows:
        sail = str(r["sail_number"])
        scores = _scores_dict(r["race_scores"])
        if sail in R6_DSQ:
            if not _has_dsq(scores.get("R6")) or _num(scores.get("R6")) != DSQ_PTS:
                fails.append(f"{sail} R6 DSQ checksum failed {scores.get('R6')!r}")
            continue
        r6_order.append(( _num(scores.get("R6")), sail))
    r6_order.sort()
    got_r6 = [s for _, s in r6_order]
    want_r6 = [s for s, _ in sorted(R6_PLACE.items(), key=lambda kv: kv[1])]
    if got_r6 != want_r6:
        fails.append(f"R6 place order want {want_r6} got {got_r6}")
    r7_order = sorted(
        ((_num(_scores_dict(r["race_scores"]).get("R7")), str(r["sail_number"])) for r in rows),
        key=lambda t: (t[0] is None, t[0], t[1]),
    )
    got_r7 = [s for _, s in r7_order]
    want_r7 = [s for s, _ in sorted(R7_PLACE.items(), key=lambda kv: kv[1])]
    if got_r7 != want_r7:
        fails.append(f"R7 place order want {want_r7} got {got_r7}")
    return fails


def apply(cur, rows) -> None:
    if len(rows) != N_ENTRIES:
        raise SystemExit(f"expected {N_ENTRIES} result rows, got {len(rows)}")
    missing = [s for s in ROWS if s not in {str(r["sail_number"]) for r in rows}]
    if missing:
        raise SystemExit(f"sail numbers not in results: {missing}")
    for r in rows:
        sail = str(r["sail_number"])
        spec = ROWS[sail]
        scores = _scores_dict(r["race_scores"])
        scores.update(_want_scores(spec))
        # Drop stale race keys beyond R7 if any
        for k in list(scores):
            m = re.fullmatch(r"R(\d+)", str(k))
            if m and int(m.group(1)) > 7:
                scores.pop(k)
        cur.execute(
            """
            UPDATE results
            SET race_scores = %s,
                races_sailed = 7,
                total_points_raw = %s,
                nett_points_raw = %s,
                rank = %s,
                as_at_time = %s
            WHERE result_id = %s
            """,
            (
                json.dumps(scores),
                spec["nett"],
                spec["nett"],
                spec["rank"],
                AS_AT,
                r["result_id"],
            ),
        )
    cur.execute(
        """
        UPDATE regatta_blocks
        SET races_sailed = 7, discard_count = 0
        WHERE regatta_id = %s
        """,
        (REGATTA,),
    )
    cur.execute(
        """
        UPDATE regattas
        SET result_status = 'Provisional', as_at_time = %s
        WHERE regatta_id = %s
        """,
        (AS_AT, REGATTA),
    )


def fetch(cur):
    cur.execute(
        """
        SELECT result_id, sail_number, club_raw, race_scores,
               total_points_raw, nett_points_raw, rank, races_sailed
        FROM results
        WHERE regatta_id=%s
        ORDER BY rank, sail_number
        """,
        (REGATTA,),
    )
    return cur.fetchall()


def report(rows, fails, wrote: bool) -> dict:
    out_rows = []
    for r in rows:
        sail = str(r["sail_number"])
        scores = _scores_dict(r["race_scores"])
        out_rows.append(
            {
                "rank": r["rank"],
                "sail": sail,
                "club": r["club_raw"],
                **{f"R{i}": scores.get(f"R{i}") for i in range(1, 8)},
                "nett": float(r["nett_points_raw"]) if r["nett_points_raw"] is not None else None,
            }
        )
    return {
        "ok": not fails,
        "wrote": wrote,
        "regatta_id": REGATTA,
        "source": "Sailwave PDF Overall after 7 races _updated. Provisional. Discards 0. Appendix A.",
        "as_at": AS_AT.isoformat(),
        "status_line": "Results are Provisional as at 29 August 2026 at 06:27",
        "races_sailed": 7,
        "discard_count": 0,
        "entries": N_ENTRIES,
        "r6_revised": {
            "places": R6_PLACE,
            "dsq_18": list(R6_DSQ),
        },
        "r7": R7_PLACE,
        "fails": fails,
        "rows": out_rows,
    }


def main() -> int:
    db = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DB_URL required")
    check_only = "--check" in sys.argv
    with psycopg2.connect(db) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            rows = fetch(cur)
            if not check_only:
                apply(cur, rows)
        if not check_only:
            conn.commit()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            rows = fetch(cur)
            extra = []
            cur.execute(
                "SELECT races_sailed, discard_count FROM regatta_blocks WHERE regatta_id=%s",
                (REGATTA,),
            )
            blocks = cur.fetchall()
            if not blocks:
                extra.append("no regatta_blocks row")
            for b in blocks:
                if int(b["races_sailed"] or 0) != 7:
                    extra.append(f"block races_sailed want 7 got {b['races_sailed']}")
                if int(b["discard_count"] or 0) != 0:
                    extra.append(f"block discard_count want 0 got {b['discard_count']}")
            cur.execute(
                "SELECT result_status, as_at_time FROM regattas WHERE regatta_id=%s",
                (REGATTA,),
            )
            reg = cur.fetchone()
            if not reg:
                extra.append("no regattas row")
            else:
                if str(reg["result_status"] or "") != "Provisional":
                    extra.append(f"result_status want Provisional got {reg['result_status']}")
                got_as = reg["as_at_time"]
                if got_as is None:
                    extra.append("as_at_time missing")
                else:
                    if got_as.tzinfo is None:
                        got_as = got_as.replace(tzinfo=SAST)
                    if got_as.astimezone(SAST).replace(second=0, microsecond=0) != AS_AT:
                        extra.append(f"as_at_time want {AS_AT.isoformat()} got {got_as.isoformat()}")

    fails = checksum_rows(rows) + extra
    print(json.dumps(report(rows, fails, wrote=not check_only), indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
