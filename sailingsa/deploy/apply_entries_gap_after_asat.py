#!/usr/bin/env python3
"""Cape Classic Event std: gap between as-at date and N Entries."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = (
    '    ".regatta-header-status-stack .status-line,'
    '.regatta-header-status-stack .entry-total-line{margin:0;line-height:1.2}"'
)
NEW = (
    '    ".regatta-header-status-stack .status-line,'
    '.regatta-header-status-stack .entry-total-line{margin:0;line-height:1.2}"\n'
    '    ".regatta-header-status-stack .entry-total-line{margin-top:14px}"'
)


def main() -> None:
    text = API.read_text()
    if ".regatta-header-status-stack .entry-total-line{margin-top:14px}" in text:
        print("ALREADY_PATCHED")
        return
    if OLD not in text:
        raise SystemExit("CSS_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.entries_gap.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    API.write_text(text.replace(OLD, NEW, 1))
    print("PATCHED")


if __name__ == "__main__":
    main()
