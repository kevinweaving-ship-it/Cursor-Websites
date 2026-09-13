#!/usr/bin/env python3
"""Apply PWS Overberg seed + club_weather_stations + full network catalog."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/sailingsa")
HERE = Path(__file__).resolve().parents[1]
if not ROOT.exists():
    ROOT = Path(__file__).resolve().parents[2]

SQL_FILES = [
    HERE / "backend/sql/002_weather_pws_overberg.sql",
    HERE / "backend/sql/003_club_weather_stations.sql",
]


def _run_sql(conn, path: Path) -> None:
    if not path.exists():
        print("missing", path)
        return
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        buf = []
        for line in sql.splitlines():
            buf.append(line)
            joined = "\n".join(buf).strip()
            if joined.endswith(";"):
                cur.execute(joined)
                buf = []
        leftover = "\n".join(buf).strip()
        if leftover:
            cur.execute(leftover)


def _upsert_catalog(conn) -> None:
    sys.path.insert(0, str(ROOT))
    from sailingsa.backend.weather_network_catalog import CLUBS, LINKS, STATIONS
    from sailingsa.backend.weather_store import haversine_km

    club_by_code = {c["code"]: c for c in CLUBS}
    with conn.cursor() as cur:
        for st in STATIONS:
            meta = st.get("meta") or {}
            cur.execute(
                """
                INSERT INTO weather_stations (
                    slug, display_name, provider, provider_station_id, kind,
                    latitude, longitude, timezone, native_interval_sec, is_active, meta
                ) VALUES (
                    %(slug)s, %(display_name)s, %(provider)s, %(provider_station_id)s, %(kind)s,
                    %(lat)s, %(lon)s, 'Africa/Johannesburg', %(interval)s, true, %(meta)s
                )
                ON CONFLICT (provider, provider_station_id) DO UPDATE SET
                    slug = EXCLUDED.slug,
                    display_name = EXCLUDED.display_name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    native_interval_sec = EXCLUDED.native_interval_sec,
                    is_active = true,
                    meta = weather_stations.meta || EXCLUDED.meta,
                    updated_at = now()
                """,
                {
                    "slug": st["slug"],
                    "display_name": st["display_name"],
                    "provider": st["provider"],
                    "provider_station_id": st["provider_station_id"],
                    "kind": st["kind"],
                    "lat": st["lat"],
                    "lon": st["lon"],
                    "interval": st.get("native_interval_sec"),
                    "meta": json.dumps(meta),
                },
            )
        cur.execute("SELECT id, slug, latitude, longitude FROM weather_stations")
        by_slug = {row["slug"]: row for row in cur.fetchall()}
        for club_code, slug, role in LINKS:
            strow = by_slug.get(slug)
            if not strow:
                print("missing station for link", club_code, slug)
                continue
            club = club_by_code[club_code]
            dist = round(
                haversine_km(club["lat"], club["lon"], float(strow["latitude"]), float(strow["longitude"])),
                3,
            )
            cur.execute(
                """
                INSERT INTO club_weather_stations (
                    club_code, club_id, station_id, distance_km, role, enabled, weight, meta
                ) VALUES (
                    %(club_code)s, %(club_id)s, %(station_id)s, %(distance_km)s, %(role)s,
                    true, NULL, %(meta)s
                )
                ON CONFLICT (club_code, station_id) DO UPDATE SET
                    club_id = EXCLUDED.club_id,
                    distance_km = EXCLUDED.distance_km,
                    role = EXCLUDED.role,
                    enabled = true,
                    meta = club_weather_stations.meta || EXCLUDED.meta,
                    updated_at = now()
                """,
                {
                    "club_code": club_code,
                    "club_id": club.get("club_id"),
                    "station_id": int(strow["id"]),
                    "distance_km": dist,
                    "role": role,
                    "meta": json.dumps({"independent": True, "learned_weight": False}),
                },
            )


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from sailingsa.backend.weather_store import _connect

    conn = _connect()
    try:
        for path in SQL_FILES:
            try:
                _run_sql(conn, path)
                print("sql", path.name)
            except Exception as e:
                conn.rollback()
                print("sql_skip", path.name, type(e).__name__, str(e)[:120])
        _upsert_catalog(conn)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM weather_stations")
            print("stations", cur.fetchone()["n"])
            cur.execute("SELECT club_code, count(*) AS n FROM club_weather_stations GROUP BY 1 ORDER BY 1")
            for row in cur.fetchall():
                print("club", row["club_code"], row["n"])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
