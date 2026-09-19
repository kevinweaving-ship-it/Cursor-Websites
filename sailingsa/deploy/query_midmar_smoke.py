#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
conn = psycopg2.connect(DSN)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("===== RESULTS 177 / 2000 / 200 / Copedaph =====")
cur.execute(
    """
    SELECT result_id, entry_id, rank, helm_name, helm_sa_sailing_id, sail_number,
           boat_name, club_raw, validation_flag, race_scores, nett_points_raw
    FROM results
    WHERE regatta_id=%s
      AND (
        helm_sa_sailing_id = 177
        OR sail_number IN ('2000','200')
        OR boat_name ILIKE %s
        OR boat_name ILIKE %s
        OR helm_name ILIKE %s
      )
    ORDER BY result_id
    """,
    (RID, "%copedaph%", "%oakum%", "%millar%"),
)
rows = cur.fetchall()
for r in rows:
    print(dict(r))
print("N", len(rows))

print("\n===== ALL SAILS =====")
cur.execute(
    """
    SELECT helm_name, helm_sa_sailing_id, sail_number, boat_name, validation_flag
    FROM results WHERE regatta_id=%s
    ORDER BY COALESCE(rank,99999), result_id
    """,
    (RID,),
)
for r in cur.fetchall():
    print(dict(r))

print("\n===== ENTRIES 177 =====")
cur.execute(
    """
    SELECT column_name FROM information_schema.columns
    WHERE table_name='entries' AND table_schema='public'
    ORDER BY ordinal_position
    """
)
cols = [r["column_name"] for r in cur.fetchall()]
print("COLS", cols)
wanted = [c for c in cols if c in (
    "entry_id", "regatta_id", "helm_sas_id", "helm_name", "sail_number",
    "boat_name", "club_raw", "validation_flag",
)]
cur.execute(
    f"""
    SELECT {", ".join(wanted)}
    FROM entries
    WHERE regatta_id=%s AND (
      helm_sas_id IN ('177','2000')
      OR sail_number IN ('2000','200')
      OR helm_name ILIKE %s
    )
    """,
    (RID, "%millar%"),
)
for r in cur.fetchall():
    print(dict(r))

print("\n===== FLEET SAIL 200 EXISTS? =====")
cur.execute(
    "SELECT COUNT(*) n FROM results WHERE regatta_id=%s AND sail_number='200'",
    (RID,),
)
print(dict(cur.fetchone()))
cur.close()
conn.close()
