"""Contract tests: standalone /regatta Print/Share + compact portrait print CSS."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_FILES = (ROOT / "api.py", ROOT / "api" / "api.py")


def test_print_share_helper_wired_on_standalone_sheets():
    for path in API_FILES:
        text = path.read_text(encoding="utf-8")
        assert "def _regatta_print_share_buttons_html" in text, path
        assert "print_share_bar_html" in text, path
        assert text.count("print_btn = _regatta_print_share_buttons_html()") == 2, path
        assert (
            '<div class="action-buttons"><button class="action-button" onclick="window.print()">Print</button></div>'
            not in text
        ), path


def test_compact_print_css_portrait_header_and_fleet_line():
    from sailingsa.backend.regatta_print_compact_css import PRINT_COMPACT_CSS, print_share_bar_html

    css = PRINT_COMPACT_CSS
    assert "size: A4 portrait" in css
    assert "grid-template-columns: auto minmax(0,1fr) auto" in css
    assert "max-height: 22px" in css
    assert "max-width: 48px" in css
    assert ".class-header-club-logo-col { display: none !important; }" in css
    assert "min-width: 0 !important" in css
    assert "white-space: nowrap" in css
    assert "table-layout: fixed" in css
    assert ".race-col" in css
    assert "2025-12-19-hyc-youth-nationals" in Path(
        ROOT / "sailingsa" / "backend" / "regatta_print_compact_css.py"
    ).read_text(encoding="utf-8")
    assert "break-inside: avoid-page" in css
    assert ".regatta-page > .fleet-section:first-of-type" in css
    assert "page-break-before: avoid" in css
    assert "break-after: avoid-page" in css
    bar = print_share_bar_html()
    assert "ssa-print-compact" in bar
    assert "regattaShareBtn" in bar
    assert "navigator.share" in bar
    assert 'id="ssaPrintPageFooter"' in bar
    assert "ssa-print-page-footer" in css
    assert "position: fixed" in css
    assert "fillFooter" in bar
    assert "link[rel=" in bar
    assert "ssa-print-new-page" in css
    assert "keepFleetsOnOnePage" in bar
    assert "ssaRegattaPrint" in bar
    src = Path(ROOT / "sailingsa" / "backend" / "regatta_print_compact_css.py").read_text(
        encoding="utf-8"
    )
    assert "A fleet is never split across two pages" in src


def test_live_patch_replaces_print_only_markup():
    patch = (ROOT / "sailingsa" / "deploy" / "live_patch_zvyc_cc_print_share.py").read_text(
        encoding="utf-8"
    )
    assert "ssa-print-compact" in patch
    assert "print_share_bar_html" in patch


if __name__ == "__main__":
    test_print_share_helper_wired_on_standalone_sheets()
    test_compact_print_css_portrait_header_and_fleet_line()
    test_live_patch_replaces_print_only_markup()
    print("ok")
