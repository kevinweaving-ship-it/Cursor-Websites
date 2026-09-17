#!/usr/bin/env python3
"""Read-only: which columns other Hunter 19 results actually use."""
import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
conn = psycopg2.connect(DSN)
cur = conn.cursor()

print("===== HUNTER 19 REGATTAS =====")
cur.execute(
    """
    SELECT r.regatta_id, rg.event_name, COUNT(*) AS n,
           COUNT(NULLIF(TRIM(r.sail_number), '')) AS sail_n,
           COUNT(NULLIF(TRIM(r.bow_no), '')) AS bow_n,
           COUNT(NULLIF(TRIM(r.hull_no), '')) AS hull_n,
           COUNT(NULLIF(TRIM(r.boat_name), '')) AS boat_n,
           COUNT(NULLIF(TRIM(r.jib_no), '')) AS jib_n,
           COUNT(NULLIF(TRIM(r.fleet_label), '')) AS fleet_n,
           COUNT(NULLIF(TRIM(r.class_canonical), '')) AS class_n,
           COUNT(NULLIF(TRIM(r.club_raw), '')) AS club_n,
           COUNT(NULLIF(TRIM(r.helm_name), '')) AS helm_n,
           COUNT(NULLIF(TRIM(r.crew_name), '')) AS crew_n,
           COUNT(NULLIF(TRIM(r.crew2_name), '')) AS crew2_n
    FROM results r
    LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
    WHERE r.class_canonical ILIKE '%hunter%19%'
       OR r.class_original ILIKE '%hunter%19%'
       OR r.fleet_label ILIKE '%hunter%19%'
    GROUP BY r.regatta_id, rg.event_name
    ORDER BY n DESC
    """
)
print(
    "regatta_id | event | n | sail | bow | hull | boat_name | jib | fleet | class | club | helm | crew | crew2"
)
for row in cur.fetchall():
    print(row)

print("\n===== DISTINCT CLASS / FLEET LABELS =====")
cur.execute(
    """
    SELECT class_canonical, class_original, fleet_label, COUNT(*)
    FROM results
    WHERE class_canonical ILIKE '%hunter%19%'
       OR class_original ILIKE '%hunter%19%'
       OR fleet_label ILIKE '%hunter%19%'
    GROUP BY 1,2,3
    ORDER BY 4 DESC
    """
)
for row in cur.fetchall():
    print(row)

print("\n===== SAMPLE ROWS (populated cols only) =====")
cur.execute(
    """
    SELECT r.regatta_id, r.helm_name, r.crew_name, r.crew2_name,
           r.sail_number, r.bow_no, r.hull_no, r.boat_name, r.jib_no,
           r.class_canonical, r.fleet_label, r.club_raw
    FROM results r
    WHERE (
        r.class_canonical ILIKE '%hunter%19%'
        OR r.class_original ILIKE '%hunter%19%'
        OR r.fleet_label ILIKE '%hunter%19%'
    )
      AND r.regatta_id <> '2026-09-19-hmyc-midmar-cup'
    ORDER BY r.result_id DESC
    LIMIT 25
    """
)
for row in cur.fetchall():
    print(row)

print("\n===== COL FILL RATES (all H19 except Midmar) =====")
cur.execute(
    """
    SELECT
      COUNT(*) AS n,
      COUNT(NULLIF(TRIM(sail_number), '')) AS sail_number,
      COUNT(NULLIF(TRIM(bow_no), '')) AS bow_no,
      COUNT(NULLIF(TRIM(hull_no), '')) AS hull_no,
      COUNT(NULLIF(TRIM(boat_name), '')) AS boat_name,
      COUNT(NULLIF(TRIM(jib_no), '')) AS jib_no,
      COUNT(NULLIF(TRIM(fleet_label), '')) AS fleet_label,
      COUNT(NULLIF(TRIM(class_canonical), '')) AS class_canonical,
      COUNT(NULLIF(TRIM(club_raw), '')) AS club_raw,
      COUNT(NULLIF(TRIM(helm_name), '')) AS helm_name,
      COUNT(NULLIF(TRIM(crew_name), '')) AS crew_name,
      COUNT(NULLIF(TRIM(crew2_name), '')) AS crew2_name
    FROM results
    WHERE (
        class_canonical ILIKE '%hunter%19%'
        OR class_original ILIKE '%hunter%19%'
        OR fleet_label ILIKE '%hunter%19%'
    )
      AND regatta_id <> '2026-09-19-hmyc-midmar-cup'
    """
)
print(cur.fetchone())

print("\n===== BLOCK FLEET VS CLASS =====")
cur.execute(
    """
    SELECT rb.regatta_id, rb.block_id, rb.class_canonical, rb.fleet_label, rb.class_original
    FROM regatta_blocks rb
    WHERE rb.class_canonical ILIKE '%hunter%19%'
       OR rb.fleet_label ILIKE '%hunter%19%'
       OR rb.class_original ILIKE '%hunter%19%'
    ORDER BY rb.regatta_id DESC
    LIMIT 20
    """
)
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
