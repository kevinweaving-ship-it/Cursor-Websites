#!/usr/bin/env python3
"""Confirm 741 Bueno Vento: dark-blue validated clickable boat name. Not temp grey."""
from pathlib import Path
import psycopg2
import psycopg2.extras

RID = "2026-09-19-hmyc-midmar-cup"
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
MM = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")
VER = "mmlb15"

TEMP_OLD = """    '741': 'Bueno Vento',
    '40': "Odin's Eye",
"""
TEMP_NEW = """    '40': "Odin's Eye",
"""


def _bust(text: str) -> str:
    out = text
    for old in ("mmlb6", "mmlb7", "mmlb8", "mmlb9", "mmlb10", "mmlb11", "mmlb12", "mmlb13", "mmlb14"):
        out = out.replace("midmar-leaderboard.js?v=" + old, "midmar-leaderboard.js?v=" + VER)
    return out


def main() -> None:
    js = JS.read_text()
    if TEMP_OLD not in js:
        if "'741': 'Bueno Vento'" not in js and '"741": "Bueno Vento"' not in js:
            print("JS_ALREADY_NO_741")
        else:
            raise SystemExit("ANCHOR_TEMP")
    else:
        JS.write_text(js.replace(TEMP_OLD, TEMP_NEW, 1))
        print("JS_OK")

    if MM.is_file():
        mm = MM.read_text()
        mm2 = _bust(mm)
        if mm2 != mm:
            MM.write_text(mm2)
            print("MM_VER", VER)
        else:
            print("MM_VER_ALREADY", VER in mm)

    api = API.read_text()
    api2 = _bust(api)
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY", VER in api)

    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT result_id, helm_name, sail_number, boat_name, validation_flag
        FROM results
        WHERE regatta_id=%s AND TRIM(COALESCE(sail_number::text,''))='741'
        """,
        (RID,),
    )
    row = cur.fetchone()
    print("BEFORE", dict(row) if row else None)
    if not row:
        raise SystemExit("NO_741_ROW")
    bn = str(row["boat_name"] or "").strip()
    if bn.casefold() != "bueno vento":
        raise SystemExit("REFUSE unexpected boat_name: " + bn)
    cur.execute(
        """
        UPDATE results
        SET validation_flag = CASE
              WHEN validation_flag = 'boat_name_temp' THEN NULL
              ELSE validation_flag
            END
        WHERE result_id=%s AND regatta_id=%s
        """,
        (row["result_id"], RID),
    )
    conn.commit()
    cur.execute(
        """
        SELECT result_id, helm_name, sail_number, boat_name, validation_flag
        FROM results WHERE result_id=%s
        """,
        (row["result_id"],),
    )
    print("AFTER", dict(cur.fetchone()))
    cur.close()
    conn.close()
    print("DONE confirm 741 Bueno Vento")


if __name__ == "__main__":
    main()
