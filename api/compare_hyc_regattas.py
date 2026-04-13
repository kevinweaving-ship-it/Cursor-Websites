#!/usr/bin/env python3
"""List regattas with host_club_id = HYC for comparison local vs live."""
import os
import sys
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")

def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "local"
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT r.regatta_id, r.event_name, r.start_date, r.host_club_id
        FROM regattas r
        WHERE r.host_club_id = (SELECT club_id FROM clubs WHERE UPPER(TRIM(club_abbrev)) = 'HYC')
        ORDER BY r.start_date DESC NULLS LAST, r.regatta_id
    """)
    rows = cur.fetchall()
    print(f"[{label}] HYC-hosted regattas: {len(rows)}")
    for r in rows:
        print(f"  {r['regatta_id']!r} | {r['event_name']!r} | {r['start_date']} | host={r['host_club_id']}")

    # Also check: any regattas with HYC/Hermanus in name but NOT host_club_id=10
    cur.execute("""
        SELECT r.regatta_id, r.event_name, r.start_date, r.host_club_id
        FROM regattas r
        WHERE (UPPER(COALESCE(r.event_name, '')) LIKE '%HYC%'
               OR UPPER(COALESCE(r.event_name, '')) LIKE '%HERMANUS%')
          AND (r.host_club_id IS NULL OR r.host_club_id != (SELECT club_id FROM clubs WHERE UPPER(TRIM(club_abbrev)) = 'HYC'))
        ORDER BY r.start_date DESC NULLS LAST
    """)
    other = cur.fetchall()
    if other:
        print(f"\n[{label}] HYC/Hermanus in name but host_club_id != HYC: {len(other)}")
        for r in other:
            print(f"  {r['regatta_id']!r} | {r['event_name']!r} | host={r['host_club_id']}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
