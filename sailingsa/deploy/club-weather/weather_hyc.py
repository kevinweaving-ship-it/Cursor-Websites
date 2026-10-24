"""HYC venue wind from Weather Underground PWS IOVERS2.

Catalog: GET /api/weather/clubs/HYC/stations (venue slug pws-iovers2).
WU current/history wind is mph (imperial) or km/h (metric). Convert to knots
for the generic weather card — same units as ZVYC / HMYC.

When WU rotates the browser apiKey (dashboard redesign), weather_wu_discover
re-scrapes https://www.wunderground.com/dashboard/pws/IOVERS2 and retries.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import weather_wu_discover as wu_disc

SLUG = "pws-iovers2"
STATION_NAME = "Hermanus Yacht Club IOVERS2"
PROVIDER = "weather_underground"
PROVIDER_ID = "IOVERS2"
STATIONS_URL = "https://sailingsa.co.za/api/weather/clubs/HYC/stations"
# Legacy fallback only — discovery replaces this when it 401s.
WU_WEB_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
MPH_TO_KT = 0.8689762419
KMH_TO_KT = 0.5399568035
DEFAULT_PERIOD_SEC = 60

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


def _first_num(src: dict, *keys: str) -> Optional[float]:
    for k in keys:
        if src.get(k) is None:
            continue
        try:
            return float(src[k])
        except (TypeError, ValueError):
            continue
    return None


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
    env = (os.environ.get("WU_API_KEY") or os.environ.get("WUNDERGROUND_API_KEY") or os.environ.get("WEATHERCOM_API_KEY") or "").strip()
    key, _src = wu_disc.working_api_key(env or None, PROVIDER_ID, force_refresh=False)
    return (key or env or WU_WEB_KEY).strip()


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
        avg_kt = mph_to_kt(_first_num(imperial, "windSpeed", "windspeedAvg", "windSpeedAvg"))
        gust_kt = mph_to_kt(_first_num(imperial, "windGust", "windgustHigh", "windGustHigh", "windspeedHigh"))
        temp_f = _first_num(imperial, "temp", "tempAvg")
        temp_c = round((temp_f - 32.0) * 5.0 / 9.0, 2) if temp_f is not None else None
    elif metric:
        avg_kt = kmh_to_kt(_first_num(metric, "windSpeed", "windspeedAvg", "windSpeedAvg"))
        gust_kt = kmh_to_kt(_first_num(metric, "windGust", "windgustHigh", "windGustHigh", "windspeedHigh"))
        temp_c = _first_num(metric, "temp", "tempAvg")
    else:
        return None
    wind_dir = _first_num(obs, "winddir", "winddirAvg")
    humidity = _first_num(obs, "humidity", "humidityAvg")
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
    env = (os.environ.get("WU_API_KEY") or os.environ.get("WUNDERGROUND_API_KEY") or os.environ.get("WEATHERCOM_API_KEY") or "").strip()
    raw = wu_disc.fetch_with_autofix(PROVIDER_ID, env_key=env or None, hours=hours, units="m")
    if not raw.get("ok"):
        raise RuntimeError(str(raw.get("err") or "wu_fetch_failed")[:200])
    rows: list[dict] = []
    for obs in raw.get("observations") or []:
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
        "key_source": raw.get("key_source"),
    }


def history_payload(hours: int = 12) -> dict:
    hours = max(1, min(int(hours or 12), 48))
    now = time.time()
    hit = _cache.get("payload")
    if hit and _cache.get("hours") == hours and (now - float(_cache.get("at") or 0)) < _CACHE_SEC:
        return hit
    try:
        payload = fetch_hyc_history(hours)
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "slug": SLUG, "count": 0, "readings": [], "err": str(exc)[:200]}
    _cache["at"] = now
    _cache["hours"] = hours
    _cache["payload"] = payload
    return payload
