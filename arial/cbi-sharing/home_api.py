#!/opt/cbi-sharing/venv/bin/python
"""CBI Home read API — isolated from Smart Life home_api on :8008.

Reads only /opt/cbi-sharing/state. Safe to restart without touching the collector.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

_MAIN_SW = re.compile(r"^switch(_\d+)?$")
STATE = Path(os.getenv("CBI_SHARING_STATE") or "/opt/cbi-sharing/state")
HOMES_PATH = Path(os.getenv("CBI_SHARING_HOMES") or "/opt/cbi-sharing/homes.json")
DB = STATE / "home_events.sqlite"
SNAP = STATE / "home_snapshot.json"
SEEN = STATE / "homes_seen.json"
WATER = STATE / "water_stats.json"
ELE = STATE / "ele_stats.json"
HOST = os.getenv("CBI_HOME_API_HOST") or "127.0.0.1"
PORT = int(os.getenv("CBI_SHARING_HOME_API_PORT") or 8011)
TOKEN = (os.getenv("CBI_SHARING_CTRL_TOKEN") or "").strip()
log = logging.getLogger("cbi-home-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s cbi-home-api %(message)s")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def db() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)


def _on_seconds(con: sqlite3.Connection, dev: str, code: str, start: float, end: float) -> float:
    prev = con.execute(
        "SELECT value FROM events WHERE dev=? AND code=? AND ts<? ORDER BY ts DESC LIMIT 1",
        (dev, code, start),
    ).fetchone()
    state = bool(json.loads(prev[0])) if prev else False
    total, t = 0.0, start
    for ts, val in con.execute(
        "SELECT ts, value FROM events WHERE dev=? AND code=? AND ts>=? AND ts<? AND category<>'seed' ORDER BY ts",
        (dev, code, start, end),
    ):
        v = bool(json.loads(val))
        if state:
            total += ts - t
        state, t = v, ts
    if state:
        total += end - t
    return total


def usage_for(con: sqlite3.Connection, o: dict[str, Any]) -> dict[str, Any]:
    now = time.time()
    lt = time.gmtime(now + 7200)
    day0 = now - (lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
    month0 = day0 - (lt.tm_mday - 1) * 86400
    out: dict[str, Any] = {"day0": day0, "month0": month0}
    if "add_ele" in o.get("status") or {}:
        u = (o.get("units") or {}).get("add_ele") or {}
        scale = 10.0 ** int(u.get("scale", 3) or 0)
        for key, since in (("todayKwh", day0), ("monthKwh", month0)):
            r = con.execute(
                "SELECT COALESCE(SUM(CAST(value AS REAL)),0) FROM events WHERE dev=? AND code='add_ele' AND category<>'seed' AND ts>=?",
                (o["id"], since),
            ).fetchone()
            out[key] = round((r[0] or 0) / scale, 3)
    gangs = {}
    for code in [c for c in (o.get("status") or {}) if _MAIN_SW.match(c)]:
        gangs[code] = {
            "todayS": round(_on_seconds(con, o["id"], code, day0, now)),
            "monthS": round(_on_seconds(con, o["id"], code, month0, now)),
        }
    if gangs:
        out["gangs"] = gangs
        out["todayOnS"] = sum(g["todayS"] for g in gangs.values())
        out["monthOnS"] = sum(g["monthS"] for g in gangs.values())
    return out


def water_use_for(o: dict[str, Any]) -> dict[str, Any] | None:
    wu = o.get("waterUse")
    if isinstance(wu, dict) and any(k in wu for k in ("todayL", "monthL", "lastMonthL")):
        return wu
    cache = (_load(WATER, {}).get("devices") or {})
    hit = cache.get(o.get("id"))
    return hit if isinstance(hit, dict) else None


def ele_use_for(o: dict[str, Any]) -> dict[str, Any] | None:
    eu = o.get("eleUse")
    if isinstance(eu, dict) and any(k in eu for k in ("todayKwh", "monthKwh", "lastMonthKwh")):
        return eu
    cache = (_load(ELE, {}).get("devices") or {})
    hit = cache.get(o.get("id"))
    return hit if isinstance(hit, dict) else None


def _attach_meter_stats(o: dict[str, Any]) -> None:
    wu = water_use_for(o)
    if wu:
        o["waterUse"] = wu
    eu = ele_use_for(o)
    if eu:
        o["eleUse"] = eu


def home_view(home: str = "") -> dict[str, Any]:
    snap = _load(SNAP, {"at": 0, "devices": []})
    out = [
        dict(d)
        for d in snap.get("devices") or []
        if not home or str(d.get("home_id") or d.get("home") or "") == home
    ]
    if DB.exists():
        with db() as con:
            for o in out:
                try:
                    o["usage"] = usage_for(con, o)
                except (sqlite3.Error, ValueError, TypeError) as exc:
                    log.warning("usage calc failed for %s: %s", o.get("name"), exc)
                _attach_meter_stats(o)
    else:
        for o in out:
            _attach_meter_stats(o)
    return {
        "ok": True,
        "source": "cbi",
        "at": time.time(),
        "snapshotAt": snap.get("at"),
        "snapshotAgeS": round(time.time() - float(snap.get("at") or 0), 1),
        "home": home or None,
        "devices": out,
    }


def home_history(dev: str, code: str, hours: float) -> dict[str, Any]:
    since = time.time() - max(0.1, min(hours, 24 * 3650)) * 3600
    rows = []
    if DB.exists():
        with db() as con:
            rows = con.execute(
                "SELECT ts, value FROM events WHERE dev=? AND code=? AND ts>=? ORDER BY ts",
                (dev, code, since),
            ).fetchall()
    return {"ok": True, "source": "cbi", "dev": dev, "code": code, "rows": [[round(t, 1), json.loads(v)] for t, v in rows]}


class H(BaseHTTPRequestHandler):
    server_version = "cbi-home-api/1"

    def log_message(self, *a):
        return

    def _json(self, code: int, obj: Any) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self) -> bool:
        return TOKEN and self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/health":
                snap = _load(SNAP, {"at": 0})
                n = (0, None, None)
                if DB.exists():
                    with db() as con:
                        n = con.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM events").fetchone()
                return self._json(200, {
                    "ok": True,
                    "source": "cbi",
                    "snapshotAgeS": round(time.time() - float(snap.get("at") or 0), 1),
                    "events": n[0],
                    "from": n[1],
                    "to": n[2],
                })
            if not self._authed():
                return self._json(401, {"ok": False, "error": "unauthorized", "source": "cbi"})
            if path == "/homes":
                return self._json(200, {
                    "ok": True,
                    "source": "cbi",
                    "mapped": _load(HOMES_PATH, {}),
                    "seen": _load(SEEN, {}),
                })
            if path == "/home":
                q = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                key = (q.get("home_id") or q.get("home") or [""])[0]
                return self._json(200, home_view(key))
            if path == "/home/history":
                q = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                return self._json(200, home_history((q.get("dev") or [""])[0], (q.get("code") or [""])[0], float((q.get("hours") or ["24"])[0])))
            return self._json(404, {"ok": False, "source": "cbi"})
        except Exception as exc:
            log.exception("CBI home-api request failed")
            return self._json(500, {"ok": False, "error": str(exc)[:200], "source": "cbi"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), H)
    log.info("cbi-home-api on %s:%s (db=%s) — not Smart Life :8008", HOST, PORT, DB)
    srv.serve_forever()
