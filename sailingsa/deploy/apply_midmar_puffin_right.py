#!/usr/bin/env python3
"""Puffin boat: Ullman left | name | Puffin logo right, same 22px size."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
ART = Path("/var/www/sailingsa/artwork/Sponsor Logo")
MARK = "MIDMAR_PUFFIN_RIGHT_v1"

BOAT_OLD = '''    if low == "puffin":
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
'''

BOAT_NEW = '''    if low == "puffin":
        img = _fleet_sheet_artwork_img(
            "/artwork/Sponsor Logo/Ullman-Sails.png",
            "Ullman Sails",
            "rs-club-row-logo-sm",
        )
        puffin_img = _fleet_sheet_artwork_img(
            "/artwork/Sponsor Logo/Puffin.svg",
            "Puffin",
            "rs-club-row-logo-sm rs-boat-logo-right",
        )
        href = "/sponsors/ullman"
        name_link = f'<a href="{href}" title="Ullman Sails">{html_module.escape(bn)}</a>'
        bits = "".join(x for x in (img, name_link, puffin_img) if x)
        if img or puffin_img:
            return f'<span class="rs-club-with-logo">{bits}</span>'  # MIDMAR_PUFFIN_RIGHT_v1
        return name_link
'''

CSS_ADD = (
    '    ".fleet-results-table td.boat-col .rs-boat-logo-right,'
    ".midmar-lb .rs-boat-logo-right{flex:0 0 22px!important;width:22px!important;"
    "max-width:22px!important;height:22px!important;object-fit:contain!important;"
    "box-sizing:content-box!important;padding-left:4px!important;margin-left:4px!important;"
    "padding-right:0!important;margin-right:0!important;"
    'border-right:0!important;border-left:1px solid rgba(26,39,80,0.22)!important}"\n'
)

CHIP_OLD = "    return '<span class=\"rs-club-with-logo\">' + img + text + '</span>';\n"
CHIP_NEW = (
    "    var right='';\n"
    "    if(rightSrc){right='<img class=\"rs-club-row-logo-sm rs-boat-logo-right\" src=\"'+rightSrc+'\" alt=\"\" title=\"'+esc(rightTitle||'')+'\" loading=\"lazy\" decoding=\"async\">';}\n"
    "    return '<span class=\"rs-club-with-logo\">' + img + text + right + '</span>';\n"
)

FN_OLD = "  function logoChip(src, title, href, label, logoHref) {\n"
FN_NEW = "  function logoChip(src, title, href, label, logoHref, rightSrc, rightTitle) {\n"

SP_OLD = "    { test: function (n) { return n === 'puffin'; }, file: 'Ullman-Sails.png', alt: 'Ullman Sails', href: '/sponsors/ullman' },\n"
SP_NEW = "    { test: function (n) { return n === 'puffin'; }, file: 'Ullman-Sails.png', alt: 'Ullman Sails', href: '/sponsors/ullman', rightFile: 'Puffin.svg', rightAlt: 'Puffin' },\n"

BH_OLD = (
    "          '/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.file) + '?v=20260912c',\n"
    "          sp.alt,\n"
    "          href,\n"
    "          bn,\n"
    "          sp.href\n"
)
BH_NEW = (
    "          '/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.file) + '?v=20260919p',\n"
    "          sp.alt,\n"
    "          href,\n"
    "          bn,\n"
    "          sp.href,\n"
    "          sp.rightFile ? ('/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.rightFile) + '?v=20260919p') : '',\n"
    "          sp.rightAlt || ''\n"
)


def _install_logo() -> None:
    src = Path("/tmp/Puffin.svg")
    ART.mkdir(parents=True, exist_ok=True)
    dest = ART / "Puffin.svg"
    if src.is_file():
        shutil.copy2(src, dest)
        dest.chmod(0o644)
    print("LOGO", dest, dest.is_file(), dest.stat().st_size if dest.is_file() else 0)


def main() -> None:
    _install_logo()
    api = API.read_text()
    if MARK in api:
        print("API_ALREADY")
    else:
        if BOAT_OLD not in api:
            raise SystemExit("ANCHOR_BOAT")
        if "rs-boat-logo-right" not in api:
            key = "td.boat-col .rs-club-row-logo-sm"
            i = api.find(key)
            if i < 0:
                raise SystemExit("ANCHOR_CSS")
            end = api.find('}"', i)
            if end < 0:
                raise SystemExit("ANCHOR_CSS_END")
            insert_at = end + 2
            if insert_at < len(api) and api[insert_at] == "\n":
                insert_at += 1
            api = api[:insert_at] + CSS_ADD + api[insert_at:]
        api = api.replace(BOAT_OLD, BOAT_NEW, 1)
        ts = time.strftime("%Y%m%d_%H%M%S")
        shutil.copy2(API, API.with_name(f"api.py.bak.puffin_right.{ts}"))
        API.write_text(api)
        print("API_OK", MARK)

    js = JS.read_text()
    if "rs-boat-logo-right" in js and "rightFile" in js:
        print("JS_ALREADY")
    else:
        if FN_OLD not in js:
            raise SystemExit("ANCHOR_FN")
        if CHIP_OLD not in js:
            raise SystemExit("ANCHOR_CHIP")
        if SP_OLD not in js:
            raise SystemExit("ANCHOR_SP")
        if BH_OLD not in js:
            raise SystemExit("ANCHOR_BH")
        js = js.replace(FN_OLD, FN_NEW, 1)
        js = js.replace(CHIP_OLD, CHIP_NEW, 1)
        js = js.replace(SP_OLD, SP_NEW, 1)
        js = js.replace(BH_OLD, BH_NEW, 1)
        JS.write_text(js)
        print("JS_OK")
    print("DONE", MARK)


if __name__ == "__main__":
    main()
