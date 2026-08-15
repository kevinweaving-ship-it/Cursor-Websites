#!/usr/bin/env python3
"""Ensure left header logo for North Sails–named regattas uses Sponsor Logo."""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
RULES = [
    '    ("north sails", "/artwork/Sponsor Logo/North-Sails.png", "North Sails"),',
    '    ("north-sails", "/artwork/Sponsor Logo/North-Sails.png", "North Sails"),',
]


def main() -> int:
    text = API.read_text(encoding="utf-8")
    bak = API.with_suffix(f".py.bak_ns_sponsor_{int(time.time())}")
    shutil.copy2(API, bak)

    if '("north sails"' not in text:
        m = re.search(r'^\s*\("ullman".*\),?\s*$', text, re.M)
        if not m:
            raise SystemExit("ullman rule not found")
        text = text.replace(m.group(0), m.group(0) + "\n" + "\n".join(RULES), 1)
        print("added name→sponsor rules")
    else:
        print("name rules ok")

    # Ensure left logo HTML encodes spaces and labels North Sails
    if 'alt="North Sails"' not in text and "alt=\"North Sails\"" not in text:
        print("NOTE: left-logo HTML helper may need manual encode/alt patch (already on live)")
    API.write_text(text, encoding="utf-8")
    print("backup", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
