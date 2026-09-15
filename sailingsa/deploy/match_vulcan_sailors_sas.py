#!/usr/bin/env python3
"""Match VULCAN Challenge 2026 helm/crew to sas_id_personal.

Why they were unmatched: ingest wrote PDF names only and never set
helm_sa_sailing_id / crew_sa_sailing_id.

Only unique SAS IDs are written. First-name-only / missing SAS stay NULL.
Tim (Solenta crew) is Timothy Weaving 21172.
"""
from __future__ import annotations

import psycopg2

RID = "2026-09-13-vulcan-challenge"

# (block tail, sail, helm_name_display, helm_sas, crew_name_display, crew_sas)
# Display names: PDF unless we expand a first-name / typo to the SAS record.
MATCHES = [
    ("01-hobie", "90687", "Graham Offord", 10054, None, None),
    ("01-hobie", "112487", "Robert Obree", 17505, None, None),
    ("01-hobie", "91000", "Andrew Walker", 2110, None, None),
    ("01-hobie", "90107", "Paco Mendes", 14333, None, None),
    ("02-hunter-19", "263", "Paul Tomes", 6563, "Mary-Clare Tomes", None),
    ("02-hunter-19", "754", "Robert Dove", 1687, "Brian Langham", None),
    ("02-hunter-19", "256", "Martin Wesermann", None, "Andrew Mandy", None),
    ("02-hunter-19", "773", "Robert Fine", 6240, "Paul Pearce", 24594),
    ("02-hunter-19", "405", "Paul Moxley", 15229, "Mark Preen", 15228),
    ("02-hunter-19", "007", "Howard Donnelly", 644, "Jendo Ocenasek", 5831),
    ("02-hunter-19", "403", "Hayden Miller", 8683, "Timothy Weaving", 21172),
    ("02-hunter-19", "727", "Kris Jarzebowski", 19413, "Jamie Jarzebowski", 25413),
    ("02-hunter-19", "401", "Dion De Gruchy", 21725, "David Eccles", 19392),
    ("02-hunter-19", "145", "Andy Le May", None, "Lucy Jamieson", 19417),
    ("03-keelboats", "SA600", "Scott Macfarlane", 6413, None, None),
    ("03-keelboats", "SA3141", "Greg Townes", 9047, None, None),
    ("03-keelboats", "SA2186", "Greg Francois", 26153, None, None),
]

ALIASES = [
    ("graham", 10054),
    ("rob orbree", 17505),
    ("robert obree", 17505),
    ("tim", 21172),
    ("timothy weaving", 21172),
    ("jamie jarzebowski", 25413),
    ("scott macfarlane", 6413),
    ("greg francois", 26153),
    ("dion de gruchy", 21725),
]


def main() -> None:
    conn = psycopg2.connect("postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master")
    cur = conn.cursor()

    # Confirm SAS IDs still resolve to the expected names
    checks = {
        10054: "offord",
        17505: "obree",
        2110: "walker",
        14333: "mendes",
        6563: "tomes",
        1687: "dove",
        6240: "fine",
        24594: "pearce",
        15229: "moxley",
        15228: "preen",
        644: "donnelly",
        5831: "ocenasek",
        8683: "miller",
        21172: "weaving",
        19413: "jarzebowski",
        25413: "jarzebowski",
        21725: "gruchy",
        19392: "eccles",
        19417: "jamieson",
        6413: "macfarlane",
        9047: "townes",
        26153: "francois",
    }
    for sid, needle in checks.items():
        cur.execute(
            "SELECT LOWER(full_name) FROM sas_id_personal WHERE sa_sailing_id::text = %s",
            (str(sid),),
        )
        row = cur.fetchone()
        if not row or needle not in (row[0] or ""):
            raise SystemExit(f"SAS_MISMATCH {sid} {row}")

    for tail, sail, helm, helm_sas, crew, crew_sas in MATCHES:
        bid = f"{RID}:{tail}"
        cur.execute(
            """
            UPDATE public.results
            SET helm_name = %s,
                helm_sa_sailing_id = %s,
                crew_name = %s,
                crew_sa_sailing_id = %s
            WHERE regatta_id = %s AND block_id = %s AND sail_number = %s
            """,
            (helm, helm_sas, crew, crew_sas, RID, bid, sail),
        )
        print(f"UPD {bid} {sail} helm={helm}/{helm_sas} crew={crew}/{crew_sas} rows={cur.rowcount}")

    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema='public' AND table_name='sailor_helm_aliases'
        )
        """
    )
    if cur.fetchone()[0]:
        for alias, sid in ALIASES:
            cur.execute(
                """
                INSERT INTO sailor_helm_aliases (helm_name_alias, sa_sailing_id)
                VALUES (%s, %s)
                ON CONFLICT (helm_name_alias) DO UPDATE SET sa_sailing_id = EXCLUDED.sa_sailing_id
                """,
                (alias, sid),
            )

    conn.commit()
    cur.execute(
        """
        SELECT rank, boat_name, sail_number, helm_name, helm_sa_sailing_id,
               crew_name, crew_sa_sailing_id
        FROM public.results
        WHERE regatta_id = %s
        ORDER BY block_id, rank
        """,
        (RID,),
    )
    print("RESULT")
    unmatched = 0
    for row in cur.fetchall():
        print(" ", row)
        if not row[4] and row[3]:
            unmatched += 1
        if row[5] and not row[6]:
            unmatched += 1
    print("UNMATCHED_NAME_SLOTS", unmatched)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
