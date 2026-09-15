#!/usr/bin/env python3
"""Live api.py: never put scoring in fleet titles; Class==Fleet uses '{Class} Fleet'.

Run on the server against /var/www/sailingsa/api/api.py.
Does not change mixed-fleet names. Scoring stays on the sailed line only.
"""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''
_FLEET_TITLE_SCORING_TAIL_RE = re.compile(
    r"\\s*[—–-]\\s*(?:"
    r"ToT(?:\\s*-\\s*Custom)?|"
    r"Appendix\\s*A|"
    r"Low\\s*Point|"
    r"PHRF(?:\\s*TOT)?|"
    r"PCS(?:\\s+\\w+)*|"
    r"Scoring(?:\\s+system)?|"
    r"Rating(?:\\s+system)?"
    r")(?:\\s+Fleet)?\\s*$",
    re.I,
)


def _strip_scoring_system_from_fleet_title(label: Optional[str]) -> str:
    """Never put scoring/rating in a fleet title. Scoring belongs on the sailed line only."""
    s = " ".join(str(label or "").split())
    if not s:
        return ""
    prev = None
    while prev != s:
        prev = s
        s = _FLEET_TITLE_SCORING_TAIL_RE.sub("", s).strip()
    s = re.sub(
        r"(?i)^(?:ToT(?:\\s*-\\s*Custom)?|Appendix\\s*A|Low\\s*Point)(?:\\s+Fleet)?$",
        "",
        s,
    ).strip()
    return s


def _class_and_fleet_names_match(class_name: Optional[str], fleet_name: Optional[str]) -> bool:
    """True when this block is a single class whose name is the fleet name (420 / 420 Fleet)."""
    c = _class_name_core_without_fleet_suffix(class_name)
    f = _class_name_core_without_fleet_suffix(fleet_name)
    if not c or not f:
        return False
    if c.casefold() in _RATING_OR_HANDICAP_FLEET_CORES:
        return False
    return c.casefold() == f.casefold()

'''

ANCHOR_END = '''    return s + " Fleet"


def _wc_dinghy_table_label_open_a_to_open(raw: Optional[str]) -> str:
'''

REPL_END = '''    return s + " Fleet"

''' + HELPER + '''
def _wc_dinghy_table_label_open_a_to_open(raw: Optional[str]) -> str:
'''

TITLE_OLD = '''    _bl_raw_title = (fleet.get("block_label_raw") or "").strip()
    _bl_norm = re.sub(r"\\s+", " ", _bl_raw_title.lower()).strip()
    if _bl_norm in _GENERIC_BLOCK_TITLES and (fleet_label or class_canonical):
        _bl_raw_title = ""
    if _bl_raw_title:
        # Keep numbered prefix in DB for sort; bar title is unnumbered (420 lesson).
        _display_raw_title = _strip_numbered_block_label_prefix(_bl_raw_title) or _bl_raw_title
        if standalone_class_page:
            fleet_header_title = _collapse_duplicate_fleet_word(_display_raw_title)
        else:
            fleet_header_title = _ensure_single_trailing_fleet(_display_raw_title)
    elif standalone_class_page:
        base = (fleet_label or class_canonical or fname).strip()
        fleet_header_title = re.sub(r"(?i)\\s+fleet$", "", _collapse_duplicate_fleet_word(base)).strip() or "Results"
    elif fname == "Fleet" and (fleet_label or class_canonical):
        fleet_header_title = _ensure_single_trailing_fleet(fleet_label or class_canonical)
    elif re.search(r"(?i)\\bfleet$", fname) or fname == "Fleet" or re.search(r"\\bUnder\\s+\\d+\\b", fname, re.I):
        fleet_header_title = _collapse_duplicate_fleet_word(fname)
    else:
        fleet_header_title = _ensure_single_trailing_fleet(fname)
    if _regatta_slug_is_sa_pilot_standalone(_rid_ft):
'''

TITLE_NEW = '''    _bl_raw_title = _strip_scoring_system_from_fleet_title(fleet.get("block_label_raw") or "")
    _bl_norm = re.sub(r"\\s+", " ", _bl_raw_title.lower()).strip()
    if _bl_norm in _GENERIC_BLOCK_TITLES and (fleet_label or class_canonical):
        _bl_raw_title = ""
    if _bl_raw_title:
        # Keep numbered prefix in DB for sort; bar title is unnumbered (420 lesson).
        _display_raw_title = _strip_numbered_block_label_prefix(_bl_raw_title) or _bl_raw_title
        _display_raw_title = _strip_scoring_system_from_fleet_title(_display_raw_title) or _display_raw_title
        if standalone_class_page:
            fleet_header_title = _collapse_duplicate_fleet_word(_display_raw_title)
        else:
            fleet_header_title = _ensure_single_trailing_fleet(_display_raw_title)
    elif standalone_class_page:
        base = (fleet_label or class_canonical or fname).strip()
        fleet_header_title = re.sub(r"(?i)\\s+fleet$", "", _collapse_duplicate_fleet_word(base)).strip() or "Results"
    elif fname == "Fleet" and (fleet_label or class_canonical):
        fleet_header_title = _ensure_single_trailing_fleet(fleet_label or class_canonical)
    elif re.search(r"(?i)\\bfleet$", fname) or fname == "Fleet" or re.search(r"\\bUnder\\s+\\d+\\b", fname, re.I):
        fleet_header_title = _collapse_duplicate_fleet_word(fname)
    else:
        fleet_header_title = _ensure_single_trailing_fleet(fname)
    _title_stripped = _strip_scoring_system_from_fleet_title(fleet_header_title)
    if _title_stripped:
        fleet_header_title = _title_stripped
    elif fleet_label or class_canonical:
        fleet_header_title = _ensure_single_trailing_fleet(fleet_label or class_canonical)
    # Class == fleet (420 / 420 Fleet): centre title is "{Class} Fleet". Mixed names stay as stored.
    if not standalone_class_page:
        _match_class = class_canonical or (fleet.get("class_original") or "")
        if _class_and_fleet_names_match(_match_class, fleet_label or fleet_header_title):
            _core = _class_name_core_without_fleet_suffix(_match_class)
            if _core:
                fleet_header_title = _ensure_single_trailing_fleet(_core)
    if _regatta_slug_is_sa_pilot_standalone(_rid_ft):
