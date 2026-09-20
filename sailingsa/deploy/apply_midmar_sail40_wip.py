#!/usr/bin/env python3
"""Sail 40 boat name → Work in Progress. Final, linked. Rebuild Midmar PDFs."""
from pathlib import Path
import psycopg2
import psycopg2.extras

RID = "2026-09-19-hmyc-midmar-cup"
NAME = "Work in Progress"
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
MM = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")
VER = "mmlb16"
RESULT_ID = 21218
ENTRY_ID = 10

TEMP_OLD = """    '40': "Odin's Eye",
"""
TEMP_NEW = ""

TEMP_OBJ_OLD = """  var TEMP_BOATS = {
    '40': "Odin's Eye",
  };
"""
TEMP_OBJ_NEW = """  var TEMP_BOATS = {
  };
"""


def _bust(text: str) -> str:
    out = text
    for old in (
        "mmlb6",
        "mmlb7",
        "mmlb8",
        "mmlb9",
        "mmlb10",
        "mmlb11",
        "mmlb12",
        "mmlb13",
        "mmlb14",
        "mmlb15",
    ):
        out = out.replace("midmar-leaderboard.js?v=" + old, "midmar-leaderboard.js?v=" + VER)
    return out


def main() -> None:
    js = JS.read_text()
    if TEMP_OBJ_OLD in js:
        JS.write_text(js.replace(TEMP_OBJ_OLD, TEMP_OBJ_NEW, 1))
        print("JS_OK")
    elif TEMP_OLD in js:
        JS.write_text(js.replace(TEMP_OLD, TEMP_NEW, 1))
        print("JS_LINE")
    elif "Odin's Eye" not in js:
        print("JS_ALREADY")
    else:
        raise SystemExit("ANCHOR_TEMP")

    if MM.is_file():
        mm = MM.read_text()
        mm2 = _bust(mm)
        if mm2 != mm:
            MM.write_text(mm2)
            print("MM_VER", VER)
    api = API.read_text()
    api2 = _bust(api)
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")

    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT result_id, helm_name, sail_number, boat_name, validation_flag
        FROM results WHERE result_id=%s AND regatta_id=%s
        """,
        (RESULT_ID, RID),
    )
    row = cur.fetchone()
    print("BEFORE", dict(row) if row else None)
    if not row:
        raise SystemExit("NO_40_ROW")
    if str(row["sail_number"] or "").strip() != "40":
        raise SystemExit("REFUSE sail " + str(row["sail_number"]))
    if str(row["helm_name"] or "").strip() != "Penny Macpherson":
        raise SystemExit("REFUSE helm " + str(row["helm_name"]))
    cur.execute(
        """
        UPDATE results
        SET boat_name=%s,
            validation_flag = CASE
              WHEN validation_flag = 'boat_name_temp' THEN NULL
              ELSE validation_flag
            END
        WHERE result_id=%s AND regatta_id=%s
        """,
        (NAME, RESULT_ID, RID),
    )
    cur.execute(
        """
        UPDATE entries
        SET boat_name=%s
        WHERE entry_id=%s AND regatta_id=%s AND TRIM(COALESCE(sail_number::text,''))='40'
        """,
        (NAME, ENTRY_ID, RID),
    )
    print("ENTRIES", cur.rowcount)
    # Only Midmar-sourced temp name row, if any.
    cur.execute(
        """
        UPDATE boat_names
        SET boat_name=%s, notes=COALESCE(notes,'') 
        WHERE source_regatta_id=%s AND boat_name ILIKE %s
        """,
        (NAME, RID, "%odin%"),
    )
    print("BOAT_NAMES", cur.rowcount)
    conn.commit()
    cur.execute(
        "SELECT result_id, helm_name, sail_number, boat_name, validation_flag FROM results WHERE result_id=%s",
        (RESULT_ID,),
    )
    print("AFTER", dict(cur.fetchone()))
    cur.close()
    conn.close()

    import os
    import sys

    os.chdir("/var/www/sailingsa/api")
    if "/var/www/sailingsa" not in sys.path:
        sys.path.insert(0, "/var/www/sailingsa")
    if "/var/www/sailingsa/api" not in sys.path:
        sys.path.insert(0, "/var/www/sailingsa/api")
    import api as ssa

    print("PDF_REBUILD", ssa._rebuild_regatta_stored_pdfs(RID))
    pdfs = [
        Path("/var/www/sailingsa/data/regatta-pdfs/2026-09-19-hmyc-midmar-cup/results.pdf"),
        Path("/var/www/sailingsa/data/regatta-pdfs/2026-09-19-hmyc-midmar-cup/class-hunter-19.pdf"),
        Path("/var/www/sailingsa/data/regatta-pdfs/2026-09-19-hmyc-midmar-cup-hunter-19/results.pdf"),
    ]
    for p in pdfs:
        print("PDF", p, p.is_file(), p.stat().st_size if p.is_file() else 0)
    print("DONE", NAME)


if __name__ == "__main__":
    main()
