"""Register-delta EST fill for Hansekop hourly bins.

Only spreads a real meter-register (dp102) delta across the silent window.
Does not invent hours or invent kWh.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SAST = timezone(timedelta(hours=2))
MAX_KW = 8.0  # reject deltas that cannot be real house load


def hour_key(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone(SAST).strftime("%Y%m%d%H")


def plausible_delta(delta_kwh: float, seconds: float, max_kw: float = MAX_KW) -> bool:
    if delta_kwh <= 0 or seconds <= 0:
        return False
    return delta_kwh <= max_kw * (seconds / 3600.0)


def spread_register_delta(
    delta_kwh: float,
    start_ts: float,
    end_ts: float,
) -> dict[str, float]:
    """Split a register delta across hour keys by overlap seconds in [start, end)."""
    start_ts = float(start_ts)
    end_ts = float(end_ts)
    if end_ts <= start_ts or not plausible_delta(delta_kwh, end_ts - start_ts):
        return {}
    span = end_ts - start_ts
    out: dict[str, float] = {}
    cur = start_ts
    while cur < end_ts - 1e-9:
        local = datetime.fromtimestamp(cur, tz=timezone.utc).astimezone(SAST)
        hour_end = (local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).timestamp()
        seg_end = min(end_ts, hour_end)
        share = delta_kwh * (seg_end - cur) / span
        key = hour_key(cur)
        out[key] = round(out.get(key, 0.0) + share, 6)
        cur = seg_end
    return out


def neighbor_avg(measured: dict[str, float | None], before_key: str) -> float | None:
    """Mean of complete measured hours on the same day before the silent hour (not invented)."""
    day = before_key[:8]
    vals = []
    for key in sorted(k for k in measured if k.startswith(day) and k < before_key):
        v = measured.get(key)
        if isinstance(v, (int, float)) and v >= 0.9:
            vals.append(float(v))
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)


def apply_adds(
    measured: dict[str, float | None],
    adds: dict[str, float],
    avg_kwh: float | None = None,
) -> tuple[dict[str, float], list[str]]:
    """Merge adds into bins. Empty full hours use neighbor avg; leftover register delta goes on the partial restore hour."""
    bins: dict[str, float] = {}
    est: list[str] = []
    keys = sorted(set(measured) | set(adds))
    leftover = 0.0
    for key in keys:
        have = measured.get(key)
        add = float(adds.get(key) or 0.0)
        if have is None:
            if add <= 0:
                continue
            if avg_kwh and add > avg_kwh:
                leftover += add - avg_kwh
                add = avg_kwh
            bins[key] = round(add, 6)
            est.append(key)
            continue
        bins[key] = round(float(have) + add, 6)
    if leftover and keys:
        last = keys[-1]
        if last in bins:
            bins[last] = round(bins[last] + leftover, 6)
        elif adds.get(last):
            bins[last] = round(float(adds[last]) + leftover, 6)
    return bins, est


def backfill_payload(
    *,
    delta_kwh: float,
    start_ts: float,
    end_ts: float,
    measured: dict[str, float | None],
    register_from_wh: float,
    register_to_wh: float,
    applied_at: float,
) -> dict[str, Any] | None:
    adds = spread_register_delta(delta_kwh, start_ts, end_ts)
    if not adds:
        return None
    empty = sorted(k for k, v in measured.items() if v is None and k in adds) or sorted(adds)
    avg = neighbor_avg(measured, empty[0]) if empty else None
    bins, est = apply_adds(measured, adds, avg)
    if not est and not adds:
        return None
    return {
        "appliedAt": applied_at,
        "method": "register-delta dp102; empty hours capped at neighbor avg; leftover on partial restore hour",
        "neighborAvgKwh": avg,
        "gapKwh": round(float(delta_kwh), 6),
        "registerFromWh": register_from_wh,
        "registerToWh": register_to_wh,
        "silentFrom": start_ts,
        "silentTo": end_ts,
        "hours": est,
        "adds": {k: round(v, 6) for k, v in adds.items()},
        "bins": bins,
    }
