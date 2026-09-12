#!/usr/bin/env python3
"""Lipton once-off: do not put LIVE + Start chips on generic live event headers."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

REPLACEMENTS = [
    (
        '''def _regatta_live_board_badge_html(regatta_id: str, start_d, end_d, *, sa_toggle: bool = False) -> str:
    """When event date-window is live: LIVE / Racing Rn / POSTPONED + Start or T+ elapsed.

    LIVE → Start HH:MM · date. RACING (or live-race phase racing with gun) → Racing Rn + T+.
    """
    if not _regatta_dates_are_live(start_d, end_d):
        return ""
''',
        '''def _regatta_live_board_badge_html(regatta_id: str, start_d, end_d, *, sa_toggle: bool = False) -> str:
    """Lipton once-off LIVE / Racing / POSTPONED + Start. Not on other live event headers."""
    if not _regatta_is_lipton_challenge(regatta_id or ""):
        return ""
    if not _regatta_dates_are_live(start_d, end_d):
        return ""
''',
    ),
    (
        '''def _regatta_page_live_board_attrs(regatta_id: str, start_d, end_d) -> str:
    """data-live-board-tint-rid + page-status + underway (hides wx/cam; reorders page)."""
    if not _regatta_dates_are_live(start_d, end_d):
        return ""
''',
        '''def _regatta_page_live_board_attrs(regatta_id: str, start_d, end_d) -> str:
    """Lipton live-board page attrs only. Generic live URLs stay a normal results page."""
    if not _regatta_is_lipton_challenge(regatta_id or ""):
        return ""
    if not _regatta_dates_are_live(start_d, end_d):
        return ""
''',
    ),
    (
        '    ".regatta-page:not([data-live-lipton=\\"1\\"])>.regatta-live-wx,.regatta-page:not([data-live-lipton=\\"1\\"])>.regatta-live-clip{display:none!important}"',
        '    ".regatta-page:not([data-live-lipton=\\"1\\"])>.regatta-live-wx,.regatta-page:not([data-live-lipton=\\"1\\"])>.regatta-live-clip,.regatta-page:not([data-live-lipton=\\"1\\"]) .regatta-live-board-row{display:none!important}"',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n} for:\n{old[:200]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
