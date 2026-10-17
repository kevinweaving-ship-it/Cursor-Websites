#!/usr/bin/env python3
"""Patch live api.py: overnight LIVE chip stays on last completed Rn (R5).

Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_OVERNIGHT_R5_CHIP_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_DATE = '''    if now.hour >= 19:
        use_tomorrow = True
'''

NEW_DATE = '''    if now.hour >= 17:
        use_tomorrow = True
'''

OLD_DOC = '''    """Date for Start box (e.g. '27 Aug 2026') — tomorrow when day done / after 19:00 SA, else today."""
'''

NEW_DOC = '''    """Date for Start box (e.g. '27 Aug 2026') — tomorrow when day done / after 17:00 SA, else today."""
'''

OLD_RK = '''    if not re.match(r"^R\d+$", race_key):
        race_key = next_key
    else:
        try:
            if int(race_key[1:]) < int(str(next_key)[1:]):
                race_key = next_key
        except Exception:
            race_key = next_key
'''

NEW_RK = '''    if not re.match(r"^R\d+$", race_key):
        race_key = next_key
    elif not lr.get("day_done"):
        # ''' + MARKER + ''' overnight: keep last completed Rn (R5). Do not arm R6 on the LIVE chip.
        try:
            if int(race_key[1:]) < int(str(next_key)[1:]):
                race_key = next_key
        except Exception:
            race_key = next_key
'''

OLD_CMT = '''    /* Stop inventing next Rn after ~19:00 SA or admin day_done. */
'''

NEW_CMT = '''    /* Stop inventing next Rn after ~17:00 SA or admin day_done. */
'''


def _patch_once(text: str, label: str, old: str, new: str) -> tuple[str, bool]:
    n = text.count(old)
    if n == 0 and new in text:
        print(f"already {label}")
        return text, True
    if n != 1:
        print(f"FAIL {label}: found {n}", file=sys.stderr)
        return text, False
    return text.replace(old, new, 1), True


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    ok = True
    text, p = _patch_once(text, "date-hour", OLD_DATE, NEW_DATE)
    ok = ok and p
    text, p = _patch_once(text, "date-doc", OLD_DOC, NEW_DOC)
    ok = ok and p
    text, p = _patch_once(text, "race-key", OLD_RK, NEW_RK)
    ok = ok and p
    text, p = _patch_once(text, "js-cmt", OLD_CMT, NEW_CMT)
    ok = ok and p
    if not ok:
        return 1
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
