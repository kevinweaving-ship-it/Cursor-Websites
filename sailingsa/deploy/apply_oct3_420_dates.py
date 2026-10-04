#!/usr/bin/env python3
"""420 Nationals dates: Sat 26 – Sun 27 Sep 2026 (2 days). RID/URL unchanged."""
import json

import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-25-tsc-420-nationals"
EID = 184126
START = "2026-09-26"
END = "2026-09-27"


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE regattas
        SET start_date=%s, end_date=%s
        WHERE regatta_id=%s
        """,
        (START, END, RID),
    )
    print("REG_UPD", cur.rowcount)
    cur.execute(
        """
        UPDATE events
        SET start_date=%s, end_date=%s
        WHERE event_id=%s
        """,
        (START, END, EID),
    )
    print("EV_UPD", cur.rowcount)
    conn.commit()
    cur.execute(
        """
        SELECT regatta_id, event_name, start_date::text, end_date::text
        FROM regattas WHERE regatta_id=%s
        """,
        (RID,),
    )
    print("REG", json.dumps(cur.fetchone(), default=str))
    cur.execute(
        """
        SELECT event_id, event_name, start_date::text, end_date::text, regatta_id
        FROM events WHERE event_id=%s
        """,
        (EID,),
    )
    print("EV", json.dumps(cur.fetchone(), default=str))
    conn.close()


if __name__ == "__main__":
    main()
