#!/usr/bin/env python3
"""420 Nationals: Timothy Weaving club HYC → RNYC. Scores unchanged."""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-25-tsc-420-nationals"
RESULT_ID = 21263
HELM = "Timothy Weaving"
SAIL = "53095"
OLD_CLUB = "HYC"
OLD_ID = 10
NEW_CLUB = "RNYC"
NEW_ID = 20


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT result_id, helm_name, crew_name, sail_number, club_raw, club_id,
               helm_sa_sailing_id, crew_sa_sailing_id, race_scores
        FROM results WHERE result_id=%s AND regatta_id=%s
        """,
        (RESULT_ID, RID),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit("MISSING_ROW")
    if row["helm_name"] != HELM or str(row["sail_number"]) != SAIL:
        raise SystemExit("REFUSE identity " + str(dict(row)))
    if row["club_raw"] != OLD_CLUB or int(row["club_id"]) != OLD_ID:
        if row["club_raw"] == NEW_CLUB and int(row["club_id"]) == NEW_ID:
            print("ALREADY", dict(row))
            return
        raise SystemExit("REFUSE club " + str(dict(row)))
    scores_before = row["race_scores"]
    cur.execute(
        "UPDATE results SET club_raw=%s, club_id=%s WHERE result_id=%s AND regatta_id=%s",
        (NEW_CLUB, NEW_ID, RESULT_ID, RID),
    )
    conn.commit()
    cur.execute(
        """
        SELECT result_id, helm_name, sail_number, club_raw, club_id, race_scores
        FROM results WHERE result_id=%s
        """,
        (RESULT_ID,),
    )
    after = cur.fetchone()
    if after["race_scores"] != scores_before:
        raise SystemExit("REFUSE scores changed")
    if after["club_raw"] != NEW_CLUB or int(after["club_id"]) != NEW_ID:
        raise SystemExit("REFUSE update failed " + str(dict(after)))
    print("OK", dict(after))
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
