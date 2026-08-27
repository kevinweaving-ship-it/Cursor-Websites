#!/usr/bin/env python3
"""Classify a Lipton race against the three compulsory courses.

Card: Quadrangle, Triangle, Windward/Leeward.

- Quadrangle: two weather marks upwind with a real reach between them,
  two leewards downwind, start and finish are separate gates.
- Triangle: one weather, a wing off to the side, one leeward.
- Windward/Leeward: weather + close offset, leeward gate, combined start/finish.
"""
from __future__ import annotations

import math

R = 6371000.0


def haversine_m(a, b) -> float | None:
    if not a or not b:
        return None
    lat1, lon1 = a
    lat2, lon2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def line_mid(line: dict | None):
    if not line or not line.get("left") or not line.get("right"):
        return None
    return (
        (line["left"]["lat"] + line["right"]["lat"]) / 2,
        (line["left"]["lon"] + line["right"]["lon"]) / 2,
    )


def series_mid(series: dict | None):
    if not series:
        return None
    pts = [
        (series["lat"][i], series["lon"][i])
        for i in range(len(series.get("lat") or []))
        if series["lat"][i] is not None
    ]
    if not pts:
        return None
    lo = int(len(pts) * 0.2)
    hi = max(lo + 1, int(len(pts) * 0.8))
    sl = pts[lo:hi] or pts
    return (sum(p[0] for p in sl) / len(sl), sum(p[1] for p in sl) / len(sl))


def classify_course(*, marks: dict, start_line: dict | None, finish_line: dict | None, lap1_mark_ids: list[int]) -> dict:
    """Return {id, label, note} from mark GPS vs the compulsory course card."""
    start = line_mid(start_line)
    finish = line_mid(finish_line)
    pts = {str(k): series_mid(v) if isinstance(v, dict) and "lat" in v else v for k, v in (marks or {}).items()}
    m1, m2, m3, m4 = pts.get("1"), pts.get("2"), pts.get("3"), pts.get("4")
    d12 = haversine_m(m1, m2)
    d34 = haversine_m(m3, m4)
    d1s = haversine_m(m1, start)
    d2s = haversine_m(m2, start)
    sf = haversine_m(start, finish)
    n_lap1 = len([m for m in lap1_mark_ids if m])

    # Combined start/finish + close weather/offset = windward/leeward.
    if sf is not None and sf < 50 and d12 is not None and d12 < 250:
        return {
            "id": "wl",
            "label": "Windward / Leeward",
            "note": "Weather + offset upwind, combined start/finish gate.",
        }

    # Two far weathers with a reaching leg = quadrangle.
    if (
        d12 is not None
        and d12 > 400
        and d1s is not None
        and d2s is not None
        and d1s > 800
        and d2s > 800
    ):
        return {
            "id": "quadrangle",
            "label": "Quadrangle",
            "note": "Two weather marks upwind and two leewards. Separate start and finish.",
        }

    # One distant weather and a nearer wing = triangle.
    if d1s is not None and d1s > 800 and d2s is not None and d2s < 800:
        return {
            "id": "triangle",
            "label": "Triangle",
            "note": "Weather, wing, leeward. Device 4 is the pin, not a fourth rounding.",
        }

    if n_lap1 >= 4:
        return {
            "id": "quadrangle",
            "label": "Quadrangle",
            "note": "Four mark roundings on lap 1.",
        }
    if n_lap1 == 3:
        return {
            "id": "triangle",
            "label": "Triangle",
            "note": "Three mark roundings on lap 1.",
        }
    return {
        "id": "unknown",
        "label": "Course",
        "note": "Not enough mark GPS to match Quadrangle / Triangle / Windward-Leeward.",
    }


def course_from_pack(trail: dict, replay: dict) -> dict:
    lap1 = [
        int(p.get("mark") or 0)
        for p in (replay.get("passes") or [])
        if p.get("id") not in ("ST", "FIN") and int(p.get("lap") or 1) == 1
    ]
    return classify_course(
        marks=trail.get("marks") or {},
        start_line=trail.get("start_line"),
        finish_line=trail.get("finish_line"),
        lap1_mark_ids=lap1,
    )
