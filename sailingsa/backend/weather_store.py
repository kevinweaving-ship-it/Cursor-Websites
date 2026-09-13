"""Generic weather storage: stations, readings, forecasts.

Live api.py imports ingest_wind2speed_payload so the Cape Classic card
response stays unchanged while tableData observations accumulate.
Missing source values stay NULL. Never invent 0 or fake gusts.
Cardinal is never stored as authoritative data.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

KMH_PER_KT = 1.852
W2S_SLUG = "w2s-zeekoevlei"
W2S_PROVIDER = "wind2speed"
W2S_PROVIDER_ID = "35"
W2S_PERIOD_SEC = 180
W2S_TZ = "Africa/Johannesburg"
FORECAST_SQLITE = Path("/var/www/sailingsa/data/forecast_history.sqlite")
WINDGURU_CACHE = Path("/var/www/sailingsa/data/windguru_1309608.json")


def _dsn() -> str:
    for key in ("DB_URL", "DATABASE_URL"):
        val = os.environ.get(key)
        if val:
            return val
    for path in (
        Path("/var/www/sailingsa/api/.env"),
        Path("/etc/sailingsa.env"),
    ):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("DB_URL=") or line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip("'").strip('"')
    raise RuntimeError("DB_URL not set")


def _connect():
    import psycopg2
    import psycopg2.extras

    return psycopg2.connect(_dsn(), cursor_factory=psycopg2.extras.RealDictCursor)


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _nonzero(v: Any) -> Optional[float]:
    """Treat exact 0 as missing (Wind2Speed temp/hum currently arrive as 0)."""
    n = _num(v)
    if n is None or n == 0:
        return None
    return n


def _kmh_to_kt(v: Any) -> Optional[float]:
    n = _num(v)
    if n is None:
        return None
    return round(n / KMH_PER_KT, 2)


def _parse_obs_local(raw: Any):
    if not raw:
        return None
    txt = str(raw).strip().replace("Z", "")
    if "." in txt:
        txt = txt.split(".", 1)[0]
    try:
        from zoneinfo import ZoneInfo

        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(W2S_TZ))
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _hash_payload(station_id: int, observed_at, body: dict) -> str:
    blob = json.dumps(
        {"s": station_id, "t": observed_at.isoformat(), "b": body},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get_station(conn, slug: str) -> Optional[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM weather_stations WHERE slug = %s", (slug,))
        return cur.fetchone()


def ingest_wind2speed_payload(inner: dict, envelope: Optional[dict] = None) -> int:
    """Insert each tableData row at obsTimeLocal. Conflict-safe. Returns inserted+updated count skipped as 0-extra.

    tableData wind speeds are km/h. stats snapshot winds are already knots and
    are not written as extra 40s rows.
    """
    inner = inner or {}
    table = inner.get("tableData") or []
    if not isinstance(table, list) or not table:
        return 0
    station_meta = inner.get("station") or {}
    inserted = 0
    conn = _connect()
    try:
        st = get_station(conn, W2S_SLUG)
        if not st:
            return 0
        sid = int(st["id"])
        with conn.cursor() as cur:
            for row in table:
                if not isinstance(row, dict):
                    continue
                observed = _parse_obs_local(row.get("obsTimeLocal"))
                if observed is None:
                    continue
                avg_kt = _kmh_to_kt(row.get("windspeedAvg"))
                gust_kt = _kmh_to_kt(row.get("windspeedHigh"))
                min_kt = _kmh_to_kt(row.get("windspeedLow"))
                body = {
                    "wind_avg_kt": avg_kt,
                    "wind_gust_kt": gust_kt,
                    "wind_min_kt": min_kt,
                    "wind_dir_avg_deg": _num(row.get("winddirAvg")),
                    "wind_dir_min_deg": _num(row.get("winddirLow")),
                    "wind_dir_max_deg": _num(row.get("winddirHigh")),
                    "temp_c": _nonzero(row.get("tempAvg")),
                    "pressure_hpa": _nonzero(row.get("pressureAvg")),
                    "humidity_pct": _nonzero(row.get("humidityAvg")),
                }
                extras = {
                    "provider_row_id": row.get("id"),
                    "station_id_src": row.get("stationId") or station_meta.get("id"),
                    "code": station_meta.get("cod"),
                }
                raw = {
                    "row": row,
                    "station": {
                        k: station_meta.get(k)
                        for k in ("id", "nam", "cod", "DInterval")
                    },
                    "interval": (envelope or {}).get("interval"),
                }
                payload_hash = _hash_payload(sid, observed, body)
                cur.execute(
                    """
                    INSERT INTO weather_readings (
                        station_id, observed_at, period_sec,
                        wind_kt, wind_avg_kt, wind_gust_kt, wind_min_kt,
                        wind_dir_deg, wind_dir_avg_deg, wind_dir_min_deg, wind_dir_max_deg,
                        temp_c, pressure_hpa, humidity_pct,
                        extras, raw, payload_hash
                    ) VALUES (
                        %(station_id)s, %(observed_at)s, %(period_sec)s,
                        %(wind_kt)s, %(wind_avg_kt)s, %(wind_gust_kt)s, %(wind_min_kt)s,
                        %(wind_dir_deg)s, %(wind_dir_avg_deg)s, %(wind_dir_min_deg)s, %(wind_dir_max_deg)s,
                        %(temp_c)s, %(pressure_hpa)s, %(humidity_pct)s,
                        %(extras)s, %(raw)s, %(payload_hash)s
                    )
                    ON CONFLICT DO NOTHING
                    """,
                    {
                        "station_id": sid,
                        "observed_at": observed,
                        "period_sec": W2S_PERIOD_SEC,
                        "wind_kt": avg_kt,
                        "wind_avg_kt": avg_kt,
                        "wind_gust_kt": gust_kt,
                        "wind_min_kt": min_kt,
                        "wind_dir_deg": _num(row.get("winddirAvg")),
                        "wind_dir_avg_deg": _num(row.get("winddirAvg")),
                        "wind_dir_min_deg": _num(row.get("winddirLow")),
                        "wind_dir_max_deg": _num(row.get("winddirHigh")),
                        "temp_c": body["temp_c"],
                        "pressure_hpa": body["pressure_hpa"],
                        "humidity_pct": body["humidity_pct"],
                        "extras": json.dumps(extras),
                        "raw": json.dumps(raw, default=str),
                        "payload_hash": payload_hash,
                    },
                )
                inserted += cur.rowcount or 0
        conn.commit()
        return inserted
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def latest_reading(slug: str) -> Optional[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.*, s.slug, s.display_name, s.provider, s.provider_station_id,
                       s.latitude AS station_lat, s.longitude AS station_lon,
                       s.timezone, s.native_interval_sec
                FROM weather_readings r
                JOIN weather_stations s ON s.id = r.station_id
                WHERE s.slug = %s AND s.is_active
                ORDER BY r.observed_at DESC
                LIMIT 1
                """,
                (slug,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def history_readings(
    slugs: Iterable[str],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 2000,
) -> list[dict]:
    slug_list = [str(s).strip() for s in slugs if str(s).strip()]
    if not slug_list:
        return []
    conn = _connect()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT r.*, s.slug, s.display_name, s.provider, s.provider_station_id,
                       s.latitude AS station_lat, s.longitude AS station_lon,
                       s.timezone, s.native_interval_sec
                FROM weather_readings r
                JOIN weather_stations s ON s.id = r.station_id
                WHERE s.slug = ANY(%s) AND s.is_active
            """
            args: list[Any] = [slug_list]
            if start is not None:
                sql += " AND r.observed_at >= %s"
                args.append(start)
            if end is not None:
                sql += " AND r.observed_at <= %s"
                args.append(end)
            sql += " ORDER BY s.slug, r.observed_at ASC LIMIT %s"
            args.append(max(1, min(int(limit), 10000)))
            cur.execute(sql, args)
            return list(cur.fetchall() or [])
    finally:
        conn.close()


def _iso(dt) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)


def reading_public(row: dict) -> dict:
    """Canonical API shape. No cardinal field."""
    if not row:
        return {}
    lat = row.get("latitude")
    lon = row.get("longitude")
    if lat is None:
        lat = row.get("station_lat")
    if lon is None:
        lon = row.get("station_lon")
    return {
        "station_slug": row.get("slug"),
        "station_name": row.get("display_name"),
        "provider": row.get("provider"),
        "provider_station_id": row.get("provider_station_id"),
        "observed_at": _iso(row.get("observed_at")),
        "ingested_at": _iso(row.get("ingested_at")),
        "period_sec": row.get("period_sec"),
        "latitude": lat,
        "longitude": lon,
        "wind_kt": row.get("wind_kt"),
        "wind_avg_kt": row.get("wind_avg_kt"),
        "wind_gust_kt": row.get("wind_gust_kt"),
        "wind_min_kt": row.get("wind_min_kt"),
        "wind_dir_deg": row.get("wind_dir_deg"),
        "wind_dir_avg_deg": row.get("wind_dir_avg_deg"),
        "wind_dir_min_deg": row.get("wind_dir_min_deg"),
        "wind_dir_max_deg": row.get("wind_dir_max_deg"),
        "temp_c": row.get("temp_c"),
        "feels_like_c": row.get("feels_like_c"),
        "dewpoint_c": row.get("dewpoint_c"),
        "pressure_hpa": row.get("pressure_hpa"),
        "humidity_pct": row.get("humidity_pct"),
        "rain_rate_mm_h": row.get("rain_rate_mm_h"),
        "rain_mm_period": row.get("rain_mm_period"),
        "rain_mm_24h": row.get("rain_mm_24h"),
        "uv_index": row.get("uv_index"),
        "solar_wm2": row.get("solar_wm2"),
        "battery_pct": row.get("battery_pct"),
        "wave_height_m": row.get("wave_height_m"),
        "wave_period_s": row.get("wave_period_s"),
        "wave_dir_deg": row.get("wave_dir_deg"),
    }


def _windguru_latlon() -> tuple[float, float]:
    if WINDGURU_CACHE.exists():
        try:
            data = json.loads(WINDGURU_CACHE.read_text(encoding="utf-8"))
            lat = float(data["lat"])
            lon = float(data["lon"])
            return lat, lon
        except Exception:
            pass
    # Windguru spot 1309608 — Voelklip/Hermanus area fallback only if cache missing.
    return -34.407, 19.249


def import_windguru_sqlite(sqlite_path: Optional[Path] = None) -> int:
    """Copy original Windguru issued/target snapshots. Never imports /18.52 FVA actuals."""
    path = sqlite_path or FORECAST_SQLITE
    if not path.exists():
        return 0
    lat, lon = _windguru_latlon()
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = src.execute(
            "SELECT issued, model, spot, target, spd, gust, dir, tmp, slp, rain, cloud FROM forecast"
        ).fetchall()
    finally:
        src.close()
    if not rows:
        return 0
    conn = _connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO weather_stations (
                    slug, display_name, provider, provider_station_id, kind,
                    latitude, longitude, timezone, native_interval_sec, is_active, meta
                ) VALUES (
                    'windguru-1309608', 'Windguru 1309608', 'windguru', '1309608',
                    'forecast_point', %s, %s, 'Africa/Johannesburg', 3600, true,
                    '{"spot":"1309608"}'::jsonb
                )
                ON CONFLICT (provider, provider_station_id) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    updated_at = now()
                RETURNING id
                """,
                (lat, lon),
            )
            station_id = cur.fetchone()["id"]
            for issued, model, spot, target, spd, gust, direction, tmp, slp, rain, cloud in rows:
                try:
                    issued_at = datetime.fromtimestamp(int(issued), tz=timezone.utc)
                    target_at = datetime.fromtimestamp(int(target), tz=timezone.utc)
                except Exception:
                    continue
                lead = int((target_at - issued_at).total_seconds())
                cur.execute(
                    """
                    INSERT INTO weather_forecasts (
                        forecast_source, model, station_id, forecast_lat, forecast_lon,
                        issued_at, target_at, lead_seconds,
                        wind_kt, wind_gust_kt, wind_dir_deg, temp_c, pressure_hpa,
                        rain, cloud, extras, raw
                    ) VALUES (
                        'windguru', %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        str(model),
                        station_id,
                        lat,
                        lon,
                        issued_at,
                        target_at,
                        lead,
                        _num(spd),
                        _num(gust),
                        _num(direction),
                        _num(tmp),
                        _num(slp),
                        _num(rain),
                        _num(cloud),
                        json.dumps({"spot": str(spot)}),
                        json.dumps(
                            {
                                "issued": issued,
                                "model": model,
                                "spot": spot,
                                "target": target,
                                "spd": spd,
                                "gust": gust,
                                "dir": direction,
                                "tmp": tmp,
                                "slp": slp,
                                "rain": rain,
                                "cloud": cloud,
                            },
                            default=str,
                        ),
                    ),
                )
                inserted += cur.rowcount or 0
        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_iso_query(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    txt = str(raw).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import atan2, cos, radians, sin, sqrt

    r = 6371.0088
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))


def insert_observation(station_id: int, observed_at: datetime, fields: dict, extras: dict, raw: Any, period_sec: Optional[int] = None) -> int:
    """Conflict-safe append. Returns 1 if inserted, 0 if duplicate timestamp."""
    conn = _connect()
    try:
        payload_hash = _hash_payload(station_id, observed_at, fields)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO weather_readings (
                    station_id, observed_at, period_sec,
                    wind_kt, wind_avg_kt, wind_gust_kt, wind_min_kt,
                    wind_dir_deg, wind_dir_avg_deg, wind_dir_min_deg, wind_dir_max_deg,
                    temp_c, feels_like_c, dewpoint_c, pressure_hpa, humidity_pct,
                    rain_rate_mm_h, rain_mm_period, rain_mm_24h,
                    uv_index, solar_wm2, battery_pct,
                    wave_height_m, wave_period_s, wave_dir_deg,
                    latitude, longitude, extras, raw, payload_hash
                ) VALUES (
                    %(station_id)s, %(observed_at)s, %(period_sec)s,
                    %(wind_kt)s, %(wind_avg_kt)s, %(wind_gust_kt)s, %(wind_min_kt)s,
                    %(wind_dir_deg)s, %(wind_dir_avg_deg)s, %(wind_dir_min_deg)s, %(wind_dir_max_deg)s,
                    %(temp_c)s, %(feels_like_c)s, %(dewpoint_c)s, %(pressure_hpa)s, %(humidity_pct)s,
                    %(rain_rate_mm_h)s, %(rain_mm_period)s, %(rain_mm_24h)s,
                    %(uv_index)s, %(solar_wm2)s, %(battery_pct)s,
                    %(wave_height_m)s, %(wave_period_s)s, %(wave_dir_deg)s,
                    %(latitude)s, %(longitude)s, %(extras)s, %(raw)s, %(payload_hash)s
                )
                ON CONFLICT DO NOTHING
                """,
                {
                    "station_id": station_id,
                    "observed_at": observed_at,
                    "period_sec": period_sec,
                    "wind_kt": fields.get("wind_kt"),
                    "wind_avg_kt": fields.get("wind_avg_kt"),
                    "wind_gust_kt": fields.get("wind_gust_kt"),
                    "wind_min_kt": fields.get("wind_min_kt"),
                    "wind_dir_deg": fields.get("wind_dir_deg"),
                    "wind_dir_avg_deg": fields.get("wind_dir_avg_deg"),
                    "wind_dir_min_deg": fields.get("wind_dir_min_deg"),
                    "wind_dir_max_deg": fields.get("wind_dir_max_deg"),
                    "temp_c": fields.get("temp_c"),
                    "feels_like_c": fields.get("feels_like_c"),
                    "dewpoint_c": fields.get("dewpoint_c"),
                    "pressure_hpa": fields.get("pressure_hpa"),
                    "humidity_pct": fields.get("humidity_pct"),
                    "rain_rate_mm_h": fields.get("rain_rate_mm_h"),
                    "rain_mm_period": fields.get("rain_mm_period"),
                    "rain_mm_24h": fields.get("rain_mm_24h"),
                    "uv_index": fields.get("uv_index"),
                    "solar_wm2": fields.get("solar_wm2"),
                    "battery_pct": fields.get("battery_pct"),
                    "wave_height_m": fields.get("wave_height_m"),
                    "wave_period_s": fields.get("wave_period_s"),
                    "wave_dir_deg": fields.get("wave_dir_deg"),
                    "latitude": fields.get("latitude"),
                    "longitude": fields.get("longitude"),
                    "extras": json.dumps(extras or {}),
                    "raw": json.dumps(raw, default=str) if raw is not None else None,
                    "payload_hash": payload_hash,
                },
            )
            n = cur.rowcount or 0
        conn.commit()
        return n
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def regional_snapshot(
    lat: float,
    lon: float,
    radius_km: Optional[float] = None,
    slugs: Optional[Iterable[str]] = None,
    at: Optional[datetime] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[dict]:
    """Each observation station separately. No averaging, no substitution."""
    when = at or end or datetime.now(timezone.utc)
    slug_list = [str(s).strip() for s in (slugs or []) if str(s).strip()]
    conn = _connect()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT s.id, s.slug, s.display_name, s.provider, s.provider_station_id,
                       s.kind, s.latitude AS station_lat, s.longitude AS station_lon,
                       s.timezone, s.native_interval_sec, s.is_active, s.meta,
                       r.observed_at, r.ingested_at, r.period_sec,
                       r.wind_kt, r.wind_avg_kt, r.wind_gust_kt, r.wind_min_kt,
                       r.wind_dir_deg, r.temp_c, r.dewpoint_c, r.pressure_hpa,
                       r.humidity_pct, r.rain_rate_mm_h, r.rain_mm_24h, r.uv_index,
                       r.latitude, r.longitude
                FROM weather_stations s
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM weather_readings rr
                    WHERE rr.station_id = s.id AND rr.observed_at <= %s
            """
            args: list[Any] = [when]
            if start is not None:
                sql += " AND rr.observed_at >= %s"
                args.append(start)
            sql += """
                    ORDER BY rr.observed_at DESC
                    LIMIT 1
                ) r ON true
                WHERE s.kind = 'observation' AND s.is_active
            """
            if slug_list:
                sql += " AND s.slug = ANY(%s)"
                args.append(slug_list)
            cur.execute(sql, args)
            rows = list(cur.fetchall() or [])
    finally:
        conn.close()
    out = []
    for row in rows:
        slat = float(row["station_lat"])
        slon = float(row["station_lon"])
        dist = round(haversine_km(lat, lon, slat, slon), 3)
        if radius_km is not None and dist > float(radius_km):
            continue
        obs = row.get("observed_at")
        age = None
        if obs is not None:
            if getattr(obs, "tzinfo", None) is None:
                obs_aware = obs.replace(tzinfo=timezone.utc)
            else:
                obs_aware = obs
            age = int((when - obs_aware).total_seconds())
        item = reading_public(row)
        item.update(
            {
                "distance_km": dist,
                "reading_age_sec": age,
                "has_reading": obs is not None,
                "station_latitude": slat,
                "station_longitude": slon,
                "independent": True,
            }
        )
        out.append(item)
    out.sort(key=lambda x: (x.get("distance_km") is None, x.get("distance_km") or 0, x.get("station_slug") or ""))
    return out


def list_stations(
    kind: Optional[str] = None,
    provider: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT s.*, r.observed_at AS last_reading_observed_at,
                       r.ingested_at AS last_reading_ingested_at,
                       r.wind_kt AS last_wind_kt, r.wind_gust_kt AS last_wind_gust_kt
                FROM weather_stations s
                LEFT JOIN LATERAL (
                    SELECT observed_at, ingested_at, wind_kt, wind_gust_kt
                    FROM weather_readings rr
                    WHERE rr.station_id = s.id
                    ORDER BY rr.observed_at DESC
                    LIMIT 1
                ) r ON true
                WHERE 1=1
            """
            args: list[Any] = []
            if active_only:
                sql += " AND s.is_active"
            if kind:
                sql += " AND s.kind = %s"
                args.append(kind)
            if provider:
                sql += " AND s.provider = %s"
                args.append(provider)
            sql += " ORDER BY s.slug"
            cur.execute(sql, args)
            return list(cur.fetchall() or [])
    finally:
        conn.close()


