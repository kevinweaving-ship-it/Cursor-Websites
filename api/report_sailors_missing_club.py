#!/usr/bin/env python3
"""
List sailors (sas_id_personal) who have no club code and why.
Uses DATABASE_URL or DB_URL from env. Run on cloud: same env as API.
Usage: python3 report_sailors_missing_club.py [--summary-only] [--out file]
  --summary-only: print only counts by reason
  --out file: write full list to file (default: stdout)
"""
import os
import sys
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not DB_URL:
    print("Set DATABASE_URL or DB_URL")
    exit(1)

SUMMARY_ONLY = "--summary-only" in sys.argv
ONLY_WITH_RESULTS = "--only-with-results" in sys.argv  # list only sailors who have results (actionable)
OUT_FILE = None
if "--out" in sys.argv:
    i = sys.argv.index("--out")
    if i + 1 < len(sys.argv):
        OUT_FILE = sys.argv[i + 1]


def main():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Sailors with no club
            cur.execute("""
                SELECT sa_sailing_id::text AS sas_id,
                       COALESCE(TRIM(full_name), TRIM(first_name || ' ' || COALESCE(last_name, ''))) AS name
                FROM sas_id_personal
                WHERE primary_club IS NULL OR TRIM(COALESCE(primary_club, '')) = ''
                ORDER BY name
            """)
            sailors = cur.fetchall()
            if not sailors:
                print("All sailors have a club code set.")
                return

            # Bulk: sailors who appear in results (helm or crew)
            cur.execute("""
                SELECT DISTINCT sa_id FROM (
                    SELECT helm_sa_sailing_id::text AS sa_id FROM results WHERE helm_sa_sailing_id IS NOT NULL
                    UNION
                    SELECT crew_sa_sailing_id::text AS sa_id FROM results WHERE crew_sa_sailing_id IS NOT NULL
                ) x
            """)
            in_results = {r["sa_id"] for r in cur.fetchall()}
            # Bulk: sailors who have at least one result with club_id set
            cur.execute("""
                SELECT DISTINCT sa_id FROM (
                    SELECT helm_sa_sailing_id::text AS sa_id FROM results WHERE helm_sa_sailing_id IS NOT NULL AND club_id IS NOT NULL
                    UNION
                    SELECT crew_sa_sailing_id::text AS sa_id FROM results WHERE crew_sa_sailing_id IS NOT NULL AND club_id IS NOT NULL
                ) x
            """)
            has_club_in_results = {r["sa_id"] for r in cur.fetchall()}
            # Bulk: sailors who have at least one result with club_raw set (but may not resolve)
            cur.execute("""
                SELECT DISTINCT sa_id FROM (
                    SELECT helm_sa_sailing_id::text AS sa_id FROM results WHERE helm_sa_sailing_id IS NOT NULL AND club_raw IS NOT NULL AND TRIM(club_raw) <> ''
                    UNION
                    SELECT crew_sa_sailing_id::text AS sa_id FROM results WHERE crew_sa_sailing_id IS NOT NULL AND club_raw IS NOT NULL AND TRIM(club_raw) <> ''
                ) x
            """)
            has_raw_in_results = {r["sa_id"] for r in cur.fetchall()}

            reasons = {}
            lines = []
            for s in sailors:
                sid = s["sas_id"]
                name = (s["name"] or "").strip() or "(no name)"
                if sid not in in_results:
                    reason = "No results in DB (never appeared as helm/crew)"
                elif sid in has_club_in_results:
                    reason = "Has results with club_id but primary_club not set (re-run script)"
                elif sid in has_raw_in_results:
                    reason = "All results have club_raw but none resolve to a club (add club/alias)"
                else:
                    reason = "Has results but no club_raw on any result row"
                reasons[reason] = reasons.get(reason, 0) + 1
                if ONLY_WITH_RESULTS and sid not in in_results:
                    continue
                lines.append((sid, name, reason))

            print(f"Sailors with no club code: {len(sailors)}\n")
            print("Summary by reason:")
            print("-" * 60)
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"  {count:6d}  {reason}")
            print("-" * 60)

            if SUMMARY_ONLY:
                print("Done (use without --summary-only for full list).")
                return

            out = open(OUT_FILE, "w") if OUT_FILE else sys.stdout
            try:
                if OUT_FILE:
                    out.write("sas_id\tname\treason\n")
                    out.write("-" * 80 + "\n")
                for sid, name, reason in lines:
                    out.write(f"{sid}\t{name}\t{reason}\n")
                if OUT_FILE:
                    out.write("-" * 80 + "\nDone.\n")
                    print(f"Full list written to {OUT_FILE}")
            finally:
                if OUT_FILE:
                    out.close()
            if not OUT_FILE:
                print("Done.")


if __name__ == "__main__":
    main()
