"""HYC venue wind from Weather Underground PWS IOVERS2.

Catalog: GET /api/weather/clubs/HYC/stations (venue slug pws-iovers2).
WU current/history wind is mph (imperial) or km/h (metric). Convert to knots
for the generic weather card — same units as ZVYC / HMYC.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

SLUG = "pws-iovers2"
STATION_NAME = "Overstrand IOVERS2"
PROVIDER = "weather_underground"
PROVIDER_ID = "IOVERS2"
STATIONS_URL = "https://sailingsa.co.za/api/weather/clubs/HYC/stations"
WU_CURRENT = "https://api.weather.com/v2/pws/observations/current"
WU_DAY = "https://api.weather.com/v2/pws/observations/all/1day"
# Public WU web key (same as dashboard). Override with WU_API_KEY.
WU_WEB_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
MPH_TO_KT = 0.8689762419
KMH_TO_KT = 0.5399568035
DEFAULT_PERIOD_SEC = 60
UA = "SailingSA-weather/1.0"

_cache: dict[str, Any] = {"at": 0.0, "hours": 0, "payload": None}
_CACHE_SEC = 30.0


def mph_to_kt(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return round(n * MPH_TO_KT, 2)


def kmh_to_kt(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return round(n * KMH_TO_KT, 2)


def _wu_key() -> str:
    return (os.environ.get("WU_API_KEY") or WU_WEB_KEY).strip()


def _obs_iso(obs: dict) -> Optional[str]:
    raw = str(obs.get("obsTimeUtc") or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def reading_from_wu_obs(obs: dict, period_sec: int = DEFAULT_PERIOD_SEC) -> Optional[dict]:
    """Map one WU PWS observation to the generic weather-card reading (knots)."""
    if not isinstance(obs, dict):
        return None
    observed = _obs_iso(obs)
    if not observed:
        return None
    imperial = obs.get("imperial") if isinstance(obs.get("imperial"), dict) else None
    metric = obs.get("metric") if isinstance(obs.get("metric"), dict) else None
    if imperial:
        avg_kt = mph_to_kt(imperial.get("windSpeed"))
        gust_kt = mph_to_kt(imperial.get("windGust"))
        try:
            temp_c = round((float(imperial["temp"]) - 32.0) * 5.0 / 9.0, 2) if imperial.get("temp") is not None else None
        except (TypeError, ValueError):
            temp_c = None
    elif metric:
        avg_kt = kmh_to_kt(metric.get("windSpeed"))
        gust_kt = kmh_to_kt(metric.get("windGust"))
        try:
            temp_c = float(metric["temp"]) if metric.get("temp") is not None else None
        except (TypeError, ValueError):
            temp_c = None
    else:
        return None
    try:
        wind_dir = float(obs["winddir"]) if obs.get("winddir") is not None else None
    except (TypeError, ValueError):
        wind_dir = None
    try:
        humidity = float(obs["humidity"]) if obs.get("humidity") is not None else None
    except (TypeError, ValueError):
        humidity = None
    rt = obs.get("realtimeFrequency")
    try:
        rt_sec = int(rt) if rt not in (None, "") else 0
    except (TypeError, ValueError):
        rt_sec = 0
    period = rt_sec if rt_sec > 0 else int(period_sec or DEFAULT_PERIOD_SEC)
    return {
        "station_slug": SLUG,
        "station_name": STATION_NAME,
        "provider": PROVIDER,
        "provider_station_id": PROVIDER_ID,
        "observed_at": observed,
        "wind_kt": avg_kt,
        "wind_avg_kt": avg_kt,
        "wind_gust_kt": gust_kt,
        "wind_dir_deg": wind_dir,
        "wind_dir_avg_deg": wind_dir,
        "temp_c": temp_c,
        "humidity_pct": humidity,
        "period_sec": period,
    }


def _wu_get(path: str, extra: Optional[dict] = None) -> dict:
    q = {
        "stationId": PROVIDER_ID,
        "format": "json",
        "units": "e",
        "numericPrecision": "decimal",
        "apiKey": _wu_key(),
    }
    if extra:
        q.update(extra)
    url = path + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _period_from_readings(rows: list[dict]) -> int:
    if len(rows) < 2:
        return DEFAULT_PERIOD_SEC
    last = datetime.fromisoformat(rows[-1]["observed_at"].replace("Z", "+00:00"))
    prev = datetime.fromisoformat(rows[-2]["observed_at"].replace("Z", "+00:00"))
    sec = int((last - prev).total_seconds())
    if 15 <= sec <= 3600:
        return sec
    return DEFAULT_PERIOD_SEC


def fetch_hyc_history(hours: int = 12) -> dict:
    hours = max(1, min(int(hours or 12), 48))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    day = _wu_get(WU_DAY)
    obs_list = list(day.get("observations") or [])
    cur = _wu_get(WU_CURRENT)
    for obs in cur.get("observations") or []:
        oid = _obs_iso(obs)
        if oid and all(_obs_iso(x) != oid for x in obs_list):
            obs_list.append(obs)
    rows: list[dict] = []
    for obs in obs_list:
        row = reading_from_wu_obs(obs)
        if not row:
            continue
        dt = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        if dt >= cutoff:
            rows.append(row)
    rows.sort(key=lambda r: r["observed_at"])
    period = _period_from_readings(rows)
    for row in rows:
        if not row.get("period_sec"):
            row["period_sec"] = period
    return {
        "ok": True,
        "slug": SLUG,
        "count": len(rows),
        "readings": rows,
        "source": STATIONS_URL,
        "provider_station_id": PROVIDER_ID,
        "period_sec": period,
        "units": "kn",
    }


def history_payload(hours: int = 12) -> dict:
    hours = max(1, min(int(hours or 12), 48))
    now = time.time()
    hit = _cache.get("payload")
    if hit and _cache.get("hours") == hours and (now - float(_cache.get("at") or 0)) < _CACHE_SEC:
        return hit
    try:
        payload = fetch_hyc_history(hours)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, KeyError) as exc:
        payload = {"ok": False, "slug": SLUG, "count": 0, "readings": [], "err": str(exc)[:200]}
    _cache["at"] = now
    _cache["hours"] = hours
    _cache["payload"] = payload
    return payload
