#!/usr/bin/env python3
"""Make hourly kWh from mains restore to now equal the meter register delta.

Ground truth: dp102 at restore (0.0 on 01 Sep 18:57 SAST) and dp102 now.
Prefix hours before the first jsonl dp102 keep their measured shape, scaled if
needed. From the first dp102 sample onward, hours are partitioned from the
register so they cannot drift.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, "/var/www/sailingsa/api")
from energy_backfill import hour_key, hours_from_register_points  # noqa: E402

SAST = timezone(timedelta(hours=2))
DEV = "bf90676b1341ecb34dse39"
BINS = Path("/var/www/sailingsa/data/arial_energy_bins.json")
REFS = Path("/var/www/sailingsa/data/arial_meter_refs.json")
JSONL = Path("/opt/tuya-sharing/state/raw_dps.jsonl")
CHECK = Path("/var/www/sailingsa/data/arial_energy_checksum.json")
EST = Path("/var/www/sailingsa/data/arial_energy_bins_backfill_register_checksum.json")
PROBE = "http://127.0.0.1:8003/api/arial/tuya/probe?device_id=" + DEV
DP102 = 102


def load_json(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return data if isinstance(data, type(default)) else default


def dp102_points() -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    last_t = last_k = None
    with JSONL.open() as f:
        for line in f:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("dpId") != DP102:
                continue
            val = o.get("value")
            if not isinstance(val, (int, float)):
                continue
            wall = float(o.get("wall") or 0)
            kwh = float(val) / 1000.0 if float(val) > 1000 else float(val)
            if last_t is not None and wall - last_t < 1 and abs(kwh - last_k) < 1e-6:
                continue
            out.append((wall, kwh))
            last_t, last_k = wall, kwh
    return out


def probe_now() -> tuple[float, float]:
    data = json.loads(urllib.request.urlopen(PROBE, timeout=10).read())
    m = {r["code"]: r.get("value") for r in (data.get("status") or []) if isinstance(r, dict)}
    kwh = m.get("meter_register_kwh")
    if not isinstance(kwh, (int, float)):
        raise SystemExit("probe has no meter_register_kwh")
    ts = float(data.get("readingTs") or time.time())
    return ts, float(kwh)


def main() -> None:
    refs = load_json(REFS, {})
    restore_ts = float(refs.get("restoreAt") or 0)
    restore_kwh = float(refs.get("meterKwhAtRestore") or 0)
    if not restore_ts:
        raise SystemExit("missing restoreAt")
    store = load_json(BINS, {})
    existing = dict((store.get("bins") or {}).get(DEV) or {})
    now_ts, now_kwh = probe_now()
    expected = round(now_kwh - restore_kwh, 6)
    samples = dp102_points()
    if not samples:
        raise SystemExit("no dp102 samples")

    first_ts, first_kwh = samples[0]
    first_hour = hour_key(first_ts)
    prefix = {k: float(v) for k, v in existing.items() if k < first_hour and isinstance(v, (int, float))}
    prefix_sum = round(sum(prefix.values()), 6)
    need_prefix = round(first_kwh - restore_kwh, 6)
    if prefix_sum > 0 and abs(prefix_sum - need_prefix) > 0.001:
        if prefix_sum > need_prefix > 0:
            scale = need_prefix / prefix_sum
            prefix = {k: round(v * scale, 6) for k, v in prefix.items()}
            prefix_sum = round(sum(prefix.values()), 6)
        elif prefix_sum < need_prefix:
            # leftover belongs in the first jsonl hour, before the first sample
            pass
    pre_first = round(max(0.0, need_prefix - prefix_sum), 6)

    points = [(first_ts, first_kwh)] + samples[1:]
    if now_ts > points[-1][0] and now_kwh >= points[-1][1]:
        points.append((now_ts, now_kwh))
    reg_hours = hours_from_register_points(points, require_plausible=False)
    if first_hour in reg_hours or pre_first:
        reg_hours[first_hour] = round(reg_hours.get(first_hour, 0.0) + pre_first, 6)

    # Hours from first jsonl sample onward come from the register; earlier hours keep shape.
    new_hours = dict(prefix)
    new_hours.update(reg_hours)

    # Identity: current hour absorbs any leftover millikWh from rounding.
    restore_key = hour_key(restore_ts)
    now_key = hour_key(now_ts)
    span = {k: v for k, v in new_hours.items() if restore_key <= k <= now_key}
    got = round(sum(span.values()), 6)
    residual = round(expected - got, 6)
    if abs(residual) >= 0.0005:
        span[now_key] = round(span.get(now_key, 0.0) + residual, 6)
        new_hours[now_key] = span[now_key]
        got = round(sum(v for k, v in new_hours.items() if restore_key <= k <= now_key), 6)
        residual = round(expected - got, 6)

    bins = store.setdefault("bins", {})
    if not isinstance(bins, dict):
        bins = {}
        store["bins"] = bins
    bins[DEV] = new_hours
    tmp = BINS.with_suffix(".tmp")
    tmp.write_text(json.dumps(store), encoding="utf-8")
    tmp.replace(BINS)

    sampled_hours = {hour_key(t) for t, _ in samples}
    est_hours = sorted(
        k for k in new_hours if k >= first_hour and k <= now_key and k not in sampled_hours
    )
    payload = {
        "appliedAt": time.time(),
        "method": "register checksum: prefix scaled to first dp102; hours from first dp102 partitioned from register",
        "restoreAt": restore_ts,
        "restoreKwh": restore_kwh,
        "registerNow": now_kwh,
        "expectedKwh": expected,
        "hoursSumKwh": got,
        "residualKwh": residual,
        "ok": abs(residual) < 0.05,
        "firstDp102At": first_ts,
        "firstDp102Kwh": first_kwh,
        "prefixSumKwh": prefix_sum,
        "hours": est_hours,
    }
    CHECK.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    EST.write_text(json.dumps({"appliedAt": payload["appliedAt"], "hours": est_hours, "method": payload["method"]}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("restoreKwh", "registerNow", "expectedKwh", "hoursSumKwh", "residualKwh", "ok", "prefixSumKwh", "firstDp102Kwh")}, indent=2))
    print("est hours", len(est_hours))


if __name__ == "__main__":
    main()
