#!/usr/bin/env python3
"""Caitlin Macpherson helm, Jethro Milne crew on Midmar sail 297."""
import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
CAITLIN = 28155
JETHRO = 19130
MATTHEW = 15791


def unique(cur, sid, fn, ln):
    cur.execute(
        """
        SELECT sa_sailing_id::text, full_name FROM sas_id_personal
        WHERE sa_sailing_id::text = %s
          AND first_name ILIKE %s AND last_name ILIKE %s
        """,
        (str(sid), fn, ln),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"REFUSE: {fn} {ln} SAS {sid}")
    cur.execute(
        """
        SELECT sa_sailing_id::text FROM sas_id_personal
        WHERE first_name ILIKE %s AND last_name ILIKE %s
        """,
        (fn, ln),
    )
    ids = {r[0] for r in cur.fetchall()}
    if ids != {str(sid)}:
        raise SystemExit(f"REFUSE: {fn} {ln} not unique {ids}")
    print("SAS_OK", row)
    return row[1]


conn = psycopg2.connect(DSN)
cur = conn.cursor()
caitlin = unique(cur, CAITLIN, "Caitlin", "Macpherson")
jethro = unique(cur, JETHRO, "Jethro", "Milne")
matthew = unique(cur, MATTHEW, "Matthew", "Macpherson")

if caitlin.lower() in (jethro.lower(), matthew.lower()):
    raise SystemExit("REFUSE: helm duplicated in crew names")

cur.execute(
    """
    UPDATE results
    SET helm_name=%s,
        helm_sa_sailing_id=%s,
        crew_name=%s,
        crew_sa_sailing_id=%s,
        crew2_name=%s,
        crew2_sa_sailing_id=%s,
        block_id=%s
    WHERE regatta_id=%s AND helm_sa_sailing_id = ANY(%s)
    """,
    (
        caitlin,
        CAITLIN,
        jethro,
        JETHRO,
        matthew,
        MATTHEW,
        BLOCK,
        RID,
        [JETHRO, CAITLIN],
    ),
)
print("RESULT", cur.rowcount)

cur.execute(
    """
    UPDATE entries
    SET helm_sas_id=%s, crew_sas_id=%s, block_id=%s, verified=TRUE
    WHERE regatta_id=%s AND helm_sas_id = ANY(%s)
    """,
    (str(CAITLIN), str(JETHRO), BLOCK, RID, [str(JETHRO), str(CAITLIN)]),
)
print("ENTRY", cur.rowcount)
conn.commit()

cur.execute(
    """
    SELECT rank, helm_name, helm_sa_sailing_id, crew_name, crew2_name,
           crew_sa_sailing_id, crew2_sa_sailing_id, sail_number, club_raw
    FROM results
    WHERE regatta_id=%s AND helm_sa_sailing_id=%s
    """,
    (RID, CAITLIN),
)
row = cur.fetchone()
print("AFTER", row)
helm = (row[1] or "").lower()
if helm in ((row[3] or "").lower(), (row[4] or "").lower()):
    raise SystemExit("REFUSE_AFTER: helm in crew")
cur.close()
conn.close()
