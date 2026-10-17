#!/usr/bin/env python3
"""SSR overnight chip must follow live-race JSON gun, not stale icon-cache gun.

Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_SSR_JSON_GUN_ONLY_V3"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_V0 = '''    phase = str(lr.get("phase") or "").strip().lower()
    # Lipton 2026: Super admin chip is page mode (LIVE / RACING / POSTPONED).
    if "lipton" in str(regatta_id or "").strip().lower():
        if bool(lr.get("day_done")) and not gun:
            st = "LIVE"
        racing_ui = st == "RACING"
'''

OLD_V2 = '''    phase = str(lr.get("phase") or "").strip().lower()
    # Lipton 2026: Super admin chip is page mode (LIVE / RACING / POSTPONED).
    if "lipton" in str(regatta_id or "").strip().lower():
        # LIPTON_SSR_JSON_GUN_ONLY_V2 healed icon gun + finished/day_done is not overnight RACING.
        if (
            bool(lr.get("day_done"))
            and str(lr.get("phase") or "").strip().lower() in ("finished", "idle")
            and not bool(lr.get("race_armed"))
        ):
            st = "LIVE"
            gun = ""
        racing_ui = st == "RACING"
'''

NEW = '''    phase = str(lr.get("phase") or "").strip().lower()
    # Lipton 2026: Super admin chip is page mode (LIVE / RACING / POSTPONED).
    if "lipton" in str(regatta_id or "").strip().lower():
        # LIPTON_SSR_JSON_GUN_ONLY_V3 day_done means harbour closed: LIVE, ignore icon RACING.
        if bool(lr.get("day_done")) or str(lr.get("schedule_slot") or "") == "day_close":
            st = "LIVE"
            gun = ""
        racing_ui = st == "RACING"
'''


HEAL_OLD = '''            try:
                skip_heal = _lipton_overnight_harbour(rid, st) or _lipton_pre_arm_put_block(rid, st)
            except Exception:
                skip_heal = False
            if not skip_heal:
                st["gun_at"] = ig
'''

HEAL_NEW = '''            try:
                skip_heal = _lipton_overnight_harbour(rid, st) or _lipton_pre_arm_put_block(rid, st) or bool(st.get("day_done"))
            except Exception:
                skip_heal = bool(st.get("day_done"))
            if not skip_heal:
                st["gun_at"] = ig
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    changed = False
    if MARKER not in text:
        if text.count(OLD_V2) == 1:
            text = text.replace(OLD_V2, NEW, 1)
            changed = True
        elif text.count(OLD_V0) == 1:
            text = text.replace(OLD_V0, NEW, 1)
            changed = True
        else:
            print("FAIL ssr-json-gun: neither V0 nor V2 block", file=sys.stderr)
            return 1
    else:
        print("already", MARKER)
    if HEAL_OLD in text:
        if text.count(HEAL_OLD) != 1:
            print("FAIL skip_heal count", text.count(HEAL_OLD), file=sys.stderr)
            return 1
        text = text.replace(HEAL_OLD, HEAL_NEW, 1)
        changed = True
        print("patched skip_heal day_done")
    if not changed:
        print("ok", API_PATH)
        return 0
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
