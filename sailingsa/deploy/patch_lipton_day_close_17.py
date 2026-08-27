#!/usr/bin/env python3
"""Patch live api.py: Lipton day-close 17:00 SAST; don't blink Start on LIVE.

Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_DAY_CLOSE_17_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_DOC = '''    """Automate overnight → 10:00 wake → 12:00 R4 arm → 19:00 day close.

    Never invents gun_at / T+. Race start auto = arm next Rn + wait for Vakaros T+ (or SA PUT).
    """'''

NEW_DOC = '''    """Automate overnight → 10:00 wake → 12:00 next-Rn arm → 17:00 day close.

    Never invents gun_at / T+. Race start auto = arm next Rn + wait for Vakaros T+ (or SA PUT).
    # ''' + MARKER + '''
    """'''

OLD_CLOSE = '''    # --- Day close from 19:00 (harbour overnight) ---
    if mins >= 19 * 60:
        board_now = ""
        try:
            board_now = _regatta_live_board_status_override(rid) or ""
        except Exception:
            board_now = str(st.get("board_status") or "").strip().upper()
        # Super admin RACING wins over the clock.
        if board_now == "RACING":
            st["day_done"] = False
            st["track_idle"] = False
            st["phase"] = "racing"
            st["status"] = "RACING"
            st["board_status"] = "RACING"
            st["schedule_slot"] = "sa_racing"
            st["race_armed"] = True
            return _write_live_race_state(rid, st)
'''

NEW_CLOSE = '''    # --- Day close from 17:00 (harbour overnight). R6 arms tomorrow 10:00/12:00. ---
    if mins >= 17 * 60:
        # Stuck board=RACING / stale gun must not block overnight LIVE after racing.
'''

OLD_BLINK = '''    ".regatta-live-board-start{display:inline-flex;align-items:center;gap:6px;background:#15803d;color:#fff;font-size:13px;font-weight:900;line-height:1.1;letter-spacing:.04em;padding:6px 12px;border-radius:6px;animation:ssa-live-start-blink 1.6s ease-in-out infinite}"'''

NEW_BLINK = '''    ".regatta-live-board-start{display:inline-flex;align-items:center;gap:6px;background:#15803d;color:#fff;font-size:13px;font-weight:900;line-height:1.1;letter-spacing:.04em;padding:6px 12px;border-radius:6px}"
    '.regatta-page[data-live-race-underway="1"] .regatta-live-board-start{animation:ssa-live-start-blink 1.6s ease-in-out infinite}' '''


OLD_GET = '''    board = _regatta_live_board_status_override(rid) or "LIVE"
    st["board_status"] = board
    # HARD LOCK: never report LIVE while race gun is running.
    if st.get("gun_at") and str(st.get("phase") or "").lower() == "racing" and board != "POSTPONED":
'''

NEW_GET = '''    board = _regatta_live_board_status_override(rid) or "LIVE"
    # LIPTON_NO_GUN_LIVE_OVERRIDE_V1
    # No gun + day closed / finished: icons RACING must not resurrect the board.
    if not st.get("gun_at") and (
        st.get("day_done")
        or str(st.get("phase") or "").strip().lower() in ("finished", "idle")
        or str(st.get("schedule_slot") or "") == "day_close"
    ):
        if board == "RACING":
            board = "LIVE"
            try:
                _set_regatta_live_board_status(rid, "LIVE")
            except Exception:
                pass
    st["board_status"] = board
    # HARD LOCK: never report LIVE while race gun is running.
    if st.get("gun_at") and str(st.get("phase") or "").lower() == "racing" and board != "POSTPONED":
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER not in text:
        for label, old in (("doc", OLD_DOC), ("close", OLD_CLOSE), ("blink", OLD_BLINK)):
            n = text.count(old)
            if n != 1:
                print(f"FAIL {label}: found {n}", file=sys.stderr)
                return 1
        text = text.replace(OLD_DOC, NEW_DOC, 1)
        text = text.replace(OLD_CLOSE, NEW_CLOSE, 1)
        text = text.replace(OLD_BLINK, NEW_BLINK, 1)
        print("patched", MARKER)
    else:
        print("already", MARKER)
    if "LIPTON_NO_GUN_LIVE_OVERRIDE_V1" not in text:
        n = text.count(OLD_GET)
        if n != 1:
            print(f"FAIL get-override: found {n}", file=sys.stderr)
            return 1
        text = text.replace(OLD_GET, NEW_GET, 1)
        print("patched LIPTON_NO_GUN_LIVE_OVERRIDE_V1")
    else:
        print("already LIPTON_NO_GUN_LIVE_OVERRIDE_V1")
    API_PATH.write_text(text, encoding="utf-8")
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
