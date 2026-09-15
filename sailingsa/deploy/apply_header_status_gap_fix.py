#!/usr/bin/env python3
"""Tighten Event URL header: Results / as-at / Entries stack (Cape Classic std)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

CSS_OLD = '    ".status-line{font-size:14px;color:#1a2750;margin-top:8px}"'
CSS_NEW = (
    '    ".status-line{font-size:14px;color:#1a2750;margin-top:2px;margin-bottom:0;line-height:1.2}"\n'
    '    ".header .status-line + .status-line{margin-top:0}"\n'
    '    ".header .entry-total-line{margin-top:1px;margin-bottom:0}"\n'
    '    ".regatta-header-status-stack{display:flex;flex-direction:column;align-items:center;gap:1px;margin-top:4px}"\n'
    '    ".regatta-header-status-stack .status-line,'
    '.regatta-header-status-stack .entry-total-line{margin:0;line-height:1.2}"'
)

WRAP_OLD = """                + cape_classic_event_header_status_html(  # CC_EVENT_HEADER_TIDY_v2
                    status_line_text, str(regatta_id)
                )
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
"""
WRAP_OLD_V3 = WRAP_OLD.replace("TIDY_v2", "TIDY_v3")

WRAP_NEW = """                + '<div class="regatta-header-status-stack">'
                + cape_classic_event_header_status_html(
                    status_line_text, str(regatta_id)
                )
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
                + "</div>"
"""


def main() -> None:
    text = API.read_text()
    if "regatta-header-status-stack" in text and ".header .status-line + .status-line" in text:
        print("ALREADY_PATCHED")
        return
    if CSS_OLD not in text:
        raise SystemExit("CSS_ANCHOR_MISSING")
    text = text.replace(CSS_OLD, CSS_NEW, 1)
    n = 0
    if WRAP_OLD in text:
        text = text.replace(WRAP_OLD, WRAP_NEW, 1)
        n += 1
    if WRAP_OLD_V3 in text:
        text = text.replace(WRAP_OLD_V3, WRAP_NEW, 1)
        n += 1
    if n < 1:
        raise SystemExit("WRAP_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.header_gap.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak, "WRAPS", n)
    API.write_text(text)
    print("PATCHED")


if __name__ == "__main__":
    main()
