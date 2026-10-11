"""Close Dam Bottle: Final as at 11 October 2026 at 10:23. Does not change gold api.py."""
from __future__ import annotations

import os

import psycopg2

URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
RID = "2026-10-10-hmyc-dam-bottle-sprints"
AS_AT = "2026-10-11 10:23:00+02"


def main() -> None:
    conn = psycopg2.connect(URL)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE public.regattas
        SET result_status = 'Final',
            as_at_time = %s::timestamptz,
            updated_at = NOW()
        WHERE regatta_id = %s
        RETURNING result_status, as_at_time
        """,
        (AS_AT, RID),
    )
    print("regatta", cur.fetchall())
    cur.execute(
        """
        UPDATE public.results
        SET result_status = 'Final',
            as_at_time = %s::timestamptz
        WHERE regatta_id = %s
        """,
        (AS_AT, RID),
    )
    print("results", cur.rowcount)
    cur.execute(
        """
        UPDATE public.events
        SET event_status = 'completed'
        WHERE regatta_id = %s
        RETURNING event_status
        """,
        (RID,),
    )
    print("events", cur.fetchall())
    cur.execute(
        """
        UPDATE public.regatta_blocks
        SET entries_closed = FALSE
        WHERE regatta_id = %s
        RETURNING block_id, entries_closed
        """,
        (RID,),
    )
    print("blocks", cur.fetchall())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
