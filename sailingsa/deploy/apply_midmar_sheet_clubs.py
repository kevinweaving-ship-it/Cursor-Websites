#!/usr/bin/env python3
"""Align Midmar clubs to the HMYC entry sheet.

Only write a club when the sheet code exists in clubs.
Already-correct rows stay. Unknown codes (DRYC, PRSC) stay as-is.
Does not invent clubs. Does not change Hayden 403. Megan stays deleted.
"""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"

# Sheet club by current helm SAS (checksummed). Megan not on the water.
SHEET = {
    1218: "BYC",    # Paul 2013
    177: "DRYC",    # Craig Millar 2000 — not in clubs
    1221: "HMYC",   # Tony 2019
    22984: "ELYC",  # Paige / Bryan 741
    15579: "PRSC",  # Dani / Nick 442 — not in clubs
    729: "WYAC",    # Luke 2004
    21715: "PYC",   # Gust 2018
    8683: "RNYC",   # Hayden 403
    18659: "VYC",   # Penny 40
    28155: "POYC",  # Caitlin / Jethro 297
    14193: "KSYC",  # Shalin / Craig Deverson 748
}


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT sa_sailing_id::text, first_name, last_name
        FROM sas_id_personal WHERE sa_sailing_id::text = '729'
        """
    )
    luke = cur.fetchone()
    if not luke or (luke["first_name"] or "").strip().lower() != "luke":
        raise SystemExit(f"REFUSE: SAS 729 is not Luke: {luke}")
    print("SAS_OK", dict(luke))

    cur.execute(
        """
        SELECT club_id, club_abbrev FROM clubs
        WHERE UPPER(TRIM(club_abbrev)) = ANY(%s)
        """,
        (list({c.upper() for c in SHEET.values()}),),
    )
    clubs = {r["club_abbrev"].upper(): r["club_id"] for r in cur.fetchall()}
    print("CLUBS", clubs)

    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number,
               club_raw, club_id
        FROM results WHERE regatta_id=%s
        ORDER BY COALESCE(rank,99999), result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    applied = []
    skipped = []
    for r in rows:
        sid = int(r["helm_sa_sailing_id"])
        want = SHEET.get(sid)
        live = (r["club_raw"] or "").strip().upper()
        if not want:
            skipped.append((r["helm_name"], "not_on_sheet"))
            continue
        if live == want:
            skipped.append((r["helm_name"], want, "already"))
            continue
        cid = clubs.get(want)
        if cid is None:
            skipped.append((r["helm_name"], want, "missing_from_clubs", live))
            continue
        cur.execute(
            """
            UPDATE results
            SET club_raw=%s, club_id=%s
            WHERE result_id=%s AND regatta_id=%s
            """,
            (want, cid, r["result_id"], RID),
        )
        cur.execute(
            """
            UPDATE entries
            SET club_code=%s
            WHERE regatta_id=%s AND helm_sas_id::text=%s
            """,
            (want, RID, str(sid)),
        )
        applied.append((r["helm_name"], r["sail_number"], live, want, cid))

    conn.commit()
    cur.execute(
        """
        SELECT r.helm_name, r.sail_number, r.club_raw, r.club_id, c.club_abbrev
        FROM results r
        LEFT JOIN clubs c ON c.club_id = r.club_id
        WHERE r.regatta_id=%s
        ORDER BY COALESCE(r.rank,99999), r.result_id
        """,
        (RID,),
    )
    print("===== AFTER =====")
    for r in cur.fetchall():
        print(dict(r))
    print("APPLIED", applied)
    print("SKIPPED", skipped)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
