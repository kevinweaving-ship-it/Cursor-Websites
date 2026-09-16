#!/usr/bin/env python3
"""Persist 2022 DF95 Nationals host = PERBC; infer host by club_id not raw label."""
from pathlib import Path
import shutil
import time
import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
API = Path("/var/www/sailingsa/api/api.py")
MARK = "GOLD_INFER_HOST_BY_CLUB_ID_v1"

INFER_OLD = '''                SELECT COALESCE(NULLIF(btrim(r.club_raw), ''), NULLIF(btrim(c.club_abbrev), ''), '(blank)') AS club,
                       MAX(c.club_id) AS club_id,
                       MAX(NULLIF(btrim(c.club_abbrev), '')) AS abbrev,
                       MAX(NULLIF(btrim(c.club_fullname), '')) AS fullname,
                       COUNT(*) AS n
                FROM results r
                LEFT JOIN clubs c ON c.club_id = r.club_id
                WHERE r.regatta_id = %s
                GROUP BY 1
                ORDER BY n DESC
'''

INFER_NEW = '''                SELECT COALESCE(c.club_id::text, NULLIF(btrim(r.club_raw), ''), '(blank)') AS club,
                       MAX(c.club_id) AS club_id,
                       MAX(NULLIF(btrim(c.club_abbrev), '')) AS abbrev,
                       MAX(NULLIF(btrim(c.club_fullname), '')) AS fullname,
                       COUNT(*) AS n
                FROM results r
                LEFT JOIN clubs c ON c.club_id = r.club_id
                WHERE r.regatta_id = %s
                GROUP BY COALESCE(c.club_id::text, NULLIF(btrim(r.club_raw), ''), '(blank)')
                ORDER BY n DESC
'''


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE regattas
        SET host_club_id = 138,
            host_club_code = 'PERBC',
            host_club_name = 'Port Elizabeth Radio Boat Club'
        WHERE regatta_id = '2022-09-11-df95-nationals'
          AND host_club_id IS NULL
        """
    )
    print("DF95_HOST", cur.rowcount)
    conn.commit()
    cur.close()
    conn.close()

    api = API.read_text()
    if MARK in api:
        print("INFER_ALREADY")
        return
    if INFER_OLD not in api:
        raise SystemExit("INFER_SQL_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.gold_infer_club.{ts}"))
    api = api.replace(INFER_OLD, INFER_NEW, 1)
    api = api.replace(
        "def _gold_infer_event_host(regatta_id: str, event_name: str = \"\"):",
        "def _gold_infer_event_host(regatta_id: str, event_name: str = \"\"):\n    # "
        + MARK,
        1,
    )
    API.write_text(api)
    print("INFER_OK", MARK)


if __name__ == "__main__":
    main()
