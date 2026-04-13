#!/usr/bin/env python3
"""
Ensure (1) all results rows have club_id where club_raw can be resolved,
(2) each sailor (sailing_id) has home_club_code = the club they sail for most (from results).
Uses same logic as api.py update_sailor_club_affiliations and _resolve_club.
Run on cloud: uses DATABASE_URL or DB_URL from env.
"""
import os
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not DB_URL:
    print("Set DATABASE_URL or DB_URL")
    exit(1)


def _resolve_club(cur, club_raw: str):
    if not club_raw or not (club_raw or "").strip():
        return (None, None)
    raw = (club_raw or "").strip()
    cur.execute("""
        WITH q AS (SELECT lower(%s) k)
        SELECT c.club_id, c.club_abbrev
          FROM q
          JOIN clubs c ON lower(c.club_abbrev)=q.k OR lower(COALESCE(c.club_fullname,''))=q.k
        UNION
        SELECT a.club_id, c2.club_abbrev
          FROM q
          JOIN club_aliases a ON lower(a.alias)=q.k
          JOIN clubs c2 ON c2.club_id=a.club_id
        LIMIT 1
    """, (raw,))
    row = cur.fetchone()
    return (row["club_id"], row["club_abbrev"]) if row else (None, None)


def main():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1) Backfill results.club_id from club_raw (same as api _resolve_club)
            cur.execute("""
                SELECT result_id, club_raw FROM results
                WHERE club_raw IS NOT NULL AND trim(club_raw) <> '' AND club_id IS NULL
                LIMIT 100000
            """)
            rows = cur.fetchall()
            updated_results = 0
            for row in rows:
                club_id, _ = _resolve_club(cur, row["club_raw"])
                if club_id is not None:
                    cur.execute(
                        "UPDATE results SET club_id = %s WHERE result_id = %s",
                        (club_id, row["result_id"]),
                    )
                    updated_results += 1
            conn.commit()
            print(f"Backfilled results.club_id: {updated_results} rows")

            # Which sailor table(s) exist
            cur.execute("""
                SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sailing_id') AS has_sailing_id
            """)
            has_sailing_id = cur.fetchone().get("has_sailing_id")
            cur.execute("""
                SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sas_id_personal') AS ok
            """)
            has_sas = cur.fetchone().get("ok")
            cur.execute("""
                SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'sas_id_personal' AND column_name = 'primary_club') AS ok
            """)
            has_primary_club = cur.fetchone().get("ok") if has_sas else False

            # 2) Most-sailed club per sailor (CTE used for both tables if present)
            cte_sql = """
                WITH club_counts AS (
                    SELECT helm_sa_sailing_id AS sa_id, c.club_abbrev, COUNT(*) AS appearances
                    FROM results r JOIN clubs c ON c.club_id = r.club_id
                    WHERE r.helm_sa_sailing_id IS NOT NULL AND r.club_id IS NOT NULL
                    GROUP BY helm_sa_sailing_id, c.club_abbrev
                    UNION ALL
                    SELECT crew_sa_sailing_id AS sa_id, c.club_abbrev, COUNT(*) AS appearances
                    FROM results r JOIN clubs c ON c.club_id = r.club_id
                    WHERE r.crew_sa_sailing_id IS NOT NULL AND r.club_id IS NOT NULL
                    GROUP BY crew_sa_sailing_id, c.club_abbrev
                ),
                most_common_club AS (
                    SELECT DISTINCT ON (sa_id) sa_id, club_abbrev, SUM(appearances) AS total_appearances
                    FROM club_counts
                    GROUP BY sa_id, club_abbrev
                    ORDER BY sa_id, total_appearances DESC, club_abbrev
                )
            """
            updated_sailing_id = 0
            if has_sailing_id:
                cur.execute(cte_sql + """
                    UPDATE sailing_id s SET home_club_code = m.club_abbrev
                    FROM most_common_club m
                    WHERE s.sa_sailing_id::text = m.sa_id::text
                      AND (s.home_club_code IS NULL OR s.home_club_code != m.club_abbrev)
                """)
                updated_sailing_id = cur.rowcount
                conn.commit()
                print(f"Updated sailing_id.home_club_code (most-sailed club): {updated_sailing_id} sailors")

            if has_sas and has_primary_club:
                cur.execute(cte_sql + """
                    UPDATE sas_id_personal s SET primary_club = m.club_abbrev
                    FROM most_common_club m
                    WHERE s.sa_sailing_id::text = m.sa_id::text
                      AND (s.primary_club IS NULL OR s.primary_club != m.club_abbrev)
                """)
                updated_sas = cur.rowcount
                conn.commit()
                print(f"Updated sas_id_personal.primary_club: {updated_sas} sailors")
            elif not has_sailing_id:
                print("sailing_id not present; sas_id_personal.primary_club: skipped (table or column not present)")

            # Summary
            cur.execute("""
                SELECT COUNT(*) AS n FROM results
                WHERE club_raw IS NOT NULL AND trim(club_raw) <> '' AND club_id IS NULL
            """)
            missing = cur.fetchone().get("n", 0)
            print(f"Results still missing club_id (unresolved club_raw): {missing}")
            print("Done.")


if __name__ == "__main__":
    main()
