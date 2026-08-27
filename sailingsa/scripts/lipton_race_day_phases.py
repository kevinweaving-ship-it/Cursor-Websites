#!/usr/bin/env python3
"""Lipton race-day phases — dock → course set → T− → racing.

Pure logic (no network). Live loop is lipton_race_day_live.py.

Phases (operator story):
  DOCK       boats + marks at club, SOG < 1 kn
  COURSE_SET marks committed once boats start moving; record buoy positions
  PRESTART   boats lining up; race = last finished + 1 (tracker race no)
  T_MINUS    tracker T−; sync clock; arm race mode
  RACING     gun / T+; keep grabbing same GPS we archive historically
  FINISHED   finishes in; stop race mode; await next

Always grab GPS from dock outward. Do not write Nett from tracker places.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


KNOT_MS = 0.514444  # 1 kn in m/s
SOG_DOCK_MAX_MS = KNOT_MS  # below 1 kn = dock / idle
SOG_MOVING_MS = KNOT_MS  # at/above 1 kn = moving to course
MARK_COMMIT_MIN = 3  # need at least weather + gate devices
FLEET_IDLE_FRAC = 0.6
FLEET_MOVING_FRAC = 0.35
PRESTART_NEAR_START_M = 400.0


class Phase(str, Enum):
    DOCK = "DOCK"
    COURSE_SET = "COURSE_SET"
    PRESTART = "PRESTART"
    T_MINUS = "T_MINUS"
    RACING = "RACING"
    FINISHED = "FINISHED"


PHASE_ORDER = [
    Phase.DOCK,
    Phase.COURSE_SET,
    Phase.PRESTART,
    Phase.T_MINUS,
    Phase.RACING,
    Phase.FINISHED,
]


@dataclass
class BoatSample:
    sail: str
    sog_ms: float | None
    lat: float | None = None
    lon: float | None = None


@dataclass
class MarkSample:
    name: str  # "1".."4"
    lat: float
    lon: float
    sog_ms: float | None = None


@dataclass
class TrackerRace:
    race_number: int
    gun_ts_ms: int | None = None
    finish_count: int = 0
    ocs: list[str] = field(default_factory=list)
    has_start_line: bool = False


@dataclass
class PhaseInput:
    now_ms: int
    boats: list[BoatSample]
    marks: list[MarkSample]
    last_finished_race: int
    tracker_race: TrackerRace | None
    marks_committed: bool = False
    committed_marks: dict[str, dict] | None = None


@dataclass
class PhaseResult:
    phase: Phase
    race_number: int
    marks_committed: bool
    committed_marks: dict[str, dict]
    race_mode: bool
    t_minus_s: float | None
    t_plus_s: float | None
    gun_ts_ms: int | None
    reasons: list[str]
    grab: bool = True  # always grab dock → course → race

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["phase"] = self.phase.value
        return d


def sog_knots(sog_ms: float | None) -> float | None:
    if sog_ms is None:
        return None
    return float(sog_ms) / KNOT_MS


def fleet_idle_fraction(boats: list[BoatSample]) -> float:
    known = [b for b in boats if b.sog_ms is not None]
    if not known:
        return 0.0
    idle = sum(1 for b in known if b.sog_ms < SOG_DOCK_MAX_MS)
    return idle / len(known)


def fleet_moving_fraction(boats: list[BoatSample]) -> float:
    known = [b for b in boats if b.sog_ms is not None]
    if not known:
        return 0.0
    moving = sum(1 for b in known if b.sog_ms >= SOG_MOVING_MS)
    return moving / len(known)


def expected_race_number(last_finished_race: int, tracker: TrackerRace | None) -> int:
    """Next race = last finished + 1; tracker race number wins when present."""
    nxt = max(1, int(last_finished_race) + 1)
    if tracker and tracker.race_number:
        return int(tracker.race_number)
    return nxt


def snapshot_marks(marks: list[MarkSample]) -> dict[str, dict]:
    out = {}
    for m in marks:
        out[str(m.name)] = {
            "lat": round(float(m.lat), 6),
            "lon": round(float(m.lon), 6),
            "sog_ms": m.sog_ms,
        }
    return out


def t_minus_plus(now_ms: int, gun_ts_ms: int | None) -> tuple[float | None, float | None]:
    if gun_ts_ms is None:
        return None, None
    delta = (gun_ts_ms - now_ms) / 1000.0
    if delta > 0:
        return round(delta, 3), None
    return None, round(-delta, 3)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def boats_near_start_frac(boats: list[BoatSample], start_lat: float, start_lon: float, radius_m: float = PRESTART_NEAR_START_M) -> float:
    known = [b for b in boats if b.lat is not None and b.lon is not None]
    if not known:
        return 0.0
    near = sum(1 for b in known if haversine_m(b.lat, b.lon, start_lat, start_lon) <= radius_m)
    return near / len(known)


def advance_phase(prev: Phase, inp: PhaseInput) -> PhaseResult:
    """One step of the race-day machine."""
    reasons: list[str] = []
    race_no = expected_race_number(inp.last_finished_race, inp.tracker_race)
    gun = inp.tracker_race.gun_ts_ms if inp.tracker_race else None
    t_m, t_p = t_minus_plus(inp.now_ms, gun)
    idle_f = fleet_idle_fraction(inp.boats)
    moving_f = fleet_moving_fraction(inp.boats)
    marks_ok = len(inp.marks) >= MARK_COMMIT_MIN
    committed = bool(inp.marks_committed)
    committed_marks = dict(inp.committed_marks or {})

    # Finish wins when tracker shows finishes for this race.
    if (
        inp.tracker_race
        and inp.tracker_race.race_number == race_no
        and inp.tracker_race.finish_count >= max(8, int(0.5 * max(1, len(inp.boats))))
        and (t_p is not None and t_p > 60)
    ):
        reasons.append(f"finishes={inp.tracker_race.finish_count}")
        return PhaseResult(
            phase=Phase.FINISHED,
            race_number=race_no,
            marks_committed=committed,
            committed_marks=committed_marks,
            race_mode=False,
            t_minus_s=t_m,
            t_plus_s=t_p,
            gun_ts_ms=gun,
            reasons=reasons,
        )

    # Racing: at/after gun
    if gun is not None and inp.now_ms >= gun:
        reasons.append("now>=gun")
        return PhaseResult(
            phase=Phase.RACING,
            race_number=race_no,
            marks_committed=committed or marks_ok,
            committed_marks=committed_marks or (snapshot_marks(inp.marks) if marks_ok else {}),
            race_mode=True,
            t_minus_s=None,
            t_plus_s=t_p,
            gun_ts_ms=gun,
            reasons=reasons,
        )

    # T−: gun in the future
    if gun is not None and t_m is not None and t_m > 0:
        reasons.append(f"T−={t_m:.0f}s")
        return PhaseResult(
            phase=Phase.T_MINUS,
            race_number=race_no,
            marks_committed=committed or marks_ok,
            committed_marks=committed_marks or (snapshot_marks(inp.marks) if marks_ok else {}),
            race_mode=True,
            t_minus_s=t_m,
            t_plus_s=None,
            gun_ts_ms=gun,
            reasons=reasons,
        )

    # Commit marks when we leave dock (boats moving) and marks are visible.
    if not committed and marks_ok and moving_f >= FLEET_MOVING_FRAC:
        committed = True
        committed_marks = snapshot_marks(inp.marks)
        reasons.append("marks_committed_on_move")
        return PhaseResult(
            phase=Phase.COURSE_SET,
            race_number=race_no,
            marks_committed=True,
            committed_marks=committed_marks,
            race_mode=False,
            t_minus_s=t_m,
            t_plus_s=t_p,
            gun_ts_ms=gun,
            reasons=reasons,
        )

    if committed:
        # Prestart if tracker has start line / race armed, or boats clustering near pin mark 4.
        pin = committed_marks.get("4") or (snapshot_marks(inp.marks).get("4") if marks_ok else None)
        near = 0.0
        if pin:
            near = boats_near_start_frac(inp.boats, pin["lat"], pin["lon"])
        if (inp.tracker_race and inp.tracker_race.has_start_line) or near >= 0.3:
            reasons.append(f"prestart near_start={near:.2f}")
            return PhaseResult(
                phase=Phase.PRESTART,
                race_number=race_no,
                marks_committed=True,
                committed_marks=committed_marks,
                race_mode=False,
                t_minus_s=t_m,
                t_plus_s=t_p,
                gun_ts_ms=gun,
                reasons=reasons,
            )
        reasons.append("course_set waiting_lineup")
        return PhaseResult(
            phase=Phase.COURSE_SET,
            race_number=race_no,
            marks_committed=True,
            committed_marks=committed_marks,
            race_mode=False,
            t_minus_s=t_m,
            t_plus_s=t_p,
            gun_ts_ms=gun,
            reasons=reasons,
        )

    # Default dock: idle fleet, marks may be at club
    if idle_f >= FLEET_IDLE_FRAC or not marks_ok:
        reasons.append(f"dock idle_frac={idle_f:.2f} marks={len(inp.marks)}")
        return PhaseResult(
            phase=Phase.DOCK,
            race_number=race_no,
            marks_committed=False,
            committed_marks={},
            race_mode=False,
            t_minus_s=t_m,
            t_plus_s=t_p,
            gun_ts_ms=gun,
            reasons=reasons,
        )

    reasons.append("fallback_dock")
    return PhaseResult(
        phase=Phase.DOCK,
        race_number=race_no,
        marks_committed=committed,
        committed_marks=committed_marks,
        race_mode=False,
        t_minus_s=t_m,
        t_plus_s=t_p,
        gun_ts_ms=gun,
        reasons=reasons + [f"prev={prev.value}"],
    )
