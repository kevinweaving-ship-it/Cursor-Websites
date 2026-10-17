#!/usr/bin/env python3
"""Patch live api.py: leftover gun at 10:00 wake is not R6 underway.

Morning wake treated gun+phase racing as race_active, so a leftover
Vakaros gun that survived until 10:00 would stay RACING. Skip heal
from icons in the same window. Never copy repo api.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_PRE_ARM_WAKE_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_WAKE = '''        race_active = bool(has_gun) and phase_now == "racing" and not done_now
        # Arm sheet / next Rn — never wipe an active race.
'''

NEW_WAKE = '''        race_active = bool(has_gun) and phase_now == "racing" and not done_now
        # ''' + MARKER + ''' leftover gun before 12:00 is stale, not R6 underway.
        if (
            "lipton" in rid.lower()
            and race_active
            and not st.get("force_racing")
            and not st.get("simulate")
            and mins < 12 * 60
        ):
            race_active = False
            has_gun = False
            st["gun_at"] = None
            st["gun_source"] = None
        # Arm sheet / next Rn — never wipe an active race.
'''

OLD_HEAL = '''    if not race_done and not st.get("day_done") and not overnight_slot:
        # LIPTON_NO_HEAL_OVERNIGHT_V1
'''

NEW_HEAL = '''    if not race_done and not st.get("day_done") and not overnight_slot and not _lipton_pre_arm_put_block(rid, st):
        # LIPTON_NO_HEAL_OVERNIGHT_V1
'''

OLD_READ = '''    if not st.get("gun_at"):
        ig, irk = _icons_live_race_gun(rid)
        if ig:
            st["gun_at"] = ig
            if irk and not st.get("race_key"):
                st["race_key"] = irk
'''

NEW_READ = '''    if not st.get("gun_at"):
        ig, irk = _icons_live_race_gun(rid)
        if ig:
            try:
                skip_heal = _lipton_overnight_harbour(rid, st) or _lipton_pre_arm_put_block(rid, st)
            except Exception:
                skip_heal = False
            if not skip_heal:
                st["gun_at"] = ig
                if irk and not st.get("race_key"):
                    st["race_key"] = irk
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n_w = text.count(OLD_WAKE)
    n_h = text.count(OLD_HEAL)
    n_r = text.count(OLD_READ)
    if n_w != 1 or n_h != 1 or n_r != 1:
        print(f"FAIL wake: wake={n_w} heal={n_h} read={n_r}", file=sys.stderr)
        return 1
    if "LIPTON_PRE_ARM_PUT_V1" not in text:
        print("FAIL need LIPTON_PRE_ARM_PUT_V1 first", file=sys.stderr)
        return 1
    text = text.replace(OLD_WAKE, NEW_WAKE, 1)
    text = text.replace(OLD_HEAL, NEW_HEAL, 1)
    text = text.replace(OLD_READ, NEW_READ, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
