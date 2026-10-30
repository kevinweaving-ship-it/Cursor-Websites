#!/usr/bin/env python3
"""Fix events-logos duplicate canonical: inject FB head after page build."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX3_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

GALLERY_OLD = """        extra_head = (
            '<link rel="canonical" href="https://sailingsa.co.za/events-logos">'
            + _fb_og_head_for('events_logos', 'index', 'Named Events | SailingSA', 'Named event logos and regatta series on SailingSA.', _canonical_base_url() + '/events-logos', source_url='/assets/logos/sailingsa-logo.png')
            + "<style>" + _directory_logo_grid_extra_css() + elg.gallery_extra_css() + "</style>"
        )
        resp = _html_with_gold_header("Named Events | SailingSA", inner, extra_head)
        html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
        _events_logos_cache_set_gallery(html)"""

GALLERY_NEW = """        _fb_gallery_head = _fb_og_head_for('events_logos', 'index', 'Named Events | SailingSA', 'Named event logos and regatta series on SailingSA.', _canonical_base_url() + '/events-logos', source_url='/assets/logos/sailingsa-logo.png')
        extra_head = "<style>" + _directory_logo_grid_extra_css() + elg.gallery_extra_css() + "</style>"
        resp = _html_with_gold_header("Named Events | SailingSA", inner, extra_head)
        html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
        import facebook_og as _fb
        html = _fb.inject_facebook_head(html, _fb_gallery_head)
        _events_logos_cache_set_gallery(html)"""

DETAIL_OLD = """        extra_head = (
            _fb_og_head_for('events_logos', slug, title, f'Named event: {title.split(" | ")[0]}. Regattas and hosts on SailingSA.', _canonical_base_url() + canonical_path, source_url=_fb_og_events_logo_url(slug))
            + f"<style>{elg.detail_extra_css()}</style>"
        )
        resp = _html_with_gold_header(title, inner, extra_head)
        html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
        _events_logos_cache_set_detail(slug, html)"""

DETAIL_NEW = """        _fb_detail_head = _fb_og_head_for('events_logos', slug, title, f'Named event: {title.split(" | ")[0]}. Regattas and hosts on SailingSA.', _canonical_base_url() + canonical_path, source_url=_fb_og_events_logo_url(slug))
        extra_head = f"<style>{elg.detail_extra_css()}</style>"
        resp = _html_with_gold_header(title, inner, extra_head)
        html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
        import facebook_og as _fb
        html = _fb.inject_facebook_head(html, _fb_detail_head)
        _events_logos_cache_set_detail(slug, html)"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix3")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix3_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")
    if GALLERY_OLD not in text:
        raise SystemExit("events-logos gallery block not found")
    if DETAIL_OLD not in text:
        raise SystemExit("events-logos detail block not found")
    text = text.replace(GALLERY_OLD, GALLERY_NEW, 1)
    text = text.replace(DETAIL_OLD, DETAIL_NEW, 1)
    text = text.replace("# FB_OG_FIX2_v1", "# FB_OG_FIX2_v1\n" + MARKER, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix3", API_PATH)


if __name__ == "__main__":
    main()
