#!/usr/bin/env python3
"""Surgical live api.py patch: Cape Classic fleet header + class/club row logos.

Marker: CC_FLEET_CLASS_LOGOS_v1
Never overwrite live api.py with the repo copy.

This Cape Classic only (2026-09-13-zvyc-cape-classic and fleet children):
- Single-class fleet with a class logo: header is logo + 'Fleet' (no '420 Fleet').
- Mixed fleets (Open) keep 'Open Fleet'; Class column shows the boat class.
- Class column: small class logo left of class name.
- Club column: small club logo left of club code (same pattern, no taller rows).
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "CC_FLEET_CLASS_LOGOS_v1"

OLD_ART = """    elif css == \"rs-club-row-logo\":
        _img_style = (
            'style=\"height:32px;width:48px;max-height:32px;max-width:48px;'
            'object-fit:contain;object-position:center;display:block;vertical-align:middle;flex:0 0 48px\" '
        )
"""

NEW_ART = """    elif css == \"rs-club-row-logo\":
        _img_style = (
            'style=\"height:32px;width:48px;max-height:32px;max-width:48px;'
            'object-fit:contain;object-position:center;display:block;vertical-align:middle;flex:0 0 48px\" '
        )
    elif css in (\"rs-club-row-logo-sm\", \"rs-class-row-logo\"):
        # Compact cap — never a fixed height that expands the rank row.
        _img_style = (
            'style=\"height:auto;width:auto;max-height:16px;max-width:28px;'
            'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto\" '
        )
"""

OLD_CLUBFN = '''def _fleet_sheet_club_cell_with_logo_html(club_link_html: str, club_raw: str) -> str:
    """Club logo left, club code right. Codes share one start edge."""
    code = _fleet_sheet_club_logo_code(club_raw)
    logo_u = _club_logo_public_url(code) if code else ""
    if code == "ZVSC":
        logo_u = "/api/club-logo/ZVSC"
    if not club_link_html:
        return ""
    if not logo_u:
        return club_link_html
    img = _fleet_sheet_artwork_img(logo_u, code, "rs-club-row-logo")
    if not img:
        return club_link_html
    return f'<span class="rs-club-with-logo">{img}{club_link_html}</span>'
'''

NEW_CLUBFN = '''def _is_cape_classic_2026_zvy_event(regatta_id) -> bool:
    """This Cape Classic only (2026-09-13 ZVYC) — parent and fleet children."""
    # ''' + MARKER + '''
    try:
        from sailingsa.backend.cape_classic_fleet_sheet import is_cape_classic_2026_zvy_event
        return is_cape_classic_2026_zvy_event(regatta_id)
    except Exception:
        s = str(regatta_id or "").strip().lower()
        return s == "2026-09-13-zvyc-cape-classic" or s.startswith("2026-09-13-zvyc-cape-classic-")


def _fleet_sheet_club_cell_with_logo_html(
    club_link_html: str, club_raw: str, compact: bool = False
) -> str:
    """Club logo left, club code right. Codes share one start edge."""
    code = _fleet_sheet_club_logo_code(club_raw)
    logo_u = _club_logo_public_url(code) if code else ""
    if code == "ZVSC":
        logo_u = "/api/club-logo/ZVSC"
    if not club_link_html:
        return ""
    if not logo_u:
        return club_link_html
    css = "rs-club-row-logo-sm" if compact else "rs-club-row-logo"
    img = _fleet_sheet_artwork_img(logo_u, code, css)
    if not img:
        return club_link_html
    return f'<span class="rs-club-with-logo">{img}{club_link_html}</span>'


def _fleet_sheet_class_cell_with_logo_html(class_link_html: str, class_raw: str) -> str:
    """Class logo left, class name right. Small cap — never grow row height."""
    if not class_link_html:
        return ""
    cn = str(class_raw or "").strip()
    logo_u = ""
    if cn:
        try:
            logo_u = (_catalogue_logo_path_for_class_name(cn) or "").strip()
        except Exception:
            logo_u = ""
    if not logo_u:
        return class_link_html
    img = _fleet_sheet_artwork_img(logo_u, cn, "rs-class-row-logo")
    if not img:
        return class_link_html
    return f'<span class="rs-class-with-logo">{img}{class_link_html}</span>'
'''

OLD_TITLE = '''    if _regatta_slug_is_sa_pilot_standalone(_rid_ft):
        fleet_header_title = _collapse_duplicate_fleet_word(_wc_dinghy_fleet_title_display(fleet_header_title))
    else:
        fleet_header_title = _collapse_duplicate_fleet_word(fleet_header_title)
    fleet_title_inner = fleet_header_title
'''

NEW_TITLE = '''    if _regatta_slug_is_sa_pilot_standalone(_rid_ft):
        fleet_header_title = _collapse_duplicate_fleet_word(_wc_dinghy_fleet_title_display(fleet_header_title))
    else:
        fleet_header_title = _collapse_duplicate_fleet_word(fleet_header_title)
    if _is_cape_classic_2026_zvy_event(_rid_ft) and not standalone_class_page:
        _cc_names = {
            str(r.get("class_name") or "").strip()
            for r in (fleet.get("rows") or [])
            if str(r.get("class_name") or "").strip()
        }
        _cc_core = re.sub(r"(?i)\\s+fleet$", "", str(fleet_header_title or "")).strip()
        _cc_logo = ""
        if len(_cc_names) <= 1:
            try:
                _cc_logo = (
                    _catalogue_logo_path_for_class_name(
                        _cc_core or class_canonical or fleet_label
                    )
                    or ""
                ).strip()
                if not _cc_logo and _cc_names:
                    _cc_logo = (
                        _catalogue_logo_path_for_class_name(next(iter(_cc_names))) or ""
                    ).strip()
            except Exception:
                _cc_logo = ""
            try:
                from sailingsa.backend.cape_classic_fleet_sheet import (
                    fleet_header_title_without_class_dup,
                )
                fleet_header_title = fleet_header_title_without_class_dup(
                    fleet_header_title,
                    unique_classes=_cc_names,
                    has_class_logo=bool(_cc_logo),
                )
            except Exception:
                if _cc_logo and _cc_core.casefold() not in ("staff", "event staff", "crew"):
                    fleet_header_title = "Fleet"
    fleet_title_inner = fleet_header_title
'''

OLD_SHOWC = '''    show_class_col = _pref_on("class") and ("lipton" not in str(_rid_ft or "").strip().lower())
'''

NEW_SHOWC = '''    show_class_col = _pref_on("class") and ("lipton" not in str(_rid_ft or "").strip().lower())
    if _is_cape_classic_2026_zvy_event(_rid_ft):
        show_class_col = True
'''

OLD_CLASS_STR = '''        else:
            class_str = ""
        sail_raw = str(r.get("sail_number") or "")
'''

NEW_CLASS_STR = '''        else:
            class_str = ""
        if _is_cape_classic_2026_zvy_event(_rid_ft) and class_str:
            class_str = _fleet_sheet_class_cell_with_logo_html(class_str, class_display_raw)
        sail_raw = str(r.get("sail_number") or "")
'''

OLD_CLUBCALL = '''            club_disp = _fleet_sheet_club_cell_with_logo_html(club_link_html, club_raw)
'''

NEW_CLUBCALL = '''            club_disp = _fleet_sheet_club_cell_with_logo_html(
                club_link_html, club_raw, compact=_is_cape_classic_2026_zvy_event(_rid_ft)
            )
'''

OLD_TABLE = '''    table_html = f'<table class="fleet-results-table"><thead><tr>{thead}</tr></thead><tbody>{"".join(trs)}</tbody></table>'
'''

NEW_TABLE = '''    _tbl_cls = "fleet-results-table"
    if _is_cape_classic_2026_zvy_event(_rid_ft):
        _tbl_cls += " rs-compact-row-logos"
    table_html = f'<table class="{_tbl_cls}"><thead><tr>{thead}</tr></thead><tbody>{"".join(trs)}</tbody></table>'
'''

OLD_CSS1 = '''    ".fleet-results-table td.club-col{white-space:nowrap;overflow:visible}"
'''

NEW_CSS1 = '''    ".fleet-results-table td.club-col{white-space:nowrap;overflow:visible}"
    ".fleet-results-table .rs-class-with-logo{display:inline-flex!important;flex-direction:row!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px;max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"
    ".fleet-results-table .rs-class-row-logo,.fleet-results-table .rs-club-row-logo-sm{display:inline-block!important;height:auto!important;width:auto!important;max-height:16px!important;max-width:28px!important;object-fit:contain!important;object-position:center!important;vertical-align:middle;flex:0 0 auto!important}"
    ".fleet-results-table td.class-col{white-space:nowrap;overflow:visible}"
'''

OLD_CSS2 = '''    ".fleet-results-table .rs-club-row-logo{height:32px!important;width:48px!important;max-height:32px!important;max-width:48px!important;object-fit:contain!important;object-position:center!important;display:block!important;flex:0 0 48px!important}"
    ".fleet-results-table .rs-club-with-logo>a,.fleet-results-table .rs-club-with-logo>span{display:inline-block!important;min-width:0;text-align:left}"
'''

NEW_CSS2 = '''    ".fleet-results-table .rs-club-row-logo{height:32px!important;width:48px!important;max-height:32px!important;max-width:48px!important;object-fit:contain!important;object-position:center!important;display:block!important;flex:0 0 48px!important}"
    ".fleet-results-table .rs-class-row-logo,.fleet-results-table .rs-club-row-logo-sm{height:auto!important;width:auto!important;max-height:16px!important;max-width:28px!important;object-fit:contain!important;display:inline-block!important;flex:0 0 auto!important}"
    ".fleet-results-table .rs-class-with-logo{display:inline-flex!important;flex-direction:row!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px;white-space:nowrap!important}"
    ".fleet-results-table .rs-club-with-logo>a,.fleet-results-table .rs-club-with-logo>span{display:inline-block!important;min-width:0;text-align:left}"
'''


MARKER2 = "CC_FLEET_CLASS_LOGOS_v2"

OLD_IMG_ALT = '''    return (
        f'<img class="{html_module.escape(css)}" src="{html_module.escape(src_raw)}" '
        f'alt="{html_module.escape(alt)}" title="{html_module.escape(alt)}" '
        f"{_img_style}"
        f'loading="lazy" decoding="async">'
    )
'''

NEW_IMG_ALT = '''    _alt_out = "" if css in ("rs-club-row-logo-sm", "rs-class-row-logo") else alt
    return (
        f'<img class="{html_module.escape(css)}" src="{html_module.escape(src_raw)}" '
        f'alt="{html_module.escape(_alt_out)}" title="{html_module.escape(alt)}" '
        f"{_img_style}"
        f'loading="lazy" decoding="async">'
    )
    # ''' + "CC_FLEET_CLASS_LOGOS_v2" + '''
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER not in text:
        replacements = [
            ("art", OLD_ART, NEW_ART),
            ("clubfn", OLD_CLUBFN, NEW_CLUBFN),
            ("title", OLD_TITLE, NEW_TITLE),
            ("showc", OLD_SHOWC, NEW_SHOWC),
            ("class_str", OLD_CLASS_STR, NEW_CLASS_STR),
            ("clubcall", OLD_CLUBCALL, NEW_CLUBCALL),
            ("table", OLD_TABLE, NEW_TABLE),
            ("css1", OLD_CSS1, NEW_CSS1),
            ("css2", OLD_CSS2, NEW_CSS2),
        ]
        missing = [name for name, old, _ in replacements if old not in text]
        if missing:
            raise SystemExit("missing blocks: " + ",".join(missing))
        for name, old, new in replacements:
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"{name} count={n}")
            text = text.replace(old, new, 1)
            print("replaced", name)
        if MARKER not in text:
            raise SystemExit("marker failed")
    else:
        print("already patched v1")

    if MARKER2 not in text:
        n = text.count(OLD_IMG_ALT)
        if n != 1:
            raise SystemExit(f"img alt count={n}")
        text = text.replace(OLD_IMG_ALT, NEW_IMG_ALT, 1)
        print("replaced img alt")
        if MARKER2 not in text:
            raise SystemExit("v2 marker failed")
    else:
        print("already patched v2")

    MARKER3 = "CC_FLEET_CLASS_LOGOS_v3"
    if MARKER3 not in text:
        old_cls = '''def _fleet_sheet_class_cell_with_logo_html(class_link_html: str, class_raw: str) -> str:
    """Class logo left, class name right. Small cap — never grow row height."""
    if not class_link_html:
        return ""
    cn = str(class_raw or "").strip()
    logo_u = ""
    if cn:
        try:
            logo_u = (_catalogue_logo_path_for_class_name(cn) or "").strip()
        except Exception:
            logo_u = ""
    if not logo_u:
        return class_link_html
    img = _fleet_sheet_artwork_img(logo_u, cn, "rs-class-row-logo")
    if not img:
        return class_link_html
    return f'<span class="rs-class-with-logo">{img}{class_link_html}</span>'
'''
        new_cls = '''def _fleet_sheet_class_cell_with_logo_html(class_link_html: str, class_raw: str) -> str:
    """Class logo stands in for the class name when present (same as fleet header)."""
    # ''' + "CC_FLEET_CLASS_LOGOS_v3" + '''
    if not class_link_html:
        return ""
    cn = str(class_raw or "").strip()
    logo_u = ""
    if cn:
        try:
            logo_u = (_catalogue_logo_path_for_class_name(cn) or "").strip()
        except Exception:
            logo_u = ""
    if not logo_u:
        return class_link_html
    img = _fleet_sheet_artwork_img(logo_u, cn, "rs-class-row-logo")
    if not img:
        return class_link_html
    try:
        from sailingsa.backend.cape_classic_fleet_sheet import class_link_html_logo_only
        return class_link_html_logo_only(class_link_html, img, cn)
    except Exception:
        m = re.match(r"(?is)(<a\\s[^>]*>).*?(</a>)\\s*$", class_link_html.strip())
        if m:
            return f'<span class="rs-class-with-logo">{m.group(1)}{img}{m.group(2)}</span>'
        return f'<span class="rs-class-with-logo">{img}</span>'
'''
        if old_cls not in text:
            raise SystemExit("class cell fn missing")
        if text.count(old_cls) != 1:
            raise SystemExit("class cell fn count")
        text = text.replace(old_cls, new_cls, 1)
        old_alt = '''    _alt_out = "" if css in ("rs-club-row-logo-sm", "rs-class-row-logo") else alt
'''
        new_alt = '''    _alt_out = "" if css == "rs-club-row-logo-sm" else alt
'''
        if old_alt not in text:
            raise SystemExit("class alt branch missing")
        text = text.replace(old_alt, new_alt, 1)
        print("replaced class cell logo-only")
        if MARKER3 not in text:
            raise SystemExit("v3 marker failed")
    else:
        print("already patched v3")

    API.write_text(text, encoding="utf-8")
    print("PATCHED", API, "bytes", API.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
