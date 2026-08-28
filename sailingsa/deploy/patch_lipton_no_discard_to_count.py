#!/usr/bin/env python3
"""Lipton NoR 24.1: no discards; To count = races sailed."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "LIPTON_NO_DISCARD_TO_COUNT_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''    discard_count = fleet.get("discard_count") or 0
    to_count = fleet.get("to_count")
    if to_count is None and discard_count is not None:
        to_count = max(0, int(races_sailed) - int(discard_count))
'''

NEW = '''    discard_count = fleet.get("discard_count") or 0
    to_count = fleet.get("to_count")
    if to_count is None and discard_count is not None:
        to_count = max(0, int(races_sailed) - int(discard_count))
    if str(regatta_id or "").strip() == "2026-08-29-lipton-challenge-cup":
        # LIPTON_NO_DISCARD_TO_COUNT_V1 NoR 24.1: no discards; to_count = races sailed.
        discard_count = 0
        to_count = races_sailed
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL to-count: found {n}", file=sys.stderr)
        return 1
    tmp = Path("/tmp") / (API_PATH.name + ".tocount")
    tmp.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    rc = os.system(f"cp {tmp} {API_PATH}")
    if rc != 0:
        print("FAIL cp", rc, file=sys.stderr)
        return 1
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
