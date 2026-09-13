#!/usr/bin/env python3
"""Cape Classic Event URL: icon + 'N Entries'. Marker: CC_EVENT_HEADER_ENTRIES_v1."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "CC_EVENT_HEADER_ENTRIES_v1"

OLD = '''    if n <= 0:
        return ""
    return f'<div class="entry-total-line">Total Entries = {n}</div>'
'''
NEW = '''    if n <= 0:
        return ""
    try:  # ''' + MARKER + '''
        from sailingsa.backend.cape_classic_fleet_sheet import (
            cape_classic_entries_line_html,
        )
        return cape_classic_entries_line_html(n)
    except Exception:
        return f'<div class="entry-total-line">{n} Entries</div>'
'''

OLD_CSS = '".entry-total-line{font-size:12px;color:#1a2750;font-weight:600;margin-top:2px;margin-bottom:0;line-height:1.2}"'
NEW_CSS = (
    OLD_CSS
    + '\n    ".entry-total-line--icon{display:inline-flex;align-items:center;gap:6px}"'
    + '\n    ".entry-total-ico{display:inline-flex;align-items:center;line-height:0}"'
)


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched", MARKER)
        return
    if OLD not in text:
        raise SystemExit("entries return block not found")
    if OLD_CSS not in text:
        raise SystemExit("entry-total-line css not found")
    text = text.replace(OLD, NEW, 1).replace(OLD_CSS, NEW_CSS, 1)
    API.write_text(text, encoding="utf-8")
    print("patched", API, MARKER)


if __name__ == "__main__":
    main()
