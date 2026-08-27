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
    last_ts = {sail: gun + 60_000 for sail in boat_by}
    mark_passes = []
    summary = []
    for spec in COURSE_PASSES:
        ranked = []
        for sail in boat_by:
            fin = finish_ts.get(sail, last_finish)
            cutoff = fin - 80_000 if spec["mark"] == "4" else fin
            nxt = next(
                (c for c in cands[sail].get(spec["mark"], []) if last_ts[sail] + 25_000 < c["ts"] < cutoff),
                None,
            )
            if not nxt:
                continue
            last_ts[sail] = nxt["ts"]
            ranked.append({"boat": sail, "ts_ms": int(nxt["ts"])})
        ranked.sort(key=lambda r: r["ts_ms"])
        if not ranked:
            continue
        mark_passes.append(
            {
                "id": spec["id"],
                "label": f"M{spec['mark']}",
                "lap": spec["lap"],
                "mark": int(spec["mark"]),
                "boats": ranked,
            }
        )
        summary.append({"id": spec["id"], "n": len(ranked), "first": ranked[0]["boat"]})

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
        "play_start_ts_ms": gun,
        "play_start_sast": gun_sast,
        "first_finish_ts_ms": first_finish,
        "first_finish_sast": first_sast,
        "end_ts_ms": last_finish,
        "end_sast": end_sast,
        "play_end_ts_ms": last_finish,
        "default_rate": 1,
        "ocs": ocs,
        "exonerated": exonerated,
        "ocs_ts": {row["boat"]: row["ocs_ts_ms"] for row in st if "ocs_ts_ms" in row},
        "mark1": mark_passes[0]["boats"] if mark_passes else [],
        "boats": boats,
        "finish": finish_rows,
        "jumps": {"gun": gun, "start": gun, "finish": first_finish},
        "mark_labels": [p["label"] for p in mark_passes],
        "passes": [{"id": "ST", "label": "ST", "lap": 0, "mark": 0, "boats": st}, *mark_passes],
        "checksum": build_checksum(
            fleet=sorted(boats),
            st=st,
            mark_passes=mark_passes,
            finish=finish_rows,
            course_passes=COURSE_PASSES,
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
