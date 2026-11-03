#!/usr/bin/env python3
"""Midmar / event results PDF: landscape, inverted favicon, share fallback."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_pdf_share_js_share_fallback():
    js = (ROOT / "js/regatta-pdf-share.js").read_text(encoding="utf-8")
    assert "ssaRegattaShare" in js
    assert "copySheetUrl" in js
    assert "navigator.clipboard.writeText" in js
    assert "wa.me/?text=" in js
    assert "AbortError" in js
    assert "#regattaShareBtn" in js
    frontend = ROOT / "sailingsa/frontend/js/regatta-pdf-share.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


def test_stored_pdf_landscape_and_inverted_favicon():
    src = (ROOT / "sailingsa/backend/regatta_stored_pdf.py").read_text(encoding="utf-8")
    assert "_SSA_FAVICON_INVERT = \"/assets/logos/Live/mark-on-color-512.png\"" in src
    assert "left_src = abs_asset_url(_SSA_FAVICON_INVERT)" in src
    assert 'orient = "portrait" if cc_portrait else "landscape"' in src
    assert "--font-render-hinting=none" in src
    assert "--disable-lcd-text" in src
    css = (ROOT / "sailingsa/backend/regatta_print_compact_css.py").read_text(encoding="utf-8")
    assert "IBM Plex Sans" not in css
    assert '"Liberation Sans", Arial, Helvetica, sans-serif' in css
    assert "table-layout: auto !important" in css
    assert "20260919print9" in css
    assert 'id="regattaShareBtn">Share</button>' in css


if __name__ == "__main__":
    test_pdf_share_js_share_fallback()
    test_stored_pdf_landscape_and_inverted_favicon()
    print("regatta_pdf_share_min_tests: ok")
