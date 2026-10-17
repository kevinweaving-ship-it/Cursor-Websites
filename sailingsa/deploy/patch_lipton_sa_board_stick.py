#!/usr/bin/env python3
"""Lipton 2026 only: Super admin LIVE/RACING/POSTPONED sticks. Stop page flash.

POSTPONED here = racing-day AP (event day + 10:00–19:00 SAST).
Entire-event postpone-to-new-date is a different feature — not this chip.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
API_PY = Path("/var/www/sailingsa/api/api.py")
LIVE_JSON = Path(f"/var/tmp/sailingsa_live_race_{RID}.json")
SAST = timezone(timedelta(hours=2))
ICON_PATHS = [
    Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/data/wc_regatta_header_icons.json"),
]

REPS = [
    (
        '    # --- Day close from 17:00 (harbour overnight). R6 arms tomorrow 10:00/12:00. ---\n'
        '    if mins >= 17 * 60:\n'
        '        # Stuck board=RACING / stale gun must not block overnight LIVE after racing.\n',
        '    # --- Day close from 19:00 (harbour overnight). R6 arms tomorrow 10:00/12:00. ---\n'
        '    if mins >= 19 * 60:\n'
        '        board_now = ""\n'
        '        try:\n'
        '            board_now = _regatta_live_board_status_override(rid) or ""\n'
        '        except Exception:\n'
        '            board_now = str(st.get("board_status") or "").strip().upper()\n'
        '        # Super admin RACING/POSTPONED is not overnight-closed.\n'
        '        if board_now in ("RACING", "POSTPONED"):\n'
        '            st["day_done"] = False\n'
        '            st["track_idle"] = False\n'
        '            st["status"] = board_now\n'
        '            st["board_status"] = board_now\n'
        '            st["schedule_slot"] = "sa_board"\n'
        '            if board_now == "RACING":\n'
        '                st["phase"] = "racing"\n'
        '                st["race_armed"] = True\n'
        '            return _write_live_race_state(rid, st)\n'
        '        # Stuck board=RACING / stale gun must not block overnight LIVE after racing.\n',
        "day_close 19:00 + SA",
    ),
    (
        '    # HARD LOCK: never LIVE while race active.\n'
        '    racing_ui = (st == "RACING") or (bool(gun) and phase == "racing" and st != "POSTPONED")\n'
        '    if racing_ui:\n'
        '        st = "RACING"\n'
        '    underway = "1" if racing_ui else "0"\n',
        '    # Lipton 2026: Super admin chip is page mode (LIVE / RACING / POSTPONED).\n'
        '    if "lipton" in str(regatta_id or "").strip().lower():\n'
        '        racing_ui = st == "RACING"\n'
        '        underway = "1" if racing_ui else "0"\n'
        '    else:\n'
        '        racing_ui = (st == "RACING") or (bool(gun) and phase == "racing" and st != "POSTPONED")\n'
        '        if racing_ui:\n'
        '            st = "RACING"\n'
        '        underway = "1" if racing_ui else "0"\n',
        "page attrs SA",
    ),
    (
        '        # HARD LOCK: never apply LIVE while a race is running — keeps board RACING.\n'
        '        if st == "LIVE" and race_active:\n'
        '            st = "RACING"\n'
        '            ent["live_board_status"] = "RACING"\n'
        '            all_d[rid] = ent\n'
        '            _write_wc_regatta_header_icons(all_d)\n',
        '        # Lipton 2026: Super admin LIVE is allowed even if a gun exists.\n'
        '        if st == "LIVE" and race_active and "lipton" not in rid.lower():\n'
        '            st = "RACING"\n'
        '            ent["live_board_status"] = "RACING"\n'
        '            all_d[rid] = ent\n'
        '            _write_wc_regatta_header_icons(all_d)\n',
        "set_status LIVE lock",
    ),
    (
        '    st = _regatta_live_board_status_override(rid) or "LIVE"\n'
        '    # HARD LOCK: poll must never demote an *active* race to LIVE.\n',
        '    st = _regatta_live_board_status_override(rid) or "LIVE"\n'
        '    if "lipton" in rid.lower():\n'
        '        if st not in ("LIVE", "RACING", "POSTPONED"):\n'
        '            st = "LIVE"\n'
        '        return JSONResponse(\n'
        '            {"regatta_id": rid, "status": st},\n'
        '            headers={"Cache-Control": "no-store"},\n'
        '        )\n'
        '    # HARD LOCK: poll must never demote an *active* race to LIVE.\n',
        "GET board SA",
    ),
    (
        '    # HARD LOCK: never report LIVE while race gun is running.\n'
        '    if st.get("gun_at") and str(st.get("phase") or "").lower() == "racing" and board != "POSTPONED":\n',
        '    # Lipton 2026: do not override Super admin LIVE/POSTPONED because a gun exists.\n'
        '    if "lipton" not in rid.lower() and st.get("gun_at") and str(st.get("phase") or "").lower() == "racing" and board != "POSTPONED":\n',
        "GET live-race gun lock",
    ),
    (
        "    /* HARD LOCK: never paint LIVE while race gun is running. */\n"
        "    if (st === 'LIVE' && started) st = 'RACING';\n",
        "    var lipton = !!(pg && pg.getAttribute('data-live-lipton')==='1');\n"
        "    /* Lipton 2026: Super admin LIVE/RACING/POSTPONED is the page mode. */\n"
        "    if (!lipton && st === 'LIVE' && started) st = 'RACING';\n",
        "JS applyAll gun lock",
    ),
    (
        '''          if (st === 'LIVE' && (boardHasStartedGun(rid) || (function(){
            var pg=document.querySelector('.regatta-page[data-live-board-tint-rid="'+rid+'"]');
            return pg && pg.getAttribute('data-live-race-underway')==='1';
          })())) st = 'RACING';''',
        '''          var pgL=document.querySelector('.regatta-page[data-live-board-tint-rid="'+rid+'"]');
          var lipton=!!(pgL && pgL.getAttribute('data-live-lipton')==='1');
          if (!lipton && st === 'LIVE' && (boardHasStartedGun(rid) || (pgL && pgL.getAttribute('data-live-race-underway')==='1'))) st = 'RACING';''',
        "JS refresh lock",
    ),
    (
        "      } else if (st === 'LIVE' || st === 'POSTPONED') {\n"
        "        if (!started) p.setAttribute('data-live-race-underway', '0');\n"
        "      }",
        "      } else if (st === 'LIVE' || st === 'POSTPONED') {\n"
        "        if (lipton || !started) p.setAttribute('data-live-race-underway', '0');\n"
        "      }",
        "JS underway",
    ),
]


def patch_api() -> None:
    s = API_PY.read_text(encoding="utf-8")
    orig = s
    for old, new, label in REPS:
        if new in s and old not in s:
            print("already", label)
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1, found {n}")
        s = s.replace(old, new, 1)
        print("ok", label)
    if s == orig:
        print("api.py already patched")
        return
    bak = API_PY.with_name(API_PY.name + ".bak-sa-board-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(API_PY, bak)
    API_PY.write_text(s, encoding="utf-8")
    print("patched", API_PY, "backup", bak)


def _load(p: Path):
    try:
        o = json.loads(p.read_text(encoding="utf-8"))
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def set_racing() -> None:
    now = datetime.now(SAST).isoformat()
    st = _load(LIVE_JSON) or {}
    st["regatta_id"] = RID
    st["day_done"] = False
    st["track_idle"] = False
    st["race_complete"] = False
    st["applied"] = False
    st["race_armed"] = True
    st["phase"] = "racing"
    st["status"] = "RACING"
    st["board_status"] = "RACING"
    st["schedule_slot"] = "sa_board"
    st["race_key"] = "R6"
    st["gun_at"] = now
    st["gun_source"] = "sa_board"
    payload = json.dumps(st, indent=2, ensure_ascii=False) + "\n"
    tmp = LIVE_JSON.with_name(LIVE_JSON.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, LIVE_JSON)
    try:
        shutil.chown(str(LIVE_JSON), user="www-data", group="www-data")
    except Exception:
        os.system(f"chown www-data:www-data {LIVE_JSON}")
    os.chmod(LIVE_JSON, 0o664)
    for p in ICON_PATHS:
        d = _load(p)
        if not d:
            print("skip", p)
            continue
        ent = dict(d.get(RID) or {})
        ent["live_board_status"] = "RACING"
        ent["live_race_key"] = "R6"
        ent["live_race_gun_at"] = now
        d[RID] = ent
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("icons RACING", p)
    print("state RACING", now)


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    if only in ("all", "js"):
        patch_api()
    if only in ("all", "state"):
        set_racing()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
