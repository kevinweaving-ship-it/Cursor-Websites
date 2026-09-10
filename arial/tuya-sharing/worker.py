#!/opt/tuya-sharing/venv/bin/python
"""tuya-sharing worker — production Tuya transport for Arial / Hansekop.

Uses the Smart Life device-sharing session (tuya-device-sharing-sdk, same flow as Home Assistant)
instead of Tuya IoT Core / OpenAPI. Runs as its own systemd service, separate from arial-api.

Read path : MQTT device reports for the mains meter -> normalized (scales taken from the device's own
            status_range metadata) -> POST /api/arial/meter/ingest (the existing backing store behind
            /api/arial/tuya/probe, /tuya/energy, /tuya/history).
Write path: ONE device only (the Hansekop 4-gang light switch), ONE code family only (switch_1..4, Boolean).
            State is confirmed from the device report / re-query after the command, never assumed.
The mains meter is never commanded.
"""
from __future__ import annotations

import json
import re
import logging
import os
import queue
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests
import sqlite3
from tuya_sharing import CustomerDevice, Manager, SharingDeviceListener, SharingTokenListener
from tuya_sharing.version import VERSION as SDK_VERSION

# Verbatim from Home Assistant core homeassistant/components/tuya/const.py (dev, 2026-09-05)
TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"

METER_ID = "bf90676b1341ecb34dse39"      # HSK Mains Meter (ATORCH GR2PWS, category cz) — READ ONLY
LIGHTS_ID = "bf7f4a91ef39b11261xcua"     # HSK - Light Switch x4 (category kg)
LIGHT_CODES = ("switch_1", "switch_2", "switch_3", "switch_4")
EXTRA_LIGHTS_PATH = Path(os.getenv("TUYA_SHARING_STATE") or "/opt/tuya-sharing/state") / "lights_extra.json"


def light_ids() -> list[str]:
    """Hansekop x4 switch plus any extra light devices (Voelklip rooms) listed in state/lights_extra.json."""
    try:
        extra = [str(x) for x in json.load(open(EXTRA_LIGHTS_PATH)) if x]
    except (OSError, ValueError):
        extra = []
    return [LIGHTS_ID] + [x for x in extra if x != LIGHTS_ID]


_MAIN_SW = re.compile(r"^switch(_\d+)?$")     # switch_1.. gangs, or a breaker's single "switch"
HOME_NAME = os.getenv("TUYA_SHARING_HOME_NAME") or "Voelklip - Home"        # (legacy single-home label)
HOME_NAMES = [x.strip() for x in (os.getenv("TUYA_SHARING_HOME_NAMES") or "Voelklip - Home,My Home ..").split(",") if x.strip()]   # homes watched + recorded
HOME_DB = Path(os.getenv("TUYA_SHARING_STATE") or "/opt/tuya-sharing/state") / "home_events.sqlite"
HOME_RECORD_SKIP = {"switch_backlight", "light_mode", "child_lock",
                    "unlock_offline_pd", "unlock_offline_clear", "remote_no_pd_setkey", "remote_no_dp_key", "lock_record",
                    "local_capacity_link", "lock_local_record", "remote_add", "remote_list", "switch_interlock"}


