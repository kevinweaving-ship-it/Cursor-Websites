#!/usr/bin/env python3
"""Pack Race 10 live mark times from teleapi using replay rounding_candidates.

Writes starts + lockedPass JSON the DEV live table can merge. Empty = not received.
Not Nett. Does not invent GPS.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_dev_later_laps import rounding_candidates  # noqa: E402
from lipton_mark_rounding import MARK_SN, fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sailingsa/frontend/js/lipton-dev-live-passes.json"
STARTS_OUT = ROOT / "sailingsa/frontend/js/lipton-dev-live-starts.json"
R = 6371000.0
RACE = 10
WL_IDS = ["M1", "PIN", "M1b", "PINb", "M1c"]


def ms_iso(value) -> int:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def xy(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * math.cos(math.radians(lat0)) * R
    y = math.radians(lat - lat0) * R
    return x, y


def main() -> int:
    doc = fetch_regatta_doc()
    r10 = next(r for r in _j22_division(doc)["races"] if int(r.get("raceNumber") or 0) == RACE)
    s0 = r10["starts"][0]
    ocs = [str(x) for x in (s0.get("ocsParticipants") or [])]
    gun = ms_iso(s0["startTime"])
    line = s0["startLine"]
    pin_lat, pin_lon = line["leftEnd"]
    rc_lat, rc_lon = line["rightEnd"]
    lat0 = (pin_lat + rc_lat) / 2
    lon0 = (pin_lon + rc_lon) / 2
    ax, ay = xy(pin_lat, pin_lon, lat0, lon0)
    bx, by = xy(rc_lat, rc_lon, lat0, lon0)
    abx, aby = bx - ax, by - ay
    ab_len = math.hypot(abx, aby) or 1

    def signed(lat, lon):
        px, py = xy(lat, lon, lat0, lon0)
        apx, apy = px - ax, py - ay
        dist = (abx * apy - aby * apx) / ab_len
        along = (apx * abx + apy * aby) / ab_len
        return dist, along

    gun_signed = []
    for st in s0.get("startingStats") or []:
        pos = (st.get("positionAtStart") or {}).get("coordinates") or []
        if len(pos) < 2:
            continue
        lon, lat = pos[0], pos[1]
        d, _along = signed(lat, lon)
        gun_signed.append(d)
    flip = bool(gun_signed) and sorted(gun_signed)[len(gun_signed) // 2] < 0

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    before = max(now_ms, gun) + 20_000
    print(json.dumps({"fetch": True, "gun": gun, "before": before, "span_min": round((before - gun) / 60000, 1)}), flush=True)
    rows = fetch_rows(gun - 90_000, before, verbose=True)
    marks_by_sn = defaultdict(list)
    boat_by = defaultdict(list)
    for rec in rows:
        if rec.get("sn") in MARK_SN.values():
            marks_by_sn[rec["sn"]].append(rec)
        if rec.get("role") == "competitor":
            boat_by[rec["sail_number"]].append(rec)
    for sn in marks_by_sn:
        marks_by_sn[sn] = sorted(marks_by_sn[sn], key=lambda x: x["ts"])
    for sail in list(boat_by):
        boat_by[sail] = sorted(boat_by[sail], key=lambda x: x["ts"])
        if any(int(p.get("race_number") or 0) == RACE for p in boat_by[sail]):
            boat_by[sail] = [p for p in boat_by[sail] if int(p.get("race_number") or 0) == RACE]

    def line_hits(pts, look_from, look_to=None):
        hits = []
        prev = None
        for p in pts:
            if p["ts"] < look_from:
                continue
            if look_to is not None and p["ts"] > look_to:
                break
            d, along = signed(p["latitude"], p["longitude"])
            if flip:
                d = -d
            if prev is not None:
                d0, t0, a0 = prev
                if -80 <= along <= ab_len + 80 or -80 <= a0 <= ab_len + 80:
                    if d0 > 0 and d <= 0:
                        frac = d0 / (d0 - d) if d0 != d else 1.0
                        ts = int(t0 + (p["ts"] - t0) * frac)
                        hits.append({"ts": ts, "dir": "enter"})
                    elif d0 <= 0 and d > 0:
                        frac = (-d0) / (d - d0) if d != d0 else 1.0
                        ts = int(t0 + (p["ts"] - t0) * frac)
                        hits.append({"ts": ts, "dir": "exit"})
            prev = (d, p["ts"], along)
        return hits

    ocs_n = {str(x).upper().replace(" ", "") for x in ocs}

    def start_times(sail, pts):
        is_ocs = str(sail).upper().replace(" ", "") in ocs_n
        hits = [h for h in line_hits(pts, gun - (90_000 if is_ocs else 5_000), gun + 180_000) if h["dir"] == "enter"]
        if is_ocs:
            return (hits[1]["ts"] if len(hits) >= 2 else None)
        return next((h["ts"] for h in hits if h["ts"] >= gun - 500), None)

    starts = {}
    for sail, pts in boat_by.items():
        ts = start_times(sail, pts)
        if ts is None:
            continue
        starts[sail] = {"st_ms": int(ts), "ocs": str(sail).upper().replace(" ", "") in ocs_n}

    cands = {
        sail: {name: rounding_candidates(pts, marks_by_sn.get(sn) or []) for name, sn in MARK_SN.items()}
        for sail, pts in boat_by.items()
    }

    def first_cand(sail, mark, after, before_ts):
        return next((c for c in cands[sail].get(str(mark), []) if after < c["ts"] < before_ts), None)

    last_ts = {sail: gun + 6_000 for sail in boat_by}
    locked = {sail: {} for sail in boat_by}
    for sail, st in starts.items():
        locked.setdefault(sail, {})["ST"] = int(st["st_ms"])
        last_ts[sail] = max(last_ts.get(sail, 0), int(st["st_ms"]) + 6_000)

    for lap, (wid, lid) in enumerate((("M1", "PIN"), ("M1b", "PINb"), ("M1c", None)), start=1):
        nxts = {}
        for sail, pts in boat_by.items():
            c = first_cand(sail, "1", last_ts.get(sail, gun) + 2_000, before)
            if not c:
                continue
            locked.setdefault(sail, {})[wid] = int(c["ts"])
            nxts[sail] = c["ts"]
        for sail, ts in nxts.items():
            last_ts[sail] = ts
        if lid is None:
            break
        nxts = {}
        for sail, pts in boat_by.items():
            opts = []
            for mark in ("3", "4"):
                c = first_cand(sail, mark, last_ts.get(sail, gun) + 2_000, before)
                if c:
                    opts.append(c)
            if not opts:
                continue
            c = min(opts, key=lambda x: x["ts"])
            locked.setdefault(sail, {})[lid] = int(c["ts"])
            nxts[sail] = c["ts"]
        for sail, ts in nxts.items():
            last_ts[sail] = ts

    for sail, pts in boat_by.items():
        after = locked.get(sail, {}).get("M1c") or locked.get(sail, {}).get("PINb")
        if not after:
            continue
        hit = next((h for h in line_hits(pts, after + 45_000) if h["ts"] > after + 45_000), None)
        if hit:
            locked[sail]["FIN"] = int(hit["ts"])

    finishes = sorted(r10.get("finishes") or [], key=lambda f: f.get("finishingTime") or "")
    for f in finishes:
        sail = f.get("sailNumber")
        if not sail or not f.get("finishingTime"):
            continue
        try:
            ts = ms_iso(f["finishingTime"])
        except Exception:
            continue
        locked.setdefault(sail, {})["FIN"] = int(ts)

    counts = {k: 0 for k in ["ST", "M1", "PIN", "M1b", "PINb", "M1c", "FIN"]}
    for lock in locked.values():
        for k in counts:
            if lock.get(k) is not None:
                counts[k] += 1

    passes_doc = {
        "gun_ts_ms": gun,
        "race_number": RACE,
        "ocs": ocs,
        "starts": starts,
        "lockedPass": locked,
        "counts": counts,
        "boats": len(boat_by),
        "source": "teleapi + replay rounding_candidates. Empty = not received.",
    }
    start_doc = {
        "gun_ts_ms": gun,
        "ocs": ocs,
        "starts": starts,
        "source": "teleapi GPS start-line crossing for this gun. Empty = not received.",
    }
    OUT.write_text(json.dumps(passes_doc, separators=(",", ":")) + "\n")
    STARTS_OUT.write_text(json.dumps(start_doc, separators=(",", ":")) + "\n")
    print(json.dumps({"ok": True, "out": str(OUT), "counts": counts, "starts": len(starts), "boats": len(boat_by)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
