#!/usr/bin/env python3
"""Pack Lipton -dev replay JSON for one J22 race.

Keeps the 17-boat identity map. Start order from GPS line crossings.
Marks from trail visits. Finishes from Firestore. Not Nett.

  python3 sailingsa/scripts/lipton_dev_pack_race4.py
  python3 sailingsa/scripts/lipton_dev_pack_race4.py --race 1
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_dev_checksum import build_checksum  # noqa: E402
from lipton_dev_course import classify_course  # noqa: E402
from lipton_dev_later_laps import rounding_candidates  # noqa: E402
from lipton_mark_rounding import COURSE_PASSES, MARK_SN, fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
SAST = ZoneInfo("Africa/Johannesburg")
R = 6371000.0


def replay_paths(race: int) -> tuple[Path, Path]:
    if race == 4:
        return ROOT / "sailingsa/frontend/js/lipton-dev-replay.json", ROOT / "js/lipton-dev-replay.json"
    suffix = f"-r{race}"
    return (
        ROOT / f"sailingsa/frontend/js/lipton-dev-replay{suffix}.json",
        ROOT / f"js/lipton-dev-replay{suffix}.json",
    )


def xy(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * math.cos(math.radians(lat0)) * R
    y = math.radians(lat - lat0) * R
    return x, y


def ms_iso(value) -> int:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SAST)
    return int(dt.timestamp() * 1000)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pack Lipton -dev replay JSON for one race")
    ap.add_argument("--race", type=int, default=4)
    args = ap.parse_args()
    race = int(args.race)
    out, out_copy = replay_paths(race)
    prev = json.loads(IDENTITY.read_text())
    boats = prev.get("boats") or {}
    if len(boats) != 17:
        raise SystemExit("identity map missing")

    doc = fetch_regatta_doc()
    r4 = next(r for r in _j22_division(doc)["races"] if int(r.get("raceNumber") or 0) == race)
    s0 = r4["starts"][0]
    ocs = [str(x) for x in (s0.get("ocsParticipants") or [])]
    exonerated = [str(x) for x in (s0.get("exoneratedParticipants") or [])]
    gun = ms_iso(s0["startTime"])
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

    finishes = sorted(r4.get("finishes") or [], key=lambda f: f.get("finishingTime") or "")
    finish_rows = []
    finish_ts = {}
    for f in finishes:
        sail = f.get("sailNumber")
        ts = ms_iso(f["finishingTime"])
        finish_ts[sail] = ts
        row = {"boat": sail, "ts_ms": ts}
        coords = ((f.get("positionAtFinish") or {}).get("coordinates")) or []
        if len(coords) >= 2:
            row["lon"] = round(float(coords[0]), 6)
            row["lat"] = round(float(coords[1]), 6)
        finish_rows.append(row)
    last_finish = max(finish_ts.values())
    first_finish = min(finish_ts.values())

    print("load trail", gun, last_finish, flush=True)
    try:
        from lipton_dev_archive_telemetry import load_race_rows  # noqa: E402

        rows = load_race_rows(race)
    except Exception:
        rows = []
    if rows:
        print(json.dumps({"archive_rows": len(rows), "race": race}), flush=True)
        rows = [r for r in rows if gun - 90_000 <= int(r.get("ts") or 0) <= last_finish + 20_000] or rows
    else:
        print("fetch trail", gun, last_finish, flush=True)
        rows = fetch_rows(gun - 90_000, last_finish + 20_000)
    marks_by_sn = defaultdict(list)
    boat_by = defaultdict(list)
    for rec in rows:
        if rec.get("sn") in MARK_SN.values():
            marks_by_sn[rec["sn"]].append(rec)
        if rec.get("role") == "competitor" and rec.get("race_number") in (race, None, 0, float(race)):
            boat_by[rec["sail_number"]].append(rec)
    for sn in marks_by_sn:
        marks_by_sn[sn] = sorted(marks_by_sn[sn], key=lambda x: x["ts"])
    for sail in list(boat_by):
        boat_by[sail] = sorted(boat_by[sail], key=lambda x: x["ts"])
        if any(p.get("race_number") == race for p in boat_by[sail]):
            boat_by[sail] = [p for p in boat_by[sail] if p.get("race_number") == race]

    def line_hits(pts, look_from):
        """Prestart (d>0) → course (d<=0) enters, and the reverse exits."""
        hits = []
        prev = None
        for p in pts:
            if p["ts"] < look_from:
                continue
            d, along = signed(p["latitude"], p["longitude"])
            if flip:
                d = -d
            if prev is not None:
                d0, t0, a0 = prev
                if -20 <= along <= ab_len + 20 or -20 <= a0 <= ab_len + 20:
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

    def start_times(sail, pts):
        is_ocs = sail in ocs
        look_from = gun - 90_000 if is_ocs else gun - 2_000
        hits = line_hits(pts, look_from)
        if not is_ocs:
            for h in hits:
                if h["dir"] == "enter" and h["ts"] >= gun - 500:
                    return h["ts"], None
            return None, None
        ocs_ts = next((h["ts"] for h in hits if h["dir"] == "enter"), gun)
        saw_exit = False
        legal = None
        for h in hits:
            if h["dir"] == "exit" and h["ts"] >= ocs_ts:
                saw_exit = True
            elif h["dir"] == "enter" and saw_exit:
                legal = h["ts"]
                break
        return legal or ocs_ts, ocs_ts

    st = []
    for sail, pts in boat_by.items():
        ts, ocs_dip = start_times(sail, pts)
        if ts is None:
            raise SystemExit(f"no start crossing for {sail}")
        row = {"boat": sail, "ts_ms": ts}
        if ocs_dip is not None:
            row["ocs_ts_ms"] = int(ocs_dip)
        st.append(row)
    st.sort(key=lambda r: r["ts_ms"])

    cands = {
        sail: {name: rounding_candidates(pts, marks_by_sn.get(sn) or []) for name, sn in MARK_SN.items()}
        for sail, pts in boat_by.items()
    }
    min_fleet = max(8, (len(boat_by) + 1) // 2)
    m2_hits = sum(
        1
        for sail in boat_by
        if any(gun + 120_000 < c["ts"] < first_finish - 120_000 for c in cands[sail].get("2") or [])
    )

    def first_cand(sail, mark, after, before):
        return next((c for c in cands[sail].get(str(mark), []) if after < c["ts"] < before), None)

    def commit_pass(spec_id, lap, mark, ranked):
        ranked.sort(key=lambda r: r["ts_ms"])
        mark_passes.append(
            {
                "id": spec_id,
                "label": f"M{mark}",
                "lap": lap,
                "mark": int(mark),
                "boats": ranked,
            }
        )
        summary.append({"id": spec_id, "n": len(ranked), "first": ranked[0]["boat"]})

    last_ts = {sail: gun + 60_000 for sail in boat_by}
    mark_passes = []
    summary = []
    use_wl = m2_hits < min_fleet
    if use_wl:
        for lap in (1, 2, 3):
            weather = []
            nxts = {}
            for sail in boat_by:
                fin = finish_ts.get(sail, last_finish) - 80_000
                c = first_cand(sail, "1", last_ts[sail] + 2_000, fin)
                if not c:
                    continue
                weather.append({"boat": sail, "ts_ms": int(c["ts"])})
                nxts[sail] = c["ts"]
            if len(weather) < min_fleet:
                break
            for sail, ts in nxts.items():
                last_ts[sail] = ts
            commit_pass(f"L{lap}-1", lap, 1, weather)
            leeward = []
            nxts = {}
            for sail in boat_by:
                fin = finish_ts.get(sail, last_finish) - 80_000
                opts = []
                for mark in ("3", "4"):
                    c = first_cand(sail, mark, last_ts[sail] + 2_000, fin)
                    if c:
                        opts.append(c)
                if not opts:
                    continue
                c = min(opts, key=lambda x: x["ts"])
                leeward.append({"boat": sail, "ts_ms": int(c["ts"])})
                nxts[sail] = c["ts"]
            if len(leeward) < min_fleet:
                break
            for sail, ts in nxts.items():
                last_ts[sail] = ts
            commit_pass(f"L{lap}-3", lap, 3, leeward)
    else:
        for spec in COURSE_PASSES:
            ranked = []
            nxts = {}
            for sail in boat_by:
                fin = finish_ts.get(sail, last_finish)
                cutoff = fin - 80_000 if spec["mark"] == "4" else fin
                nxt = first_cand(sail, spec["mark"], last_ts[sail] + 2_000, cutoff)
                if not nxt:
                    continue
                ranked.append({"boat": sail, "ts_ms": int(nxt["ts"])})
                nxts[sail] = nxt["ts"]
            ranked.sort(key=lambda r: r["ts_ms"])
            if len(ranked) < min_fleet:
                continue
            for sail, ts in nxts.items():
                last_ts[sail] = ts
            commit_pass(spec["id"], spec["lap"], int(spec["mark"]), ranked)

    def rec_mid(recs):
        if not recs:
            return None
        lo = len(recs) // 5
        hi = max(lo + 1, 4 * len(recs) // 5)
        sl = recs[lo:hi]
        return (
            sum(r["latitude"] for r in sl) / len(sl),
            sum(r["longitude"] for r in sl) / len(sl),
        )

    fin_line = None
    if finishes:
        f0 = finishes[0]
        ll = ((f0.get("lineLeftLocation") or {}).get("coordinates")) or []
        rr = ((f0.get("lineRightLocation") or {}).get("coordinates")) or []
        if len(ll) >= 2 and len(rr) >= 2:
            fin_line = {
                "left": {"lat": float(ll[1]), "lon": float(ll[0])},
                "right": {"lat": float(rr[1]), "lon": float(rr[0])},
            }
    course = classify_course(
        marks={name: rec_mid(marks_by_sn.get(sn) or []) for name, sn in MARK_SN.items()},
        start_line={
            "left": {"lat": pin_lat, "lon": pin_lon},
            "right": {"lat": rc_lat, "lon": rc_lon},
        },
        finish_line=fin_line,
        lap1_mark_ids=[p["mark"] for p in mark_passes if int(p.get("lap") or 1) == 1],
    )
    if use_wl:
        course = {
            "id": "wl",
            "label": "Windward / Leeward",
            "note": "Weather then leeward gate (first of M3/M4). Wing was not rounded by the fleet.",
        }

    gun_sast = datetime.fromtimestamp(gun / 1000, SAST).isoformat()
    first_sast = datetime.fromtimestamp(first_finish / 1000, SAST).isoformat()
    end_sast = datetime.fromtimestamp(last_finish / 1000, SAST).isoformat()
    pack = {
        "mode": "replay",
        "live": False,
        "note": (
            f"Race {race} tracker. Every teleapi point is used for roundings (heading + closest). "
            "ST = seconds after first legal starter; OCS boats labelled OCS. "
            "Empty cell = GPS not received. Not Nett."
        ),
        "regatta_id": prev["regatta_id"],
        "dev_slug": prev["dev_slug"],
        "event_id": prev["event_id"],
        "fleet": "J22",
        "watch_path": prev["watch_path"],
        "race_number": race,
        "race_day": 1 if race <= 3 else 2,
        "gun_ts_ms": gun,
        "gun_sast": gun_sast,
        "play_start_ts_ms": gun - 10_000,
        "play_start_sast": datetime.fromtimestamp((gun - 10_000) / 1000, SAST).isoformat(),
        "first_finish_ts_ms": first_finish,
        "first_finish_sast": first_sast,
        "end_ts_ms": last_finish,
        "end_sast": end_sast,
        "play_end_ts_ms": last_finish,
        "default_rate": 1,
        "ocs": ocs,
        "exonerated": exonerated,
        "course": course,
        "ocs_ts": {row["boat"]: row["ocs_ts_ms"] for row in st if "ocs_ts_ms" in row},
        "mark1": mark_passes[0]["boats"] if mark_passes else [],
        "boats": boats,
        "finish": finish_rows,
        "jumps": {"gun": gun, "start": gun, "finish": first_finish},
        "mark_labels": [p["label"] for p in mark_passes],
        "passes": [{"id": "ST", "label": "ST", "lap": 0, "mark": 0, "boats": st}, *mark_passes],
        # Always checksum only marks the fleet actually sailed. COURSE_PASSES lists
        # every template leg (incl. wings never rounded / W/L middles) which used to
        # surface as false "checksum gaps L1-2 …" when a mark was towed between laps.
        "checksum": build_checksum(
            fleet=sorted(boats),
            st=st,
            mark_passes=mark_passes,
            finish=finish_rows,
            course_passes=[{"id": p["id"], "lap": p["lap"], "mark": str(p["mark"])} for p in mark_passes],
        ),
        "sources": {
            "guns_finishes_ocs": f"Vakaros Firestore races[R{race}] starts/finishes/ocsParticipants",
            "start_order": "teleapi GPS start-line crossing. OCS boats use recross after returning to prestart, not the OCS dip.",
            "marks": "teleapi every GPS point; heading + closest. Empty = not received.",
            "identity": "public Lipton sheet bow/boat/club logos",
        },
    }
    text = json.dumps(pack, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text)
    out_copy.write_text(text)
    legal = next((b["boat"] for b in st if b["boat"] not in ocs), st[0]["boat"] if st else None)
    print(
        json.dumps(
            {
                "ok": True,
                "race": race,
                "out": str(out),
                "gun": gun_sast,
                "ocs": ocs,
                "exonerated": exonerated,
                "st_first": st[0]["boat"] if st else None,
                "st_first_legal": legal,
                "st_sbyc_rank": next((i + 1 for i, b in enumerate(st) if b["boat"] == "SBYC"), None),
                "st_n": len(st),
                "marks": summary,
                "finish_n": len(finish_rows),
                "finish_first": finish_rows[0]["boat"] if finish_rows else None,
                "course": course,
                "checksum_ok": pack["checksum"]["ok"],
                "checksum_gaps": pack["checksum"]["gaps"],
                "sanity_ok": pack["checksum"].get("sanity", {}).get("ok"),
                "sanity": pack["checksum"].get("sanity"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
