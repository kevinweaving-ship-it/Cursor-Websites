#!/usr/bin/env python3
"""Lipton 2026 only — archive mark-rounding trails from Vakaros teleapi.

Spectator Firestore has guns / finishes / course rules. The GPS trail that
shows *how* a boat rounded lives on teleapi.regatta.app. After the event that
feed is gone, so freeze the derived rounding + metre-accuracy here.

Do not invent positions. Do not write tracker places into Nett.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_vakaros import (
    LIPTON_EVENT_ID,
    LIPTON_FLEET,
    LIPTON_SLUG,
    SNAPSHOT_DDL,
    WATCH_ORIGIN,
    ensure_table,
)

SAST = ZoneInfo("Africa/Johannesburg")
TELEAPI = "https://teleapi.regatta.app/telemetry"
MARK_SN = {
    "1": 25633,  # windward
    "2": 25610,  # wing
    "3": 25619,  # leeward
}
J22_BOAT_LENGTH_M = 6.71
ZONE_BOAT_LENGTHS = 3
ZONE_RADIUS_M = round(J22_BOAT_LENGTH_M * ZONE_BOAT_LENGTHS, 1)
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
R5_MARK1_PATH = DOCS_DIR / "lipton_2026_r5_mark1_rounding.json"


def _http_json(url: str, timeout: int = 60):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SailingSA-LiptonRounding/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def ang_diff(a, b) -> float:
    return (b - a + 180) % 360 - 180


def fetch_rows(after_ms: int, before_ms: int) -> list[dict]:
    rows = []
    fields = None
    t = after_ms
    while t < before_ms:
        t2 = min(t + 120_000, before_ms)
        data = _http_json(
            f"{TELEAPI}/event/{LIPTON_EVENT_ID}?after={t}&before={t2}&limit=100000&division={LIPTON_FLEET}"
        )
        fields = data["Fields"]
        rows.extend(data.get("Rows") or [])
        t = t2
    idx = {k: i for i, k in enumerate(fields or [])}
    return [{k: row[i] for k, i in idx.items()} for row in rows]


def _pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(p * (len(s) - 1)))], 3)


def _median(xs):
    return round(statistics.median(xs), 3) if xs else None


def analyze_r5_mark1(rows: list[dict] | None = None) -> dict:
    """Race 5, day 2, windward mark 1. Window after the mark had settled."""
    start = datetime(2026, 8, 27, 16, 15, tzinfo=SAST)
    end = datetime(2026, 8, 27, 16, 32, tzinfo=SAST)
    after = int(start.timestamp() * 1000)
    before = int(end.timestamp() * 1000)
    if rows is None:
        rows = fetch_rows(after, before)

    mark_sn = MARK_SN["1"]
    mark2_sn = MARK_SN["2"]
    marks = sorted([r for r in rows if r.get("sn") == mark_sn], key=lambda x: x["ts"])
    marks2 = [r for r in rows if r.get("sn") == mark2_sn]
    boats = [r for r in rows if r.get("role") == "competitor"]
    if not marks or not boats:
        raise RuntimeError("teleapi returned no mark-1 or competitor pings")

    late_cut = int(datetime(2026, 8, 27, 16, 20, tzinfo=SAST).timestamp() * 1000)
    late = [m for m in marks if m["ts"] >= late_cut] or marks
    mlat = statistics.median(m["latitude"] for m in late)
    mlon = statistics.median(m["longitude"] for m in late)
    m2lat = statistics.median(m["latitude"] for m in marks2[-80:]) if marks2 else None
    m2lon = statistics.median(m["longitude"] for m in marks2[-80:]) if marks2 else None

    windows = defaultdict(list)
    for m in marks:
        windows[m["ts"] // 10_000].append(m)
    w_med, w_p95, jumps = [], [], []
    for pts in windows.values():
        if len(pts) < 3:
            continue
        clat = statistics.median(p["latitude"] for p in pts)
        clon = statistics.median(p["longitude"] for p in pts)
        d = [haversine_m(p["latitude"], p["longitude"], clat, clon) for p in pts]
        w_med.append(statistics.median(d))
        w_p95.append(sorted(d)[int(0.95 * (len(d) - 1))])
    for a, b in zip(marks, marks[1:]):
        dt = (b["ts"] - a["ts"]) / 1000
        if 0 < dt < 3:
            jumps.append(haversine_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"]))

    boat_by = defaultdict(list)
    for b in boats:
        boat_by[b["sail_number"]].append(b)
    resid = []
    for pts in boat_by.values():
        pts = sorted(pts, key=lambda x: x["ts"])
        for a, b in zip(pts, pts[1:]):
            dt = (b["ts"] - a["ts"]) / 1000
            if not (0.4 < dt < 2.5):
                continue
            moved = haversine_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
            resid.append(abs(moved - (a.get("sog") or 0) * dt))

    heading_in_bins = {}
    heading_out_bins = {}
    bin_defs = [
        (300, 400),
        (200, 300),
        (150, 200),
        (100, 150),
        (75, 100),
        (50, 75),
        (30, 50),
        (20, 30),
        (10, 20),
        (5, 10),
        (0, 5),
    ]

    roundings = []
    closest = {}
    mark_i = 0

    def nearest_mark(ts):
        nonlocal mark_i
        while mark_i + 1 < len(marks) and abs(marks[mark_i + 1]["ts"] - ts) < abs(marks[mark_i]["ts"] - ts):
            mark_i += 1
        while mark_i > 0 and abs(marks[mark_i - 1]["ts"] - ts) <= abs(marks[mark_i]["ts"] - ts):
            mark_i -= 1
        return marks[mark_i]

    for sn, pts in boat_by.items():
        best = None
        for p in sorted(pts, key=lambda x: x["ts"]):
            mk = nearest_mark(p["ts"])
            d = haversine_m(p["latitude"], p["longitude"], mk["latitude"], mk["longitude"])
            if best is None or d < best[0]:
                best = (d, p, mk)
        closest[sn] = best

    def bin_key(lo, hi):
        return f"{lo}-{hi}m"

    for lo, hi in bin_defs:
        inbound, outbound_m2 = [], []
        for sn, pts in boat_by.items():
            t0 = closest[sn][1]["ts"]
            for p in pts:
                dist = haversine_m(p["latitude"], p["longitude"], mlat, mlon)
                if not (lo <= dist < hi):
                    continue
                if p["ts"] < t0:
                    brg = bearing_deg(p["latitude"], p["longitude"], mlat, mlon)
                    inbound.append(abs(ang_diff(p["heading"], brg)))
                elif p["ts"] > t0 and m2lat is not None:
                    brg2 = bearing_deg(p["latitude"], p["longitude"], m2lat, m2lon)
                    outbound_m2.append(abs(ang_diff(p["heading"], brg2)))
        heading_in_bins[bin_key(lo, hi)] = {
            "n": len(inbound),
            "heading_vs_mark_median_deg": _median(inbound),
            "heading_vs_mark_p75_deg": _pct(inbound, 0.75),
        }
        heading_out_bins[bin_key(lo, hi)] = {
            "n": len(outbound_m2),
            "heading_vs_mark2_median_deg": _median(outbound_m2),
            "heading_vs_mark2_p75_deg": _pct(outbound_m2, 0.75),
        }

    def first_cross(seq, thresh, *, decreasing, mlat=mlat, mlon=mlon):
        for p in seq:
            dist = haversine_m(p["latitude"], p["longitude"], mlat, mlon)
            if decreasing and dist <= thresh:
                return round(dist, 1)
            if (not decreasing) and dist >= thresh:
                return round(dist, 1)
        return None

    for sn, pts in boat_by.items():
        pts = sorted(pts, key=lambda x: x["ts"])
        dist, p, mk = closest[sn]
        t0 = p["ts"]
        before_pts = [x for x in pts if t0 - 8000 <= x["ts"] <= t0 - 1500]
        after_pts = [x for x in pts if t0 + 4000 <= x["ts"] <= t0 + 12000]
        hdg_in = statistics.median([x["heading"] for x in before_pts]) if before_pts else p["heading"]
        hdg_out = statistics.median([x["heading"] for x in after_pts]) if after_pts else None
        dhdg = abs(ang_diff(hdg_in, hdg_out)) if hdg_out is not None else None
        inbound = [x for x in pts if x["ts"] < t0]
        outbound = [x for x in pts if x["ts"] > t0]
        jitter = []
        for x in pts:
            if abs(x["ts"] - t0) <= 1500:
                jitter.append(haversine_m(x["latitude"], x["longitude"], mlat, mlon))

        def band_median(seq, lo, hi, key, scale=1.0):
            xs = []
            for x in seq:
                d = haversine_m(x["latitude"], x["longitude"], mlat, mlon)
                if lo <= d < hi:
                    xs.append((x.get(key) or 0) * scale)
            return round(statistics.median(xs), 1) if xs else None

        sog_in_50 = band_median(inbound, 40, 80, "sog", 1.94384)
        sog_in_20 = band_median(inbound, 15, 30, "sog", 1.94384)
        sog_mark = round((p.get("sog") or 0) * 1.94384, 1)
        sog_out_20 = band_median(outbound, 15, 30, "sog", 1.94384)
        sog_out_50 = band_median(outbound, 40, 80, "sog", 1.94384)
        roll_in_50 = band_median(inbound, 40, 80, "roll")
        roll_at = p.get("roll")
        roll_out_50 = band_median(outbound, 40, 80, "roll")
        pitch_in_50 = band_median(inbound, 40, 80, "pitch")
        pitch_at = p.get("pitch")
        pitch_out_50 = band_median(outbound, 40, 80, "pitch")
        slowed = None
        if sog_in_50 is not None:
            slowed = sog_mark <= (sog_in_50 - 0.8)
        roundings.append(
            {
                "boat": sn,
                "closest_sast": datetime.fromtimestamp(t0 / 1000, SAST).strftime("%H:%M:%S"),
                "closest_ts_ms": t0,
                "closest_m": round(dist, 1),
                "in_3bl_zone": dist <= ZONE_RADIUS_M,
                "hdg_in_deg": round(hdg_in, 1),
                "hdg_out_deg": round(hdg_out, 1) if hdg_out is not None else None,
                "delta_hdg_deg": round(dhdg, 1) if dhdg is not None else None,
                "bear_away": bool(dhdg is not None and dhdg >= 90),
                "sog_50m_in_kn": sog_in_50,
                "sog_20m_in_kn": sog_in_20,
                "sog_at_mark_kn": sog_mark,
                "sog_20m_out_kn": sog_out_20,
                "sog_50m_out_kn": sog_out_50,
                "slowed_at_rounding": slowed,
                "roll_50m_in_deg": roll_in_50,
                "roll_at_mark_deg": roll_at,
                "roll_50m_out_deg": roll_out_50,
                "pitch_50m_in_deg": pitch_in_50,
                "pitch_at_mark_deg": pitch_at,
                "pitch_50m_out_deg": pitch_out_50,
                "inbound_first_le_75m": first_cross(inbound, 75, decreasing=True),
                "inbound_first_le_50m": first_cross(inbound, 50, decreasing=True),
                "inbound_first_le_20m": first_cross(inbound, 20, decreasing=True),
                "outbound_first_ge_20m": first_cross(outbound, 20, decreasing=False),
                "outbound_first_ge_50m": first_cross(outbound, 50, decreasing=False),
                "closest_1s_span_m": round(max(jitter) - min(jitter), 1) if len(jitter) >= 2 else 0.0,
                "replay": f"{WATCH_ORIGIN}/watch/{LIPTON_EVENT_ID}/{LIPTON_FLEET}?race-day=2&ts={t0}",
            }
        )
    roundings.sort(key=lambda r: r["closest_ts_ms"])
    for i, row in enumerate(roundings, start=1):
        row["order"] = i

    sog_in = [r["sog_50m_in_kn"] for r in roundings if r["sog_50m_in_kn"] is not None]
    sog_mk = [r["sog_at_mark_kn"] for r in roundings if r["sog_at_mark_kn"] is not None]
    sog_out = [r["sog_50m_out_kn"] for r in roundings if r["sog_50m_out_kn"] is not None]
    slowed_n = sum(1 for r in roundings if r["slowed_at_rounding"] is True)
    speed_n = sum(1 for r in roundings if r["slowed_at_rounding"] is not None)
    bear = [r for r in roundings if r.get("bear_away")]
    bear_dkn = []
    for r in bear:
        if r["sog_50m_in_kn"] is not None:
            bear_dkn.append(round(r["sog_at_mark_kn"] - r["sog_50m_in_kn"], 1))
    abs_roll_in = [abs(r["roll_50m_in_deg"]) for r in roundings if r.get("roll_50m_in_deg") is not None]
    abs_roll_at = [abs(r["roll_at_mark_deg"]) for r in roundings if r.get("roll_at_mark_deg") is not None]
    abs_roll_out = [abs(r["roll_50m_out_deg"]) for r in roundings if r.get("roll_50m_out_deg") is not None]
    pitch_in = [r["pitch_50m_in_deg"] for r in roundings if r.get("pitch_50m_in_deg") is not None]
    pitch_at = [r["pitch_at_mark_deg"] for r in roundings if r.get("pitch_at_mark_deg") is not None]
    pitch_out = [r["pitch_50m_out_deg"] for r in roundings if r.get("pitch_50m_out_deg") is not None]
    boat_p95 = _pct(resid, 0.95)
    mark_p95 = _median(w_p95)
    typical_m = 5
    conservative_m = 10
    payload = {
        "ok": True,
        "regatta_id": LIPTON_SLUG,
        "event_id": LIPTON_EVENT_ID,
        "fleet": LIPTON_FLEET,
        "source": "teleapi_mark_rounding",
        "teleapi": f"{TELEAPI}/event/{LIPTON_EVENT_ID}",
        "race_number": 5,
        "race_day": 2,
        "mark": {
            "name": "1",
            "role": "windward",
            "sn": mark_sn,
            "leave_to": "port",
            "zone_boat_lengths": ZONE_BOAT_LENGTHS,
            "zone_radius_m": ZONE_RADIUS_M,
            "settled_lat": mlat,
            "settled_lon": mlon,
        },
        "window_sast": {"from": start.isoformat(), "to": end.isoformat()},
        "use": "Show sailors what a tight port rounding looked like. Not a Nett source.",
        "speed_at_rounding": {
            "question": "Do boats slow when they change angle at the mark?",
            "answer": (
                "often_not"
                if speed_n and slowed_n < speed_n / 2
                else "usually_yes" if speed_n else "unknown"
            ),
            "median_sog_50m_in_kn": _median(sog_in),
            "median_sog_at_mark_kn": _median(sog_mk),
            "median_sog_50m_out_kn": _median(sog_out),
            "boats_that_slowed": slowed_n,
            "boats_with_speed": speed_n,
            "bear_away_boats": len(bear),
            "bear_away_median_delta_kn": _median(bear_dkn),
            "note": (
                "Slow = SOG at closest is at least 0.8 kn below SOG 40–80 m inbound. "
                "Checked: not generally true. Big bear-away (>90° HDG) often dips; boats already reaching do not. "
                "Do not use a speed dip as the rounding detector."
            ),
        },
        "heel_and_trim": {
            "heel_source": "roll_deg",
            "trim_source": "pitch_deg",
            "median_abs_roll_50m_in_deg": _median(abs_roll_in),
            "median_abs_roll_at_mark_deg": _median(abs_roll_at),
            "median_abs_roll_50m_out_deg": _median(abs_roll_out),
            "median_pitch_50m_in_deg": _median(pitch_in),
            "median_pitch_at_mark_deg": _median(pitch_at),
            "median_pitch_50m_out_deg": _median(pitch_out),
            "heel_useful": True,
            "trim_useful": False,
            "note": (
                "Heel (roll): boats flatten from upwind heel onto the reach (typical |roll| ~16° in → ~8° out). "
                "Useful as a supporting signal with heading, not as a rounding clock. "
                "Trim (pitch): only a few degrees, noisy integers. Not useful as a rounding signal."
            ),
        },
        "accuracy_m": {
            "metres_to_mark_always_computed": True,
            "accuracy_does_not_fade_with_range": True,
            "typical_m": typical_m,
            "conservative_m": conservative_m,
            "do_not_claim_below_m": 3,
            "lost_when_range_below_error_m": 10,
            "note": (
                "Metres to the mark (or start pin) is always computed from lat/lon. "
                "The error is about the same at 400 m as at 40 m — it does not fade with range. "
                "What is lost close-in is *useful* precision: inside ~10 m the GPS error is as big as the distance, "
                "so '2 m from the buoy' is not real. Gun DTL millimetres (dtlMm) exist only at the start gun."
            ),
            "mark_10s_scatter_median_m": _median(w_med),
            "mark_10s_scatter_p95_m": mark_p95,
            "mark_consecutive_jump_median_m": _median(jumps),
            "boat_step_residual_median_m": _median(resid),
            "boat_step_residual_p95_m": boat_p95,
            "approach": {
                "heading_to_mark_usable_from_m": 300,
                "heading_to_mark_still_clean_m": 50,
                "turn_starts_inside_m": 30,
                "heading_to_mark_unreliable_inside_m": 10,
                "note": (
                    "Distance itself is available at any range. "
                    "'Going to the mark' means heading tracks bearing and distance is falling. "
                    f"That is readable from ~300 m. Inside ~30 m they are already turning. "
                    f"Do not treat trail DTL as millimetre-accurate; gun DTL millimetres are Firestore dtlMm only."
                ),
            },
            "past_mark": {
                "rounded_clear_by_m": 20,
                "course_to_next_mark_best_m": [10, 75],
                "still_accurate_at_m": 200,
                "note": (
                    "GPS noise does not get worse after the mark. Same ~5 m typical / ~10 m conservative. "
                    "We can tell they have rounded once distance is increasing and heading has swung (~10–20 m past). "
                    "Course toward mark 2 is clearest 10–75 m past. After ~100 m some boats sail high/low; that is sailing, not GPS."
                ),
            },
            "zone": {
                "three_boat_lengths_m": ZONE_RADIUS_M,
                "usable": True,
                "note": "20 m zone is several times GPS noise, so in-zone vs out-of-zone is usable.",
            },
        },
        "heading_to_mark_inbound": heading_in_bins,
        "heading_to_mark2_outbound": heading_out_bins,
        "roundings": roundings,
        "counts": {
            "telemetry_rows": len(rows),
            "mark1_pings": len(marks),
            "competitor_pings": len(boats),
            "boats": len(roundings),
            "in_zone": sum(1 for r in roundings if r["in_3bl_zone"]),
        },
        "first_about_to_round": {
            "boat": roundings[0]["boat"] if roundings else None,
            "sast": roundings[0]["closest_sast"] if roundings else None,
            "closest_m": roundings[0]["closest_m"] if roundings else None,
            "replay": roundings[0]["replay"] if roundings else None,
        },
    }
    return payload


def write_file(payload: dict, path: Path = R5_MARK1_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    return path


def save_snapshot(payload: dict, db_url: str | None = None) -> dict:
    import psycopg2
    from psycopg2.extras import Json

    url = db_url or os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DB_URL or DATABASE_URL required to save a snapshot")
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    summary = {
        "kind": "mark_rounding",
        "race_number": payload.get("race_number"),
        "mark": (payload.get("mark") or {}).get("name"),
        "boats": (payload.get("counts") or {}).get("boats"),
        "first": payload.get("first_about_to_round"),
        "accuracy_m": payload.get("accuracy_m"),
        "last_finished_race": 5,
        "next_race_number": 6,
    }
    conn = psycopg2.connect(url)
    try:
        ensure_table(conn)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.vakaros_snapshots (
                        regatta_id, event_id, fleet, source,
                        tracker_modified_ts, tracker_create_time, tracker_update_time,
                        sequence_number, payload_sha256, payload, payload_raw,
                        summary, player_html, notes
                    ) VALUES (
                        %s, %s, %s, %s,
                        NULL, NULL, NULL,
                        NULL, %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING snapshot_id, fetched_at
                    """,
                    (
                        LIPTON_SLUG,
                        LIPTON_EVENT_ID,
                        LIPTON_FLEET,
                        "teleapi_mark_rounding",
                        hashlib.sha256(blob).hexdigest(),
                        Json(payload),
                        Json({"teleapi": payload.get("teleapi"), "window_sast": payload.get("window_sast")}),
                        Json(summary),
                        Json(None),
                        "Race 5 mark-1 rounding from GPS trail. For sailor rounding advice. Not a Nett source.",
                    ),
                )
                row = cur.fetchone()
    finally:
        conn.close()
    return {
        "ok": True,
        "snapshot_id": row[0],
        "fetched_at": row[1].isoformat() if row[1] else None,
        "source": "teleapi_mark_rounding",
        "boats": summary["boats"],
        "accuracy_typical_m": (payload.get("accuracy_m") or {}).get("typical_m"),
        "accuracy_conservative_m": (payload.get("accuracy_m") or {}).get("conservative_m"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Lipton mark-rounding archive (teleapi)")
    ap.add_argument("--fetch", action="store_true", help="Pull teleapi and write the frozen JSON")
    ap.add_argument("--save", action="store_true", help="Insert frozen JSON into vakaros_snapshots")
    ap.add_argument("--from-file", default=str(R5_MARK1_PATH), help="JSON to save")
    args = ap.parse_args()
    if args.fetch:
        payload = analyze_r5_mark1()
        path = write_file(payload)
        print(json.dumps({"ok": True, "wrote": str(path), "boats": payload["counts"]["boats"]}, indent=2))
        if args.save:
            print(json.dumps(save_snapshot(payload), indent=2))
        return 0
    if args.save:
        path = Path(args.from_file)
        payload = json.loads(path.read_text())
        print(json.dumps(save_snapshot(payload), indent=2))
        return 0
    if Path(args.from_file).exists():
        print(Path(args.from_file).read_text())
        return 0
    payload = analyze_r5_mark1()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
