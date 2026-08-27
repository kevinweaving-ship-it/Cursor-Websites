#!/usr/bin/env python3
"""Downsample Race 4 GPS trail for the -dev canvas map. Trail only. Not Nett."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_mark_rounding import MARK_SN, fetch_rows  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
OUT = ROOT / "sailingsa/frontend/js/lipton-dev-trail.json"
OUT_COPY = ROOT / "js/lipton-dev-trail.json"
STEP_MS = 1000
RACE = 4


def q(v):
    return round(float(v), 5)


def main() -> int:
    replay = json.loads(REPLAY.read_text())
    gun = int(replay["gun_ts_ms"])
    end = int(replay.get("play_end_ts_ms") or replay["end_ts_ms"])
    line = None
    print("fetch", gun, end, flush=True)
    rows = fetch_rows(gun - 15_000, end + 5_000)
    boat_by = defaultdict(list)
    marks_by = defaultdict(list)
    for rec in rows:
        if rec.get("sn") in MARK_SN.values():
            marks_by[rec["sn"]].append(rec)
        if rec.get("role") == "competitor" and rec.get("race_number") in (RACE, None, 0, float(RACE)):
            boat_by[rec["sail_number"]].append(rec)
    for sail in list(boat_by):
        pts = sorted(boat_by[sail], key=lambda x: x["ts"])
        if any(p.get("race_number") == RACE for p in pts):
            pts = [p for p in pts if p.get("race_number") == RACE]
        boat_by[sail] = pts

    n = int((end - gun) / STEP_MS) + 1
    boats = {}
    for sail, pts in boat_by.items():
        lat = [None] * n
        lon = [None] * n
        i = 0
        for p in pts:
            if p["ts"] < gun - STEP_MS or p["ts"] > end + STEP_MS:
                continue
            idx = int(round((p["ts"] - gun) / STEP_MS))
            if idx < 0 or idx >= n:
                continue
            lat[idx] = q(p["latitude"])
            lon[idx] = q(p["longitude"])
        # fill small holes
        for i in range(n):
            if lat[i] is not None:
                continue
            lo = i - 1
            while lo >= 0 and lat[lo] is None:
                lo -= 1
            hi = i + 1
            while hi < n and lat[hi] is None:
                hi += 1
            if lo >= 0 and hi < n and hi - lo <= 4:
                f = (i - lo) / (hi - lo)
                lat[i] = round(lat[lo] + (lat[hi] - lat[lo]) * f, 5)
                lon[i] = round(lon[lo] + (lon[hi] - lon[lo]) * f, 5)
        boats[sail] = {"lat": lat, "lon": lon}

    marks = {}
    for name, sn in MARK_SN.items():
        pts = marks_by.get(sn) or []
        if not pts:
            continue
        mid = sorted(pts, key=lambda x: x["ts"])[len(pts) // 2]
        marks[name] = {"lat": q(mid["latitude"]), "lon": q(mid["longitude"])}

    payload = {
        "race_number": RACE,
        "gun_ts_ms": gun,
        "end_ts_ms": end,
        "step_ms": STEP_MS,
        "n": n,
        "boats": boats,
        "marks": marks,
        "note": "Race 4 teleapi GPS, 1 s samples. Play/speed on -dev drive this map. Not Nett.",
    }
    text = json.dumps(payload, separators=(",", ":")) + "\n"
    OUT.write_text(text)
    OUT_COPY.write_text(text)
    print(json.dumps({"ok": True, "bytes": len(text), "boats": len(boats), "n": n, "marks": list(marks)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
