#!/usr/bin/env python3
"""Set host_club_id = HYC for regattas with HYC/Hermanus in event_name but host_club_id IS NULL."""
import os
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT club_id FROM clubs WHERE UPPER(TRIM(club_abbrev)) = 'HYC' LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("HYC club not found")
        return
    hyc_id = row["club_id"]

    cur.execute("""
        SELECT regatta_id, event_name, host_club_id
        FROM regattas
        WHERE host_club_id IS NULL
          AND (UPPER(COALESCE(event_name, '')) LIKE '%HYC%'
               OR UPPER(COALESCE(event_name, '')) LIKE '%HERMANUS%')
    """)
    to_fix = cur.fetchall()
    if not to_fix:
        print("No regattas to fix (all HYC/Hermanus events already have host_club_id)")
        conn.close()
        return

    print(f"Updating host_club_id = {hyc_id} for {len(to_fix)} regattas:")
    for r in to_fix:
        print(f"  {r['regatta_id']!r} | {r['event_name']!r}")

    cur.execute("""
        UPDATE regattas
        SET host_club_id = %s
        WHERE host_club_id IS NULL
          AND (UPPER(COALESCE(event_name, '')) LIKE '%%HYC%%'
               OR UPPER(COALESCE(event_name, '')) LIKE '%%HERMANUS%%')
    """, (hyc_id,))
    n = cur.rowcount
    conn.commit()
    print(f"\nUpdated {n} rows.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
