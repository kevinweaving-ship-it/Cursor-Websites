#!/usr/bin/env python3
"""Force Lipton live-race JSON + icons mirrors to LIVE / no gun (between races / overnight)."""
from __future__ import annotations

import json
import os
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
STATE = Path("/var/tmp/sailingsa_live_race_2026-08-29-lipton-challenge-cup.json")
ICON_PATHS = [
    Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/deploy/wc_regatta_header_icons.json"),
]


def _write_json(path: Path, data) -> None:
    tmp = Path("/tmp") / (path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.system(f"cp {tmp} {path}")
    os.system(f"chown www-data:www-data {path} >/dev/null 2>&1 || true")
    os.system(f"chmod 664 {path} >/dev/null 2>&1 || true")


def main() -> None:
    st = json.loads(STATE.read_text(encoding="utf-8"))
    st["phase"] = "finished"
    st["status"] = "LIVE"
    st["board_status"] = "LIVE"
    st["gun_at"] = None
    st["gun_source"] = None
    st["day_done"] = True
    st["track_idle"] = True
    st["race_armed"] = False
    st["race_complete"] = True
    st["schedule_slot"] = "day_close"
    st["elapsed"] = None
    st["elapsed_raw"] = None
    st["force_racing"] = False
    st["simulate"] = False
    # Last completed race is R5. race_key=R6 + finished makes next_race_key skip to R7.
    st["race_key"] = "R5"
    _write_json(STATE, st)
    os.system(f"chown www-data:www-data {STATE} >/dev/null 2>&1 || true")
    os.system(f"chmod 664 {STATE} >/dev/null 2>&1 || true")

    for p in ICON_PATHS:
        if not p.is_file():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        ent = dict(d.get(RID) or {})
        ent["live_board_status"] = "LIVE"
        ent["live_race_gun_at"] = None
        d[RID] = ent
        _write_json(p, d)
        print("icons LIVE", p)

    print("state", {k: st.get(k) for k in ("phase", "board_status", "gun_at", "day_done", "race_key", "schedule_slot")})


if __name__ == "__main__":
    main()
