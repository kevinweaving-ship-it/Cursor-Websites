"""Set Bryan Paxman Dam Bottle club DAC/DUC -> HMYC. Live DB only. Does not change gold api.py."""
from __future__ import annotations

import os

import psycopg2

URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
REGATTA = "2026-10-10-hmyc-dam-bottle-sprints"
SAS_ID = 23999


def main() -> None:
    conn = psycopg2.connect(URL)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE public.results
        SET club_raw = 'HMYC', club_id = 98
        WHERE regatta_id = %s
          AND helm_sa_sailing_id = %s
          AND helm_name = 'Bryan Paxman'
          AND club_raw IN ('DAC', 'DUC')
        RETURNING result_id, helm_name, club_raw, club_id
        """,
        (REGATTA, SAS_ID),
    )
    results = cur.fetchall()
    cur.execute(
        """
        UPDATE public.entries
        SET club_code = 'HMYC'
        WHERE regatta_id = %s
          AND helm_sas_id = %s
          AND club_code IN ('DAC', 'DUC')
        RETURNING entry_id, sail_number, club_code
        """,
        (REGATTA, str(SAS_ID)),
    )
    entries = cur.fetchall()
    cur.execute(
        """
        UPDATE public.sas_id_personal
        SET club_1 = CASE WHEN club_1 IN ('DAC', 'DUC') THEN 'HMYC' ELSE club_1 END,
            primary_club = CASE WHEN primary_club IN ('DAC', 'DUC') THEN 'HMYC' ELSE primary_club END
        WHERE sa_sailing_id::text = %s
          AND (club_1 IN ('DAC', 'DUC') OR primary_club IN ('DAC', 'DUC'))
        RETURNING sa_sailing_id, full_name, club_1, primary_club
        """,
        (str(SAS_ID),),
    )
    sailor = cur.fetchall()
    conn.commit()
    print("results", results)
    print("entries", entries)
    print("sailor", sailor)
    if not results and not entries and not sailor:
        raise SystemExit("no Bryan Paxman DAC/DUC row to update")
    conn.close()


if __name__ == "__main__":
    main()
