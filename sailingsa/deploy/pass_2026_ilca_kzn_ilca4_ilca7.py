#!/usr/bin/env python3
"""Pass ILCA 4.7 / 6 / 7 fleets for 2026 ILCA KZN Regionals.

Column order (as sheet): Rank | Sail No | Club | Name | Category | Gender | R1–R6 | Total | Nett
Source: https://cdn.revolutionise.com.au/site/ltjdspwjl1li4gni.pdf
Event page: https://www.laser.org.za/events/364968

Workflow: docs/RESULT_PARSE_ADD.md — shared helpers in result_parse_common.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_2026_ilca_kzn_regionals_stub import (  # noqa: E402
    REGATTA_ID,
    link_event,
    patch_header_icons,
    upsert_regatta,
    _db_url,
)
from result_parse_common import ensure_gender_column, insert_fleet  # noqa: E402

NAME_ALIASES = {
    "connor lowe": "Conor Lowe",
    "anthony mcmillan": "Anthony MacMillan",
    "caitlin macpherson": "Caitlin MacPherson",
    "matthew macpherson": "Matthew MacPherson",
    "penny macpherson": "Penny MacPherson",
    "kees van welie": "Kees van Welie",
    "michaels barrett": "Michael Barrett",
}

# Sheet rows: rank, sail, club, name, category, gender, r1..r6, total, nett
ILCA4 = {
    "class_original": "ILCA 4",
    "class_canonical": "Ilca 4.7",
    "block_slug": "ilca-4-7",
    "entries": 12,
    "discards": 1,
    "races": 6,
    "rows": [
        (1, "191090", "ZVYC", "Joshua Keytel", "Youth", "M", ["1.0", "(3.0)", "1.0", "1.0", "1.0", "1.0"], "8.0", "5.0"),
        (2, "191082", "HYC", "Nathan McCombe", "Youth", "M", ["2.0", "2.0", "(3.0)", "2.0", "3.0", "2.0"], "14.0", "11.0"),
        (3, "191056", "Aeolians", "Maximilian Malan", "Youth", "M", ["3.0", "1.0", "(4.0)", "3.0", "2.0", "3.0"], "16.0", "12.0"),
        (4, "55859", "HYC", "Connor Lowe", "Youth", "M", ["4.0", "(6.0)", "2.0", "4.0", "6.0", "4.0"], "26.0", "20.0"),
        (5, "160125", "ZYC", "Kai Law", "Youth", "M", ["6.0", "4.0", "5.0", "(OCS)", "4.0", "6.0"], "38.0", "25.0"),
        (6, "71", "PYC", "Jerome Vermaak", "Youth", "M", ["5.0", "5.0", "(DNC)", "OCS", "5.0", "5.0"], "46.0", "33.0"),
        (7, "191066", "HMYC", "Caitlin Macpherson", "Youth", "F", ["(DNC)", "DNC", "DNC", "6.0", "7.0", "9.0"], "61.0", "48.0"),
        (8, "205896", "ZYC", "Skyla Gaudin", "Youth", "F", ["(DNC)", "DNC", "DNC", "5.0", "9.0", "10.0"], "63.0", "50.0"),
        (9, "191055", "HMYC", "Matthew Macpherson", "Youth", "M", ["(DNC)", "DNC", "DNC", "7.0", "10.0", "7.0"], "63.0", "50.0"),
        (10, "208178", "PYC", "John-Alan Harding", "Youth", "M", ["(DNC)", "DNC", "DNC", "8.0", "8.0", "8.0"], "63.0", "50.0"),
        (11, "161595", "KSYC", "Shalin Naidoo", "Youth", "M", ["8.0", "7.0", "(DNC)", "DNC", "DNC", "DNC"], "67.0", "54.0"),
        (12, "19106", "ZYC", "Shelby Steenkamp", "Youth", "F", ["7.0", "8.0", "(DNC)", "DNC", "DNC", "DNC"], "67.0", "54.0"),
    ],
}
ILCA7 = {
    "class_original": "ILCA 7",
    "class_canonical": "Ilca 7",
    "block_slug": "ilca-7",
    "entries": 10,
    "discards": 1,
    "races": 6,
    "rows": [
        (1, "124133", "KSYC", "Rudy McNeill", "Senior", "M", ["(1.0)", "1.0", "1.0", "1.0", "1.0", "1.0"], "6.0", "5.0"),
        (2, "208177", "ZVYC", "Alistair Keytel", "Senior", "M", ["(2.0)", "2.0", "2.0", "2.0", "2.0", "2.0"], "12.0", "10.0"),
        (3, "191097", "PYC", "Luke Wagner", "Senior", "M", ["3.0", "3.0", "4.0", "(5.0)", "4.0", "5.0"], "24.0", "19.0"),
        (4, "214132", "PYC", "Campbell Alexander", "Senior", "M", ["4.0", "5.0", "3.0", "(7.0)", "5.0", "3.0"], "27.0", "20.0"),
        (5, "191093", "HMYC", "Anthony McMillan", "Senior", "M", ["5.0", "4.0", "5.0", "(6.0)", "3.0", "6.0"], "29.0", "23.0"),
        (6, "2337", "ESC", "Barry Hundley", "Senior", "M", ["6.0", "(OCS)", "6.0", "4.0", "7.0", "7.0"], "41.0", "30.0"),
        (7, "191033", "ELYC", "Shaun Gradwell", "Senior", "M", ["(DNC)", "DNC", "DNC", "3.0", "6.0", "4.0"], "46.0", "35.0"),
        (8, "TBA", "PYC", "Struan Alexander", "Senior", "M", ["7.0", "6.0", "(DNC)", "8.0", "9.0", "8.0"], "49.0", "38.0"),
        (9, "122771", "BSC", "Ian Campbell", "Senior", "M", ["(DNC)", "7.0", "RET", "9.0", "8.0", "10.0"], "56.0", "45.0"),
        (10, "12277", "BSC", "Stephan Deeke", "Senior", "M", ["(DNC)", "DNC", "DNC", "10.0", "10.0", "9.0"], "62.0", "51.0"),
    ],
}
ILCA6 = {
    "class_original": "ILCA 6",
    "class_canonical": "Ilca 6",
    "block_slug": "ilca-6",
    "entries": 10,
    "discards": 1,
    "races": 6,
    "rows": [
        (1, "188566", "ZVYC", "Blake Madel", "Youth", "M", ["3.0", "1.0", "1.0", "1.0", "(OCS)", "2.0"], "19.0", "8.0"),
        (2, "201753", "RNYC", "Paul Changuion", "Senior", "M", ["1.0", "3.0", "2.0", "2.0", "(OCS)", "4.0"], "23.0", "12.0"),
        (3, "160127", "SYC", "Aydin O'Hara", "Youth", "M", ["2.0", "4.0", "3.0", "(5.0)", "2.0", "3.0"], "19.0", "14.0"),
        (4, "144324", "HMYC", "Noah Clulow", "Youth", "M", ["(RET)", "2.0", "DNC", "7.0", "1.0", "1.0"], "33.0", "22.0"),
        (5, "144153", "RNYC", "Michaels Barrett", "Youth", "F", ["4.0", "(6.0)", "5.0", "4.0", "4.0", "6.0"], "29.0", "23.0"),
        (6, "188079", "HMYC", "Daniela Cantarelli", "Youth", "F", ["5.0", "5.0", "4.0", "6.0", "5.0", "(7.0)"], "32.0", "25.0"),
        (7, "19123", "HMYC", "Penny Macpherson", "Senior", "F", ["(DNC)", "DNC", "DNC", "3.0", "3.0", "5.0"], "44.0", "33.0"),
        (8, "42555", "BSC", "Stephan Deeke", "Senior", "M", ["7.0", "8.0", "6.0", "(DNC)", "DNC", "DNC"], "54.0", "43.0"),
        (9, "191233", "HMYC", "Kees van Welie", "Senior", "M", ["6.0", "7.0", "(DNC)", "DNC", "DNC", "DNC"], "57.0", "46.0"),
        (10, "37181", "BSC", "Mike Tainton", "Senior", "M", ["(DNC)", "DNC", "DNC", "8.0", "6.0", "RET"], "58.0", "47.0"),
    ],
}


def main() -> None:
    patch_header_icons()
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            upsert_regatta(cur)
            n = link_event(cur)
            ensure_gender_column(cur)
            unmatched = []
            for fleet in (ILCA4, ILCA6, ILCA7):
                unmatched += insert_fleet(
                    cur,
                    regatta_id=REGATTA_ID,
                    fleet=fleet,
                    name_aliases=NAME_ALIASES,
                )
        conn.commit()
    finally:
        conn.close()
    print(f"regatta_id={REGATTA_ID}")
    print(f"events_linked={n}")
    print("source_url=https://cdn.revolutionise.com.au/site/ltjdspwjl1li4gni.pdf")
    print("url=https://sailingsa.co.za/regatta/2026-08-10-ilca-kzn-regional-championships")
    print("fleets=Ilca 4.7, Ilca 6, Ilca 7")
    if unmatched:
        print("UNMATCHED sailors (need SA ID / Temp):")
        for u in unmatched:
            print(f"  {u}")
    else:
        print("all helms matched to sas_id_personal")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