def _home_db():
    con = sqlite3.connect(HOME_DB, timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS events (ts REAL NOT NULL, dev TEXT NOT NULL, name TEXT, category TEXT, code TEXT NOT NULL, value TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_events_dev_code_ts ON events(dev, code, ts)")
    return con
# Expected metadata for the meter; the worker verifies these against the live status_range before feeding.
METER_EXPECTED = {"cur_voltage": ("V", 2), "cur_current": ("A", 3), "cur_power": ("W", 2), "add_ele": ("kwh", 2)}

STATE_DIR = Path(os.getenv("TUYA_SHARING_STATE") or "/opt/tuya-sharing/state")
SESSION_PATH = STATE_DIR / "session.json"
ENERGY_PATH = STATE_DIR / "meter_energy.json"
HEALTH_PATH = STATE_DIR / "health.json"
LAST_READ_PATH = STATE_DIR / "meter_last_reading.json"
INGEST_URL = os.getenv("ARIAL_INGEST_URL") or "http://127.0.0.1:8003/api/arial/meter/ingest"
INGEST_TOKEN = (os.getenv("ARIAL_METER_INGEST_TOKEN") or "").strip()
CTRL_HOST = os.getenv("TUYA_SHARING_CTRL_HOST") or "127.0.0.1"
CTRL_PORT = int(os.getenv("TUYA_SHARING_CTRL_PORT") or 8007)
CTRL_TOKEN = (os.getenv("TUYA_SHARING_CTRL_TOKEN") or "").strip()
HEARTBEAT_S = float(os.getenv("TUYA_SHARING_HEARTBEAT_S") or 20)
STALE_S = float(os.getenv("TUYA_SHARING_STALE_S") or 180)      # matches arial_api _ENERGY_MAX_GAP_S
RESYNC_S = float(os.getenv("TUYA_SHARING_RESYNC_S") or 1800)   # periodic API re-query (also exercises token refresh)
CONFIRM_S = float(os.getenv("TUYA_SHARING_CONFIRM_S") or 4.0)

log = logging.getLogger("tuya-sharing")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", stream=sys.stdout)
logging.getLogger("tuya_sharing").setLevel(logging.WARNING)


def _write_private(path: Path, data: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump(data, fh, separators=(",", ":"), default=str)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _load(path: Path, default: Any = None) -> Any:
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


class TokenPersist(SharingTokenListener):
    def update_token(self, token_info: dict[str, Any]) -> None:
        sess = _load(SESSION_PATH, {})
        sess["token_info"] = token_info
        sess["last_refresh_at"] = int(time.time())
        _write_private(SESSION_PATH, sess)
        log.info("token refreshed; new expiry in %ss", token_info.get("expire_time"))


class Worker(SharingDeviceListener):
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.started = time.time()
        sess = _load(SESSION_PATH)
        if not sess:
            raise SystemExit(f"no session at {SESSION_PATH}; authorize via the QR flow first")
        self.sess = sess
        self.mgr = Manager(TUYA_CLIENT_ID, sess["user_code"], sess["terminal_id"], sess["endpoint"],
                           sess["token_info"], TokenPersist())
        self.mgr.add_device_listener(self)
        self.energy = _load(ENERGY_PATH) or {"kwh_total": 0.0, "since": time.time(), "last_t": 0, "count": 0}
        self.meter_scale: dict[str, float] = {}
        self.meter_last_report = 0.0        # when the last real V/A/W/kWh reading was taken
        self.meter_last_ts = 0.0            # device-side ts (s) of that reading — never task/resync now
        self.READING_CODES = ("cur_voltage", "cur_current", "cur_power", "add_ele")
        self.meter_online: bool | None = None
        self.last_push: dict[str, Any] = {}
        self.push_errors = 0
        self.mqtt_last_msg = 0.0
        self.light_wait = threading.Condition(self.lock)
        self.home_raw: dict[str, dict[str, Any]] = {}
        self.auth_failed = False
        self.push_q: queue.Queue[str] = queue.Queue(maxsize=50)
        self.raw_dps: dict[int, dict[str, Any]] = {}   # undocumented meter dpIds (not in spec) — recorded, never interpreted
        self._seed_raw_dps()
        self._seed_last_reading()

    METER_COUNTER_DP = 102  # cumulative Wh since power restore; verified against integrated cur_power 2026-09-05

    def _seed_raw_dps(self) -> None:
        """Recover the last seen counter value across restarts (dp102 only reports every ~5 min)."""
        try:
            with open(STATE_DIR / "raw_dps.jsonl") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                        self.raw_dps[int(r["dpId"])] = {"t": r.get("t"), "value": r.get("value"), "wall": r.get("wall")}
                    except Exception:  # noqa: BLE001
                        continue
        except OSError:
            pass

    @staticmethod
    def _as_unix(t: Any) -> float:
        if isinstance(t, bool) or not isinstance(t, (int, float)) or t <= 0:
            return 0.0
        n = float(t)
        if n > 1e12:
            n /= 1000.0
        return n if n > 1e9 else 0.0

    def _seed_last_reading(self) -> None:
        """Last time the meter was actually online with V/A/W. Ignore startup/resync/offline stamps."""
        cands: list[float] = []
        saved = _load(LAST_READ_PATH) or {}
        if isinstance(saved, dict):
            cands.append(self._as_unix(saved.get("ts")))
        try:
            con = sqlite3.connect("/var/www/sailingsa/data/arial_meter_history.sqlite")
            row = con.execute(
                "SELECT ts FROM readings WHERE device=? AND online=1 AND v IS NOT NULL AND w IS NOT NULL "
                "ORDER BY ts DESC LIMIT 1",
                (METER_ID,),
            ).fetchone()
            con.close()
            if row:
                cands.append(self._as_unix(row[0]))
        except sqlite3.Error:
            pass
        for rec in self.raw_dps.values():
            if isinstance(rec, dict):
                cands.append(self._as_unix(rec.get("t")))
        cands = [t for t in cands if t]
        if not cands:
            return
        ts = max(cands)
        if ts > self.meter_last_ts:
            self._set_last_reading(ts)

    def _set_last_reading(self, ts: float) -> None:
        self.meter_last_ts = ts
        self.meter_last_report = ts
        try:
            _write_private(LAST_READ_PATH, {"ts": ts})
        except OSError:
            pass

    def _raw_scaled(self, dp: int, div: float) -> float | None:
        rec = self.raw_dps.get(dp)
        v = rec.get("value") if rec else None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        return round(float(v) / div, 2)

    @staticmethod
    def _power_factor(v: float | None, a: float | None, w: float | None) -> float | None:
        if not v or not a or w is None or v * a <= 0:
            return None
        return round(min(1.0, max(0.0, w / (v * a))), 2)

    def meter_kwh(self) -> float | None:
        """Lifetime register in kWh. If the meter's dp102 register ever restarts from 0 (power loss / reset), the last
        value seen is folded into counter_base so the lifetime figure keeps climbing instead of jumping back."""
        rec = self.raw_dps.get(self.METER_COUNTER_DP)
        if not rec or not isinstance(rec.get("value"), (int, float)) or isinstance(rec.get("value"), bool):
            return None
        wh = float(rec["value"])
        last = self.energy.get("counter_last_wh")
        if isinstance(last, (int, float)) and wh + 1000 < float(last):   # dropped by >1 kWh: register reset
            self.energy["counter_base_wh"] = float(self.energy.get("counter_base_wh", 0.0)) + float(last)
            self.energy["counter_resets"] = int(self.energy.get("counter_resets", 0)) + 1
            log.warning("meter register reset detected: last=%s now=%s base=%s", last, wh, self.energy["counter_base_wh"])
        if last != wh:
            self.energy["counter_last_wh"] = wh
            _write_private(ENERGY_PATH, self.energy)
        total_wh = float(self.energy.get("counter_base_wh", 0.0)) + wh
        try:
            w_now = float(self.mgr.device_map[METER_ID].status.get("cur_power") or 0) / self.meter_scale["cur_power"]
            wall = float(rec.get("wall") or 0)
            if w_now > 0 and wall > 0:
                total_wh += w_now * min(max(time.time() - wall, 0.0), 900.0) / 3600.0
        except Exception:  # noqa: BLE001
            pass
        return round(total_wh / 1000.0, 3)

    # ----------------------------------------------------------------- setup
    def sync_devices(self) -> None:
        """Homes + the two watched devices only (not the whole account)."""
        homes = self.mgr.home_repository.query_homes()
        # by-id lookups are only allowed for our own devices; everything else (incl. shared homes) comes via the home queries
        devices = self.mgr.device_repository.query_devices_by_ids([METER_ID, LIGHTS_ID])
        home_devices, home_of = [], {}
        for h in homes:
            if str(h.name).strip() in HOME_NAMES:
                for d in self.mgr.device_repository.query_devices_by_home(h.id):
                    home_devices.append(d)
                    home_of[d.id] = str(h.name).strip()
        self.home_of = home_of
        with self.lock:
            self.mgr.user_homes = homes
            for d in devices + home_devices:
                d.set_up = True                      # HA entity.py does this; required for MQTT device topics
                self.mgr.device_map[d.id] = d
            self.home_ids = {d.id for d in home_devices if d.id != METER_ID}   # meter keeps its own pipeline (energy bins/history), not a home tile
        if home_devices:
            log.info("homes %s: %d devices watched + recorded (%d online)", HOME_NAMES, len(home_devices), sum(1 for d in home_devices if d.online))
            try:
                # seed one full snapshot so history starts with a known state for every code
                now = time.time()
                with _home_db() as con:
                    for d in home_devices:
                        if d.id == METER_ID:
                            continue
                        if con.execute("SELECT 1 FROM events WHERE dev=? LIMIT 1", (d.id,)).fetchone():
                            continue   # seed once per device; resyncs/restarts must not add snapshot rows
                        for c, v in d.status.items():
                            if c not in HOME_RECORD_SKIP and c != "add_ele":   # add_ele is an increment, never a snapshot
                                con.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (now, d.id, d.name.strip(), "seed", c, json.dumps(v)))
            except sqlite3.Error as exc:
                log.warning("home db seed failed: %s", exc)
        meter = self.mgr.device_map.get(METER_ID)
        if meter is None:
            raise SystemExit("meter not present in the sharing session")
        scales = {}
        for code, (unit, scale) in METER_EXPECTED.items():
            rng = meter.status_range.get(code)
            vals = json.loads(rng.values) if rng and rng.values else {}
            if not rng or str(vals.get("unit", "")).lower() != unit.lower() or int(vals.get("scale", -1)) != scale:
                raise SystemExit(f"meter metadata mismatch for {code}: {vals!r} (expected unit={unit} scale={scale})")
            scales[code] = 10.0 ** scale
        add_rt = getattr(meter.status_range.get("add_ele"), "report_type", None)
        if add_rt != "sum":
            raise SystemExit(f"add_ele report_type={add_rt!r}; accumulation logic assumes 'sum'")
        with self.lock:
            self.meter_scale = scales
            self.meter_online = bool(meter.online)
            # Keep the last real reading time. Resync/startup must not stamp "now".
            if not self.meter_last_ts:
                self._seed_last_reading()
        log.info("meter %s online=%s raw=%s scales=%s add_ele=sum", meter.name.strip(), meter.online, meter.status,
                 {k: int(v) for k, v in scales.items()})
        lights = self.mgr.device_map.get(LIGHTS_ID)
        if lights is None:
            raise SystemExit("lights device not present in the sharing session")
        for c in LIGHT_CODES:
            fn = lights.function.get(c)
            if not fn or fn.type != "Boolean":
                raise SystemExit(f"light function {c} missing or not Boolean: {fn}")
        log.info("lights %s online=%s switches=%s", lights.name.strip(), lights.online,
                 {c: lights.status.get(c) for c in LIGHT_CODES})
        extra = [i for i in light_ids() if i != LIGHTS_ID]
        missing = [i for i in extra if i not in self.mgr.device_map]
        if missing:
            log.warning("extra light devices not in sharing session: %s", missing)
        log.info("extra lights watched: %d", len(extra) - len(missing))

    # -------------------------------------------------------------- listener
    def update_device(self, device: CustomerDevice, updated_status_properties=None, dp_timestamps=None) -> None:
        now = time.time()
        with self.lock:
            self.mqtt_last_msg = now
        if device.id == METER_ID:
            self._on_meter(device, updated_status_properties or [], dp_timestamps or {}, now)
        elif device.id in light_ids() or device.id in getattr(self, "home_ids", set()):
            with self.light_wait:
                self.light_wait.notify_all()   # wake any pending switch command waiting for this device's report
            if updated_status_properties:
                log.info("lights report %s", {c: device.status.get(c) for c in updated_status_properties})
        if device.id in getattr(self, "home_ids", set()) and updated_status_properties:
            self._record_home(device, updated_status_properties, now)
            if now - getattr(self, "_snap_at", 0) > 0.4:
                self.write_snapshot()

    def write_snapshot(self) -> None:
        """Current state of every home device -> state/home_snapshot.json (read by home_api.py, the separate read API)."""
        try:
            with self.lock:
                devs = [self.mgr.device_map[i] for i in getattr(self, "home_ids", set()) if i in self.mgr.device_map]
                out = [{"id": d.id, "name": d.name.strip(), "category": d.category, "online": bool(d.online), "status": dict(d.status),
                        "home": getattr(self, "home_of", {}).get(d.id, HOME_NAME),
                        "icon": getattr(d, "icon", None) or None, "product_id": getattr(d, "product_id", None) or None,
                        "product_name": (getattr(d, "product_name", None) or "").strip() or None,
                        "raw": {k: v.get("value") for k, v in self.home_raw.get(d.id, {}).items()},
                        "units": {c: (json.loads(r.values) if r.values else {}) for c, r in d.status_range.items() if c in d.status}} for d in devs]
            tmp = STATE_DIR / "home_snapshot.json.tmp"
            tmp.write_text(json.dumps({"at": time.time(), "home": HOME_NAME, "devices": out}), encoding="utf-8")
            os.chmod(tmp, 0o644)
            os.replace(tmp, STATE_DIR / "home_snapshot.json")
            self._snap_at = time.time()
        except Exception as exc:  # noqa: BLE001
            log.warning("snapshot write failed: %s", exc)

    def _record_home(self, device: CustomerDevice, codes, now: float) -> None:
        rows = [(now, device.id, device.name.strip(), device.category, c, json.dumps(device.status.get(c)))
                for c in codes if c not in HOME_RECORD_SKIP]
        if not rows:
            return
        try:
            with _home_db() as con:
                con.executemany("INSERT INTO events VALUES (?,?,?,?,?,?)", rows)
        except sqlite3.Error as exc:
            log.warning("home db write failed: %s", exc)

    @staticmethod
    def _on_seconds(con, dev: str, code: str, start: float, end: float) -> float:
        """Seconds the switch was ON between start and end, from the change log (state before start carried in)."""
        prev = con.execute("SELECT value FROM events WHERE dev=? AND code=? AND ts<? ORDER BY ts DESC LIMIT 1", (dev, code, start)).fetchone()
        state = bool(json.loads(prev[0])) if prev else False
        total, t = 0.0, start
        for ts, val in con.execute("SELECT ts, value FROM events WHERE dev=? AND code=? AND ts>=? AND ts<? AND category<>'seed' ORDER BY ts", (dev, code, start, end)):
            v = bool(json.loads(val))
            if state:
                total += ts - t
            state, t = v, ts
        if state:
            total += end - t
        return total

    def usage_for(self, con, o: dict) -> dict[str, Any]:
        """Today / this-month usage per device: kWh (plugs, from add_ele increments) and ON time per switch gang."""
        now = time.time()
        lt = time.gmtime(now + 7200)                               # SAST wall clock
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
            gangs[code] = {"todayS": round(self._on_seconds(con, o["id"], code, day0, now)),
                           "monthS": round(self._on_seconds(con, o["id"], code, month0, now))}
        if gangs:
            out["gangs"] = gangs
            out["todayOnS"] = sum(g["todayS"] for g in gangs.values())
            out["monthOnS"] = sum(g["monthS"] for g in gangs.values())
        return out

    @staticmethod
    def wind_stats(con, dev: str) -> dict[str, Any]:
        """Wind context for the gauge: previous reading, 3 h series (5-min bins), 24 h max, 30-min trend, pressure trend."""
        now = time.time()

        def series(code, hours):
            return [(t, float(json.loads(v))) for t, v in con.execute(
                "SELECT ts, value FROM events WHERE dev=? AND code=? AND category<>'seed' AND ts>=? ORDER BY ts", (dev, code, now - hours * 3600))]

        def bins(rows, minutes, hours):
            n = int(hours * 60 / minutes)
            out = [None] * n
            t0 = now - hours * 3600
            for t, v in rows:
                i = int((t - t0) / (minutes * 60))
                if 0 <= i < n:
                    out[i] = v if out[i] is None else max(out[i], v)
            return out

        avg, gust, pres = series("windspeed_avg", 24), series("windspeed_gust", 24), series("atmospheric_pressture", 6)
        cur = series("dp131", 24)      # undocumented dp131 = the app's "Wind Speed" (current, km/h x10), reported every 30 s
        def last(rows, k=1):
            return rows[-k][1] if len(rows) >= k else None
        def mean(rows, since):
            v = [x for t, x in rows if t >= since]
            return sum(v) / len(v) if v else None
        m_now, m_prev = mean(gust, now - 900), mean([r for r in gust if r[0] < now - 900], now - 2700)   # last 15 min vs the 30 min before
        trend = None if m_now is None or m_prev is None else m_now - m_prev
        mx = max(gust, key=lambda r: r[1]) if gust else None
        mxa = max(avg, key=lambda r: r[1]) if avg else None
        p_now, p_old = last(pres), (pres[0][1] if pres else None)
        # direction: dp134 carries compass letters in a base64 byte string
        import base64
        PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        dirs = []
        for t, v in con.execute("SELECT ts, value FROM events WHERE dev=? AND code='dp134' AND ts>=? ORDER BY ts", (dev, now - 24 * 3600)):
            try:
                letters = "".join(ch for ch in base64.b64decode(json.loads(v))[:5].decode("latin1") if ch in "NESW")
                if letters in PTS:
                    dirs.append((t, PTS.index(letters)))
            except Exception:  # noqa: BLE001
                pass
        dir_recent = [i for t, i in dirs if t >= now - 1800]
        dir24 = bins([(t, i) for t, i in dirs], 5, 24)
        return {"prevAvg": last(avg, 2), "prevGust": last(gust, 2), "trendGust": trend,
                "curRaw": last(cur), "curKn": (last(cur) / 10 / 1.852) if last(cur) is not None else None, "curAt": cur[-1][0] if cur else None,
                "prevCurKn": (last(cur, 2) / 10 / 1.852) if last(cur, 2) is not None else None,
                "series24hCur": bins(cur, 5, 24), "series3hCur": bins(cur, 5, 3), "binMin": 5,
                "dirRecent": dir_recent, "dirLast": dirs[-1][1] if dirs else None, "dir24h": dir24,
                "series24hGust": bins(gust, 5, 24), "series24hAvg": bins(avg, 5, 24),
                "max24Gust": {"v": mx[1], "t": mx[0]} if mx else None, "max24Avg": {"v": mxa[1], "t": mxa[0]} if mxa else None,
                "series3hGust": bins(gust, 5, 3), "series3hAvg": bins(avg, 5, 3),
                "pressureTrend": (p_now - p_old) if (p_now is not None and p_old is not None and len(pres) > 1) else None,
                "samples": len(gust)}

    def home_view(self) -> dict[str, Any]:
        """Current state of every watched home device + light on-since / plug energy from the event log."""
        with self.lock:
            devs = [self.mgr.device_map[i] for i in getattr(self, "home_ids", set()) if i in self.mgr.device_map]
            out = [{"id": d.id, "name": d.name.strip(), "category": d.category, "online": bool(d.online), "status": dict(d.status),
                    "raw": {k: v.get("value") for k, v in self.home_raw.get(d.id, {}).items()},
                    "units": {c: (json.loads(r.values) if r.values else {}) for c, r in d.status_range.items() if c in d.status}} for d in devs]
        try:
            with _home_db() as con:
                for o in out:
                    # light gangs: when did each switch last change (for "on for 2h15")
                    since = {}
                    for code in [c for c in o["status"] if _MAIN_SW.match(c)]:
                        cur = json.dumps(o["status"][code])
                        row = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND code=? AND value<>?", (o["id"], code, cur)).fetchone()
                        first = con.execute("SELECT MIN(ts) FROM events WHERE dev=? AND code=? AND ts>COALESCE(?,0)", (o["id"], code, row[0] if row else None)).fetchone()
                        since[code] = first[0] if first and first[0] else None
                    o["since"] = since
                    if o["category"] == "qxj":
                        o["wind"] = self.wind_stats(con, o["id"])
                    if o["category"] == "jtmspro":
                        rows = con.execute("SELECT ts, code, value FROM events WHERE dev=? AND code LIKE 'unlock_%' AND category<>'seed' AND value<>'0' ORDER BY ts DESC LIMIT 2", (o["id"],)).fetchall()
                        o["lastUnlock"] = {"ts": rows[0][0], "method": rows[0][1].replace("unlock_", ""), "slot": json.loads(rows[0][2])} if rows else None
                        o["prevUnlock"] = {"ts": rows[1][0], "method": rows[1][1].replace("unlock_", ""), "slot": json.loads(rows[1][2])} if len(rows) > 1 else None
                    r = con.execute("SELECT MAX(ts) FROM events WHERE dev=? AND category<>'seed' AND (code LIKE 'switch_%' OR code LIKE 'unlock_%' OR code IN ('doorbell','hijack','open_inside','alarm_lock'))", (o["id"],)).fetchone()
                    o["lastEvent"] = r[0] if r else None      # last state change (not power heartbeats) -> card ordering
                    if "cur_power" in o["status"]:
                        # running average draw (raw units) over the last 7 days of reports while actually drawing
                        r = con.execute("SELECT AVG(CAST(value AS REAL)), COUNT(*) FROM events WHERE dev=? AND code='cur_power' AND category<>'seed' AND CAST(value AS REAL)>50 AND ts>=?",
                                        (o["id"], time.time() - 7 * 86400)).fetchone()
                        o["avgPowerRaw"] = r[0] if r and r[1] >= 5 else None
                        o["avgPowerN"] = r[1] if r else 0
                    try:
                        o["usage"] = self.usage_for(con, o)
                    except (sqlite3.Error, ValueError, TypeError) as exc:
                        log.warning("usage calc failed for %s: %s", o["name"], exc)
                    if "add_ele" in o["status"]:
                        day0 = time.time() - (time.time() + 7200) % 86400   # SAST midnight
                        r = con.execute("SELECT COALESCE(SUM(CAST(value AS REAL)),0) FROM events WHERE dev=? AND code='add_ele' AND ts>=?", (o["id"], day0)).fetchone()
                        o["todayAddEle"] = r[0] if r else 0
        except sqlite3.Error as exc:
            log.warning("home db read failed: %s", exc)
        return {"ok": True, "at": time.time(), "home": HOME_NAME, "devices": out}

    def home_history(self, dev: str, code: str, hours: float) -> dict[str, Any]:
        since = time.time() - max(0.1, min(hours, 24 * 90)) * 3600
        with _home_db() as con:
            rows = con.execute("SELECT ts, value FROM events WHERE dev=? AND code=? AND ts>=? ORDER BY ts", (dev, code, since)).fetchall()
        return {"ok": True, "dev": dev, "code": code, "rows": [[round(t, 1), json.loads(v)] for t, v in rows]}

    def add_device(self, device: CustomerDevice) -> None:  # bindUser for other devices: ignore
        pass

    def remove_device(self, device_id: str) -> None:
        log.warning("device removed from account: %s", device_id)

    def _on_meter(self, device: CustomerDevice, changed: list[str], dp_ts: dict[str, int], now: float) -> None:
        with self.lock:
            prev_online = self.meter_online
            self.meter_online = bool(device.online)
            if "add_ele" in changed:
                t = int(dp_ts.get("add_ele") or 0)
                if t and t == self.energy.get("last_t"):
                    pass  # duplicate delivery of the same report
                else:
                    inc = float(device.status.get("add_ele") or 0) / self.meter_scale["add_ele"]
                    self.energy["kwh_total"] = round(float(self.energy.get("kwh_total", 0.0)) + inc, 5)
                    self.energy["last_t"] = t
                    self.energy["count"] = int(self.energy.get("count", 0)) + 1
                    self.energy["last_inc_kwh"] = inc
                    _write_private(ENERGY_PATH, self.energy)
            reading = [c for c in changed if c in self.READING_CODES]
            if reading and device.online:
                taken = max((self._as_unix(dp_ts.get(c)) for c in reading), default=0.0)
                # Only stamp a device reading time. A resync/snapshot with no DP ts is not a new reading.
                if taken:
                    self._set_last_reading(taken)
        if prev_online is not None and prev_online != self.meter_online:
            log.warning("meter online -> %s", self.meter_online)
        if changed or prev_online != self.meter_online:
            self.push(reason="report" if changed else "online-change")

    # ------------------------------------------------------------------ push
    def normalized(self) -> dict[str, Any]:
        d = self.mgr.device_map[METER_ID]
        s = d.status

        def num(code: str) -> float | None:
            raw = s.get(code)
            if raw is None or isinstance(raw, bool):
                return None
            return round(float(raw) / self.meter_scale[code], 3)

        return {
            "v": num("cur_voltage"), "a": num("cur_current"), "w": num("cur_power"),
            "kwh": round(float(self.energy.get("kwh_total", 0.0)), 3),
            "meterKwh": self.meter_kwh(),
            "hz": self._raw_scaled(133, 100.0),
            "tempC": self._raw_scaled(135, 1.0),
            "pf": self._power_factor(num("cur_voltage"), num("cur_current"), num("cur_power")),
            "switch": s.get("switch_1") if isinstance(s.get("switch_1"), bool) else None,
            "online": bool(self.meter_online),
            "raw": dict(s),
        }

    def push(self, reason: str) -> None:
        """Queue a push so MQTT callbacks never block on HTTP."""
        try:
            self.push_q.put_nowait(reason)
        except queue.Full:
            pass

    def push_loop(self) -> None:
        while not self.stop.is_set():
            try:
                reason = self.push_q.get(timeout=1)
            except queue.Empty:
                continue
            self._push_now(reason)

    def _push_now(self, reason: str) -> bool:
        if not INGEST_TOKEN:
            return False
        with self.lock:
            n = self.normalized()
            ts = self.meter_last_ts
            if not ts:
                return False
        payload = {"device": METER_ID, "ts": ts, "online": n["online"], "v": n["v"], "a": n["a"], "w": n["w"],
                   "kwh": n["kwh"], "src": "sharing"}
        if n.get("meterKwh") is not None:
            payload["meterKwh"] = n["meterKwh"]
        for k in ("hz", "tempC", "pf"):
            if n.get(k) is not None:
                payload[k] = n[k]
        if n["switch"] is not None:
            payload["switch"] = n["switch"]
        try:
            r = requests.post(INGEST_URL, json=payload, timeout=5,
                              headers={"Authorization": f"Bearer {INGEST_TOKEN}"})
            ok = r.status_code == 200 and r.json().get("ok") is True
            if not ok:
                self.push_errors += 1
                log.warning("ingest %s -> %s %s", reason, r.status_code, r.text[:200])
            else:
                with self.lock:
                    self.last_push = {"at": time.time(), "reason": reason, "ts": ts, "v": n["v"], "a": n["a"],
                                      "w": n["w"], "kwh": n["kwh"], "online": n["online"]}
            return ok
        except requests.RequestException as exc:
            self.push_errors += 1
            log.warning("ingest %s failed: %s", reason, exc)
            return False

    # --------------------------------------------------------------- control
    def light_set(self, target: str, value: bool, device_id: str | None = None) -> dict[str, Any]:
        device_id = device_id or LIGHTS_ID
        if device_id not in light_ids() and device_id not in getattr(self, "home_ids", set()):
            raise ValueError("device not controllable")   # controllable = Hansekop lights + every watched home device
        dev = self.mgr.device_map.get(device_id)
        if dev is None:
            raise ValueError("device not in sharing session")
        main = [c for c in dev.function if _MAIN_SW.match(c) and getattr(dev.function[c], "type", "") == "Boolean"] or list(LIGHT_CODES)
        codes = main if target == "all" else [target]
        if any(c not in main for c in codes):
            raise ValueError("unknown switch")
        commands = [{"code": c, "value": bool(value)} for c in codes]
        log.info("LIGHT command device=%s %s", device_id, commands)
        t0 = time.time()
        self.mgr.send_commands(device_id, commands)   # SDK path: POST /v1.1/m/thing/{id}/commands
        # Confirm from the device report (MQTT) — never assume.
        deadline = t0 + CONFIRM_S
        with self.light_wait:
            while time.time() < deadline and not all(dev.status.get(c) is bool(value) for c in codes):
                self.light_wait.wait(max(0.05, deadline - time.time()))
        confirmed = all(dev.status.get(c) is bool(value) for c in codes)
        source = "mqtt"
        if not confirmed:
            # Fall back to an authoritative re-query of the device status.
            fresh = self.mgr.device_repository.query_devices_by_ids([device_id])
            if fresh:
                with self.lock:
                    fresh[0].set_up = True
                    self.mgr.device_map[device_id] = fresh[0]
                dev = fresh[0]
            confirmed = all(dev.status.get(c) is bool(value) for c in codes)
            source = "requery"
        log.info("LIGHT result device=%s confirmed=%s via %s in %.2fs state=%s", device_id, confirmed, source,
                 time.time() - t0, {c: dev.status.get(c) for c in main})
        return {"ok": True, "confirmed": confirmed, "confirmSource": source, "latencyS": round(time.time() - t0, 2),
                "deviceId": device_id, "online": bool(dev.online), "switches": [{"code": c, "on": dev.status.get(c)} for c in main]}

    def _raw_mq(self, msg: dict) -> None:
        """Record meter dpIds that are absent from the published specification (the SDK drops them)."""
        try:
            if msg.get("protocol") != 4:
                return
            dev_id = msg["data"].get("devId")
            if dev_id in getattr(self, "home_ids", set()) and dev_id != METER_ID:
                self._raw_home(dev_id, msg["data"].get("status") or [])
                return
            if dev_id != METER_ID:
                return
            known = self.mgr.device_map[METER_ID].local_strategy
            if (STATE_DIR / "capture_all_dps").exists():
                known = {}
            rows = []
            for s in msg["data"].get("status") or []:
                dp = s.get("dpId")
                if dp is None or dp in known:
                    continue
                rec = {"t": s.get("t"), "value": s.get("value"), "wall": time.time()}
                with self.lock:
                    self.raw_dps[int(dp)] = rec
                rows.append({"dpId": dp, **rec})
            if rows:
                with open(STATE_DIR / "raw_dps.jsonl", "a") as fh:
                    for r in rows:
                        fh.write(json.dumps(r) + "\n")
                if any(r["dpId"] == self.METER_COUNTER_DP for r in rows):
                    self.push("counter")
        except Exception:  # noqa: BLE001
            log.exception("raw mq")

    def _raw_home(self, dev_id: str, status: list) -> None:
        """Home devices: dpIds missing from the published spec (the SDK drops them) are logged as code 'dp<N>' and kept
        in self.home_raw so the card can use them (weather station wind direction / light intensity live here)."""
        dev = self.mgr.device_map.get(dev_id)
        if dev is None:
            return
        known = dev.local_strategy or {}
        rows, now = [], time.time()
        for s in status:
            dp = s.get("dpId")
            if dp is None or dp in known:
                continue
            code = f"dp{int(dp)}"
            with self.lock:
                self.home_raw.setdefault(dev_id, {})[code] = {"value": s.get("value"), "t": s.get("t"), "wall": now}
            rows.append((now, dev_id, dev.name.strip(), dev.category, code, json.dumps(s.get("value"))))
        if rows:
            try:
                with _home_db() as con:
                    con.executemany("INSERT INTO events VALUES (?,?,?,?,?,?)", rows)
            except sqlite3.Error as exc:
                log.warning("home raw write failed: %s", exc)
            if now - getattr(self, "_snap_at", 0) > 0.4:
                self.write_snapshot()

    def scan_all(self) -> dict[str, Any]:
        """Read-only: current status of every device in the sharing session's homes (fresh query, no MQTT subscribe)."""
        out = []
        for home in self.mgr.home_repository.query_homes():
            for d in self.mgr.device_repository.query_devices_by_home(home.id):
                out.append({"home": home.name, "id": d.id, "name": d.name.strip(), "category": d.category, "product": d.product_name,
                            "icon": getattr(d, "icon", None) or None, "product_id": getattr(d, "product_id", None) or None,
                            "product_name": (getattr(d, "product_name", None) or "").strip() or None,
                            "online": bool(d.online), "status": dict(d.status),
                            "units": {c: (json.loads(r.values) if r.values else {}) for c, r in d.status_range.items()}})
        return {"ok": True, "at": time.time(), "devices": out}

    def scenes_view(self) -> dict[str, Any]:
        """Read-only: tap-to-run scenes / automations visible to the sharing session, per home."""
        out = []
        for home in self.mgr.home_repository.query_homes():
            try:
                for sc in self.mgr.scene_repository.query_scenes([home.id]):
                    out.append({"home": home.name, "id": getattr(sc, "scene_id", None), "name": getattr(sc, "name", None),
                                "enabled": getattr(sc, "enabled", None), "status": getattr(sc, "status", None)})
            except Exception as exc:  # noqa: BLE001
                out.append({"home": home.name, "error": str(exc)[:160]})
        return {"ok": True, "scenes": out}

    def device_view(self, dev_id: str) -> dict[str, Any] | None:
        dev = self.mgr.device_map.get(dev_id)
        if dev is None:
            return None
        with self.lock:
            out = {"deviceId": dev.id, "name": dev.name.strip(), "online": bool(dev.online), "status": dict(dev.status),
                   "mqttConnected": self.mqtt_connected(), "at": time.time()}
            if dev_id == METER_ID:
                out.update(self.normalized())
                out["lastReportAgeS"] = round(time.time() - (self.meter_last_ts or self.meter_last_report), 1) if (self.meter_last_ts or self.meter_last_report) else None
                out["lastReadingAt"] = round(self.meter_last_ts, 3) if self.meter_last_ts else None
            return out

    def mqtt_connected(self) -> bool:
        mq = self.mgr.mq
        try:
            return bool(mq and mq.client and mq.client.is_connected())
        except Exception:  # noqa: BLE001
            return False

    def health(self) -> dict[str, Any]:
        with self.lock:
            tok = self.mgr.customer_api.token_info
            return {
                "ok": self.mqtt_connected() and not self.auth_failed,
                "sdk": SDK_VERSION, "uptimeS": round(time.time() - self.started, 1),
                "username": self.sess.get("username"), "endpoint": self.sess.get("endpoint"),
                "tokenExpiresInS": round(tok.expire_time / 1000 - time.time(), 0),
                "mqttConnected": self.mqtt_connected(),
                "mqttLastMsgAgeS": round(time.time() - self.mqtt_last_msg, 1) if self.mqtt_last_msg else None,
                "meterOnline": self.meter_online,
                "meterLastReadingAt": round(self.meter_last_ts, 3) if self.meter_last_ts else None,
                "meterLastReportAgeS": round(time.time() - self.meter_last_ts, 1) if self.meter_last_ts else (
                    round(time.time() - self.meter_last_report, 1) if self.meter_last_report else None),
                "meterStale": (time.time() - (self.meter_last_ts or self.meter_last_report or 0)) > STALE_S
                if (self.meter_last_ts or self.meter_last_report) else True,
                "energy": self.energy, "lastPush": self.last_push, "pushErrors": self.push_errors,
                "authFailed": self.auth_failed,
                "rawDps": {str(k): v for k, v in self.raw_dps.items()},
            }

    # --------------------------------------------------------------- threads
    def heartbeat_loop(self) -> None:
        """Re-assert the last real reading while the link is genuinely alive; go silent when stale so the
        existing METER_FRESH_S threshold in arial_api turns the card to No link honestly."""
        while not self.stop.wait(HEARTBEAT_S):
            self.write_snapshot()
            with self.lock:
                age = time.time() - self.meter_last_report
                alive = self.mqtt_connected() and age <= STALE_S and self.meter_online
            if alive:
                self.push(reason="heartbeat")
            elif self.meter_online is False:
                self.push(reason="offline")   # genuine device offline (Tuya bizCode) — recorded as such
            else:
                log.warning("link stale: mqtt=%s lastReportAge=%.0fs — not pushing", self.mqtt_connected(), age)
            try:
                _write_private(HEALTH_PATH, self.health())
            except OSError:
                pass

    def resync_loop(self) -> None:
        while not self.stop.wait(RESYNC_S):
            try:
                self.sync_devices()
                self.push(reason="resync")
                self.auth_failed = False
            except SystemExit as exc:
                log.error("resync: %s", exc)
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                log.error("resync failed: %s", msg)
                if "sign invalid" in msg or "token" in msg.lower():
                    self.auth_failed = True

    def run(self) -> None:
        self.sync_devices()
        self.mgr.refresh_mq()
        for _ in range(100):
            if self.mqtt_connected():
                break
            time.sleep(0.1)
        log.info("mqtt connected=%s", self.mqtt_connected())
        if self.mgr.mq:
            self.mgr.mq.add_message_listener(self._raw_mq)
        threading.Thread(target=self.push_loop, name="push", daemon=True).start()
        self.push(reason="startup")
        threading.Thread(target=self.heartbeat_loop, name="heartbeat", daemon=True).start()
        threading.Thread(target=self.resync_loop, name="resync", daemon=True).start()
        srv = ThreadingHTTPServer((CTRL_HOST, CTRL_PORT), make_handler(self))
        threading.Thread(target=srv.serve_forever, name="ctrl", daemon=True).start()
        log.info("control API on %s:%s", CTRL_HOST, CTRL_PORT)
        self.stop.wait()
        srv.shutdown()
        if self.mgr.mq:
            self.mgr.mq.stop()


def make_handler(w: Worker):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # quiet
            pass

        def _json(self, code: int, obj: Any) -> None:
            body = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authed(self) -> bool:
            auth = self.headers.get("Authorization") or ""
            return bool(CTRL_TOKEN) and auth == f"Bearer {CTRL_TOKEN}"

        def do_GET(self):
            if self.path == "/health":
                return self._json(200, w.health())
            if self.path == "/home":
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                return self._json(200, w.home_view())
            if self.path.startswith("/home/history"):
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                from urllib.parse import parse_qs
                q = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                try:
                    return self._json(200, w.home_history((q.get("dev") or [""])[0], (q.get("code") or [""])[0], float((q.get("hours") or ["24"])[0])))
                except (ValueError, sqlite3.Error) as exc:
                    return self._json(400, {"ok": False, "error": str(exc)[:200]})
            if self.path == "/scenes":
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                return self._json(200, w.scenes_view())
            if self.path == "/scan":
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                try:
                    return self._json(200, w.scan_all())
                except Exception as exc:  # noqa: BLE001
                    return self._json(502, {"ok": False, "error": str(exc)[:200]})
            if self.path.startswith("/devices/"):
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                view = w.device_view(self.path.split("/", 2)[2].split("?")[0])
                if view is None:
                    return self._json(404, {"ok": False, "error": "device not watched"})
                view["ok"] = True
                return self._json(200, view)
            return self._json(404, {"ok": False})

        def do_POST(self):
            if self.path == "/push":
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                ok = w._push_now("manual")
                return self._json(200, {"ok": ok, "lastPush": w.last_push, "pushErrors": w.push_errors})
            if self.path != "/light":
                return self._json(404, {"ok": False})
            if not self._authed():
                return self._json(401, {"ok": False, "error": "unauthorized"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                target = str(body.get("switch") or "")
                value = body.get("value")
                if not isinstance(value, bool):
                    raise ValueError("value must be boolean")
                return self._json(200, w.light_set(target, value, str(body.get("device_id") or LIGHTS_ID)))
            except ValueError as exc:
                return self._json(400, {"ok": False, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                log.exception("light command failed")
                return self._json(502, {"ok": False, "error": str(exc)[:200]})

    return H


def main() -> int:
    w = Worker()
    signal.signal(signal.SIGTERM, lambda *_: w.stop.set())
    signal.signal(signal.SIGINT, lambda *_: w.stop.set())
    try:
        w.run()
    except SystemExit as exc:
        log.error("fatal: %s", exc)
        _write_private(HEALTH_PATH, {"ok": False, "fatal": str(exc), "at": time.time()})
        return 2
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        log.exception("fatal")
        _write_private(HEALTH_PATH, {"ok": False, "fatal": msg, "authRequired": "sign invalid" in msg, "at": time.time()})
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
