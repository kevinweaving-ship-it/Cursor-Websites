#!/usr/bin/env python3
"""boat_summary + identifier_value for Midmar missing sails."""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"

conn = psycopg2.connect(DSN)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("===== boat_identifiers =====")
cur.execute(
    """
    SELECT identifier_id, boat_id, identifier_type, identifier_value,
           class_id, is_current, source_regatta_id
    FROM boat_identifiers
    WHERE TRIM(identifier_value) IN ('2013','741','40','442')
    ORDER BY identifier_value, boat_id
    """
)
print([dict(x) for x in cur.fetchall()])

print("\n===== boat_summary =====")
cur.execute(
    """
    SELECT boat_id, current_sail_number, current_class_name, current_boat_name,
           primary_helm_name, primary_helm_sa_id, events_count
    FROM boat_summary
    WHERE TRIM(COALESCE(current_sail_number,'')) IN ('2013','741','40','442')
       OR LOWER(COALESCE(current_boat_name,'')) IN
          ('essex girl','bueno vento','odin''s eye','odins eye','scout','sheba')
    ORDER BY current_sail_number, current_boat_name
    """
)
print([dict(x) for x in cur.fetchall()])

print("\n===== validation_flag =====")
cur.execute(
    """
    SELECT validation_flag, COUNT(*) n
    FROM results
    WHERE validation_flag IS NOT NULL
    GROUP BY 1 ORDER BY n DESC LIMIT 20
    """
)
print([dict(x) for x in cur.fetchall()])

print("\n===== entries cols =====")
cur.execute(
    """
    SELECT column_name FROM information_schema.columns
    WHERE table_name='entries' ORDER BY ordinal_position
    """
)
print([r["column_name"] for r in cur.fetchall()])

cur.close()
conn.close()
