#!/usr/bin/env python3
"""Club weather ingest on the SailingSA box (not Tuya / not aerialnet).

- UKZN Agromet Midmar → HMYC venue (no API key)
- Wind2Speed Zeekoevlei → ZVYC venue (pull public API)
- Weather Underground PWS → all catalog clubs when WU_API_KEY is set
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOTS = ["/var/www/sailingsa/api", "/var/www/sailingsa"]
for r in ROOTS:
    if r not in sys.path:
        sys.path.insert(0, r)

os.environ.setdefault("PYTHONPATH", ":".join(ROOTS))


def _log(msg: str) -> None:
    print(msg, flush=True)


def ensure_agromet_station(conn) -> int:
    import json as _json
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO weather_stations (
                slug, display_name, provider, provider_station_id, kind,
                latitude, longitude, timezone, native_interval_sec, is_active, meta
            ) VALUES (
                'agromet-midmar', 'Henley Midmar Agromet', 'ukzn_agromet', 'Midmar.Five',
                'observation', -29.494, 30.194, 'Africa/Johannesburg', 300, true,
                %s::jsonb
            )
            ON CONFLICT (provider, provider_station_id) DO UPDATE SET
                slug = EXCLUDED.slug,
                display_name = EXCLUDED.display_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                is_active = true,
                updated_at = now()
            RETURNING id
            """,
            (
                _json.dumps(
                    {
                        "feed": "https://agromet.ukzn.ac.za/midmar/",
                        "independent": True,
                        "venue": "hmyc",
                        "cam_still": "https://hmyccam1.nwsza.net/latest.jpg",
                    }
                ),
            ),
        )
        station_id = int(cur.fetchone()["id"])
        cur.execute(
            """
            INSERT INTO club_weather_stations (club_code, club_id, station_id, distance_km, role, enabled, weight, meta)
            VALUES ('HMYC', 98, %s, 0, 'venue', true, 1.0, '{"source":"ukzn_agromet"}'::jsonb)
            ON CONFLICT (club_code, station_id) DO UPDATE SET
                role = 'venue',
                enabled = true,
                updated_at = now()
            """,
            (station_id,),
        )
    conn.commit()
    return station_id


def ingest_agromet() -> dict:
    import weather_agromet as ag
    from sailingsa.backend.weather_store import _connect, insert_observation, mark_station_ingest

    payload = ag.fetch_agromet_five(hours=6)
    if not payload.get("ok"):
        return {"ok": False, "source": "agromet", "err": payload.get("err")}
    conn = _connect()
    try:
        station_id = ensure_agromet_station(conn)
        n = 0
        for row in payload.get("readings") or []:
            obs = row.get("observed_at")
            if not obs:
                continue
            if isinstance(obs, str):
                txt = obs.replace("Z", "+00:00")
                try:
                    observed = datetime.fromisoformat(txt)
                except ValueError:
                    continue
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
            else:
                observed = obs
            fields = {
                "wind_kt": row.get("wind_kt"),
                "wind_avg_kt": row.get("wind_avg_kt"),
                "wind_gust_kt": row.get("wind_gust_kt"),
                "wind_dir_deg": row.get("wind_dir_deg"),
                "wind_dir_avg_deg": row.get("wind_dir_avg_deg"),
                "temp_c": row.get("temp_c"),
                "humidity_pct": row.get("humidity_pct"),
                "latitude": -29.494,
                "longitude": 30.194,
            }
            n += insert_observation(
                station_id,
                observed,
                fields,
                {"provider": "ukzn_agromet", "source": "club_weather_ingest"},
                row,
                period_sec=int(row.get("period_sec") or 300),
            )
        try:
            mark_station_ingest(station_id)
        except Exception:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE weather_stations SET last_ingest_at = now(), last_observation_at = coalesce("
                    "(SELECT max(observed_at) FROM weather_readings WHERE station_id = %s), last_observation_at), "
                    "updated_at = now() WHERE id = %s",
                    (station_id, station_id),
                )
                conn.commit()
        return {"ok": True, "source": "agromet", "inserted": n, "readings": payload.get("count")}
    finally:
        conn.close()


