#!/usr/bin/env python3
"""Start-line catchup only. Writes history + packed start times. Does not serve live GPS."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lipton_dev_live import HISTORY_PATHS, live_snapshot  # noqa: E402

OUT = Path("/var/www/sailingsa/js/lipton-dev-live-history.json")
STARTS_OUT = (
    Path("/var/www/sailingsa/js/lipton-dev-live-starts.json"),
    Path("/var/www/sailingsa/frontend/js/lipton-dev-live-starts.json"),
)
R = 6371000.0


def _norm(s: str) -> str:
    return str(s or "").upper().replace(" ", "")


def _at_ts(trail: list[dict], ts: int) -> dict | None:
    if not trail:
        return None
    if ts <= int(trail[0]["ts_ms"]):
        return trail[0]
    if ts >= int(trail[-1]["ts_ms"]):
        return trail[-1]
    lo, hi = 0, len(trail) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if int(trail[mid]["ts_ms"]) <= ts:
            lo = mid
        else:
            hi = mid
    return trail[lo]


def _pack_starts(data: dict) -> dict:
    """Same OCS rule as packed replay: 1st enter = dip, 2nd enter = legal ST. First 180s."""
    gun = data.get("gun_ts_ms")
    if not gun:
        return {}
    gun = int(gun)
    ocs = {_norm(x) for x in (data.get("ocs") or [])}
    pin = data.get("pin") or {}
    rc = data.get("committee") or {}
    ptrail = pin.get("trail") or ([pin] if pin.get("lat") is not None else [])
    rtrail = rc.get("trail") or ([rc] if rc.get("lat") is not None else [])
    pg, rg = _at_ts(ptrail, gun), _at_ts(rtrail, gun)
    if not pg or not rg:
        return {}
    lat0 = (pg["lat"] + rg["lat"]) / 2
    lon0 = (pg["lon"] + rg["lon"]) / 2
    cos = math.cos(math.radians(lat0))

    def toxy(lat, lon):
        return (
            math.radians(lon - lon0) * cos * R,
            math.radians(lat - lat0) * R,
        )

    ax, ay = toxy(pg["lat"], pg["lon"])
    bx, by = toxy(rg["lat"], rg["lon"])
    lx, ly = bx - ax, by - ay
    length = math.hypot(lx, ly) or 1
    ux, uy = lx / length, ly / length
    nx, ny = -uy, ux
    ds = []
    boats = data.get("boats") or {}
    for b in boats.values():
        trail = (b or {}).get("trail") or []
        p = _at_ts(trail, gun)
        if not p:
            continue
        qx, qy = toxy(p["lat"], p["lon"])
        ds.append((qx - ax) * nx + (qy - ay) * ny)
    ds.sort()
    flip = bool(ds) and ds[len(ds) // 2] < 0

    def signed(lat, lon):
        qx, qy = toxy(lat, lon)
        d = (qx - ax) * nx + (qy - ay) * ny
        along = (qx - ax) * ux + (qy - ay) * uy
        if flip:
            d = -d
        return d, along

    def enters(pts):
        hits = []
        prev = None
        for p in pts:
            ts = int(p.get("ts_ms") or 0)
            if ts < gun - 5000:
                continue
            if ts > gun + 180_000:
                break
            d, along = signed(p["lat"], p["lon"])
            if prev is not None:
                d0, t0, a0 = prev
                if d0 > 0 and d <= 0:
                    frac = d0 / (d0 - d) if d0 != d else 1.0
                    t = int(t0 + (ts - t0) * frac)
                    along_x = a0 + (along - a0) * frac
                    if -80 <= along_x <= length + 80:
                        hits.append(t)
            prev = (d, ts, along)
        return hits

    out = {}
    for sail, b in boats.items():
        pts = (b or {}).get("trail") or []
        hits = enters(pts)
        is_ocs = _norm(sail) in ocs
        if is_ocs:
            st = hits[1] if len(hits) >= 2 else None
            dip = hits[0] if hits else None
        else:
            st = next((t for t in hits if t >= gun - 500), None)
            dip = None
        if st is None:
            continue
        row = {"st_ms": int(st), "ocs": is_ocs}
        if dip is not None:
            row["ocs_ts_ms"] = int(dip)
        out[sail] = row
    return out


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    data = live_snapshot(history=True)
    text = json.dumps(data, separators=(",", ":"), default=str)
    for p in (OUT,) + HISTORY_PATHS:
        try:
            _atomic_write(p, text)
        except OSError:
            continue
    starts = _pack_starts(data)
    start_doc = {
        "gun_ts_ms": data.get("gun_ts_ms"),
        "ocs": data.get("ocs") or [],
        "starts": starts,
        "source": "packed replay OCS rule on catchup GPS. Empty = not received.",
    }
    start_text = json.dumps(start_doc, separators=(",", ":"), default=str)
    for p in STARTS_OUT:
        try:
            _atomic_write(p, start_text)
        except OSError:
            continue
    boats = data.get("boats") or {}
    gun = data.get("gun_ts_ms")
    from_gun = 0
    span = 0
    if gun:
        for b in boats.values():
            t = (b or {}).get("trail") or []
            if t and int(t[0].get("ts_ms") or 0) <= int(gun) + 15_000:
                from_gun += 1
            if len(t) >= 2:
                span = max(span, int(t[-1].get("ts_ms") or 0) - int(t[0].get("ts_ms") or 0))
    ocs_n = sum(1 for v in starts.values() if v.get("ocs") and v.get("st_ms"))
    print(
        f"catchup ok boats={len(boats)} from_gun={from_gun} "
        f"span_s={span/1000:.0f} starts={len(starts)} ocs_st={ocs_n} "
        f"gun={gun} ocs={data.get('ocs')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
