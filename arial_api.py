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
import sqlite3
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
# Olarm's deviceApiAccessOnly filter 404s for shared devices whose owner has not enabled API access (Klein River House);
# ARIAL_OLARM_API_ONLY=0 drops the filter for that site so panel/activity still work from the plain endpoints.
_OLARM_DEV_PARAMS = {"deviceApiAccessOnly": "1"} if (os.getenv("ARIAL_OLARM_API_ONLY") or "1").strip() != "0" else {}
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
_EVENTS_POLL_SEC = 10.0
_SAST = timezone(timedelta(hours=2))
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ZONE_EVENT_ACTIONS = {"zone", "zone_watch"}
AREA_EVENT_ACTIONS = {"area"}
ALARM_EVENT_ACTIONS = {"zone_alarm", "s_alm", "s_alm_f", "s_alm_m"}
NOISE_EVENT_ACTIONS = {"zones_idle", "device", "heartbeat"}
POWER_EVENT_ACTIONS = {"power", "ac", "mains", "battery"}
ALARM_EVENT_STATES = {"alarm", "emergency", "panic", "fire", "medical"}

# Site of this API instance. A second instance (e.g. Voelklip / HOME) runs the same code with these env vars set.
HANSEKOP_ID = (os.getenv("ARIAL_OLARM_DEVICE_ID") or "0bb544db-30b0-453d-bf39-d323538ebd5e").strip()
SITE_ID = (os.getenv("ARIAL_SITE_ID") or "hansekop").strip()
SITE_LABEL = (os.getenv("ARIAL_SITE_LABEL") or "HANSEKOP").strip()
SITE_TUYA = (os.getenv("ARIAL_TUYA_ENABLED") or "1").strip().lower() not in {"0", "false", "no"}
SITE_AREA_LABEL = (os.getenv("ARIAL_AREA_LABEL") or "Facility Building").strip()
SITE_AREA_LABELS = [x.strip() for x in (os.getenv("ARIAL_AREA_LABELS") or "").split(",")]
PGM_ALLOW = {int(x) for x in (os.getenv("ARIAL_PGM_ALLOW") or "").split(",") if x.strip().isdigit()}   # PGM outputs the keypad may pulse (e.g. garage door), per site   # optional per-area display names overriding the Olarm labels (e.g. "House,Flat")
KEYPAD_CODES = {
    "7302": {"name": "Marc", "from": "Pingoa"},
    "7102": {"name": "Amoroc", "from": "Amoroc"},
    "7777": {"name": "Onguard", "from": "Onguard"},
    "2640": {"name": "Comnet", "from": "Comnet"},
    "6114": {"name": "Kevin", "from": "Kevin"},
    "2525": {"name": "Bugsy", "from": "Bugsy"},
    "1111": {"name": "Tim", "from": "Tim"},
    "0843": {"name": "Annette", "from": "Annette"},
}
_KEYPAD_USERS = {x.strip().lower() for x in (os.getenv("ARIAL_KEYPAD_USERS") or "").split(",") if x.strip()}
if _KEYPAD_USERS:   # site-restricted keypad: only these people's existing PINs work here
    KEYPAD_CODES = {k: v for k, v in KEYPAD_CODES.items() if str(v.get("name", "")).lower() in _KEYPAD_USERS or str(v.get("from", "")).lower() in _KEYPAD_USERS}
_KEYPAD_USERS = {x.strip().lower() for x in (os.getenv("ARIAL_KEYPAD_USERS") or "").split(",") if x.strip()}
if _KEYPAD_USERS:   # site-restricted keypad: only these people's existing PINs work here
    KEYPAD_CODES = {k: v for k, v in KEYPAD_CODES.items() if str(v.get("name", "")).lower() in _KEYPAD_USERS or str(v.get("from", "")).lower() in _KEYPAD_USERS}
_KEYPAD_USERS = {x.strip().lower() for x in (os.getenv("ARIAL_KEYPAD_USERS") or "").split(",") if x.strip()}
if _KEYPAD_USERS:   # site-restricted keypad: only these people's existing PINs work here
    KEYPAD_CODES = {k: v for k, v in KEYPAD_CODES.items() if str(v.get("name", "")).lower() in _KEYPAD_USERS or str(v.get("from", "")).lower() in _KEYPAD_USERS}
KEYPAD_ACTORS = {str(v["from"]) for v in KEYPAD_CODES.values()}

# Tuya OpenAPI — TUYS keypad UI stays paused until tuya_probe() returns ok.
TUYA_DEFAULT_ENDPOINT = "https://openapi.tuyaeu.com"
TUYA_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
TUYA_MAINS_METER_ID = "bf90676b1341ecb34dse39"
# Transport for the Hansekop Tuya devices. "sharing" = the Smart Life device-sharing worker (tuya-sharing.service,
# /opt/tuya-sharing) pushes meter readings to /api/arial/meter/ingest and executes light commands; this process
# then makes NO IoT Core / OpenAPI calls. Any other value keeps the legacy Cloud path unchanged.
TUYA_TRANSPORT = (os.getenv("ARIAL_TUYA_TRANSPORT") or "cloud").strip().lower()
TUYA_SHARING = TUYA_TRANSPORT == "sharing"
# Home card / device list / switch forwarder. Smart Life = "sharing" (:8007/:8008).
# CBI Home = "cbi" (:8010/:8011). Do not merge the two collectors; a site only subscribes.
HOME_TRANSPORT = TUYA_TRANSPORT in {"sharing", "cbi"}
SHARING_CTRL_URL = (os.getenv("ARIAL_SHARING_CTRL_URL") or "http://127.0.0.1:8007").rstrip("/")
SHARING_CTRL_TOKEN = (os.getenv("ARIAL_SHARING_CTRL_TOKEN") or "").strip()
CBI_HOME_ID = (os.getenv("ARIAL_CBI_HOME_ID") or "").strip()
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
    if TUYA_SHARING:
        return True
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
    _tuya_token_file_save(_tuya_token)
    return _tuya_token


def _tuya_token_file() -> Path:
    env = (os.getenv("ARIAL_TUYA_TOKEN_FILE") or "").strip()
    if env:
        return Path(env)
    for base in (Path("/var/www/sailingsa/data"), _DATA_DIR, Path("/var/tmp"), Path("/tmp")):
        if base.is_dir():
            return base / "arial_tuya_token.json"
    return Path("/tmp/arial_tuya_token.json")


