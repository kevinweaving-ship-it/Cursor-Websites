#!/usr/bin/env python3
"""Look up Midmar preload names and validate unique SAS IDs."""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"

NAMES = [
    ("Paul", "Changioun"),
    ("Paul", "Changuion"),
    ("Craig", "Millar"),
    ("Craig", "Miller"),
    ("Tony", "Cockerill"),
    ("Anthony", "Cockerill"),
    ("Megan", "Guald"),
    ("Megan", "Gould"),
    ("Bryan", "Paxman"),
    ("Brian", "Paxman"),
    ("Nick", "Sommerville"),
    ("Nick", "Somerville"),
    ("Nicholas", "Sommerville"),
    ("Nicholas", "Somerville"),
    ("Luke", "Wagner"),
    ("Gust", "Funke"),
    ("Gustav", "Funke"),
    ("Hayden", "Miller"),
    ("Tim", "Weaving"),
    ("Timothy", "Weaving"),
    ("Howard", "Leoto"),
]

conn = psycopg2.connect(DSN)
cur = conn.cursor()

print("===== COLS =====")
for table in ("entries", "results", "sas_id_personal"):
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    print(table, [r[0] for r in cur.fetchall()])

print("\n===== MIDMAR =====")
cur.execute("SELECT regatta_id, event_name, start_date, fleet_classes FROM regattas WHERE regatta_id=%s", (RID,))
print("regatta", cur.fetchall())
cur.execute("SELECT block_id, class_canonical, class_id FROM regatta_blocks WHERE regatta_id=%s", (RID,))
print("blocks", cur.fetchall())
cur.execute("SELECT COUNT(*) FROM entries WHERE regatta_id=%s", (RID,))
print("entries", cur.fetchone())
cur.execute("SELECT COUNT(*) FROM results WHERE regatta_id=%s", (RID,))
print("results", cur.fetchone())

# detect name columns
cur.execute(
    """
    SELECT column_name FROM information_schema.columns
    WHERE table_schema='public' AND table_name='sas_id_personal'
    """
)
cols = {r[0] for r in cur.fetchall()}
print("sas cols sample", sorted(cols)[:40])

id_col = "sa_sailing_id" if "sa_sailing_id" in cols else ("sas_id" if "sas_id" in cols else None)
fn_col = "first_name" if "first_name" in cols else ("firstname" if "firstname" in cols else None)
ln_col = "last_name" if "last_name" in cols else ("surname" if "surname" in cols else None)
print("id/fn/ln", id_col, fn_col, ln_col)

print("\n===== NAME LOOKUPS =====")
seen = set()
for fn, ln in NAMES:
    key = (fn.lower(), ln.lower())
    if key in seen:
        continue
    seen.add(key)
    cur.execute(
        f"""
        SELECT {id_col}::text, {fn_col}, {ln_col}
        FROM sas_id_personal
        WHERE {fn_col} ILIKE %s AND {ln_col} ILIKE %s
        ORDER BY {id_col}
        LIMIT 20
        """,
        (fn, ln),
    )
    rows = cur.fetchall()
    print(f"{fn} {ln}: n={len(rows)} {rows}")

print("\n===== BROADER LAST-NAME =====")
for ln in (
    "changioun",
    "changuion",
    "cockerill",
    "guald",
    "gould",
    "paxman",
    "sommerville",
    "somerville",
    "wagner",
    "funke",
    "weaving",
    "leoto",
    "millar",
    "miller",
):
    cur.execute(
        f"""
        SELECT {id_col}::text, {fn_col}, {ln_col}
        FROM sas_id_personal
        WHERE {ln_col} ILIKE %s
        ORDER BY {ln_col}, {fn_col}
        LIMIT 25
        """,
        (ln,),
    )
    rows = cur.fetchall()
    print(f"LN {ln}: n={len(rows)} {rows}")

cur.close()
conn.close()
