#!/usr/bin/env python3
"""Patch live api.py: JS liveDayClosed is also 00:00–10:00, not only after 17:00.

Without day_done, the chip could invent R6 after midnight. Match server harbour close.
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_JS_PRE_WAKE_CLOSE_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''      if((h*60+m)>=17*60) return true;
'''

NEW = '''      if((h*60+m)>=17*60 || (h*60+m)<10*60) return true; /* ''' + MARKER + ''' */
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL js-close: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
