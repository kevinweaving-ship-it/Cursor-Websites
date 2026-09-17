"""UKZN Agromet Midmar (HMYC) weather — Campbell LoggerNet Web Server.

Public dashboard: https://agromet.ukzn.ac.za/midmar/index.html
Table Midmar.Five is 5-minute: WS_ms_S_WVT (avg m/s), windspeed_ms_Max (gust m/s),
WindDir_D1_WVT (deg). Convert m/s → knots for the generic wind card.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

SLUG = "agromet-midmar"
STATION_NAME = "Henley Midmar Agromet"
AGROMET_QUERY = "https://agromet.ukzn.ac.za/midmar/?command=DataQuery"
URI = "Server:Midmar.Five"
SAST = ZoneInfo("Africa/Johannesburg")
MS_TO_KT = 1.9438444924406
FIELDS = [
    "AirTC_Avg",
    "RH",
    "solarradiation_Avg",
    "baromin_Avg",
    "rain_mm_Tot",
    "WS_ms_S_WVT",
    "WindDir_D1_WVT",
    "WindDir_SD1_WVT",
    "windspeed_ms_Max",
]

_SSL = ssl._create_unverified_context()


def _ms_to_kt(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return round(n * MS_TO_KT, 2)


def _parse_observed_at(raw: str) -> Optional[str]:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif "+" in s[10:] or s.count("-") > 2:
            dt = datetime.fromisoformat(s)
        else:
            dt = datetime.fromisoformat(s).replace(tzinfo=SAST)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def reading_from_record(rec: dict, field_names: Optional[list[str]] = None) -> Optional[dict]:
    names = field_names or FIELDS
    vals = rec.get("vals") or []
    by = {names[i]: vals[i] if i < len(vals) else None for i in range(len(names))}
    observed = _parse_observed_at(str(rec.get("time") or ""))
    if not observed:
        return None
    avg_kt = _ms_to_kt(by.get("WS_ms_S_WVT"))
    gust_kt = _ms_to_kt(by.get("windspeed_ms_Max"))
    try:
        wind_dir = float(by["WindDir_D1_WVT"]) if by.get("WindDir_D1_WVT") is not None else None
    except (TypeError, ValueError):
        wind_dir = None
    try:
        temp_c = float(by["AirTC_Avg"]) if by.get("AirTC_Avg") is not None else None
    except (TypeError, ValueError):
        temp_c = None
    try:
        humidity = float(by["RH"]) if by.get("RH") is not None else None
    except (TypeError, ValueError):
        humidity = None
    return {
        "station_slug": SLUG,
        "station_name": STATION_NAME,
        "provider": "ukzn_agromet",
        "provider_station_id": "Midmar.Five",
        "observed_at": observed,
        "wind_kt": avg_kt,
        "wind_avg_kt": avg_kt,
        "wind_gust_kt": gust_kt,
        "wind_dir_deg": wind_dir,
        "wind_dir_avg_deg": wind_dir,
        "temp_c": temp_c,
        "humidity_pct": humidity,
        "period_sec": 300,
    }


def fetch_agromet_five(hours: int = 12) -> dict:
    hours = max(1, min(int(hours or 12), 48))
    start = datetime.now(SAST) - timedelta(hours=hours)
    p1 = start.strftime("%Y-%m-%dT%H:%M:%S")
    q = urllib.parse.urlencode(
        {
            "command": "DataQuery",
            "uri": URI,
            "format": "json",
            "mode": "since-time",
            "p1": p1,
        }
    )
    url = "https://agromet.ukzn.ac.za/midmar/?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "SailingSA-weather/1.0"})
    with urllib.request.urlopen(req, context=_SSL, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    names = [f.get("name") for f in ((payload.get("head") or {}).get("fields") or []) if f.get("name")]
    readings = []
    for rec in payload.get("data") or []:
        row = reading_from_record(rec, names or None)
        if row:
            readings.append(row)
    return {
        "ok": True,
        "slug": SLUG,
        "count": len(readings),
        "readings": readings,
        "source": "ukzn_agromet_midmar",
    }


def history_payload(hours: int = 12) -> dict:
    try:
        return fetch_agromet_five(hours)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "slug": SLUG, "count": 0, "readings": [], "err": str(exc)[:200]}
