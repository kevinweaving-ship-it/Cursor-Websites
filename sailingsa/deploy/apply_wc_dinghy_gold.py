#!/usr/bin/env python3
"""Western Cape Dinghy Event URL → Cape Classic gold (title + class/club logos)."""
from pathlib import Path
import shutil
import time

import psycopg2

API = Path("/var/www/sailingsa/api/api.py")
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-04-06-western-cape-dinghy-championships"
OLD_NAME = "2026-04-06 Western Cape Dinghy Champs"
NEW_NAME = "2026 Western Cape Dinghy Champs"


def _sql() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE public.regattas
        SET event_name = %s
        WHERE regatta_id = %s
          AND event_name = %s
        """,
        (NEW_NAME, RID, OLD_NAME),
    )
    print("EVENT_NAME", cur.rowcount)
    conn.commit()
    cur.execute("SELECT event_name FROM public.regattas WHERE regatta_id = %s", (RID,))
    print("NAME_NOW", cur.fetchone())
    conn.close()


def _patch_api() -> None:
    api = API.read_text()
    n = 0

    old = """        if _is_cape_classic_2026_zvy_event(_rid_ft) and class_str:
            class_str = _fleet_sheet_class_cell_with_logo_html(class_str, class_display_raw)"""
    new = """        if (not _regatta_is_lipton_challenge(_rid_ft)) and class_str:
            class_str = _fleet_sheet_class_cell_with_logo_html(class_str, class_display_raw)"""
    if old not in api:
        raise SystemExit("CLASS_CELL_GATE_MISSING")
    api = api.replace(old, new, 1)
    n += 1
    print("CLASS_CELL_LOGO_ALL")

    old = """                club_link_html, club_raw, compact=_is_cape_classic_2026_zvy_event(_rid_ft)"""
    new = """                club_link_html, club_raw, compact=(not _regatta_is_lipton_challenge(_rid_ft))"""
    if old not in api:
        raise SystemExit("CLUB_COMPACT_GATE_MISSING")
    api = api.replace(old, new, 1)
    n += 1
    print("CLUB_COMPACT_ALL")

    old = """                    if _is_cape_classic_2026_zvy_event(_rid_ft) and has_penalty:"""
    new = """                    if (not _regatta_is_lipton_challenge(_rid_ft)) and has_penalty:"""
    if old not in api:
        raise SystemExit("PENALTY_SPLIT_GATE_MISSING")
    api = api.replace(old, new, 1)
    n += 1
    print("PENALTY_SPLIT_ALL")

    old = """    if _is_cape_classic_2026_zvy_event(_rid_ft):
        _tbl_cls += " rs-compact-row-logos" """
    new = """    if not _regatta_is_lipton_challenge(_rid_ft):
        _tbl_cls += " rs-compact-row-logos" """
    if old not in api:
        raise SystemExit("COMPACT_TABLE_GATE_MISSING")
    api = api.replace(old, new, 1)
    n += 1
    print("COMPACT_TABLE_ALL")

    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.wc_dinghy_gold.{ts}")
    shutil.copy2(API, bak)
    print("BAK", bak)
    API.write_text(api)
    print("FILES_PATCHED", n)


def main() -> None:
    _sql()
    _patch_api()


if __name__ == "__main__":
    main()