def _tuya_token_file_save(token: dict[str, Any]) -> None:
    """Share one token across uvicorn workers; Tuya invalidates older simple-mode tokens when a new one is minted."""
    path = _tuya_token_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(_flock_path(path), "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            path.write_text(json.dumps(token), encoding="utf-8")
    except OSError:
        pass


def _tuya_token_file_load() -> dict[str, Any] | None:
    path = _tuya_token_file()
    try:
        with open(_flock_path(path), "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_SH)
            data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("access_token"):
        return None
    if int(data.get("expire_at_ms") or 0) - 60_000 <= int(time.time() * 1000):
        return None
    return data


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
    global _tuya_token
    cached = _tuya_token
    now = int(time.time() * 1000)
    shared = _tuya_token_file_load()
    if shared and (not cached or shared.get("access_token") != cached.get("access_token")):
        # Another worker minted a newer token; ours would be rejected by Tuya.
        if not cached or int(shared.get("expire_at_ms") or 0) >= int(cached.get("expire_at_ms") or 0):
            _tuya_token = cached = shared
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
    if not payload.get("success") and int(payload.get("code") or 0) == 501:
        # Tuya cloud hiccup ("request fail with unkown error"); one quick retry clears it.
        time.sleep(0.4)
        payload = _tuya_call("GET", f"/v1.0/devices/{device_id}/status", creds=creds, access_token=access)
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


# ---------------------------------------------------------------------------
# LAN meter ingest. A site-side collector (tinytuya, read-only) pushes normalized readings of the HSK Mains
# Meter here. While a push is fresh, /tuya/probe and /tuya/energy answer from it and Tuya Cloud is not polled;
# when it goes stale the existing Cloud path runs unchanged. Nothing is synthesised: only pushed samples are
# integrated into the hourly bins (same trapezoid + max-gap rule as the Cloud sampler).
# ---------------------------------------------------------------------------
METER_INGEST_TOKEN_ENV = "ARIAL_METER_INGEST_TOKEN"
METER_FRESH_S = float(os.getenv("ARIAL_METER_FRESH_S") or 60.0)
METER_MAX_SKEW_S = 300.0
METER_MAX_BODY = 64 * 1024
METER_MAX_HISTORY = 720
METER_HISTORY_MAX_AGE_S = 7 * 86400
_meter_lock = threading.Lock()
_meter_latest: dict[str, Any] | None = None
_meter_latest_mtime = 0.0


def _meter_latest_path() -> Path:
    env = (os.getenv("ARIAL_METER_LATEST_PATH") or "").strip()
    if env:
        return Path(env)
    return Path("/var/www/sailingsa/data") / "arial_meter_latest.json"


def _meter_load() -> dict[str, Any] | None:
    """Latest pushed reading, re-read when the file changes so every worker/process sees the same push."""
    global _meter_latest, _meter_latest_mtime
    path = _meter_latest_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return _meter_latest
    if mtime != _meter_latest_mtime:
        try:
            data = json.loads(path.read_text())
            _meter_latest = data if isinstance(data, dict) else None
            _meter_latest_mtime = mtime
        except Exception:
            pass
    return _meter_latest


def _meter_fresh(now: float) -> dict[str, Any] | None:
    with _meter_lock:
        latest = _meter_load()
    if not latest or str(latest.get("device") or "") != TUYA_MAINS_METER_ID:
        return None
    try:
        received = float(latest.get("receivedAt") or 0)
    except (TypeError, ValueError):
        return None
    if not received or now - received > METER_FRESH_S:
        return None
    return latest


def _meter_ts(raw: Any, now: float) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("ts must be a number")
    ts = float(raw)
    if ts > 1e11:  # milliseconds
        ts /= 1000.0
    if not (0 < ts < now + 10 * 365 * 86400):
        raise ValueError("ts out of range")
    return ts


def _meter_num(raw: Any, lo: float, hi: float, name: str) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"{name} must be a number or null")
    n = float(raw)
    if n != n or n in (float("inf"), float("-inf")) or not (lo <= n <= hi):
        raise ValueError(f"{name} out of range")
    return n


def _meter_point(obj: Any, now: float) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("point must be an object")
    pt = {
        "ts": _meter_ts(obj.get("ts"), now),
        "v": _meter_num(obj.get("v"), 0, 500, "v"),
        "a": _meter_num(obj.get("a"), 0, 500, "a"),
        "w": _meter_num(obj.get("w"), 0, 200000, "w"),
        "kwh": _meter_num(obj.get("kwh"), 0, 1e8, "kwh"),
    }
    if obj.get("meterKwh") is not None:
        pt["meterKwh"] = _meter_num(obj.get("meterKwh"), 0, 1e8, "meterKwh")
    if obj.get("hz") is not None:
        pt["hz"] = _meter_num(obj.get("hz"), 0, 100, "hz")
    if obj.get("pf") is not None:
        pt["pf"] = _meter_num(obj.get("pf"), 0, 1, "pf")
    if obj.get("tempC") is not None:
        pt["tempC"] = _meter_num(obj.get("tempC"), -50, 150, "tempC")
    if "online" in obj:
        if not isinstance(obj["online"], bool):
            raise ValueError("online must be true/false")
        pt["online"] = obj["online"]
    if "switch" in obj and obj["switch"] is not None:
        if not isinstance(obj["switch"], bool):
            raise ValueError("switch must be true/false")
        pt["switch"] = obj["switch"]
    return pt


def _meter_status_rows(latest: dict[str, Any]) -> list[dict[str, Any]]:
    """Present the pushed reading in the same shape/scales as the Cloud status rows the card already reads."""
    rows: list[dict[str, Any]] = []
    if latest.get("v") is not None:
        rows.append({"code": "cur_voltage", "value": int(round(float(latest["v"]) * 100))})
    if latest.get("a") is not None:
        rows.append({"code": "cur_current", "value": int(round(float(latest["a"]) * 1000))})
    if latest.get("w") is not None:
        rows.append({"code": "cur_power", "value": int(round(float(latest["w"]) * 100))})
    if latest.get("kwh") is not None:
        rows.append({"code": "add_ele", "value": int(round(float(latest["kwh"]) * 100))})
    if isinstance(latest.get("switch"), bool):
        rows.append({"code": "switch", "value": latest["switch"]})
    for src, code in (("hz", "meter_hz"), ("pf", "meter_pf"), ("tempC", "meter_temp_c")):
        if latest.get(src) is not None:
            rows.append({"code": code, "value": float(latest[src])})
    if latest.get("meterKwh") is not None:
        # Not Tuya spec codes: the meter's own lifetime register (dp102, kWh) plus server-side references.
        lifetime = float(latest["meterKwh"])
        refs = _meter_refs_load()
        # The device register (dp102) restarts from 0 on power-up, so it is NOT a since-installed total. Only publish
        # "meter_kwh" (since installed) once a base has been set from a trusted total; the raw register is always available.
        rows.append({"code": "meter_register_kwh", "value": lifetime})
        base = refs.get("meterOffsetKwh")
        if isinstance(base, (int, float)):
            rows.append({"code": "meter_kwh", "value": round(lifetime + float(base), 3)})
        anchor = refs.get("meterKwhAtRestore")
        if isinstance(anchor, (int, float)):
            rows.append({"code": "meter_since_restore_kwh", "value": round(max(0.0, lifetime - float(anchor)), 3)})
        offset = refs.get("eskomOffsetKwh")
        if isinstance(offset, (int, float)):
            rows.append({"code": "eskom_kwh", "value": round(lifetime + float(offset), 1)})
    return rows


_METER_REFS_PATH = Path("/var/www/sailingsa/data/arial_meter_refs.json")
_meter_refs_cache: dict[str, Any] = {"mtime": None, "data": {}}


def _meter_refs_load() -> dict[str, Any]:
    """meterKwhAtRestore: lifetime register value when mains was last restored (since-restore = lifetime - anchor).
    eskomOffsetKwh: Eskom reading minus lifetime register at sync time (Eskom calc = lifetime + offset)."""
    try:
        mtime = _METER_REFS_PATH.stat().st_mtime
    except OSError:
        return {}
    if mtime != _meter_refs_cache["mtime"]:
        try:
            data = json.loads(_METER_REFS_PATH.read_text())
            _meter_refs_cache.update({"mtime": mtime, "data": data if isinstance(data, dict) else {}})
        except (OSError, ValueError):
            return dict(_meter_refs_cache["data"])
    return dict(_meter_refs_cache["data"])


def _meter_refs_write(update: dict[str, Any]) -> dict[str, Any]:
    data = _meter_refs_load()
    data.update(update)
    tmp = _METER_REFS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    os.replace(tmp, _METER_REFS_PATH)
    return data


_METER_HISTORY_DB = Path((os.getenv("ARIAL_METER_HISTORY_DB") or "").strip() or "/var/www/sailingsa/data/arial_meter_history.sqlite")
METER_HISTORY_DAYS = int(os.getenv("ARIAL_METER_HISTORY_DAYS") or 30)
_meter_db_lock = threading.Lock()
_meter_db_writes = 0
_meter_sampler_state_path = Path((os.getenv("ARIAL_METER_SAMPLER_STATE") or "").strip() or "/var/www/sailingsa/data/arial_meter_sampler.json")


def _meter_normalize_status(status: list[Any]) -> dict[str, Any]:
    """Cloud status rows -> V / A / W / kWh / switch using the GR2PWS DP spec scales (same as the card uses).
    Codes that are absent stay None; nothing is derived."""
    out: dict[str, Any] = {"v": None, "a": None, "w": None, "kwh": None, "switch": None, "kwhCode": None}
    vals: dict[str, Any] = {}
    for row in status or []:
        if isinstance(row, dict) and row.get("code"):
            vals[str(row["code"])] = row.get("value")

    def num(code: str, scale: float) -> float | None:
        raw = vals.get(code)
        if raw is None or isinstance(raw, bool):
            return None
        try:
            return float(raw) / scale
        except (TypeError, ValueError):
            return None

    out["v"] = num("cur_voltage", 100.0)
    out["a"] = num("cur_current", 1000.0)
    out["w"] = num("cur_power", 100.0)
    for code in ("total_forward_energy", "forward_energy_total", "add_ele"):
        k = num(code, 100.0)
        if k is not None:
            out["kwh"] = k
            out["kwhCode"] = code
            break
    for code in ("switch", "switch_1"):
        if isinstance(vals.get(code), bool):
            out["switch"] = vals[code]
            break
    return out


def _meter_latest_write(latest: dict[str, Any]) -> None:
    global _meter_latest, _meter_latest_mtime
    path = _meter_latest_path()
    with _meter_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(latest, separators=(",", ":")))
        tmp.replace(path)
        _meter_latest = latest
        try:
            _meter_latest_mtime = path.stat().st_mtime
        except OSError:
            pass


def _meter_db() -> sqlite3.Connection:
    _METER_HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_METER_HISTORY_DB), timeout=5)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS readings (ts REAL PRIMARY KEY, device TEXT NOT NULL, online INTEGER NOT NULL, "
        "v REAL, a REAL, w REAL, kwh REAL, switch INTEGER, src TEXT)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS readings_device_ts ON readings(device, ts)")
    return conn


def _meter_history_write(device: str, ts: float, online: bool, r: dict[str, Any], src: str) -> None:
    """Persist one real reading (or an offline mark). Prunes rows older than METER_HISTORY_DAYS periodically."""
    global _meter_db_writes
    sw = r.get("switch")
    with _meter_db_lock:
        try:
            conn = _meter_db()
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO readings (ts, device, online, v, a, w, kwh, switch, src) VALUES (?,?,?,?,?,?,?,?,?)",
                    (round(float(ts), 3), device, 1 if online else 0, r.get("v"), r.get("a"), r.get("w"), r.get("kwh"),
                     None if sw is None else (1 if sw else 0), src),
                )
                _meter_db_writes += 1
                if _meter_db_writes % 200 == 1:
                    conn.execute("DELETE FROM readings WHERE ts < ?", (time.time() - METER_HISTORY_DAYS * 86400,))
            conn.close()
        except sqlite3.Error:
            pass


def _meter_history_rows(device: str, since: float, until: float, limit: int) -> list[dict[str, Any]]:
    with _meter_db_lock:
        try:
            conn = _meter_db()
            cur = conn.execute(
                "SELECT ts, online, v, a, w, kwh, switch, src FROM readings WHERE device=? AND ts>=? AND ts<=? ORDER BY ts DESC LIMIT ?",
                (device, since, until, limit),
            )
            rows = cur.fetchall()
            conn.close()
        except sqlite3.Error:
            return []
    out = []
    for ts, online, v, a, w, kwh, sw, src in reversed(rows):
        out.append({"ts": ts, "online": bool(online), "v": v, "a": a, "w": w, "kwh": kwh,
                    "switch": None if sw is None else bool(sw), "src": src})
    return out


def _meter_sampler_note(info: dict[str, Any]) -> None:
    try:
        _meter_sampler_state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = _meter_sampler_state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(info, pid=os.getpid(), at=time.time()), separators=(",", ":")))
        tmp.replace(_meter_sampler_state_path)
    except OSError:
        pass


def _meter_sampler_state() -> dict[str, Any] | None:
    try:
        data = json.loads(_meter_sampler_state_path.read_text())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _meter_apply(device: str, reading: dict[str, Any], history: list[dict[str, Any]]) -> int:
    """Feed pushed samples through the existing bin/recent/outage logic. Returns samples integrated."""
    points = sorted(history + [reading], key=lambda x: x["ts"])
    used = 0
    for pt in points:
        if pt.get("online") is False or pt.get("w") is None:
            continue
        rows = [{"code": "cur_power", "value": int(round(pt["w"] * 100))}]
        _energy_record_sample(device, rows, pt["ts"])
        used += 1
    if reading.get("w") is not None and reading.get("online", True):
        _energy_note_recent(device, [{"code": "cur_power", "value": int(round(reading["w"] * 100))}], reading["ts"])
    online = reading.get("online")
    if isinstance(online, bool):
        _power_mark(online=online, now=reading["ts"])
        if not online:
            with _energy_lock:
                _energy_last.pop(device, None)
    return used


@router.post("/api/arial/meter/ingest")
async def arial_meter_ingest(request: Request):
    token = (os.getenv(METER_INGEST_TOKEN_ENV) or "").strip()
    if not token:
        return JSONResponse({"ok": False, "error": "ingest disabled"}, status_code=503)
    auth = request.headers.get("authorization") or ""
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].strip(), token):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > METER_MAX_BODY:
        return JSONResponse({"ok": False, "error": "body too large"}, status_code=413)
    body = await request.body()
    if len(body) > METER_MAX_BODY:
        return JSONResponse({"ok": False, "error": "body too large"}, status_code=413)
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"ok": False, "error": "object expected"}, status_code=400)
    device = str(payload.get("device") or "")
    if device != TUYA_MAINS_METER_ID:
        return JSONResponse({"ok": False, "error": "device not allowed"}, status_code=403)
    now = time.time()
    try:
        reading = _meter_point(payload, now)
        if not isinstance(payload.get("online"), bool):
            raise ValueError("online must be true/false")
        if abs(now - reading["ts"]) > METER_MAX_SKEW_S:
            raise ValueError("ts skew > 5 minutes")
        if reading["online"] and all(reading.get(k) is None for k in ("v", "a", "w", "kwh")):
            raise ValueError("no readings")
        src = str(payload.get("src") or "lan")[:16]
        history: list[dict[str, Any]] = []
        raw_hist = payload.get("history")
        if raw_hist is not None:
            if not isinstance(raw_hist, list) or len(raw_hist) > METER_MAX_HISTORY:
                raise ValueError(f"history must be a list of at most {METER_MAX_HISTORY} points")
            for item in raw_hist:
                pt = _meter_point(item, now)
                if pt["ts"] > now + METER_MAX_SKEW_S or pt["ts"] < now - METER_HISTORY_MAX_AGE_S:
                    raise ValueError("history ts out of window")
                history.append(pt)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    used = _meter_apply(device, reading, history)
    latest = {
        "device": device,
        "ts": reading["ts"],
        "receivedAt": now,
        "online": reading["online"],
        "v": reading["v"],
        "a": reading["a"],
        "w": reading["w"],
        "kwh": reading["kwh"],
        "src": src,
        "historyPoints": len(history),
    }
    if "switch" in reading:
        latest["switch"] = reading["switch"]
    if reading.get("meterKwh") is not None:
        latest["meterKwh"] = reading["meterKwh"]
    for k in ("hz", "pf", "tempC"):
        if reading.get(k) is not None:
            latest[k] = reading[k]
    try:
        _meter_latest_write(latest)
    except OSError as exc:
        return JSONResponse({"ok": False, "error": f"store failed: {exc}"}, status_code=500)
    for pt in history:
        _meter_history_write(device, pt["ts"], pt.get("online", True), pt, src)
    _meter_history_write(device, reading["ts"], reading["online"], reading, src)
    return {"ok": True, "serverTime": now, "stored": True, "historyPoints": len(history), "samplesIntegrated": used}


