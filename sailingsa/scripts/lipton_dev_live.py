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
WINDOW_MS = 25_000
HISTORY_MS = 8 * 60 * 1000
CLOCK_LAG_MS = 10_000
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
    """Map teleapi sn → role from current Firestore names. Empty if not named."""
    out = {"rc": None, "pin": PIN_SN, "marks": {}}
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
        elif name.isdigit() and name != "4":
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


def _trail_from_recs(recs: list[dict], keep: int) -> list[dict]:
    pts = sorted((p for p in recs if p.get("latitude") is not None), key=lambda p: int(p.get("ts") or 0))
    trail = []
    for p in pts:
        ts = int(p.get("ts") or 0)
        step = {
            "lat": round(float(p["latitude"]), 6),
            "lon": round(float(p["longitude"]), 6),
            "ts_ms": ts,
        }
        if p.get("heading") is not None:
            step["hdg"] = p.get("heading")
        if trail and ts - trail[-1]["ts_ms"] < 900:
            trail[-1] = step
        else:
            trail.append(step)
    if keep >= 0:
        return trail[-keep:]
    return trail


def _load_history_file() -> dict:
    for p in HISTORY_PATHS:
        try:
            if p.is_file() and time.time() - p.stat().st_mtime < 180:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("boats"):
                    return data
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return {}


def _save_history_file(payload: dict) -> None:
    text = json.dumps(payload, separators=(",", ":"), default=str)
    for p in HISTORY_PATHS:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        except OSError:
            continue


def live_snapshot(*, history: bool = False) -> dict:
    if history:
        hit = _load_history_file()
        if hit:
            hit = dict(hit)
            hit["from_cache"] = True
            return hit
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    playback_ms = now_ms - CLOCK_LAG_MS
    cached = _load_state()
    doc = None
    summary = None
    if not cached.get("gun_ts_ms"):
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
    if gun_ms is None and cached.get("gun_ts_ms"):
        gun_ms = int(cached["gun_ts_ms"])
        race = race or {
            "race_number": cached.get("race_number"),
            "stage": cached.get("stage") or "starting",
            "gun_at_sast": cached.get("gun_sast"),
        }
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
    rows = _tele_latest(now_ms - (HISTORY_MS if history else WINDOW_MS), now_ms + 2000)
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
    keep = 0 if history else 20
    for sail, pts in tracks.items():
        trail = _trail_from_recs(pts, keep)
        if not trail:
            continue
        last = trail[-1]
        boats[sail] = {
            "lat": last["lat"],
            "lon": last["lon"],
            "ts_ms": last["ts_ms"],
            "hdg": last.get("hdg"),
            "trail": trail,
        }
    pin_trail = _trail_from_recs(sn_tracks.get(devices["pin"]) or [], keep)
    rc_sn = devices.get("rc")
    rc_trail = _trail_from_recs(sn_tracks.get(rc_sn) or [], keep) if rc_sn else []
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
        mtrail = _trail_from_recs(sn_tracks.get(sn) or [], keep)
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
        "race_number": (race["race_number"] if race else None) or (summary or {}).get("next_race_number") or cached.get("race_number"),
        "stage": (race.get("stage") if race else None) or "waiting",
        "gun_ts_ms": gun_ms,
        "gun_sast": (race.get("gun_at_sast") if race else None) or cached.get("gun_sast"),
        "now_ts_ms": now_ms,
        "playback_ts_ms": playback_ms,
        "clock_lag_ms": CLOCK_LAG_MS,
        "delta_ms": delta,
        "sign": None if delta is None else ("T+" if delta >= 0 else "T-"),
        "prep_flag": start0.get("prepFlag") or cached.get("prep_flag"),
        "ocs": list(start0.get("ocsParticipants") or cached.get("ocs") or []),
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
        "source": "firestore gun + teleapi last 30s. Empty = not received.",
    }
    if gun_ms is not None:
        _save_state(out)
    if boats:
        _save_history_file(out)
    return out


if __name__ == "__main__":
    print(json.dumps(live_snapshot(), indent=2, default=str))
