#!/usr/bin/env python3
"""Post Lipton R5, restore LIVE chip (not racing), next race R6."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
API_PY = Path("/var/www/sailingsa/api/api.py")
LIVE_JSON = Path(f"/var/tmp/sailingsa_live_race_{RID}.json")
ICON_PATHS = [
    Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
]

R5_TIMES = [
    ("26", 1, "T+01:11:59.412"),
    ("32", 2, "T+01:12:26.477"),
    ("23", 3, "T+01:12:50.380"),
    ("8", 4, "T+01:13:13.907"),
    ("31", 5, "T+01:13:26.542"),
    ("28", 6, "T+01:13:39.235"),
    ("49", 7, "T+01:13:46.140"),
    ("34", 8, "T+01:13:55.716"),
    ("52", 9, "T+01:14:04.109"),
    ("48", 10, "T+01:14:08.766"),
    ("46", 11, "T+01:15:28.464"),
    ("63", 12, "T+01:15:37.036"),
    ("44", 13, "T+01:15:46.731"),
    ("14", 14, "T+01:15:51.019"),
    ("55", 15, "T+01:16:40.551"),
    ("51", 16, "T+01:18:53.225"),
    ("43", 17, "T+01:19:26.529"),
]

HIDE_BADGE = '''    # Racing done / no current race: do not show LIVE or Racing chip.
    if lr.get("day_done") or lr.get("track_idle") or (
        not gun_at and phase in ("idle", "finished", "")
    ):
        return ""
'''

HIDE_ATTRS = '''    if lr.get("day_done") or lr.get("track_idle") or (
        not gun and phase in ("idle", "finished", "")
    ):
        lipton = "1" if "lipton" in str(regatta_id or "").strip().lower() else "0"
        return (
            f' data-live-board-tint-rid="{rid_esc}" data-live-board-page-status=""'
            f' data-live-race-underway="0" data-live-day-done="1"'
            f' data-live-lipton="{lipton}"'
        )
'''

JS_HIDE = """              document.querySelectorAll('.regatta-live-board-row').forEach(function(row){
                row.setAttribute('hidden','');
                row.style.display='none';
              });
              document.querySelectorAll('.regatta-live-board[data-live-board-rid="'+rid+'"]').forEach(function(btn){
"""

JS_LIVE = """              applyAll(rid, 'LIVE');
              document.querySelectorAll('.regatta-live-board[data-live-board-rid="'+rid+'"]').forEach(function(btn){
"""


def restore_live_chip(s: str) -> str:
    s = s.replace(HIDE_BADGE, "", 1)
    s = s.replace(HIDE_ATTRS, "", 1)
    if JS_HIDE in s:
        s = s.replace(JS_HIDE, JS_LIVE, 1)
    return s


def set_live_mode() -> None:
    st = {}
    if LIVE_JSON.is_file():
        try:
            st = json.loads(LIVE_JSON.read_text(encoding="utf-8")) or {}
        except Exception:
            st = {}
    st["regatta_id"] = RID
    st["phase"] = "finished"
    st["status"] = "LIVE"
    st["board_status"] = "LIVE"
    st["gun_at"] = None
    st["gun_source"] = None
    st["day_done"] = True
    st["track_idle"] = False
    st["race_armed"] = False
    st["race_complete"] = True
    st["applied"] = True
    st["race_key"] = "R6"
    st["schedule_slot"] = "day_close"
    rt = dict(st.get("race_times") or {})
    rt["R5"] = [{"bow": b, "place": p, "elapsed": e} for b, p, e in R5_TIMES]
    st["race_times"] = rt
    LIVE_JSON.write_text(json.dumps(st, indent=2), encoding="utf-8")
    try:
        shutil.chown(str(LIVE_JSON), user="www-data", group="www-data")
    except Exception:
        os.system(f"chown www-data:www-data {LIVE_JSON}")
    os.chmod(LIVE_JSON, 0o664)
    for p in ICON_PATHS:
        try:
            raw = p.read_text(encoding="utf-8")
            if not raw.strip():
                continue
            d = json.loads(raw)
            if not isinstance(d, dict):
                continue
            ent = dict(d.get(RID) or {})
            ent["live_board_status"] = "LIVE"
            ent["live_race_key"] = "R6"
            ent.pop("live_race_gun_at", None)
            d[RID] = ent
            p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as e:
            print("icon skip", p, e)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else API_PY)
    original = path.read_text(encoding="utf-8")
    updated = restore_live_chip(original)
    if updated != original:
        bak = path.with_name(path.name + ".bak-r5-live-" + time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, bak)
        path.write_text(updated, encoding="utf-8")
        print("restored LIVE chip", path, "backup", bak)
    else:
        print("LIVE chip already visible or hide strings missing")
    set_live_mode()
    print("live mode LIVE next R6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
