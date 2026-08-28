#!/usr/bin/env python3
"""Lipton -dev live clock + latest GPS as received. Does not invent guns or tracks."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lipton_vakaros import (
    FINISHED_STAGES,
    LIPTON_EVENT_ID,
    LIPTON_FLEET,
    _j22_division,
    fetch_regatta_doc,
    parse_ts,
    summarize_event,
)

TELEAPI = "https://teleapi.regatta.app/telemetry"
WINDOW_MS = 45_000
HISTORY_MS = 4 * 60 * 1000
LIVE_TRAIL_MS = 45_000
STEP_MS = 280
CLOCK_LAG_MS = 2_000
CHUNK_MS = 3 * 60 * 1000
SNAP_TTL_S = 0.8
SNAP_PATH = Path("/tmp/lipton_dev_live_snap.json")
STATE_PATH = Path("/tmp/lipton_dev_live_state.json")
HISTORY_PATHS = (
    Path("/var/www/sailingsa/js/lipton-dev-live-history.json"),
    Path("/tmp/lipton_dev_live_history.json"),
)
PIN_SN = 25607
MARK_SN = {"1": 25633, "2": 25610, "3": 25619, "4": 25607}


def _ms(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp() * 1000)


def _sn_int(sn) -> int | None:
    s = str(sn or "").strip()
    if not s:
        return None
    if s.isdigit() and len(s) <= 6:
        return int(s)
    try:
        return int(s[-4:], 16)
    except ValueError:
        return None


def _pt(rec: dict | None) -> dict | None:
    if not rec:
        return None
    lat, lon = rec.get("latitude"), rec.get("longitude")
    if lat is None or lon is None:
        return None
    out = {
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "ts_ms": rec.get("ts"),
    }
    hdg = rec.get("heading")
    if hdg is not None:
        out["hdg"] = hdg
    sog = rec.get("sog")
    if sog is not None:
        out["sog"] = sog
    return out


def _device_map(doc: dict) -> dict:
    """Map teleapi sn → role. Always keep pin / RC / M1–M3 fallbacks."""
    out = {"rc": 25604, "pin": PIN_SN, "marks": dict(MARK_SN)}
    for d in doc.get("rcDevices") or []:
        if not isinstance(d, dict):
            continue
        sn = _sn_int(d.get("sn"))
        name = str(d.get("name") or "").strip()
        if sn is None or not name:
            continue
        if name.upper() == "RC":
            out["rc"] = sn
        elif name == "4":
            out["pin"] = sn
            out["marks"]["4"] = sn
        elif name.isdigit():
            out["marks"][name] = sn
    if "4" not in out["marks"]:
        out["marks"]["4"] = out["pin"]
    return out


def _tele_latest(after_ms: int, before_ms: int) -> list[dict]:
    url = (
        f"{TELEAPI}/event/{LIPTON_EVENT_ID}"
        f"?after={after_ms}&before={before_ms}&limit=20000&division={LIPTON_FLEET}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SailingSA-LiptonLive/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    fields = data.get("Fields") or []
    rows = data.get("Rows") or []
    idx = {k: i for i, k in enumerate(fields)}
    return [{k: row[i] for k, i in idx.items()} for row in rows]


def _load_snap_file() -> dict | None:
    try:
        if time.time() - SNAP_PATH.stat().st_mtime > SNAP_TTL_S:
            return None
        data = json.loads(SNAP_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("ok"):
            return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def _save_snap_file(payload: dict) -> None:
    try:
        tmp = SNAP_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")
        tmp.replace(SNAP_PATH)
    except OSError:
        pass


def _save_state(payload: dict) -> None:
    keep = {
        k: payload.get(k)
        for k in (
            "race_number",
            "stage",
            "gun_ts_ms",
            "gun_sast",
            "prep_flag",
            "ocs",
            "reason",
        )
    }
    try:
        STATE_PATH.write_text(json.dumps(keep), encoding="utf-8")
    except OSError:
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _trail_from_recs(recs: list[dict], keep_ms: int | None) -> list[dict]:
    pts = sorted((p for p in recs if p.get("latitude") is not None), key=lambda p: int(p.get("ts") or 0))
    trail = []
    for p in pts:
        ts = int(p.get("ts") or 0)
        if ts <= 0:
            continue
        step = {
            "lat": round(float(p["latitude"]), 6),
            "lon": round(float(p["longitude"]), 6),
            "ts_ms": ts,
        }
        if p.get("heading") is not None:
            step["hdg"] = p.get("heading")
        if p.get("sog") is not None:
            step["sog"] = p.get("sog")
        if trail and ts - trail[-1]["ts_ms"] < STEP_MS:
            trail[-1] = step
        else:
            trail.append(step)
    if keep_ms and trail:
        cut = trail[-1]["ts_ms"] - keep_ms
        trail = [x for x in trail if x["ts_ms"] >= cut]
    return trail


def _tele_range(after_ms: int, before_ms: int) -> list[dict]:
    rows: list[dict] = []
    t = int(after_ms)
    end_all = int(before_ms)
    while t < end_all:
        end = min(t + CHUNK_MS, end_all)
        rows.extend(_tele_latest(t, end))
        t = end
    return rows


def _first_trail_ts(data: dict) -> int | None:
    first = None
    for b in (data.get("boats") or {}).values():
        t = (b or {}).get("trail") or []
        if not t:
            continue
        ts = int(t[0].get("ts_ms") or 0)
        if ts and (first is None or ts < first):
            first = ts
    return first


def _covers_start(data: dict, gun_ms: int | None) -> bool:
    """Enough boats from the gun to stop a full-race re-fetch. Not every boat."""
    boats = (data or {}).get("boats") or {}
    if len(boats) < 10:
        return False
    if gun_ms is None:
        return _history_span_ms(data) >= 20_000
    gun = int(gun_ms)
    from_gun = 0
    for b in boats.values():
        t = (b or {}).get("trail") or []
        if t and int(t[0].get("ts_ms") or 0) <= gun + 15_000:
            from_gun += 1
    pin = ((data.get("pin") or {}).get("trail") or [])
    pin_ok = bool(pin and int(pin[0].get("ts_ms") or 0) <= gun + 15_000)
    return from_gun >= min(12, len(boats)) and pin_ok


def _merge_trail(old: list | None, new: list | None) -> list[dict]:
    by: dict[int, dict] = {}
    for p in (old or []) + (new or []):
        if not p or p.get("lat") is None or p.get("lon") is None:
            continue
        ts = int(p.get("ts_ms") or 0)
        if ts <= 0:
            continue
        by[ts] = p
    return [by[k] for k in sorted(by)]


def _slice_trail(trail: list[dict], keep_ms: int, *, gun_ms: int | None = None) -> list[dict]:
    if not trail:
        return []
    if gun_ms:
        cut = int(gun_ms) - 30_000
    else:
        cut = trail[-1]["ts_ms"] - keep_ms
    return [x for x in trail if x["ts_ms"] >= cut]


def _boat_from_trail(trail: list[dict]) -> dict | None:
    if not trail:
        return None
    last = dict(trail[-1])
    last["trail"] = trail
    return last


def _history_span_ms(data: dict) -> int:
    span = 0
    for b in (data.get("boats") or {}).values():
        t = (b or {}).get("trail") or []
        if len(t) >= 2:
            span = max(span, int(t[-1].get("ts_ms") or 0) - int(t[0].get("ts_ms") or 0))
    return span


def _load_history_file(*, max_age_s: float | None = 180) -> dict:
    for p in HISTORY_PATHS:
        try:
            if not p.is_file():
                continue
            if max_age_s is not None and time.time() - p.stat().st_mtime > max_age_s:
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("boats"):
                return data
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return {}


def _merge_history_payload(old: dict, new: dict) -> dict:
    if not old or not old.get("boats"):
        return new
    out = dict(new)
    gun_ms = new.get("gun_ts_ms") or old.get("gun_ts_ms")
    boats: dict[str, dict] = {}
    sails = set(old.get("boats") or {}) | set(new.get("boats") or {})
    for sail in sails:
        ob = (old.get("boats") or {}).get(sail) or {}
        nb = (new.get("boats") or {}).get(sail) or {}
        trail = _merge_trail(ob.get("trail"), nb.get("trail") or ([nb] if nb.get("lat") is not None else []))
        trail = _slice_trail(trail, HISTORY_MS, gun_ms=gun_ms)
        built = _boat_from_trail(trail)
        if built:
            boats[sail] = built
    out["boats"] = boats

    def merge_mark(old_m, new_m):
        trail = _merge_trail(
            (old_m or {}).get("trail") or ([old_m] if old_m and old_m.get("lat") is not None else []),
            (new_m or {}).get("trail") or ([new_m] if new_m and new_m.get("lat") is not None else []),
        )
        trail = _slice_trail(trail, HISTORY_MS, gun_ms=gun_ms)
        return _boat_from_trail(trail)

    pin = merge_mark(old.get("pin"), new.get("pin"))
    rc = merge_mark(old.get("committee"), new.get("committee"))
    if pin:
        out["pin"] = pin
    if rc:
        out["committee"] = rc
        if pin:
            out["start_line"] = {"left": pin, "right": rc}
    marks = {}
    keys = set(old.get("marks") or {}) | set(new.get("marks") or {})
    for k in keys:
        mk = merge_mark((old.get("marks") or {}).get(k), (new.get("marks") or {}).get(k))
        if mk:
            marks[k] = mk
    if marks:
        out["marks"] = marks
    return out


def _save_history_file(payload: dict) -> None:
    old = _load_history_file(max_age_s=None)
    merged = _merge_history_payload(old, payload)
    text = json.dumps(merged, separators=(",", ":"), default=str)
    for p in HISTORY_PATHS:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(p)
        except OSError:
            continue


def live_snapshot(*, history: bool = False) -> dict:
    if not history:
        cached_snap = _load_snap_file()
        if cached_snap:
            return cached_snap
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    playback_ms = now_ms - CLOCK_LAG_MS
    cached = _load_state()
    stored_hit = _load_history_file(max_age_s=None) if history else {}
    doc = None
    summary = None
    try:
        doc = fetch_regatta_doc()
        summary = summarize_event(doc)
    except Exception:
        summary = None
    races = (summary or {}).get("races") or []
    unfinished = [r for r in races if str(r.get("stage") or "").lower() not in FINISHED_STAGES]
    race = min(unfinished, key=lambda r: r["race_number"]) if unfinished else None
    gun = parse_ts(race.get("gun_at_utc")) if race else None
    gun_ms = _ms(gun)
    # Finished-race guns must not stay "live" — that re-fetches the whole race
    # and hides the next start. Cached gun is only for an unfinished race.
    if gun_ms is None and race is None:
        waiting = True
    elif gun_ms is None and cached.get("gun_ts_ms"):
        gun_ms = int(cached["gun_ts_ms"])
        race = race or {
            "race_number": cached.get("race_number"),
            "stage": cached.get("stage") or "starting",
            "gun_at_sast": cached.get("gun_sast"),
        }
        waiting = False
    else:
        waiting = gun_ms is None
    delta = (playback_ms - gun_ms) if gun_ms is not None else None
    devices = _device_map(doc) if doc else {"rc": 25604, "pin": PIN_SN, "marks": dict(MARK_SN)}
    raw_race = None
    if doc and race and race.get("race_number"):
        raw_race = next(
            (
                x
                for x in (_j22_division(doc).get("races") or [])
                if int(x.get("raceNumber") or 0) == race["race_number"]
            ),
            None,
        )
    start0 = ((raw_race or {}).get("starts") or [{}])[0] if raw_race else {}
    keep_ms = WINDOW_MS if waiting else (HISTORY_MS if history else WINDOW_MS)
    rec_keep: int | None = keep_ms
    have_hist = _covers_start(stored_hit, gun_ms)
    prestart = gun_ms is not None and now_ms < int(gun_ms) - 5_000
    if (not waiting) and (not prestart) and history and gun_ms is not None and not have_hist:
        start = int(gun_ms) - 30_000
        if start < now_ms:
            rows = _tele_range(start, now_ms + 2000)
            rec_keep = None
        else:
            rows = _tele_latest(now_ms - keep_ms, now_ms + 2000)
    else:
        rows = _tele_latest(now_ms - keep_ms, now_ms + 2000)
    boats: dict[str, dict] = {}
    by_sn: dict[int, dict] = {}
    tracks: dict[str, list] = {}
    sn_tracks: dict[int, list] = {}
    for rec in rows:
        sn = rec.get("sn")
        try:
            sn = int(sn) if sn is not None else None
        except (TypeError, ValueError):
            sn = None
        if rec.get("role") == "competitor" and rec.get("sail_number"):
            sail = str(rec["sail_number"]).strip()
            tracks.setdefault(sail, []).append(rec)
        if sn is not None:
            sn_tracks.setdefault(sn, []).append(rec)
            prev = by_sn.get(sn)
            if not prev or int(rec.get("ts") or 0) >= int(prev.get("ts") or 0):
                by_sn[sn] = rec
    for sail, pts in tracks.items():
        trail = _trail_from_recs(pts, rec_keep)
        built = _boat_from_trail(trail)
        if built:
            boats[sail] = built
    pin_trail = _trail_from_recs(sn_tracks.get(devices["pin"]) or [], rec_keep)
    rc_sn = devices.get("rc")
    rc_trail = _trail_from_recs(sn_tracks.get(rc_sn) or [], rec_keep) if rc_sn else []
    pin = pin_trail[-1] if pin_trail else _pt(by_sn.get(devices["pin"]))
    rc = rc_trail[-1] if rc_trail else (_pt(by_sn.get(rc_sn)) if rc_sn else None)
    if pin and pin_trail:
        pin = dict(pin)
        pin["trail"] = pin_trail
    if rc and rc_trail:
        rc = dict(rc)
        rc["trail"] = rc_trail
    marks = {}
    for name, sn in (devices.get("marks") or {}).items():
        if name == "4":
            continue
        mtrail = _trail_from_recs(sn_tracks.get(sn) or [], rec_keep)
        if mtrail:
            mk = dict(mtrail[-1])
            mk["trail"] = mtrail
            marks[name] = mk
        else:
            pt = _pt(by_sn.get(sn))
            if pt:
                marks[name] = pt
    start_line = None
    if pin and rc:
        start_line = {"left": pin, "right": rc}
    out = {
        "ok": True,
        "live": True,
        "waiting": waiting,
        "reason": ((summary or cached).get("next_race_reason") if waiting else "tracker gun vs wall clock"),
        "race_number": (
            (race["race_number"] if race else None)
            or (summary or {}).get("next_race_number")
            or (None if waiting else cached.get("race_number"))
        ),
        "stage": (race.get("stage") if race else None) or "waiting",
        "gun_ts_ms": gun_ms,
        "gun_sast": (race.get("gun_at_sast") if race else None),
        "now_ts_ms": now_ms,
        "playback_ts_ms": playback_ms,
        "clock_lag_ms": CLOCK_LAG_MS,
        "delta_ms": delta,
        "sign": None if delta is None else ("T+" if delta >= 0 else "T-"),
        "prep_flag": start0.get("prepFlag"),
        "ocs": list(start0.get("ocsParticipants") or []),
        "boats": boats,
        "marks": marks,
        "pin": pin,
        "committee": rc,
        "start_line": start_line,
        "received": {
            "boats": len(boats),
            "marks": len(marks),
            "pin": pin is not None,
            "committee": rc is not None,
        },
        "source": "firestore gun + teleapi as received. Empty = not received.",
    }
    _save_state(out)
    if history and boats and not waiting:
        _save_history_file(out)
    if history and not waiting:
        stored = _load_history_file(max_age_s=None)
        if stored and stored.get("boats"):
            stored = dict(stored)
            for k, v in out.items():
                if k not in ("boats", "marks", "pin", "committee", "start_line"):
                    stored[k] = v
            stored["from_cache"] = False
            return stored
    if not history:
        _save_snap_file(out)
    return out


if __name__ == "__main__":
    print(json.dumps(live_snapshot(), indent=2, default=str))
