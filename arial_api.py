"""Arial Dev — Olarm alarm dashboard + per-user profiles on /arial.

Token: environment OLARM_API_TOKEN only (never expose to the browser).
Users: data/arial_users.json (gitignored), separate from SailingSA accounts.
"""
from __future__ import annotations

import asyncio
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

OLARM_BASE = "https://api.olarm.com"
ALLOWED_ACTIONS = {
    "area-disarm",
    "area-arm",
    "area-stay",
    "area-sleep",
    "zone-bypass",
    "zone-unbypass",
    "user-panic",
}
ZONE_TYPE_LABEL = {
    0: "N/A",
    10: "Door",
    11: "Window",
    20: "Indoor PIR",
    21: "Outdoor PIR",
    50: "Panic button",
    51: "Panic zone",
    90: "Not in use",
}
ZONE_STATE_LABEL = {
    "c": "Closed",
    "a": "Active",
    "b": "Bypassed",
    "al": "Alarm",
}

_ROOT = Path(__file__).resolve().parent
_DATA_DIR = _ROOT / "data"
_USERS_PATH = _DATA_DIR / "arial_users.json"
_lock = threading.Lock()
_olarm_http_lock = threading.Lock()
_olarm_http: httpx.Client | None = None
_live_thread: threading.Thread | None = None
_live_stop = threading.Event()
_panel_cache: dict[str, Any] = {"at": 0.0, "data": None, "seq": 0}
_PANEL_TTL_SEC = 5.0
_last_keypad: dict[str, Any] | None = None
_keypad_log: list[dict[str, Any]] = []
_keypad_log_mtime: float = -1.0
_KEYPAD_LOG_MAX = 80
_KEYPAD_MATCH_MS = 300_000
_KEYPAD_CMD_STATE = {
    "area-arm": "arm",
    "area-stay": "stay",
    "area-sleep": "sleep",
    "area-disarm": "disarm",
}
_activity_cache: dict[str, Any] = {"at": 0.0, "data": None, "last_key": "", "seq": 0}
_ACTIVITY_TTL_SEC = 8.0
_EVENTS_POLL_SEC = 3.0
_SAST = timezone(timedelta(hours=2))
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ZONE_EVENT_ACTIONS = {"zone", "zone_watch"}
AREA_EVENT_ACTIONS = {"area"}
ALARM_EVENT_ACTIONS = {"zone_alarm", "s_alm", "s_alm_f", "s_alm_m"}
NOISE_EVENT_ACTIONS = {"zones_idle", "device", "heartbeat"}
POWER_EVENT_ACTIONS = {"power", "ac", "mains", "battery"}
ALARM_EVENT_STATES = {"alarm", "emergency", "panic", "fire", "medical"}

HANSEKOP_ID = "0bb544db-30b0-453d-bf39-d323538ebd5e"
KEYPAD_CODES = {
    "7302": {"name": "Marc", "from": "Pingoa"},
    "7102": {"name": "Amoroc", "from": "Amoroc"},
    "7777": {"name": "Onguard", "from": "Onguard"},
    "2640": {"name": "Comnet", "from": "Comnet"},
}

# Tuya OpenAPI — TUYS keypad UI stays paused until tuya_probe() returns ok.
TUYA_DEFAULT_ENDPOINT = "https://openapi.tuyaeu.com"
TUYA_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
TUYA_MAINS_METER_ID = "bf90676b1341ecb34dse39"
TUYA_CODE_TOKEN_INVALID = 1010
TUYA_CODE_SIGN_INVALID = 1004
TUYA_CODE_PERMISSION = 1106
TUYA_CODE_SUBSCRIPTION = 28841002
TUYA_EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()
_tuya_http: httpx.Client | None = None
_tuya_http_lock = threading.Lock()
_tuya_token: dict[str, Any] | None = None

router = APIRouter()


def _arial_dir() -> Path:
    candidates = (
        _ROOT / "arial",
        _ROOT / "sailingsa" / "frontend" / "arial",
        Path(os.getenv("STATIC_DIR") or "") / "arial",
        _ROOT.parent / "arial",
    )
    for p in candidates:
        if p.is_dir() and (p / "index.html").is_file():
            return p
    return _ROOT / "arial"


def _olarm_token() -> str:
    tok = (os.getenv("OLARM_API_TOKEN") or os.getenv("ARIAL_OLARM_TOKEN") or "").strip()
    if tok.startswith("api_") or len(tok) > 20:
        return tok
    env_path = _ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("OLARM_API_TOKEN", "ARIAL_OLARM_TOKEN"):
                tok = v.strip().strip('"').strip("'")
                if tok:
                    return tok
    return tok


def _dotenv_map() -> dict[str, str]:
    env_path = _ROOT / ".env"
    out: dict[str, str] = {}
    if not env_path.is_file():
        return out
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _env_first(*names: str) -> str:
    for name in names:
        v = (os.getenv(name) or "").strip().strip('"').strip("'")
        if v:
            return v
    dotenv = _dotenv_map()
    for name in names:
        v = (dotenv.get(name) or "").strip()
        if v:
            return v
    return ""


def tuya_endpoint_for_region(region: str) -> str:
    key = (region or "eu").strip().lower()
    if key in ("central europe", "centraleurope", "eu", "europe"):
        key = "eu"
    return TUYA_ENDPOINTS.get(key, TUYA_DEFAULT_ENDPOINT)


def _tuya_creds() -> dict[str, str]:
    endpoint = _env_first("TUYA_ENDPOINT")
    if not endpoint:
        endpoint = tuya_endpoint_for_region(_env_first("TUYA_REGION") or "eu")
    return {
        "client_id": _env_first("TUYA_CLIENT_ID", "TUYA_ACCESS_ID"),
        "secret": _env_first("TUYA_SECRET", "TUYA_ACCESS_KEY", "TUYA_CLIENT_SECRET"),
        "endpoint": endpoint.rstrip("/"),
        "device_id": _env_first("TUYA_DEVICE_ID") or TUYA_MAINS_METER_ID,
    }


def tuya_configured() -> bool:
    creds = _tuya_creds()
    return bool(creds["client_id"] and creds["secret"])


def tuya_str_to_sign(
    method: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
) -> str:
    """New Tuya OpenAPI string-to-sign (official tuya-connector-python)."""
    if body:
        content = json.dumps(body)
        content_sha = hashlib.sha256(content.encode("utf8")).hexdigest()
    else:
        content_sha = TUYA_EMPTY_BODY_SHA256
    signed = f"{method.upper()}\n{content_sha}\n\n{path}"
    if params:
        query = "&".join(f"{k}={params[k]}" for k in sorted(params))
        signed += "?" + query
    return signed


def tuya_sign(
    secret: str,
    client_id: str,
    t: int,
    str_to_sign: str,
    access_token: str = "",
) -> str:
    message = f"{client_id}{access_token or ''}{t}{str_to_sign}"
    return hmac.new(secret.encode("utf8"), message.encode("utf8"), hashlib.sha256).hexdigest().upper()


def tuya_sign_access_token(path: str, cached_access: str) -> str:
    """Token get/refresh must HMAC without a (possibly dead) access_token."""
    if path.startswith("/v1.0/token"):
        return ""
    return cached_access or ""


def _tuya_reset_token() -> None:
    global _tuya_token
    _tuya_token = None


def _tuya_sync_client(endpoint: str) -> httpx.Client:
    global _tuya_http
    base = endpoint.rstrip("/")
    current = ""
    if _tuya_http is not None and not _tuya_http.is_closed:
        current = str(_tuya_http.base_url).rstrip("/")
    if _tuya_http is None or _tuya_http.is_closed or current != base:
        if _tuya_http is not None:
            try:
                _tuya_http.close()
            except Exception:
                pass
        _tuya_http = httpx.Client(base_url=base, timeout=20.0)
    return _tuya_http


