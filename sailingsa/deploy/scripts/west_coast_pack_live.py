#!/usr/bin/env python3
"""Refresh SailingSA West Coast Live GPS packs from Yellowbrick BIN (server-side only).

Writes /var/www/sailingsa/data/west-coast-{all,ab,c}-replay.json + trail.json.
YB URLs never appear in the public page; this job pulls positions for the map packer.
Live: /usr/local/bin/west_coast_pack_live.py + /etc/cron.d/sailingsa_west_coast_gps (every minute).
"""
from __future__ import annotations

import json
import os
import ssl
import struct
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

DATA = Path("/var/www/sailingsa/data")
RACE_KEYS = ("wcor26", "wcor26_c")  # A/B/Multi + Class C
YB_BASE = "https://cf.yb.tl"
UA = {"User-Agent": "SailingSA-WestCoast-Packer/1.0", "Accept": "*/*"}
CTX = ssl.create_default_context()
STEP_MS = 5000
LOG = Path("/var/log/west-coast-gps-pack.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n"
    try:
        with LOG.open("a") as f:
            f.write(line)
    except Exception:
        pass


def fetch_bytes(path: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(f"{YB_BASE}/{path}", headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def fetch_json(path: str) -> Any:
    raw = fetch_bytes(path)
    return json.loads(raw.decode("utf-8", "replace"))


def zxe(buf: bytes) -> list[dict]:
    """Decode YB AllPositions3 / LatestPositions3 (DataView big-endian)."""
    if not buf:
        return []
    flags = buf[0]
    has_alt = (flags & 1) == 1
    has_dtf = (flags & 2) == 2
    has_lap = (flags & 4) == 4
    has_pc = (flags & 8) == 8
    big_count = has_lap and has_pc and has_alt
    if big_count:
        has_alt = has_lap = has_pc = False
    base_at = int.from_bytes(buf[1:5], "big")
    p = 5
    out: list[dict] = []
    while p < len(buf):
        team_id = int.from_bytes(buf[p : p + 2], "big")
        p += 2
        if big_count:
            n = int.from_bytes(buf[p : p + 8], "big")
            p += 8
        else:
            n = int.from_bytes(buf[p : p + 2], "big")
            p += 2
        moments: list[dict] = []
        prev: dict = {}
        for _ in range(n):
            flag = buf[p]
            d: dict = {}
            if (flag & 128) == 128:
                b = int.from_bytes(buf[p : p + 2], "big")
                p += 2
                dlat = int.from_bytes(buf[p : p + 2], "big", signed=True)
                p += 2
                dlon = int.from_bytes(buf[p : p + 2], "big", signed=True)
                p += 2
                if has_alt:
                    d["alt"] = int.from_bytes(buf[p : p + 2], "big", signed=True)
                    p += 2
                if has_dtf:
                    x = int.from_bytes(buf[p : p + 2], "big", signed=True)
                    p += 2
                    d["dtf"] = (prev.get("dtf") or 0) + x
                    if has_lap:
                        d["lap"] = buf[p]
                        p += 1
                if has_pc:
                    d["pc"] = int.from_bytes(buf[p : p + 2], "big", signed=True) / 32000.0
                    p += 2
                b &= 32767
                d["lat"] = (prev.get("lat") or 0) + dlat
                d["lon"] = (prev.get("lon") or 0) + dlon
                d["at"] = (prev.get("at") or 0) - b
                d["pc"] = (prev.get("pc") or 0) + d.get("pc", 0)
            else:
                b = int.from_bytes(buf[p : p + 4], "big")
                p += 4
                lat = int.from_bytes(buf[p : p + 4], "big", signed=True)
                p += 4
                lon = int.from_bytes(buf[p : p + 4], "big", signed=True)
                p += 4
                if has_alt:
                    d["alt"] = int.from_bytes(buf[p : p + 2], "big", signed=True)
                    p += 2
                if has_dtf:
                    d["dtf"] = int.from_bytes(buf[p : p + 4], "big", signed=True)
                    p += 4
                    if has_lap:
                        d["lap"] = buf[p]
                        p += 1
                if has_pc:
                    d["pc"] = int.from_bytes(buf[p : p + 4], "big", signed=True) / 21e6
                    p += 4
                d["lat"] = lat
                d["lon"] = lon
                d["at"] = base_at + b
            moments.append(d)
            prev = d
        for m in moments:
            m["lat"] = m["lat"] / 1e5
            m["lon"] = m["lon"] / 1e5
        out.append({"id": team_id, "moments": moments})
    return out


def norm_sail(s: str) -> str:
    """Alphanumeric upper; strip leading zeros in the numeric tail (SA 064 -> SA64)."""
    raw = "".join(ch for ch in str(s or "").upper() if ch.isalnum())
    if not raw:
        return ""
    i = 0
    while i < len(raw) and raw[i].isalpha():
        i += 1
    prefix, digits = raw[:i], raw[i:]
    if digits:
        digits = str(int(digits))  # drop leading zeros
    return prefix + digits


def team_sail_map(setup: dict, id_offset: int = 0) -> dict[int, str]:
    """Map YB team id -> sail number (RaceSetup.sail), not bow markerText.

    id_offset keeps Class C team ids distinct when merging multiple race keys
    that reuse small integers (rare collision guard — unused when races share ids).
    """
    m: dict[int, str] = {}
    for t in setup.get("teams") or []:
        tid = t.get("id")
        if tid is None:
            continue
        typ = (t.get("type") or "").upper()
        if typ == "COMMITTEE":
            continue
        sail = (t.get("sail") or "").strip()
        marker = (t.get("markerText") or "").strip()
        name = (t.get("name") or "").strip()
        label = sail or name or marker
        if label:
            m[int(tid) + id_offset] = label
    return m


def match_pack_key(label: str, pack_keys: list[str]) -> str | None:
    want = norm_sail(label)
    if not want:
        return None
    by_norm = {norm_sail(k): k for k in pack_keys}
    if want in by_norm:
        return by_norm[want]
    # bare number vs SA-prefixed
    if want.isdigit():
        for n, k in by_norm.items():
            if n.endswith(want) and n[: -len(want)].rstrip("0123456789") in ("", "SA"):
                return k
    if want.startswith("SA") and want[2:].isdigit():
        bare = want[2:]
        if bare in by_norm:
            return by_norm[bare]
    return None


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
            f.write("\n")
        os.chmod(tmp, 0o664)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def last_fix_ms(fixes: list) -> int:
    if not fixes:
        return 0
    return int(fixes[-1][0])


def extend_trail(trail: dict, end_ts_ms: int) -> None:
    gun = int(trail["grid_start_ts_ms"] if trail.get("grid_start_ts_ms") is not None else trail["gun_ts_ms"])
    step = int(trail.get("step_ms") or STEP_MS)
    need_n = int((end_ts_ms - gun) // step) + 1
    if need_n < 1:
        need_n = 1
    cur_n = int(trail.get("n") or 0)
    if need_n <= cur_n:
        trail["end_ts_ms"] = end_ts_ms
        return
    add = need_n - cur_n
    for sail, series in (trail.get("boats") or {}).items():
        lat = series.setdefault("lat", [])
        lon = series.setdefault("lon", [])
        # pad to cur_n first if inconsistent
        while len(lat) < cur_n:
            lat.append(None)
        while len(lon) < cur_n:
            lon.append(None)
        lat.extend([None] * add)
        lon.extend([None] * add)
    trail["n"] = need_n
    trail["end_ts_ms"] = end_ts_ms
    trail["step_ms"] = step


def place_on_trail(trail: dict, sail: str, ts_ms: int, lat: float, lon: float) -> None:
    gun = int(trail["grid_start_ts_ms"] if trail.get("grid_start_ts_ms") is not None else trail["gun_ts_ms"])
    step = int(trail.get("step_ms") or STEP_MS)
    idx = int(round((ts_ms - gun) / step))
    if idx < 0:
        return
    series = trail["boats"].setdefault(sail, {"lat": [], "lon": []})
    lat_a = series.setdefault("lat", [])
    lon_a = series.setdefault("lon", [])
    while len(lat_a) <= idx:
        lat_a.append(None)
        lon_a.append(None)
    lat_a[idx] = lat
    lon_a[idx] = lon


def merge_moments_into_pack(
    replay: dict,
    trail: dict,
    sail: str,
    moments: list[dict],
) -> int:
    """Return count of newly appended gps fixes."""
    fixes = replay.setdefault("gps_fixes", {}).setdefault(sail, [])
    added = 0
    last = last_fix_ms(fixes)
    moments = sorted(moments or [], key=lambda m: int(m.get("at") or 0))
    for m in moments:
        at_s = int(m["at"])
        ts_ms = at_s * 1000
        if ts_ms <= last:
            continue
        lat = float(m["lat"])
        lon = float(m["lon"])
        fixes.append([ts_ms, lat, lon])
        place_on_trail(trail, sail, ts_ms, lat, lon)
        last = ts_ms
        added += 1
    return added


def pack_fleet(fleet: str, id_to_label: dict[int, str], tracks: list[dict]) -> dict:
    replay_path = DATA / f"west-coast-{fleet}-replay.json"
    trail_path = DATA / f"west-coast-{fleet}-trail.json"
    if not replay_path.exists() or not trail_path.exists():
        return {"fleet": fleet, "skipped": "missing files"}

    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    trail = json.loads(trail_path.read_text(encoding="utf-8"))
    pack_keys = list((replay.get("boats") or {}).keys())
    label_to_key: dict[str, str] = {}
    for tid, label in id_to_label.items():
        key = match_pack_key(label, pack_keys)
        if key:
            label_to_key[str(tid)] = key

    added_total = 0
    max_ts = int(replay.get("end_ts_ms") or 0)
    for tr in tracks:
        key = label_to_key.get(str(tr["id"]))
        if not key:
            continue
        added_total += merge_moments_into_pack(replay, trail, key, tr.get("moments") or [])
        fixes = replay["gps_fixes"].get(key) or []
        if fixes:
            max_ts = max(max_ts, int(fixes[-1][0]))

    # Also advance end to wall-clock capped by newest fix (do not invent future)
    if max_ts <= int(replay.get("end_ts_ms") or 0) and added_total == 0:
        return {"fleet": fleet, "added": 0, "end_ts_ms": replay.get("end_ts_ms"), "unchanged": True}

    # Snap end to step grid
    gun = int(trail["grid_start_ts_ms"] if trail.get("grid_start_ts_ms") is not None else trail["gun_ts_ms"])
    step = int(trail.get("step_ms") or STEP_MS)
    end_ts = max(int(replay.get("end_ts_ms") or 0), max_ts)
    # ceil to step
    if end_ts > gun:
        end_ts = gun + ((end_ts - gun + step - 1) // step) * step

    extend_trail(trail, end_ts)
    replay["end_ts_ms"] = end_ts
    replay["play_end_ts_ms"] = end_ts
    trail["end_ts_ms"] = end_ts

    # Ensure every boat key exists in both gps_fixes and trail.boats
    for sail in pack_keys:
        replay.setdefault("gps_fixes", {}).setdefault(sail, replay.get("gps_fixes", {}).get(sail) or [])
        if sail not in trail.setdefault("boats", {}):
            n = int(trail.get("n") or 0)
            trail["boats"][sail] = {"lat": [None] * n, "lon": [None] * n}
        else:
            # pad lengths
            series = trail["boats"][sail]
            n = int(trail.get("n") or 0)
            while len(series.setdefault("lat", [])) < n:
                series["lat"].append(None)
            while len(series.setdefault("lon", [])) < n:
                series["lon"].append(None)

    atomic_write(replay_path, replay)
    atomic_write(trail_path, trail)
    try:
        os.chown(replay_path, -1, os.stat(DATA).st_gid)
        os.chown(trail_path, -1, os.stat(DATA).st_gid)
    except Exception:
        pass
    return {"fleet": fleet, "added": added_total, "end_ts_ms": end_ts, "boats_mapped": len(label_to_key)}


def load_race_tracks(race_key: str) -> tuple[dict[int, str], list[dict], list[str]]:
    """Return (id->sail, tracks, source_parts) for one YB race key."""
    setup = fetch_json(f"JSON/{race_key}/RaceSetup")
    id_to_label = team_sail_map(setup)
    by_id: dict[int, dict] = {}
    source_parts: list[str] = []
    try:
        for tr in zxe(fetch_bytes(f"BIN/{race_key}/AllPositions3")):
            by_id[int(tr["id"])] = tr
        source_parts.append(f"{race_key}/AllPositions3")
    except Exception as e:
        log(f"{race_key} AllPositions3 failed: {e}")
    try:
        for tr in zxe(fetch_bytes(f"BIN/{race_key}/LatestPositions3")):
            tid = int(tr["id"])
            if tid not in by_id:
                by_id[tid] = tr
            else:
                seen = {(int(m["at"]), round(m["lat"], 5), round(m["lon"], 5)) for m in by_id[tid]["moments"]}
                for m in tr.get("moments") or []:
                    key = (int(m["at"]), round(m["lat"], 5), round(m["lon"], 5))
                    if key not in seen:
                        by_id[tid]["moments"].append(m)
        source_parts.append(f"{race_key}/LatestPositions3")
    except Exception as e:
        log(f"{race_key} LatestPositions3 failed: {e}")
    # Prefix track ids with race-key namespace only when ids collide across races
    # with different sails — here AB and C use distinct team ids, so keep raw ids.
    return id_to_label, list(by_id.values()), source_parts


def main() -> int:
    try:
        id_to_label: dict[int, str] = {}
        tracks: list[dict] = []
        source_parts: list[str] = []
        for race_key in RACE_KEYS:
            labels, race_tracks, parts = load_race_tracks(race_key)
            # Merge labels; if same team id maps to different sails, keep first (AB)
            for tid, sail in labels.items():
                id_to_label.setdefault(tid, sail)
            # Merge tracks by team id (Class C ids 3,6 do not overlap AB racing ids)
            existing = {int(t["id"]): t for t in tracks}
            for tr in race_tracks:
                tid = int(tr["id"])
                if tid not in existing:
                    tracks.append(tr)
                    existing[tid] = tr
                else:
                    seen = {(int(m["at"]), round(m["lat"], 5), round(m["lon"], 5)) for m in existing[tid]["moments"]}
                    for m in tr.get("moments") or []:
                        key = (int(m["at"]), round(m["lat"], 5), round(m["lon"], 5))
                        if key not in seen:
                            existing[tid]["moments"].append(m)
            source_parts.extend(parts)
        source = "+".join(source_parts) or "none"
        if not tracks:
            raise RuntimeError("no BIN tracks decoded")
        results = []
        for fleet in ("all", "ab", "c"):
            results.append(pack_fleet(fleet, id_to_label, tracks))
        log(f"ok source={source} teams={len(id_to_label)} tracks={len(tracks)} {results}")
        print(json.dumps({"ok": True, "source": source, "results": results}))
        return 0
    except Exception as e:
        log(f"ERR {type(e).__name__}: {e}")
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
