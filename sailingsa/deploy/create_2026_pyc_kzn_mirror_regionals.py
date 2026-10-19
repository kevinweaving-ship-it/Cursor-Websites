#!/usr/bin/env python3
"""Create Event URL + Low Point results for 2026 KZN Mirror Regionals (PYC).

Gold template: /regatta/2026-09-24-ayc-505-nationals
Same columns; R1–R8 instead of R1–R12.

Discard rule (Appendix A / Low Point):
  total = sum of ALL race points including the discarded race
  nett  = total − discarded race points
  Discards: 1 → exactly one parenthesised score per row
"""
from __future__ import annotations

import json
import os
import re
import sys

import psycopg2
import psycopg2.extras

REGATTA_ID = "2026-05-16-pyc-kzn-mirror-regionals"
BLOCK_ID = f"{REGATTA_ID}:mirror"
EVENT_NAME = "KZN Mirror Regional Championships"
SAS_SOURCE_EVENT_ID = "344422"
CLASS_NAME = "Mirror"  # class = fleet; header left = Mirror class logo (never KZN-Mirror-ILCA Event Logo)
# Single fleet → parent Event URL only. Do not create /class-mirror or hyphen-tail child URLs.
# No Marine Megastore / Facebook live-video card (that is Lipton + Cape Classic only).
# Print/share PDF is parent results.pdf only — delete class-*.pdf leftovers; never keep replaced ILCA Event Logo.

AS_AT = "2026-05-17 17:05:00+02"
START = "2026-05-16"
END = "2026-05-17"
YEAR = 2026
SAILED = 8
DISCARDS = 1
TO_COUNT = 7
ENTRIES = 8
PENALTY = ENTRIES + 1  # 9.0


def parse_pts(cell: str) -> float:
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", cell)
    if not m:
        raise ValueError(f"no points in {cell!r}")
    return float(m.group(1))


def checksum(scores: dict[str, str]) -> tuple[float, float]:
    total = 0.0
    discarded = 0.0
    n_disc = 0
    for v in scores.values():
        pts = parse_pts(v)
        total += pts
        if v.startswith("(") and v.endswith(")"):
            discarded += pts
            n_disc += 1
    if n_disc != DISCARDS:
        raise SystemExit(f"discard count {n_disc} != {DISCARDS}: {scores}")
    nett = total - discarded
    return total, nett