def mark_station_ingest(slug: str, *, observed_at=None, failure_reason: Optional[str] = None) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            if failure_reason:
                cur.execute(
                    """
                    UPDATE weather_stations
                    SET last_failure_at = now(),
                        last_failure_reason = %s,
                        updated_at = now()
                    WHERE slug = %s
                    """,
                    (str(failure_reason)[:300], slug),
                )
            else:
                cur.execute(
                    """
                    UPDATE weather_stations
                    SET last_ingest_at = now(),
                        last_observation_at = COALESCE(%s, last_observation_at),
                        last_failure_at = NULL,
                        last_failure_reason = NULL,
                        updated_at = now()
                    WHERE slug = %s
                    """,
                    (observed_at, slug),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def club_station_snapshot(
    club_code: str,
    at: Optional[datetime] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[dict]:
    """One row per mapped station. Never averaged, never substituted."""
    code = str(club_code or "").strip().upper()
    if not code:
        return []
    when = at or end or datetime.now(timezone.utc)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT s.id, s.slug, s.display_name, s.provider, s.provider_station_id,
                       s.kind, s.latitude AS station_lat, s.longitude AS station_lon,
                       s.timezone, s.native_interval_sec, s.is_active, s.meta,
                       s.last_observation_at AS station_last_observation_at,
                       s.last_ingest_at, s.last_failure_at, s.last_failure_reason,
                       cws.club_code, cws.club_id, cws.role, cws.distance_km,
                       cws.enabled, cws.weight,
                       r.observed_at, r.ingested_at, r.period_sec,
                       r.wind_kt, r.wind_avg_kt, r.wind_gust_kt, r.wind_min_kt,
                       r.wind_dir_deg, r.temp_c, r.dewpoint_c, r.pressure_hpa,
                       r.humidity_pct, r.rain_rate_mm_h, r.rain_mm_24h, r.uv_index,
                       r.wave_height_m, r.wave_period_s, r.wave_dir_deg,
                       r.latitude, r.longitude
                FROM club_weather_stations cws
                JOIN weather_stations s ON s.id = cws.station_id
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM weather_readings rr
                    WHERE rr.station_id = s.id
                      AND rr.observed_at <= %s
            """
            args: list[Any] = [when]
            if start is not None:
                sql += " AND rr.observed_at >= %s"
                args.append(start)
            sql += """
                    ORDER BY rr.observed_at DESC
                    LIMIT 1
                ) r ON true
                WHERE upper(cws.club_code) = %s AND cws.enabled AND s.is_active
                ORDER BY cws.distance_km NULLS LAST, s.slug
            """
            args.append(code)
            cur.execute(sql, args)
            rows = list(cur.fetchall() or [])
    finally:
        conn.close()
    out = []
    for row in rows:
        obs = row.get("observed_at")
        age = None
        if obs is not None:
            obs_aware = obs if getattr(obs, "tzinfo", None) else obs.replace(tzinfo=timezone.utc)
            age = int((when - obs_aware).total_seconds())
        item = reading_public(row)
        item.update(
            {
                "club_code": row.get("club_code"),
                "club_id": row.get("club_id"),
                "role": row.get("role"),
                "distance_km": None if row.get("distance_km") is None else float(row["distance_km"]),
                "weight": row.get("weight"),
                "reading_age_sec": age,
                "has_reading": obs is not None,
                "station_latitude": float(row["station_lat"]),
                "station_longitude": float(row["station_lon"]),
                "independent": True,
                "last_ingest_at": _iso(row.get("last_ingest_at")),
                "last_failure_at": _iso(row.get("last_failure_at")),
                "last_failure_reason": row.get("last_failure_reason"),
            }
        )
        out.append(item)
    return out


def club_station_history(
    club_code: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 5000,
) -> list[dict]:
    snap = club_station_snapshot(club_code)
    slugs = [row["station_slug"] for row in snap if row.get("station_slug")]
    return history_readings(slugs, start=start, end=end, limit=limit)


if __name__ == "__main__":
    assert _kmh_to_kt(1.852) == 1.0
    assert _kmh_to_kt(None) is None
    assert _nonzero(0) is None
    assert _nonzero(12.5) == 12.5
    assert abs((_kmh_to_kt(3.6) or 0) - 1.94) < 0.02
    assert abs(haversine_km(-34.42, 19.24, -34.44, 19.46) - 20.3) < 1.5
    print("ok")
