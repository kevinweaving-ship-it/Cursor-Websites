#!/usr/bin/env python3
"""Patch live api.py: after 17:00 still apply a completed unapplied race.

Overnight skip must not drop a late R6 that finishes after harbour close.
After midnight leftover applies stay skipped. Never copy repo api.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_APPLY_LATE_FINISH_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''    if _lipton_overnight_harbour(rid, st):
        # LIPTON_APPLY_OVERNIGHT_SKIP_V1
        return {"ok": True, "overnight": True, "skipped": True, "regatta_id": rid}
'''

NEW = '''    if _lipton_overnight_harbour(rid, st):
        # LIPTON_APPLY_OVERNIGHT_SKIP_V1
        # ''' + MARKER + ''' after 17:00 still apply a completed unapplied race.
        skip = True
        try:
            mins = int(_live_race_sa_minutes_now())
        except Exception:
            mins = 0
        if mins >= 17 * 60 and st.get("race_complete") and not st.get("applied"):
            skip = False
        if skip:
            return {"ok": True, "overnight": True, "skipped": True, "regatta_id": rid}
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL late-finish: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
