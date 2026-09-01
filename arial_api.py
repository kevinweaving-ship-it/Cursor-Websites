"""Arial Dev — Olarm alarm dashboard + per-user profiles on /arial.

Token: environment OLARM_API_TOKEN only (never expose to the browser).
Users: data/arial_users.json (gitignored), separate from SailingSA accounts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

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

HANSEKOP_ID = "0bb544db-30b0-453d-bf39-d323538ebd5e"
KEYPAD_CODES = {
    "7302": {"name": "Marc", "from": "Pingoa"},
}

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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{OLARM_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.request(
                method, url, headers=headers, params=params, json=json_body
            )
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
    area_states = list(state.get("areas") or [])
    areas = []
    limit = int(profile.get("areasLimit") or max(len(area_labels), len(area_states), 0))
    for i in range(limit):
        label = (area_labels[i] if i < len(area_labels) else "") or f"Area {i + 1}"
        st = area_states[i] if i < len(area_states) else ""
        areas.append({"num": i + 1, "label": label, "state": st})
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
    return out


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
        "signedIn": bool(user),
        "me": _public_user(user) if user else None,
        "nextDomain": "arial.co.za",
    }


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
    return {"ok": True, "user": KEYPAD_CODES[code], "result": raw}


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
