#!/usr/bin/env python3
"""Persist host + Final where results exist (gold Event URL data)."""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"


def club_row(cur, *needles):
    for n in needles:
        cur.execute(
            """
            SELECT club_id, club_abbrev, club_fullname
            FROM clubs
            WHERE upper(club_abbrev)=upper(%s)
               OR upper(club_fullname)=upper(%s)
               OR club_fullname ILIKE %s
            LIMIT 1
            """,
            (n, n, f"%{n}%"),
        )
        r = cur.fetchone()
        if r:
            return r
    return None


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        UPDATE regattas r
        SET result_status = 'Final'
        WHERE COALESCE(btrim(r.result_status), '') IN ('', 'Unknown', 'unknown')
          AND EXISTS (SELECT 1 FROM results x WHERE x.regatta_id = r.regatta_id)
        """
    )
    print("FINALIZED", cur.rowcount)

    pairs = [
        ("2026-02-15-hyc-cape-classic", ("HYC", "Hermanus Yacht Club")),
        ("2025-10-19-eastern-cape-champs-monohull", ("Redhouse", "RNYC", "Redhouse Yacht Club")),
    ]
    for rid, names in pairs:
        c = club_row(cur, *names)
        if not c:
            print("NO_CLUB", rid, names)
            continue
        cur.execute(
            """
            UPDATE regattas
            SET host_club_id=%s, host_club_code=%s, host_club_name=%s
            WHERE regatta_id=%s
              AND (host_club_id IS NULL OR COALESCE(host_club_code,'')='')
            """,
            (c["club_id"], c["club_abbrev"], c["club_fullname"], rid),
        )
        print("HOST", rid, c["club_abbrev"], cur.rowcount)
    conn.commit()
    print("DATA_OK")


if __name__ == "__main__":
    main()
