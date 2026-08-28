#!/usr/bin/env python3
"""Prepend Race 5 start-line crossings onto Lipton -dev replay JSON.

Start is a line (pin device 4 / leftEnd, RC / rightEnd), not a rounding.
Crossing time = first GPS interpolation from prestart side onto the course
after the gun. Not DTL-at-gun. Not Nett. No OCS in Race 5.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_mark_rounding import fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
OUT_COPY = ROOT / "js/lipton-dev-replay.json"
R = 6371000.0
GUN = 1787838601000


def xy(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * math.cos(math.radians(lat0)) * R
    y = math.radians(lat - lat0) * R
    return x, y


def main() -> int:
    doc = fetch_regatta_doc()
    r5 = next(r for r in _j22_division(doc)["races"] if int(r.get("raceNumber") or 0) == 5)
    s0 = r5["starts"][0]
    if s0.get("ocsParticipants"):
        raise SystemExit(f"OCS present, refusing to invent a clean start order: {s0.get('ocsParticipants')}")
    line = s0["startLine"]
    pin_lat, pin_lon = line["leftEnd"]
    rc_lat, rc_lon = line["rightEnd"]
    lat0 = (pin_lat + rc_lat) / 2
    lon0 = (pin_lon + rc_lon) / 2
    ax, ay = xy(pin_lat, pin_lon, lat0, lon0)
    bx, by = xy(rc_lat, rc_lon, lat0, lon0)
    abx, aby = bx - ax, by - ay
    ab_len = math.hypot(abx, aby)

    def signed(lat, lon):
        px, py = xy(lat, lon, lat0, lon0)
        apx, apy = px - ax, py - ay
        dist = (abx * apy - aby * apx) / ab_len
        along = (apx * abx + apy * aby) / ab_len
        return dist, along

    gun_signed = []
    for st in s0["startingStats"]:
        lon, lat = st["positionAtStart"]["coordinates"]
        d, _along = signed(lat, lon)
        gun_signed.append(d)
    flip = sorted(gun_signed)[len(gun_signed) // 2] < 0

    rows = fetch_rows(GUN - 5000, GUN + 120_000)
    boat_by = defaultdict(list)
    for rec in rows:
        if rec.get("role") == "competitor" and rec.get("race_number") in (5, None, 0, 5.0):
            boat_by[rec["sail_number"]].append(rec)
    for sail in list(boat_by):
        boat_by[sail] = sorted(boat_by[sail], key=lambda x: x["ts"])
        if any(p.get("race_number") == 5 for p in boat_by[sail]):
            boat_by[sail] = [p for p in boat_by[sail] if p.get("race_number") == 5]

    ranked = []
    for sail, pts in boat_by.items():
        prev = None
        hit = None
        for p in pts:
            d, along = signed(p["latitude"], p["longitude"])
            if flip:
                d = -d
            if prev is not None and p["ts"] >= GUN:
                d0, t0, a0 = prev
                if d0 > 0 and d <= 0:
                    frac = d0 / (d0 - d) if d0 != d else 1.0
                    ts = int(t0 + (p["ts"] - t0) * frac)
                    along_x = a0 + (along - a0) * frac
                    if -15 <= along_x <= ab_len + 15:
                        hit = ts
                        break
            if p["ts"] >= GUN - 2000:
                prev = (d, p["ts"], along)
        if hit is None:
            raise SystemExit(f"no start-line crossing for {sail}")
        ranked.append({"boat": sail, "ts_ms": hit})
    ranked.sort(key=lambda r: r["ts_ms"])

    prev = json.loads(OUT.read_text())
    rest = [p for p in prev.get("passes") or [] if p.get("id") != "ST"]
    prev["passes"] = [
        {"id": "ST", "label": "ST", "lap": 0, "mark": 0, "boats": ranked},
        *rest,
    ]
    src = prev.setdefault("sources", {})
    src["start_order"] = (
        "teleapi GPS crossing of Firestore startLine (pin leftEnd / RC rightEnd) after R5 gun. "
        "Not dtlMm. Not OCS. Gaps under ~2.5s are near-ties (GPS ~5 m)."
    )
    text = json.dumps(prev, indent=2, ensure_ascii=False) + "\n"
    OUT.write_text(text)
    OUT_COPY.write_text(text)
    print(json.dumps({"ok": True, "n": len(ranked), "first": ranked[0]["boat"], "last": ranked[-1]["boat"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
