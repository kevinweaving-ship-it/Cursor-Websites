#!/usr/bin/env python3
"""Centre race codes under the score; lift slightly off the cell bottom."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = (
    '    ".fleet-results-table .wc-score{font-size:1em;font-weight:600}"\n'
    '    ".fleet-results-table .wc-code{font-size:0.55em;margin-left:2px;font-weight:700;opacity:0.85}"'
)
NEW = (
    '    ".fleet-results-table td.race-col > span.code{'
    "display:inline-flex;flex-direction:column;align-items:center;"
    'justify-content:center;line-height:1.05;padding-bottom:3px}"\n'
    '    ".fleet-results-table .wc-score{font-size:1em;font-weight:600;line-height:1.1}"\n'
    '    ".fleet-results-table .wc-code{display:block;font-size:0.55em;'
    "margin:1px 0 0;padding-bottom:2px;font-weight:700;opacity:0.85;"
    'text-align:center;line-height:1}"'
)


def main() -> None:
    text = API.read_text()
    if "td.race-col > span.code{display:inline-flex;flex-direction:column" in text:
        print("ALREADY_PATCHED")
        return
    if OLD not in text:
        raise SystemExit("CSS_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.wc_code_center.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    API.write_text(text.replace(OLD, NEW, 1))
    print("PATCHED")


if __name__ == "__main__":
    main()
