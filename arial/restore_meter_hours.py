"""Rebuild Hansekop hourly kWh bins from the meter SQLite register.

Uses last lifetime-kWh in each SA hour minus the previous hour.
Does not invent hours. Deltas above 8 kWh/h are dropped as implausible.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SAST = timezone(timedelta(hours=2))
MAX_KWH_PER_HOUR = 8.0
METER = "bf90676b1341ecb34dse39"


def hour_key(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone(SAST).strftime("%Y%m%d%H")


def bins_from_register(rows: Iterable[tuple[float, float]]) -> dict[str, float]:
    last: dict[str, float] = {}
    for ts, kwh in rows:
        if kwh is None:
            continue
        try:
            last[hour_key(ts)] = float(kwh)
        except (TypeError, ValueError):
            continue
    keys = sorted(last)
    out: dict[str, float] = {}
    prev: float | None = None
    for key in keys:
        cur = last[key]
        if prev is not None:
            delta = cur - prev
            if 0 < delta <= MAX_KWH_PER_HOUR:
                out[key] = round(delta, 3)
        prev = cur
    return out


def bins_from_sqlite(path: str | Path, device: str = METER) -> dict[str, float]:
    con = sqlite3.connect(str(path))
    rows = con.execute(
        "select ts, kwh from readings where device = ? order by ts",
        (device,),
    ).fetchall()
    con.close()
    return bins_from_register(rows)


def merge_hours(*sources: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for src in sources:
        for k, v in src.items():
            if not isinstance(v, (int, float)):
                continue
            out[str(k)] = max(float(v), float(out.get(str(k)) or 0.0))
    return {k: round(v, 3) for k, v in sorted(out.items())}


def hours_from_store(data: dict) -> dict[str, float]:
    bins = data.get("bins") if isinstance(data, dict) else None
    if not isinstance(bins, dict):
        return {}
    raw = bins.get(METER) or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}


def rebuild_store(store: dict, sqlite_path: str | Path, extra_hours: dict[str, float] | None = None) -> dict:
    from_sql = bins_from_sqlite(sqlite_path)
    current = hours_from_store(store)
    # SQLite fills missing history. Live power-integrated hours win when both exist
    # (register last-of-hour can jump by 0.1 kWh steps and overshoot).
    merged = merge_hours(extra_hours or {}, from_sql)
    merged.update(current)
    out = dict(store) if isinstance(store, dict) else {}
    bins = dict(out.get("bins") or {})
    bins[METER] = merged
    out["bins"] = bins
    return out


def main() -> None:
    data_dir = Path(os.environ.get("ARIAL_DATA", "/var/www/sailingsa/data"))
    store_path = data_dir / "arial_energy_bins.json"
    sqlite_path = data_dir / "arial_meter_history.sqlite"
    store = json.loads(store_path.read_text()) if store_path.is_file() else {"bins": {}, "recent": {}, "power": {}}
    extra: dict[str, float] = {}
    for bak in sorted(data_dir.glob("arial_energy_bins.json.bak*")):
        try:
            extra = merge_hours(extra, hours_from_store(json.loads(bak.read_text())))
        except (OSError, ValueError):
            continue
    out = rebuild_store(store, sqlite_path, extra)
    tmp = store_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, separators=(",", ":")))
    os.replace(tmp, store_path)
    hours = out["bins"][METER]
    days = sorted({k[:8] for k in hours})
    print("hours", len(hours), "days", days[0] if days else None, "->", days[-1] if days else None)


if __name__ == "__main__":
    main()
