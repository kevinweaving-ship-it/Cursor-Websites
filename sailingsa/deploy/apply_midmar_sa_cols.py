#!/usr/bin/env python3
"""Midmar SA: per-column public hide/show. Default all ticked (show all). No WC fleet edit."""
from pathlib import Path
import json
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_SA_COLS_v1"
RID = "2026-09-19-hmyc-midmar-cup"
KEYS = (
    "rank",
    "fleet",
    "class",
    "category",
    "sail_no",
    "boat_name",
    "jib",
    "bow",
    "hull",
    "club",
    "helm",
    "crew",
    "race_scores",
    "total",
    "nett",
)


def _write_show_all_prefs() -> None:
    show_all = {k: True for k in KEYS}
    paths = [
        Path("/var/www/sailingsa/frontend/data/wc_regatta_column_prefs.json"),
        Path("/var/www/sailingsa/api/static/data/wc_regatta_column_prefs.json"),
        Path("/var/www/sailingsa/static/data/wc_regatta_column_prefs.json"),
        Path("/var/www/sailingsa/sailingsa/frontend/data/wc_regatta_column_prefs.json"),
    ]
    for cand in paths:
        raw = {}
        if cand.is_file():
            try:
                raw = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        if not isinstance(raw, dict):
            raw = {}
        raw[RID] = dict(show_all)
        cand.parent.mkdir(parents=True, exist_ok=True)
        cand.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("PREFS_ALL_ON", cand)


USE_OLD = "        use_wc_cols = _regatta_slug_is_sa_pilot_standalone(str(regatta_id))\n"
USE_NEW = (
    "        use_wc_cols = _regatta_slug_is_sa_pilot_standalone(str(regatta_id))\n"
    "        use_col_prefs = bool(use_wc_cols) or str(regatta_id).strip() == _midmar_cup_rid()  # MIDMAR_SA_COLS_v1\n"
)

PREFS_OLD = "        wc_prefs = _merge_wc_column_prefs_for_regatta(str(regatta_id)) if use_wc_cols else None\n"
PREFS_NEW = "        wc_prefs = _merge_wc_column_prefs_for_regatta(str(regatta_id)) if use_col_prefs else None\n"

PANEL_IF_OLD = (
    "        if use_wc_cols and is_sa:\n"
    "            sa_columns_frag = _wc_regatta_sa_columns_panel_html(str(regatta_id), wc_prefs)\n"
)
PANEL_IF_NEW = (
    "        if use_col_prefs and is_sa:\n"
    "            sa_columns_frag = _wc_regatta_sa_columns_panel_html(str(regatta_id), wc_prefs)\n"
)

COL_OLD = "column_prefs=wc_prefs if use_wc_cols else None,"
COL_NEW = "column_prefs=wc_prefs if use_col_prefs else None,"

FORCE_OLD = '''        show_boat = True
        show_bow = False
        show_crew_col = True
'''
FORCE_NEW = '''        show_boat = _pref_on("boat_name")
        show_bow = False
        show_crew_col = _pref_on("crew")
'''

CREW_ON_OLD = '''def _midmar_crew_public_on() -> bool:
    raw = _read_wc_regatta_column_prefs_raw().get(_midmar_cup_rid())
    if not isinstance(raw, dict) or "crew" not in raw:
        return False
    return bool(raw["crew"])
'''
CREW_ON_NEW = '''def _midmar_crew_public_on() -> bool:
    raw = _read_wc_regatta_column_prefs_raw().get(_midmar_cup_rid())
    if not isinstance(raw, dict) or "crew" not in raw:
        return True
    return bool(raw["crew"])
'''

LABELS_OLD = '''        ("nett", "Nett"),
    )
    parts = [
'''
LABELS_NEW = '''        ("nett", "Nett"),
    )
    if str(regatta_id).strip() == _midmar_cup_rid():
        labels = (
            ("rank", "Rank"),
            ("sail_no", "Sail No"),
            ("boat_name", "Boat Name"),
            ("club", "Club"),
            ("helm", "Helm"),
            ("crew", "Crew"),
            ("race_scores", "Race scores (R1…)"),
            ("total", "Total"),
            ("nett", "Nett"),
        )
    parts = [
'''


def main() -> None:
    text = API.read_text()
    if MARK in text:
        print("ALREADY", MARK)
        _write_show_all_prefs()
        return
    checks = [
        (USE_OLD, 2, "USE"),
        (PREFS_OLD, 2, "PREFS"),
        (PANEL_IF_OLD, 2, "PANEL_IF"),
        (COL_OLD, 2, "COL"),
        (FORCE_OLD, 1, "FORCE"),
        (CREW_ON_OLD, 1, "CREW"),
        (LABELS_OLD, 1, "LABELS"),
    ]
    for s, n, name in checks:
        c = text.count(s)
        if c != n:
            raise SystemExit(f"ANCHOR_{name}_{c}")
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.sa_cols.{ts}"))
    text = text.replace(USE_OLD, USE_NEW)
    text = text.replace(PREFS_OLD, PREFS_NEW)
    text = text.replace(PANEL_IF_OLD, PANEL_IF_NEW)
    text = text.replace(COL_OLD, COL_NEW)
    text = text.replace(FORCE_OLD, FORCE_NEW, 1)
    text = text.replace(CREW_ON_OLD, CREW_ON_NEW, 1)
    text = text.replace(LABELS_OLD, LABELS_NEW, 1)
    API.write_text(text)
    _write_show_all_prefs()
    print("OK", MARK)


if __name__ == "__main__":
    main()
