#!/usr/bin/env python3
"""Grant Alison Grunewald #28280 HMYC club manager (Cape Classic club_admin pattern)."""

from __future__ import annotations

import os
import sys

SQL = """
UPDATE public.sas_id_personal
   SET primary_club = 'HMYC',
       club_1 = 'HMYC',
       club_manager = 'Club Manager',
       club_roles = 'Club Manager',
       c_role_1 = 'Club Manager'
 WHERE sa_sailing_id::text = '28280';

UPDATE public.user_accounts
   SET role = 'club_manager',
       admin_club_id = 98,
       full_name = COALESCE(NULLIF(TRIM(full_name), ''), 'Alison Grunewald'),
       updated_at = NOW()
 WHERE sas_id = '28280'
   AND is_active = TRUE;
"""


def main() -> int:
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not url:
        sys.stderr.write("Set DATABASE_URL (live SSH).\n")
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    try:
        cur = conn.cursor()
        cur.execute(SQL)
        conn.commit()
        print("ok alison 28280 HMYC club_manager")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
