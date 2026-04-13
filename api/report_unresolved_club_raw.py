#!/usr/bin/env python3
"""List results that have club_raw but no club_id (unresolved). Uses DATABASE_URL or DB_URL."""
import os
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not DB_URL:
    print("Set DATABASE_URL or DB_URL")
    exit(1)

def main():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT r.result_id, r.regatta_id, r.helm_name, r.crew_name,
                       r.club_raw, r.class_canonical,
                       rg.event_name, rg.year
                FROM results r
                LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                WHERE r.club_raw IS NOT NULL AND TRIM(r.club_raw) <> ''
                  AND r.club_id IS NULL
                ORDER BY r.club_raw, r.result_id
            """)
            rows = cur.fetchall()
            print(f"Results with club_raw but no club_id (unresolved): {len(rows)}\n")
            print("reason: club_raw does not match any club in 'clubs' or 'club_aliases'\n")
            print("result_id\tregatta_id\tevent_name\tyear\tclass\tclub_raw\thelm_name\tcrew_name")
            print("-" * 120)
            for row in rows:
                rid = row["result_id"]
                reg = row["regatta_id"] or ""
                evt = (row["event_name"] or "")[:30]
                yr = row["year"] or ""
                cls = (row["class_canonical"] or row.get("class_original") or "")[:20]
                raw = (row["club_raw"] or "").strip()
                helm = (row["helm_name"] or "")[:25]
                crew = (row["crew_name"] or "")[:25]
                print(f"{rid}\t{reg}\t{evt}\t{yr}\t{cls}\t{raw}\t{helm}\t{crew}")
            print("-" * 120)
            # Distinct club_raw values so we know what to add as alias
            cur.execute("""
                SELECT DISTINCT TRIM(r.club_raw) AS club_raw
                FROM results r
                WHERE r.club_raw IS NOT NULL AND TRIM(r.club_raw) <> '' AND r.club_id IS NULL
                ORDER BY 1
            """)
            distinct = cur.fetchall()
            print("\nDistinct club_raw values to add (as club or alias):")
            for row in distinct:
                print(f"  {row['club_raw']}")

if __name__ == "__main__":
    main()
