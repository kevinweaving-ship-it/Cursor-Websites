#!/usr/bin/env python3
"""Puffin boat name: Ullman sponsor logo | divider | Puffin, link /sponsors/ullman.

Same divider as club logo | club code (rs-club-row-logo-sm border-right).
"""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_PUFFIN_ULLMAN_v1"

BOAT_OLD = '''    bn = str(boat_name or "").strip()
    if not bn:
        return ""
    sail_s = str(sail_number or "").strip()
    low = bn.casefold()
    is_baby_j = (
'''

BOAT_NEW = '''    bn = str(boat_name or "").strip()
    if not bn:
        return ""
    sail_s = str(sail_number or "").strip()
    low = bn.casefold()
    # MIDMAR_PUFFIN_ULLMAN_v1: Ullman logo | divider | Puffin → /sponsors/ullman
    if low == "puffin":
        img = _fleet_sheet_artwork_img(
            "/artwork/Sponsor Logo/Ullman-Sails.png",
            "Ullman Sails",
            "rs-club-row-logo-sm",
        )
        href = "/sponsors/ullman"
        name_link = f'<a href="{href}" title="Ullman Sails">{html_module.escape(bn)}</a>'
        if img:
            # Same chip as club: {logo}{code-link} + border-right divider on the img.
            return f'<span class="rs-club-with-logo">{img}{name_link}</span>'
        return name_link
    is_baby_j = (
'''

CSS_OLD = (
    '".fleet-results-table td.club-col .rs-club-row-logo-sm{flex:0 0 22px!important;'
    "width:22px!important;max-width:22px!important;object-fit:contain!important;"
    "box-sizing:content-box!important;padding-right:4px!important;margin-right:4px!important;"
    'border-right:1px solid rgba(26,39,80,0.22)!important}"'
)

CSS_NEW = (
    '".fleet-results-table td.club-col .rs-club-row-logo-sm,'
    ".fleet-results-table td.boat-col .rs-club-row-logo-sm{flex:0 0 22px!important;"
    "width:22px!important;max-width:22px!important;object-fit:contain!important;"
    "box-sizing:content-box!important;padding-right:4px!important;margin-right:4px!important;"
    'border-right:1px solid rgba(26,39,80,0.22)!important}"'
)


def main() -> None:
    api = API.read_text()
    if MARK in api and "td.boat-col .rs-club-row-logo-sm" in api:
        print("API_ALREADY", MARK)
        return
    if BOAT_OLD not in api:
        raise SystemExit("BOAT_ANCHOR_MISSING")
    if CSS_OLD not in api:
        raise SystemExit("CSS_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.puffin_ullman.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    api = api.replace(BOAT_OLD, BOAT_NEW, 1)
    api = api.replace(CSS_OLD, CSS_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
