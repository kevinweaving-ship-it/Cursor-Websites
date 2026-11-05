#!/usr/bin/env python3
"""Fill Hansekop hourly holes from real dp102 register deltas (no invented kWh).

Silent windows (no jsonl DPs, no sqlite rows):
  14 Sep 16:00  and  15 Sep 01:00–06:00
Uses the same register-delta method as 9 Sep (energy_backfill.py).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/var/www/sailingsa/api")
from energy_backfill import backfill_payload  # noqa: E402

SAST = ZoneInfo("Africa/Johannesburg")
DEV = "bf90676b1341ecb34dse39"
BINS = Path("/var/www/sailingsa/data/arial_energy_bins.json")
DATA = Path("/var/www/sailingsa/data")

# Last dp102 before silence / first dp102 after restore, from raw_dps.jsonl.
GAPS = [
    {
        "out": "arial_energy_bins_backfill_20260914.json",
        "reg_from_wh": 325012.0,  # 2026-09-14 15:25:56 SAST
        "reg_to_wh": 327111.0,    # 2026-09-14 17:19:56 SAST
        "start": datetime(2026, 9, 14, 15, 25, 56, tzinfo=SAST),
        "end": datetime(2026, 9, 14, 17, 19, 56, tzinfo=SAST),
    },
    {
        "out": "arial_energy_bins_backfill_20260915.json",
        "reg_from_wh": 334500.0,  # 2026-09-14 23:59:55 SAST
        "reg_to_wh": 342216.0,    # 2026-09-15 07:09:55 SAST
        "start": datetime(2026, 9, 14, 23, 59, 55, tzinfo=SAST),
        "end": datetime(2026, 9, 15, 7, 9, 55, tzinfo=SAST),
    },
]


def load_store() -> dict:
    try:
        data = json.loads(BINS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data


def measured_for(store: dict, start: datetime, end: datetime) -> dict[str, float | None]:
    """Hours from midnight of the silent start through the restore hour (neighbor avg + leftover)."""
    mine = ((store.get("bins") or {}).get(DEV) or {}) if isinstance(store.get("bins"), dict) else {}
    out: dict[str, float | None] = {}
    cur = start.astimezone(SAST).replace(hour=0, minute=0, second=0, microsecond=0)
    last = end.astimezone(SAST).replace(minute=0, second=0, microsecond=0)
    while cur <= last:
        key = cur.strftime("%Y%m%d%H")
        v = mine.get(key)
        out[key] = float(v) if isinstance(v, (int, float)) else None
        cur += timedelta(hours=1)
    return out


def main() -> None:
    store = load_store()
    mine = store.setdefault("bins", {}).setdefault(DEV, {})
    wrote = []
    for gap in GAPS:
        delta = (gap["reg_to_wh"] - gap["reg_from_wh"]) / 1000.0
        measured = measured_for(store, gap["start"], gap["end"])
        payload = backfill_payload(
            delta_kwh=delta,
            start_ts=gap["start"].timestamp(),
            end_ts=gap["end"].timestamp(),
            measured=measured,
            register_from_wh=gap["reg_from_wh"],
            register_to_wh=gap["reg_to_wh"],
            applied_at=time.time(),
        )
        if not payload:
            raise SystemExit(f"no backfill for {gap['out']} (delta rejected)")
        out = DATA / gap["out"]
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        for k, v in (payload.get("bins") or {}).items():
            mine[k] = float(v)
        wrote.append({"file": str(out), "hours": payload.get("hours"), "adds": payload.get("adds"), "gapKwh": payload.get("gapKwh")})
    tmp = BINS.with_suffix(".tmp")
    tmp.write_text(json.dumps(store), encoding="utf-8")
    tmp.replace(BINS)
    print(json.dumps(wrote, indent=2))


if __name__ == "__main__":
    main()
