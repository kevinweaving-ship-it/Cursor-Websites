#!/usr/bin/env python3
"""Lipton URL: racing done — hide LIVE/RACING board when no current race.

Event date window still includes today, so the page kept a LIVE chip. When
day_done / track_idle / idle+no gun, omit the live-race board entirely.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

API_PY = Path("/var/www/sailingsa/api/api.py")

BADGE_OLD = """    phase = str(lr.get("phase") or "").strip().lower()
    # HARD LOCK: never show LIVE while race active (gun + racing / board RACING).
    race_active = bool(gun_at) and (
        phase == "racing" or st == "RACING" or not bool(lr.get("race_complete"))
    )
"""

BADGE_NEW = """    phase = str(lr.get("phase") or "").strip().lower()
    # Racing done / no current race: do not show LIVE or Racing chip.
    if lr.get("day_done") or lr.get("track_idle") or (
        not gun_at and phase in ("idle", "finished", "")
    ):
        return ""
    # HARD LOCK: never show LIVE while race active (gun + racing / board RACING).
    race_active = (
        bool(gun_at)
        and phase == "racing"
        and not bool(lr.get("day_done"))
        and not bool(lr.get("race_complete"))
    )
"""

ATTRS_OLD = """    phase = str(lr.get("phase") or "").strip().lower()
    # HARD LOCK: never LIVE while race active.
    racing_ui = (st == "RACING") or (bool(gun) and phase == "racing" and st != "POSTPONED")
    if racing_ui:
        st = "RACING"
    underway = "1" if racing_ui else "0"
"""

ATTRS_NEW = """    phase = str(lr.get("phase") or "").strip().lower()
    if lr.get("day_done") or lr.get("track_idle") or (
        not gun and phase in ("idle", "finished", "")
    ):
        lipton = "1" if "lipton" in str(regatta_id or "").strip().lower() else "0"
        return (
            f' data-live-board-tint-rid="{rid_esc}" data-live-board-page-status=""'
            f' data-live-race-underway="0" data-live-day-done="1"'
            f' data-live-lipton="{lipton}"'
        )
    # HARD LOCK: never LIVE while race active.
    racing_ui = (st == "RACING") or (bool(gun) and phase == "racing" and st != "POSTPONED")
    if racing_ui:
        st = "RACING"
    underway = "1" if racing_ui else "0"
"""

JS_OLD = """              applyAll(rid, 'LIVE');
              document.querySelectorAll('.regatta-live-board[data-live-board-rid="'+rid+'"]').forEach(function(btn){
"""

JS_NEW = """              document.querySelectorAll('.regatta-live-board-row').forEach(function(row){
                row.setAttribute('hidden','');
                row.style.display='none';
              });
              document.querySelectorAll('.regatta-live-board[data-live-board-rid="'+rid+'"]').forEach(function(btn){
"""


def patch_text(s: str) -> str:
    if "Racing done / no current race: do not show LIVE" in s and "regatta-live-board-row').forEach" in s:
        return s
    for old, new, label in (
        (BADGE_OLD, BADGE_NEW, "badge html"),
        (ATTRS_OLD, ATTRS_NEW, "page attrs"),
        (JS_OLD, JS_NEW, "overnightDone hide board"),
    ):
        if new in s and old not in s:
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1, found {n}")
        s = s.replace(old, new, 1)
    if "Racing done / no current race: do not show LIVE" not in s:
        raise SystemExit("badge guard missing")
    return s


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else API_PY)
    original = path.read_text(encoding="utf-8")
    updated = patch_text(original)
    if updated == original:
        print("already patched", path)
        return 0
    bak = path.with_name(path.name + ".bak-no-live-race-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, bak)
    path.write_text(updated, encoding="utf-8")
    print("patched", path)
    print("backup", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
