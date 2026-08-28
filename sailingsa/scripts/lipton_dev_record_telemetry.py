#!/usr/bin/env python3
"""Record every Lipton teleapi point onto our map/course.

Live: poll the tracker, keep every unique ping, then detect roundings a few
seconds later so closest-approach + leave exist. Do not invent GPS. Not Nett.

  python3 sailingsa/scripts/lipton_dev_record_telemetry.py --race 4
  python3 sailingsa/scripts/lipton_dev_record_telemetry.py --race 4 --live
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_mark_rounding import fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LIVE_DELAY_MS = 5_000
POLL_S = 2.0


def _ms_iso(value) -> int:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    sast = ZoneInfo("Africa/Johannesburg")
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=sast)
    return int(dt.timestamp() * 1000)


def race_window(race: int) -> tuple[int, int]:
    doc = fetch_regatta_doc()
    r = next(x for x in _j22_division(doc)["races"] if int(x.get("raceNumber") or 0) == race)
    s0 = r["starts"][0]
    gun = _ms_iso(s0["startTime"])
    finishes = r.get("finishes") or []
    if finishes:
        end = max(_ms_iso(f["finishingTime"]) for f in finishes)
    elif r.get("endTime"):
        end = _ms_iso(r["endTime"])
    else:
        end = int(time.time() * 1000)
    return gun - 90_000, end + 20_000


def row_key(rec: dict) -> tuple:
    return (
        rec.get("sn"),
        rec.get("sail_number"),
        rec.get("ts"),
        rec.get("latitude"),
        rec.get("longitude"),
    )


def append_unique(path: Path, rows: list[dict], seen: set) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with path.open("a", encoding="utf-8") as fh:
        for rec in rows:
            k = row_key(rec)
            if k in seen:
                continue
            seen.add(k)
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
            added += 1
    return added


def load_seen(path: Path) -> set:
    seen = set()
    if not path.exists():
        return seen
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            seen.add(row_key(json.loads(line)))
    return seen


def main() -> int:
    ap = argparse.ArgumentParser(description="Record every Lipton teleapi GPS point")
    ap.add_argument("--race", type=int, default=4)
    ap.add_argument("--live", action="store_true", help="Poll until interrupted; roundings wait --delay-ms")
    ap.add_argument("--delay-ms", type=int, default=LIVE_DELAY_MS, help="Hold points this long before packing")
    ap.add_argument("--rebuild", action="store_true", help="After fetch, run pack_race4 (historical)")
    args = ap.parse_args()
    out = DATA_DIR / f"lipton_r{args.race}_telemetry.jsonl"
    seen = load_seen(out)
    print(json.dumps({"archive": str(out), "already": len(seen), "delay_ms": args.delay_ms}), flush=True)

    if args.live:
        now = int(time.time() * 1000)
        t = now - 30_000
        try:
            while True:
                now = int(time.time() * 1000)
                rows = fetch_rows(t, now)
                added = append_unique(out, rows, seen)
                t = max(t, now - 8_000)
                print(
                    json.dumps(
                        {
                            "poll": True,
                            "added": added,
                            "total": len(seen),
                            "plot_before_ts": now - args.delay_ms,
                            "note": "our map/course; roundings wait delay so CPA+leave exist",
                        }
                    ),
                    flush=True,
                )
                if args.rebuild and added:
                    from lipton_dev_pack_race4 import main as pack_main

                    pack_main()
                time.sleep(POLL_S)
        except KeyboardInterrupt:
            print(json.dumps({"stopped": True, "total": len(seen)}), flush=True)
            return 0

    after, before = race_window(args.race)
    print("fetch", after, before, flush=True)
    rows = fetch_rows(after, before)
    added = append_unique(out, rows, seen)
    print(json.dumps({"ok": True, "added": added, "total": len(seen), "rows": len(rows)}), flush=True)
    if args.rebuild:
        from lipton_dev_pack_race4 import main as pack_main

        return pack_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
