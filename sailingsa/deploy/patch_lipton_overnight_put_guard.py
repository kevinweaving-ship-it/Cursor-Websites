#!/usr/bin/env python3
"""Patch live api.py: refuse Lipton RACING/gun after 17:00 / before 10:00.

Client JS already no-ops tracker T+ when day-done. Server PUT and board
RACING did not, so a T+ POST overnight could stamp a gun and skip close.
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_OVERNIGHT_PUT_GUARD_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

HELPER = r'''
def _lipton_overnight_harbour(rid, st=None):
    """''' + MARKER + r''' Harbour closed (17:00–10:00) and no real gun race."""
    if "lipton" not in str(rid or "").lower():
        return False
    st = st if isinstance(st, dict) else {}
    if st.get("force_racing") or st.get("simulate"):
        return False
    try:
        mins = int(_live_race_sa_minutes_now())
    except Exception:
        return False
    if not (mins >= 17 * 60 or mins < 10 * 60):
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

OLD_DEF = '''def _set_regatta_live_board_status(regatta_id: str, status: str) -> str:
'''

NEW_DEF = HELPER + OLD_DEF

OLD_RACING = '''        if st == "RACING":
            phase = str(lr.get("phase") or "").strip().lower()
            was_done = bool(lr.get("race_complete")) or phase in ("finished", "idle", "")
'''

NEW_RACING = '''        if st == "RACING" and _lipton_overnight_harbour(rid, lr):
            st = "LIVE"
            ent["live_board_status"] = "LIVE"
            all_d[rid] = ent
            _write_wc_regatta_header_icons(all_d)
        if st == "RACING":
            phase = str(lr.get("phase") or "").strip().lower()
            was_done = bool(lr.get("race_complete")) or phase in ("finished", "idle", "")
'''

OLD_PUT = '''    cur = _read_live_race_state(rid)
    phase = str(body.get("phase") or cur.get("phase") or "idle").strip().lower()
'''

NEW_PUT = '''    cur = _read_live_race_state(rid)
    if _lipton_overnight_harbour(rid, cur):
        # ''' + MARKER + ''' tracker T+ / RACING must not stamp a gun after close.
        try:
            _set_regatta_live_board_status(rid, "LIVE")
        except Exception:
            pass
        out = dict(cur)
        out["ok"] = True
        out["overnight"] = True
        out["board_status"] = "LIVE"
        return out
    phase = str(body.get("phase") or cur.get("phase") or "idle").strip().lower()
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n_def = text.count(OLD_DEF)
    n_racing = text.count(OLD_RACING)
    n_put = text.count(OLD_PUT)
    if n_def != 1 or n_racing != 1 or n_put != 1:
        print(f"FAIL guard: def={n_def} racing={n_racing} put={n_put}", file=sys.stderr)
        return 1
    text = text.replace(OLD_DEF, NEW_DEF, 1)
    text = text.replace(OLD_RACING, NEW_RACING, 1)
    text = text.replace(OLD_PUT, NEW_PUT, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
