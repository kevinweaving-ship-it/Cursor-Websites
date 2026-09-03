#!/usr/bin/env python3
"""Patch live api.py: after 10:00 wake, LIVE chip follows API race_key (R6).

A tab left open overnight keeps data-live-board-race-key=R5. Tracker T+ at
12:00 would then PUT finishes onto R5. Never copy repo api.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_LIVE_BUTTON_RK_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''        if(!racingUi){
          var table0=document.querySelector('.fleet-results-table');
          if(table0){
            [].forEach.call(table0.querySelectorAll('.live-race-plus-t-col'), function(el){
              el.classList.add('is-prior-hidden');
            });
          }
          lastSig='static|'+(st.day_done?'1':'0')+'|'+phase;
          return;
        }
'''

NEW = '''        if(!racingUi){
          var table0=document.querySelector('.fleet-results-table');
          if(table0){
            [].forEach.call(table0.querySelectorAll('.live-race-plus-t-col'), function(el){
              el.classList.add('is-prior-hidden');
            });
          }
          /* ''' + MARKER + ''' overnight keep last Rn; after wake follow API R6+. */
          if(!st.day_done && st.race_key){
            document.querySelectorAll('.regatta-live-board[data-live-board-rid="'+rid+'"]').forEach(function(btn){
              btn.setAttribute('data-live-board-race-key', String(st.race_key).toUpperCase());
            });
          }
          lastSig='static|'+(st.day_done?'1':'0')+'|'+phase;
          return;
        }
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL button rk: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
