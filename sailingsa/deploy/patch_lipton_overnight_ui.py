#!/usr/bin/env python3
"""Patch live api.py: overnight Lipton keeps Start hidden and as-at frozen.

Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_OVERNIGHT_UI_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_ATTRS = '''    if "lipton" in str(regatta_id or "").strip().lower():
        racing_ui = st == "RACING"
        underway = "1" if racing_ui else "0"
    else:
        racing_ui = (st == "RACING") or (bool(gun) and phase == "racing" and st != "POSTPONED")
        if racing_ui:
            st = "RACING"
        underway = "1" if racing_ui else "0"
    lipton = "1" if "lipton" in str(regatta_id or "").strip().lower() else "0"
    return (
        f' data-live-board-tint-rid="{rid_esc}" data-live-board-page-status="{st}"'
        f' data-live-race-underway="{underway}"'
        f' data-live-lipton="{lipton}"'
    )
'''

NEW_ATTRS = '''    if "lipton" in str(regatta_id or "").strip().lower():
        if bool(lr.get("day_done")) and not gun:
            st = "LIVE"
        racing_ui = st == "RACING"
        underway = "1" if racing_ui else "0"
    else:
        racing_ui = (st == "RACING") or (bool(gun) and phase == "racing" and st != "POSTPONED")
        if racing_ui:
            st = "RACING"
        underway = "1" if racing_ui else "0"
    lipton = "1" if "lipton" in str(regatta_id or "").strip().lower() else "0"
    day_done = "1" if bool(lr.get("day_done")) else "0"
    return (
        f' data-live-board-tint-rid="{rid_esc}" data-live-board-page-status="{st}"'
        f' data-live-race-underway="{underway}"'
        f' data-live-lipton="{lipton}"'
        f' data-live-day-done="{day_done}"'
    )
'''

OLD_SYNC = '''    if (start) {
      if (st==='POSTPONED' || prestartCd || (st==='LIVE' && !showRacingUi && !prestartArmed))
        start.removeAttribute('hidden');
      else start.setAttribute('hidden','');
    }
'''

NEW_SYNC = '''    if (start) {
      /* ''' + MARKER + ''' overnight: do not unhide Start 12:00 on LIVE. */
      var overnight = !!(page && page.getAttribute('data-live-day-done')==='1');
      if (overnight) {
        start.setAttribute('hidden','');
      } else if (st==='POSTPONED' || prestartCd || (st==='LIVE' && !showRacingUi && !prestartArmed))
        start.removeAttribute('hidden');
      else start.setAttribute('hidden','');
    }
'''

OLD_LIVE_OK = '''    live_ok = bool(is_provisional and end_s and _regatta_dates_are_live(start_date or end_date, end_date or start_date))
'''

NEW_LIVE_OK = '''    live_ok = bool(is_provisional and end_s and _regatta_dates_are_live(start_date or end_date, end_date or start_date))
    # ''' + MARKER + ''' freeze as-at after harbour close (DB stamp, not wall clock).
    if live_ok and is_lipton and regatta_id:
        try:
            _lr = _read_live_race_state(str(regatta_id)) or {}
            if _lr.get("day_done") or str(_lr.get("schedule_slot") or "") == "day_close":
                live_ok = False
        except Exception:
            pass
'''


def _patch_once(text: str, label: str, old: str, new: str) -> tuple[str, bool]:
    if MARKER in new and MARKER in text and old not in text:
        print(f"already {label}")
        return text, True
    n = text.count(old)
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
    text, p = _patch_once(text, "attrs", OLD_ATTRS, NEW_ATTRS)
    ok = ok and p
    text, p = _patch_once(text, "sync-start", OLD_SYNC, NEW_SYNC)
    ok = ok and p
    text, p = _patch_once(text, "as-at", OLD_LIVE_OK, NEW_LIVE_OK)
    ok = ok and p
    if not ok:
        return 1
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
