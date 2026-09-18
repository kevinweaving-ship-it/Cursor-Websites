#!/usr/bin/env python3
"""Midmar std columns (Bow No, Boat Name) + MP scroll so Crew is reachable.

Live-only surgical patch of /var/www/sailingsa/api/api.py. Does not overwrite the file.
"""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_STD_COLS_MP_SCROLL_v1"
RID = "2026-09-19-hmyc-midmar-cup"

CREW_OLD = """    show_crew_col = _optional_col_visible("crew", has_crew)

    def _norm_result_sheet_label(v: object) -> str:
"""

CREW_NEW = """    show_crew_col = _optional_col_visible("crew", has_crew)
    # MIDMAR_STD_COLS_MP_SCROLL_v1: always show Bow No + Boat Name; keep Crew for MP scroll.
    if str(fleet.get("regatta_id") or "").strip() == "2026-09-19-hmyc-midmar-cup":
        show_boat = True
        show_bow = True
        show_crew_col = True

    def _norm_result_sheet_label(v: object) -> str:
"""

BOW_TH_OLD = """        thead += f'<th class="wc-meta-col">{html_module.escape(_bow_lab)}</th>'"""
BOW_TH_NEW = """        thead += f'<th class="wc-meta-col bow-col">{html_module.escape(_bow_lab)}</th>'"""

BOAT_TH_OLD = """        thead += '<th class="wc-meta-col">Boat Name</th>'"""
BOAT_TH_NEW = """        thead += '<th class="wc-meta-col boat-col">Boat Name</th>'"""

BOW_TD_OLD = """            row_html += f'<td class="wc-meta-col">{_wc_cell(bow_disp, bv, "bow_no", None, 32)}</td>'"""
BOW_TD_NEW = """            row_html += f'<td class="wc-meta-col bow-col">{_wc_cell(bow_disp, bv, "bow_no", None, 32)}</td>'"""

BOAT_TD_OLD = """            row_html += f'<td class="wc-meta-col">{_wc_cell(bn_html, bn_edit, "boat_name", None, 120)}</td>'"""
BOAT_TD_NEW = """            row_html += f'<td class="wc-meta-col boat-col">{_wc_cell(bn_html, bn_edit, "boat_name", None, 120)}</td>'"""

HIDE_OLD = (
    '".fleet-section .table-wrapper table.fleet-results-table th.class-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table td.class-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table th.crew-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table td.crew-col{display:none!important}"'
)

HIDE_NEW = (
    '".fleet-section .table-wrapper table.fleet-results-table th.class-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table td.class-col{display:none!important}"\n'
    '    "/* MIDMAR_STD_COLS_MP_SCROLL_v1: Crew / Bow / Boat stay visible; swipe to see them. */"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table th.crew-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table td.crew-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table th.bow-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table td.bow-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table th.boat-col,"\n'
    '    ".fleet-section .table-wrapper table.fleet-results-table td.boat-col{"\n'
    '    "display:table-cell!important;white-space:nowrap!important;min-width:max-content}"'
)

WRAP_OLD = (
    '".fleet-section .table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}"'
)
WRAP_NEW = (
    '".fleet-section .table-wrapper{overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;'
    'touch-action:pan-x pinch-zoom;overscroll-behavior-x:contain}"'
)


def main() -> None:
    api = API.read_text()
    if MARK in api and CREW_NEW in api and HIDE_NEW in api:
        print("API_ALREADY", MARK)
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.midmar_std_cols.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)

    missing = []
    for name, old in (
        ("CREW", CREW_OLD),
        ("BOW_TH", BOW_TH_OLD),
        ("BOAT_TH", BOAT_TH_OLD),
        ("BOW_TD", BOW_TD_OLD),
        ("BOAT_TD", BOAT_TD_OLD),
        ("HIDE", HIDE_OLD),
        ("WRAP", WRAP_OLD),
    ):
        n = api.count(old)
        print("COUNT", name, n)
        if n != 1:
            missing.append(f"{name}:{n}")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))

    api = api.replace(CREW_OLD, CREW_NEW, 1)
    api = api.replace(BOW_TH_OLD, BOW_TH_NEW, 1)
    api = api.replace(BOAT_TH_OLD, BOAT_TH_NEW, 1)
    api = api.replace(BOW_TD_OLD, BOW_TD_NEW, 1)
    api = api.replace(BOAT_TD_OLD, BOAT_TD_NEW, 1)
    api = api.replace(HIDE_OLD, HIDE_NEW, 1)
    api = api.replace(WRAP_OLD, WRAP_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK, RID)


if __name__ == "__main__":
    main()