def _tuya_send(
    method: str,
    endpoint: str,
    path: str,
    headers: dict[str, str],
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    client = _tuya_sync_client(endpoint)
    resp = client.request(method, path, headers=headers, params=params)
    try:
        data = resp.json()
    except Exception:
        data = {"success": False, "code": resp.status_code, "msg": (resp.text or "")[:240]}
    if not isinstance(data, dict):
        return {"success": False, "msg": "non-object tuya response"}
    return data


def _tuya_call(
    method: str,
    path: str,
    *,
    creds: dict[str, str],
    params: Optional[dict[str, Any]] = None,
    access_token: str = "",
) -> dict[str, Any]:
    t = int(time.time() * 1000)
    token_for_sign = tuya_sign_access_token(path, access_token)
    sign = tuya_sign(
        creds["secret"],
        creds["client_id"],
        t,
        tuya_str_to_sign(method, path, params),
        access_token=token_for_sign,
    )
    headers = {
        "client_id": creds["client_id"],
        "sign": sign,
        "sign_method": "HMAC-SHA256",
        "t": str(t),
        "lang": "en",
        "access_token": token_for_sign,
    }
    return _tuya_send(method, creds["endpoint"], path, headers, params)


def _tuya_store_token(payload: dict[str, Any]) -> dict[str, Any] | None:
    global _tuya_token
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    access = str(result.get("access_token") or "")
    if not payload.get("success") or not access:
        return None
    expire_sec = int(result.get("expire") or result.get("expire_time") or 7200)
    server_t = int(payload.get("t") or int(time.time() * 1000))
    _tuya_token = {
        "access_token": access,
        "refresh_token": str(result.get("refresh_token") or ""),
        "uid": str(result.get("uid") or ""),
        "expire_at_ms": server_t + expire_sec * 1000,
    }
    return _tuya_token


def _tuya_connect(creds: dict[str, str]) -> dict[str, Any]:
    payload = _tuya_call("GET", "/v1.0/token", creds=creds, params={"grant_type": 1}, access_token="")
    stored = _tuya_store_token(payload)
    if stored is None:
        return payload
    return payload


def _tuya_refresh(creds: dict[str, str]) -> dict[str, Any]:
    cached = _tuya_token or {}
    refresh = str(cached.get("refresh_token") or "")
    if not refresh:
        return _tuya_connect(creds)
    # Official SDK clears access_token before refresh so HMAC does not use a dead token.
    payload = _tuya_call("GET", f"/v1.0/token/{refresh}", creds=creds, access_token="")
    stored = _tuya_store_token(payload)
    if stored is None:
        _tuya_reset_token()
        return _tuya_connect(creds)
    return payload


def _tuya_ensure_token(creds: dict[str, str]) -> dict[str, Any]:
    cached = _tuya_token
    now = int(time.time() * 1000)
    if not cached or not cached.get("access_token"):
        return _tuya_connect(creds)
    expire_at = int(cached.get("expire_at_ms") or 0)
    if expire_at - 60_000 <= now:
        return _tuya_refresh(creds)
    return {"success": True, "result": cached}


def _tuya_device_status(creds: dict[str, str], device_id: str) -> dict[str, Any]:
    token_payload = _tuya_ensure_token(creds)
    access = ""
    if _tuya_token:
        access = str(_tuya_token.get("access_token") or "")
    if not access:
        return token_payload
    payload = _tuya_call(
        "GET",
        f"/v1.0/devices/{device_id}/status",
        creds=creds,
        access_token=access,
    )
    if int(payload.get("code") or 0) == TUYA_CODE_TOKEN_INVALID:
        # Fresh simple token, never HMAC-refresh with the dead access_token.
        _tuya_reset_token()
        token_payload = _tuya_connect(creds)
        access = str((_tuya_token or {}).get("access_token") or "")
        if not access:
            return token_payload
        payload = _tuya_call(
            "GET",
            f"/v1.0/devices/{device_id}/status",
            creds=creds,
            access_token=access,
        )
    return payload


def _tuya_hint(code: Any, msg: str, *, token_ok: bool, device_ok: bool) -> str:
    n = int(code or 0) if str(code or "").lstrip("-").isdigit() else 0
    text = (msg or "").lower()
    if not token_ok and n == TUYA_CODE_SIGN_INVALID:
        return "Sign invalid (1004): clock skew, wrong secret, or old HMAC. Server time must be NTP-synced; use the new METHOD+SHA256 signature."
    if token_ok and not device_ok and (n == TUYA_CODE_TOKEN_INVALID or "token invalid" in text or "token is expired" in text):
        return (
            "Token mint succeeded but device /status returned 1010. That is the usual IoT Core trial-expiry "
            "response, not a dead HMAC. On iot.tuya.com: Cloud → Cloud Services → IoT Core → Extend Trial Period "
            "(https://iot.tuya.com/cloud/products/apply-extension). If the form errors, Back then Extend again. "
            "After approval: Devices → Link Tuya App Account → unlink Smart Life then relink (Central Europe). "
            "Also check the project IP allowlist includes 102.218.215.253 or is empty."
        )
    if n == TUYA_CODE_SUBSCRIPTION or "subscription" in text:
        return "IoT Core / cloud development subscription expired (28841002). Extend the trial, then unlink/relink Smart Life."
    if n == TUYA_CODE_PERMISSION:
        return "Permission deny (1106): device is not linked to this cloud project, or the datacenter is wrong (use openapi.tuyaeu.com for Central Europe)."
    if not token_ok:
        return "Could not mint a Tuya access token. Check TUYA_CLIENT_ID / TUYA_SECRET and TUYA_REGION=eu."
    if device_ok:
        return ""
    return msg or "Tuya device status failed."


def tuya_probe(device_id: str | None = None) -> dict[str, Any]:
    """On-demand OpenAPI probe. Does not start meter polling or unpause TUYS UI."""
    creds = _tuya_creds()
    out: dict[str, Any] = {
        "ok": False,
        "configured": bool(creds["client_id"] and creds["secret"]),
        "paused": True,
        "endpoint": creds["endpoint"],
        "deviceId": (device_id or creds["device_id"]).strip() or TUYA_MAINS_METER_ID,
        "tokenOk": False,
        "deviceOk": False,
        "tuyaCode": None,
        "tuyaMsg": "",
        "hint": "",
        "status": None,
    }
    if not out["configured"]:
        out["hint"] = (
            "TUYA_CLIENT_ID / TUYA_SECRET are not set. Put them in the live process env (never git), "
            "then GET /api/arial/tuya/probe. TUYS UI stays paused until this probe returns ok."
        )
        return out
    try:
        with _tuya_http_lock:
            _tuya_reset_token()
            token_payload = _tuya_ensure_token(creds)
            out["tuyaCode"] = token_payload.get("code")
            out["tuyaMsg"] = str(token_payload.get("msg") or "")
            if not token_payload.get("success") or not (_tuya_token or {}).get("access_token"):
                out["hint"] = _tuya_hint(out["tuyaCode"], out["tuyaMsg"], token_ok=False, device_ok=False)
                return out
            out["tokenOk"] = True
            expire_at = int((_tuya_token or {}).get("expire_at_ms") or 0)
            out["tokenExpireAtMs"] = expire_at
            status_payload = _tuya_device_status(creds, out["deviceId"])
            out["tuyaCode"] = status_payload.get("code")
            out["tuyaMsg"] = str(status_payload.get("msg") or "")
            if status_payload.get("success"):
                out["deviceOk"] = True
                out["ok"] = True
                result = status_payload.get("result")
                out["status"] = result if isinstance(result, list) else result
                out["dpsCount"] = len(result) if isinstance(result, list) else None
                if isinstance(result, list):
                    _energy_note_recent(out["deviceId"], result, time.time())
                    _energy_record_sample(out["deviceId"], result)
                _ensure_energy_sampler(out["deviceId"])
            else:
                out["hint"] = _tuya_hint(out["tuyaCode"], out["tuyaMsg"], token_ok=True, device_ok=False)
                return out
            out["hint"] = ""
            return out
    except httpx.HTTPError as exc:
        out["tuyaMsg"] = str(exc)
        out["hint"] = f"Tuya OpenAPI unreachable: {exc}"
        return out


# ---------------------------------------------------------------------------
# Hourly energy (kWh x 24) for the breaker card. Two real sources only:
#   1. Tuya statistics API (hours of add_ele) when the project has it enabled.
#   2. Bins integrated from live cur_power samples taken on every probe.
# Never synthesise history; missing hours stay null.
# ---------------------------------------------------------------------------
ENERGY_DAYS = 3
_ENERGY_MAX_GAP_S = 180.0
_energy_lock = threading.Lock()
_energy_bins: dict[str, dict[str, float]] = {}
_energy_last: dict[str, tuple[float, float]] = {}
_energy_loaded = False
_energy_stats_cache: dict[str, Any] = {"at": 0.0, "device": "", "days": None}


def _energy_log_candidates() -> list[Path]:
    env = (os.getenv("ARIAL_ENERGY_LOG") or "").strip()
    if env:
        return [Path(env)]
    return [
        Path("/var/www/sailingsa/data/arial_energy_bins.json"),
        _DATA_DIR / "arial_energy_bins.json",
        Path("/var/tmp/arial_energy_bins.json"),
        Path("/tmp/arial_energy_bins.json"),
    ]


_energy_mtime = 0.0
_energy_recent: dict[str, list[tuple[float, float]]] = {}
_power_state: dict[str, Any] = {"loaded": False, "online": None, "acOk": None, "offSince": None, "restoreAt": None, "outages": []}
_POWER_KEYS = ("online", "acOk", "offSince", "restoreAt", "outages")


def _energy_store_path() -> Path:
    for path in _energy_log_candidates():
        if path.is_file():
            return path
    return _energy_log_candidates()[0]


def _energy_merge_disk(data: Any) -> None:
    """Fold a store payload from disk into memory (max per hour bin; union of outages; newest restore)."""
    if not isinstance(data, dict):
        return
    bins = data.get("bins") if isinstance(data.get("bins"), dict) else {}
    for dev, hours in bins.items():
        if not isinstance(hours, dict):
            continue
        mine = _energy_bins.setdefault(str(dev), {})
        for h, v in hours.items():
            if isinstance(v, (int, float)):
                mine[str(h)] = max(float(v), float(mine.get(str(h)) or 0.0))
    recent = data.get("recent") if isinstance(data.get("recent"), dict) else {}
    for dev, rows in recent.items():
        if not isinstance(rows, list):
            continue
        merged = {round(float(t), 3): (float(t), float(w)) for t, w in _energy_recent.get(str(dev), [])}
        for row in rows:
            if isinstance(row, list) and len(row) == 2:
                try:
                    merged[round(float(row[0]), 3)] = (float(row[0]), float(row[1]))
                except (TypeError, ValueError):
                    continue
        _energy_recent[str(dev)] = [merged[k] for k in sorted(merged)][-_RECENT_N:]
    saved = data.get("power") if isinstance(data.get("power"), dict) else None
    if isinstance(saved, dict):
        for key in ("online", "acOk", "offSince"):
            if _power_state.get(key) is None and saved.get(key) is not None:
                _power_state[key] = saved.get(key)
        outs = {round(float(o.get("to") or 0)): o for o in (_power_state.get("outages") or []) if isinstance(o, dict)}
        for o in saved.get("outages") or []:
            if isinstance(o, dict) and o.get("to"):
                outs.setdefault(round(float(o["to"])), o)
        _power_state["outages"] = [outs[k] for k in sorted(outs)][-50:]
        mine_r = _power_state.get("restoreAt")
        theirs_r = saved.get("restoreAt")
        if theirs_r is not None and (mine_r is None or float(theirs_r) > float(mine_r)):
            _power_state["restoreAt"] = theirs_r
    _power_state["loaded"] = True


def _energy_load() -> None:
    """(Re)load the shared store when another worker has written it. Caller holds _energy_lock."""
    global _energy_loaded, _energy_mtime
    path = _energy_store_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _energy_loaded = True
        _power_state["loaded"] = True
        return
    if _energy_loaded and mtime == _energy_mtime:
        return
    try:
        with open(_flock_path(path), "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_SH)
            data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _energy_loaded = True
        return
    _energy_merge_disk(data)
    _energy_loaded = True
    _energy_mtime = mtime


def _power_load() -> None:
    _energy_load()


def _energy_save() -> None:
    """Merge with what is on disk, then write. Caller holds _energy_lock."""
    global _energy_mtime
    path = _energy_store_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(_flock_path(path), "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                _energy_merge_disk(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass
            payload = {
                "bins": _energy_bins,
                "recent": {dev: [[t, w] for t, w in rows] for dev, rows in _energy_recent.items()},
                "power": {k: _power_state[k] for k in _POWER_KEYS},
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            _energy_mtime = path.stat().st_mtime
    except OSError:
        return


def _scale_power_w(raw: Any) -> float | None:
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return None
    if n > 20000:
        return n / 100.0
    if n > 5000:
        return n / 10.0
    return n


def _sa_hour_key(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(_SAST).strftime("%Y%m%d%H")


def _energy_prune(device: str, now: float) -> None:
    keep_from = (datetime.fromtimestamp(now, tz=timezone.utc).astimezone(_SAST) - timedelta(days=ENERGY_DAYS + 1)).strftime("%Y%m%d%H")
    hours = _energy_bins.get(device) or {}
    for key in [k for k in hours if k < keep_from]:
        hours.pop(key, None)


def _energy_record_sample(device: str, status: list[Any], now: float | None = None) -> None:
    """Integrate cur_power (W) between consecutive probes into SA-local hourly kWh bins."""
    power = None
    for row in status or []:
        if isinstance(row, dict) and row.get("code") == "cur_power":
            power = _scale_power_w(row.get("value"))
    if power is None:
        return
    ts = float(now if now is not None else time.time())
    with _energy_lock:
        _energy_load()
        prev = _energy_last.get(device)
        _energy_last[device] = (ts, power)
        if not prev:
            return
        prev_ts, prev_w = prev
        dt = ts - prev_ts
        if dt <= 0 or dt > _ENERGY_MAX_GAP_S:
            return
        # Trapezoid over the interval, split at hour boundaries so each bin is exact.
        avg_w = (prev_w + power) / 2.0
        hours = _energy_bins.setdefault(device, {})
        cur = prev_ts
        while cur < ts:
            local = datetime.fromtimestamp(cur, tz=timezone.utc).astimezone(_SAST)
            hour_end = (local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).timestamp()
            seg_end = min(ts, hour_end)
            key = _sa_hour_key(cur)
            hours[key] = round(hours.get(key, 0.0) + avg_w * (seg_end - cur) / 3_600_000.0, 6)
            cur = seg_end
        _energy_prune(device, ts)
        _energy_save()


def _energy_days_from_bins(device: str, now: float | None = None) -> list[dict[str, Any]]:
    ts = float(now if now is not None else time.time())
    with _energy_lock:
        _energy_load()
        hours = dict(_energy_bins.get(device) or {})
    return _energy_shape_days(hours, ts)


def _energy_shape_days(hours: dict[str, float], ts: float) -> list[dict[str, Any]]:
    local_now = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(_SAST)
    days: list[dict[str, Any]] = []
    for back in range(ENERGY_DAYS):
        day = (local_now - timedelta(days=back)).replace(hour=0, minute=0, second=0, microsecond=0)
        ymd = day.strftime("%Y%m%d")
        vals: list[float | None] = []
        for h in range(24):
            key = f"{ymd}{h:02d}"
            v = hours.get(key)
            vals.append(round(float(v), 3) if isinstance(v, (int, float)) else None)
        have = [v for v in vals if v is not None]
        days.append(
            {
                "ymd": day.strftime("%Y-%m-%d"),
                "label": "Today" if back == 0 else ("Yesterday" if back == 1 else day.strftime("%a %d %b")),
                "hours": vals,
                "totalKwh": round(sum(have), 3) if have else None,
                "hoursWithData": len(have),
                "partial": back == 0,
            }
        )
    return days


def _tuya_statistics_hours(creds: dict[str, str], device: str, ts: float) -> dict[str, float] | None:
    """Tuya 'statistics by hour' for add_ele. Returns None if the API is not enabled or fails."""
    access = str((_tuya_token or {}).get("access_token") or "")
    if not access:
        return None
    local_now = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(_SAST)
    start = (local_now - timedelta(days=ENERGY_DAYS - 1)).replace(hour=0)
    payload = _tuya_call(
        "GET",
        f"/v1.0/devices/{device}/statistics/hours",
        creds=creds,
        params={"code": "add_ele", "start_hour": start.strftime("%Y%m%d%H"), "end_hour": local_now.strftime("%Y%m%d%H")},
        access_token=access,
    )
    if not payload.get("success"):
        return None
    result = payload.get("result")
    raw = result.get("hours") if isinstance(result, dict) else None
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, float] = {}
    for key, val in raw.items():
        try:
            n = float(val)
        except (TypeError, ValueError):
            continue
        out[str(key)] = n / 100.0 if n >= 100 else n
    return out or None


_energy_thread: threading.Thread | None = None
_ENERGY_SAMPLE_S = 60.0
_RECOVERY_S = 2 * 3600.0
_POWER_MIN_OUTAGE_S = 120.0
_RECENT_N = 30


def _power_mark(*, online: bool | None = None, ac_ok: bool | None = None, now: float | None = None) -> None:
    """Track mains loss/restore from the meter's online flag and the Olarm AC state."""
    ts = float(now if now is not None else time.time())
    with _energy_lock:
        _power_load()
        changed = False
        for key, val in (("online", online), ("acOk", ac_ok)):
            if val is None:
                continue
            prev = _power_state.get(key)
            if prev is val:
                continue
            _power_state[key] = val
            changed = True
            if prev is None:
                continue
            if val is False and _power_state.get("offSince") is None:
                _power_state["offSince"] = ts
            if val is True and _power_state.get("offSince") is not None:
                off = float(_power_state["offSince"])
                _power_state["offSince"] = None
                if ts - off < _POWER_MIN_OUTAGE_S:
                    continue  # blip / API restart, not a mains failure
                _power_state["restoreAt"] = ts
                _power_state["outages"] = (_power_state.get("outages") or [])[-49:] + [{"from": off, "to": ts}]
        if changed:
            _energy_save()


def _power_snapshot(now: float) -> dict[str, Any]:
    with _energy_lock:
        _power_load()
        restore = _power_state.get("restoreAt")
        out = {"restoreAt": restore, "online": _power_state.get("online"), "acOk": _power_state.get("acOk")}
    out["recovery"] = bool(restore) and (now - float(restore)) < _RECOVERY_S
    out["sinceRestoreS"] = int(now - float(restore)) if restore else None
    return out


def _tuya_device_detail(creds: dict[str, str], device: str) -> dict[str, Any]:
    token_payload = _tuya_ensure_token(creds)
    access = str((_tuya_token or {}).get("access_token") or "")
    if not access:
        return token_payload
    payload = _tuya_call("GET", f"/v1.0/devices/{device}", creds=creds, access_token=access)
    if int(payload.get("code") or 0) == TUYA_CODE_TOKEN_INVALID:
        _tuya_reset_token()
        _tuya_connect(creds)
        access = str((_tuya_token or {}).get("access_token") or "")
        if access:
            payload = _tuya_call("GET", f"/v1.0/devices/{device}", creds=creds, access_token=access)
    return payload


def _energy_note_recent(device: str, status: list[Any], now: float) -> None:
    for row in status or []:
        if isinstance(row, dict) and row.get("code") == "cur_power":
            w = _scale_power_w(row.get("value"))
            if w is None:
                return
            with _energy_lock:
                _energy_load()
                rec = _energy_recent.setdefault(device, [])
                rec.append((now, w))
                del rec[:-_RECENT_N]
            return


def _tuya_logs(creds: dict[str, str], device: str, *, types: str, start_ms: int, end_ms: int, codes: str = "", max_pages: int = 60) -> list[dict[str, Any]]:
    """Page through GET /v1.0/devices/{id}/logs (newest first). Returns raw rows."""
    access = str((_tuya_token or {}).get("access_token") or "")
    if not access:
        _tuya_ensure_token(creds)
        access = str((_tuya_token or {}).get("access_token") or "")
    if not access:
        return []
    rows: list[dict[str, Any]] = []
    row_key = ""
    for _ in range(max_pages):
        params: dict[str, Any] = {"type": types, "start_time": start_ms, "end_time": end_ms, "size": "100"}
        if codes:
            params["codes"] = codes
        if row_key:
            params["start_row_key"] = row_key
        payload = _tuya_call("GET", f"/v1.0/devices/{device}/logs", creds=creds, params=params, access_token=access)
        if not payload.get("success"):
            break
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        rows.extend(r for r in (result.get("logs") or []) if isinstance(r, dict))
        if not result.get("has_next") or not result.get("current_row_key"):
            break
        row_key = str(result.get("current_row_key"))
    return rows


_LIFECYCLE_ONLINE, _LIFECYCLE_OFFLINE, _LIFECYCLE_RESTART = 1, 2, 9
_POWER_LOG_GAP_S = 600.0


def _outages_from_lifecycle(rows: list[dict[str, Any]]) -> list[dict[str, float]]:
    """Mains outages = offline→online gaps ≥10 min, or any online followed by a device restart (power-on boot)."""
    events = sorted(
        ((int(r.get("event_time") or 0) / 1000.0, int(r.get("event_id") or 0)) for r in rows if r.get("event_time")),
        key=lambda x: x[0],
    )
    outages: list[dict[str, float]] = []
    off_since: float | None = None
    last_online: float | None = None
    for ts, kind in events:
        if kind == _LIFECYCLE_OFFLINE:
            if off_since is None:
                off_since = ts
        elif kind == _LIFECYCLE_ONLINE:
            if off_since is not None and ts - off_since >= _POWER_LOG_GAP_S:
                outages.append({"from": off_since, "to": ts})
            off_since = None
            last_online = ts
        elif kind == _LIFECYCLE_RESTART:
            if last_online is not None and ts - last_online <= 120 and not any(abs(o["to"] - last_online) < 1 for o in outages):
                outages.append({"from": off_since if off_since is not None else last_online, "to": last_online})
            off_since = None
    outages.sort(key=lambda o: o["to"])
    return outages


def _power_sync_from_logs(creds: dict[str, str], device: str, days: int = 7) -> dict[str, Any]:
    end_ms = int(time.time() * 1000)
    rows = _tuya_logs(creds, device, types="1,2,9", start_ms=end_ms - days * 86_400_000, end_ms=end_ms, max_pages=10)
    outages = _outages_from_lifecycle(rows)
    if not rows:
        return {"rows": 0, "outages": 0}
    with _energy_lock:
        _power_load()
        merged = {round(o["to"]): o for o in (_power_state.get("outages") or []) if isinstance(o, dict)}
        for o in outages:
            merged[round(o["to"])] = o
        ordered = [merged[k] for k in sorted(merged)][-50:]
        _power_state["outages"] = ordered
        if ordered:
            _power_state["restoreAt"] = max(float(o["to"]) for o in ordered)
        _energy_save()
    return {"rows": len(rows), "outages": len(outages)}


def _energy_backfill_from_logs(creds: dict[str, str], device: str, start_ts: float, end_ts: float | None = None) -> dict[str, Any]:
    """Rebuild hourly bins in [start, end) from Tuya's cur_power report log (real readings, trapezoid-integrated)."""
    end_ts = float(end_ts if end_ts is not None else time.time())
    # Tuya caps a single log query (~3000 rows); walk hour-sized windows so nothing is dropped.
    rows: list[dict[str, Any]] = []
    win = float(start_ts)
    while win < end_ts:
        nxt = min(end_ts, win + 3600.0)
        rows.extend(_tuya_logs(creds, device, types="7", codes="cur_power", start_ms=int(win * 1000), end_ms=int(nxt * 1000), max_pages=40))
        win = nxt
    samples = sorted(
        ((int(r.get("event_time")) / 1000.0, _scale_power_w(r.get("value"))) for r in rows if r.get("event_time")),
        key=lambda x: x[0],
    )
    samples = [(t, w) for t, w in samples if w is not None]
    if len(samples) < 2:
        return {"rows": len(rows), "hours": 0}
    hours: dict[str, float] = {}
    for (t0, w0), (t1, w1) in zip(samples, samples[1:]):
        dt = t1 - t0
        if dt <= 0 or dt > _ENERGY_MAX_GAP_S:
            continue
        avg_w = (w0 + w1) / 2.0
        cur = t0
        while cur < t1:
            local = datetime.fromtimestamp(cur, tz=timezone.utc).astimezone(_SAST)
            hour_end = (local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).timestamp()
            seg_end = min(t1, hour_end)
            key = _sa_hour_key(cur)
            hours[key] = hours.get(key, 0.0) + avg_w * (seg_end - cur) / 3_600_000.0
            cur = seg_end
    with _energy_lock:
        _energy_load()
        bins = _energy_bins.setdefault(device, {})
        for key, val in hours.items():
            # The log covers the whole hour; our sampler may only have part of it. Keep the larger real total.
            bins[key] = round(max(val, float(bins.get(key) or 0.0)), 6)
        _energy_save()
    return {"rows": len(rows), "hours": len(hours), "first": samples[0][0], "last": samples[-1][0]}


_power_sync_at = 0.0


def _energy_bootstrap(device: str) -> None:
    """On start: restores from 7 days of lifecycle log, and refill the last 24 h of bins from power reports."""
    global _power_sync_at
    creds = _tuya_creds()
    if not (creds["client_id"] and creds["secret"]):
        return
    with _tuya_http_lock:
        _power_sync_from_logs(creds, device, days=7)
        _power_sync_at = time.time()
        restore = _power_snapshot(time.time()).get("restoreAt")
        since = max(time.time() - ENERGY_DAYS * 86_400, float(restore) if restore else 0.0)
        _energy_backfill_from_logs(creds, device, since)


def _energy_sampler_loop(device: str) -> None:
    global _power_sync_at
    try:
        _energy_bootstrap(device)
    except Exception:
        pass
    while True:
        time.sleep(_ENERGY_SAMPLE_S)
        try:
            creds = _tuya_creds()
            if not (creds["client_id"] and creds["secret"]):
                continue
            if time.time() - _power_sync_at >= 600:
                _power_sync_at = time.time()
                with _tuya_http_lock:
                    _power_sync_from_logs(creds, device, days=2)
            panel = _stale_panel() or {}
            ac = (panel.get("arialPower") or {}).get("acOk") if isinstance(panel.get("arialPower"), dict) else None
            if isinstance(ac, bool):
                _power_mark(ac_ok=ac)
            with _tuya_http_lock:
                payload = _tuya_device_detail(creds, device)
            if not payload.get("success"):
                continue
            result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
            online = result.get("online")
            if isinstance(online, bool):
                _power_mark(online=online)
                if not online:
                    _energy_last.pop(device, None)
                    continue
            status = result.get("status")
            if isinstance(status, list):
                now = time.time()
                _energy_note_recent(device, status, now)
                _energy_record_sample(device, status, now=now)
        except Exception:
            continue


def _energy_analysis(device: str, days: list[dict[str, Any]], now: float) -> dict[str, Any]:
    """Baseline kW from earlier days vs the last ~30 min, ignoring recovery windows after restores."""
    with _energy_lock:
        _power_load()
        outages = list(_power_state.get("outages") or [])
        recent = list(_energy_recent.get(device) or [])
    def in_recovery(hour_key: str) -> bool:
        try:
            start = datetime.strptime(hour_key, "%Y%m%d%H").replace(tzinfo=_SAST).timestamp()
        except ValueError:
            return False
        for o in outages:
            to = float(o.get("to") or 0)
            if to and start - _RECOVERY_S < to and start + 3600 > to - 60:
                return True
        return False
    base_vals: list[float] = []
    day_totals: list[float] = []
    for day in days[1:]:
        ymd = str(day.get("ymd") or "").replace("-", "")
        hours = day.get("hours") or []
        for h, v in enumerate(hours):
            if v is None:
                continue
            if in_recovery(f"{ymd}{h:02d}"):
                continue
            base_vals.append(float(v))
        if int(day.get("hoursWithData") or 0) >= 20 and day.get("totalKwh") is not None:
            day_totals.append(float(day["totalKwh"]))
    baseline_kw = round(sum(base_vals) / len(base_vals), 3) if len(base_vals) >= 6 else None
    recent_w = [w for t, w in recent if now - t <= 1800]
    recent_kw = round(sum(recent_w) / len(recent_w) / 1000.0, 3) if recent_w else None
    power = _power_snapshot(now)
    flag = "learning"
    delta = None
    if power["recovery"]:
        flag = "recovery"
    elif baseline_kw and recent_kw is not None and baseline_kw > 0:
        delta = round((recent_kw / baseline_kw - 1.0) * 100.0)
        flag = "check" if recent_kw >= baseline_kw * 1.5 else ("above" if recent_kw >= baseline_kw * 1.25 else "normal")
    return {
        "baselineKw": baseline_kw,
        "recentKw": recent_kw,
        "deltaPct": delta,
        "flag": flag,
        "avgDayKwh": round(sum(day_totals) / len(day_totals), 3) if day_totals else None,
        "power": power,
    }


_energy_sampler_lockf = None
_energy_sampler_checked_at = 0.0


def _ensure_energy_sampler(device: str) -> None:
    """Keep hourly bins filling even when nobody has the card open. One sampler across all uvicorn workers."""
    global _energy_thread, _energy_sampler_lockf, _energy_sampler_checked_at
    if _energy_thread is not None and _energy_thread.is_alive():
        return
    if os.getenv("ARIAL_ENERGY_SAMPLER", "1").strip().lower() in {"0", "false", "no"}:
        return
    now = time.time()
    if now - _energy_sampler_checked_at < 30:
        return
    _energy_sampler_checked_at = now
    lock_path = Path(str(_energy_store_path()) + ".sampler.lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lockf = open(lock_path, "a+", encoding="utf-8")
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another worker owns the sampler
    _energy_sampler_lockf = lockf
    _energy_thread = threading.Thread(target=_energy_sampler_loop, args=(device,), name="arial-energy-sampler", daemon=True)
    _energy_thread.start()


def tuya_energy(device_id: str | None = None) -> dict[str, Any]:
    creds = _tuya_creds()
    device = (device_id or creds["device_id"]).strip() or TUYA_MAINS_METER_ID
    now = time.time()
    if creds["client_id"] and creds["secret"]:
        _ensure_energy_sampler(device)
    out: dict[str, Any] = {"ok": False, "deviceId": device, "tz": "Africa/Johannesburg", "source": "", "days": []}
    if not (creds["client_id"] and creds["secret"]):
        out["source"] = "none"
        return out
    stats: dict[str, float] | None = None
    cache = _energy_stats_cache
    if cache["device"] == device and cache["days"] is not None and now - float(cache["at"]) < 300:
        stats = cache["days"]
    else:
        try:
            with _tuya_http_lock:
                stats = _tuya_statistics_hours(creds, device, now)
        except httpx.HTTPError:
            stats = None
        _energy_stats_cache.update({"at": now, "device": device, "days": stats if stats else {}})
    if stats:
        out["source"] = "tuya-statistics"
        out["days"] = _energy_shape_days(stats, now)
    else:
        out["source"] = "sampled"
        out["days"] = _energy_days_from_bins(device, now)
    out.update(_energy_analysis(device, out["days"], now))
    out["ok"] = True
    return out


def _olarm_sync_client() -> httpx.Client:
    global _olarm_http
    tok = _olarm_token()
    if _olarm_http is None or _olarm_http.is_closed:
        _olarm_http = httpx.Client(
            base_url=OLARM_BASE,
            timeout=20.0,
            headers={"Content-Type": "application/json"},
            limits=httpx.Limits(max_keepalive_connections=4, max_connections=8, keepalive_expiry=90.0),
        )
    _olarm_http.headers["Authorization"] = f"Bearer {tok}" if tok else ""
    return _olarm_http


def _ensure_live_session() -> None:
    global _live_thread
    with _lock:
        if _live_thread is not None and _live_thread.is_alive():
            return
        _live_stop.clear()
        _live_thread = threading.Thread(target=_olarm_live_loop, name="arial-olarm-live", daemon=True)
        _live_thread.start()


def _olarm_live_loop() -> None:
    last_events_at = 0.0
    last_area_sig = ""
    while not _live_stop.wait(1.25):
        if not _olarm_token():
            continue
        try:
            now = time.time()
            events_resp = None
            area_changed = False
            with _olarm_http_lock:
                client = _olarm_sync_client()
                resp = client.get(
                    f"/api/v4/devices/{HANSEKOP_ID}",
                    params={"deviceApiAccessOnly": "1"},
                )
                if resp.status_code == 200:
                    raw = resp.json()
                    if isinstance(raw, dict):
                        panel = enrich_device(raw)
                        _cached_panel(panel)
                        sig = ",".join(
                            str(a.get("state") or "")
                            for a in (panel.get("arialAreas") or [])
                            if isinstance(a, dict)
                        )
                        if sig and sig != last_area_sig:
                            area_changed = last_area_sig != ""
                            last_area_sig = sig
                if area_changed or now - last_events_at >= _EVENTS_POLL_SEC:
                    events_resp = client.get(
                        f"/api/v4/devices/{HANSEKOP_ID}/events",
                        params={"limit": 80},
                    )
                    last_events_at = now
            if events_resp is not None and events_resp.status_code == 200:
                payload = events_resp.json()
                rows = payload.get("data") if isinstance(payload, dict) else []
                if isinstance(rows, list):
                    apply_olarm_events(rows, _stale_panel())
        except Exception:
            continue


def _hash_pw(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _load_store() -> dict[str, Any]:
    if not _USERS_PATH.is_file():
        return {"users": [], "sessions": {}}
    try:
        data = json.loads(_USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": [], "sessions": {}}
    data.setdefault("users", [])
    data.setdefault("sessions", {})
    return data


def _save_store(data: dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _USERS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_USERS_PATH)


def _public_user(u: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": u.get("id"),
        "email": u.get("email"),
        "display_name": u.get("display_name") or "",
        "phone": u.get("phone") or "",
        "notes": u.get("notes") or "",
        "created_at": u.get("created_at"),
    }


def _session_user(request: Request) -> Optional[dict[str, Any]]:
    token = request.cookies.get("arial_session") or ""
    if not token:
        return None
    with _lock:
        store = _load_store()
        uid = store.get("sessions", {}).get(token)
        if not uid:
            return None
        for u in store.get("users") or []:
            if u.get("id") == uid:
                return u
    return None


def require_user(request: Request) -> dict[str, Any]:
    u = _session_user(request)
    if not u:
        raise HTTPException(status_code=401, detail="Sign in required")
    return u


def _email_ok(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


async def _olarm_request(
    method: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
) -> Any:
    token = _olarm_token()
    if not token:
        raise HTTPException(status_code=503, detail="OLARM_API_TOKEN is not configured")
    url = path if path.startswith("http") else f"{OLARM_BASE}{path}"

    def _do() -> httpx.Response:
        with _olarm_http_lock:
            client = _olarm_sync_client()
            return client.request(method, url, params=params, json=json_body)

    try:
        resp = await asyncio.to_thread(_do)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Olarm unreachable: {exc}") from exc
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Olarm token expired")
    if resp.status_code == 403:
        raise HTTPException(status_code=403, detail="Olarm token is not allowed for this call")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Olarm device not found")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="Olarm rate limited")
    if resp.status_code >= 400:
        try:
            body = resp.json()
            msg = body.get("message") or body.get("error") or resp.text[:240]
        except Exception:
            msg = resp.text[:240]
        raise HTTPException(status_code=502, detail=f"Olarm error {resp.status_code}: {msg}")
    ctype = resp.headers.get("content-type") or ""
    if "application/json" in ctype:
        return resp.json()
    return {"raw": resp.text}


def enrich_device(device: dict[str, Any]) -> dict[str, Any]:
    """Attach display labels for areas and zones. Does not strip raw Olarm fields."""
    profile = device.get("deviceProfile") or {}
    state = device.get("deviceState") or {}
    area_labels = list(profile.get("areasLabels") or [])
    area_states = _as_list(state.get("areas"))
    area_details = _as_list(state.get("areasDetail"))
    area_stamps = _as_list(state.get("areasStamp"))
    areas = []
    countdown = None
    limit = int(profile.get("areasLimit") or max(len(area_labels), len(area_states), 0))
    for i in range(limit):
        label = (area_labels[i] if i < len(area_labels) else "") or f"Area {i + 1}"
        st = area_states[i] if i < len(area_states) else ""
        detail = area_details[i] if i < len(area_details) else ""
        stamp = area_stamps[i] if i < len(area_stamps) else None
        cd = _area_countdown(st, detail)
        if cd is not None and countdown is None:
            countdown = cd
        areas.append(
            {
                "num": i + 1,
                "label": label,
                "state": st,
                "detail": detail,
                "stamp": stamp,
                "countdown": cd,
            }
        )
    zone_labels = list(profile.get("zonesLabels") or [])
    zone_types = list(profile.get("zonesTypes") or [])
    zone_states = list(state.get("zones") or [])
    zlimit = int(profile.get("zonesLimit") or 0)
    zones = []
    for i in range(zlimit):
        label = (zone_labels[i] if i < len(zone_labels) else "") or ""
        if not str(label).strip():
            continue
        zt = zone_types[i] if i < len(zone_types) else 0
        zs = zone_states[i] if i < len(zone_states) else ""
        try:
            zt_int = int(zt)
        except (TypeError, ValueError):
            zt_int = 0
        zones.append(
            {
                "num": i + 1,
                "label": str(label).strip(),
                "type": zt_int,
                "typeLabel": ZONE_TYPE_LABEL.get(zt_int, "Unknown"),
                "state": zs,
                "stateLabel": ZONE_STATE_LABEL.get(str(zs), str(zs) or "—"),
            }
        )
    out = dict(device)
    out["arialAreas"] = areas
    out["arialZones"] = zones
    out["arialCountdown"] = countdown
    out["arialExitDelay"] = _profile_exit_delay(profile)
    out["arialPower"] = arial_power(state)
    if _last_keypad:
        out["arialActor"] = dict(_last_keypad)
    return out


def _power_ok(value: Any) -> bool:
    s = str(value or "").strip().lower()
    if s in ("", "ok", "1", "true", "on", "normal"):
        return True
    if s in ("fail", "failed", "fault", "problem", "low", "0", "false", "off", "error"):
        return False
    return s not in ("missing", "unknown")


def arial_power(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    nested = state.get("power") if isinstance(state.get("power"), dict) else {}
    ac = state.get("powerAC")
    if ac is None:
        ac = nested.get("AC", nested.get("ac"))
    batt = state.get("powerBattery")
    if batt is None:
        batt = nested.get("Batt", nested.get("battery"))
    ac_s = str(ac if ac is not None else "ok")
    batt_s = str(batt if batt is not None else "ok")
    return {
        "ac": ac_s,
        "battery": batt_s,
        "acOk": _power_ok(ac if ac is not None else "ok"),
        "batteryOk": _power_ok(batt if batt is not None else "ok"),
    }


def classify_olarm_event(event: dict[str, Any] | None) -> str:
    event = event or {}
    action = str(event.get("eventAction") or "").strip().lower()
    state = str(event.get("eventState") or "").strip().lower()
    msg = str(event.get("eventMsg") or "").strip().lower()
    if action in POWER_EVENT_ACTIONS or "power" in msg or "battery" in msg or "mains" in msg:
        return "power"
    if action in ALARM_EVENT_ACTIONS or state in {"emergency", "panic", "fire", "medical"} or "in alarm" in msg:
        return "zones"
    if action in AREA_EVENT_ACTIONS or state in {"arm", "disarm", "stay", "sleep", "countdown"} or "countdown" in msg:
        return "areas"
    if action in ZONE_EVENT_ACTIONS:
        return "zones"
    return "areas"


def is_noise_olarm_event(event: dict[str, Any] | None) -> bool:
    event = event or {}
    action = str(event.get("eventAction") or "").strip().lower()
    msg = str(event.get("eventMsg") or "").strip().lower()
    if action in NOISE_EVENT_ACTIONS:
        return True
    if "system idle" in msg or "idle for" in msg:
        return True
    if "olarm device" in msg and ("online" in msg or "offline" in msg):
        return True
    return False


def _sa_stamp(ms: Any) -> tuple[str, str]:
    try:
        n = int(ms)
        if n > 10_000_000_000:
            n = n / 1000.0
        dt = datetime.fromtimestamp(n, tz=timezone.utc).astimezone(_SAST)
    except (TypeError, ValueError, OSError, OverflowError):
        dt = datetime.now(_SAST)
    return f"{dt.hour:02d}:{dt.minute:02d}", f"{dt.day:02d} {_MONTHS[dt.month - 1]} {dt.year}"


def _event_state_label(state: str) -> str:
    raw = str(state or "").strip()
    mapping = {
        "active": "ACTIVE",
        "closed": "CLOSED",
        "arm": "ARMED",
        "disarm": "DISARMED",
        "stay": "STAY ARMED",
        "sleep": "SLEEP ARMED",
        "alert": "",
        "alarm": "ALARM",
        "countdown": "COUNTDOWN",
        "emergency": "EMERGENCY",
        "panic": "PANIC",
        "fail": "FAILURE",
        "restore": "RESTORE",
        "low": "LOW",
    }
    return mapping.get(raw.lower(), raw.upper()) if raw else ""


def _event_time_ms(event: dict[str, Any] | None) -> int:
    try:
        n = int((event or {}).get("eventTime") or 0)
        if n and n < 10_000_000_000:
            n *= 1000
        return n
    except (TypeError, ValueError):
        return 0


def _keypad_log_candidates() -> list[Path]:
    env = (os.getenv("ARIAL_KEYPAD_LOG") or "").strip()
    if env:
        return [Path(env)]
    return [
        Path("/var/www/sailingsa/data/arial_keypad_log.json"),
        _DATA_DIR / "arial_keypad_log.json",
        Path("/var/tmp/arial_keypad_log.json"),
        Path("/tmp/arial_keypad_log.json"),
        _ROOT / "arial_keypad_log.json",
    ]


def _keypad_log_path() -> Path:
    for path in _keypad_log_candidates():
        if path.is_file():
            return path
    return _keypad_log_candidates()[0]


def _hansekop_area_label() -> str:
    panel = _stale_panel() or {}
    for area in panel.get("arialAreas") or []:
        if not isinstance(area, dict):
            continue
        label = str(area.get("label") or "").strip()
        if label:
            return label
    return "Facility Building"


def _compact_activity_text(*parts: Any) -> str:
    return "".join(str(p or "") for p in parts).lower().replace(" ", "").replace("_", "").replace("-", "")


def _is_skip_area_text(*parts: Any) -> bool:
    compact = _compact_activity_text(*parts)
    return "countdown" in compact or "notready" in compact


def _area_state_token(state: str) -> str:
    s = str(state or "").strip().lower()
    if s in {"arm", "stay", "sleep", "countdown", "disarm", "notready"}:
        return s
    if "disarm" in s:
        return "disarm"
    if _is_skip_area_text(s) and "countdown" in _compact_activity_text(s):
        return "countdown"
    if _is_skip_area_text(s):
        return "notready"
    if "stay" in s:
        return "stay"
    if "sleep" in s:
        return "sleep"
    if "arm" in s:
        return "arm"
    return s


def _map_our_actor(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if not s:
        return ""
    if "pingoa" in s or s == "marc":
        return "Pingoa"
    if "amoroc" in s:
        return "Amoroc"
    if "onguard" in s:
        return "Onguard"
    if "comnet" in s:
        return "Comnet"
    return ""


def is_skip_activity_event(event: dict[str, Any] | None) -> bool:
    event = event or {}
    if is_noise_olarm_event(event):
        return True
    return _is_skip_area_text(
        event.get("eventState"),
        event.get("state"),
        event.get("eventMsg"),
        event.get("activity"),
        event.get("title"),
        event.get("msg"),
    )


def _activity_via(actor: str) -> str:
    return "Remote" if str(actor or "").strip() in {"Pingoa", "Amoroc", "Onguard", "Comnet"} else ""


def _activity_line(label: str, state_lab: str, actor: str, via: str = "") -> str:
    label = str(label or "").strip()
    state_lab = str(state_lab or "").strip()
    text = label if not state_lab or state_lab.lower() in label.lower() else f"{label} {state_lab}"
    who = str(actor or "").strip()
    if who and who.lower() not in text.lower():
        text = f"{text} · {who}" if text else who
    src = str(via or "").strip() or _activity_via(who)
    if src and src.lower() not in text.lower():
        text = f"{text} · {src}" if text else src
    return text


def dedupe_area_activity(rows: list[Any]) -> list[dict[str, Any]]:
    """One ARMED per arm cycle (until a DISARMED). Drop countdown."""
    out: list[dict[str, Any]] = []
    armed: dict[str, bool] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        st = _area_state_token(str(row.get("state") or ""))
        title = str(row.get("title") or "").strip() or "_"
        if st in {"countdown", "notready"}:
            continue
        if st in {"arm", "stay", "sleep"}:
            if armed.get(title):
                continue
            armed[title] = True
        elif st == "disarm":
            armed[title] = False
        out.append(row)
    return out


def _flock_path(path: Path) -> Path:
    return Path(str(path) + ".lock")


def _load_keypad_log() -> None:
    global _keypad_log, _last_keypad, _keypad_log_mtime
    path = _keypad_log_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return
    if mtime == _keypad_log_mtime and _keypad_log:
        return
    lock_path = _flock_path(path)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_SH)
            data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, list):
        return
    rows = [dict(x) for x in data if isinstance(x, dict)]
    _keypad_log = rows[-_KEYPAD_LOG_MAX:]
    _keypad_log_mtime = mtime
    if _keypad_log:
        _last_keypad = dict(_keypad_log[-1])


def _save_keypad_log() -> None:
    global _keypad_log_mtime
    payload = json.dumps(_keypad_log[-_KEYPAD_LOG_MAX:])
    last_err: OSError | None = None
    for path in _keypad_log_candidates():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = _flock_path(path)
            with open(lock_path, "a+", encoding="utf-8") as lockf:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
                path.write_text(payload, encoding="utf-8")
            _keypad_log_mtime = path.stat().st_mtime
            return
        except OSError as exc:
            last_err = exc
            continue
    if last_err:
        pass


def _remember_keypad(code: str, cmd: str) -> dict[str, Any]:
    global _last_keypad
    _load_keypad_log()
    user = KEYPAD_CODES.get(code) or {}
    who = str(user.get("from") or user.get("name") or "").strip()
    _last_keypad = {
        "from": str(user.get("from") or ""),
        "name": str(user.get("name") or ""),
        "label": who,
        "code": code,
        "action": cmd,
        "area": _hansekop_area_label(),
        "at": time.time(),
    }
    _keypad_log.append(dict(_last_keypad))
    del _keypad_log[:-_KEYPAD_LOG_MAX]
    _save_keypad_log()
    return _last_keypad


def _arial_event_actor(tab: str, event: dict[str, Any], device: dict[str, Any] | None) -> str:
    """Credit the logged-in keypad user (Pingoa / Amoroc / Onguard / Comnet). Never Olarm userFullname."""
    if tab != "areas":
        return ""
    _load_keypad_log()
    state = _area_state_token(str(event.get("eventState") or event.get("state") or ""))
    want_arm = state in {"arm", "stay", "sleep", "countdown"}
    want_disarm = state == "disarm"
    if not want_arm and not want_disarm:
        return _map_our_actor(
            str(event.get("userFullname") or event.get("userName") or event.get("user") or "")
        )
    ev_ms = _event_time_ms(event)
    if not ev_ms:
        try:
            ev_ms = int(event.get("at") or 0)
            if ev_ms and ev_ms < 10_000_000_000:
                ev_ms *= 1000
        except (TypeError, ValueError):
            ev_ms = 0
    now_ms = int(time.time() * 1000)
    best: dict[str, Any] | None = None
    best_dt = None
    rows = list(_keypad_log)
    if device and isinstance(device.get("arialActor"), dict):
        rows.append(device["arialActor"])
    if _last_keypad:
        rows.append(_last_keypad)
    for row in reversed(rows):
        if not isinstance(row, dict):
            continue
        cmd = str(row.get("action") or "")
        if want_arm and cmd not in {"area-arm", "area-stay", "area-sleep"}:
            continue
        if want_disarm and cmd != "area-disarm":
            continue
        try:
            kp_ms = int(float(row.get("at") or 0) * 1000)
        except (TypeError, ValueError):
            kp_ms = 0
        if not kp_ms:
            continue
        point = ev_ms or now_ms
        dt = point - kp_ms
        if dt < -15_000 or dt > _KEYPAD_MATCH_MS:
            continue
        score = abs(dt)
        if best_dt is None or score < best_dt:
            best = row
            best_dt = score
    if best:
        label = _map_our_actor(str(best.get("from") or best.get("label") or best.get("name") or ""))
        if not label:
            label = str(best.get("from") or best.get("label") or "").strip()
        if label in {"Pingoa", "Amoroc", "Onguard", "Comnet"}:
            return label
    return _map_our_actor(
        str(event.get("userFullname") or event.get("userName") or event.get("user") or "")
    )


def _stamp_activity_actors(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        return {"ok": True, "power": {}, "events": [], "live": True}
    device = _stale_panel() if isinstance(_stale_panel(), dict) else None
    rows = [r for r in (bundle.get("events") or []) if isinstance(r, dict) and not is_skip_activity_event(r)]
    for row in rows:
        if str(row.get("tab") or "") != "areas":
            continue
        actor = _arial_event_actor(
            "areas",
            {
                "eventState": _area_state_token(str(row.get("state") or "")),
                "eventTime": row.get("at"),
                "at": row.get("at"),
            },
            device,
        )
        if not actor:
            continue
        row["actor"] = actor
        row["via"] = _activity_via(actor) or row.get("via") or ""
        row["activity"] = _activity_line(str(row.get("title") or ""), str(row.get("state") or ""), actor, str(row.get("via") or ""))
    have = []
    for row in rows:
        if str(row.get("tab") or "") != "areas":
            continue
        have.append((_area_state_token(str(row.get("state") or "")), _event_time_ms({"eventTime": row.get("at")})))
    _load_keypad_log()
    extras: list[dict[str, Any]] = []
    for rec in reversed(_keypad_log):
        state = _KEYPAD_CMD_STATE.get(str(rec.get("action") or ""))
        if not state:
            continue
        try:
            kp_ms = int(float(rec.get("at") or 0) * 1000)
        except (TypeError, ValueError):
            continue
        if not kp_ms:
            continue
        matched = False
        for ev_state, ev_ms in have:
            same = (state == "disarm" and ev_state == "disarm") or (
                state != "disarm" and ev_state in {"arm", "stay", "sleep"}
            )
            if same and ev_ms and abs(ev_ms - kp_ms) <= _KEYPAD_MATCH_MS:
                matched = True
                break
        if matched:
            continue
        actor = _map_our_actor(str(rec.get("from") or rec.get("label") or ""))
        if actor not in {"Pingoa", "Amoroc", "Onguard", "Comnet"}:
            continue
        label = str(rec.get("area") or "").strip() or _hansekop_area_label()
        state_lab = _event_state_label(state)
        extras.append(
            {
                "tab": "areas",
                "time": _sa_stamp(kp_ms)[0],
                "date": _sa_stamp(kp_ms)[1],
                "title": label,
                "state": state_lab,
                "activity": _activity_line(label, state_lab, actor, "Remote"),
                "actor": actor,
                "via": "Remote",
                "msg": "",
                "num": 1,
                "action": "area",
                "at": kp_ms,
            }
        )
        if len(extras) >= 8:
            break
    if extras:
        rows = extras + rows
        rows.sort(key=lambda r: int(r.get("at") or 0), reverse=True)
    bundle["events"] = dedupe_area_activity(rows)
    return bundle


def olarm_event_key(event: dict[str, Any] | None) -> str:
    event = event or {}
    return "|".join(
        [
            str(event.get("eventTime") or event.get("at") or ""),
            str(event.get("eventAction") or event.get("action") or event.get("tab") or ""),
            str(event.get("eventState") or event.get("state") or ""),
            str(event.get("eventNum") or event.get("num") or ""),
            str(event.get("eventMsg") or event.get("title") or "")[:80],
        ]
    )


def apply_olarm_events(events: list[Any], device: dict[str, Any] | None = None) -> str:
    """Poll result: ack if the newest Olarm record is unchanged, else insert."""
    rows = [e for e in events if isinstance(e, dict)]
    newest = ""
    best_t = -1
    for event in rows:
        t = _event_time_ms(event)
        if t >= best_t:
            best_t = t
            newest = olarm_event_key(event)
    with _lock:
        if newest and newest == str(_activity_cache.get("last_key") or "") and _activity_cache.get("data"):
            _activity_cache["at"] = time.time()
            data = _activity_cache.get("data")
            if isinstance(data, dict):
                data["ack"] = True
                data["lastKey"] = newest
            return "ack"
    bundle = _activity_bundle(device, rows)
    bundle["lastKey"] = newest
    bundle["ack"] = False
    with _lock:
        _activity_cache["data"] = bundle
        _activity_cache["at"] = time.time()
        _activity_cache["last_key"] = newest
        _activity_cache["seq"] = int(_activity_cache.get("seq") or 0) + 1
    return "insert" if newest else "empty"


def _activity_payload(bundle: dict[str, Any] | None, ack: bool) -> dict[str, Any]:
    out = _stamp_activity_actors(bundle if isinstance(bundle, dict) else {"ok": True, "events": [], "power": {}})
    with _lock:
        last_key = str(_activity_cache.get("last_key") or "")
    out["lastKey"] = last_key or out.get("lastKey") or ""
    events = out.get("events") if isinstance(out.get("events"), list) else []
    digest = hashlib.sha256("\n".join(olarm_event_key(e) for e in events if isinstance(e, dict)).encode("utf-8")).hexdigest()
    out["checksum"] = digest[:16]
    out["ack"] = ack
    out["ok"] = True
    return out


def format_olarm_event(event: dict[str, Any], device: dict[str, Any] | None = None) -> dict[str, Any]:
    device = device or {}
    zones = {int(z.get("num") or 0): z for z in (device.get("arialZones") or []) if isinstance(z, dict)}
    areas = {int(a.get("num") or 0): a for a in (device.get("arialAreas") or []) if isinstance(a, dict)}
    action = str(event.get("eventAction") or "")
    try:
        num = int(event.get("eventNum") or 0)
    except (TypeError, ValueError):
        num = 0
    tab = classify_olarm_event(event)
    msg = str(event.get("eventMsg") or "").strip()
    label = ""
    if tab in {"zones", "alarms"} and num in zones:
        label = str(zones[num].get("label") or "").strip()
    elif tab == "areas" and num in areas:
        label = str(areas[num].get("label") or "").strip()
    if not label and " - " in msg:
        label = msg.split(" - ")[-1].strip()
    if not label:
        label = msg or action or "Event"
    state_lab = _event_state_label(str(event.get("eventState") or ""))
    if tab == "power" and msg:
        label = msg
    time_s, date_s = _sa_stamp(event.get("eventTime"))
    actor = _arial_event_actor(tab, event, device)
    via = _activity_via(actor)
    activity = _activity_line(label, state_lab, actor, via)
    return {
        "tab": tab,
        "time": time_s,
        "date": date_s,
        "title": label,
        "state": state_lab,
        "activity": activity,
        "actor": actor,
        "via": via,
        "msg": msg,
        "num": num,
        "action": action,
        "at": event.get("eventTime"),
    }


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _countdown_int(value: Any) -> int | None:
    if value is None or value is True or value is False:
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        return n if 0 < n <= 180 else None
    if isinstance(value, dict):
        for key in ("time", "seconds", "countdown", "remaining", "exitDelay", "delay"):
            n = _countdown_int(value.get(key))
            if n:
                return n
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return _countdown_int(int(text))
    m = re.search(r"(\d{1,3})\s*(?:s|sec|secs|second|seconds)?\b", text, re.I)
    if m:
        return _countdown_int(int(m.group(1)))
    return None


def _profile_exit_delay(profile: dict[str, Any]) -> int:
    for key in ("exitDelay", "exitDelaySeconds", "areasExitDelay", "armDelay", "exitTime"):
        raw = profile.get(key)
        if isinstance(raw, list) and raw:
            raw = raw[0]
        n = _countdown_int(raw)
        if n and n > 10:
            return n
    return 60


def _looks_like_timer(detail: Any) -> bool:
    if isinstance(detail, bool) or detail is None:
        return False
    if isinstance(detail, (int, float, dict)):
        return True
    text = str(detail).strip().lower()
    if not text:
        return False
    if text.isdigit():
        return True
    return bool(re.search(r"(delay|exit|countdown|second|\d+\s*s\b)", text))


def _area_countdown(state: Any, detail: Any) -> int | None:
    st = str(state or "").strip().lower()
    if st == "countdown" or _looks_like_timer(detail):
        n = _countdown_int(detail)
        if n:
            return n
    text = f"{state or ''} {detail or ''}".strip().lower()
    if "countdown" in text or "exit delay" in text:
        return _countdown_int(text)
    return None


def _cookie_response(payload: dict[str, Any], session: Optional[str], clear: bool = False) -> JSONResponse:
    resp = JSONResponse(payload)
    if clear:
        resp.delete_cookie("arial_session", path="/")
        return resp
    if session:
        resp.set_cookie(
            "arial_session",
            session,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24 * 30,
        )
    return resp


def _cached_panel(device: dict[str, Any] | None = None, *, clear: bool = False) -> dict[str, Any] | None:
    with _lock:
        if clear:
            _panel_cache["data"] = None
            _panel_cache["at"] = 0.0
            return None
        if device is not None:
            _panel_cache["data"] = device
            _panel_cache["at"] = time.time()
            _panel_cache["seq"] = int(_panel_cache.get("seq") or 0) + 1
            return device
        cached = _panel_cache.get("data")
        if cached is not None and (time.time() - float(_panel_cache.get("at") or 0)) < _PANEL_TTL_SEC:
            return cached
        return None


def _stale_panel() -> dict[str, Any] | None:
    with _lock:
        data = _panel_cache.get("data")
        return data if isinstance(data, dict) else None


@router.get("/arial")
@router.get("/arial/")
def arial_index():
    path = _arial_dir() / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arial Dev page missing")
    return FileResponse(path, media_type="text/html")


@router.get("/arial/app.js")
def arial_js():
    path = _arial_dir() / "app.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="missing")
    return FileResponse(path, media_type="application/javascript")


@router.get("/arial/arial.css")
def arial_css():
    path = _arial_dir() / "arial.css"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="missing")
    return FileResponse(path, media_type="text/css")


@router.get("/arial/{asset_path:path}")
def arial_asset(asset_path: str):
    root = _arial_dir().resolve()
    path = (root / asset_path).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="missing")
    return FileResponse(path)


@router.get("/api/arial/status")
def arial_status(request: Request):
    user = _session_user(request)
    return {
        "ok": True,
        "dev": True,
        "olarmConfigured": bool(_olarm_token()),
        "tuyaConfigured": tuya_configured(),
        "tuyaPaused": True,
        "signedIn": bool(user),
        "me": _public_user(user) if user else None,
        "nextDomain": "arial.co.za",
    }


@router.get("/api/arial/tuya/probe")
def arial_tuya_probe(device_id: Optional[str] = None):
    """Mint a token and GET /v1.0/devices/{id}/status. Does not unpause TUYS UI."""
    return tuya_probe(device_id)


@router.get("/api/arial/tuya/energy")
def arial_tuya_energy(device_id: Optional[str] = None):
    """kWh x 24 for today, yesterday and the day before (SA time). Real data only."""
    return tuya_energy(device_id)


@router.post("/api/arial/auth/register")
async def arial_register(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    display_name = str(body.get("display_name") or "").strip()
    if not _email_ok(email):
        return JSONResponse({"ok": False, "error": "Valid email required"}, status_code=400)
    if len(password) < 6:
        return JSONResponse({"ok": False, "error": "Password must be at least 6 characters"}, status_code=400)
    if not display_name:
        display_name = email.split("@")[0]
    with _lock:
        store = _load_store()
        if any((u.get("email") or "").lower() == email for u in store["users"]):
            return JSONResponse({"ok": False, "error": "That email is already registered"}, status_code=409)
        salt = secrets.token_hex(8)
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "display_name": display_name,
            "phone": str(body.get("phone") or "").strip(),
            "notes": "",
            "password_salt": salt,
            "password_hash": _hash_pw(password, salt),
            "created_at": int(time.time()),
        }
        store["users"].append(user)
        session = secrets.token_urlsafe(32)
        store["sessions"][session] = user["id"]
        _save_store(store)
    return _cookie_response({"ok": True, "me": _public_user(user)}, session)


@router.post("/api/arial/auth/login")
async def arial_login(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    with _lock:
        store = _load_store()
        user = next((u for u in store["users"] if (u.get("email") or "").lower() == email), None)
        if not user:
            return JSONResponse({"ok": False, "error": "Invalid email or password"}, status_code=401)
        expected = user.get("password_hash")
        salt = user.get("password_salt") or ""
        if expected != _hash_pw(password, salt):
            return JSONResponse({"ok": False, "error": "Invalid email or password"}, status_code=401)
        session = secrets.token_urlsafe(32)
        store["sessions"][session] = user["id"]
        _save_store(store)
    return _cookie_response({"ok": True, "me": _public_user(user)}, session)


@router.post("/api/arial/auth/logout")
def arial_logout(request: Request):
    token = request.cookies.get("arial_session") or ""
    if token:
        with _lock:
            store = _load_store()
            store.get("sessions", {}).pop(token, None)
            _save_store(store)
    return _cookie_response({"ok": True}, None, clear=True)


@router.get("/api/arial/me")
def arial_me(request: Request):
    user = require_user(request)
    return {"ok": True, "me": _public_user(user)}


@router.put("/api/arial/me")
async def arial_me_update(request: Request):
    user = require_user(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    with _lock:
        store = _load_store()
        for u in store["users"]:
            if u.get("id") != user.get("id"):
                continue
            if "display_name" in body:
                u["display_name"] = str(body.get("display_name") or "").strip()
            if "phone" in body:
                u["phone"] = str(body.get("phone") or "").strip()
            if "notes" in body:
                u["notes"] = str(body.get("notes") or "").strip()[:2000]
            user = u
            break
        _save_store(store)
    return {"ok": True, "me": _public_user(user)}


@router.get("/api/arial/devices")
async def arial_devices(request: Request):
    raw = await _olarm_request(
        "GET",
        "/api/v4/devices",
        params={"page": 1, "pageLength": 100, "deviceApiAccessOnly": "1"},
    )
    devices = [enrich_device(d) for d in (raw.get("data") or [])]
    return {
        "ok": True,
        "userId": raw.get("userId"),
        "pageCount": raw.get("pageCount"),
        "devices": devices,
    }


@router.get("/api/arial/panel")
async def arial_panel():
    _ensure_live_session()
    cached = _cached_panel()
    if cached is not None:
        return {"ok": True, "device": cached, "live": True}
    try:
        raw = await _olarm_request(
            "GET",
            f"/api/v4/devices/{HANSEKOP_ID}",
            params={"deviceApiAccessOnly": "1"},
        )
    except HTTPException as exc:
        stale = _stale_panel()
        if exc.status_code == 429 and stale is not None:
            return {"ok": True, "device": stale}
        raise
    return {"ok": True, "device": _cached_panel(enrich_device(raw)), "live": True}


def _activity_bundle(device: dict[str, Any] | None, events: list[Any]) -> dict[str, Any]:
    power = arial_power((device or {}).get("deviceState") if device else None)
    if device and isinstance(device.get("arialPower"), dict):
        power = device["arialPower"]
    rows = [
        format_olarm_event(e, device)
        for e in events
        if isinstance(e, dict) and not is_skip_activity_event(e)
    ]
    return _stamp_activity_actors({"ok": True, "power": power, "events": rows, "live": True})


@router.get("/api/arial/activity")
async def arial_activity():
    _ensure_live_session()
    with _lock:
        cached = _activity_cache.get("data")
        last_at = float(_activity_cache.get("at") or 0)
    if cached is not None:
        return _activity_payload(cached, ack=True)
    device = _stale_panel()
    try:
        raw = await asyncio.wait_for(
            _olarm_request(
                "GET",
                f"/api/v4/devices/{HANSEKOP_ID}/events",
                params={"limit": 80},
            ),
            timeout=4.0,
        )
    except (HTTPException, asyncio.TimeoutError):
        if cached is not None:
            return _activity_payload(cached, ack=True)
        return _activity_payload({"ok": True, "power": {}, "events": [], "live": False}, ack=False)
    events = raw.get("data") if isinstance(raw, dict) else []
    if not isinstance(events, list):
        events = []
    if device is None:
        device = _stale_panel()
    apply_olarm_events(events, device if isinstance(device, dict) else None)
    with _lock:
        cached = _activity_cache.get("data")
    return _activity_payload(cached, ack=False)


@router.get("/api/arial/live")
async def arial_live():
    _ensure_live_session()

    async def events() -> AsyncIterator[str]:
        last_panel = -1
        last_act = -1
        while True:
            panel_seq = 0
            act_seq = 0
            device = None
            act = None
            with _lock:
                panel_seq = int(_panel_cache.get("seq") or 0)
                cached = _panel_cache.get("data")
                device = cached if isinstance(cached, dict) else None
                act_seq = int(_activity_cache.get("seq") or 0)
                act = _activity_cache.get("data")
            push: dict[str, Any] = {"ok": True, "live": True}
            changed = False
            if panel_seq != last_panel and device is not None:
                last_panel = panel_seq
                push["device"] = device
                changed = True
            if act_seq != last_act:
                last_act = act_seq
                push["activity"] = _activity_payload(act if isinstance(act, dict) else {"ok": True, "events": []}, ack=False)
                changed = True
            if changed:
                yield "data: " + json.dumps(push) + "\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/arial/keypad")
async def arial_keypad(request: Request):
    """Logged-in keypad PIN can arm/stay/disarm Hansekop. No cookie profile required."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = str(body.get("code") or "").strip()
    cmd = str(body.get("actionCmd") or "").strip()
    if code not in KEYPAD_CODES:
        raise HTTPException(status_code=401, detail="Invalid code")
    if cmd not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="Unknown or disallowed action")
    try:
        num = int(body.get("actionNum") or 1)
    except (TypeError, ValueError):
        num = 1
    if cmd != "user-panic" and num < 1:
        num = 1
    actor = _remember_keypad(code, cmd)
    raw = await _olarm_request(
        "POST",
        f"/api/v4/devices/{HANSEKOP_ID}/actions",
        json_body={"actionCmd": cmd, "actionNum": num},
    )
    try:
        fresh = await _olarm_request(
            "GET",
            f"/api/v4/devices/{HANSEKOP_ID}",
            params={"deviceApiAccessOnly": "1"},
        )
        if isinstance(fresh, dict):
            panel = enrich_device(fresh)
            panel["arialActor"] = dict(actor)
            _cached_panel(panel)
        else:
            _cached_panel(clear=True)
    except HTTPException:
        _cached_panel(clear=True)
    with _lock:
        _activity_cache["last_key"] = ""
        cached = _activity_cache.get("data")
    if isinstance(cached, dict):
        _stamp_activity_actors(cached)
        with _lock:
            _activity_cache["data"] = cached
            _activity_cache["at"] = time.time()
            _activity_cache["seq"] = int(_activity_cache.get("seq") or 0) + 1
    _ensure_live_session()
    return {"ok": True, "user": KEYPAD_CODES[code], "actor": actor, "result": raw, "device": _stale_panel()}


@router.get("/api/arial/devices/{device_id}")
async def arial_device(request: Request, device_id: str):
    require_user(request)
    raw = await _olarm_request(
        "GET",
        f"/api/v4/devices/{device_id}",
        params={"deviceApiAccessOnly": "1"},
    )
    return {"ok": True, "device": enrich_device(raw)}


@router.get("/api/arial/devices/{device_id}/events")
async def arial_events(request: Request, device_id: str, limit: int = 30):
    require_user(request)
    raw = await _olarm_request(
        "GET",
        f"/api/v4/devices/{device_id}/events",
        params={"limit": max(1, min(limit, 50))},
    )
    return {"ok": True, "events": raw.get("data") or [], "page": raw}


@router.post("/api/arial/devices/{device_id}/actions")
async def arial_action(request: Request, device_id: str):
    require_user(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    cmd = str(body.get("actionCmd") or "").strip()
    try:
        num = int(body.get("actionNum") or 0)
    except (TypeError, ValueError):
        num = 0
    if cmd not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="Unknown or disallowed action")
    if cmd != "user-panic" and num < 1:
        raise HTTPException(status_code=400, detail="actionNum required")
    raw = await _olarm_request(
        "POST",
        f"/api/v4/devices/{device_id}/actions",
        json_body={"actionCmd": cmd, "actionNum": num},
    )
    return {"ok": True, "result": raw}
