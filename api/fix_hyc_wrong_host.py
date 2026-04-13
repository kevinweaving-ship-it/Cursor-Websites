#!/usr/bin/env python3
"""Set host_club_id = HYC (10) for regattas wrongly set to 110."""
import os
import psycopg2

DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")

IDS = [
    "311-2025-hyc-cape-classic-ilca-4-16-results",
    "308-2025-hyc-cape-classic-mirror-results",
    "312-2025-hyc-cape-classic-dabchick-results",
    "310-2025-hyc-cape-classic-ilca-6-results",
    "309-2025-hyc-cape-classic-ilca-7-results",
]

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT club_id FROM clubs WHERE UPPER(TRIM(club_abbrev)) = 'HYC' LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("HYC club not found")
        conn.close()
        return
    hyc_id = row[0]

    cur.execute("""
        UPDATE regattas SET host_club_id = %s
        WHERE regatta_id = ANY(%s) AND host_club_id != %s
    """, (hyc_id, IDS, hyc_id))
    n = cur.rowcount
    conn.commit()
    print(f"Updated {n} HYC regattas to host_club_id={hyc_id}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
