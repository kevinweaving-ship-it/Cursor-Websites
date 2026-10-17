#!/usr/bin/env python3
"""Lipton live-race: move automated end-of-day from 17:00 SAST to 19:00 SAST.

Does not change Super-admin LIVE/RACING/POSTPONED click behaviour.
Does not put the page into Race mode.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API_PY = Path("/var/www/sailingsa/api/api.py")

REPS = [
    (
        '    """Automate overnight → 10:00 wake → 12:00 R4 arm → 17:00 day close.\n',
        '    """Automate overnight → 10:00 wake → 12:00 R4 arm → 19:00 day close.\n',
        "schedule docstring",
    ),
    (
        "    # --- Day close from 17:00 (harbour overnight) ---\n"
        "    if mins >= 17 * 60:\n",
        "    # --- Day close from 19:00 (harbour overnight) ---\n"
        "    if mins >= 19 * 60:\n",
        "schedule day_close",
    ),
    (
        '    """Date for Start box (e.g. \'27 Aug 2026\') — tomorrow when day done / after 17:00 SA, else today."""\n',
        '    """Date for Start box (e.g. \'27 Aug 2026\') — tomorrow when day done / after 19:00 SA, else today."""\n',
        "start-date docstring",
    ),
    (
        "    if now.hour >= 17:\n"
        "        use_tomorrow = True\n",
        "    if now.hour >= 19:\n"
        "        use_tomorrow = True\n",
        "start-date hour",
    ),
    (
        "    /* Stop inventing next Rn after ~17:00 SA or admin day_done. */\n",
        "    /* Stop inventing next Rn after ~19:00 SA or admin day_done. */\n",
        "JS liveDayClosed comment",
    ),
    (
        "      if((h*60+m)>=17*60) return true;\n",
        "      if((h*60+m)>=19*60) return true;\n",
        "JS liveDayClosed clock",
    ),
]


def main() -> int:
    original = API_PY.read_text(encoding="utf-8")
    s = original
    for old, new, label in REPS:
        if new in s and old not in s:
            print("already", label)
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1, found {n}")
        s = s.replace(old, new, 1)
    if s == original:
        print("already patched", API_PY)
        return 0
    bak = API_PY.with_name(API_PY.name + ".bak-end-day-1900-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(API_PY, bak)
    API_PY.write_text(s, encoding="utf-8")
    print("patched", API_PY)
    print("backup", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
