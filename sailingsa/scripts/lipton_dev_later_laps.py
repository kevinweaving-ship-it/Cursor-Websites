#!/usr/bin/env python3
"""Append lap-2/3 mark passes onto Lipton -dev replay JSON from teleapi trail.

Keeps frozen lap-1 passes as-is. Does not write docs/lipton_2026_r5_mark_orders.json.
Does not invent boats that never rounded. Not a Nett source.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_mark_rounding import (  # noqa: E402
    COURSE_PASSES,
    MARK_SN,
    SAST,
    bearing_deg,
    fetch_rows,
    haversine_m,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
OUT_COPY = ROOT / "js/lipton-dev-replay.json"


def _mark_relocated(a: dict, b: dict, *, thresh_m: float = 50.0) -> bool:
    """True when buoy GPS jumped — RO towed the mark (wind shift), not GPS noise."""
    return haversine_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"]) >= thresh_m


def nearest_mark(marks_sorted: list[dict], ts: int) -> dict | None:
    """Buoy ping for this instant. Prefer same station after a mid-race mark move.

    RO often tows weather/wing between laps. Do not keep the pre-tow lat/lon once
    the buoy has relocated — that creates false checksum gaps on later laps.
    """
    if not marks_sorted:
        return None
    lo, hi = 0, len(marks_sorted) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if marks_sorted[mid]["ts"] <= ts:
            lo = mid
        else:
            hi = mid - 1
    last = marks_sorted[lo] if marks_sorted[lo]["ts"] <= ts else None
    nxt = None
    if last is None:
        nxt = marks_sorted[0]
    elif lo + 1 < len(marks_sorted):
        nxt = marks_sorted[lo + 1]
    # If the next ping is a relocation and we are past the tow window, use the new station.
    if last and nxt and _mark_relocated(last, nxt):
        mid_ts = (last["ts"] + nxt["ts"]) // 2
        if ts >= mid_ts:
            return nxt
        return last
    stale_ms = 120_000
    if last and ts - last["ts"] <= stale_ms:
        return last
    if nxt and nxt["ts"] - ts <= stale_ms:
        return nxt
    if last and nxt:
        return last if (ts - last["ts"]) <= (nxt["ts"] - ts) else nxt
    return last or nxt


def mark_move_events(marks_sorted: list[dict], *, thresh_m: float = 50.0, gun_ts_ms: int | None = None) -> list[dict]:
    """List buoy relocations (RO towed mark). For -dev audit / checksum notes."""
    out = []
    if not marks_sorted:
        return out
    prev = marks_sorted[0]
    for cur in marks_sorted[1:]:
        d = haversine_m(prev["latitude"], prev["longitude"], cur["latitude"], cur["longitude"])
        if d >= thresh_m:
            row = {
                "from_ts": int(prev["ts"]),
                "to_ts": int(cur["ts"]),
                "moved_m": round(d, 1),
                "from": {"lat": round(prev["latitude"], 6), "lon": round(prev["longitude"], 6)},
                "to": {"lat": round(cur["latitude"], 6), "lon": round(cur["longitude"], 6)},
            }
            if gun_ts_ms is not None:
                row["from_gun_s"] = round((prev["ts"] - gun_ts_ms) / 1000)
                row["to_gun_s"] = round((cur["ts"] - gun_ts_ms) / 1000)
            out.append(row)
            prev = cur
        else:
            # stay on the current station centroid for noise
            prev = cur
    return out


def rounding_candidates(pts: list[dict], marks_sorted: list[dict], *, enter_m=80.0, leave_extra_m=8.0, gap_inbound_ms=15_000):
    """Heading + closest distance on every received point. Do not invent GPS.

    Tracker holes before a real CPA still count: if the next ping is already in
    the zone, that *is* received rounding data. A hole where the boat reappears
    hundreds of metres past the mark is a checksum miss, not a guess.
    """
    if not pts or not marks_sorted:
        return []
    series = []
    prev_ts = None
    for p in pts:
        mk = nearest_mark(marks_sorted, p["ts"])
        if not mk:
            continue
        d = haversine_m(p["latitude"], p["longitude"], mk["latitude"], mk["longitude"])
        gap = None if prev_ts is None else p["ts"] - prev_ts
        series.append((p, d, gap))
        prev_ts = p["ts"]
    out = []
    i = 0
    n = len(series)
    while i < n:
        p, d, gap = series[i]
        if d > enter_m:
            i += 1
            continue
        inbound = bool(gap is None or gap >= gap_inbound_ms)
        if not inbound:
            k = i - 1
            while k >= 0 and (p["ts"] - series[k][0]["ts"]) <= 180_000:
                if series[k][1] >= enter_m:
                    inbound = True
                    break
                k -= 1
        hdg = p.get("heading")
        if hdg is not None and not inbound:
            brg = _bearing_to_mark(p, nearest_mark(marks_sorted, p["ts"]))
            if brg is not None and abs(_ang_diff(hdg, brg)) <= 95:
                inbound = True
        best = (d, p)
        j = i
        left = False
        while j < n and (series[j][0]["ts"] - p["ts"]) < 180_000:
            dj = series[j][1]
            if dj < best[0]:
                best = (dj, series[j][0])
            if dj >= best[0] + leave_extra_m:
                left = True
                break
            j += 1
        if not left and best[0] <= 25.0:
            nxt_gap = series[j][2] if j < n else None
            if j >= n or (nxt_gap is not None and nxt_gap >= gap_inbound_ms):
                left = True
        if inbound and left and best[0] <= enter_m:
            bp = best[1]
            out.append(
                {
                    "ts": bp["ts"],
                    "sast": datetime.fromtimestamp(bp["ts"] / 1000, SAST).strftime("%H:%M:%S"),
                    "closest_m": round(best[0], 1),
                    "sog_kn": round((bp.get("sog") or 0) * 1.94384, 1),
                    "heading": bp.get("heading"),
                }
            )
            skip_until = bp["ts"] + 40_000
            while i < n and series[i][0]["ts"] < skip_until:
                i += 1
            continue
        i += 1
    out.extend(_gap_roundings(series, marks_sorted, enter_m, {c["ts"] for c in out}))
    out.sort(key=lambda c: c["ts"])
    return out


def _chord_cpa(p0: dict, p1: dict, mk: dict) -> tuple[float, int]:
    best = None
    dt = p1["ts"] - p0["ts"]
    for k in range(41):
        f = k / 40
        lat = p0["latitude"] + (p1["latitude"] - p0["latitude"]) * f
        lon = p0["longitude"] + (p1["longitude"] - p0["longitude"]) * f
        d = haversine_m(lat, lon, mk["latitude"], mk["longitude"])
        ts = int(p0["ts"] + dt * f)
        if best is None or d < best[0]:
            best = (d, ts)
    return best


def _destination(lat: float, lon: float, bearing: float, dist_m: float) -> tuple[float, float]:
    r = 6371000.0
    ang = dist_m / r
    br = math.radians(bearing)
    p1 = math.radians(lat)
    l1 = math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(ang) + math.cos(p1) * math.sin(ang) * math.cos(br))
    l2 = l1 + math.atan2(math.sin(br) * math.sin(ang) * math.cos(p1), math.cos(ang) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def _reverse_dr_cpa(p: dict, mk: dict, heading: float, sog_ms: float, max_ms: int) -> tuple[float, int] | None:
    if sog_ms < 0.4 or max_ms <= 0:
        return None
    back = (heading + 180) % 360
    best = None
    step = 1.0
    t = 0.0
    max_s = min(max_ms / 1000.0, 480.0)
    while t <= max_s:
        lat, lon = _destination(p["latitude"], p["longitude"], back, sog_ms * t)
        d = haversine_m(lat, lon, mk["latitude"], mk["longitude"])
        if best is None or d < best[0]:
            best = (d, int(p["ts"] - t * 1000))
        t += step
    return best


def _gap_roundings(series, marks_sorted, enter_m, existing: set[int]) -> list[dict]:
    """Hole between two received pings that still brackets a mark. Map tails stay gappy."""
    extra = []
    n = len(series)
    for i in range(1, n):
        p0, _d0, _g0 = series[i - 1]
        p1, _d1, g1 = series[i]
        if not g1 or g1 < 20_000:
            continue
        mk = nearest_mark(marks_sorted, (p0["ts"] + p1["ts"]) // 2)
        if not mk:
            continue
        best_d, best_ts = _chord_cpa(p0, p1, mk)
        if best_d > enter_m:
            hdg = p1.get("heading")
            sog = p1.get("sog") or 0.0
            if hdg is None and i + 1 < n:
                hdg = bearing_deg(p1["latitude"], p1["longitude"], series[i + 1][0]["latitude"], series[i + 1][0]["longitude"])
                dt = (series[i + 1][0]["ts"] - p1["ts"]) / 1000.0
                if dt > 0:
                    sog = haversine_m(p1["latitude"], p1["longitude"], series[i + 1][0]["latitude"], series[i + 1][0]["longitude"]) / dt
            back = _reverse_dr_cpa(p1, mk, hdg, sog, g1) if hdg is not None else None
            if not back or back[0] > enter_m:
                continue
            best_d, best_ts = back
        if any(abs(best_ts - t) < 40_000 for t in existing):
            continue
        existing.add(best_ts)
        extra.append(
            {
                "ts": best_ts,
                "sast": datetime.fromtimestamp(best_ts / 1000, SAST).strftime("%H:%M:%S"),
                "closest_m": round(best_d, 1),
                "sog_kn": round((p1.get("sog") or 0) * 1.94384, 1),
                "heading": p1.get("heading"),
                "via": "gap",
            }
        )
    return extra


def _bearing_to_mark(p: dict, mk: dict | None) -> float | None:
    if not mk:
        return None
    return bearing_deg(p["latitude"], p["longitude"], mk["latitude"], mk["longitude"])


def _ang_diff(a, b) -> float:
    return (b - a + 180) % 360 - 180


def main() -> int:
    prev = json.loads(OUT.read_text())
    gun = int(prev["gun_ts_ms"])
    end = int(prev.get("end_ts_ms") or prev["first_finish_ts_ms"]) + 15_000
    finish_map = {row["boat"]: int(row["ts_ms"]) for row in prev.get("finish") or []}
    l1_passes = [p for p in prev.get("passes") or [] if str(p.get("id") or "").startswith("L1-")]
    last_l1 = {}
    for passing in l1_passes:
        for row in passing.get("boats") or []:
            last_l1[row["boat"]] = int(row.get("ts_ms") or row.get("ts"))

    after = min(last_l1.values()) if last_l1 else gun
    print("fetch", after, end, flush=True)
    rows = fetch_rows(after, end)
    marks_by_sn = defaultdict(list)
    boat_by = defaultdict(list)
    for rec in rows:
        if rec.get("sn") in MARK_SN.values():
            marks_by_sn[rec["sn"]].append(rec)
        if rec.get("role") == "competitor" and rec.get("race_number") in (5, None, 0, 5.0):
            boat_by[rec["sail_number"]].append(rec)
    for sn in marks_by_sn:
        marks_by_sn[sn] = sorted(marks_by_sn[sn], key=lambda x: x["ts"])
    for sail in boat_by:
        boat_by[sail] = sorted(boat_by[sail], key=lambda x: x["ts"])
        if any(p.get("race_number") == 5 for p in boat_by[sail]):
            boat_by[sail] = [p for p in boat_by[sail] if p.get("race_number") == 5]

    cands = {sail: {name: rounding_candidates(pts, marks_by_sn.get(sn) or []) for name, sn in MARK_SN.items()} for sail, pts in boat_by.items()}

    later_specs = [s for s in COURSE_PASSES if s["lap"] >= 2]
    last_ts = {sail: last_l1.get(sail, after) for sail in boat_by}
    later_passes = []
    summary = []
    for spec in later_specs:
        ranked = []
        for sail in boat_by:
            fin = finish_map.get(sail, end)
            cutoff = fin - 80_000 if spec["mark"] == "4" else fin
            nxt = next(
                (c for c in cands[sail].get(spec["mark"], []) if last_ts[sail] + 25_000 < c["ts"] < cutoff),
                None,
            )
            if not nxt:
                continue
            last_ts[sail] = nxt["ts"]
            ranked.append({"boat": sail, "ts_ms": int(nxt["ts"]), "sast": nxt["sast"], "closest_m": nxt["closest_m"]})
        ranked.sort(key=lambda r: r["ts_ms"])
        if not ranked:
            continue
        later_passes.append(
            {
                "id": spec["id"],
                "label": f"M{spec['mark']}",
                "lap": spec["lap"],
                "mark": int(spec["mark"]),
                "boats": [{"boat": r["boat"], "ts_ms": r["ts_ms"]} for r in ranked],
            }
        )
        summary.append(
            {
                "id": spec["id"],
                "n": len(ranked),
                "first": ranked[0]["boat"] if ranked else None,
                "sast": ranked[0]["sast"] if ranked else None,
                "last": ranked[-1]["sast"] if ranked else None,
            }
        )

    prev["passes"] = l1_passes + later_passes
    prev["mark_labels"] = [p["label"] for p in prev["passes"]]
    note = prev.get("note") or ""
    if "later laps" not in note.lower():
        prev["note"] = (
            "Race 5 tracker. Each pass is one rounding; M1/M2/M3/M4 repeat on later laps. "
            "Rank re-sorts per pass. Splits = previous recorded pass to this pass (first M1 vs gun). "
            "Fin = gun to finish. Empty cell = that boat did not round that mark on trail. Not Nett."
        )
    text = json.dumps(prev, indent=2, ensure_ascii=False) + "\n"
    OUT.write_text(text)
    OUT_COPY.write_text(text)
    print(json.dumps({"ok": True, "rows": len(rows), "boats": len(boat_by), "later": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
