#!/usr/bin/env python3
"""Correct Lipton -dev replay packs for mid-race mark moves (RO tow / wind shift).

Uses packed trail JSON (time-series buoy GPS) — no teleapi. Rebuilds mark passes
with lap-correct buoy stations, recomputes checksum on sailed marks only, and
records mark_moves for the audit line.

  python3 sailingsa/scripts/lipton_dev_correct_mark_moves.py
  python3 sailingsa/scripts/lipton_dev_correct_mark_moves.py --races 1,2,5
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_dev_checksum import build_checksum  # noqa: E402
from lipton_dev_later_laps import mark_move_events, rounding_candidates  # noqa: E402
from lipton_dev_pass_assign import pack_passes_with_fleet_windows  # noqa: E402
from lipton_mark_rounding import MARK_SN  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def paths(race: int) -> tuple[Path, Path, Path, Path]:
    if race == 4:
        return (
            ROOT / "sailingsa/frontend/js/lipton-dev-replay.json",
            ROOT / "js/lipton-dev-replay.json",
            ROOT / "sailingsa/frontend/js/lipton-dev-trail.json",
            ROOT / "js/lipton-dev-trail.json",
        )
    s = f"-r{race}"
    return (
        ROOT / f"sailingsa/frontend/js/lipton-dev-replay{s}.json",
        ROOT / f"js/lipton-dev-replay{s}.json",
        ROOT / f"sailingsa/frontend/js/lipton-dev-trail{s}.json",
        ROOT / f"js/lipton-dev-trail{s}.json",
    )


def trail_to_points(series: dict, origin: int, step: int) -> list[dict]:
    lats = series.get("lat") or []
    lons = series.get("lon") or []
    out = []
    for i, (la, lo) in enumerate(zip(lats, lons)):
        if la is None or lo is None:
            continue
        out.append(
            {
                "ts": int(origin + i * step),
                "latitude": float(la),
                "longitude": float(lo),
                "heading": None,
                "sog": 0.0,
            }
        )
    return out


def detect_wl(cands: dict, gun: int, first_finish: int, fleet_n: int) -> bool:
    min_fleet = max(8, (fleet_n + 1) // 2)
    m2_hits = sum(
        1
        for sail in cands
        if any(gun + 120_000 < c["ts"] < first_finish - 120_000 for c in cands[sail].get("2") or [])
    )
    return m2_hits < min_fleet


def lap_mark_stations(mark_passes: list[dict], marks_by_name: dict, gun: int) -> dict:
    """Median buoy fix at each packed pass (proof marks moved between laps)."""
    out = {}
    for p in mark_passes:
        mk = str(p["mark"])
        pts = marks_by_name.get(mk) or []
        if not pts or not p.get("boats"):
            continue
        ts_list = [int(b["ts_ms"]) for b in p["boats"] if b.get("ts_ms") is not None]
        if not ts_list:
            continue
        med = sorted(ts_list)[len(ts_list) // 2]
        # nearest mark ping to median boat time
        best = min(pts, key=lambda r: abs(r["ts"] - med))
        out[p["id"]] = {
            "mark": mk,
            "lat": round(best["latitude"], 6),
            "lon": round(best["longitude"], 6),
            "ts_ms": int(best["ts"]),
            "gun_s": round((best["ts"] - gun) / 1000),
            "fleet_n": len(p["boats"]),
        }
    return out


def correct_race(race: int) -> dict:
    replay_a, replay_b, trail_a, trail_b = paths(race)
    replay = json.loads(replay_a.read_text())
    trail = json.loads(trail_a.read_text() if trail_a.exists() else trail_b.read_text())
    origin = int(trail["grid_start_ts_ms"])
    step = int(trail["step_ms"])
    gun = int(replay["gun_ts_ms"])
    finish_rows = replay.get("finish") or []
    finish_ts = {r["boat"]: int(r["ts_ms"]) for r in finish_rows}
    last_finish = max(finish_ts.values()) if finish_ts else int(replay["end_ts_ms"])
    first_finish = min(finish_ts.values()) if finish_ts else last_finish
    st = next((p.get("boats") or [] for p in replay.get("passes") or [] if p.get("id") == "ST"), [])
    if not st:
        raise SystemExit(f"R{race}: missing ST pass")

    marks_by_name = {}
    moves = {}
    for name, series in (trail.get("marks") or {}).items():
        pts = trail_to_points(series, origin, step)
        marks_by_name[str(name)] = pts
        ev = mark_move_events(pts, thresh_m=50.0, gun_ts_ms=gun)
        # keep big moves only (≥50m already); merge tiny chatter already filtered
        if ev:
            moves[str(name)] = [e for e in ev if e["moved_m"] >= 50]

    boat_pts = {
        sail: trail_to_points(series, origin, step)
        for sail, series in (trail.get("boats") or {}).items()
    }
    # Map mark name -> SN list used by rounding_candidates
    sn_to_name = {sn: name for name, sn in MARK_SN.items()}
    marks_by_sn = {}
    for name, pts in marks_by_name.items():
        # name is "1"/"2"/… matching MARK_SN keys
        sn = MARK_SN.get(str(name))
        if sn:
            marks_by_sn[sn] = pts

    cands = {
        sail: {
            name: rounding_candidates(pts, marks_by_sn.get(sn) or [])
            for name, sn in MARK_SN.items()
        }
        for sail, pts in boat_pts.items()
    }
    use_wl = detect_wl(cands, gun, first_finish, len(boat_pts))
    mark_passes = pack_passes_with_fleet_windows(
        cands,
        gun=gun,
        finish_ts=finish_ts,
        last_finish=last_finish,
        use_wl=use_wl,
    )
    stations = lap_mark_stations(mark_passes, marks_by_name, gun)

    # Lap-to-lap deltas for report
    by_mark = defaultdict(list)
    for pid, row in stations.items():
        by_mark[row["mark"]].append((pid, row))
    lap_deltas = []
    for mk, rows in sorted(by_mark.items(), key=lambda x: int(x[0])):
        for a, b in zip(rows, rows[1:]):
            d = _hav(a[1]["lat"], a[1]["lon"], b[1]["lat"], b[1]["lon"])
            lap_deltas.append({"mark": mk, "from": a[0], "to": b[0], "m": round(d, 1)})

    checksum = build_checksum(
        fleet=sorted(replay.get("boats") or boat_pts.keys()),
        st=st,
        mark_passes=mark_passes,
        finish=finish_rows,
        course_passes=[{"id": p["id"], "lap": p["lap"], "mark": str(p["mark"])} for p in mark_passes],
    )

    prev_cs = replay.get("checksum") or {}
    prev_gaps = prev_cs.get("gaps") or []
    replay["passes"] = [{"id": "ST", "label": "ST", "lap": 0, "mark": 0, "boats": st}, *mark_passes]
    replay["mark_labels"] = [p["label"] for p in mark_passes]
    if mark_passes:
        replay["mark1"] = mark_passes[0]["boats"]
    replay["checksum"] = checksum
    replay["mark_moves"] = {
        "note": "Buoy GPS jumps ≥50m (RO tow / wind shift). Roundings use buoy station at boat time.",
        "by_mark": moves,
        "stations_at_passes": stations,
        "lap_deltas_m": lap_deltas,
    }
    if use_wl:
        replay["course"] = {
            "id": "wl",
            "label": "Windward / Leeward",
            "note": "Weather then leeward gate (first of M3/M4). Wing was not rounded by the fleet.",
        }
    src = replay.get("sources") or {}
    src["marks"] = (
        "teleapi/trail every GPS point; heading+closest with lap-correct buoy after mark moves. "
        "Empty = not received."
    )
    replay["sources"] = src

    text = json.dumps(replay, indent=2, ensure_ascii=False) + "\n"
    replay_a.write_text(text)
    replay_b.write_text(text)
    return {
        "race": race,
        "use_wl": use_wl,
        "passes": [p["id"] for p in mark_passes],
        "pass_n": {p["id"]: len(p["boats"]) for p in mark_passes},
        "prev_checksum_ok": prev_cs.get("ok"),
        "prev_gaps": prev_gaps,
        "checksum_ok": checksum["ok"],
        "gaps": checksum["gaps"],
        "sanity_ok": (checksum.get("sanity") or {}).get("ok"),
        "mark_move_marks": sorted(moves.keys(), key=lambda x: int(x)),
        "lap_deltas_m": [d for d in lap_deltas if d["m"] >= 25],
    }


def _hav(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--races", default="1,2,3,4,5")
    args = ap.parse_args()
    races = [int(x) for x in str(args.races).split(",") if x.strip()]
    report = []
    for race in races:
        report.append(correct_race(race))
    print(json.dumps({"ok": True, "races": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
