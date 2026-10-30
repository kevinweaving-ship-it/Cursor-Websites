#!/usr/bin/env python3
"""Keep DH/SH before Fleet when a class logo is shown.

Live helper (PYTHONPATH=/var/www/sailingsa):

    sailingsa/backend/cape_classic_fleet_sheet.py
    fleet_header_title_without_class_dup()

Single-class events stay logo + 'Fleet' (Midmar Hunter 19).
Dart 18 Nationals is two fleets: logo + 'DH Fleet' / 'SH Fleet'.
"""

from __future__ import annotations

import re
from pathlib import Path

LIVE = Path("/var/www/sailingsa/sailingsa/backend/cape_classic_fleet_sheet.py")

OLD = """    if has_class_logo:
        return "Fleet"
    return raw
"""

NEW = """    if has_class_logo:
        # GOLD: logo is the class name. Keep a distinct DH/SH division before Fleet.
        m = re.search(r"\\b(DH|SH)\\b", raw, flags=re.I)
        if m:
            return f"{m.group(1).upper()} Fleet"
        return "Fleet"
    return raw
"""


def apply(path: Path) -> int:
    text = path.read_text()
    if "Keep a distinct DH/SH division before Fleet" in text:
        print(f"already patched {path}")
        return 0
    if OLD not in text:
        raise SystemExit(f"pattern not found in {path}")
    path.write_text(text.replace(OLD, NEW, 1))
    print(f"patched {path}")
    return 0


if __name__ == "__main__":
    apply(LIVE)
