#!/opt/cbi-sharing/venv/bin/python
"""CBI Home source/listener — isolated from Smart Life /opt/tuya-sharing.

Arial rule: Olarm, Hikvision, EZVIZ, Smart Life, CBI are separate sources.
A site URL (e.g. /bing/) subscribes to the sources it needs. This process is
only the CBI source. It does not read Smart Life state or serve other brands.

Same SDK shape as Smart Life, but own venv/state/ports. homes.json maps a
CBI home_id onto a site URL. Bing is the first subscriber.
"""
from __future__ import annotations

import json
import logging
import os
import re
import signal
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from oem import OemClient, client_from_session, connect_oem, write_session
from tuya_sharing import CustomerDevice, Manager, SharingDeviceListener, SharingTokenListener
from tuya_sharing.version import VERSION as SDK_VERSION

TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
_MAIN_SW = re.compile(r"^switch(_\d+)?$")
HOME_RECORD_SKIP = {
    "switch_backlight", "light_mode", "child_lock",
    "unlock_offline_pd", "unlock_offline_clear", "remote_no_pd_setkey",
    "remote_no_dp_key", "lock_record", "local_capacity_link",
    "lock_local_record", "remote_add", "remote_list", "switch_interlock",
}

ROOT = Path("/opt/cbi-sharing")
STATE_DIR = Path(os.getenv("CBI_SHARING_STATE") or str(ROOT / "state"))
HOMES_PATH = Path(os.getenv("CBI_SHARING_HOMES") or str(ROOT / "homes.json"))
SESSION_PATH = STATE_DIR / "session.json"
HEALTH_PATH = STATE_DIR / "health.json"
SNAP_PATH = STATE_DIR / "home_snapshot.json"
SEEN_PATH = STATE_DIR / "homes_seen.json"
WATER_STATS_PATH = STATE_DIR / "water_stats.json"
HOME_DB = STATE_DIR / "home_events.sqlite"
WATER_REFRESH_S = float(os.getenv("CBI_WATER_REFRESH_S") or 600)
CTRL_HOST = os.getenv("CBI_SHARING_CTRL_HOST") or "127.0.0.1"
CTRL_PORT = int(os.getenv("CBI_SHARING_CTRL_PORT") or 8010)
CTRL_TOKEN = (os.getenv("CBI_SHARING_CTRL_TOKEN") or "").strip()
HEARTBEAT_S = float(os.getenv("CBI_SHARING_HEARTBEAT_S") or 20)
RESYNC_S = float(os.getenv("CBI_SHARING_RESYNC_S") or 1800)
CONFIRM_S = float(os.getenv("CBI_SHARING_CONFIRM_S") or 4.0)

log = logging.getLogger("cbi-sharing")
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


def load_homes() -> dict[str, dict[str, Any]]:
    raw = _load(HOMES_PATH, {})
    return raw if isinstance(raw, dict) else {}


def _sast_year_month(now: float | None = None) -> tuple[int, int]:
    lt = time.gmtime((now or time.time()) + 7200)
    return lt.tm_year, lt.tm_mon


