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
    fetch_lipton_from_tracker,
    fetch_regatta_doc,
    parse_ts,
)

TELEAPI = "https://teleapi.regatta.app/telemetry"
WINDOW_MS = 30_000

# Historic teleapi integers for pin / marks. RC is derived from Firestore.
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


def live_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    summary = fetch_lipton_from_tracker()
    races = summary.get("races") or []
    unfinished = [r for r in races if str(r.get("stage") or "").lower() not in FINISHED_STAGES]
    race = min(unfinished, key=lambda r: r["race_number"]) if unfinished else None
    gun = parse_ts(race.get("gun_at_utc")) if race else None
    gun_ms = _ms(gun)
    waiting = gun is None
    delta = (now_ms - gun_ms) if gun_ms is not None else None
    doc = fetch_regatta_doc()
    devices = _device_map(doc)
    raw_race = None
    if race:
        raw_race = next(
            (
                x
                for x in (_j22_division(doc).get("races") or [])
                if int(x.get("raceNumber") or 0) == race["race_number"]
            ),
            None,
        )
    start0 = ((raw_race or {}).get("starts") or [{}])[0] if raw_race else {}
    rows = _tele_latest(now_ms - WINDOW_MS, now_ms + 1000)
    want_n = race["race_number"] if race else None
    boats: dict[str, dict] = {}
    by_sn: dict[int, dict] = {}
    for rec in rows:
        sn = rec.get("sn")
        try:
            sn = int(sn) if sn is not None else None
        except (TypeError, ValueError):
            sn = None
        rn = rec.get("race_number")
        if want_n is not None and rn not in (want_n, None, 0):
            continue
        if rec.get("role") == "competitor" and rec.get("sail_number"):
            sail = str(rec["sail_number"]).strip()
            prev = boats.get(sail)
            if not prev or int(rec.get("ts") or 0) >= int(prev.get("ts_ms") or 0):
                pt = _pt(rec)
                if pt:
                    boats[sail] = pt
        if sn is not None:
            prev = by_sn.get(sn)
            if not prev or int(rec.get("ts") or 0) >= int(prev.get("ts") or 0):
                by_sn[sn] = rec
    pin = _pt(by_sn.get(devices["pin"]))
    rc = _pt(by_sn.get(devices["rc"])) if devices.get("rc") else None
    marks = {}
    for name, sn in (devices.get("marks") or {}).items():
        if name == "4":
            continue
        pt = _pt(by_sn.get(sn))
        if pt:
            marks[name] = pt
    start_line = None
    if pin and rc:
        start_line = {"left": pin, "right": rc}
    return {
        "ok": True,
        "live": True,
        "waiting": waiting,
        "reason": summary.get("next_race_reason") if waiting else "tracker gun vs wall clock",
        "race_number": race["race_number"] if race else summary.get("next_race_number"),
        "stage": race.get("stage") if race else "waiting",
        "gun_ts_ms": gun_ms,
        "gun_sast": race.get("gun_at_sast") if race else None,
        "now_ts_ms": now_ms,
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
        "source": "firestore gun + teleapi last 30s. Empty = not received.",
    }


if __name__ == "__main__":
    print(json.dumps(live_snapshot(), indent=2, default=str))
