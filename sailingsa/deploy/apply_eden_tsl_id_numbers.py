#!/usr/bin/env python3
"""Store official Eden TSL ID numbers and derive DOB/age. Existing SAS IDs only.

ID numbers from the S.A. Sailing Eden District team sheet (17/18 October 2026).
Age is as at the event date 17 October 2026. YYMMDD from the SA ID prefix.

  export DB_URL=...
  python3 sailingsa/deploy/apply_eden_tsl_id_numbers.py --dry-run
  python3 sailingsa/deploy/apply_eden_tsl_id_numbers.py
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

EVENT_DATE = date(2026, 10, 17)

# First 13 digits from the official sheet (SAS numbers already verified in DB).
EDEN = (
    ("15711", "1005145401087"),
    ("13488", "0907175454085"),
    ("27609", "1006130657089"),
    ("27610", "1310035960908"),
    ("23531", "1201255354089"),
    ("28588", "0805235269083"),
)


def get_db_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def dob_from_id(id_number: str) -> date:
    yy = int(id_number[0:2])
    mm = int(id_number[2:4])
    dd = int(id_number[4:6])
    year = 2000 + yy if yy <= 30 else 1900 + yy
    return date(year, mm, dd)


def age_on(dob: date, on: date) -> int:
    years = on.year - dob.year
    if (on.month, on.day) < (dob.month, dob.day):
        years -= 1
    return years


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if psycopg2 is None:
        print("ERROR: psycopg2 required", file=sys.stderr)
        return 2

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            ALTER TABLE public.sas_id_personal
            ADD COLUMN IF NOT EXISTS id_number character varying(13)
            """
        )
        for sas_id, id_number in EDEN:
            dob = dob_from_id(id_number)
            age = age_on(dob, EVENT_DATE)
            cur.execute(
                """
                SELECT sa_sailing_id, first_name, last_name, date_of_birth, year_of_birth, age, id_number
                FROM public.sas_id_personal
                WHERE sa_sailing_id::text = %s
                LIMIT 1
                """,
                (sas_id,),
            )
            row = cur.fetchone()
            if not row:
                print(f"SKIP {sas_id} — not in sas_id_personal (not invented)")
                continue
            print(
                f"{sas_id} {row['first_name']} {row['last_name']} "
                f"id={id_number} dob={dob.isoformat()} age={age}"
            )
            if args.dry_run:
                continue
            cur.execute(
                """
                UPDATE public.sas_id_personal
                SET id_number = %s,
                    date_of_birth = %s,
                    year_of_birth = %s,
                    age = %s
                WHERE sa_sailing_id::text = %s
                """,
                (id_number, dob, dob.year, age, sas_id),
            )
        if args.dry_run:
            conn.rollback()
            print("dry-run: no writes")
            return 0
        conn.commit()
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
