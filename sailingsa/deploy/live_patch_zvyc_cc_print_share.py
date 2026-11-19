#!/usr/bin/env python3
"""Print/Share + compact portrait print CSS on live standalone /regatta pages.

Surgical replace only — does not overwrite live api.py wholesale.
Copy this file and sailingsa/backend/regatta_print_compact_css.py to the server.
"""

from pathlib import Path
import sys

LIVE_API = Path("/var/www/sailingsa/api/api.py")
OLD_ASSIGN = (
    "print_btn = "
    '\'<div class="action-buttons"><button class="action-button" onclick="window.print()">Print</button></div>\''
)
NEW_ASSIGN = "print_btn = _regatta_print_share_buttons_html()"
HELPER = (
    "def _regatta_print_share_buttons_html() -> str:\n"
    '    """Print + Share + compact A4 CSS for standalone /regatta sheets."""\n'
    "    from sailingsa.backend.regatta_print_compact_css import print_share_bar_html\n"
    "\n"
    "    return print_share_bar_html()\n"
    "\n"
    "\n"
)
HELPER_ANCHOR = "def serve_cape_classic_crew_standalone(request: Request):"


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
    _load_bar_html()
    if "def _regatta_print_share_buttons_html" not in text:
        if HELPER_ANCHOR not in text:
            raise SystemExit("helper anchor serve_cape_classic_crew_standalone not found")
        text = text.replace(HELPER_ANCHOR, HELPER + HELPER_ANCHOR, 1)
    n = text.count(OLD_ASSIGN)
    if n:
        text = text.replace(OLD_ASSIGN, NEW_ASSIGN)
    if text.count(NEW_ASSIGN) < 1:
        raise SystemExit("print_btn helper assignment not found after patch")
    LIVE_API.write_text(text, encoding="utf-8")
    print(f"wired print_btn helper (replaced {n} print-only buttons)")


def _css_only() -> str:
    from sailingsa.backend.regatta_print_compact_css import PRINT_COMPACT_CSS

    return PRINT_COMPACT_CSS


if __name__ == "__main__":
    main()
