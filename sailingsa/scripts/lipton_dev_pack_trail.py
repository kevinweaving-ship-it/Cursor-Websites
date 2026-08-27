#!/usr/bin/env python3
"""Downsample Race 4 GPS trail for the -dev canvas map. Trail only. Not Nett.

Do not linearly fill GPS holes: that draws chords through marks.
Marks are a 1 s series (same grid as boats) so the buoy is where it was
when boats actually rounded, not a race-long average.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_mark_rounding import MARK_SN, fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
OUT = ROOT / "sailingsa/frontend/js/lipton-dev-trail.json"
OUT_COPY = ROOT / "js/lipton-dev-trail.json"
STEP_MS = 1000
RACE = 4


def q(v):
    return round(float(v), 5)


def pt_latlon(lat, lon):
    return {"lat": q(lat), "lon": q(lon)}


def race_lines(race: int) -> dict:
    """Start and finish are lines (pin + RC). Not roundings. Device 4 is the pin."""
    doc = fetch_regatta_doc()
    r = next(x for x in _j22_division(doc)["races"] if int(x.get("raceNumber") or 0) == race)
    s0 = r["starts"][0]
    left, right = s0["startLine"]["leftEnd"], s0["startLine"]["rightEnd"]
    start = {"left": pt_latlon(left[0], left[1]), "right": pt_latlon(right[0], right[1])}
    finishes = sorted(r.get("finishes") or [], key=lambda f: f.get("finishingTime") or "")
    finish = None
    if finishes:
        f0 = finishes[0]
        ll, rr = f0["lineLeftLocation"]["coordinates"], f0["lineRightLocation"]["coordinates"]
        finish = {"left": pt_latlon(ll[1], ll[0]), "right": pt_latlon(rr[1], rr[0])}
    return {"start_line": start, "finish_line": finish}


def grid_series(pts: list[dict], gun: int, n: int) -> dict:
    lat = [None] * n
    lon = [None] * n
    for p in pts:
        idx = int(round((p["ts"] - gun) / STEP_MS))
        if idx < 0 or idx >= n:
            continue
        lat[idx] = q(p["latitude"])
        lon[idx] = q(p["longitude"])
    return {"lat": lat, "lon": lon}


def main() -> int:
    replay = json.loads(REPLAY.read_text())
    gun = int(replay["gun_ts_ms"])
    end = int(replay.get("play_end_ts_ms") or replay["end_ts_ms"])
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
        boats[sail] = grid_series(
            [p for p in pts if gun - STEP_MS <= p["ts"] <= end + STEP_MS],
            gun,
            n,
        )

    marks = {}
    for name, sn in MARK_SN.items():
        pts = sorted(marks_by.get(sn) or [], key=lambda x: x["ts"])
        if not pts:
            continue
        marks[name] = grid_series(
            [p for p in pts if gun - STEP_MS <= p["ts"] <= end + STEP_MS],
            gun,
            n,
        )

    lines = race_lines(RACE)
    payload = {
        "race_number": RACE,
        "gun_ts_ms": gun,
        "end_ts_ms": end,
        "step_ms": STEP_MS,
        "n": n,
        "boats": boats,
        "marks": marks,
        "start_line": lines["start_line"],
        "finish_line": lines["finish_line"],
        "note": "Race 4 teleapi GPS, 1 s samples. Marks are time series. Start/finish are pin–RC lines. No interpolated holes. Not Nett.",
    }
    text = json.dumps(payload, separators=(",", ":")) + "\n"
    OUT.write_text(text)
    OUT_COPY.write_text(text)
    print(json.dumps({
        "ok": True,
        "bytes": len(text),
        "boats": len(boats),
        "n": n,
        "marks": list(marks),
        "mark_hits": {k: sum(1 for x in v["lat"] if x is not None) for k, v in marks.items()},
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
