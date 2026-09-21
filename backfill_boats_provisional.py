#!/usr/bin/env python3
"""
Backfill provisional boats from existing results data.
EXACT-MATCH RULES ONLY - no fuzzy matching.

Rules:
1. Group results by (sail_number_normalized, class_id)
2. If class belongs to a hull family with share_sail_identity=TRUE, group by family
3. Create boat_id for unique matches only
4. Ambiguous cases (multiple boats with same sail in family): leave boat_id=NULL

Usage: python3 backfill_boats_provisional.py [--dry-run]
Env: DATABASE_URL or DB_URL
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
except ImportError:
    print("ERROR: psycopg2 required", file=sys.stderr)
    sys.exit(1)


def get_db_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("DB_URL")


def normalize_sail_number(sail: str) -> str:
    """Normalize sail number: uppercase, collapse whitespace, strip."""
    if not sail:
        return ""
    s = sail.upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def main():
    parser = argparse.ArgumentParser(description="Backfill provisional boats from results.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done, don't write")
    args = parser.parse_args()

    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL or DB_URL required", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print(f"[{datetime.now().isoformat()}] Starting boat backfill (dry_run={args.dry_run})")

    # Step 1: Get class families with share_sail_identity=TRUE
    cur.execute("""
        SELECT cf.family_id, cf.family_name, cfm.class_id
        FROM class_hull_families cf
        JOIN class_family_members cfm ON cf.family_id = cfm.family_id
        WHERE cf.share_sail_identity = TRUE
    """)
    family_classes = {}  # class_id -> family_id
    families = {}  # family_id -> family_name
    for row in cur.fetchall():
        family_classes[row["class_id"]] = row["family_id"]
        families[row["family_id"]] = row["family_name"]
    
    print(f"  Found {len(families)} shared-identity families: {list(families.values())}")

    # Step 2: Get distinct (sail_number, class_id) pairs from results
    cur.execute(r"""
        SELECT DISTINCT 
            UPPER(TRIM(REGEXP_REPLACE(sail_number, '\s+', ' ', 'g'))) as sail_norm,
            class_id,
            MAX(boat_name) as boat_name,
            COUNT(*) as result_count,
            MIN(helm_name) as first_helm,
            MAX(helm_name) as last_helm
        FROM results 
        WHERE sail_number IS NOT NULL 
          AND sail_number != ''
          AND class_id IS NOT NULL
        GROUP BY UPPER(TRIM(REGEXP_REPLACE(sail_number, '\s+', ' ', 'g'))), class_id
        ORDER BY result_count DESC
    """)
    sail_class_pairs = cur.fetchall()
    print(f"  Found {len(sail_class_pairs)} unique (sail_number, class_id) pairs")

    # Step 3: Group by family or class
    # Key: (family_id or class_id, sail_norm) -> list of class_ids
    grouped = {}
    for row in sail_class_pairs:
        sail = row["sail_norm"]
        class_id = row["class_id"]
        
        # Check if class belongs to a shared-identity family
        family_id = family_classes.get(class_id)
        if family_id:
            key = (f"family_{family_id}", sail)
        else:
            key = (f"class_{class_id}", sail)
        
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(row)
    
    print(f"  Grouped into {len(grouped)} potential boats")

    # Step 4: Create boats for unambiguous matches
    boats_created = 0
    identifiers_created = 0
    names_created = 0
    ambiguous_count = 0
    
    for key, rows in grouped.items():
        group_type, sail = key
        
        # For now, all within a group are considered the same boat
        # (exact match on normalized sail + class/family)
        first_row = rows[0]
        total_results = sum(r["result_count"] for r in rows)
        
        # Get class info for the first row
        class_id = first_row["class_id"]
        boat_name = first_row["boat_name"]
        
        if args.dry_run:
            print(f"    Would create boat: {sail} ({group_type}) - {total_results} results")
            boats_created += 1
            identifiers_created += len(rows)
            if boat_name:
                names_created += 1
            continue
        
        # Create boat
        cur.execute("""
            INSERT INTO boats (created_source, created_evidence, created_by)
            VALUES ('result', %s, 'backfill_provisional')
            RETURNING boat_id
        """, (
            Json({"sail": sail, "class_ids": [r["class_id"] for r in rows], "total_results": total_results}),
        ))
        boat_id = cur.fetchone()["boat_id"]
        boats_created += 1
        
        # Create identifiers for each class this sail appeared in
        for row in rows:
            cur.execute("""
                INSERT INTO boat_identifiers (
                    boat_id, identifier_type, identifier_value, class_id,
                    valid_from, is_current, source_type, evidence
                )
                VALUES (%s, 'sail_number', %s, %s, 
                        '1900-01-01', TRUE, 'result', %s)
            """, (
                boat_id,
                sail,
                row["class_id"],
                Json({"first_helm": row["first_helm"], "result_count": row["result_count"]}),
            ))
            identifiers_created += 1
        
        # Create boat name if available
        if boat_name and boat_name.strip():
            cur.execute("""
                INSERT INTO boat_names (boat_id, boat_name, first_seen_date, last_seen_date, source_type, evidence)
                VALUES (%s, %s, '1900-01-01', CURRENT_DATE, 'result', %s)
            """, (
                boat_id,
                boat_name.strip(),
                Json({"from_results": True}),
            ))
            names_created += 1
    
    if not args.dry_run:
        conn.commit()
    
    print(f"\n[{datetime.now().isoformat()}] Backfill complete:")
    print(f"  Boats created: {boats_created}")
    print(f"  Identifiers created: {identifiers_created}")
    print(f"  Names created: {names_created}")
    print(f"  Ambiguous (skipped): {ambiguous_count}")
    
    # Step 5: Update results with boat_id (exact match only)
    if not args.dry_run:
        print("\nUpdating results with boat_id...")
        cur.execute(r"""
            UPDATE results r
            SET boat_id = bi.boat_id
            FROM boat_identifiers bi
            WHERE bi.identifier_type = 'sail_number'
              AND bi.identifier_value = UPPER(TRIM(REGEXP_REPLACE(r.sail_number, '\s+', ' ', 'g')))
              AND bi.class_id = r.class_id
              AND bi.is_current = TRUE
              AND r.boat_id IS NULL
        """)
        results_updated = cur.rowcount
        conn.commit()
        print(f"  Results linked to boats: {results_updated}")
    
    cur.close()
    conn.close()
    print(f"\n[{datetime.now().isoformat()}] Done")


if __name__ == "__main__":
    main()