def parse_water_month(raw: dict[str, Any], now: float | None = None) -> dict[str, float]:
    """today / this month / last month litres from tuya.m.dp.stat.month.list (minux)."""
    years = raw.get("years") if isinstance(raw.get("years"), dict) else {}
    y, m = _sast_year_month(now)
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)

    def pick(yy: int, mm: int) -> float:
        row = years.get(str(yy)) if isinstance(years.get(str(yy)), dict) else {}
        try:
            return float((row or {}).get("%02d" % mm) or 0)
        except (TypeError, ValueError):
            return 0.0

    def num(key: str) -> float:
        try:
            return float(raw.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0

    return {
        "todayL": num("thisDay"),
        "monthL": pick(y, m),
        "lastMonthL": pick(py, pm),
        "totalL": num("sum"),
    }


def _home_db() -> sqlite3.Connection:
    con = sqlite3.connect(HOME_DB, timeout=10)
    con.execute(
        "CREATE TABLE IF NOT EXISTS events ("
        "ts REAL NOT NULL, home_id TEXT, dev TEXT NOT NULL, name TEXT, "
        "category TEXT, code TEXT NOT NULL, value TEXT)"
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_cbi_dev_code_ts ON events(dev, code, ts)")
    return con


class TokenPersist(SharingTokenListener):
    def update_token(self, token_info: dict[str, Any]) -> None:
        sess = _load(SESSION_PATH, {})
        sess["token_info"] = token_info
        sess["last_refresh_at"] = int(time.time())
        _write_private(SESSION_PATH, sess)
        log.info("CBI token refreshed; new expiry in %ss", token_info.get("expire_time"))


class Worker(SharingDeviceListener):
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.light_wait = threading.Condition(self.lock)
        self.started = time.time()
        self.mgr: Manager | None = None
        self.oem: OemClient | None = None
        self.kind = ""
        self.devices: dict[str, dict[str, Any]] = {}
        self.home_of: dict[str, str] = {}
        self.home_id_of: dict[str, str] = {}
        self.home_ids: set[str] = set()
        self.mqtt_last_msg = 0.0
        self.auth_failed = False
        self.collecting = False
        self.auth_error = ""

    def health(self) -> dict[str, Any]:
        mapped = load_homes()
        return {
            "ok": bool(self.collecting and not self.auth_failed and SESSION_PATH.exists()),
            "source": "cbi",
            "kind": self.kind or ("oem" if self.oem else "sharing" if self.mgr else ""),
            "sdk": SDK_VERSION,
            "uptimeS": round(time.time() - self.started, 1),
            "session": SESSION_PATH.exists(),
            "authRequired": not SESSION_PATH.exists() or self.auth_failed,
            "authError": self.auth_error[:180] if self.auth_error else "",
            "collecting": self.collecting,
            "mappedHomes": list(mapped),
            "watchedDevices": len(self.home_ids),
            "mqttLastMsgAgeS": round(time.time() - self.mqtt_last_msg, 1) if self.mqtt_last_msg else None,
            "at": time.time(),
        }

    def write_health(self) -> None:
        _write_private(HEALTH_PATH, self.health())

    def mqtt_connected(self) -> bool:
        try:
            return bool(self.mgr and self.mgr.mq and getattr(self.mgr.mq, "client", None))
        except Exception:
            return False

    def connect(self) -> None:
        sess = _load(SESSION_PATH) or {}
        if sess.get("kind") == "oem" and sess.get("sid"):
            self.oem = client_from_session(SESSION_PATH)
            self.kind = "oem"
            log.info("CBI OEM session uid=%s region=%s", self.oem.uid, self.oem.region)
            return
        if sess.get("token_info") and sess.get("kind") != "oem":
            raise SystemExit("refusing a Smart Life / HA sharing session on the CBI collector")
        if not sess and os.getenv("CBI_OEM_AUTO_LOGIN") == "1":
            log.info("CBI OEM password login (white-label Thing SDK 5, not HA QR)")
            self.oem = connect_oem()
            write_session(SESSION_PATH, self.oem)
            self.kind = "oem"
            log.info("CBI OEM login uid=%s region=%s", self.oem.uid, self.oem.region)
            return
        raise SystemExit("no CBI OEM session — run poc.py login (white-label app, not Smart Life / HA QR)")

    def sync_devices(self) -> None:
        if self.oem:
            return self._sync_oem()
        assert self.mgr
        mapped = load_homes()
        homes = self.mgr.home_repository.query_homes()
        seen = []
        home_devices: list[CustomerDevice] = []
        home_of: dict[str, str] = {}
        home_id_of: dict[str, str] = {}
        for h in homes:
            hid = str(h.id)
            name = str(h.name).strip()
            devices = list(self.mgr.device_repository.query_devices_by_home(h.id))
            seen.append({"id": hid, "name": name, "devices": len(devices)})
            if mapped and hid not in mapped:
                log.warning("unmapped CBI home %s %r — add to homes.json (Smart Life homes are a different tool)", hid, name)
                continue
            for d in devices:
                home_devices.append(d)
                home_of[d.id] = name
                home_id_of[d.id] = hid
        _write_private(SEEN_PATH, {"at": time.time(), "homes": seen})
        with self.lock:
            self.mgr.user_homes = homes
            for d in home_devices:
                d.set_up = True
                self.mgr.device_map[d.id] = d
            self.home_of = home_of
            self.home_id_of = home_id_of
            self.home_ids = {d.id for d in home_devices}
        log.info("CBI mapped homes=%d watched=%d online=%d seen=%d",
                 len(mapped), len(home_devices), sum(1 for d in home_devices if d.online), len(seen))
        now = time.time()
        try:
            with _home_db() as con:
                for d in home_devices:
                    if con.execute("SELECT 1 FROM events WHERE dev=? LIMIT 1", (d.id,)).fetchone():
                        continue
                    hid = home_id_of.get(d.id)
                    for c, v in d.status.items():
                        if c not in HOME_RECORD_SKIP and c != "add_ele":
                            con.execute(
                                "INSERT INTO events VALUES (?,?,?,?,?,?,?)",
                                (now, hid, d.id, d.name.strip(), "seed", c, json.dumps(v)),
                            )
        except sqlite3.Error as exc:
            log.warning("CBI db seed failed: %s", exc)
        self.write_snapshot()

    def _sync_oem(self) -> None:
        assert self.oem
        mapped = load_homes()
        seen, devices = self.oem.snapshot_devices(mapped)
        _write_private(SEEN_PATH, {"at": time.time(), "homes": seen})
        home_of = {d["id"]: d.get("home") or "" for d in devices}
        home_id_of = {d["id"]: str(d.get("home_id") or "") for d in devices}
        with self.lock:
            self.devices = {d["id"]: d for d in devices}
            self.home_of = home_of
            self.home_id_of = home_id_of
            self.home_ids = set(self.devices)
        log.info("CBI OEM homes=%d watched=%d seen=%d",
                 len(mapped) or len(seen), len(devices), len(seen))
        now = time.time()
        try:
            with _home_db() as con:
                for d in devices:
                    if con.execute("SELECT 1 FROM events WHERE dev=? LIMIT 1", (d["id"],)).fetchone():
                        continue
                    hid = home_id_of.get(d["id"])
                    for c, v in (d.get("status") or {}).items():
                        if c not in HOME_RECORD_SKIP and c != "add_ele":
                            con.execute(
                                "INSERT INTO events VALUES (?,?,?,?,?,?,?)",
                                (now, hid, d["id"], d.get("name"), "seed", c, json.dumps(v)),
                            )
        except sqlite3.Error as exc:
            log.warning("CBI db seed failed: %s", exc)
        self.write_snapshot()

    def refresh_water_stats(self, force: bool = False) -> None:
        """Read-only Tuya month bins for BV05 / sfkzq. Cached — cloud rate-limits this API."""
        if not self.oem:
            return
        prev = _load(WATER_STATS_PATH, {}) or {}
        if not force and time.time() - float(prev.get("at") or 0) < WATER_REFRESH_S:
            return
        devices: dict[str, dict[str, float]] = dict(prev.get("devices") or {})
        with self.lock:
            rows = [self.devices[i] for i in self.home_ids if i in self.devices]
        for d in rows:
            if str(d.get("category") or "") != "sfkzq":
                continue
            hid = str(d.get("home_id") or self.home_id_of.get(d["id"]) or "")
            try:
                raw = self.oem._api(
                    "tuya.m.dp.stat.month.list",
                    {"devId": d["id"], "gwId": d["id"], "dpId": "6", "type": "minux"},
                    extra={"gid": hid} if hid else None,
                )
                if isinstance(raw, dict):
                    devices[d["id"]] = parse_water_month(raw)
                    log.info("CBI water stats %s today=%.0f month=%.0f last=%.0f",
                             d.get("name"), devices[d["id"]]["todayL"],
                             devices[d["id"]]["monthL"], devices[d["id"]]["lastMonthL"])
            except Exception as exc:
                log.warning("CBI water stats skipped: %s", type(exc).__name__)
        _write_private(WATER_STATS_PATH, {"at": time.time(), "devices": devices})

    def _attach_water(self, out: list[dict[str, Any]]) -> None:
        cache = ((_load(WATER_STATS_PATH, {}) or {}).get("devices") or {})
        for row in out:
            wu = cache.get(row.get("id"))
            if wu:
                row["waterUse"] = wu

    def write_snapshot(self) -> None:
        try:
            if self.oem:
                self.refresh_water_stats()
                with self.lock:
                    out = [dict(self.devices[i]) for i in self.home_ids if i in self.devices]
                self._attach_water(out)
                tmp = SNAP_PATH.with_suffix(".json.tmp")
                tmp.write_text(json.dumps({"at": time.time(), "source": "cbi", "devices": out}), encoding="utf-8")
                os.chmod(tmp, 0o644)
                os.replace(tmp, SNAP_PATH)
                return
            with self.lock:
                devs = [self.mgr.device_map[i] for i in self.home_ids if self.mgr and i in self.mgr.device_map]
                out = []
                for d in devs:
                    out.append({
                        "id": d.id,
                        "name": d.name.strip(),
                        "category": d.category,
                        "online": bool(d.online),
                        "status": dict(d.status),
                        "home": self.home_of.get(d.id, ""),
                        "home_id": self.home_id_of.get(d.id, ""),
                        "icon": getattr(d, "icon", None) or None,
                        "product_id": getattr(d, "product_id", None) or None,
                        "product_name": (getattr(d, "product_name", None) or "").strip() or None,
                        "units": {
                            c: (json.loads(r.values) if r.values else {})
                            for c, r in d.status_range.items() if c in d.status
                        },
                    })
            self._attach_water(out)
            tmp = SNAP_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps({"at": time.time(), "source": "cbi", "devices": out}), encoding="utf-8")
            os.chmod(tmp, 0o644)
            os.replace(tmp, SNAP_PATH)
        except Exception as exc:
            log.warning("CBI snapshot write failed: %s", exc)

    def update_device(self, device: CustomerDevice, updated_status_properties=None, dp_timestamps=None) -> None:
        now = time.time()
        self.mqtt_last_msg = now
        if device.id not in self.home_ids:
            return
        with self.light_wait:
            self.light_wait.notify_all()
        if updated_status_properties:
            self._record_home(device, updated_status_properties, now)
            self.write_snapshot()

    def add_device(self, device: CustomerDevice) -> None:
        return

    def remove_device(self, device_id: str) -> None:
        return

    def _record_home(self, device: CustomerDevice, codes, now: float) -> None:
        hid = self.home_id_of.get(device.id)
        rows = [
            (now, hid, device.id, device.name.strip(), device.category, c, json.dumps(device.status.get(c)))
            for c in codes if c not in HOME_RECORD_SKIP
        ]
        if not rows:
            return
        try:
            with _home_db() as con:
                con.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?)", rows)
        except sqlite3.Error as exc:
            log.warning("CBI db write failed: %s", exc)

    def switch_set(self, device_id: str, target: str, value: bool) -> dict[str, Any]:
        if device_id not in self.home_ids:
            raise ValueError("device not in a mapped CBI home")
        if self.oem:
            return self._switch_oem(device_id, target, value)
        assert self.mgr
        dev = self.mgr.device_map.get(device_id)
        if dev is None:
            raise ValueError("device not in CBI session")
        main = [c for c in dev.function if _MAIN_SW.match(c) and getattr(dev.function[c], "type", "") == "Boolean"]
        codes = main if target == "all" else [target]
        if not codes or any(c not in main for c in codes):
            raise ValueError("unknown switch")
        commands = [{"code": c, "value": bool(value)} for c in codes]
        t0 = time.time()
        self.mgr.send_commands(device_id, commands)
        deadline = t0 + CONFIRM_S
        with self.light_wait:
            while time.time() < deadline and not all(dev.status.get(c) is bool(value) for c in codes):
                self.light_wait.wait(max(0.05, deadline - time.time()))
        confirmed = all(dev.status.get(c) is bool(value) for c in codes)
        return {
            "ok": True,
            "source": "cbi",
            "confirmed": confirmed,
            "latencyS": round(time.time() - t0, 2),
            "deviceId": device_id,
            "home_id": self.home_id_of.get(device_id),
            "online": bool(dev.online),
            "switches": [{"code": c, "on": dev.status.get(c)} for c in main],
        }

    def _switch_oem(self, device_id: str, target: str, value: bool) -> dict[str, Any]:
        assert self.oem
        dev = self.devices.get(device_id) or {}
        status = dict(dev.get("status") or {})
        main = [c for c in status if _MAIN_SW.match(c) or c in {"1", "switch"}]
        if not main and target == "all":
            main = ["1"]
        codes = main if target == "all" else [target]
        if not codes:
            raise ValueError("unknown switch")
        dps: dict[str, Any] = {}
        for c in codes:
            key = "1" if c in {"switch", "switch_1", "all"} and "1" in status else c
            dps[key] = bool(value)
        t0 = time.time()
        self.oem.send_dps(device_id, self.home_id_of.get(device_id) or "", dps)
        time.sleep(min(CONFIRM_S, 1.5))
        self.sync_devices()
        dev = self.devices.get(device_id) or {}
        status = dict(dev.get("status") or {})
        return {
            "ok": True,
            "source": "cbi",
            "confirmed": True,
            "latencyS": round(time.time() - t0, 2),
            "deviceId": device_id,
            "home_id": self.home_id_of.get(device_id),
            "online": bool(dev.get("online")),
            "switches": [{"code": c, "on": status.get(c)} for c in codes],
        }

    def heartbeat_loop(self) -> None:
        while not self.stop.wait(HEARTBEAT_S):
            self.write_health()
            if self.collecting:
                self.write_snapshot()

    def resync_loop(self) -> None:
        while not self.stop.wait(RESYNC_S):
            if not self.collecting:
                continue
            try:
                self.sync_devices()
            except Exception as exc:
                msg = str(exc)
                log.error("CBI resync failed: %s", msg)
                if "sign invalid" in msg or "token" in msg.lower():
                    self.auth_failed = True

    def run_collect(self) -> None:
        self.connect()
        self.sync_devices()
        if self.mgr:
            self.mgr.refresh_mq()
            for _ in range(100):
                if self.mqtt_connected():
                    break
                time.sleep(0.1)
            log.info("CBI mqtt connected=%s", self.mqtt_connected())
        else:
            log.info("CBI OEM poll mode (no HA sharing MQTT)")
        self.collecting = True
        self.auth_failed = False
        self.auth_error = ""
        self.write_health()

    def run(self) -> None:
        srv = ThreadingHTTPServer((CTRL_HOST, CTRL_PORT), make_handler(self))
        threading.Thread(target=srv.serve_forever, name="cbi-ctrl", daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, name="cbi-hb", daemon=True).start()
        log.info("CBI control API on %s:%s (separate from Smart Life :8007)", CTRL_HOST, CTRL_PORT)
        while not self.stop.is_set():
            if not self.collecting and not self.auth_failed:
                try:
                    self.run_collect()
                    threading.Thread(target=self.resync_loop, name="cbi-resync", daemon=True).start()
                except SystemExit as exc:
                    log.error("CBI waiting for OEM login: %s", exc)
                    self.auth_error = str(exc)
                    self.write_health()
                except Exception as exc:
                    log.exception("CBI connect failed")
                    self.auth_failed = True
                    self.auth_error = str(exc)
                    self.write_health()
            elif not SESSION_PATH.exists() or self.auth_failed:
                now = time.time()
                if now - getattr(self, "_wait_log", 0) > 60:
                    log.info("CBI OEM login retry (white-label app session, not HA QR)")
                    self._wait_log = now
                    self.auth_failed = False
                self.write_health()
            self.stop.wait(8)
        srv.shutdown()
        if self.mgr and self.mgr.mq:
            self.mgr.mq.stop()


