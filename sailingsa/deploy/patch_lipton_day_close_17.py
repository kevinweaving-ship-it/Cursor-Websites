#!/usr/bin/env python3
"""Patch live api.py: Lipton day-close 17:00 SAST; no fake gun; overnight stays R5.

Never overwrite live api.py with the repo copy. Unique-string patches only.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_DAY_CLOSE_17_V2"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_CLOSE_HEAD = '''    # --- Day close from 19:00 (harbour overnight). R6 arms tomorrow 10:00/12:00. ---
    if mins >= 19 * 60:
        board_now = ""
        try:
            board_now = _regatta_live_board_status_override(rid) or ""
        except Exception:
            board_now = str(st.get("board_status") or "").strip().upper()
        # Super admin RACING/POSTPONED is not overnight-closed.
        if board_now in ("RACING", "POSTPONED"):
            st["day_done"] = False
            st["track_idle"] = False
            st["status"] = board_now
            st["board_status"] = board_now
            st["schedule_slot"] = "sa_board"
            if board_now == "RACING":
                st["phase"] = "racing"
                st["race_armed"] = True
            return _write_live_race_state(rid, st)
        # Stuck board=RACING / stale gun must not block overnight LIVE after racing.
'''

NEW_CLOSE_HEAD = '''    # --- Day close from 17:00 (harbour overnight). R6 arms tomorrow 10:00/12:00. ---
    # ''' + MARKER + '''
    if mins >= 17 * 60:
        board_now = ""
        try:
            board_now = _regatta_live_board_status_override(rid) or ""
        except Exception:
            board_now = str(st.get("board_status") or "").strip().upper()
        has_gun_close = bool(_normalize_gun_at_iso(st.get("gun_at") or ""))
        phase_close = str(st.get("phase") or "").strip().lower()
        race_active_close = (
            has_gun_close
            and phase_close == "racing"
            and not bool(st.get("race_complete"))
        )
        # POSTPONED, or a real gun-underway race, is not overnight-closed.
        # Stuck board=RACING with no gun must not skip harbour close.
        if board_now == "POSTPONED" or (board_now == "RACING" and race_active_close):
            st["day_done"] = False
            st["track_idle"] = False
            st["status"] = board_now
            st["board_status"] = board_now
            st["schedule_slot"] = "sa_board"
            if board_now == "RACING":
                st["phase"] = "racing"
                st["race_armed"] = True
            return _write_live_race_state(rid, st)
        # Pin last completed Rn so overnight R6 does not become tomorrow R7.
        try:
            rt = st.get("race_times") if isinstance(st.get("race_times"), dict) else {}
            filled_n = []
            for k, rows in (rt or {}).items():
                m = re.match(r"^R(\\d+)$", str(k), re.I)
                if not m:
                    continue
                if isinstance(rows, list) and any(
                    isinstance(r, dict)
                    and (r.get("place") is not None or r.get("finish_ms") is not None)
                    for r in rows
                ):
                    filled_n.append(int(m.group(1)))
            if filled_n:
                st["race_key"] = "R" + str(max(filled_n))
        except Exception:
            pass
        # Stuck board=RACING / stale gun must not block overnight LIVE after racing.
'''

OLD_CLOSE_BODY = '''            st["race_armed"] = False
            st["gun_at"] = None
            st["gun_source"] = None
            st["phase"] = "finished" if (st.get("race_times") or st.get("race_complete")) else "idle"
            st["status"] = "LIVE"
            st["board_status"] = "LIVE"
            changed = True
'''

NEW_CLOSE_BODY = '''            st["race_armed"] = False
            st["gun_at"] = None
            st["gun_source"] = None
            st["phase"] = "finished" if (st.get("race_times") or st.get("race_complete")) else "idle"
            st["status"] = "LIVE"
            st["board_status"] = "LIVE"
            st["force_racing"] = False
            st["simulate"] = False
            changed = True
'''

OLD_SHOW_START = '''    show_start = status_key in ("LIVE", "POSTPONED") and not gun_at
'''

NEW_SHOW_START = '''    show_start = status_key in ("LIVE", "POSTPONED") and not gun_at and not bool(lr.get("day_done"))
'''

OLD_JS_CLOSE = '''      if((h*60+m)>=19*60) return true;
'''

NEW_JS_CLOSE = '''      if((h*60+m)>=17*60) return true;
'''

OLD_HEAL = '''    if not race_done:
        if not st.get("gun_at") and icons_gun and (board == "RACING" or phase == "racing"):
'''

NEW_HEAL = '''    if not race_done and not st.get("day_done") and str(st.get("schedule_slot") or "") != "day_close":
        if not st.get("gun_at") and icons_gun and (board == "RACING" or phase == "racing"):
'''

OLD_INVENT = '''                else:
                    try:
                        lr["gun_at"] = _regatta_sa_now().isoformat()
                    except Exception:
                        lr["gun_at"] = datetime.now(timezone(timedelta(hours=2))).isoformat()
                    lr["gun_source"] = lr.get("gun_source") or "sa_board"
'''

NEW_INVENT = '''                else:
                    # Lipton: never invent wall-clock gun / fake T+. Wait for Vakaros or SA PUT.
                    if "lipton" in rid.lower():
                        lr["gun_at"] = None
                        lr["gun_source"] = None
                    else:
                        try:
                            lr["gun_at"] = _regatta_sa_now().isoformat()
                        except Exception:
                            lr["gun_at"] = datetime.now(timezone(timedelta(hours=2))).isoformat()
                        lr["gun_source"] = lr.get("gun_source") or "sa_board"
'''

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


def _patch_once(text: str, label: str, old: str, new: str) -> tuple[str, bool]:
    n = text.count(old)
    if n == 0 and new.strip() and new in text:
        print(f"already {label}")
        return text, True
    if n != 1:
        print(f"FAIL {label}: found {n}", file=sys.stderr)
        return text, False
    return text.replace(old, new, 1), True


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if "LIPTON_PRE_WAKE_CLOSE_V1" in text:
        # Close is 17:00 + 00:00–10:00; V2 unique strings were consumed.
        print("already close-17 via LIPTON_PRE_WAKE_CLOSE_V1")
        print("ok", API_PATH)
        return 0
    ok = True
    if MARKER not in text:
        text, p = _patch_once(text, "close-head", OLD_CLOSE_HEAD, NEW_CLOSE_HEAD)
        ok = ok and p
        text, p = _patch_once(text, "close-body", OLD_CLOSE_BODY, NEW_CLOSE_BODY)
        ok = ok and p
        text, p = _patch_once(text, "show-start", OLD_SHOW_START, NEW_SHOW_START)
        ok = ok and p
        text, p = _patch_once(text, "js-close", OLD_JS_CLOSE, NEW_JS_CLOSE)
        ok = ok and p
        text, p = _patch_once(text, "heal", OLD_HEAL, NEW_HEAL)
        ok = ok and p
        text, p = _patch_once(text, "invent-gun", OLD_INVENT, NEW_INVENT)
        ok = ok and p
        if ok:
            print("patched", MARKER)
    else:
        print("already", MARKER)
    if "LIPTON_NO_GUN_LIVE_OVERRIDE_V1" not in text:
        text, p = _patch_once(text, "get-override", OLD_GET, NEW_GET)
        ok = ok and p
        if p:
            print("patched LIPTON_NO_GUN_LIVE_OVERRIDE_V1")
    else:
        print("already LIPTON_NO_GUN_LIVE_OVERRIDE_V1")
    if not ok:
        return 1
    API_PATH.write_text(text, encoding="utf-8")
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
