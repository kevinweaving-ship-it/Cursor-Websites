#!/usr/bin/env python3
"""Merge split wc_regatta_header_icons.json mirrors on live.

A 1-key Lipton stub with newest mtime made _read_wc_regatta_header_icons return only
Lipton and drop the rest of the catalog. Stale copies still had R5 + first_gun 15:51.

Merges per-regatta (newest mtime wins per key), then overlays the current Lipton
live-race board (LIVE / current Rn / no leftover gun) unless a real race is underway.
Writes every known mirror via /tmp + cp (Path.write_text as root can EACCES).

Never overwrites live api.py.
"""
from __future__ import annotations

import json
import os
import sys
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
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.system(f"cp {tmp} {path}")
    os.system(f"chown www-data:www-data {path} >/dev/null 2>&1 || true")
    os.system(f"chmod 664 {path} >/dev/null 2>&1 || true")


def _merge_mirrors() -> dict:
    merged: dict = {}
    rid_mt: dict = {}
    for p in ICON_PATHS:
        if not p.is_file():
            continue
        try:
            mt = float(p.stat().st_mtime)
            o = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print("skip", p, e)
            continue
        if not isinstance(o, dict):
            continue
        print("read", p, "nkeys", len(o), "mtime", int(mt))
        for rid, rec in o.items():
            k = str(rid)
            if k not in merged or mt >= rid_mt.get(k, -1.0):
                merged[k] = rec if isinstance(rec, dict) else rec
                rid_mt[k] = mt
    return merged


def _overlay_lipton(merged: dict) -> dict:
    ent = dict(merged.get(RID) or {})
    # Keep venue from any copy if the newest Lipton stub dropped it.
    if not ent.get("venue"):
        for p in ICON_PATHS:
            if not p.is_file():
                continue
            try:
                rec = (json.loads(p.read_text(encoding="utf-8")) or {}).get(RID) or {}
            except Exception:
                continue
            if isinstance(rec, dict) and rec.get("venue"):
                ent["venue"] = rec.get("venue")
                if rec.get("venue_co_host"):
                    ent["venue_co_host"] = rec.get("venue_co_host")
                break
    racing = False
    rk = str(ent.get("live_race_key") or "").strip().upper()
    if STATE.is_file():
        st = json.loads(STATE.read_text(encoding="utf-8"))
        gun = st.get("gun_at")
        phase = str(st.get("phase") or "").strip().lower()
        status = str(st.get("status") or st.get("board_status") or "").strip().upper()
        racing = bool(gun) and (phase in ("racing", "start") or status == "RACING")
        if st.get("race_key"):
            rk = str(st.get("race_key")).strip().upper()
        if racing:
            print("leave racing gun", gun, "rk", rk)
            merged[RID] = ent
            return merged
    ent["live_board_status"] = "LIVE"
    if rk.startswith("R"):
        ent["live_race_key"] = rk
    ent["live_race_gun_at"] = None
    for k in ("first_gun", "live_board_start", "race_start"):
        ent.pop(k, None)
    merged[RID] = ent
    print("lipton overlay", {k: ent.get(k) for k in ("live_board_status", "live_race_key", "live_race_gun_at", "venue")})
    return merged


def main() -> int:
    merged = _merge_mirrors()
    if not merged:
        print("FAIL empty merge", file=sys.stderr)
        return 1
    merged = _overlay_lipton(merged)
    print("merged_nkeys", len(merged))
    for p in ICON_PATHS:
        if not p.is_file() and not p.parent.is_dir():
            continue
        _write_json(p, merged)
        print("wrote", p, "nkeys", len(json.loads(p.read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
