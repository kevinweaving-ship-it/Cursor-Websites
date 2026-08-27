#!/usr/bin/env python3
"""Patch live api.py: Lipton as-at is always DB stamp, never wall clock.

Morning wake clears day_done, which would re-enable data-as-at-live and
replace "27 August 2026 at 17:17" with the device clock. Status line rule
is regattas.as_at_time only. Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_ASAT_DB_ONLY_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''    live_ok = bool(is_provisional and end_s and _regatta_dates_are_live(start_date or end_date, end_date or start_date))
    # LIPTON_OVERNIGHT_UI_V1 freeze as-at after harbour close (DB stamp, not wall clock).
    if live_ok and is_lipton and regatta_id:
        try:
            _lr = _read_live_race_state(str(regatta_id)) or {}
            if _lr.get("day_done") or str(_lr.get("schedule_slot") or "") == "day_close":
                live_ok = False
        except Exception:
            pass
'''

NEW = '''    live_ok = bool(is_provisional and end_s and _regatta_dates_are_live(start_date or end_date, end_date or start_date))
    # ''' + MARKER + ''' never tick wall clock; status line is regattas.as_at_time.
    if is_lipton:
        live_ok = False
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL as-at: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
