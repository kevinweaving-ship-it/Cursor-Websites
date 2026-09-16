#!/usr/bin/env python3
"""Slightly larger overlay codes; as wide as (20), no extra row height."""
from pathlib import Path
import shutil
import time

SRC = Path("/var/www/sailingsa/sailingsa/backend/regatta_print_compact_css.py")

# Only the overlay code rules (both still 33%).
OLD = "  font-size: 33% !important;"
NEW = "  font-size: 50% !important;"

OLD_LS = "  letter-spacing: 0.02em !important;"
NEW_LS = "  letter-spacing: 0.08em !important;"


def main() -> None:
    text = SRC.read_text()
    n = text.count(OLD)
    if n < 1:
        if "font-size: 50% !important;" in text and "letter-spacing: 0.08em !important;" in text:
            print("ALREADY_PATCHED")
            return
        raise SystemExit("SIZE_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = SRC.with_name(f"regatta_print_compact_css.py.bak.{ts}")
    shutil.copy2(SRC, bak)
    text = text.replace(OLD, NEW)
    if OLD_LS in text:
        text = text.replace(OLD_LS, NEW_LS)
    SRC.write_text(text)
    print("BACKUP", bak, "SIZE", n, "PATCHED")


if __name__ == "__main__":
    main()
