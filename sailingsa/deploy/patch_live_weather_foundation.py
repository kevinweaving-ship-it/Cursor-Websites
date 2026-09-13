#!/usr/bin/env python3
"""Hook Wind2Speed ingest + generic weather APIs. Marker: WX_FOUNDATION_v1.

Does not change /api/wind2speed/zeekoevlei response body.
Does not touch slot-card JS or CSS.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "WX_FOUNDATION_v1"

OLD = '''        body = {
            "ok": True,
            "source": "wind2speed.africa/widgetPage/35",
            "station": station.get("nam") or "Zeekoevlei",
            "code": station.get("cod"),
'''
NEW = '''        try:  # ''' + MARKER + '''
            from sailingsa.backend.weather_store import ingest_wind2speed_payload
            ingest_wind2speed_payload(inner, payload)
        except Exception:
            pass
        body = {
            "ok": True,
            "source": "wind2speed.africa/widgetPage/35",
            "station": station.get("nam") or "Zeekoevlei",
            "code": station.get("cod"),
'''

ROUTES = r'''

@app.get("/api/weather/stations/{slug}/latest")
def api_weather_station_latest(slug: str):
    """Generic latest observation. Cardinal is not stored; derive from degrees in UI later."""
    try:
        from sailingsa.backend.weather_store import latest_reading, reading_public
        row = latest_reading(slug)
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    if not row:
        return JSONResponse({"ok": False, "err": "no readings"}, status_code=404)
    return JSONResponse({"ok": True, "reading": reading_public(row)}, headers={"Cache-Control": "no-store"})


@app.get("/api/weather/stations/{slug}/history")
def api_weather_station_history(
    slug: str,
    start: str = Query(""),
    end: str = Query(""),
    limit: int = Query(2000, ge=1, le=10000),
):
    try:
        from sailingsa.backend.weather_store import history_readings, parse_iso_query, reading_public
        rows = history_readings(
            [slug],
            start=parse_iso_query(start) if start else None,
            end=parse_iso_query(end) if end else None,
            limit=limit,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    return JSONResponse(
        {"ok": True, "slug": slug, "count": len(rows), "readings": [reading_public(r) for r in rows]},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/weather/readings")
def api_weather_readings(
    slugs: str = Query(""),
    start: str = Query(""),
    end: str = Query(""),
    limit: int = Query(2000, ge=1, le=10000),
):
    names = [s.strip() for s in (slugs or "").split(",") if s.strip()]
    if not names:
        return JSONResponse({"ok": False, "err": "slugs required"}, status_code=400)
    try:
        from sailingsa.backend.weather_store import history_readings, parse_iso_query, reading_public
        rows = history_readings(
            names,
            start=parse_iso_query(start) if start else None,
            end=parse_iso_query(end) if end else None,
            limit=limit,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:200]}, status_code=500)
    return JSONResponse(
        {"ok": True, "count": len(rows), "readings": [reading_public(r) for r in rows]},
        headers={"Cache-Control": "no-store"},
    )
'''


def main() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched", MARKER)
        return
    if OLD not in text:
        raise SystemExit("wind2speed body block not found")
    if 'def api_weather_station_latest' in text:
        raise SystemExit("generic weather routes already present")
    text = text.replace(OLD, NEW, 1)
    needle = '@app.get("/api/wind2speed/zeekoevlei")'
    # insert generic routes after the wind2speed function: before @app.get("/api/stats")
    stats = '\n@app.get("/api/stats")'
    idx = text.find(stats)
    if idx < 0:
        raise SystemExit("api/stats marker not found")
    # only the first stats after wind2speed
    w2s = text.find(needle)
    idx = text.find(stats, w2s if w2s >= 0 else 0)
    if idx < 0:
        raise SystemExit("api/stats after wind2speed not found")
    text = text[:idx] + ROUTES + text[idx:]
    API.write_text(text, encoding="utf-8")
    print("patched", API, MARKER)


if __name__ == "__main__":
    main()
