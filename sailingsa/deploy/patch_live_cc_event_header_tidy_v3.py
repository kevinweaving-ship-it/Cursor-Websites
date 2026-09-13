#!/usr/bin/env python3
"""Event URL header only: split Results / as at. Marker: CC_EVENT_HEADER_TIDY_v3."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "CC_EVENT_HEADER_TIDY_v3"

OLD = """                + f'<div class="status-line">{status_line_text}</div>'
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
"""
NEW = f"""                + cape_classic_event_header_status_html(  # {MARKER}
                    status_line_text, str(regatta_id)
                )
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
"""


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched", MARKER)
        return
    n = text.count(OLD)
    if n != 1:
        raise SystemExit(f"expected 1 Event URL status+entries wrap, found {n}")
    API.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", API, MARKER)


if __name__ == "__main__":
    main()
