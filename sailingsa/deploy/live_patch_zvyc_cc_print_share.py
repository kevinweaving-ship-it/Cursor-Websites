#!/usr/bin/env python3
"""Print/Share + compact portrait print CSS on live standalone /regatta pages.

Surgical replace only — does not overwrite live api.py wholesale.
Copy this file and sailingsa/backend/regatta_print_compact_css.py to the server.
"""

from pathlib import Path
import sys

LIVE_API = Path("/var/www/sailingsa/api/api.py")
OLD = '<div class="action-buttons"><button class="action-button" onclick="window.print()">Print</button></div>'
STYLE_ID = "ssa-print-compact"


def _load_bar_html() -> str:
    repo_backend = Path(__file__).resolve().parent.parent / "backend"
    for base in (Path("/var/www/sailingsa"), repo_backend.parent.parent, repo_backend.parent):
        if str(base) not in sys.path:
            sys.path.insert(0, str(base))
    try:
        from sailingsa.backend.regatta_print_compact_css import print_share_bar_html

        return print_share_bar_html()
    except Exception:
        sibling = Path(__file__).resolve().parent / "regatta_print_compact_css.py"
        if not sibling.is_file():
            sibling = repo_backend / "regatta_print_compact_css.py"
        if not sibling.is_file():
            raise SystemExit("regatta_print_compact_css.py not found")
        ns = {}
        exec(sibling.read_text(encoding="utf-8"), ns)
        return ns["print_share_bar_html"]()


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    bar = _load_bar_html()
    if STYLE_ID in text and "regattaShareBtn" in text:
        print("already patched")
        return
    if OLD in text:
        text = text.replace(OLD, bar)
        LIVE_API.write_text(text, encoding="utf-8")
        print("patched Print/Share + compact print CSS")
        return
    if "regattaShareBtn" in text and STYLE_ID not in text:
        needle = '<button type="button" class="action-button" id="regattaShareBtn">Share</button>'
        if needle not in text:
            raise SystemExit("Share button found but compact CSS inject point missing")
        text = text.replace(
            '<div class="action-buttons">',
            '<style id="ssa-print-compact">' + _css_only() + "</style>" + '<div class="action-buttons">',
            1,
        )
        LIVE_API.write_text(text, encoding="utf-8")
        print("injected compact print CSS beside existing Share button")
        return
    raise SystemExit("Print action-buttons HTML not found")


def _css_only() -> str:
    from sailingsa.backend.regatta_print_compact_css import PRINT_COMPACT_CSS

    return PRINT_COMPACT_CSS


if __name__ == "__main__":
    main()
