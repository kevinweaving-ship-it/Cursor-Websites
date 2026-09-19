#!/usr/bin/env python3
"""Amend Midmar Craig Millar SAS 177: sail 2000 → 200, boat Smoke & Oakum."""
from __future__ import annotations

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
SID = 177
OLD_SAIL = "2000"
NEW_SAIL = "200"
OLD_NAME = "Copedaph"
NEW_NAME = "Smoke & Oakum"
HELM = "Craig Millar"


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT result_id, entry_id, helm_name, helm_sa_sailing_id, sail_number,
               boat_name, validation_flag
        FROM results
        WHERE regatta_id=%s AND helm_sa_sailing_id=%s
        """,
        (RID, SID),
    )
    rows = cur.fetchall()
    if len(rows) != 1:
        raise SystemExit("REFUSE expected 1 Craig Millar result, got " + str(len(rows)))
    row = rows[0]
    live = (row["helm_name"] or "").strip()
    if live.casefold() != HELM.casefold():
        raise SystemExit(f"REFUSE name mismatch expected {HELM!r} got {live!r}")
    sail = str(row["sail_number"] or "").strip()
    if sail != OLD_SAIL:
        raise SystemExit(f"REFUSE sail not {OLD_SAIL}: {sail!r}")
    name = (row["boat_name"] or "").strip()
    if name.casefold() != OLD_NAME.casefold():
        raise SystemExit(f"REFUSE boat not {OLD_NAME}: {name!r}")

    cur.execute(
        "SELECT result_id, helm_name, sail_number FROM results WHERE regatta_id=%s AND sail_number=%s",
        (RID, NEW_SAIL),
    )
    clash = cur.fetchall()
    if clash:
        raise SystemExit("REFUSE sail 200 already in fleet: " + str(clash))

    cur.execute(
        """
        UPDATE results
        SET sail_number=%s, boat_name=%s, validation_flag=NULL
        WHERE result_id=%s AND regatta_id=%s AND helm_sa_sailing_id=%s
        """,
        (NEW_SAIL, NEW_NAME, row["result_id"], RID, SID),
    )
    if cur.rowcount != 1:
        raise SystemExit("REFUSE results update rows=" + str(cur.rowcount))
    print("RESULT", row["result_id"], HELM, OLD_SAIL, "->", NEW_SAIL, NEW_NAME)

    cur.execute(
        """
        UPDATE entries
        SET sail_number=%s, boat_name=%s
        WHERE regatta_id=%s AND helm_sas_id=%s AND sail_number=%s
        """,
        (NEW_SAIL, NEW_NAME, RID, str(SID), OLD_SAIL),
    )
    print("ENTRY rows", cur.rowcount)

    conn.commit()

    cur.execute(
        """
        SELECT rank, helm_name, helm_sa_sailing_id, sail_number, boat_name, validation_flag
        FROM results WHERE regatta_id=%s ORDER BY COALESCE(rank,99999), result_id
        """,
        (RID,),
    )
    for r in cur.fetchall():
        mark = " <<" if int(r["helm_sa_sailing_id"] or 0) == SID else ""
        print(dict(r), mark)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
