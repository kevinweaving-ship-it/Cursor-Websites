#!/usr/bin/env python3
"""Fix OG on Lipton regattas + /classes + /clubs (gold-header inject)."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX6_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

LIPTON_OLD = """        if _is_lipton:
            extra_head = (
                f"<link rel=\\"canonical\\" href=\\"{html_module.escape(canonical_url)}\\">"
                f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
                f"<style>{_RESULT_SHEET_CSS}</style>"
            )
            return _html_with_gold_header(f"{escaped_title} | SailingSA", page_inner, extra_head)"""

LIPTON_NEW = """        if _is_lipton:
            _fb_lipton_head = _fb_og_head_for(
                "regatta",
                str(canonical_slug),
                f"{escaped_title} | SailingSA",
                f"Regatta results: {escaped_title}.",
                canonical_url,
                source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name),
            )
            extra_head = (
                f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
                f"<style>{_RESULT_SHEET_CSS}</style>"
            )
            resp = _html_with_gold_header(f"{escaped_title} | SailingSA", page_inner, extra_head)
            html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
            import facebook_og as _fb
            html = _fb.inject_facebook_head(html, _fb_lipton_head)
            return HTMLResponse(html)"""

CLASSES_OLD = """            extra_head = (
                '<link rel="canonical" href="https://sailingsa.co.za/classes">'
                + _fb_og_head_for('directory', 'classes', 'Classes | SailingSA', about, _canonical_base_url() + '/classes', source_url='/assets/logos/sailingsa-logo.png')
                + "<style>" + _directory_logo_grid_extra_css() + ccd.classes_directory_extra_css() + "</style>"
            )
            resp = _html_with_gold_header("Classes | SailingSA", inner, extra_head)
            html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
            _CLASSES_PAGE_HTML_CACHE["html"] = html"""

CLASSES_NEW = """            _fb_classes_head = _fb_og_head_for('directory', 'classes', 'Classes | SailingSA', about, _canonical_base_url() + '/classes', source_url='/assets/logos/sailingsa-logo.png')
            extra_head = "<style>" + _directory_logo_grid_extra_css() + ccd.classes_directory_extra_css() + "</style>"
            resp = _html_with_gold_header("Classes | SailingSA", inner, extra_head)
            html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
            import facebook_og as _fb
            html = _fb.inject_facebook_head(html, _fb_classes_head)
            _CLASSES_PAGE_HTML_CACHE["html"] = html"""

CLUBS_OLD = """    extra_head = (
        '<link rel="canonical" href="https://sailingsa.co.za/clubs">'
        + _fb_og_head_for('directory', 'clubs', 'Clubs | SailingSA', about, _canonical_base_url() + '/clubs', source_url='/assets/logos/sailingsa-logo.png')
        + "<style>" + _directory_logo_grid_extra_css() + "</style>"
    )
    return _html_with_gold_header("Clubs | SailingSA", inner, extra_head)"""

CLUBS_NEW = """    _fb_clubs_head = _fb_og_head_for('directory', 'clubs', 'Clubs | SailingSA', about, _canonical_base_url() + '/clubs', source_url='/assets/logos/sailingsa-logo.png')
    extra_head = "<style>" + _directory_logo_grid_extra_css() + "</style>"
    resp = _html_with_gold_header("Clubs | SailingSA", inner, extra_head)
    html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
    import facebook_og as _fb
    html = _fb.inject_facebook_head(html, _fb_clubs_head)
    return HTMLResponse(html)"""

CLASSES_CACHE_OLD = """    if ent.get("html") and (now - float(ent.get("ts") or 0)) < _CLASSES_PAGE_HTML_TTL_SEC:
        return HTMLResponse(ent["html"])"""
CLASSES_CACHE_NEW = """    if ent.get("html") and (now - float(ent.get("ts") or 0)) < _CLASSES_PAGE_HTML_TTL_SEC:
        if 'og:image' in (ent.get("html") or ""):
            return HTMLResponse(ent["html"])"""

CLASSES_DISK_OLD = """            html = open(disk, encoding="utf-8", errors="replace").read()
            if html:
                _CLASSES_PAGE_HTML_CACHE["html"] = html"""
CLASSES_DISK_NEW = """            html = open(disk, encoding="utf-8", errors="replace").read()
            if html and 'og:image' in html:
                _CLASSES_PAGE_HTML_CACHE["html"] = html"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix6")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix6_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    for name, old, new in (
        ("lipton regatta", LIPTON_OLD, LIPTON_NEW),
        ("classes page", CLASSES_OLD, CLASSES_NEW),
        ("clubs page", CLUBS_OLD, CLUBS_NEW),
        ("classes cache mem", CLASSES_CACHE_OLD, CLASSES_CACHE_NEW),
        ("classes cache disk", CLASSES_DISK_OLD, CLASSES_DISK_NEW),
    ):
        if old not in text:
            raise SystemExit(f"{name} anchor not found")
        text = text.replace(old, new, 1)

    text = text.replace("# FB_OG_FIX5_v1", "# FB_OG_FIX5_v1\n" + MARKER, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix6", API_PATH)


if __name__ == "__main__":
    main()
