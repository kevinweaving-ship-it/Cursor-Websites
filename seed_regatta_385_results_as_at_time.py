#!/usr/bin/env python3
"""
Seed snapshot time into results (and regattas) for regatta 385 per Result rule.
- results.as_at_time: primary source for status line (standalone and results pages).
- Format: TIMESTAMP WITH TIME ZONE (e.g. 2026-02-15 14:20:00+02) per DATA_FORMAT_SPECIFICATIONS.
- Display: "Results are Provisional as at 15 February 2026 at 14:20" per RESULTS_HTML_STATUS_LINE_RULE.
Run locally then on LIVE after deploy (see sailingsa/deploy/SSH_LIVE.md).
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DB_URL", os.getenv("DATABASE_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master"))
REGATTA_ID = "385-2026-hyc-cape-classic"
# Per sheet: "Results are provisional as of 14:20 on February 15, 2026" → store as timestamptz
AS_AT_TIME = "2026-02-15 14:20:00+02"
RESULT_STATUS = "Provisional"


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1) Seed results table (primary source for status-line date)
        cur.execute(
            """
            UPDATE results
            SET as_at_time = %s::timestamptz
            WHERE regatta_id = %s
            """,
            (AS_AT_TIME, REGATTA_ID),
        )
        results_updated = cur.rowcount
        # 2) Sync regattas for fallback / legacy paths
        cur.execute(
            """
            UPDATE regattas
            SET result_status = %s, as_at_time = %s::timestamptz
            WHERE regatta_id = %s
            """,
            (RESULT_STATUS, AS_AT_TIME, REGATTA_ID),
        )
        regattas_updated = cur.rowcount
        conn.commit()

        cur.execute(
            "SELECT as_at_time FROM results WHERE regatta_id = %s AND as_at_time IS NOT NULL LIMIT 1",
            (REGATTA_ID,),
        )
        res_row = cur.fetchone()
        cur.execute(
            "SELECT regatta_id, result_status, as_at_time FROM regattas WHERE regatta_id = %s",
            (REGATTA_ID,),
        )
        reg_row = cur.fetchone()
        print("Seeded snapshot time (Result rule format):")
        print(f"  results rows updated: {results_updated}")
        print(f"  regattas rows updated: {regattas_updated}")
        if res_row:
            print(f"  results.as_at_time sample: {res_row['as_at_time']!r}")
        if reg_row:
            print(f"  regattas: result_status={reg_row['result_status']!r}, as_at_time={reg_row['as_at_time']!r}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