'''


def _self_test() -> None:
    def strip_fn(label: str) -> str:
        s = " ".join(str(label or "").split())
        tail = re.compile(
            r"\s*[—–-]\s*(?:"
            r"ToT(?:\s*-\s*Custom)?|"
            r"Appendix\s*A|"
            r"Low\s*Point|"
            r"PHRF(?:\s*TOT)?|"
            r"PCS(?:\s+\w+)*|"
            r"Scoring(?:\s+system)?|"
            r"Rating(?:\s+system)?"
            r")(?:\s+Fleet)?\s*$",
            re.I,
        )
        prev = None
        while prev != s:
            prev = s
            s = tail.sub("", s).strip()
        s = re.sub(
            r"(?i)^(?:ToT(?:\s*-\s*Custom)?|Appendix\s*A|Low\s*Point)(?:\s+Fleet)?$",
            "",
            s,
        ).strip()
        return s

    cases = {
        "Hobie Fleet — ToT - Custom": "Hobie Fleet",
        "Hunter 19 Fleet — ToT - Custom": "Hunter 19 Fleet",
        "Keelboats — ToT - Custom": "Keelboats",
        "420 Fleet": "420 Fleet",
        "Open A Fleet": "Open A Fleet",
        "Hobie Fleet — ToT - Custom Fleet": "Hobie Fleet",
        "Appendix A": "",
        "ToT - Custom Fleet": "",
    }
    for raw, exp in cases.items():
        got = strip_fn(raw)
        assert got == exp, (raw, got, exp)
    print("SELFTEST_OK")


def main() -> None:
    _self_test()
    text = API.read_text()
    if "_strip_scoring_system_from_fleet_title" in text:
        print("ALREADY_PATCHED")
        return

    helper_mark = '    return s + " Fleet"'
    dinghy_mark = "def _wc_dinghy_table_label_open_a_to_open(raw: Optional[str]) -> str:"
    hi = text.find(helper_mark)
    di = text.find(dinghy_mark, hi)
    if hi < 0 or di < 0 or di - hi > 80:
        raise SystemExit("ANCHOR_HELPER_MISSING")
    insert_at = text.rfind("\n", 0, di)
    text = text[:insert_at] + "\n" + HELPER + text[insert_at:]

    old_assign = '    _bl_raw_title = (fleet.get("block_label_raw") or "").strip()'
    new_assign = '    _bl_raw_title = _strip_scoring_system_from_fleet_title(fleet.get("block_label_raw") or "")'
    if old_assign not in text:
        raise SystemExit("ANCHOR_TITLE_ASSIGN_MISSING")
    text = text.replace(old_assign, new_assign, 1)

    old_display = (
        "        _display_raw_title = _strip_numbered_block_label_prefix(_bl_raw_title) or _bl_raw_title\n"
        "        if standalone_class_page:"
    )
    new_display = (
        "        _display_raw_title = _strip_numbered_block_label_prefix(_bl_raw_title) or _bl_raw_title\n"
        "        _display_raw_title = _strip_scoring_system_from_fleet_title(_display_raw_title) or _display_raw_title\n"
        "        if standalone_class_page:"
    )
    if old_display not in text:
        raise SystemExit("ANCHOR_DISPLAY_MISSING")
    text = text.replace(old_display, new_display, 1)

    old_tail = (
        "        fleet_header_title = _ensure_single_trailing_fleet(fname)\n"
        "    if _regatta_slug_is_sa_pilot_standalone(_rid_ft):"
    )
    new_tail = (
        "        fleet_header_title = _ensure_single_trailing_fleet(fname)\n"
        "    _title_stripped = _strip_scoring_system_from_fleet_title(fleet_header_title)\n"
        "    if _title_stripped:\n"
        "        fleet_header_title = _title_stripped\n"
        "    elif fleet_label or class_canonical:\n"
        "        fleet_header_title = _ensure_single_trailing_fleet(fleet_label or class_canonical)\n"
        "    # Class == fleet (420 / 420 Fleet): centre title is \"{Class} Fleet\". Mixed names stay as stored.\n"
        "    if not standalone_class_page:\n"
        "        _match_class = class_canonical or (fleet.get(\"class_original\") or \"\")\n"
        "        if _class_and_fleet_names_match(_match_class, fleet_label or fleet_header_title):\n"
        "            _core = _class_name_core_without_fleet_suffix(_match_class)\n"
        "            if _core:\n"
        "                fleet_header_title = _ensure_single_trailing_fleet(_core)\n"
        "    if _regatta_slug_is_sa_pilot_standalone(_rid_ft):"
    )
    if old_tail not in text:
        raise SystemExit("ANCHOR_TITLE_TAIL_MISSING")
    text = text.replace(old_tail, new_tail, 1)

    if text.count("_strip_scoring_system_from_fleet_title") < 3:
        raise SystemExit("PATCH_FAILED")

    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.fleet_title.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    API.write_text(text)
    print("PATCHED", API)


if __name__ == "__main__":
    main()
