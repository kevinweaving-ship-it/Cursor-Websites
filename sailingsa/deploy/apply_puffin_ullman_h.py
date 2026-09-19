#!/usr/bin/env python3
"""Make Puffin logo the same 22px height as Ullman. Crop SVG + lock height."""
from pathlib import Path
import shutil

API = Path("/var/www/sailingsa/api/api.py")
ART = Path("/var/www/sailingsa/artwork/Sponsor Logo/Puffin.svg")
MARK = "MIDMAR_PUFFIN_H22_v1"

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 12 38 40" width="22" height="22">
  <ellipse cx="30" cy="36" rx="16" ry="14" fill="#f4f4f4"/>
  <circle cx="28" cy="24" r="11" fill="#1a1a1a"/>
  <circle cx="24" cy="21" r="3.2" fill="#fff"/>
  <circle cx="23.3" cy="20.6" r="1.5" fill="#111"/>
  <path d="M36 22c8 1 14 6 16 11-6 1-12-2-16-7z" fill="#f59e0b"/>
  <path d="M36 26c6 2 11 6 12 9-5 0-9-2-12-6z" fill="#ef4444"/>
</svg>
'''

CSS_OLD = (
    '    ".fleet-results-table td.boat-col .rs-boat-logo-right,'
    ".midmar-lb .rs-boat-logo-right{flex:0 0 22px!important;width:22px!important;"
    "max-width:22px!important;height:22px!important;object-fit:contain!important;"
    "box-sizing:content-box!important;padding-left:4px!important;margin-left:4px!important;"
    "padding-right:0!important;margin-right:0!important;"
    'border-right:0!important;border-left:1px solid rgba(26,39,80,0.22)!important}"\n'
)
CSS_NEW = (
    '    ".fleet-results-table td.boat-col .rs-boat-logo-right,'
    ".midmar-lb .rs-boat-logo-right{flex:0 0 22px!important;width:22px!important;"
    "height:22px!important;max-width:22px!important;max-height:22px!important;"
    "object-fit:contain!important;"
    "box-sizing:content-box!important;padding-left:4px!important;margin-left:4px!important;"
    "padding-right:0!important;margin-right:0!important;"
    'border-right:0!important;border-left:1px solid rgba(26,39,80,0.22)!important}"  # MIDMAR_PUFFIN_H22_v1\n'
)

# Also make Ullman in boat-col use explicit 22px height so both match.
ULLMAN_OLD = (
    ".fleet-results-table td.boat-col .rs-club-row-logo-sm{flex:0 0 22px!important;"
    "width:22px!important;max-width:22px!important;object-fit:contain!important;"
)
ULLMAN_NEW = (
    ".fleet-results-table td.boat-col .rs-club-row-logo-sm{flex:0 0 22px!important;"
    "width:22px!important;height:22px!important;max-width:22px!important;"
    "max-height:22px!important;object-fit:contain!important;"
)


def main() -> None:
    ART.write_text(SVG)
    ART.chmod(0o644)
    print("SVG", ART.stat().st_size)

    api = API.read_text()
    if MARK in api:
        print("API_ALREADY")
        return
    if CSS_OLD in api:
        api = api.replace(CSS_OLD, CSS_NEW, 1)
        print("CSS_RIGHT")
    elif "rs-boat-logo-right{" in api:
        i = api.find("rs-boat-logo-right{")
        print("CSS_RIGHT_OTHER", api[i : i + 220])
    else:
        key = "td.boat-col .rs-club-row-logo-sm"
        i = api.find(key)
        if i < 0:
            raise SystemExit("ANCHOR_RIGHT_CSS")
        end = api.find('}"', i)
        if end < 0:
            raise SystemExit("ANCHOR_CSS_END")
        insert_at = end + 2
        if insert_at < len(api) and api[insert_at] == "\n":
            insert_at += 1
        api = api[:insert_at] + CSS_NEW + api[insert_at:]
        print("CSS_RIGHT_INSERTED")
    if ULLMAN_OLD in api:
        api = api.replace(ULLMAN_OLD, ULLMAN_NEW, 1)
        print("CSS_ULLMAN")
    api = api.replace("/artwork/Sponsor Logo/Puffin.svg", "/artwork/Sponsor Logo/Puffin.svg?v=h22", 1)
    API.write_text(api)
    print("OK", MARK)


if __name__ == "__main__":
    main()
