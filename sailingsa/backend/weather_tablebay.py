"""Independent Table Bay sources. Do not merge provenance in storage.

The public /api/live-wx/table-bay response may still combine values for the
existing card. Stored rows stay FACT METAR, Open-Meteo atmosphere, and
Open-Meteo marine as three stations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sailingsa.backend.weather_store import (
    _num,
    get_station,
    insert_observation,
    mark_station_ingest,
    _connect,
)

FACT_SLUG = "metar-fact"
OM_ATM_SLUG = "open-meteo-table-bay-atm"
OM_MARINE_SLUG = "open-meteo-table-bay-marine"


def _parse_open_meteo_time(raw) -> Optional[datetime]:
    """Open-Meteo current.time is Africa/Johannesburg wall time unless offset is present."""
    if not raw:
        return None
    txt = str(raw).strip()
    try:
        if txt.endswith("Z") or "+" in txt[10:]:
            from sailingsa.backend.weather_store import parse_iso_query
            return parse_iso_query(txt)
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Africa/Johannesburg"))
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _sid(slug: str) -> Optional[int]:
    conn = _connect()
    try:
        st = get_station(conn, slug)
        return int(st["id"]) if st else None
    finally:
        conn.close()


def ingest_fact_metar_row(row: dict) -> int:
    """Store only values FACT actually supplied. Do not copy wind onto gust."""
    if not isinstance(row, dict):
        return 0
    sid = _sid(FACT_SLUG)
    if not sid:
        return 0
    observed = None
    if row.get("obsTime") is not None:
        try:
            observed = datetime.fromtimestamp(float(row["obsTime"]), tz=timezone.utc)
        except Exception:
            observed = None
    if observed is None:
        mark_station_ingest(FACT_SLUG, failure_reason="missing_obsTime")
        return 0
    gust = _num(row.get("wgst")) if "wgst" in row and row.get("wgst") is not None else None
    wdir = None
    if row.get("wdir") is not None and str(row.get("wdir")).isdigit():
        wdir = _num(row.get("wdir"))
    fields = {
        "wind_kt": _num(row.get("wspd")) if row.get("wspd") is not None else None,
        "wind_gust_kt": gust,
        "wind_dir_deg": wdir,
        "temp_c": _num(row.get("temp")) if row.get("temp") is not None else None,
        "dewpoint_c": _num(row.get("dewp")) if row.get("dewp") is not None else None,
        "pressure_hpa": _num(row.get("altim")) if row.get("altim") is not None else None,
        "latitude": _num(row.get("lat")) if row.get("lat") is not None else None,
        "longitude": _num(row.get("lon")) if row.get("lon") is not None else None,
    }
    extras = {
        "provider": "aviationweather_metar",
        "station_id": "FACT",
        "raw_metar": row.get("rawOb") or row.get("raw"),
        "feed": "https://aviationweather.gov/api/data/metar",
        "independent": True,
    }
    n = insert_observation(sid, observed, fields, extras, row, period_sec=1800)
    mark_station_ingest(FACT_SLUG, observed_at=observed)
    return n


def ingest_open_meteo_atmosphere(current: dict, lat: float, lon: float) -> int:
    if not isinstance(current, dict):
        return 0
    sid = _sid(OM_ATM_SLUG)
    if not sid:
        return 0
    observed = None
    txt = current.get("time")
    if txt:
        observed = _parse_open_meteo_time(txt)
    if observed is None:
        mark_station_ingest(OM_ATM_SLUG, failure_reason="missing_time")
        return 0
    fields = {
        "wind_kt": _num(current.get("wind_speed_10m")) if current.get("wind_speed_10m") is not None else None,
        "wind_gust_kt": _num(current.get("wind_gusts_10m")) if current.get("wind_gusts_10m") is not None else None,
        "wind_dir_deg": _num(current.get("wind_direction_10m")) if current.get("wind_direction_10m") is not None else None,
        "temp_c": _num(current.get("temperature_2m")) if current.get("temperature_2m") is not None else None,
        "latitude": lat,
        "longitude": lon,
    }
    extras = {
        "provider": "open_meteo",
        "kind": "atmosphere_current",
        "feed": "https://api.open-meteo.com/v1/forecast",
        "independent": True,
        "model_point": True,
    }
    n = insert_observation(sid, observed, fields, extras, current, period_sec=900)
    mark_station_ingest(OM_ATM_SLUG, observed_at=observed)
    return n


def ingest_open_meteo_marine(current: dict, lat: float, lon: float) -> int:
    if not isinstance(current, dict):
        return 0
    sid = _sid(OM_MARINE_SLUG)
    if not sid:
        return 0
    observed = None
    txt = current.get("time")
    if txt:
        observed = _parse_open_meteo_time(txt)
    if observed is None:
        mark_station_ingest(OM_MARINE_SLUG, failure_reason="missing_time")
        return 0
    fields = {
        "wave_height_m": _num(current.get("wave_height")) if current.get("wave_height") is not None else None,
        "wave_period_s": _num(current.get("wave_period")) if current.get("wave_period") is not None else None,
        "wave_dir_deg": _num(current.get("wave_direction")) if current.get("wave_direction") is not None else None,
        "latitude": lat,
        "longitude": lon,
    }
    extras = {
        "provider": "open_meteo_marine",
        "kind": "marine_current",
        "feed": "https://marine-api.open-meteo.com/v1/marine",
        "independent": True,
        "model_point": True,
    }
    n = insert_observation(sid, observed, fields, extras, current, period_sec=900)
    mark_station_ingest(OM_MARINE_SLUG, observed_at=observed)
    return n