_probe_cache: dict[str, Any] = {"at": 0.0, "device": "", "out": None}


def _probe_remember(out: dict[str, Any]) -> dict[str, Any]:
    if out.get("deviceId") == TUYA_MAINS_METER_ID:
        sampler = _meter_sampler_state()
        if sampler:
            out["sampler"] = {k: sampler.get(k) for k in ("at", "ok", "code", "msg", "online") if k in sampler}
        _probe_cache.update({"at": time.time(), "device": out["deviceId"], "out": dict(out)})
    return out


HOME_API_URL = (os.getenv("ARIAL_HOME_API_URL") or "http://127.0.0.1:8008").rstrip("/")


def _home_api_get(path: str, timeout: float = 8.0) -> dict[str, Any] | None:
    """Read-only home analytics API (home_api.py). Separate process from the collector so UI/analytics changes never
    interrupt data collection."""
    try:
        r = httpx.get(HOME_API_URL + path, headers={"Authorization": f"Bearer {SHARING_CTRL_TOKEN}"}, timeout=timeout)
        return r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("home-api %s failed: %s", path, exc)
        return None


def _sharing_get(path: str, timeout: float = 4.0) -> dict[str, Any] | None:
    """Loopback call to the tuya-sharing worker control API (read-only views + health)."""
    try:
        r = httpx.get(SHARING_CTRL_URL + path, headers={"Authorization": f"Bearer {SHARING_CTRL_TOKEN}"}, timeout=timeout)
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _sharing_health() -> dict[str, Any] | None:
    h = _sharing_get("/health")
    if not h:
        return None
    return {k: h.get(k) for k in ("ok", "mqttConnected", "meterOnline", "meterLastReportAgeS", "meterStale", "authFailed", "tokenExpiresInS")}


def _sharing_probe(out: dict[str, Any]) -> dict[str, Any]:
    """Non-meter device (the light switch): current state as held by the sharing worker (MQTT-fed)."""
    view = _sharing_get(f"/devices/{out['deviceId']}")
    out["configured"] = True
    out["source"] = "sharing"
    if not view or not view.get("ok"):
        out["tuyaMsg"] = "sharing worker unavailable" if view is None else str(view.get("error") or "device not watched")
        return out
    online = bool(view.get("online"))
    status = [{"code": k, "value": v} for k, v in (view.get("status") or {}).items()]
    out.update({"ok": online, "tokenOk": True, "deviceOk": online, "status": status, "dpsCount": len(status),
                "tuyaMsg": "" if online else "device offline (sharing)", "hint": ""})
    return out


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
    is_meter = out["deviceId"] == TUYA_MAINS_METER_ID
    if TUYA_SHARING and not is_meter:
        return _sharing_probe(out)
    if is_meter and out["configured"]:
        _ensure_energy_sampler(out["deviceId"])   # the server sampler feeds the reading below; browsers never poll Cloud
    latest = _meter_fresh(time.time()) if is_meter else None
    if latest is not None:
        # Fresh persisted reading (server Cloud sampler or LAN push): answer from it in the Cloud response shape.
        online = bool(latest.get("online"))
        src = str(latest.get("src") or "sampled")
        out.update({
            "ok": online,
            "configured": True,
            "tokenOk": True,
            "deviceOk": online,
            "source": src,
            "ageS": round(time.time() - float(latest.get("receivedAt") or 0), 1),
            "readingTs": latest.get("ts"),
            "tuyaCode": None,
            "tuyaMsg": "" if online else f"meter offline ({src})",
            "hint": "",
            "status": _meter_status_rows(latest) if online else None,
        })
        if online:
            out["dpsCount"] = len(out["status"] or [])
        return out
    if TUYA_SHARING:
        # No fresh sharing push: report the stale link honestly; never fall back to Cloud.
        out.update({"configured": True, "source": "sharing", "tuyaMsg": "sharing link stale",
                    "hint": "tuya-sharing worker has no fresh meter report (MQTT/session stale or meter offline)."})
        out["sharing"] = _sharing_health()
        return out
    if is_meter:
        # No fresh reading: fall back to Cloud, but at most one Cloud call per poll interval across all browsers.
        cached = _probe_cache.get("out")
        if cached is not None and _probe_cache.get("device") == out["deviceId"] and time.time() - float(_probe_cache.get("at") or 0) < _ENERGY_SAMPLE_S:
            res = dict(cached)
            res["cached"] = True
            return res
    if not out["configured"]:
        out["hint"] = (
            "TUYA_CLIENT_ID / TUYA_SECRET are not set. Put them in the live process env (never git), "
            "then GET /api/arial/tuya/probe. TUYS UI stays paused until this probe returns ok."
        )
        return out
    try:
        with _tuya_http_lock:
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
                # Bins are written only by the single sampler thread; probes from browsers must not add to them.
                if out["deviceId"] == ((creds["device_id"] or "").strip() or TUYA_MAINS_METER_ID):
                    _ensure_energy_sampler(out["deviceId"])
            else:
                out["hint"] = _tuya_hint(out["tuyaCode"], out["tuyaMsg"], token_ok=True, device_ok=False)
                return _probe_remember(out)
            out["hint"] = ""
            return _probe_remember(out)
    except httpx.HTTPError as exc:
        out["tuyaMsg"] = str(exc)
        out["hint"] = f"Tuya OpenAPI unreachable: {exc}"
        return _probe_remember(out)


# ---------------------------------------------------------------------------
# Hourly energy (kWh x 24) for the breaker card. Two real sources only:
#   1. Tuya statistics API (hours of add_ele) when the project has it enabled.
#   2. Bins integrated from live cur_power samples taken on every probe.
# Never synthesise history; missing hours stay null.
# ---------------------------------------------------------------------------
ENERGY_DAYS = max(1, min(7, int(os.getenv("ARIAL_ENERGY_DAYS") or 3)))  # card window; 4 reaches back to the 2 Sep restore
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
    """GR2PWS spec: cur_power unit W, scale 2 (always /100). Never guess from magnitude."""
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return None
    return n / 100.0


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


_energy_est_cache: dict[str, Any] = {"at": 0.0, "keys": set()}