# Sheet names kept only when SAS ID is unmatched. Matched rows use SAS spelling.
ROWS = [
    {
        "rank": 1,
        "ordinal": "1st",
        "sail": "60522",
        "club_raw": "HMYC",
        "club_abbrev": "HMYC",
        "helm": "Mark Flack",
        "helm_id": 11042,
        "crew": "Ila Gebuza",
        "crew_id": None,
        "scores": {
            "R1": "1.0",
            "R2": "1.0",
            "R3": "1.0",
            "R4": "1.0",
            "R5": "1.0",
            "R6": "3.0",
            "R7": "(5.0)",
            "R8": "1.0",
        },
        "sheet_total": 14.0,
        "sheet_nett": 9.0,
    },
    {
        "rank": 2,
        "ordinal": "2nd",
        "sail": "70207",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Gust Funke",  # sheet Gusi → SAS Gust
        "helm_id": 21715,
        "crew": "Kai Funke",
        "crew_id": 22836,
        "scores": {
            "R1": "2.0",
            "R2": "3.0",
            "R3": "(9.0 DNS)",
            "R4": "2.0",
            "R5": "2.0",
            "R6": "2.0",
            "R7": "3.0",
            "R8": "3.0",
        },
        "sheet_total": 26.0,
        "sheet_nett": 17.0,
    },
    {
        "rank": 3,
        "ordinal": "3rd",
        "sail": "50637",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Jerome Vermaak",
        "helm_id": 15495,
        "crew": "John-Alan Harding",  # sheet John Alan → SAS John-Alan
        "crew_id": 16401,
        "scores": {
            "R1": "4.0",
            "R2": "2.0",
            "R3": "2.0",
            "R4": "(9.0 DNC)",
            "R5": "9.0 DNC",
            "R6": "5.0",
            "R7": "2.0",
            "R8": "2.0",
        },
        "sheet_total": 35.0,
        "sheet_nett": 26.0,
    },
    {
        "rank": 4,
        "ordinal": "4th",
        "sail": "70410",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Colin Becker",
        "helm_id": 9668,
        "crew": "Cali Becker",
        "crew_id": 29495,
        "scores": {
            "R1": "(9.0 DNS)",
            "R2": "9.0 DNC",
            "R3": "9.0 DNC",
            "R4": "3.0",
            "R5": "3.0",
            "R6": "1.0",
            "R7": "1.0",
            "R8": "9.0 DNF",
        },
        "sheet_total": 44.0,
        "sheet_nett": 35.0,
    },
    {
        "rank": 5,
        "ordinal": "5th",
        "sail": "66853",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Philasande Zungu",
        "helm_id": 13991,
        "crew": "Kwanele Ziqubu",
        "crew_id": 28840,
        "scores": {
            "R1": "(9.0 DNS)",
            "R2": "9.0 DNC",
            "R3": "9.0 DNC",
            "R4": "9.0 DNS",
            "R5": "5.0",
            "R6": "6.0",
            "R7": "4.0",
            "R8": "4.0",
        },
        "sheet_total": 55.0,
        "sheet_nett": 46.0,
    },
    {
        "rank": 6,
        "ordinal": "6th",
        "sail": "50558",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Nothando Phuling",
        "helm_id": None,
        "crew": "Elethu Keke",
        "crew_id": None,
        "scores": {
            "R1": "(9.0 DNS)",
            "R2": "9.0 DNC",
            "R3": "9.0 DNC",
            "R4": "9.0 DNS",
            "R5": "4.0",
            "R6": "4.0",
            "R7": "6.0",
            "R8": "5.0",
        },
        "sheet_total": 55.0,
        "sheet_nett": 46.0,
    },
    {
        "rank": 7,
        "ordinal": "7th",
        "sail": "70245",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Sakhile Mthombeni",
        "helm_id": 15093,
        "crew": "Sabelo Mpungose",  # sheet Mpingose → SAS Mpungose
        "crew_id": 21107,
        "scores": {
            "R1": "3.0",
            "R2": "4.0",
            "R3": "(9.0 DNF)",
            "R4": "9.0 DNC",
            "R5": "9.0 DNC",
            "R6": "9.0 DNC",
            "R7": "9.0 DNC",
            "R8": "9.0 DNC",
        },
        "sheet_total": 61.0,
        "sheet_nett": 52.0,
    },
    {
        "rank": 8,
        "ordinal": "8th",
        "sail": "50552",
        "club_raw": "PYC",
        "club_abbrev": "PYC",
        "helm": "Thembeka Dlamini",
        "helm_id": 21853,
        "crew": "Losikona Linda",
        "crew_id": None,
        "scores": {
            "R1": "(9.0 DNS)",
            "R2": "9.0 DNC",
            "R3": "9.0 DNC",
            "R4": "9.0 DNS",
            "R5": "6.0",
            "R6": "7.0",
            "R7": "7.0",
            "R8": "6.0",
        },
        "sheet_total": 62.0,
        "sheet_nett": 53.0,
    },
]


def sas_display_name(cur, sa_id: int | None, fallback: str) -> str:
    if sa_id is None:
        return fallback
    cur.execute(
        """
        SELECT TRIM(BOTH FROM regexp_replace(
                 TRIM(COALESCE(first_name,'')) || ' ' || TRIM(COALESCE(last_name,'')),
                 '[\\u200b\\u200c\\u200d\\ufeff]', '', 'g'))
        FROM sas_id_personal
        WHERE sa_sailing_id::text = %s
        LIMIT 1
        """,
        (str(sa_id),),
    )
    row = cur.fetchone()
    if not row or not (row[0] or "").strip():
        return fallback
    return re.sub(r"\s+", " ", row[0]).strip()