def ingest_wind2speed() -> dict:
    try:
        req = urllib.request.Request(
            "https://sailingsa.co.za/api/wind2speed/zeekoevlei",
            headers={"User-Agent": "SailingSA-club-weather/1.0"},
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace") or "{}")
        return {"ok": bool(body.get("ok", True)), "source": "wind2speed", "wind_kt": body.get("wind_kt") or (body.get("data") or {}).get("wind_kt")}
    except Exception as e:
        return {"ok": False, "source": "wind2speed", "err": str(e)[:200]}



def ingest_hyc_iovers2() -> dict:
    """HYC venue WU PWS via dashboard autofix → weather_store."""
    import sys
    from datetime import datetime, timezone
    sys.path.insert(0, "/var/www/sailingsa/api")
    import weather_hyc as hyc
    from sailingsa.backend.weather_store import _connect, get_station, insert_observation, mark_station_ingest
    payload = hyc.fetch_hyc_history(hours=6)
    if not payload.get("ok"):
        return {"ok": False, "source": "hyc", "err": payload.get("err")}
    conn = _connect()
    try:
        st = get_station(conn, "pws-iovers2")
        if not st:
            return {"ok": False, "source": "hyc", "err": "station_missing"}
        station_id = int(st["id"])
        n = 0
        for row in payload.get("readings") or []:
            obs = row.get("observed_at")
            if not obs:
                continue
            if isinstance(obs, str):
                txt = obs.replace("Z", "+00:00")
                try:
                    observed = datetime.fromisoformat(txt)
                except ValueError:
                    continue
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
            else:
                observed = obs
            fields = {
                "wind_kt": row.get("wind_kt"),
                "wind_avg_kt": row.get("wind_avg_kt"),
                "wind_gust_kt": row.get("wind_gust_kt"),
                "wind_dir_deg": row.get("wind_dir_deg"),
                "wind_dir_avg_deg": row.get("wind_dir_avg_deg"),
                "temp_c": row.get("temp_c"),
                "humidity_pct": row.get("humidity_pct"),
                "latitude": -34.409,
                "longitude": 19.349,
            }
            n += insert_observation(station_id, observed, fields, {"provider": "weather_underground", "source": "hyc_autofix", "key_source": payload.get("key_source")}, row, period_sec=int(row.get("period_sec") or 60))
        try:
            mark_station_ingest("pws-iovers2")
        except Exception:
            pass
        return {"ok": True, "source": "hyc", "inserted": n, "readings": payload.get("count"), "key_source": payload.get("key_source")}
    finally:
        conn.close()


def ingest_pws() -> dict:
    try:
        from sailingsa.backend import weather_pws
    except Exception as e:
        return {"ok": False, "source": "pws", "err": f"import:{e}"}
    st = weather_pws.credential_status()
    if not st.get("poll_enabled"):
        return {"ok": False, "source": "pws", "err": "no_api_key", "credential": st}
    try:
        out = weather_pws.ingest_pws_network(force=True)
        return {"ok": True, "source": "pws", "result": out}
    except Exception as e:
        return {"ok": False, "source": "pws", "err": str(e)[:200]}


def main() -> int:
    results = []
    for fn in (ingest_agromet, ingest_hyc_iovers2, ingest_wind2speed, ingest_pws):
        try:
            results.append(fn())
        except Exception as e:
            results.append({"ok": False, "source": getattr(fn, "__name__", "?"), "err": str(e)[:200]})
    print(json.dumps({"ok": any(r.get("ok") for r in results), "results": results}, default=str))
    # exit 0 if at least one non-pws source worked, or pws worked
    good = [r for r in results if r.get("ok") and r.get("source") != "pws"]
    pws = next((r for r in results if r.get("source") == "pws"), {})
    if good or pws.get("ok"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
