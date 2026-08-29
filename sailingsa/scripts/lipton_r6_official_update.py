#!/usr/bin/env python3
"""Write official Lipton 2026 Race 6 into results. Checksum vs PDF. Not GPS. Not Nett invention.

Source: Sailwave PDFs Race 06 + Overall after 6 races (provisional, discards 0).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import RealDictCursor

REGATTA = "2026-08-29-lipton-challenge-cup"
SAST = ZoneInfo("Africa/Johannesburg")

# Official Race 6 place by sail_number (PDF Rank / Place).
R6 = {
    "1169": 1,  # FBYC
    "173": 2,  # RCYC Academy
    "774": 3,  # UCTYC
    "1175": 4,  # SBYC
    "1167": 5,  # LDYC
    "1116": 6,  # PYC
    "763": 7,  # KYC
    "768": 8,  # RNYC
    "1571": 9,  # HYC
    "185": 10,  # GLYC
    "1277": 11,  # WBYC
    "766": 12,  # RCYC
    "1237": 13,  # LYC
    "771": 14,  # IZI
    "1239": 15,  # TSC
    "1139": 16,  # BYC
    "1138": 17,  # WYAC
}

# Overall PDF order after 6 races (Appendix A, 0 discards).
OVERALL = [
    ("766", 1, 30.0),
    ("1571", 2, 30.0),
    ("768", 3, 31.0),
    ("1169", 4, 35.0),
    ("173", 5, 35.0),
    ("763", 6, 37.0),
    ("774", 7, 37.0),
    ("1175", 8, 41.0),
    ("1277", 9, 42.0),
    ("1167", 10, 42.0),
    ("1116", 11, 46.0),
    ("185", 12, 72.0),
    ("771", 13, 84.0),
    ("1139", 14, 85.0),
    ("1237", 15, 86.0),
    ("1239", 16, 86.0),
    ("1138", 17, 99.0),
]


def _num(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip().strip("()")
    try:
        return float(s)
    except ValueError:
        return None


def main() -> int:
    db = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DB_URL required")
    now = datetime.now(SAST)
    overall_by_sail = {s: (rank, nett) for s, rank, nett in OVERALL}
    with psycopg2.connect(db) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT result_id, sail_number, club_raw, race_scores, total_points_raw, nett_points_raw, rank, races_sailed "
                "FROM results WHERE regatta_id=%s ORDER BY rank",
                (REGATTA,),
            )
            rows = cur.fetchall()
            if len(rows) != 17:
                raise SystemExit(f"expected 17 result rows, got {len(rows)}")
            missing = [s for s in R6 if s not in {str(r["sail_number"]) for r in rows}]
            if missing:
                raise SystemExit(f"sail numbers not in results: {missing}")

            r1_r5_ok = True
            for r in rows:
                sail = str(r["sail_number"])
                scores = r["race_scores"] or {}
                if isinstance(scores, str):
                    scores = json.loads(scores)
                want = R6[sail]
                scores["R6"] = str(want)
                total = 0.0
                for i in range(1, 7):
                    n = _num(scores.get(f"R{i}"))
                    if n is None:
                        raise SystemExit(f"{sail} missing R{i}")
                    total += n
                rank, nett = overall_by_sail[sail]
                if abs(total - nett) > 0.01:
                    r1_r5_ok = False
                cur.execute(
                    """
                    UPDATE results
                    SET race_scores = %s,
                        races_sailed = 6,
                        total_points_raw = %s,
                        nett_points_raw = %s,
                        rank = %s,
                        as_at_time = %s
                    WHERE result_id = %s
                    """,
                    (json.dumps(scores), total, total, rank, now, r["result_id"]),
                )
            cur.execute(
                """
                UPDATE regatta_blocks
                SET races_sailed = 6, discard_count = 0
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
                (now, REGATTA),
            )
        conn.commit()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT sail_number, club_raw, race_scores, total_points_raw, nett_points_raw, rank "
                "FROM results WHERE regatta_id=%s ORDER BY rank",
                (REGATTA,),
            )
            out = cur.fetchall()

    fails = []
    for r in out:
        sail = str(r["sail_number"])
        scores = r["race_scores"] or {}
        if isinstance(scores, str):
            scores = json.loads(scores)
        want_r6 = R6[sail]
        got_r6 = _num(scores.get("R6"))
        rank, nett = overall_by_sail[sail]
        if got_r6 != want_r6:
            fails.append(f"{sail} R6 want {want_r6} got {got_r6}")
        if int(r["rank"] or 0) != rank:
            fails.append(f"{sail} rank want {rank} got {r['rank']}")
        if abs(float(r["nett_points_raw"]) - nett) > 0.01:
            fails.append(f"{sail} nett want {nett} got {r['nett_points_raw']}")
        if abs(float(r["total_points_raw"]) - nett) > 0.01:
            fails.append(f"{sail} total want {nett} got {r['total_points_raw']}")

    report = {
        "ok": not fails,
        "regatta_id": REGATTA,
        "source": "Sailwave PDF Race 06 + Overall after 6 races. Provisional. Discards 0.",
        "as_at": now.isoformat(),
        "r1_r5_plus_r6_match_overall_nett": r1_r5_ok,
        "fails": fails,
        "rows": [
            {
                "rank": r["rank"],
                "sail": str(r["sail_number"]),
                "club": r["club_raw"],
                "R6": (r["race_scores"] or {}).get("R6")
                if isinstance(r["race_scores"], dict)
                else json.loads(r["race_scores"]).get("R6"),
                "nett": float(r["nett_points_raw"]),
            }
            for r in out
        ],
    }
    print(json.dumps(report, indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