def main() -> int:
    db = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not db:
        print("DB_URL required", file=sys.stderr)
        return 2

    for row in ROWS:
        total, nett = checksum(row["scores"])
        if abs(total - row["sheet_total"]) > 0.01 or abs(nett - row["sheet_nett"]) > 0.01:
            raise SystemExit(
                f"checksum fail rank {row['rank']}: calc {total}/{nett} sheet {row['sheet_total']}/{row['sheet_nett']}"
            )
        for v in row["scores"].values():
            if re.search(r"\b(DNC|DNS|DNF)\b", v) and parse_pts(v) != float(PENALTY):
                raise SystemExit(f"penalty != entries+1 ({PENALTY}) in {v}")

    conn = psycopg2.connect(db)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT class_id, class_name, is_race_class FROM classes WHERE LOWER(TRIM(class_name)) = 'mirror'"
        )
        klass = cur.fetchone()
        if not klass:
            raise SystemExit("Mirror class missing")
        class_id, class_canonical, is_race = klass
        if is_race is False:
            raise SystemExit("Mirror is_race_class is false")

        cur.execute(
            "SELECT club_id, club_abbrev, club_fullname FROM clubs WHERE club_abbrev IN ('PYC','HMYC')"
        )
        clubs = {r[1]: r for r in cur.fetchall()}
        if "PYC" not in clubs or "HMYC" not in clubs:
            raise SystemExit(f"club map incomplete: {clubs}")
        pyc_id, _, pyc_full = clubs["PYC"]

        cur.execute("SELECT regatta_id FROM regattas WHERE regatta_id = %s", (REGATTA_ID,))
        if cur.fetchone():
            raise SystemExit(f"{REGATTA_ID} already exists")

        cur.execute(
            """
            INSERT INTO regattas (
                regatta_id, event_name, year, start_date, end_date,
                result_status, as_at_time, host_club_id, host_club_code, host_club_name,
                province_name, scoring_system, import_status, origin
            ) VALUES (
                %s, %s, %s, %s, %s,
                'Final', %s, %s, 'PYC', %s,
                'KZN', 'Appendix A', 'ok', 'ops_ingest'
            )
            """,
            (REGATTA_ID, EVENT_NAME, YEAR, START, END, AS_AT, pyc_id, pyc_full),
        )

        cur.execute(
            """
            INSERT INTO regatta_blocks (
                block_id, regatta_id, class_original, class_canonical, fleet_label,
                races_sailed, discard_count, to_count, scoring_system, class_id
            ) VALUES (
                %s, %s, %s, %s, '',
                %s, %s, %s, 'Appendix A', %s
            )
            """,
            (BLOCK_ID, REGATTA_ID, CLASS_NAME, class_canonical, SAILED, DISCARDS, TO_COUNT, class_id),
        )

        for row in ROWS:
            total, nett = checksum(row["scores"])
            club_id = clubs[row["club_abbrev"]][0]
            helm = sas_display_name(cur, row["helm_id"], row["helm"])
            crew = sas_display_name(cur, row["crew_id"], row["crew"])
            cur.execute(
                """
                INSERT INTO results (
                    regatta_id, block_id, rank, rank_ordinal, pos, fleet_label,
                    class_original, class_canonical, class_id,
                    sail_number, club_raw, club_id,
                    helm_name, helm_sa_sailing_id, crew_name, crew_sa_sailing_id,
                    races_sailed, discard_count, race_scores,
                    total_points_raw, nett_points_raw,
                    raced, as_at_time, result_status,
                    row_validation_status, manually_parsed
                ) VALUES (
                    %s, %s, %s, %s, %s, '',
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s::jsonb,
                    %s, %s,
                    TRUE, %s, 'Final',
                    'validated', FALSE
                )
                """,
                (
                    REGATTA_ID,
                    BLOCK_ID,
                    row["rank"],
                    row["ordinal"],
                    row["rank"],
                    CLASS_NAME,
                    class_canonical,
                    class_id,
                    row["sail"],
                    row["club_raw"],
                    club_id,
                    helm,
                    row["helm_id"],
                    crew,
                    row["crew_id"],
                    SAILED,
                    DISCARDS,
                    json.dumps(row["scores"]),
                    total,
                    nett,
                    AS_AT,
                ),
            )
            print(f"rank {row['rank']} {helm} total={total:.1f} nett={nett:.1f} discard={total-nett:.1f}")

        cur.execute(
            """
            UPDATE events
            SET regatta_id = %s
            WHERE source_event_id = %s AND (regatta_id IS NULL OR regatta_id = '')
            """,
            (REGATTA_ID, SAS_SOURCE_EVENT_ID),
        )
        if cur.rowcount != 1:
            raise SystemExit(f"events link rowcount={cur.rowcount} expected 1")

        conn.commit()
        print(f"OK {REGATTA_ID} linked SAS {SAS_SOURCE_EVENT_ID}")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
