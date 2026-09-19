#!/usr/bin/env python3
"""Set Jethro Milne Midmar sail number to 297."""
import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
SID = 19130
SAIL = "297"

conn = psycopg2.connect(DSN)
cur = conn.cursor()
cur.execute(
    """
    SELECT sa_sailing_id::text, full_name FROM sas_id_personal
    WHERE sa_sailing_id::text = %s AND first_name ILIKE 'jethro' AND last_name ILIKE 'milne'
    """,
    (str(SID),),
)
row = cur.fetchone()
if not row:
    raise SystemExit("REFUSE: Jethro Milne SAS 19130 not unique/missing")
print("SAS_OK", row)

cur.execute(
    """
    UPDATE results SET sail_number=%s
    WHERE regatta_id=%s AND helm_sa_sailing_id=%s
    """,
    (SAIL, RID, SID),
)
print("RESULT", cur.rowcount)
cur.execute(
    """
    UPDATE entries SET sail_number=%s
    WHERE regatta_id=%s AND helm_sas_id=%s
    """,
    (SAIL, RID, str(SID)),
)
print("ENTRY", cur.rowcount)
conn.commit()
cur.execute(
    """
    SELECT rank, helm_name, helm_sa_sailing_id, sail_number, club_raw
    FROM results WHERE regatta_id=%s AND helm_sa_sailing_id=%s
    """,
    (RID, SID),
)
print("AFTER", cur.fetchone())
cur.close()
conn.close()
