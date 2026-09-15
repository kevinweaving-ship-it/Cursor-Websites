#!/usr/bin/env python3
"""Undo api.py flex stack that grew race-cell height."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = (
    '    ".fleet-results-table td.race-col > span.code{'
    "display:inline-flex;flex-direction:column;align-items:center;"
    'justify-content:center;line-height:1.05;padding-bottom:3px}"\n'
    '    ".fleet-results-table .wc-score{font-size:1em;font-weight:600;line-height:1.1}"\n'
    '    ".fleet-results-table .wc-code{display:block;font-size:0.55em;'
    "margin:1px 0 0;padding-bottom:2px;font-weight:700;opacity:0.85;"
    'text-align:center;line-height:1}"'
)
NEW = (
    '    ".fleet-results-table .wc-score{font-size:1em;font-weight:600}"\n'
    '    ".fleet-results-table .wc-code{font-size:0.55em;margin-left:2px;font-weight:700;opacity:0.85}"'
)


def main() -> None:
    text = API.read_text()
    if OLD not in text:
        if NEW in text and "td.race-col > span.code{display:inline-flex" not in text:
            print("API_ALREADY_REVERTED")
            return
        raise SystemExit("API_FLEX_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.wc_flex_revert.{ts}")
    shutil.copy2(API, bak)
    API.write_text(text.replace(OLD, NEW, 1))
    print("BACKUP", bak, "REVERTED")


if __name__ == "__main__":
    main()
