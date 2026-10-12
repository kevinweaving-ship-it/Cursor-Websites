#!/opt/tuya-sharing/venv/bin/python
"""Home read API (analytics), separate from the collector.

The collector (worker.py / tuya-sharing.service) only records: MQTT -> home_events.sqlite + home_snapshot.json.
This process reads those files and serves the panel's /home, /home/history and derived stats. It can be changed
and restarted at will without touching data collection.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker import Worker, _MAIN_SW  # noqa: E402  (static analytics helpers + switch regex; no Worker instance is created)

STATE = Path(os.getenv("TUYA_SHARING_STATE") or "/opt/tuya-sharing/state")
DB = STATE / "home_events.sqlite"
SNAP = STATE / "home_snapshot.json"
HOST = os.getenv("HOME_API_HOST") or "127.0.0.1"
PORT = int(os.getenv("HOME_API_PORT") or 8008)
TOKEN = (os.getenv("TUYA_SHARING_CTRL_TOKEN") or "").strip()
log = logging.getLogger("home-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s home-api %(message)s")


def db():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    return con


def snapshot() -> dict[str, Any]:
    try:
        return json.loads(SNAP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"at": 0, "devices": []}


def usage_for(con, o: dict) -> dict[str, Any]:
    now = time.time()
    lt = time.gmtime(now + 7200)
    day0 = now - (lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
    month0 = day0 - (lt.tm_mday - 1) * 86400
    out: dict[str, Any] = {"day0": day0, "month0": month0}
    if "add_ele" in o["status"]:
        u = (o.get("units") or {}).get("add_ele") or {}
        scale = 10.0 ** int(u.get("scale", 3) or 0)
        for key, since in (("todayKwh", day0), ("monthKwh", month0)):
            r = con.execute("SELECT COALESCE(SUM(CAST(value AS REAL)),0) FROM events WHERE dev=? AND code='add_ele' AND category<>'seed' AND ts>=?", (o["id"], since)).fetchone()
            out[key] = round((r[0] or 0) / scale, 3)
    gangs = {}
    for code in [c for c in o["status"] if _MAIN_SW.match(c)]:
        gangs[code] = {"todayS": round(Worker._on_seconds(con, o["id"], code, day0, now)),
                       "monthS": round(Worker._on_seconds(con, o["id"], code, month0, now))}
    if gangs:
        out["gangs"] = gangs
        out["todayOnS"] = sum(g["todayS"] for g in gangs.values())
        out["monthOnS"] = sum(g["monthS"] for g in gangs.values())
    return out


def home_view(home: str = "") -> dict[str, Any]:
    snap = snapshot()
    out = [dict(d) for d in snap.get("devices") or [] if not home or str(d.get("home") or "") == home]
    with db() as con:
        for o in out:
            since = {}
            for code in [c for c in o["status"] if _MAIN_SW.match(c)]:
                cur = json.dumps(o["status"][code])
                row = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND code=? AND value<>?", (o["id"], code, cur)).fetchone()
                first = con.execute("SELECT MIN(ts) FROM events WHERE dev=? AND code=? AND ts>COALESCE(?,0)", (o["id"], code, row[0] if row else None)).fetchone()
                since[code] = first[0] if first and first[0] else None
            o["since"] = since
            r = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND category<>'seed' AND (code LIKE 'switch_%' OR code LIKE 'unlock_%' OR code IN ('doorbell','hijack','open_inside','alarm_lock'))", (o["id"],)).fetchone()
            o["lastEvent"] = r[0] if r else None
            if "cur_power" in o["status"]:
                r = con.execute("SELECT AVG(CAST(value AS REAL)), COUNT(*) FROM events WHERE dev=? AND code='cur_power' AND category<>'seed' AND CAST(value AS REAL)>50 AND ts>=?", (o["id"], time.time() - 7 * 86400)).fetchone()
                o["avgPowerRaw"] = r[0] if r and r[1] >= 5 else None
                o["avgPowerN"] = r[1] if r else 0
            try:
                o["usage"] = usage_for(con, o)
            except (sqlite3.Error, ValueError, TypeError) as exc:
                log.warning("usage calc failed for %s: %s", o.get("name"), exc)
            if o.get("category") == "qxj":
                o["wind"] = Worker.wind_stats(con, o["id"])
                # outdoor (solar/battery) sensor vs indoor console: last report time of each, so the card can show
                # "outside unit offline" while the console keeps reporting
                r = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND category<>'seed' AND code IN ('dp131','dp134','windspeed_gust','windspeed_avg','rain_rate','uv_index','dp135')", (o["id"],)).fetchone()
                o["outdoorLastTs"] = r[0] if r else None
                r = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND category<>'seed' AND code IN ('temp_current','humidity_value','atmospheric_pressture','pressure_drop')", (o["id"],)).fetchone()
                o["indoorLastTs"] = r[0] if r else None
                # typical seconds between reports (median of the last 40 gaps) for each unit
                def cadence(codes):
                    ts = [t for (t,) in con.execute(f"SELECT DISTINCT ts FROM events WHERE dev=? AND category<>'seed' AND code IN ({','.join('?' * len(codes))}) ORDER BY ts DESC LIMIT 41", (o["id"], *codes))]
                    gaps = sorted(b - a for a, b in zip(ts[1:], ts[:-1]) if b - a > 0.5)
                    return round(gaps[len(gaps) // 2]) if gaps else None
                o["outdoorIntervalS"] = cadence(["dp131", "dp134", "windspeed_gust"])
                o["indoorIntervalS"] = cadence(["temp_current", "humidity_value", "atmospheric_pressture"])
                # outdoor radio unit (solar/battery) vs indoor console (USB): the outdoor unit is "online" while its
                # wind/rain/UV readings keep arriving (every 30 s); the console itself is the Tuya device's online flag
                r = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND category<>'seed' AND code IN ('dp131','windspeed_gust','dp134','uv_index','rain_rate','windspeed_avg')", (o["id"],)).fetchone()
                last = r[0] if r and r[0] else None
                o["outdoor"] = {"lastTs": last, "online": bool(last and time.time() - last < 240), "ageS": round(time.time() - last) if last else None}
                o["console"] = {"online": bool(o.get("online"))}
            if o.get("category") == "jtmspro":
                rows = con.execute("SELECT ts, code, value FROM events WHERE dev=? AND code LIKE 'unlock_%' AND category<>'seed' AND value<>'0' ORDER BY ts DESC LIMIT 2", (o["id"],)).fetchall()
                o["lastUnlock"] = {"ts": rows[0][0], "method": rows[0][1].replace("unlock_", ""), "slot": json.loads(rows[0][2])} if rows else None
                o["prevUnlock"] = {"ts": rows[1][0], "method": rows[1][1].replace("unlock_", ""), "slot": json.loads(rows[1][2])} if len(rows) > 1 else None
            if "add_ele" in o["status"]:
                day0 = time.time() - (time.time() + 7200) % 86400
                r = con.execute("SELECT COALESCE(SUM(CAST(value AS REAL)),0) FROM events WHERE dev=? AND code='add_ele' AND category<>'seed' AND ts>=?", (o["id"], day0)).fetchone()
                o["todayAddEle"] = r[0] if r else 0
    return {"ok": True, "at": time.time(), "snapshotAt": snap.get("at"), "snapshotAgeS": round(time.time() - float(snap.get("at") or 0), 1),
            "home": home or snap.get("home"), "devices": out}


def home_history(dev: str, code: str, hours: float) -> dict[str, Any]:
    since = time.time() - max(0.1, min(hours, 24 * 3650)) * 3600
    with db() as con:
        rows = con.execute("SELECT ts, value FROM events WHERE dev=? AND code=? AND ts>=? ORDER BY ts", (dev, code, since)).fetchall()
    return {"ok": True, "dev": dev, "code": code, "rows": [[round(t, 1), json.loads(v)] for t, v in rows]}


class H(BaseHTTPRequestHandler):
    server_version = "home-api/1"

    def log_message(self, *a):  # quiet
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self):
        return TOKEN and self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/health":
                snap = snapshot()
                with db() as con:
                    n = con.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM events").fetchone()
                return self._json(200, {"ok": True, "snapshotAgeS": round(time.time() - float(snap.get("at") or 0), 1), "events": n[0], "from": n[1], "to": n[2]})
            if not self._authed():
                return self._json(401, {"ok": False, "error": "unauthorized"})
            if path == "/home":
                q = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                return self._json(200, home_view((q.get("home") or [""])[0]))
            if path == "/home/history":
                q = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                return self._json(200, home_history((q.get("dev") or [""])[0], (q.get("code") or [""])[0], float((q.get("hours") or ["24"])[0])))
            return self._json(404, {"ok": False})
        except Exception as exc:  # noqa: BLE001
            log.exception("request failed")
            return self._json(500, {"ok": False, "error": str(exc)[:200]})


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), H)
    log.info("home-api on %s:%s (db=%s)", HOST, PORT, DB)
    srv.serve_forever()
