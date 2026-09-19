#!/usr/bin/env python3
"""Put all 9 Midmar Cup entries on the list with official club codes.

Sheet order + checksummed SAS IDs only. Megan Guald on the clipboard is
Megan Gauld SAS 14790. Club codes that have logos:
  RNYC, HMYC, ELYC, DAC, PYC.
Does not invent SAS IDs. Does not change Hayden 403 / Puffin / crew.
"""
from __future__ import annotations

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
CLASS_NAME = "Hunter 19"
CLASS_ID = 209

# Sheet order. Clubs are official abbrevs that have Club Logo files.
ENTRIES = [
    {"rank": 1, "sid": 1218, "name": "Paul Changuion", "club": "RNYC", "club_id": 20},
    {"rank": 2, "sid": 177, "name": "Craig Millar", "club": "HMYC", "club_id": 98},
    {"rank": 3, "sid": 1221, "name": "Tony Cockerill", "club": "HMYC", "club_id": 98},
    {"rank": 4, "sid": 14790, "name": "Megan Gauld", "club": "ELYC", "club_id": 121},
    {"rank": 5, "sid": 23999, "name": "Bryan Paxman", "club": "DAC", "club_id": 52},
    {"rank": 6, "sid": 8444, "name": "Nick Somerville", "club": "HMYC", "club_id": 98},
    {"rank": 7, "sid": 729, "name": "Luke Wagner", "club": "PYC", "club_id": 5},
    {"rank": 8, "sid": 21715, "name": "Gust Funke", "club": "PYC", "club_id": 5},
    {"rank": 9, "sid": 8683, "name": "Hayden Miller", "club": "RNYC", "club_id": 20},
]


def checksum_megan(cur) -> None:
    cur.execute(
        """
        SELECT sa_sailing_id::text, full_name, first_name, last_name
        FROM sas_id_personal
        WHERE sa_sailing_id::text = '14790'
        """
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit("REFUSE: SAS 14790 Megan Gauld missing")
    sid, full, fn, ln = row
    print("MEGAN_SAS", sid, full, fn, ln)
    if (fn or "").strip().lower() != "megan" or (ln or "").strip().lower() != "gauld":
        raise SystemExit(f"REFUSE: SAS 14790 is not Megan Gauld: {full!r}")
    cur.execute(
        """
        SELECT sa_sailing_id::text, full_name
        FROM sas_id_personal
        WHERE first_name ILIKE 'megan' AND last_name ILIKE 'gauld'
        """
    )
    matches = cur.fetchall()
    print("MEGAN_GAULD_MATCHES", matches)
    if len(matches) != 1 or str(matches[0][0]).strip() != "14790":
        raise SystemExit("REFUSE: Megan Gauld is not a unique SAS ID")


def apply() -> int:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    checksum_megan(cur)

    cur.execute(
        "SELECT club_id, club_abbrev FROM clubs WHERE club_abbrev = ANY(%s)",
        ([e["club"] for e in ENTRIES],),
    )
    clubs = {r[1]: r[0] for r in cur.fetchall()}
    print("CLUBS", clubs)
    for e in ENTRIES:
        if clubs.get(e["club"]) != e["club_id"]:
            raise SystemExit(f"REFUSE: club mismatch {e['club']} {e['club_id']} vs {clubs}")

    for e in ENTRIES:
        cur.execute(
            """
            SELECT result_id FROM results
            WHERE regatta_id = %s AND helm_sa_sailing_id = %s
            ORDER BY result_id LIMIT 1
            """,
            (RID, e["sid"]),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE results
                SET rank = %s,
                    helm_name = %s,
                    club_raw = %s,
                    club_id = %s,
                    block_id = %s,
                    class_original = %s,
                    class_canonical = %s,
                    class_id = %s,
                    fleet_label = %s,
                    raced = COALESCE(raced, TRUE),
                    result_status = COALESCE(result_status, 'Provisional')
                WHERE result_id = %s
                """,
                (
                    e["rank"],
                    e["name"],
                    e["club"],
                    e["club_id"],
                    BLOCK,
                    CLASS_NAME,
                    CLASS_NAME,
                    CLASS_ID,
                    CLASS_NAME,
                    row[0],
                ),
            )
            print("UPDATE", e["rank"], e["name"], e["sid"], e["club"], "result_id", row[0])
        else:
            cur.execute(
                """
                INSERT INTO results (
                    regatta_id, block_id, rank, fleet_label,
                    class_original, class_canonical, class_id,
                    helm_name, helm_sa_sailing_id,
                    club_raw, club_id,
                    races_sailed, discard_count, race_scores,
                    raced, result_status
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    0, 0, %s,
                    TRUE, 'Provisional'
                )
                """,
                (
                    RID,
                    BLOCK,
                    e["rank"],
                    CLASS_NAME,
                    CLASS_NAME,
                    CLASS_NAME,
                    CLASS_ID,
                    e["name"],
                    e["sid"],
                    e["club"],
                    e["club_id"],
                    psycopg2.extras.Json({}),
                ),
            )
            print("INSERT", e["rank"], e["name"], e["sid"], e["club"])

        cur.execute(
            "SELECT entry_id FROM entries WHERE regatta_id=%s AND helm_sas_id=%s LIMIT 1",
            (RID, str(e["sid"])),
        )
        erow = cur.fetchone()
        if erow:
            cur.execute(
                "UPDATE entries SET club_code=%s, block_id=%s, verified=TRUE WHERE entry_id=%s",
                (e["club"], BLOCK, erow[0]),
            )
            print("ENTRY_UPDATE", e["name"], e["club"])
        else:
            cur.execute(
                """
                INSERT INTO entries (regatta_id, block_id, helm_sas_id, club_code, verified)
                VALUES (%s, %s, %s, %s, TRUE)
                """,
                (RID, BLOCK, str(e["sid"]), e["club"]),
            )
            print("ENTRY_INSERT", e["name"], e["club"])

    cur.execute(
        "UPDATE regatta_blocks SET entries_raced=%s WHERE block_id=%s",
        (len(ENTRIES), BLOCK),
    )
    print("BLOCK_ENTRIES", cur.rowcount, len(ENTRIES))

    conn.commit()

    print("\n===== RESULTS =====")
    cur.execute(
        """
        SELECT rank, result_id, helm_name, helm_sa_sailing_id, crew_name,
               sail_number, boat_name, club_raw, club_id
        FROM results WHERE regatta_id=%s
        ORDER BY COALESCE(rank, 99999), result_id
        """,
        (RID,),
    )
    for r in cur.fetchall():
        print(r)
    print("n=", cur.rowcount)

    print("\n===== ENTRIES =====")
    cur.execute(
        """
        SELECT entry_id, helm_sas_id, club_code, sail_number, boat_name
        FROM entries WHERE regatta_id=%s ORDER BY entry_id
        """,
        (RID,),
    )
    for r in cur.fetchall():
        print(r)

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(apply())
