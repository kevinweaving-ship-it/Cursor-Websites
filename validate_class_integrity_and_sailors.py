#!/usr/bin/env python3
"""
Validate results.class_id integrity and compare stored _sailors_in_class vs computed.
- Step 1: Integrity must return ZERO invalid rows; else stop.
- Step 2: Recompute true sailors per class (source of truth).
- Step 3: Compare stored _sailors_in_class vs computed; report mismatches only.
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DB_URL", os.getenv("DATABASE_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master"))


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # --- Step 1: Integrity (must be ZERO) ---
        cur.execute("""
            SELECT COUNT(*) AS invalid_fk
            FROM results r
            LEFT JOIN classes c ON c.class_id = r.class_id
            WHERE r.class_id IS NULL OR c.class_id IS NULL
        """)
        row = cur.fetchone()
        invalid_fk = int(row["invalid_fk"]) if row else 0

        cur.execute("""
            SELECT r.class_id
            FROM results r
            LEFT JOIN classes c ON c.class_id = r.class_id
            WHERE c.class_id IS NULL
            GROUP BY r.class_id
        """)
        orphan_class_ids = [r["class_id"] for r in cur.fetchall() or []]

        print("=== Step 1: Integrity === ")
        print(f"  invalid_fk (results with NULL class_id or class_id not in classes): {invalid_fk}")
        if orphan_class_ids:
            print(f"  class_id in results not in classes: {orphan_class_ids}")
        if invalid_fk > 0 or orphan_class_ids:
            print("  STOP: Fix integrity before proceeding.")
            cur.execute("""
                SELECT r.result_id, r.regatta_id, r.block_id, r.class_id, r.class_canonical, r.class_original
                FROM results r
                LEFT JOIN classes c ON c.class_id = r.class_id
                WHERE r.class_id IS NULL OR c.class_id IS NULL
                ORDER BY r.result_id
            """)
            for row in cur.fetchall() or []:
                print(f"    result_id={row['result_id']} regatta_id={row['regatta_id']} block_id={row['block_id']} class_id={row['class_id']} class_canonical={row['class_canonical']!r} class_original={row['class_original']!r}")
            print("  Backfill: UPDATE results r SET class_id = c.class_id FROM classes c WHERE TRIM(c.class_name) = TRIM(r.class_canonical) AND r.class_id IS NULL AND r.class_canonical IS NOT NULL;")
            sys.exit(1)
        print("  OK: ZERO invalid rows.\n")

        # --- Step 2: True sailors per class (source of truth) ---
        cur.execute("""
            WITH class_sailors AS (
              SELECT DISTINCT
                     COALESCE(r.helm_sa_sailing_id, r.crew_sa_sailing_id) AS sailor_id,
                     r.class_id
              FROM results r
              JOIN regattas reg ON reg.regatta_id = r.regatta_id
              WHERE r.raced = TRUE
                AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                AND r.class_id IS NOT NULL
            )
            SELECT c.class_id,
                   c.class_name,
                   COUNT(DISTINCT cs.sailor_id) AS active_sailors
            FROM classes c
            LEFT JOIN class_sailors cs ON cs.class_id = c.class_id
            GROUP BY c.class_id, c.class_name
            ORDER BY c.class_name
        """)
        computed = {r["class_id"]: (r["class_name"], r["active_sailors"]) for r in cur.fetchall() or []}
        print("=== Step 2: Computed sailors per class (source of truth) ===")
        for cid, (name, count) in sorted(computed.items(), key=lambda x: (x[1][0] or "")):
            print(f"  {cid}\t{name or '(null)'}\t{count}")
        print()

        # --- Step 3: Compare stored _sailors_in_class vs computed ---
        cur.execute("""
            SELECT class_id, class_name, _sailors_in_class
            FROM classes
        """)
        stored_rows = cur.fetchall() or []

        # Build stored map (class_id -> stored count)
        stored = {}
        for r in stored_rows:
            stored[r["class_id"]] = (r["class_name"], r["_sailors_in_class"])

        mismatches = []
        for cid, (name, comp_count) in computed.items():
            st = stored.get(cid)
            st_count = st[1] if st else None
            if st_count is not None and st_count != comp_count:
                mismatches.append({"class_id": cid, "class_name": name, "stored": st_count, "computed": comp_count})
        for cid, (name, st_count) in stored.items():
            if cid not in computed and st_count is not None and st_count != 0:
                mismatches.append({"class_id": cid, "class_name": name, "stored": st_count, "computed": 0})

        print("=== Step 3: Stored _sailors_in_class vs computed (mismatches only) ===")
        if not mismatches:
            print("  None. Stored counts match computed.")
        else:
            for m in mismatches:
                print(f"  class_id={m['class_id']} {m['class_name']!r}  stored={m['stored']}  computed={m['computed']}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
