#!/usr/bin/env python3
"""Checksum Lipton -dev mark passes and finishes. Do not invent GPS.

A pass is complete only when every still-racing boat has a received
rounding (or finish) timestamp. Empty cell = tracker never gave that visit.
"""
from __future__ import annotations

import hashlib
import json


def canonical_rows(boats: list[dict]) -> list[list]:
    rows = []
    for row in boats or []:
        sail = row.get("boat")
        ts = row.get("ts_ms", row.get("ts"))
        if sail is None or ts is None:
            continue
        rows.append([str(sail), int(ts)])
    rows.sort(key=lambda r: (r[1], r[0]))
    return rows


def sha16(payload) -> str:
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def one_pass(pass_id: str, boats: list[dict], fleet: list[str]) -> dict:
    have = {str(r.get("boat")): int(r.get("ts_ms", r.get("ts"))) for r in (boats or []) if r.get("boat") is not None}
    missing = [s for s in fleet if s not in have]
    rows = canonical_rows(boats)
    return {
        "id": pass_id,
        "n": len(have),
        "fleet_n": len(fleet),
        "missing": missing,
        "ok": len(missing) == 0,
        "sha256": sha16({"id": pass_id, "rows": rows}),
    }


def expected_mark_specs(course_passes: list[dict], mark_passes: list[dict]) -> list[dict]:
    """Course template may list extra laps. Only checksum marks the fleet actually sailed.

    A later spec with zero boats is skipped if a later mark still has boats
    (template extra marks, or a wing nobody rounded). Trailing empty specs mean
    a shortened course.
    """
    packed = {p["id"]: p for p in mark_passes}
    last_i = -1
    for i, spec in enumerate(course_passes):
        n = len((packed.get(spec["id"]) or {}).get("boats") or [])
        if n:
            last_i = i
    out = []
    for i, spec in enumerate(course_passes):
        if i > last_i:
            break
        n = len((packed.get(spec["id"]) or {}).get("boats") or [])
        if n == 0:
            continue
        out.append(spec)
    return out


def arrived_in_time(prev_boats: list[dict], this_boats: list[dict], full_fleet: list[str]) -> list[str]:
    """Boats already at the previous mark before this pass ended. Tail still on the last leg is not a gap."""
    if not prev_boats or not this_boats:
        return list(full_fleet)
    this_last = max(int(r.get("ts_ms", r.get("ts"))) for r in this_boats)
    out = []
    seen = set()
    for row in prev_boats:
        sail = row.get("boat")
        ts = row.get("ts_ms", row.get("ts"))
        if sail is None or ts is None:
            continue
        sail = str(sail)
        if sail not in full_fleet:
            continue
        if int(ts) < this_last and sail not in seen:
            seen.add(sail)
            out.append(sail)
    return out or list(full_fleet)


def pass_rank(boats: list[dict]) -> dict[str, int]:
    rows = canonical_rows(boats)
    return {str(sail): i + 1 for i, (sail, _ts) in enumerate(rows)}


def sanity_places_and_times(*, fleet: list[str], st: list[dict], mark_passes: list[dict], finish: list[dict]) -> dict:
    """Place ± must telescope; mark times must increase; legs must sum to Fin−ST.

    Gained places (prev rank − next rank) from ST to Fin must equal start rank − finish rank.
    Adjacent-leg durations must sum to elapsed (Fin − ST) when every pass is present.
    """
    fleet = [str(s) for s in fleet]
    sequence = [("ST", st)]
    sequence.extend((str(p.get("id") or f"P{i}"), p.get("boats") or []) for i, p in enumerate(mark_passes))
    sequence.append(("FIN", finish))
    by_boat: dict[str, list[tuple[str, int]]] = {s: [] for s in fleet}
    for pid, boats in sequence:
        have = {
            str(r.get("boat")): int(r.get("ts_ms", r.get("ts")))
            for r in (boats or [])
            if r.get("boat") is not None and r.get("ts_ms", r.get("ts")) is not None
        }
        for sail, ts in have.items():
            if sail in by_boat:
                by_boat[sail].append((pid, ts))
    ranks = [pass_rank(boats) for _pid, boats in sequence]
    time_fail = []
    place_fail = []
    leg_fail = []
    n_ids = len(sequence)
    for sail in fleet:
        series = by_boat.get(sail) or []
        for i in range(1, len(series)):
            if series[i][1] <= series[i - 1][1]:
                time_fail.append({"boat": sail, "from": series[i - 1][0], "to": series[i][0]})
                break
        if len(series) != n_ids:
            continue
        elapsed = series[-1][1] - series[0][1]
        legs = sum(series[i][1] - series[i - 1][1] for i in range(1, len(series)))
        if abs(elapsed - legs) > 1:
            leg_fail.append(sail)
        delta_sum = 0
        complete = True
        for i in range(len(ranks) - 1):
            a = ranks[i].get(sail)
            b = ranks[i + 1].get(sail)
            if a is None or b is None:
                complete = False
                break
            delta_sum += a - b
        if complete:
            expect = ranks[0][sail] - ranks[-1][sail]
            if delta_sum != expect:
                place_fail.append(
                    {
                        "boat": sail,
                        "start_rank": ranks[0][sail],
                        "fin_rank": ranks[-1][sail],
                        "delta_sum": delta_sum,
                        "expect": expect,
                    }
                )
    return {
        "ok": not time_fail and not place_fail and not leg_fail,
        "time_fail": time_fail,
        "place_fail": place_fail,
        "leg_fail": leg_fail,
        "note": (
            "± from ST to Fin must equal start rank minus finish rank. "
            "Pass times must increase. Adjacent legs must sum to Fin−ST."
        ),
    }


def build_checksum(*, fleet: list[str], st: list[dict], mark_passes: list[dict], finish: list[dict], course_passes: list[dict]) -> dict:
    fleet = [str(s) for s in fleet]
    parts = [one_pass("ST", st, fleet)]
    used_marks = []
    prev_boats = st
    for spec in expected_mark_specs(course_passes, mark_passes):
        got = next((p for p in mark_passes if p["id"] == spec["id"]), {"boats": []})
        boats = got.get("boats") or []
        expect = arrived_in_time(prev_boats, boats, fleet)
        used_marks.append({"id": spec["id"], "boats": boats})
        parts.append(one_pass(spec["id"], boats, expect))
        prev_boats = boats
    parts.append(one_pass("FIN", finish, fleet))
    missing = [{"id": p["id"], "missing": p["missing"]} for p in parts if not p["ok"]]
    sanity = sanity_places_and_times(fleet=fleet, st=st, mark_passes=used_marks, finish=finish)
    return {
        "fleet_n": len(fleet),
        "ok": not missing,
        "sha256": sha16([p["sha256"] for p in parts]),
        "passes": parts,
        "gaps": missing,
        "sanity": sanity,
        "note": (
            "Each pass sha256 is boat+ts from tracker GPS (marks) or Firestore (finish). "
            "Missing boats are GPS holes or a rounding we did not receive — not filled in. "
            "sanity checks place ± and that mark times add up."
        ),
    }
