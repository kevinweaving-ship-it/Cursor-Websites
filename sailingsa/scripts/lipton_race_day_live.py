#!/usr/bin/env python3
"""Lipton race-day live grabber — dock → course → T− → racing.

Continuously polls teleapi + Firestore, advances phases, commits mark
positions when the fleet leaves the club, arms race mode on T−/gun, and
appends the same GPS JSONL we use for historical replay packing.

  python3 sailingsa/scripts/lipton_race_day_live.py
  python3 sailingsa/scripts/lipton_race_day_live.py --once
  python3 sailingsa/scripts/lipton_race_day_live.py --poll 2

Does not write Nett / public results from tracker places.
Run on This Mac for race day.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_dev_record_telemetry import append_unique, load_seen  # noqa: E402
from lipton_mark_rounding import MARK_SN, fetch_rows  # noqa: E402
from lipton_race_day_phases import (  # noqa: E402
    BoatSample,
    MarkSample,
    Phase,
    PhaseInput,
    TrackerRace,
    advance_phase,
)
from lipton_vakaros import (  # noqa: E402
    LIPTON_SLUG,
    _j22_division,
    fetch_regatta_doc,
    parse_ts,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
STATE_PATH = DATA / "lipton_race_day_state.json"
MARKS_PATH = DATA / "lipton_race_day_marks.json"
SAST = ZoneInfo("Africa/Johannesburg")
POLL_DEFAULT = 2.0


def _last_finished_race(doc: dict) -> int:
    div = _j22_division(doc)
    last = 0
    for r in div.get("races") or []:
        n = int(r.get("raceNumber") or 0)
        fins = r.get("finishes") or []
        if len(fins) >= 8:
            last = max(last, n)
    return last


def _active_tracker_race(doc: dict, expect: int) -> TrackerRace | None:
    div = _j22_division(doc)
    races = sorted(
        [r for r in (div.get("races") or []) if int(r.get("raceNumber") or 0) > 0],
        key=lambda r: int(r.get("raceNumber") or 0),
    )
    if not races:
        return None
    # Prefer expected / unfinished race with a start
    pick = None
    for r in races:
        n = int(r.get("raceNumber") or 0)
        fins = r.get("finishes") or []
        if n == expect:
            pick = r
            break
        if len(fins) < 8:
            pick = r
            break
    if pick is None:
        pick = races[-1]
    s0 = (pick.get("starts") or [{}])[0] or {}
    gun = parse_ts(s0.get("startTime")) if s0.get("startTime") else None
    line = s0.get("startLine") or {}
    return TrackerRace(
        race_number=int(pick.get("raceNumber") or expect),
        gun_ts_ms=int(gun.timestamp() * 1000) if gun is not None else None,
        finish_count=len(pick.get("finishes") or []),
        ocs=[str(x) for x in (s0.get("ocsParticipants") or [])],
        has_start_line=bool(line.get("leftEnd") and line.get("rightEnd")),
    )


def _samples_from_rows(rows: list[dict]) -> tuple[list[BoatSample], list[MarkSample]]:
    # latest ping per sail / mark
    boats: dict[str, dict] = {}
    marks: dict[str, dict] = {}
    sn_to_mark = {sn: name for name, sn in MARK_SN.items()}
    for rec in rows:
        sn = rec.get("sn")
        ts = int(rec.get("ts") or 0)
        if sn in sn_to_mark:
            name = sn_to_mark[sn]
            prev = marks.get(name)
            if not prev or ts >= prev["ts"]:
                marks[name] = rec
            continue
        if rec.get("role") == "competitor" and rec.get("sail_number"):
            sail = str(rec["sail_number"])
            prev = boats.get(sail)
            if not prev or ts >= prev["ts"]:
                boats[sail] = rec
    boat_samples = [
        BoatSample(
            sail=sail,
            sog_ms=float(r["sog"]) if r.get("sog") is not None else None,
            lat=float(r["latitude"]) if r.get("latitude") is not None else None,
            lon=float(r["longitude"]) if r.get("longitude") is not None else None,
        )
        for sail, r in boats.items()
    ]
    mark_samples = [
        MarkSample(
            name=name,
            lat=float(r["latitude"]),
            lon=float(r["longitude"]),
            sog_ms=float(r["sog"]) if r.get("sog") is not None else None,
        )
        for name, r in marks.items()
        if r.get("latitude") is not None and r.get("longitude") is not None
    ]
    return boat_samples, mark_samples


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "phase": Phase.DOCK.value,
        "marks_committed": False,
        "committed_marks": {},
        "race_number": 6,
        "updated_at": None,
    }


def _save_state(state: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    if state.get("committed_marks"):
        MARKS_PATH.write_text(json.dumps(state["committed_marks"], indent=2) + "\n")


def _jsonl_for_race(race: int) -> Path:
    return DATA / f"lipton_r{race}_telemetry.jsonl"


def tick(state: dict, *, lookback_ms: int = 45_000) -> dict:
    now = int(time.time() * 1000)
    doc = fetch_regatta_doc()
    last_fin = _last_finished_race(doc)
    expect = max(1, last_fin + 1)
    tracker = _active_tracker_race(doc, expect)

    rows = fetch_rows(now - lookback_ms, now + 1_000)
    boats, marks = _samples_from_rows(rows)
    prev = Phase(state.get("phase") or Phase.DOCK.value)
    result = advance_phase(
        prev,
        PhaseInput(
            now_ms=now,
            boats=boats,
            marks=marks,
            last_finished_race=last_fin,
            tracker_race=tracker,
            marks_committed=bool(state.get("marks_committed")),
            committed_marks=state.get("committed_marks") or {},
        ),
    )

    race = int(result.race_number)
    out = _jsonl_for_race(race)
    seen = load_seen(out)
    # Also keep a continuous day file from dock onward
    day = DATA / "lipton_race_day_live.jsonl"
    day_seen = load_seen(day)
    added_race = append_unique(out, rows, seen)
    added_day = append_unique(day, rows, day_seen)

    course = result.course
    state.update(
        {
            "phase": result.phase.value,
            "race_number": race,
            "marks_committed": result.marks_committed,
            "committed_marks": result.committed_marks,
            "course": course,
            "race_mode": result.race_mode,
            "t_minus_s": result.t_minus_s,
            "t_plus_s": result.t_plus_s,
            "gun_ts_ms": result.gun_ts_ms,
            "reasons": result.reasons,
            "boats_n": len(boats),
            "marks_n": len(marks),
            "rows_poll": len(rows),
            "added_race": added_race,
            "added_day": added_day,
            "jsonl_race": str(out),
            "slug": LIPTON_SLUG,
            "updated_at": datetime.now(SAST).isoformat(),
            "note": "Grab only. Do not write Nett from tracker places.",
        }
    )
    _save_state(state)
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description="Lipton race-day live grabber")
    ap.add_argument("--once", action="store_true", help="Single poll then exit")
    ap.add_argument("--poll", type=float, default=POLL_DEFAULT, help="Seconds between polls")
    args = ap.parse_args()
    state = _load_state()
    print(json.dumps({"start": True, "state": STATE_PATH.as_posix(), "phase": state.get("phase")}), flush=True)
    try:
        while True:
            state = tick(state)
            slim = {
                k: state[k]
                for k in (
                    "phase",
                    "race_number",
                    "race_mode",
                    "t_minus_s",
                    "t_plus_s",
                    "marks_committed",
                    "boats_n",
                    "marks_n",
                    "added_race",
                    "added_day",
                    "reasons",
                    "updated_at",
                )
                if k in state
            }
            if state.get("course"):
                c = state["course"]
                slim["course"] = {
                    "id": c.get("id"),
                    "label": c.get("label"),
                    "look_for": (c.get("expect") or {}).get("look_for"),
                    "passes_hint": (c.get("expect") or {}).get("passes_hint"),
                }
            print(json.dumps(slim, ensure_ascii=False), flush=True)
            if args.once:
                return 0
            time.sleep(max(0.5, float(args.poll)))
    except KeyboardInterrupt:
        print(json.dumps({"stopped": True, "phase": state.get("phase")}), flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