def make_handler(w: Worker):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            return

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
            path = self.path.split("?", 1)[0]
            if path == "/health":
                return self._json(200, w.health())
            if not self._authed():
                return self._json(401, {"ok": False, "error": "unauthorized", "source": "cbi"})
            if path == "/homes":
                return self._json(200, {"ok": True, "source": "cbi", "mapped": load_homes(), "seen": _load(SEEN_PATH, {})})
            if path == "/home":
                q = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
                hid = (q.get("home_id") or q.get("home") or [""])[0]
                snap = _load(SNAP_PATH, {"devices": []})
                devs = [
                    d for d in (snap.get("devices") or [])
                    if not hid or str(d.get("home_id") or d.get("home") or "") == hid
                ]
                return self._json(200, {"ok": True, "source": "cbi", "at": snap.get("at"), "devices": devs})
            return self._json(404, {"ok": False, "source": "cbi"})

        def do_POST(self):
            if self.path != "/light":
                return self._json(404, {"ok": False, "source": "cbi"})
            if not self._authed():
                return self._json(401, {"ok": False, "error": "unauthorized", "source": "cbi"})
            if not w.collecting:
                return self._json(503, {"ok": False, "error": "CBI session not authorized", "source": "cbi"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                device_id = str(body.get("device_id") or "")
                if not device_id:
                    raise ValueError("device_id required")
                want_home = str(body.get("home_id") or "")
                if want_home and w.home_id_of.get(device_id) != want_home:
                    raise ValueError("device is not in that CBI home")
                target = str(body.get("switch") or "")
                value = body.get("value")
                if not isinstance(value, bool):
                    raise ValueError("value must be boolean")
                return self._json(200, w.switch_set(device_id, target, value))
            except ValueError as exc:
                return self._json(400, {"ok": False, "error": str(exc), "source": "cbi"})
            except Exception as exc:
                log.exception("CBI switch failed")
                return self._json(502, {"ok": False, "error": str(exc)[:200], "source": "cbi"})

    return H


def main() -> int:
    w = Worker()
    signal.signal(signal.SIGTERM, lambda *_: w.stop.set())
    signal.signal(signal.SIGINT, lambda *_: w.stop.set())
    try:
        w.run()
    except Exception:
        log.exception("CBI fatal")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
