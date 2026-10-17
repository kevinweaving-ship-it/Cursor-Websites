#!/usr/bin/env python3
"""Patch live api.py: GET must not heal a gun or advertise RACING overnight.

Schedule already closes 17:00 and 00:00–10:00. If day_done lagged, GET still
healed icons gun whenever schedule_slot was not exactly day_close (overnight
uses slot=overnight). Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_NO_HEAL_OVERNIGHT_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_HEAL = '''    if not race_done and not st.get("day_done") and str(st.get("schedule_slot") or "") != "day_close":
'''

NEW_HEAL = '''    overnight_slot = str(st.get("schedule_slot") or "") in ("day_close", "overnight")
    if not race_done and not st.get("day_done") and not overnight_slot:
        # ''' + MARKER + '''
'''

OLD_ADV = '''    if phase == "racing" and st.get("gun_at") and board not in ("POSTPONED", "AP", "FINISHED", "FINAL"):
        # Prefer RACING for clients even if icons board still says LIVE.
        st["board_status"] = "RACING"
'''

NEW_ADV = '''    if phase == "racing" and st.get("gun_at") and board not in ("POSTPONED", "AP", "FINISHED", "FINAL") and not (
        st.get("day_done") or str(st.get("schedule_slot") or "") in ("day_close", "overnight")
    ):
        # Prefer RACING for clients even if icons board still says LIVE.
        st["board_status"] = "RACING"
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n_heal = text.count(OLD_HEAL)
    n_adv = text.count(OLD_ADV)
    if n_heal != 1 or n_adv != 1:
        print(f"FAIL heal: heal={n_heal} adv={n_adv}", file=sys.stderr)
        return 1
    text = text.replace(OLD_HEAL, NEW_HEAL, 1)
    text = text.replace(OLD_ADV, NEW_ADV, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
