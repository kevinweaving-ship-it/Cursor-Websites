"""Contract tests: standalone /regatta pages expose Print + Share."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_FILES = (ROOT / "api.py", ROOT / "api" / "api.py")


def test_print_share_helper_wired_on_standalone_sheets():
    for path in API_FILES:
        text = path.read_text(encoding="utf-8")
        assert "def _regatta_print_share_buttons_html" in text, path
        assert "id='regattaShareBtn'" in text, path
        assert "navigator.share" in text, path
        assert "window.print()" in text, path
        assert text.count("print_btn = _regatta_print_share_buttons_html()") == 2, path
        assert (
            '<div class="action-buttons"><button class="action-button" onclick="window.print()">Print</button></div>'
            not in text
        ), path


def test_live_patch_replaces_print_only_markup():
    patch = (ROOT / "sailingsa" / "deploy" / "live_patch_zvyc_cc_print_share.py").read_text(
        encoding="utf-8"
    )
    assert "regattaShareBtn" in patch
    assert "navigator.share" in patch
    assert "window.print()" in patch


if __name__ == "__main__":
    test_print_share_helper_wired_on_standalone_sheets()
    test_live_patch_replaces_print_only_markup()
    print("ok")
