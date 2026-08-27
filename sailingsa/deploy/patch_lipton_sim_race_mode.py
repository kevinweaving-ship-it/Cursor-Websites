#!/usr/bin/env python3
"""Put Lipton 2026 URL into simulated Race mode (RACING).

After 17:00 SAST the live-race schedule forces day_close → LIVE and clears the gun,
so a JSON-only flip does not stick. This:

1) Patches _live_race_apply_sa_schedule to honor force_racing / simulate
2) Writes live-race JSON + every icons JSON mirror to RACING with a gun
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

SCHEDULE_OLD = """    st = dict(st or {})
    mins = _live_race_sa_minutes_now()
    now = _regatta_sa_now()
    changed = False

    # --- Day close from 17:00 (harbour overnight) ---
"""

SCHEDULE_NEW = """    st = dict(st or {})
    # Simulate Race mode: skip 17:00 day_close so RACING can be drilled after hours.
    if st.get("force_racing") or st.get("simulate"):
        st["day_done"] = False
        st["track_idle"] = False
        st["race_complete"] = False
        st["applied"] = False
        st["race_armed"] = True
        st["phase"] = "racing"
        st["status"] = "RACING"
        st["board_status"] = "RACING"
        st["schedule_slot"] = "simulate_racing"
        if not _normalize_gun_at_iso(st.get("gun_at") or ""):
            try:
                st["gun_at"] = _regatta_sa_now().isoformat()
            except Exception:
                st["gun_at"] = datetime.now(timezone(timedelta(hours=2))).isoformat()
            st["gun_source"] = "simulate"
        st["cam_show"] = _live_race_cam_should_show(False, True)
        try:
            _set_regatta_live_board_status(rid, "RACING")
        except Exception:
            pass
        return _write_live_race_state(rid, st)

    mins = _live_race_sa_minutes_now()
    now = _regatta_sa_now()
    changed = False

    # --- Day close from 17:00 (harbour overnight) ---
"""


def _load_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return None
        o = json.loads(raw)
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def patch_api_py() -> None:
    original = API_PY.read_text(encoding="utf-8")
    if 'if st.get("force_racing") or st.get("simulate"):' in original:
        print("api.py already has force_racing guard")
        return
    n = original.count(SCHEDULE_OLD)
    if n != 1:
        raise SystemExit(f"schedule insert: expected 1, found {n}")
    updated = original.replace(SCHEDULE_OLD, SCHEDULE_NEW, 1)
    bak = API_PY.with_name(API_PY.name + ".bak-sim-race-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(API_PY, bak)
    API_PY.write_text(updated, encoding="utf-8")
    print("patched", API_PY, "backup", bak)


def set_racing_state() -> None:
    now = datetime.now(SAST).isoformat()
    st = _load_json(LIVE_JSON) or {}
    st["regatta_id"] = RID
    st["force_racing"] = True
    st["simulate"] = True
    st["day_done"] = False
    st["track_idle"] = False
    st["race_complete"] = False
    st["applied"] = False
    st["race_armed"] = True
    st["phase"] = "racing"
    st["status"] = "RACING"
    st["board_status"] = "RACING"
    st["schedule_slot"] = "simulate_racing"
    # R5 is already posted on the sheet — simulated race is the next one (R6).
    st["race_key"] = "R6"
    st["gun_at"] = now
    st["gun_source"] = "simulate"
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
    print("live-race JSON RACING", LIVE_JSON, "gun", now, "race_key", st["race_key"])

    for p in ICON_PATHS:
        d = _load_json(p)
        if d is None:
            print("skip icons", p)
            continue
        ent = dict(d.get(RID) or {})
        ent["live_board_status"] = "RACING"
        ent["live_race_key"] = st["race_key"]
        ent["live_race_gun_at"] = now
        d[RID] = ent
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("icons RACING", p)


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    if only in ("all", "js"):
        patch_api_py()
    if only in ("all", "state"):
        set_racing_state()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
