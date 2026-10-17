#!/usr/bin/env python3
"""Patch live api.py: leftover Vakaros T+ must not gun R6 between 10:00 and 12:00.

Harbour opens at 10:00 wake. First start is 12:00. Tracker T+ from yesterday
would otherwise PUT a gun at 10:00 and flip RACING. Never copy repo api.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_PRE_ARM_PUT_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_INSERT = '''    return True


def _set_regatta_live_board_status(regatta_id: str, status: str) -> str:
    """Persist LIVE/RACING/POSTPONED to all icons JSON mirrors. Pages poll/push — no HTML cache wipe.
'''

NEW_INSERT = '''    return True


def _lipton_pre_arm_put_block(rid, st=None):
    """''' + MARKER + r''' Block tracker gun from 10:00 until 12:00 arm."""
    if "lipton" not in str(rid or "").lower():
        return False
    st = st if isinstance(st, dict) else {}
    if st.get("force_racing") or st.get("simulate") or st.get("race_armed"):
        return False
    try:
        mins = int(_live_race_sa_minutes_now())
    except Exception:
        return False
    return 10 * 60 <= mins < 12 * 60


def _set_regatta_live_board_status(regatta_id: str, status: str) -> str:
    """Persist LIVE/RACING/POSTPONED to all icons JSON mirrors. Pages poll/push — no HTML cache wipe.
'''

OLD_PUT = '''    if _lipton_overnight_harbour(rid, cur):
        # LIPTON_OVERNIGHT_PUT_GUARD_V1 tracker T+ / RACING must not stamp a gun after close.
'''

NEW_PUT = '''    if _lipton_overnight_harbour(rid, cur) or _lipton_pre_arm_put_block(rid, cur):
        # LIPTON_OVERNIGHT_PUT_GUARD_V1 tracker T+ / RACING must not stamp a gun after close.
'''

OLD_JS_FN = '''  function liveDayClosed(st){
    /* Stop inventing next Rn after ~17:00 SA or admin day_done. */
'''

NEW_JS_FN = '''  function livePreArm(){
    /* ''' + MARKER + ''' leftover Vakaros T+ must not gun before 12:00 arm. */
    try{
      var parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Africa/Johannesburg',hour:'numeric',minute:'numeric',hour12:false}).formatToParts(new Date());
      var h=Number((parts.find(function(p){return p.type==='hour';})||{}).value||0);
      var m=Number((parts.find(function(p){return p.type==='minute';})||{}).value||0);
      if((h*60+m)>=10*60 && (h*60+m)<12*60) return true;
    }catch(e){}
    return false;
  }
  function liveDayClosed(st){
    /* Stop inventing next Rn after ~17:00 SA or admin day_done. */
'''

OLD_JS_GUARD = "    if(pgDone && pgDone.getAttribute('data-live-day-done')==='1') return false; /* LIPTON_TRACKER_OVERNIGHT_GUARD_V1 */"

NEW_JS_GUARD = (
    "    if(pgDone && pgDone.getAttribute('data-live-day-done')==='1') return false; /* LIPTON_TRACKER_OVERNIGHT_GUARD_V1 */\n"
    "    if(typeof livePreArm==='function' && livePreArm()) return false; /* "
    + MARKER
    + " */"
)


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n_ins = text.count(OLD_INSERT)
    n_put = text.count(OLD_PUT)
    n_fn = text.count(OLD_JS_FN)
    n_g = text.count(OLD_JS_GUARD)
    if n_ins != 1 or n_put != 1 or n_fn != 1 or n_g != 3:
        print(f"FAIL pre-arm: insert={n_ins} put={n_put} jsfn={n_fn} guard={n_g}", file=sys.stderr)
        return 1
    text = text.replace(OLD_INSERT, NEW_INSERT, 1)
    text = text.replace(OLD_PUT, NEW_PUT, 1)
    text = text.replace(OLD_JS_FN, NEW_JS_FN, 1)
    text = text.replace(OLD_JS_GUARD, NEW_JS_GUARD)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
