#!/usr/bin/env python3
"""Set Midmar Cup sail numbers from the HMYC sail-no sheet.

Match existing boats. Do not invent numbers. Megan and Jethro stay blank
(sheet empty / 0). Hayden 403 is already correct.
"""
from __future__ import annotations

import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"

# helm_sa_sailing_id currently on the boat -> sail number
SAILS = {
    1218: "2013",   # Paul Changuion
    177: "2000",    # Craig Millar
    1221: "2019",   # Tony Cockerill
    22984: "741",   # Paige Smith (Bryan Paxman boat)
    15579: "442",   # Daniela Cantarelli (Nick Somerville boat)
    729: "2004",    # Luke Wagner
    21715: "2018",  # Gust Funke
    8683: "403",    # Hayden Miller
    18659: "40",    # Penny Macpherson
    14193: "748",   # Shalin Naidoo (Craig Deverson boat)
}


def apply() -> int:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    print("===== BEFORE =====")
    cur.execute(
        """
        SELECT rank, helm_name, helm_sa_sailing_id, crew_name, sail_number, boat_name
        FROM results WHERE regatta_id=%s
        ORDER BY COALESCE(rank, 99999), result_id
        """,
        (RID,),
    )
    for r in cur.fetchall():
        print(r)

    for sid, sail in SAILS.items():
        cur.execute(
            """
            UPDATE results
            SET sail_number = %s
            WHERE regatta_id = %s AND helm_sa_sailing_id = %s
            """,
            (sail, RID, sid),
        )
        print("RESULT", sid, sail, "rows", cur.rowcount)
        cur.execute(
            """
            UPDATE entries
            SET sail_number = %s
            WHERE regatta_id = %s AND helm_sas_id = %s
            """,
            (sail, RID, str(sid)),
        )
        print("ENTRY", sid, sail, "rows", cur.rowcount)

    conn.commit()

    print("\n===== AFTER =====")
    cur.execute(
        """
        SELECT rank, helm_name, helm_sa_sailing_id, sail_number, boat_name, club_raw
        FROM results WHERE regatta_id=%s
        ORDER BY COALESCE(rank, 99999), result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    for r in rows:
        print(r)
    print("n=", len(rows))
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(apply())
