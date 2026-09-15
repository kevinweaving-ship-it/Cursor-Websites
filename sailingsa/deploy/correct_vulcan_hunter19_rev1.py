#!/usr/bin/env python3
"""Hunter 19 rev1: Solenta Non Spin ToT 0.975 — correct time/rank only. Names untouched."""
import json
import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
BLOCK = "2026-09-13-vulcan-challenge:02-hunter-19"


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    # Solenta 403: ToT 0.9750, corrected 02:50:14, delta 00:05:28, rank 6
    cur.execute(
        """
        UPDATE public.results
        SET rank = 6,
            handicap = '0.9750',
            corrected_time = '02:50:14',
            delta_time = '00:05:28',
            race_scores = %s::jsonb,
            total_points_raw = 6.0,
            nett_points_raw = 6.0
        WHERE block_id = %s AND sail_number = '403' AND boat_name = 'Solenta'
        """,
        (json.dumps({"R1": "6.0"}), BLOCK),
    )
    print("SOLENTA", cur.rowcount)
    # Artemis 007: times unchanged; rank 7
    cur.execute(
        """
        UPDATE public.results
        SET rank = 7,
            race_scores = %s::jsonb,
            total_points_raw = 7.0,
            nett_points_raw = 7.0
        WHERE block_id = %s AND sail_number = '007' AND boat_name = 'Artemis'
        """,
        (json.dumps({"R1": "7.0"}), BLOCK),
    )
    print("ARTEMIS", cur.rowcount)
    conn.commit()
    cur.close()
    conn.close()
    print("OK")


if __name__ == "__main__":
    main()
