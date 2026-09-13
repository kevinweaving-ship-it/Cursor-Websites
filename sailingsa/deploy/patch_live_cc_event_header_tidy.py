#!/usr/bin/env python3
"""Surgical live api.py patch: Cape Classic event-header title + drop duplicate venue.

Marker: CC_EVENT_HEADER_TIDY_v1
Never overwrite live api.py with the repo copy.
Print/PDF is paused — this is the Event URL header card only.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "CC_EVENT_HEADER_TIDY_v1"

OLD_NAME = '''        display_name = (ev_name or event_name or "").strip()
        escaped_title = html_module.escape(display_name)
'''

NEW_NAME = '''        display_name = (ev_name or event_name or "").strip()
        try:
            from sailingsa.backend.cape_classic_fleet_sheet import (
                cape_classic_event_header_title,
            )
            display_name = cape_classic_event_header_title(display_name, str(regatta_id))
        except Exception:
            pass
        escaped_title = html_module.escape(display_name)
'''

OLD_VENUE = '''def _regatta_venue_row_html(regatta_id: str) -> str:
    """Venue line — shared class/size with all regattas.

    Non-Lipton: place; optional co-host chip when present.
    Lipton headers skip this helper (venue lives in Lipton stack only).
    """
    place, co_host = _regatta_venue_cohost(regatta_id)
'''

NEW_VENUE = '''def _regatta_venue_row_html(regatta_id: str) -> str:
    """Venue line — shared class/size with all regattas.

    Non-Lipton: place; optional co-host chip when present.
    Lipton headers skip this helper (venue lives in Lipton stack only).
    """
    # ''' + MARKER + '''
    try:
        from sailingsa.backend.cape_classic_fleet_sheet import (
            cape_classic_hide_duplicate_venue,
        )
        if cape_classic_hide_duplicate_venue(regatta_id):
            return ""
    except Exception:
        pass
    place, co_host = _regatta_venue_cohost(regatta_id)
'''


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched", MARKER)
        return
    if OLD_NAME not in text:
        raise SystemExit("display_name block not found")
    if OLD_VENUE not in text:
        raise SystemExit("venue helper block not found")
    text = text.replace(OLD_NAME, NEW_NAME, 1)
    text = text.replace(OLD_VENUE, NEW_VENUE, 1)
    API.write_text(text, encoding="utf-8")
    print("patched", API, MARKER)


if __name__ == "__main__":
    main()
