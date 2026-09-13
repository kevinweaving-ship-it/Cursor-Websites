#!/usr/bin/env python3
"""Cape Classic event header: split status line. Marker: CC_EVENT_HEADER_TIDY_v2."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "CC_EVENT_HEADER_TIDY_v2"

OLD_IMP = """            from sailingsa.backend.cape_classic_fleet_sheet import (
                cape_classic_event_header_title,
            )
"""
NEW_IMP = """            from sailingsa.backend.cape_classic_fleet_sheet import (
                cape_classic_event_header_title,
                cape_classic_event_header_status_html,
            )
"""
OLD_ST = """                + f'<div class="status-line">{status_line_text}</div>'
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
"""
NEW_ST = f"""                + cape_classic_event_header_status_html(  # {MARKER}
                    status_line_text, str(regatta_id)
                )
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
"""


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched", MARKER)
        return
    if OLD_IMP not in text:
        raise SystemExit("v1 title import not found")
    if OLD_ST not in text:
        raise SystemExit("status+entries block not found")
    text = text.replace(OLD_IMP, NEW_IMP, 1).replace(OLD_ST, NEW_ST, 1)
    API.write_text(text, encoding="utf-8")
    print("patched", API, MARKER)


if __name__ == "__main__":
    main()
