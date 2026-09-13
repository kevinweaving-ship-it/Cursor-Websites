#!/usr/bin/env python3
"""Add regional/club weather APIs + independent Table Bay ingest. Marker: WX_PWS_v1.

Does not change /api/live-wx/table-bay JSON shape.
Does not enable WU polling without an API key.
Does not touch weather-card UI.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "WX_PWS_v1"

FACT_OLD = '''            source_bits.append("fact-metar")
    except Exception:
        pass
'''
FACT_NEW = '''            source_bits.append("fact-metar")
            try:  # ''' + MARKER + '''
                from sailingsa.backend.weather_tablebay import ingest_fact_metar_row
                ingest_fact_metar_row(row)
            except Exception:
                pass
    except Exception:
        pass
'''

OM_OLD = '''        source_bits.append("open-meteo")
    except Exception:
        pass
'''
OM_NEW = '''        source_bits.append("open-meteo")
        try:  # ''' + MARKER + '''
            from sailingsa.backend.weather_tablebay import ingest_open_meteo_atmosphere
            ingest_open_meteo_atmosphere(cur, _LIVE_WX_LAT, _LIVE_WX_LON)
        except Exception:
            pass
    except Exception:
        pass
'''

MAR_OLD = '''        source_bits.append("open-meteo-marine")
    except Exception:
        pass
'''
MAR_NEW = '''        source_bits.append("open-meteo-marine")
        try:  # ''' + MARKER + '''
            from sailingsa.backend.weather_tablebay import ingest_open_meteo_marine
            ingest_open_meteo_marine(cur, _LIVE_WX_LAT, _LIVE_WX_LON)
        except Exception:
            pass
    except Exception:
        pass
'''

ROUTES = r'''

@app.get("/api/weather/stations")
def api_weather_stations(kind: str = Query(""), provider: str = Query("")):
    try:
        from sailingsa.backend.weather_store import list_stations, _iso
        rows = list_stations(kind=kind or None, provider=provider or None, active_only=True)
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    stations = []
    for row in rows:
        stations.append({
            "slug": row.get("slug"),
            "name": row.get("display_name"),
            "provider": row.get("provider"),
            "provider_station_id": row.get("provider_station_id"),
            "kind": row.get("kind"),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "native_interval_sec": row.get("native_interval_sec"),
            "last_observation_at": _iso(row.get("last_observation_at")),
            "independent": True,
        })
    return JSONResponse({"ok": True, "count": len(stations), "stations": stations, "averaged": False}, headers={"Cache-Control": "no-store"})


@app.get("/api/weather/region")
def api_weather_region(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(None),
    slugs: str = Query(""),
    at: str = Query(""),
    start: str = Query(""),
    end: str = Query(""),
):
    """Independent stations near a point. No average, no corrected wind."""
    try:
        from sailingsa.backend.weather_store import parse_iso_query, regional_snapshot
        names = [s.strip() for s in (slugs or "").split(",") if s.strip()]
        rows = regional_snapshot(
            lat,
            lon,
            radius_km=radius_km,
            slugs=names or None,
            at=parse_iso_query(at) if at else None,
            start=parse_iso_query(start) if start else None,
            end=parse_iso_query(end) if end else None,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    return JSONResponse(
        {"ok": True, "averaged": False, "corrected_wind": False, "count": len(rows), "stations": rows},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/weather/clubs/{club_code}/stations")
def api_weather_club_stations(club_code: str, at: str = Query(""), start: str = Query(""), end: str = Query("")):
    try:
        from sailingsa.backend.weather_store import club_station_snapshot, parse_iso_query
        rows = club_station_snapshot(
            club_code,
            at=parse_iso_query(at) if at else None,
            start=parse_iso_query(start) if start else None,
            end=parse_iso_query(end) if end else None,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    return JSONResponse(
        {
            "ok": True,
            "club_code": club_code.upper(),
            "averaged": False,
            "corrected_wind": False,
            "count": len(rows),
            "stations": rows,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/weather/clubs/{club_code}/history")
def api_weather_club_history(
    club_code: str,
    start: str = Query(""),
    end: str = Query(""),
    limit: int = Query(5000, ge=1, le=10000),
):
    try:
        from sailingsa.backend.weather_store import club_station_history, parse_iso_query, reading_public
        rows = club_station_history(
            club_code,
            start=parse_iso_query(start) if start else None,
            end=parse_iso_query(end) if end else None,
            limit=limit,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    grouped = {}
    for row in rows:
        slug = row.get("slug")
        grouped.setdefault(slug, []).append(reading_public(row))
    return JSONResponse(
        {"ok": True, "club_code": club_code.upper(), "averaged": False, "count": len(rows), "by_station": grouped},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/weather/pws/status")
def api_weather_pws_status():
    try:
        from sailingsa.backend.weather_pws import credential_status, list_pws_stations
        from sailingsa.backend.weather_store import latest_reading, _iso
        cred = credential_status()
        out = []
        for st in list_pws_stations():
            latest = latest_reading(st["slug"])
            received = []
            if latest:
                for key in ("wind_kt", "wind_gust_kt", "wind_dir_deg", "temp_c", "dewpoint_c", "humidity_pct", "pressure_hpa", "rain_rate_mm_h", "rain_mm_24h", "uv_index"):
                    if latest.get(key) is not None:
                        received.append(key)
            out.append({
                "registered": True,
                "slug": st["slug"],
                "provider": st["provider"],
                "pws_id": st["provider_station_id"],
                "latitude": st["latitude"],
                "longitude": st["longitude"],
                "feed": "https://api.weather.com/v2/pws/observations/current",
                "online": None if not cred["key_present"] else bool(latest),
                "latest_source_timestamp": _iso(latest["observed_at"]) if latest else None,
                "fields_received": received,
                "ingest_reason": None if cred["key_present"] else "no_api_key",
            })
        return JSONResponse({"ok": True, "credential": cred, "stations": out}, headers={"Cache-Control": "no-store"})
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)


@app.post("/api/weather/pws/ingest")
def api_weather_pws_ingest(force: int = Query(0, ge=0, le=1)):
    from sailingsa.backend.weather_pws import credential_status, ingest_pws_network
    cred = credential_status()
    if not cred["key_present"]:
        return JSONResponse(
            {"ok": False, "poll_enabled": False, "reason": "no_api_key", "credential": cred},
            status_code=503,
        )
    try:
        result = ingest_pws_network(force=bool(force))
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})
'''


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched", MARKER)
        return
    if "WX_FOUNDATION_v1" not in text:
        raise SystemExit("foundation marker missing")
    if FACT_OLD not in text:
        raise SystemExit("FACT ingest hook site not found")
    if OM_OLD not in text:
        raise SystemExit("open-meteo ingest hook site not found")
    if MAR_OLD not in text:
        raise SystemExit("open-meteo marine ingest hook site not found")
    text = text.replace(FACT_OLD, FACT_NEW, 1)
    text = text.replace(OM_OLD, OM_NEW, 1)
    text = text.replace(MAR_OLD, MAR_NEW, 1)
    stats = '\n@app.get("/api/stats")'
    w2s = text.find('@app.get("/api/wind2speed/zeekoevlei")')
    idx = text.find(stats, w2s if w2s >= 0 else 0)
    if idx < 0:
        raise SystemExit("api/stats after wind2speed not found")
    text = text[:idx] + ROUTES + text[idx:]
    API.write_text(text, encoding="utf-8")
    print("patched", API, MARKER)


if __name__ == "__main__":
    main()
