#!/usr/bin/env python3
"""Patch live api.py: harbour-close also runs 00:00–10:00.

Close was only mins>=17:00. After midnight a leftover gun skipped close
and PUT treated it as a live race. Never overwrite live api.py with repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_PRE_WAKE_CLOSE_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_IF = '''    # --- Day close from 17:00 (harbour overnight). R6 arms tomorrow 10:00/12:00. ---
    # LIPTON_DAY_CLOSE_17_V2
    if mins >= 17 * 60:
'''

NEW_IF = '''    # --- Day close from 17:00 and after midnight until 10:00. ---
    # ''' + MARKER + ''' leftover gun after midnight is stale.
    if mins >= 17 * 60 or mins < 10 * 60:
'''

OLD_SKIP = '''        if board_now == "POSTPONED" or (board_now == "RACING" and race_active_close):
'''

NEW_SKIP = '''        if mins >= 17 * 60 and (board_now == "POSTPONED" or (board_now == "RACING" and race_active_close)):
'''

OLD_SLOT = '''        st["cam_show"] = _live_race_cam_should_show(True, False)
        st["schedule_slot"] = "day_close"
        if changed:
'''

NEW_SLOT = '''        st["cam_show"] = _live_race_cam_should_show(True, False)
        if mins < 10 * 60:
            st["track_idle"] = bool(mins < (5 * 60 + 30))
            st["schedule_slot"] = "overnight"
        else:
            st["schedule_slot"] = "day_close"
        if changed:
'''

OLD_HARB = '''    if not (mins >= 17 * 60 or mins < 10 * 60):
        return False
    has_gun = False
    try:
        has_gun = bool(_normalize_gun_at_iso(st.get("gun_at") or ""))
    except Exception:
        has_gun = bool(st.get("gun_at"))
    phase = str(st.get("phase") or "").strip().lower()
    if has_gun and phase == "racing" and not st.get("race_complete"):
        return False
    return True
'''

NEW_HARB = '''    if mins < 10 * 60:
        return True
    if mins < 17 * 60:
        return False
    has_gun = False
    try:
        has_gun = bool(_normalize_gun_at_iso(st.get("gun_at") or ""))
    except Exception:
        has_gun = bool(st.get("gun_at"))
    phase = str(st.get("phase") or "").strip().lower()
    if has_gun and phase == "racing" and not st.get("race_complete"):
        return False
    return True
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    counts = {
        "if": text.count(OLD_IF),
        "skip": text.count(OLD_SKIP),
        "slot": text.count(OLD_SLOT),
        "harb": text.count(OLD_HARB),
    }
    if any(n != 1 for n in counts.values()):
        print(f"FAIL pre-wake: {counts}", file=sys.stderr)
        return 1
    text = text.replace(OLD_IF, NEW_IF, 1)
    text = text.replace(OLD_SKIP, NEW_SKIP, 1)
    text = text.replace(OLD_SLOT, NEW_SLOT, 1)
    text = text.replace(OLD_HARB, NEW_HARB, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
