"""Weather Underground / Weather Company PWS adapter.

One provider. Station IDs live in weather_stations, not in fetch code.
Does not scrape HTML dashboards. Polling stays off until an API key exists.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sailingsa.backend.weather_store import (
    _connect,
    _kmh_to_kt,
    _num,
    insert_observation,
    latest_reading,
    mark_station_ingest,
)

PWS_CURRENT_URL = "https://api.weather.com/v2/pws/observations/current"
PWS_MIN_POLL_SEC = 300
API_KEY_ENV_NAMES = ("WUNDERGROUND_API_KEY", "WEATHERCOM_API_KEY", "WU_API_KEY")
PROVIDER = "weather_underground"


def _env_files() -> list[Path]:
    return [
        Path("/var/www/sailingsa/api/.env"),
        Path("/etc/sailingsa.env"),
        Path("/etc/sailingsa/results_fix.env"),
        Path("/etc/sailingsa/mm-fb-app.env"),
        Path("/etc/sailingsa-olarm.env"),
        Path("/etc/sailingsa-tuya.env"),
        Path("/etc/arial-whatsapp-poc.env"),
    ]


def wu_api_key() -> tuple[Optional[str], Optional[str]]:
    """Return (key, env_name). Never logs the value."""
    for name in API_KEY_ENV_NAMES:
        val = os.environ.get(name)
        if val and str(val).strip():
            return str(val).strip(), name
    for path in _env_files():
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            left, right = line.split("=", 1)
            if left.strip() in API_KEY_ENV_NAMES and right.strip().strip("'").strip('"'):
                return right.strip().strip("'").strip('"'), left.strip()
    return None, None


def credential_status() -> dict[str, Any]:
    key, name = wu_api_key()
    return {
        "poll_enabled": bool(key),
        "key_present": bool(key),
        "key_env_name": name,
        "required_env_names": list(API_KEY_ENV_NAMES),
        "feed": PWS_CURRENT_URL,
        "units": "m",
        "configure": (
            "Set one of WUNDERGROUND_API_KEY, WEATHERCOM_API_KEY, or WU_API_KEY "
            "on sailingsa-api (systemd Environment= or /var/www/sailingsa/api/.env). "
            "Key type: Weather Company / Weather Underground API key with "
            "PWS Observations Current Conditions (v2pwsObsCur)."
        ),
        "html_scrape": False,
    }


def _parse_obs_utc(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    txt = str(raw).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def normalize_pws_observation(obs: dict) -> dict[str, Any]:
    """Canonical units. Missing keys stay None. Never copy speed onto gust."""
    metric = obs.get("metric") if isinstance(obs.get("metric"), dict) else {}
    observed = _parse_obs_utc(obs.get("obsTimeUtc"))
    if observed is None and obs.get("epoch") is not None:
        try:
            observed = datetime.fromtimestamp(int(obs["epoch"]), tz=timezone.utc)
        except Exception:
            observed = None
    wind_kt = _kmh_to_kt(metric["windSpeed"]) if "windSpeed" in metric else None
    gust_kt = _kmh_to_kt(metric["windGust"]) if "windGust" in metric else None
    extras = {
        "network": "weather_company_pws",
        "pws_id": obs.get("stationID"),
        "provider": PROVIDER,
        "feed": PWS_CURRENT_URL,
        "units_requested": "m",
        "qc_status": obs.get("qcStatus"),
        "software_type": obs.get("softwareType"),
        "neighborhood": obs.get("neighborhood"),
        "country": obs.get("country"),
        "realtime_frequency": obs.get("realtimeFrequency"),
        "solar_radiation_wm2": _num(obs.get("solarRadiation")),
        "elev_m": _num(metric.get("elev")) if "elev" in metric else None,
        "heat_index_c": _num(metric.get("heatIndex")) if "heatIndex" in metric else None,
        "wind_chill_c": _num(metric.get("windChill")) if "windChill" in metric else None,
        "obs_time_local": obs.get("obsTimeLocal"),
    }
    fields = {
        "wind_kt": wind_kt,
        "wind_avg_kt": wind_kt,
        "wind_gust_kt": gust_kt,
        "wind_dir_deg": _num(obs.get("winddir")) if "winddir" in obs else None,
        "wind_dir_avg_deg": _num(obs.get("winddir")) if "winddir" in obs else None,
        "temp_c": _num(metric.get("temp")) if "temp" in metric else None,
        "feels_like_c": _num(metric.get("heatIndex")) if "heatIndex" in metric else None,
        "dewpoint_c": _num(metric.get("dewpt")) if "dewpt" in metric else None,
        "pressure_hpa": _num(metric.get("pressure")) if "pressure" in metric else None,
        "humidity_pct": _num(obs.get("humidity")) if "humidity" in obs else None,
        "rain_rate_mm_h": _num(metric.get("precipRate")) if "precipRate" in metric else None,
        "rain_mm_24h": _num(metric.get("precipTotal")) if "precipTotal" in metric else None,
        "uv_index": _num(obs.get("uv")) if "uv" in obs else None,
        "solar_wm2": _num(obs.get("solarRadiation")) if "solarRadiation" in obs else None,
        "latitude": _num(obs.get("lat")) if "lat" in obs else None,
        "longitude": _num(obs.get("lon")) if "lon" in obs else None,
    }
    received = [k for k, v in fields.items() if v is not None]
    return {
        "observed_at": observed,
        "fields": fields,
        "extras": extras,
        "received_fields": received,
        "pws_id": obs.get("stationID"),
    }


def fetch_pws_current(pws_id: str, api_key: str) -> dict[str, Any]:
    params = urlencode(
        {
            "stationId": pws_id,
            "format": "json",
            "units": "m",
            "numericPrecision": "decimal",
            "apiKey": api_key,
        }
    )
    req = Request(
        f"{PWS_CURRENT_URL}?{params}",
        headers={"Accept": "application/json", "User-Agent": "SailingSA-weather/1"},
    )
    with urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    return body if isinstance(body, dict) else {}


def _too_soon(slug: str, min_sec: int) -> bool:
    row = latest_reading(slug)
    if not row:
        return False
    ingested = row.get("ingested_at")
    if ingested is None:
        return False
    if getattr(ingested, "tzinfo", None) is None:
        ingested = ingested.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ingested).total_seconds()
    return age < max(60, int(min_sec))


def list_pws_stations() -> list[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM weather_stations
                WHERE provider = %s AND kind = 'observation'
                ORDER BY slug
                """,
                (PROVIDER,),
            )
            return list(cur.fetchall() or [])
    finally:
        conn.close()


