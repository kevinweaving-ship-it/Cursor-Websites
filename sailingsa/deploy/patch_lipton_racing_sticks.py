#!/usr/bin/env python3
"""Lipton: Super-admin RACING must stick so racing can be enabled.

Stops public poll from demoting RACING→LIVE when there is no gun.
Stamps a gun when entering RACING so T+ / race-mode UI can run.
19:00 day_close does not override an SA RACING board.
Then sets the Lipton URL to RACING (R6).
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

DEMOTE_OLD = """        elif st == "RACING" and not race_active:
            # Between races: honour LIVE (or fall back) — clear stuck RACING badge.
            st = "LIVE"
            if (_regatta_live_board_status_override(rid) or "") == "RACING":
                try:
                    _set_regatta_live_board_status(rid, "LIVE")
                except Exception:
                    pass
"""

DEMOTE_NEW = """        elif st == "RACING" and not race_active:
            # Super admin set RACING: keep it. Missing gun must not flip back to LIVE.
            pass
"""

GUN_OLD = """                # else leave gun null until tracker T+ — do not invent wall gun
"""

GUN_NEW = """                else:
                    try:
                        lr["gun_at"] = _regatta_sa_now().isoformat()
                    except Exception:
                        lr["gun_at"] = datetime.now(timezone(timedelta(hours=2))).isoformat()
                    lr["gun_source"] = lr.get("gun_source") or "sa_board"
"""

CLOSE_OLD = """    # --- Day close from 19:00 (harbour overnight) ---
    if mins >= 19 * 60:
        if not st.get("day_done") or not st.get("track_idle") or st.get("gun_at"):
"""

CLOSE_NEW = """    # --- Day close from 19:00 (harbour overnight) ---
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
        if not st.get("day_done") or not st.get("track_idle") or st.get("gun_at"):
"""


def patch_api_py() -> None:
    original = API_PY.read_text(encoding="utf-8")
    s = original
    for old, new, label in (
        (DEMOTE_OLD, DEMOTE_NEW, "poll demote"),
        (GUN_OLD, GUN_NEW, "stamp gun"),
        (CLOSE_OLD, CLOSE_NEW, "day_close SA RACING"),
    ):
        if new in s and old not in s:
            print("already", label)
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1, found {n}")
        s = s.replace(old, new, 1)
    if s == original:
        print("api.py already patched")
        return
    bak = API_PY.with_name(API_PY.name + ".bak-racing-sticks-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(API_PY, bak)
    API_PY.write_text(s, encoding="utf-8")
    print("patched", API_PY, "backup", bak)


def _load_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return None
        o = json.loads(raw)
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def enable_racing() -> None:
    now = datetime.now(SAST).isoformat()
    st = _load_json(LIVE_JSON) or {}
    st["regatta_id"] = RID
    st["day_done"] = False
    st["track_idle"] = False
    st["race_complete"] = False
    st["applied"] = False
    st["race_armed"] = True
    st["phase"] = "racing"
    st["status"] = "RACING"
    st["board_status"] = "RACING"
    st["schedule_slot"] = "sa_racing"
    st["race_key"] = "R6"
    st["gun_at"] = now
    st["gun_source"] = "sa_board"
    st["elapsed"] = None
    st["elapsed_raw"] = None
    st["cam_show"] = True
    st["updated_at"] = now
    payload = json.dumps(st, indent=2, ensure_ascii=False) + "\n"
    tmp = LIVE_JSON.with_name(LIVE_JSON.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, LIVE_JSON)
    try:
        shutil.chown(str(LIVE_JSON), user="www-data", group="www-data")
    except Exception:
        os.system(f"chown www-data:www-data {LIVE_JSON}")
    os.chmod(LIVE_JSON, 0o664)
    print("live-race JSON RACING", st["gun_at"], st["race_key"])
    for p in ICON_PATHS:
        d = _load_json(p)
        if d is None:
            print("skip icons", p)
            continue
        ent = dict(d.get(RID) or {})
        ent["live_board_status"] = "RACING"
        ent["live_race_key"] = "R6"
        ent["live_race_gun_at"] = now
        d[RID] = ent
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("icons RACING", p)


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    if only in ("all", "js"):
        patch_api_py()
    if only in ("all", "state"):
        enable_racing()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