def _energy_estimated_hours() -> set[str]:
    """Hour keys whose kWh was back-filled (flat spread from the meter register while the link was down), so the
    card can draw them as estimates rather than measured bars. Source: data/arial_energy_bins_backfill_*.json."""
    now = time.time()
    if now - _energy_est_cache["at"] < 60:
        return _energy_est_cache["keys"]
    keys: set[str] = set()
    for p in Path("/var/www/sailingsa/data").glob("arial_energy_bins_backfill_*.json"):
        try:
            for k in json.loads(p.read_text()).get("hours") or []:
                keys.add(str(k))
        except (OSError, ValueError):
            continue
    _energy_est_cache.update({"at": now, "keys": keys})
    return keys


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
        est_keys = _energy_estimated_hours()
        days.append(
            {
                "ymd": day.strftime("%Y-%m-%d"),
                "label": "Today" if back == 0 else ("Yesterday" if back == 1 else day.strftime("%a %d %b")),
                "hours": vals,
                "estimated": [f"{ymd}{h:02d}" in est_keys for h in range(24)],
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
def _poll_interval() -> float:
    try:
        n = float(os.getenv("ARIAL_TUYA_POLL_S") or 15.0)
    except ValueError:
        n = 15.0
    return min(30.0, max(10.0, n))


_ENERGY_SAMPLE_S = _poll_interval()
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
    seen: set[tuple[Any, Any, Any]] = set()
    row_key = ""
    for _ in range(max_pages):
        params: dict[str, Any] = {"type": types, "start_time": start_ms, "end_time": end_ms, "size": "100"}
        if codes:
            params["codes"] = codes
        if row_key:
            params["start_row_key"] = row_key
        payload = _tuya_call("GET", f"/v1.0/devices/{device}/logs", creds=creds, params=params, access_token=access)
        if int(payload.get("code") or 0) == TUYA_CODE_TOKEN_INVALID:
            _tuya_reset_token()
            _tuya_ensure_token(creds)
            access = str((_tuya_token or {}).get("access_token") or "")
            if not access:
                break
            payload = _tuya_call("GET", f"/v1.0/devices/{device}/logs", creds=creds, params=params, access_token=access)
        attempt = 0
        while not payload.get("success") and _tuya_is_rate_limit(payload) and attempt < 4:
            attempt += 1
            _tuya_logs_last_error.update({"code": payload.get("code"), "msg": payload.get("msg"), "at": time.time()})
            time.sleep(3.0 * attempt)
            payload = _tuya_call("GET", f"/v1.0/devices/{device}/logs", creds=creds, params=params, access_token=access)
        if not payload.get("success"):
            _tuya_logs_last_error.update({"code": payload.get("code"), "msg": payload.get("msg"), "at": time.time()})
            break
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        page = [r for r in (result.get("logs") or []) if isinstance(r, dict)]
        fresh = 0
        for r in page:
            key = (r.get("event_time"), r.get("code"), r.get("value"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
            fresh += 1
        # Tuya sometimes reports has_next with a cursor that returns the same page; stop when nothing new arrives.
        if fresh == 0 or not result.get("has_next") or not result.get("current_row_key"):
            break
        row_key = str(result.get("current_row_key"))
        time.sleep(0.5)
    return rows


_tuya_logs_last_error: dict[str, Any] = {}


def _tuya_is_rate_limit(payload: dict[str, Any]) -> bool:
    text = str(payload.get("msg") or "").lower()
    return "frequent" in text or "rate limit" in text or int(payload.get("code") or 0) in {40000309, 28841105}


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
        rows.extend(_tuya_logs(creds, device, types="7", codes="cur_power", start_ms=int(win * 1000), end_ms=int(nxt * 1000), max_pages=12))
        win = nxt
        time.sleep(1.0)
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


_energy_bootstrap_info: dict[str, Any] = {}


def _energy_bootstrap(device: str) -> None:
    """On start: restores from 7 days of lifecycle log, and refill the last 24 h of bins from power reports."""
    global _power_sync_at
    creds = _tuya_creds()
    if not (creds["client_id"] and creds["secret"]):
        return
    with _tuya_http_lock:
        _energy_bootstrap_info["power"] = _power_sync_from_logs(creds, device, days=7)
        _power_sync_at = time.time()
        restore = _power_snapshot(time.time()).get("restoreAt")
        since = max(time.time() - ENERGY_DAYS * 86_400, float(restore) if restore else 0.0)
        _energy_bootstrap_info["backfill"] = _energy_backfill_from_logs(creds, device, since)
        _energy_bootstrap_info["at"] = time.time()
        with _energy_lock:
            _energy_save()


def _energy_sample_once(device: str) -> dict[str, Any]:
    """One Cloud poll: device detail -> outage mark, hourly bins, normalized V/A/W/kWh persisted (latest + SQLite)."""
    global _power_sync_at
    creds = _tuya_creds()
    if not (creds["client_id"] and creds["secret"]):
        return {"ok": False, "skipped": "no credentials"}
    if time.time() - _power_sync_at >= 600:
        _power_sync_at = time.time()
        try:
            with _tuya_http_lock:
                _power_sync_from_logs(creds, device, days=2)
        except Exception:
            pass
    panel = _stale_panel() or {}
    ac = (panel.get("arialPower") or {}).get("acOk") if isinstance(panel.get("arialPower"), dict) else None
    if isinstance(ac, bool):
        _power_mark(ac_ok=ac)
    with _tuya_http_lock:
        payload = _tuya_device_detail(creds, device)
    now = time.time()
    if not payload.get("success"):
        info = {"ok": False, "code": payload.get("code"), "msg": str(payload.get("msg") or "")[:200]}
        _meter_sampler_note(info)
        return info
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    online = result.get("online")
    if online is False:
        _power_mark(online=False, now=now)
        with _energy_lock:
            _energy_last.pop(device, None)
        latest = {"device": device, "ts": now, "receivedAt": now, "online": False, "v": None, "a": None, "w": None,
                  "kwh": None, "src": "cloud"}
        _meter_latest_write(latest)
        _meter_history_write(device, now, False, {}, "cloud")
        info = {"ok": True, "online": False}
        _meter_sampler_note(info)
        return info
    if isinstance(online, bool):
        _power_mark(online=True, now=now)
    status = result.get("status")
    if not isinstance(status, list):
        info = {"ok": False, "msg": "no status list"}
        _meter_sampler_note(info)
        return info
    _energy_note_recent(device, status, now)
    _energy_record_sample(device, status, now=now)
    r = _meter_normalize_status(status)
    latest = {"device": device, "ts": now, "receivedAt": now, "online": True, "v": r["v"], "a": r["a"], "w": r["w"],
              "kwh": r["kwh"], "src": "cloud", "kwhCode": r["kwhCode"]}
    if isinstance(r.get("switch"), bool):
        latest["switch"] = r["switch"]
    _meter_latest_write(latest)
    _meter_history_write(device, now, True, r, "cloud")
    info = {"ok": True, "online": True, "w": r["w"], "v": r["v"], "a": r["a"], "kwh": r["kwh"]}
    _meter_sampler_note(info)
    return info


def _energy_sampler_loop(device: str) -> None:
    try:
        _energy_bootstrap(device)
    except Exception:
        pass
    while True:
        try:
            _energy_sample_once(device)
        except Exception as exc:  # never let one bad poll end the sampler
            _meter_sampler_note({"ok": False, "msg": f"exception: {exc}"[:200]})
        time.sleep(_ENERGY_SAMPLE_S)


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
    cur_hour_key = _sa_hour_key(now)
    complete: list[tuple[str, float]] = []  # newest first
    day_totals: list[float] = []
    for day in days:
        ymd = str(day.get("ymd") or "").replace("-", "")
        hours = day.get("hours") or []
        for h in range(23, -1, -1):
            v = hours[h] if h < len(hours) else None
            if v is None:
                continue
            key = f"{ymd}{h:02d}"
            if key >= cur_hour_key or in_recovery(key):
                continue
            complete.append((key, float(v)))
        if int(day.get("hoursWithData") or 0) >= 20 and day.get("totalKwh") is not None and day is not days[0]:
            day_totals.append(float(day["totalKwh"]))
    complete.sort(key=lambda kv: kv[0], reverse=True)
    # Running baseline = median of the last 12 complete hours: robust to an idle night and to charging spikes.
    window = [v for _, v in complete[:12]]
    baseline_kw = None
    if len(window) >= 4:
        window.sort()
        mid = len(window) // 2
        baseline_kw = round(window[mid] if len(window) % 2 else (window[mid - 1] + window[mid]) / 2.0, 3)
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
    if TUYA_SHARING:
        return
    if _energy_thread is not None and _energy_thread.is_alive():
        return
    if os.getenv("ARIAL_ENERGY_SAMPLER", "1").strip().lower() in {"0", "false", "no"}:
        return
    now = time.time()
    if now - _energy_sampler_checked_at < 30:
        return
    _energy_sampler_checked_at = now
    # Own lock for the persisting sampler (legacy 60s loops in older processes hold the old .sampler.lock).
    lock_path = _meter_sampler_state_path.with_suffix(".lock")
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
    out: dict[str, Any] = {"ok": False, "deviceId": device, "tz": "Africa/Johannesburg", "source": "", "days": []}
    if device == TUYA_MAINS_METER_ID and creds["client_id"] and creds["secret"]:
        _ensure_energy_sampler(device)
    latest = _meter_fresh(now) if device == TUYA_MAINS_METER_ID else None
    if latest is not None:
        # Fresh persisted reading: bins already hold the sampled data; no Cloud statistics call from browsers.
        src = str(latest.get("src") or "sampled")
        out["source"] = f"{src}-sampled"
        out["days"] = _energy_days_from_bins(device, now)
        out.update(_energy_analysis(device, out["days"], now))
        out["debug"] = {
            "latest": {"ageS": round(now - float(latest.get("receivedAt") or 0), 1), "readingTs": latest.get("ts"), "src": src},
            "sampler": _meter_sampler_state(),
            "samplerHere": bool(_energy_thread and _energy_thread.is_alive()),
            "olarmRole": _live_role,
        }
        out["ok"] = True
        return out
    if TUYA_SHARING:
        out["source"] = "sharing-stale"
        out["days"] = _energy_days_from_bins(device, now)
        out.update(_energy_analysis(device, out["days"], now))
        out["debug"] = {"sharing": _sharing_health()}
        out["ok"] = True
        return out
    if creds["client_id"] and creds["secret"]:
        _ensure_energy_sampler(device)
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
    out["debug"] = {
        "bootstrap": _energy_bootstrap_info,
        "logsLastError": _tuya_logs_last_error,
        "samplerHere": bool(_energy_thread and _energy_thread.is_alive()),
        "olarmRole": _live_role,
        "olarmBackfill": _olarm_backfill_info,
        "olarmStoreRows": len(_olarm_store),
        "olarmLoop": _live_debug,
    }
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


# ---------------------------------------------------------------------------
# Live state shared across uvicorn workers.
# Exactly one worker (flock owner) polls Olarm; it writes panel + raw events to a
# JSON snapshot. Other workers follow that file so SSE / status / activity stay
# identical everywhere and Olarm is not hammered into 429s.
# ---------------------------------------------------------------------------
_OLARM_STORE_DAYS = 30
_OLARM_STORE_MAX = 8000
_ACTIVITY_BUNDLE_MAX = 400
_LIVE_DEVICE_POLL_SEC = 3.0
_LIVE_FAST_POLL_SEC = 1.0
_live_fast_until = 0.0   # after a keypad action, poll Olarm quickly for a short burst so the confirmed state lands fast
_olarm_store: dict[str, dict[str, Any]] = {}
_live_state_mtime = 0.0
_live_owner_lockf = None
_live_role = ""


def _live_state_path() -> Path:
    env = (os.getenv("ARIAL_LIVE_STATE") or "").strip()
    if env:
        return Path(env)
    for base in (Path("/var/www/sailingsa/data"), _DATA_DIR, Path("/var/tmp"), Path("/tmp")):
        if base.is_dir():
            return base / "arial_live_state.json"
    return Path("/tmp/arial_live_state.json")


def _olarm_store_add(rows: list[Any]) -> int:
    """Merge raw Olarm events into the 30-day store. Returns number of new rows."""
    added = 0
    newest_ms = max([_event_time_ms(r) for r in rows if isinstance(r, dict)] + [_event_time_ms(r) for r in _olarm_store.values()] + [0])
    # 30 days relative to the newest event the panel has produced (not wall clock), so history survives quiet spells.
    cutoff_ms = newest_ms - _OLARM_STORE_DAYS * 86_400_000
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = olarm_event_key(row)
        if not key or key in _olarm_store:
            continue
        if _event_time_ms(row) and _event_time_ms(row) < cutoff_ms:
            continue
        _olarm_store[key] = row
        added += 1
    if len(_olarm_store) > _OLARM_STORE_MAX or added:
        for key in [k for k, r in _olarm_store.items() if _event_time_ms(r) and _event_time_ms(r) < cutoff_ms]:
            _olarm_store.pop(key, None)
        if len(_olarm_store) > _OLARM_STORE_MAX:
            # Over the cap: shed the oldest plain zone open/close rows first so arm/disarm/alarm history survives.
            ordered = sorted(_olarm_store.items(), key=lambda kv: _event_time_ms(kv[1]))  # oldest first
            excess = len(ordered) - _OLARM_STORE_MAX
            drop: set[str] = set()
            for key, row in ordered:
                if excess <= 0:
                    break
                if str(row.get("eventAction") or "").lower() in {"zone", "zone_watch"}:
                    drop.add(key)
                    excess -= 1
            for key, _row in ordered:
                if excess <= 0:
                    break
                if key not in drop:
                    drop.add(key)
                    excess -= 1
            for key in drop:
                _olarm_store.pop(key, None)
    return added


def _olarm_store_rows() -> list[dict[str, Any]]:
    return sorted(_olarm_store.values(), key=lambda r: _event_time_ms(r), reverse=True)


def _live_state_save() -> None:
    path = _live_state_path()
    with _lock:
        panel = _panel_cache.get("data")
        payload = {
            "at": time.time(),
            "panel": panel if isinstance(panel, dict) else None,
            "events": _olarm_store_rows(),
            "lastKey": str(_activity_cache.get("last_key") or ""),
            "owner": {"pid": os.getpid(), "loop": {k: v for k, v in _live_debug.items() if k != "owner"}, "backfill": dict(_olarm_backfill_info)},
            "backfillCursor": dict(_olarm_backfill_cursor),
        }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(_flock_path(path), "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(path)
    except OSError:
        pass


def _live_state_load(force: bool = False) -> bool:
    """Follower: pull the owner's snapshot into this process's caches. Returns True when something changed."""
    global _live_state_mtime
    path = _live_state_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    if not force and mtime == _live_state_mtime:
        return False
    try:
        with open(_flock_path(path), "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_SH)
            data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    _live_state_mtime = mtime
    if not isinstance(data, dict):
        return False
    if isinstance(data.get("owner"), dict):
        _live_debug["owner"] = data["owner"]
    if isinstance(data.get("backfillCursor"), dict) and not _olarm_backfill_cursor.get("until") and not _olarm_backfill_cursor.get("done"):
        _olarm_backfill_cursor.update({k: data["backfillCursor"].get(k) for k in ("until", "done")})
    panel = data.get("panel")
    if isinstance(panel, dict):
        _cached_panel(panel)
    rows = data.get("events") if isinstance(data.get("events"), list) else []
    _olarm_store_add(rows)
    _rebuild_activity_cache(_stale_panel(), str(data.get("lastKey") or ""))
    return True


def _is_plain_zone_row(row: dict[str, Any]) -> bool:
    if str(row.get("tab") or "") != "zones":
        return False
    state = str(row.get("state") or "").upper()
    action = str(row.get("action") or "").lower()
    if "alarm" in action or "bypass" in action or "tamper" in action:
        return False
    return not any(k in state for k in ("ALARM", "PANIC", "EMERGENCY", "FIRE", "MEDICAL", "BYPASS", "TAMPER", "TROUBLE"))


def _rebuild_activity_cache(device: dict[str, Any] | None, newest: str) -> None:
    rows = _olarm_store_rows()
    bundle = _activity_bundle(device, rows)
    events = bundle.get("events") or []
    # Keep every headline event (arm/disarm/alarm/bypass/power); trim only plain zone open/close chatter to fit the cap.
    headline = [r for r in events if not _is_plain_zone_row(r)]
    room = max(0, _ACTIVITY_BUNDLE_MAX - len(headline))
    zone_rows = [r for r in events if _is_plain_zone_row(r)][:room]
    keep = set(map(id, headline)) | set(map(id, zone_rows))
    bundle["events"] = [r for r in events if id(r) in keep]
    bundle["lastKey"] = newest
    bundle["ack"] = False
    with _lock:
        _activity_cache["data"] = bundle
        _activity_cache["at"] = time.time()
        _activity_cache["last_key"] = newest
        _activity_cache["seq"] = int(_activity_cache.get("seq") or 0) + 1


def _try_live_owner() -> bool:
    global _live_owner_lockf
    if _live_owner_lockf is not None:
        return True
    lock_path = Path(str(_live_state_path()) + ".owner.lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lockf = open(lock_path, "a+", encoding="utf-8")
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _live_owner_lockf = lockf
    return True


def _ensure_live_session() -> None:
    global _live_thread, _live_role
    with _lock:
        if _live_thread is not None and _live_thread.is_alive():
            return
        _live_stop.clear()
        if _try_live_owner():
            _live_role = "owner"
            target = _olarm_owner_thread
        else:
            _live_role = "follower"
            target = _live_follow_loop
        _live_thread = threading.Thread(target=target, name=f"arial-olarm-{_live_role}", daemon=True)
        _live_thread.start()


def _olarm_owner_thread() -> None:
    # Never call this while holding _lock: _live_state_load -> _cached_panel takes _lock itself.
    try:
        _live_state_load(force=True)  # inherit history from the previous owner
    except Exception as exc:
        _live_debug["inheritError"] = f"{exc.__class__.__name__}: {exc}"
    _olarm_live_loop()


def _live_follow_loop() -> None:
    global _live_role
    try:
        _live_state_load(force=True)
    except Exception:
        pass
    while not _live_stop.wait(0.5):
        try:
            if _live_owner_lockf is None and _try_live_owner():
                # Previous owner died; take over from where its snapshot left off.
                _live_role = "owner"
                _olarm_owner_thread()
                return
            _live_state_load()
        except Exception as exc:
            _live_debug["followError"] = f"{exc.__class__.__name__}: {exc}"
            continue


_OLARM_PAGE = 40  # Olarm caps pageLength at 40
_olarm_backfill_info: dict[str, Any] = {}


def _olarm_events_page(client: httpx.Client, until_ms: int | None = None) -> tuple[int, list[dict[str, Any]]]:
    params: dict[str, Any] = {"pageLength": _OLARM_PAGE}
    if until_ms:
        params["until"] = int(until_ms)
    resp = client.get(f"/api/v4/devices/{HANSEKOP_ID}/events", params=params)
    if resp.status_code != 200:
        return resp.status_code, []
    payload = resp.json()
    rows = payload.get("data") if isinstance(payload, dict) else []
    return 200, [r for r in (rows or []) if isinstance(r, dict)]


_olarm_backfill_cursor: dict[str, Any] = {"until": None, "done": False}


def _olarm_backfill(max_pages: int = 600, pace_s: float = 6.0, stop_when_known: bool = False) -> dict[str, Any]:
    """Page backwards through Olarm history (until=oldest-1) into the store. Paced to stay under Olarm's rate limit.
    The cursor is persisted in the live-state snapshot so a restart resumes instead of starting over."""
    info = {"pages": 0, "added": 0, "oldest": None, "stopped": ""}
    cutoff_ms = int((time.time() - _OLARM_STORE_DAYS * 86_400) * 1000)
    until: int | None = None
    if not stop_when_known:
        if _olarm_backfill_cursor.get("done"):
            info["stopped"] = "already complete"
            return info
        saved = _olarm_backfill_cursor.get("until")
        if saved:
            until = int(saved)
            info["resumedFrom"] = until
    for _ in range(max_pages):
        with _olarm_http_lock:
            client = _olarm_sync_client()
            status, rows = _olarm_events_page(client, until)
        if status == 429:
            time.sleep(15.0)
            continue
        if status != 200 or not rows:
            info["stopped"] = f"status {status}" if status != 200 else "no rows"
            break
        info["pages"] += 1
        added = _olarm_store_add(rows)
        info["added"] += added
        oldest = min(_event_time_ms(r) for r in rows)
        info["oldest"] = oldest
        if added:
            # Show history as it arrives instead of only when the whole back-fill finishes.
            _rebuild_activity_cache(_stale_panel(), str(_activity_cache.get("last_key") or ""))
            _live_state_save()
        if stop_when_known and added == 0:
            info["stopped"] = "overlap"
            break
        if oldest <= cutoff_ms or oldest <= 0:
            info["stopped"] = "30 days"
            if not stop_when_known:
                _olarm_backfill_cursor["done"] = True
            break
        until = oldest - 1
        if not stop_when_known:
            _olarm_backfill_cursor["until"] = until
        time.sleep(pace_s)
    if not stop_when_known and info["stopped"] == "no rows":
        _olarm_backfill_cursor["done"] = True
    _rebuild_activity_cache(_stale_panel(), str(_activity_cache.get("last_key") or ""))
    _live_state_save()
    return info


_live_debug: dict[str, Any] = {}


def _olarm_backfill_thread() -> None:
    try:
        _olarm_backfill_info["startedAt"] = time.time()
        _olarm_backfill_info.update(_olarm_backfill())
    except Exception as exc:  # history paging must never take the live loop down
        import traceback
        _olarm_backfill_info["error"] = f"{exc.__class__.__name__}: {exc}"
        _olarm_backfill_info["trace"] = traceback.format_exc()[-800:]
    _olarm_backfill_info["doneAt"] = time.time()


def _olarm_live_loop() -> None:
    last_events_at = 0.0
    last_area_sig = ""
    backoff_until = 0.0
    threading.Thread(target=_olarm_backfill_thread, name="arial-olarm-backfill", daemon=True).start()
    while not _live_stop.wait(_LIVE_FAST_POLL_SEC if time.time() < _live_fast_until else _LIVE_DEVICE_POLL_SEC):
        _live_debug["loopAt"] = time.time()
        if not _olarm_token() or time.time() < backoff_until:
            _live_debug["skip"] = "no token" if not _olarm_token() else "backoff"
            continue
        _live_debug.pop("skip", None)
        try:
            now = time.time()
            events_resp = None
            area_changed = False
            panel_changed = False
            with _olarm_http_lock:
                client = _olarm_sync_client()
                resp = client.get(
                    f"/api/v4/devices/{HANSEKOP_ID}",
                    params=_OLARM_DEV_PARAMS,
                )
                if resp.status_code == 429:
                    backoff_until = time.time() + 15.0
                    continue
                if resp.status_code == 200:
                    raw = resp.json()
                    if isinstance(raw, dict):
                        panel = enrich_device(raw)
                        _cached_panel(panel)
                        panel_changed = True
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
                        params={"pageLength": _OLARM_PAGE},
                    )
                    last_events_at = now
                    if events_resp.status_code == 429:
                        backoff_until = time.time() + 15.0
            if events_resp is not None and events_resp.status_code == 200:
                payload = events_resp.json()
                rows = payload.get("data") if isinstance(payload, dict) else []
                if isinstance(rows, list):
                    rows = [r for r in rows if isinstance(r, dict)]
                    known_before = {olarm_event_key(r) for r in rows} & set(_olarm_store.keys())
                    apply_olarm_events(rows, _stale_panel())
                    if rows and not known_before:
                        # A full page of unseen events: more than 40 arrived since the last poll. Fill the gap.
                        _olarm_backfill(max_pages=10, pace_s=2.0, stop_when_known=True)
            if panel_changed or events_resp is not None:
                _live_state_save()
                _live_debug["savedAt"] = time.time()
        except Exception as exc:
            _live_debug["lastError"] = f"{exc.__class__.__name__}: {exc}"
            _live_debug["lastErrorAt"] = time.time()
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


IGNORE_ZONES_PATH = Path("/var/www/sailingsa/data/arial_ignore_zones.json")
_ignore_zones_cache: dict[str, Any] = {"at": 0.0, "zones": set()}


def _ignored_zones() -> set[int]:
    """Faulty zones (permanently open) hidden from the panel until repaired: {site_id: [zone numbers]} in
    arial_ignore_zones.json. Re-read every 30 s so edits need no restart. Only affects display/readiness."""
    now = time.time()
    if now - float(_ignore_zones_cache["at"]) > 30:
        try:
            cfg = json.loads(IGNORE_ZONES_PATH.read_text(encoding="utf-8"))
            _ignore_zones_cache["zones"] = {int(z) for z in (cfg.get(SITE_ID) or [])}
        except (OSError, ValueError, TypeError):
            _ignore_zones_cache["zones"] = set()
        _ignore_zones_cache["at"] = now
    return _ignore_zones_cache["zones"]


def enrich_device(device: dict[str, Any]) -> dict[str, Any]:
    """Attach display labels for areas and zones. Does not strip raw Olarm fields."""
    profile = device.get("deviceProfile") or {}
    state = device.get("deviceState") or {}
    ignored = _ignored_zones()
    if ignored:
        # Ready-state override: if every open zone is a known-faulty (ignored) one, the panel is shown as ready.
        raw_zone_states = list(state.get("zones") or [])
        open_zones = {i + 1 for i, zs in enumerate(raw_zone_states) if str(zs) == "a"}
        if open_zones and open_zones <= ignored:
            state = dict(state)
            state["areas"] = ["disarm" if str(a) == "notready" else a for a in _as_list(state.get("areas"))]
    area_labels = list(profile.get("areasLabels") or [])
    area_states = _as_list(state.get("areas"))
    area_details = _as_list(state.get("areasDetail"))
    area_stamps = _as_list(state.get("areasStamp"))
    areas = []
    countdown = None
    limit = int(profile.get("areasLimit") or max(len(area_labels), len(area_states), 0))
    for i in range(limit):
        label = (SITE_AREA_LABELS[i] if i < len(SITE_AREA_LABELS) else "") or (area_labels[i] if i < len(area_labels) else "") or (SITE_AREA_LABEL if i == 0 else f"Area {i + 1}")   # site override -> Olarm label -> unnamed first area = site label
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
        if str(zs) == "b" or (i + 1) in ignored:
            continue   # bypassed or known-faulty zones are not working zones: keep them off the panel until repaired
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
    try:
        out["arialPower"].update(_ac_track(bool(out["arialPower"].get("acOk"))))
    except Exception:
        pass
    if _last_keypad:
        out["arialActor"] = dict(_last_keypad)
    return out


# ---- Panel AC (mains) failure tracking: remembers when Olarm's powerAC left "ok", per site, so the keypad can
# show "A/C FAILURE <time/date>" for as long as the failure lasts. Olarm exposes only the current state, no event.
_AC_STATE_PATH = Path("/var/www/sailingsa/data") / f"arial_ac_state_{SITE_ID}.json"   # www-data-writable (api/data is root-owned)
_ac_state: dict[str, Any] = {"loaded": False, "acOk": None, "failSince": None, "restoredAt": None, "lastFailSince": None}
_ac_lock = threading.Lock()


def _ac_track(ac_ok: bool) -> dict[str, Any]:
    """Update the persisted AC state with the panel's current acOk; return fields for arialPower."""
    now_ms = int(time.time() * 1000)
    with _ac_lock:
        if not _ac_state["loaded"]:
            _ac_state["loaded"] = True
            try:
                saved = json.loads(_AC_STATE_PATH.read_text())
                for k in ("acOk", "failSince", "restoredAt", "lastFailSince"):
                    if k in saved:
                        _ac_state[k] = saved[k]
            except Exception:
                pass
        prev = _ac_state.get("acOk")
        changed = prev is not ac_ok
        if changed:
            _ac_state["acOk"] = ac_ok
            if ac_ok is False and _ac_state.get("failSince") is None:
                # prev None = first observation while already failed: time unknown, leave failSince None
                if prev is True:
                    _ac_state["failSince"] = now_ms
                    _ac_state["lastFailSince"] = now_ms
            if ac_ok is True and prev is False:
                _ac_state["restoredAt"] = now_ms
                _ac_state["failSince"] = None
            try:
                _AC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
                tmp = _AC_STATE_PATH.with_suffix(".tmp")
                tmp.write_text(json.dumps({k: _ac_state[k] for k in ("acOk", "failSince", "restoredAt", "lastFailSince")}))
                tmp.replace(_AC_STATE_PATH)
            except Exception:
                pass
        return {"acFailSince": _ac_state.get("failSince"), "acRestoredAt": _ac_state.get("restoredAt")}


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


def normalize_olarm_event(event: dict[str, Any] | None) -> dict[str, Any]:
    """Olarm quirks: a disarm from the app/panel arrives as eventState 'notready' with an eventMsg 'DISARMED - ...'."""
    if not isinstance(event, dict):
        return {}
    action = str(event.get("eventAction") or "").strip().lower()
    state = str(event.get("eventState") or "").strip().lower()
    msg = str(event.get("eventMsg") or "").strip().lower()
    if action == "area" and state == "notready" and msg.startswith("disarmed"):
        out = dict(event)
        out["eventState"] = "disarm"
        return out
    return event


def classify_olarm_event(event: dict[str, Any] | None) -> str:
    event = normalize_olarm_event(event or {})
    action = str(event.get("eventAction") or "").strip().lower()
    state = str(event.get("eventState") or "").strip().lower()
    msg = str(event.get("eventMsg") or "").strip().lower()
    if action in POWER_EVENT_ACTIONS or "power" in msg or "battery" in msg or "mains" in msg:
        return "power"
    if action in ALARM_EVENT_ACTIONS or state in {"alarm", "emergency", "panic", "fire", "medical"} or "in alarm" in msg or msg.startswith("alarm"):
        return "zones"
    if action in AREA_EVENT_ACTIONS or state in {"arm", "disarm", "stay", "sleep", "countdown"} or "countdown" in msg:
        return "areas"
    if action in ZONE_EVENT_ACTIONS or action.startswith("zone"):
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
    return SITE_AREA_LABEL


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
    event = normalize_olarm_event(event or {})
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
    return "Remote" if str(actor or "").strip() in KEYPAD_ACTORS else ""


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


def _area_label_for(num: int) -> str:
    panel = _stale_panel() or {}
    for area in panel.get("arialAreas") or []:
        if isinstance(area, dict) and int(area.get("num") or 0) == num:
            label = str(area.get("label") or "").strip()
            if label:
                return label
    return _hansekop_area_label()


def _remember_keypad(code: str, cmd: str, num: int = 1) -> dict[str, Any]:
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
        "num": int(num or 1),
        "area": _area_label_for(int(num or 1)),
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
        if label in KEYPAD_ACTORS:
            return label
    return _map_our_actor(
        str(event.get("userFullname") or event.get("userName") or event.get("user") or "")
    )


def _matching_press_ms(state_token: str, ev_ms: int) -> int:
    """Keypad press (ms) that this Olarm area event confirms: same arm/disarm class, closest in time, within the
    match window and not after the panel event by more than a few seconds."""
    _load_keypad_log()
    best = 0
    for rec in _keypad_log:
        st = _KEYPAD_CMD_STATE.get(str(rec.get("action") or ""))
        if not st:
            continue
        same = (state_token == "disarm" and st == "disarm") or (state_token in {"arm", "stay", "sleep"} and st != "disarm")
        if not same:
            continue
        try:
            kp_ms = int(float(rec.get("at") or 0) * 1000)
        except (TypeError, ValueError):
            continue
        if not kp_ms or kp_ms - ev_ms > 5000 or ev_ms - kp_ms > _KEYPAD_MATCH_MS:
            continue
        if not best or abs(ev_ms - kp_ms) < abs(ev_ms - best):
            best = kp_ms
    return best


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
        press_ms = _matching_press_ms(_area_state_token(str(row.get("state") or "")), _event_time_ms({"eventTime": row.get("at")}))
        if press_ms and not row.get("confirmedAt"):   # idempotent: cached bundles are re-stamped on every request
            row["confirmedAt"] = row.get("at")
            row["at"] = press_ms
            row["time"], row["date"] = _sa_stamp(press_ms)
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
        actor = _map_our_actor(str(rec.get("from") or rec.get("label") or "")) or str(rec.get("from") or "").strip()
        if actor not in KEYPAD_ACTORS:
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
                "activity": _activity_line(label, state_lab, actor, "Remote")
                            + ("  \u26a0 not confirmed by panel" if time.time() * 1000 - kp_ms > 90_000 else ""),
                "actor": actor,
                "via": "Remote",
                "msg": "",
                "num": 1,
                "action": "area",
                "at": kp_ms,
                "confirmedAt": None,
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
    added = _olarm_store_add(rows)
    with _lock:
        if newest and not added and newest == str(_activity_cache.get("last_key") or "") and _activity_cache.get("data"):
            _activity_cache["at"] = time.time()
            data = _activity_cache.get("data")
            if isinstance(data, dict):
                data["ack"] = True
                data["lastKey"] = newest
            return "ack"
    _rebuild_activity_cache(device, newest)
    return "insert" if newest else "empty"


_activity_payload_memo: dict[str, Any] = {"key": None, "out": None, "at": 0.0}


def _activity_payload(bundle: dict[str, Any] | None, ack: bool) -> dict[str, Any]:
    with _lock:
        memo_key = (int(_activity_cache.get("seq") or 0), len(_keypad_log), id(bundle))
    memo = _activity_payload_memo
    if memo["key"] == memo_key and memo["out"] is not None and time.time() - float(memo["at"]) < 2.0:
        out = dict(memo["out"])
        out["ack"] = ack
        return out
    out = _stamp_activity_actors(bundle if isinstance(bundle, dict) else {"ok": True, "events": [], "power": {}})
    with _lock:
        last_key = str(_activity_cache.get("last_key") or "")
    out["lastKey"] = last_key or out.get("lastKey") or ""
    events = out.get("events") if isinstance(out.get("events"), list) else []
    digest = hashlib.sha256("\n".join(olarm_event_key(e) for e in events if isinstance(e, dict)).encode("utf-8")).hexdigest()
    out["checksum"] = digest[:16]
    out["ack"] = ack
    out["ok"] = True
    _activity_payload_memo.update({"key": memo_key, "out": dict(out), "at": time.time()})
    return out


def format_olarm_event(event: dict[str, Any], device: dict[str, Any] | None = None) -> dict[str, Any]:
    event = normalize_olarm_event(event)
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
    if action.lower().startswith("area") and num in areas:
        label = str(areas[num].get("label") or "").strip()  # area alarm rows must not borrow a zone's name
    elif tab in {"zones", "alarms"} and num in zones:
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
    if not actor and tab == "areas" and str(event.get("eventState") or "").lower() in {"arm", "disarm", "stay", "sleep"}:
        # No keypad user matched: it came from the Olarm app / panel. Show the source, never the Olarm account name.
        if str(event.get("userFullname") or "").strip():
            via = "App"
        elif str(event.get("eventState") or "").lower() in {"arm", "stay", "sleep"}:
            via = "Auto"      # no user at all: the panel's own auto-arm schedule
        else:
            via = "Panel"     # disarmed at the physical panel keypad
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
        "olarmUser": str(event.get("userFullname") or "").strip(),   # who acted in the Olarm app; used for WhatsApp routing
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


SITE_EXIT_DELAY = int((os.getenv("ARIAL_EXIT_DELAY") or "0").strip() or 0)


def _profile_exit_delay(profile: dict[str, Any]) -> int:
    if SITE_EXIT_DELAY > 0:
        return SITE_EXIT_DELAY   # panel's real exit delay, set per site (Olarm's profile does not publish it)
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


def _site_sources() -> dict[str, Any]:
    """Which listeners this site URL uses. Sources stay separate; a site only subscribes."""
    paths = [
        Path(os.getenv("ARIAL_SOURCES_REGISTRY") or ""),
        Path("/opt/arial-sources/registry.json"),
        Path(__file__).resolve().parent / "arial" / "sources" / "registry.json",
    ]
    data: dict[str, Any] = {}
    for path in paths:
        if path and path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["_path"] = str(path)
                break
            except (OSError, ValueError):
                continue
    site = (data.get("sites") or {}).get(SITE_ID) or {}
    catalog = data.get("sources") or {}
    uses = []
    for item in site.get("uses") or []:
        src_id = item.get("source")
        uses.append({**(catalog.get(src_id) or {}), **item, "source": src_id})
    return {
        "ok": True,
        "rule": data.get("rule"),
        "site": {"id": SITE_ID, "url": site.get("url"), "label": site.get("label") or SITE_LABEL},
        "uses": uses,
    }


@router.get("/api/arial/status")
def arial_status(request: Request):
    user = _session_user(request)
    return {
        "ok": True,
        "dev": True,
        "olarmConfigured": bool(_olarm_token()),
        "tuyaConfigured": tuya_configured(),
        "tuyaPaused": True,
        "site": {"id": SITE_ID, "label": SITE_LABEL, "tuya": SITE_TUYA, "deviceId": HANSEKOP_ID},
        "sources": _site_sources(),
        "signedIn": bool(user),
        "me": _public_user(user) if user else None,
        "nextDomain": "arial.co.za",
    }


@router.get("/api/arial/sources")
def arial_sources():
    return _site_sources()


@router.get("/api/arial/tuya/probe")
def arial_tuya_probe(device_id: Optional[str] = None):
    """Mint a token and GET /v1.0/devices/{id}/status. Does not unpause TUYS UI."""
    return tuya_probe(device_id)


TUYA_LIGHTS_ID = "bf7f4a91ef39b11261xcua"  # HSK - Light Switch x4 (CB04-SBL)
LIGHT_SWITCHES = ("switch_1", "switch_2", "switch_3", "switch_4")


def _tuya_send_commands(creds: dict[str, str], device: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    _tuya_ensure_token(creds)
    access = str((_tuya_token or {}).get("access_token") or "")
    if not access:
        return {"success": False, "msg": "no token"}
    t = int(time.time() * 1000)
    path = f"/v1.0/devices/{device}/commands"
    body = json.dumps({"commands": commands}, separators=(",", ":"))
    body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    str_to_sign = f"POST\n{body_sha}\n\n{path}"
    sign = tuya_sign(creds["secret"], creds["client_id"], t, str_to_sign, access_token=access)
    headers = {
        "client_id": creds["client_id"],
        "sign": sign,
        "sign_method": "HMAC-SHA256",
        "t": str(t),
        "lang": "en",
        "access_token": access,
        "Content-Type": "application/json",
    }
    client = _tuya_sync_client(creds["endpoint"])
    resp = client.post(path, headers=headers, content=body)
    try:
        data = resp.json()
    except Exception:
        data = {"success": False, "code": resp.status_code, "msg": (resp.text or "")[:240]}
    return data if isinstance(data, dict) else {"success": False, "msg": "non-object tuya response"}


def _lights_payload(device: str) -> dict[str, Any]:
    probe = tuya_probe(device)
    switches: dict[str, bool | None] = {}
    for row in probe.get("status") or []:
        if isinstance(row, dict) and row.get("code") in LIGHT_SWITCHES:
            switches[str(row["code"])] = bool(row.get("value"))
    return {
        "ok": bool(probe.get("ok")),
        "deviceId": device,
        "online": probe.get("deviceOk"),
        "switches": [{"code": c, "on": switches.get(c)} for c in LIGHT_SWITCHES],
        "tuyaMsg": probe.get("tuyaMsg") or "",
    }


@router.get("/api/arial/tuya/lights")
def arial_tuya_lights(device_id: Optional[str] = None):
    return _lights_payload((device_id or TUYA_LIGHTS_ID).strip())


@router.get("/api/arial/tuya/lights_multi")
def arial_tuya_lights_multi(ids: str = ""):
    """State of several light devices in one call (sharing transport only). Switch codes are returned as
    '<deviceId>:<switch_n>' so the shared lights popup can address gangs on different devices."""
    if not HOME_TRANSPORT:
        raise HTTPException(status_code=503, detail="multi-device lights need a home transport")
    out_devices, switches, any_ok = [], [], False
    for dev in [d.strip() for d in ids.split(",") if d.strip()][:40]:
        view = _sharing_get(f"/devices/{dev}")
        if not view or not view.get("ok"):
            out_devices.append({"deviceId": dev, "online": False, "error": (view or {}).get("error") or "worker unavailable"})
            continue
        any_ok = True
        st = view.get("status") or {}
        online = bool(view.get("online"))
        out_devices.append({"deviceId": dev, "name": view.get("name"), "online": online})
        for c in sorted(k for k in st if re.fullmatch(r"switch_\d+", k)):
            switches.append({"code": f"{dev}:{c}", "on": (bool(st[c]) if online else None)})
    return {"ok": any_ok, "devices": out_devices, "switches": switches, "online": any_ok,
            "tuyaMsg": "" if any_ok else "sharing worker unavailable"}


@router.post("/api/arial/meter/eskom")
async def arial_meter_eskom(request: Request):
    """Keypad-PIN protected Eskom sync: {code, reading}. Stores offset = Eskom reading - current lifetime register,
    so the card can show 'Eskom (calc)' = register + offset from then on. Read-only towards the meter."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = str(body.get("code") or "").strip()
    if code not in KEYPAD_CODES:
        raise HTTPException(status_code=401, detail="Invalid code")
    try:
        reading = float(body.get("reading"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="reading (kWh) required")
    if not 0 <= reading < 1e8:
        raise HTTPException(status_code=400, detail="reading out of range")
    latest = _meter_fresh(time.time())
    if not latest or latest.get("meterKwh") is None:
        raise HTTPException(status_code=503, detail="meter register not available right now")
    lifetime = float(latest["meterKwh"])
    now = time.time()
    refs = _meter_refs_write({"eskomOffsetKwh": round(reading - lifetime, 3), "eskomReading": reading,
                              "eskomSyncedAt": now, "eskomSyncedRegisterKwh": lifetime, "eskomBy": KEYPAD_CODES[code]})
    _remember_keypad(code, "eskom-sync")
    return {"ok": True, "eskomReading": reading, "registerKwh": lifetime, "offsetKwh": refs["eskomOffsetKwh"],
            "eskomCalcKwh": round(lifetime + refs["eskomOffsetKwh"], 1), "actor": KEYPAD_CODES[code]}


@router.post("/api/arial/tuya/switch")
async def arial_tuya_switch(request: Request):
    """Keypad-PIN protected light switching: {code, switch: switch_n|all, value: bool}."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = str(body.get("code") or "").strip()
    if code not in KEYPAD_CODES:
        raise HTTPException(status_code=401, detail="Invalid code")
    device = str(body.get("device_id") or TUYA_LIGHTS_ID).strip()
    target = str(body.get("switch") or "").strip()
    value = bool(body.get("value"))
    if target == "all":
        commands = [{"code": c, "value": value} for c in LIGHT_SWITCHES]
    elif target in LIGHT_SWITCHES or re.fullmatch(r"switch_\d+", target):
        commands = [{"code": target, "value": value}]
    else:
        raise HTTPException(status_code=400, detail="Unknown switch")
    if HOME_TRANSPORT:
        # Forward to this site's home collector only (Smart Life :8007 or CBI :8010).
        try:
            r = httpx.post(SHARING_CTRL_URL + "/light", json={"device_id": device, "switch": target, "value": value},
                           headers={"Authorization": f"Bearer {SHARING_CTRL_TOKEN}"}, timeout=12.0)
            result = r.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"home worker: {exc}") from exc
        if not isinstance(result, dict) or not result.get("ok"):
            raise HTTPException(status_code=502, detail=f"{TUYA_TRANSPORT}: {(result or {}).get('error') or 'command failed'}")
        _remember_keypad(code, f"lights-{target}-{'on' if value else 'off'}")
        out = _lights_payload(device)
        if result.get("switches"):
            out.update({"ok": True, "online": result.get("online"), "switches": result["switches"]})
        out.update({"actor": KEYPAD_CODES[code], "confirmed": bool(result.get("confirmed")),
                    "confirmSource": result.get("confirmSource"), "latencyS": result.get("latencyS"),
                    "source": result.get("source") or TUYA_TRANSPORT})
        return out
    creds = _tuya_creds()
    if not (creds["client_id"] and creds["secret"]):
        raise HTTPException(status_code=503, detail="Tuya not configured")
    with _tuya_http_lock:
        result = _tuya_send_commands(creds, device, commands)
        if int(result.get("code") or 0) == TUYA_CODE_TOKEN_INVALID:
            _tuya_reset_token()
            result = _tuya_send_commands(creds, device, commands)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=f"Tuya: {result.get('msg') or result.get('code') or 'command failed'}")
    _remember_keypad(code, f"lights-{target}-{'on' if value else 'off'}")
    out = _lights_payload(device)
    out["actor"] = KEYPAD_CODES[code]
    return out


@router.get("/api/arial/tuya/history")
def arial_tuya_history(minutes: int = 60, limit: int = 2000):
    """Persisted real readings (server sampler / LAN pushes) for the mains meter. Read-only; gaps stay gaps."""
    minutes = max(1, min(int(minutes), 7 * 24 * 60))
    limit = max(1, min(int(limit), 5000))
    now = time.time()
    rows = _meter_history_rows(TUYA_MAINS_METER_ID, now - minutes * 60, now + 60, limit)
    return {"ok": True, "deviceId": TUYA_MAINS_METER_ID, "minutes": minutes, "count": len(rows), "rows": rows,
            "pollS": _ENERGY_SAMPLE_S, "sampler": _meter_sampler_state()}


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
        params={"page": 1, "pageLength": 100, **_OLARM_DEV_PARAMS},
    )
    devices = [enrich_device(d) for d in (raw.get("data") or [])]
    return {
        "ok": True,
        "userId": raw.get("userId"),
        "pageCount": raw.get("pageCount"),
        "devices": devices,
    }


def _with_ac_failure(resp: dict[str, Any]) -> dict[str, Any]:
    """Stamp acFailSince/acRestoredAt onto the served panel (runs in whichever process answers /panel)."""
    try:
        dev = resp.get("device") if isinstance(resp, dict) else None
        power = dev.get("arialPower") if isinstance(dev, dict) else None
        if isinstance(power, dict) and "acOk" in power:
            power.update(_ac_track(bool(power.get("acOk"))))
    except Exception:
        pass
    return resp


@router.get("/api/arial/panel")
async def arial_panel():
    return _with_ac_failure(await _arial_panel_inner())


async def _arial_panel_inner():
    _ensure_live_session()
    cached = _cached_panel()
    if cached is not None:
        return {"ok": True, "device": cached, "live": True}
    stale = _stale_panel()
    if stale is not None:
        # Poller refreshes every 1-3 s; answering from the last snapshot keeps the keypad instant and off Olarm's rate limit.
        return {"ok": True, "device": stale, "live": True, "stale": True}
    stale = _stale_panel()
    if stale is None and _live_state_load(force=True):
        stale = _stale_panel()
    if stale is not None and _live_role:
        # A poller owns Olarm for this site; never race it with extra calls, serve its last snapshot.
        return {"ok": True, "device": stale, "live": False}
    try:
        raw = await _olarm_request(
            "GET",
            f"/api/v4/devices/{HANSEKOP_ID}",
            params=_OLARM_DEV_PARAMS,
        )
    except HTTPException:
        if stale is not None:
            return {"ok": True, "device": stale, "live": False}
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


WHATSAPP_LOG = Path(os.getenv("ARIAL_WHATSAPP_LOG") or "/var/www/sailingsa/data/whatsapp_log.jsonl")


def _mask_number(n) -> str:
    s = re.sub(r"\D", "", str(n or ""))
    return (s[:4] + "\u2022\u2022\u2022" + s[-4:]) if len(s) > 8 else s


TUYA_ICON_MANIFEST = Path("/var/www/sailingsa/assets/tuya/manifest.json")
TUYA_ICON_FALLBACK = "/assets/tuya/fallback/device.svg"
_icon_manifest_cache: dict[str, Any] = {"mtime": 0.0, "data": {}}


def _tuya_manifest() -> dict[str, Any]:
    try:
        mt = TUYA_ICON_MANIFEST.stat().st_mtime
        if mt != _icon_manifest_cache["mtime"]:
            _icon_manifest_cache["data"] = json.loads(TUYA_ICON_MANIFEST.read_text(encoding="utf-8"))
            _icon_manifest_cache["mtime"] = mt
    except (OSError, ValueError):
        pass
    return _icon_manifest_cache["data"] or {}


def get_tuya_icon(device_id: str = "", product_id: str = "", category: str = "") -> str:
    """Local icon path for a Tuya device: exact cached device icon -> product icon -> category icon -> generic fallback.
    Only ever returns /assets/tuya/... paths (never a CDN URL)."""
    m = _tuya_manifest()
    for table, key in (("devices", device_id), ("products", product_id), ("categories", category)):
        rec = (m.get(table) or {}).get(key or "")
        p = rec and rec.get("local_path")
        if p and str(p).startswith("/assets/tuya/"):
            return p
    if device_id:   # unknown device but known category via its manifest siblings
        for rec in (m.get("devices") or {}).values():
            if category and rec.get("category") == category and str(rec.get("local_path", "")).startswith("/assets/tuya/categories/"):
                return rec["local_path"]
    return TUYA_ICON_FALLBACK


@router.get("/api/arial/tuya/icon")
def arial_tuya_icon(device: str = "", product: str = "", category: str = ""):
    return {"ok": True, "local_path": get_tuya_icon(device, product, category)}


@router.get("/api/arial/home/sensors")
def arial_home_sensors():
    """Home devices for this site: Smart Life (sharing) or CBI. Read-only from that site's home API."""
    if not HOME_TRANSPORT:
        raise HTTPException(status_code=503, detail="home transport not enabled")
    from urllib.parse import quote
    home_key = CBI_HOME_ID if TUYA_TRANSPORT == "cbi" else (os.getenv("ARIAL_TUYA_HOME") or "")
    view = _home_api_get("/home?home=" + quote(home_key or ""))
    if not view or not view.get("ok"):
        raise HTTPException(status_code=502, detail=(view or {}).get("error") or "home api unavailable")
    try:
        # slot -> person, e.g. {"fingerprint": {"17": "Tim"}, "password": {"16": "Kevin"}, "card": {"13": "Birgitta"}}
        view["lockUsers"] = json.loads(Path("/var/www/sailingsa/data/home_lock_users.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        view["lockUsers"] = {}
    try:
        view["lightNames"] = json.loads(Path("/var/www/sailingsa/data/home_light_names.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        view["lightNames"] = {}
    view["icons"] = {d["id"]: get_tuya_icon(d.get("id", ""), d.get("product_id") or "", d.get("category") or "") for d in view.get("devices") or [] if d.get("id")}
    return view


@router.post("/api/arial/home/lock_user")
async def arial_home_lock_user(request: Request):
    """Keypad-PIN protected: name a door-lock credential slot. {code, method: fingerprint|password|card|face|temporary|app, slot, name}"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = str(body.get("code") or "").strip()
    if code not in KEYPAD_CODES:
        raise HTTPException(status_code=401, detail="Invalid code")
    method = str(body.get("method") or "").strip().lower()
    slot = str(body.get("slot") or "").strip()
    name = re.sub(r"[^\w .'\-]", "", str(body.get("name") or "")).strip()[:32]
    if method not in {"fingerprint", "password", "card", "face", "temporary", "app"} or not slot.isdigit() or not name:
        raise HTTPException(status_code=400, detail="method, numeric slot and name required")
    path = Path("/var/www/sailingsa/data/home_lock_users.json")
    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            data = json.loads(fh.read() or "{}")
        except ValueError:
            data = {}
        data.setdefault(method, {})[slot] = name
        data.setdefault("_history", []).append({"at": time.time(), "by": KEYPAD_CODES[code], "method": method, "slot": slot, "name": name})
        fh.seek(0); fh.truncate(); fh.write(json.dumps(data, indent=1, ensure_ascii=False))
    _remember_keypad(code, f"lock-user-{method}-{slot}")
    return {"ok": True, "method": method, "slot": slot, "name": name}


WINDGURU_SPOT = os.getenv("ARIAL_WINDGURU_SPOT") or "1309608"
WINDGURU_CACHE = Path("/var/www/sailingsa/data/windguru_%s.json" % WINDGURU_SPOT)
_wg_lock = threading.Lock()


def _windguru_fetch() -> dict[str, Any]:
    """GFS 13 km hourly forecast from Windguru's own site API (same calls its page makes). Cached 1 h on disk."""
    hdrs = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
            "Referer": f"https://www.windguru.cz/{WINDGURU_SPOT}"}
    with httpx.Client(timeout=25.0, headers=hdrs) as c:
        spot = c.get("https://www.windguru.cz/int/iapi.php", params={"q": "forecast_spot", "id_spot": WINDGURU_SPOT}).json()
        tab = (spot.get("tabs") or [{}])[0]
        want = int(os.getenv("ARIAL_WINDGURU_MODEL") or 117)          # 117 = ECMWF IFS-HRES 9 km; 3 = GFS 13 km
        arr = tab.get("id_model_arr") or []
        m = next((x for x in arr if int(x.get("id_model") or 0) == want), None) or next((x for x in arr if int(x.get("id_model") or 0) == 3), None)
        if not m:
            raise RuntimeError("no usable model offered for spot")
        fc = c.get("https://www.windguru.cz/int/iapi.php", params={"q": "forecast", "id_model": m["id_model"], "rundef": m["rundef"], "initstr": m["initstr"],
                                                                    "id_spot": WINDGURU_SPOT, "WGCACHEABLE": 21600, "cachefix": m.get("cachefix", "")}).json()
    f = fc.get("fcst") or {}
    init = int(f.get("initstamp") or 0)
    hours = f.get("hours") or []
    rows = []
    for i, hh in enumerate(hours):
        def g(k):
            v = (f.get(k) or [])
            return v[i] if i < len(v) else None
        rows.append({"t": init + int(hh) * 3600, "spd": g("WINDSPD"), "gust": g("GUST"), "dir": g("WINDDIR"), "tmp": g("TMP"),
                     "rain": g("APCP1"), "cloud": g("TCDC"), "slp": g("SLP")})
    return {"ok": True, "spot": WINDGURU_SPOT, "model": f.get("model_name") or str(m["id_model"]), "init": init, "fetchedAt": time.time(),
            "lat": fc.get("lat"), "lon": fc.get("lon"), "sunrise": fc.get("sunrise"), "sunset": fc.get("sunset"), "units": "knots", "rows": rows}


FORECAST_DB = Path("/var/www/sailingsa/data/forecast_history.sqlite")


def _forecast_store(data: dict[str, Any]) -> None:
    """Keep every model run: (issued, model, target hour) -> wind/gust/dir/temp/pressure/rain/cloud. Rows are never
    overwritten, so the same target hour accumulates one row per run (lead-time analysis) and can be compared with
    the station's recorded actuals to learn the site bias."""
    import sqlite3
    con = sqlite3.connect(FORECAST_DB, timeout=10)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS forecast (issued INTEGER NOT NULL, model TEXT NOT NULL, spot TEXT NOT NULL, target INTEGER NOT NULL, "
                    "spd REAL, gust REAL, dir REAL, tmp REAL, slp REAL, rain REAL, cloud REAL, PRIMARY KEY (issued, model, spot, target))")
        con.executemany("INSERT OR IGNORE INTO forecast VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        [(int(data["init"]), str(data["model"]), str(data["spot"]), int(r["t"]), r.get("spd"), r.get("gust"), r.get("dir"),
                          r.get("tmp"), r.get("slp"), r.get("rain"), r.get("cloud")) for r in data.get("rows") or []])
        con.commit()
    finally:
        con.close()


@router.get("/api/arial/home/forecast_vs_actual")
def arial_home_fva(hours: int = 24):
    """Forecast (latest run per target hour) next to what the station recorded, for the last N hours. Knots / hPa / C."""
    import sqlite3
    out = []
    since = int(time.time() - max(1, min(hours, 24 * 30)) * 3600)
    try:
        fcon = sqlite3.connect(FORECAST_DB, timeout=10)
        rows = fcon.execute("SELECT target, MAX(issued), spd, gust, dir, tmp, slp FROM forecast WHERE target>=? AND target<=? GROUP BY target ORDER BY target",
                            (since, int(time.time()))).fetchall()
        fcon.close()
        # actuals come from the sharing worker's event log (its own process/user), via its history endpoint
        view = _home_api_get("/home") or {}
        wxdev = next((d["id"] for d in view.get("devices") or [] if d.get("category") == "qxj"), None)
        span_h = max(1, int((time.time() - since) / 3600) + 1)
        def hist(code):
            r = _home_api_get(f"/home/history?dev={wxdev}&code={code}&hours={span_h}", timeout=15.0) if wxdev else None
            return [(float(t), float(v)) for t, v in (r or {}).get("rows") or [] if isinstance(v, (int, float))]
        cur_h, gust_h, slp_h = hist("dp131"), hist("windspeed_gust"), hist("atmospheric_pressture")
        def actual(rows_, t0, t1, agg="avg"):
            vals = [v for t, v in rows_ if t0 <= t < t1]
            if not vals:
                return None
            return max(vals) if agg == "max" else sum(vals) / len(vals)
        for target, issued, spd, gust, d, tmp, slp in rows:
            t0, t1 = target - 1800, target + 1800
            a_cur, a_gust, a_slp = actual(cur_h, t0, t1), actual(gust_h, t0, t1, "max"), actual(slp_h, t0, t1)
            out.append({"t": target, "issued": issued, "lead_h": round((target - issued) / 3600, 1),
                        "fc": {"spd": spd, "gust": gust, "dir": d, "tmp": tmp, "slp": slp},
                        "actual": {"spd": round(a_cur / 18.52, 1) if a_cur is not None else None, "gust": round(a_gust / 18.52, 1) if a_gust is not None else None,
                                   "slp": round(a_slp, 1) if a_slp is not None else None}})
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "rows": out}


@router.get("/api/arial/home/windguru")
def arial_home_windguru():
    with _wg_lock:
        try:
            cached = json.loads(WINDGURU_CACHE.read_text(encoding="utf-8"))
            if time.time() - float(cached.get("fetchedAt") or 0) < 3600:
                return cached
        except (OSError, ValueError):
            cached = None
        try:
            data = _windguru_fetch()
            WINDGURU_CACHE.write_text(json.dumps(data), encoding="utf-8")
            try:
                _forecast_store(data)
            except Exception as exc:  # noqa: BLE001
                log.warning("forecast store failed: %s", exc)
            return data
        except Exception as exc:  # noqa: BLE001
            if cached:
                cached["stale"] = True
                return cached
            raise HTTPException(status_code=502, detail=f"windguru: {exc}") from exc


@router.get("/api/arial/home/history")
def arial_home_history(dev: str, code: str, hours: float = 24):
    if not HOME_TRANSPORT:
        raise HTTPException(status_code=503, detail="home transport not enabled")
    view = _home_api_get(f"/home/history?dev={dev}&code={code}&hours={hours}", timeout=15.0)
    if not view or not view.get("ok"):
        raise HTTPException(status_code=502, detail=(view or {}).get("error") or "home api unavailable")
    return view


@router.get("/api/arial/whatsapp/log")
async def arial_whatsapp_log(limit: int = 80):
    """Admin list of WhatsApp alerts sent / replies handled for this site (from the shared watcher log)."""
    rows = []
    try:
        with open(WHATSAPP_LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                site = str(r.get("site") or "")
                if site and site != SITE_ID:
                    continue
                t = float(r.get("t") or 0)
                dt = datetime.fromtimestamp(t, _SAST) if t else None
                rows.append({
                    "at": int(t * 1000), "date": dt.strftime("%d %b %Y") if dt else "", "time": dt.strftime("%H:%M") if dt else "",
                    "dir": r.get("dir") or "out", "kind": r.get("kind") or "alert", "to": r.get("to") or "",
                    "from": r.get("from") or "", "number": _mask_number(r.get("number")), "ok": bool(r.get("ok", True)),
                    "acks": r.get("acks") or [], "error": r.get("error"), "text": str(r.get("text") or ""),
                    "trigger": r.get("trigger") or "", "recovered": bool(r.get("recovered")),
                })
    except OSError:
        pass
    rows.sort(key=lambda x: x["at"], reverse=True)
    return {"ok": True, "site": SITE_ID, "rows": rows[: max(1, min(int(limit or 80), 500))]}


@router.get("/api/arial/activity")
async def arial_activity():
    _ensure_live_session()
    with _lock:
        cached = _activity_cache.get("data")
        last_at = float(_activity_cache.get("at") or 0)
    if cached is None and _live_state_load(force=True):
        with _lock:
            cached = _activity_cache.get("data")
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
    try:
        num = int(body.get("actionNum") or 1)
    except (TypeError, ValueError):
        num = 1
    if cmd == "pgm-pulse":
        if num not in PGM_ALLOW:
            raise HTTPException(status_code=403, detail="Output not enabled here")
    elif cmd not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="Unknown or disallowed action")
    if cmd != "user-panic" and num < 1:
        num = 1
    actor = _remember_keypad(code, cmd, num)
    global _live_fast_until
    _live_fast_until = time.time() + 75.0   # covers the exit delay + confirmation
    raw = await _olarm_request(
        "POST",
        f"/api/v4/devices/{HANSEKOP_ID}/actions",
        json_body={"actionCmd": cmd, "actionNum": num},
    )
    try:
        fresh = await _olarm_request(
            "GET",
            f"/api/v4/devices/{HANSEKOP_ID}",
            params=_OLARM_DEV_PARAMS,
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
        params=_OLARM_DEV_PARAMS,
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


# Start the mains-meter Cloud sampler as soon as a process with Tuya credentials loads this module (flock keeps a
# single sampler across processes). Browsers then read the persisted reading instead of polling Tuya Cloud.
if SITE_TUYA and not TUYA_SHARING and tuya_configured() and os.getenv("ARIAL_ENERGY_SAMPLER", "1").strip().lower() not in {"0", "false", "no"}:
    try:
        _ensure_energy_sampler(TUYA_MAINS_METER_ID)
    except Exception:
        pass
