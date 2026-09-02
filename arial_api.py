"""Arial Dev — Olarm alarm dashboard + per-user profiles on /arial.

Token: environment OLARM_API_TOKEN only (never expose to the browser).
Users: data/arial_users.json (gitignored), separate from SailingSA accounts.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import uuid
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

HANSEKOP_ID = "0bb544db-30b0-453d-bf39-d323538ebd5e"
KEYPAD_CODES = {
    "7302": {"name": "Marc", "from": "Pingoa"},
    "7102": {"name": "Amoroc", "from": "Amoroc"},
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
            else:
                out["hint"] = _tuya_hint(out["tuyaCode"], out["tuyaMsg"], token_ok=True, device_ok=False)
                return out
            out["hint"] = ""
            return out
    except httpx.HTTPError as exc:
        out["tuyaMsg"] = str(exc)
        out["hint"] = f"Tuya OpenAPI unreachable: {exc}"
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
    while not _live_stop.wait(1.25):
        if not _olarm_token():
            continue
        try:
            with _olarm_http_lock:
                client = _olarm_sync_client()
                resp = client.get(
                    f"/api/v4/devices/{HANSEKOP_ID}",
                    params={"deviceApiAccessOnly": "1"},
                )
            if resp.status_code == 200:
                raw = resp.json()
                if isinstance(raw, dict):
                    _cached_panel(enrich_device(raw))
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
    return out


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
    return 30


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


@router.get("/api/arial/live")
async def arial_live():
    _ensure_live_session()

    async def events() -> AsyncIterator[str]:
        last = -1
        while True:
            seq = 0
            data = None
            with _lock:
                seq = int(_panel_cache.get("seq") or 0)
                cached = _panel_cache.get("data")
                data = cached if isinstance(cached, dict) else None
            if seq != last and data is not None:
                last = seq
                yield "data: " + json.dumps({"ok": True, "device": data, "live": True}) + "\n\n"
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
            _cached_panel(enrich_device(fresh))
        else:
            _cached_panel(clear=True)
    except HTTPException:
        _cached_panel(clear=True)
    _ensure_live_session()
    return {"ok": True, "user": KEYPAD_CODES[code], "result": raw, "device": _stale_panel()}


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