def ingest_pws_network(force: bool = False) -> dict[str, Any]:
    """Fetch current observation for every registered WU PWS. No substitution across stations."""
    cred = credential_status()
    if not cred["key_present"]:
        return {
            "ok": False,
            "poll_enabled": False,
            "reason": "no_api_key",
            "credential": cred,
            "stations": [],
        }
    key, key_name = wu_api_key()
    results = []
    inserted_total = 0
    for st in list_pws_stations():
        slug = st["slug"]
        pws_id = st["provider_station_id"]
        interval = int(st.get("native_interval_sec") or PWS_MIN_POLL_SEC)
        item = {
            "slug": slug,
            "pws_id": pws_id,
            "inserted": 0,
            "skipped": None,
        }
        if not st.get("is_active"):
            item["skipped"] = "inactive"
            results.append(item)
            continue
        if not force and _too_soon(slug, interval):
            item["skipped"] = "min_interval"
            results.append(item)
            continue
        try:
            payload = fetch_pws_current(str(pws_id), key or "")
        except Exception as e:
            reason = str(e)[:200]
            mark_station_ingest(slug, failure_reason=reason)
            item["skipped"] = "fetch_error"
            item["error"] = reason
            results.append(item)
            continue
        obs_list = payload.get("observations") if isinstance(payload, dict) else None
        if not obs_list:
            mark_station_ingest(slug, failure_reason="offline_or_expired")
            item["skipped"] = "offline_or_expired"
            results.append(item)
            continue
        obs = obs_list[0] if isinstance(obs_list[0], dict) else None
        if not obs:
            item["skipped"] = "empty_observation"
            results.append(item)
            continue
        norm = normalize_pws_observation(obs)
        if norm["observed_at"] is None:
            mark_station_ingest(slug, failure_reason="missing_observed_at")
            item["skipped"] = "missing_observed_at"
            results.append(item)
            continue
        extras = dict(norm["extras"])
        extras["api_key_env"] = key_name
        n = insert_observation(
            int(st["id"]),
            norm["observed_at"],
            norm["fields"],
            extras,
            payload,
            period_sec=interval,
        )
        mark_station_ingest(slug, observed_at=norm["observed_at"])
        item["inserted"] = n
        item["observed_at"] = norm["observed_at"].isoformat()
        item["received_fields"] = norm["received_fields"]
        inserted_total += n
        results.append(item)
    return {
        "ok": True,
        "poll_enabled": True,
        "inserted": inserted_total,
        "credential": {"key_env_name": key_name, "key_present": True},
        "stations": results,
    }


SAMPLE_OBS = {
    "stationID": "IHERMA37",
    "obsTimeUtc": "2026-09-13T15:00:00Z",
    "obsTimeLocal": "2026-09-13 17:00:00",
    "neighborhood": "Hermanus",
    "softwareType": "EasyWeather",
    "country": "ZA",
    "solarRadiation": 120.5,
    "lon": 19.24,
    "lat": -34.42,
    "uv": 3.2,
    "winddir": 315,
    "humidity": 68,
    "qcStatus": 1,
    "metric": {
        "temp": 18.4,
        "heatIndex": 18.4,
        "dewpt": 12.1,
        "windChill": 16.0,
        "windSpeed": 18.52,
        "windGust": 27.78,
        "pressure": 1016.4,
        "precipRate": 0.0,
        "precipTotal": 1.2,
        "elev": 12,
    },
}


if __name__ == "__main__":
    norm = normalize_pws_observation(SAMPLE_OBS)
    assert norm["fields"]["wind_kt"] == 10.0
    assert abs((norm["fields"]["wind_gust_kt"] or 0) - 15.0) < 0.02
    assert norm["fields"]["temp_c"] == 18.4
    assert norm["fields"]["dewpoint_c"] == 12.1
    assert norm["fields"]["pressure_hpa"] == 1016.4
    assert norm["fields"]["humidity_pct"] == 68
    assert norm["fields"]["rain_rate_mm_h"] == 0.0
    assert norm["fields"]["rain_mm_24h"] == 1.2
    assert norm["fields"]["uv_index"] == 3.2
    assert norm["fields"]["wind_dir_deg"] == 315
    missing_gust = json.loads(json.dumps(SAMPLE_OBS))
    del missing_gust["metric"]["windGust"]
    ng = normalize_pws_observation(missing_gust)
    assert ng["fields"]["wind_gust_kt"] is None
    assert ng["fields"]["wind_kt"] == 10.0
    cred = credential_status()
    assert cred["html_scrape"] is False
    print("ok", "key_present", cred["key_present"], "env", cred["key_env_name"])
