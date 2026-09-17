"""HYC Hikvision live cam — Cam 5 on the HYC DS NVR.

ISAPI channel = camera_no * 100 + 1 (Cam 5 → 501 picture).
Credentials from env (never expose to the browser):
  HYC_NVR_HOST, HYC_NVR_USER, HYC_NVR_PASSWORD, optional HYC_NVR_PORT (80).
Super-admin show/hide is stored in a small JSON file.
"""
from __future__ import annotations

import json
import os
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
    urlopen,
)
from zoneinfo import ZoneInfo

CAM_NO = 5
ISAPI_CHANNEL = CAM_NO * 100 + 1
LABEL = "HYC club cam"
KIND = "live"
INTERVAL_SEC = 2
SAST = ZoneInfo("Africa/Johannesburg")
SRC = "/api/club-cam/hyc/snapshot"
STATUS_SRC = "/api/club-cam/hyc"
UA = "SailingSA-club-cam/1.0"

_vis_cache = {"at": 0.0, "visible": True}
_VIS_TTL = 1.0
_snap_cache = {"at": 0.0, "body": b"", "ok": False, "err": ""}
_SNAP_TTL = 1.5


def vis_path() -> Path:
    raw = (os.environ.get("HYC_CAM_VISIBLE_FILE") or "").strip()
    if raw:
        return Path(raw)
    for cand in (
        Path("/var/lib/sailingsa/club-cam-hyc.json"),
        Path("/tmp/sailingsa-club-cam-hyc.json"),
    ):
        parent = cand.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            if os.access(parent, os.W_OK):
                return cand
        except OSError:
            continue
    return Path("/tmp/sailingsa-club-cam-hyc.json")


def is_visible() -> bool:
    now = time.time()
    if now - float(_vis_cache.get("at") or 0) < _VIS_TTL:
        return bool(_vis_cache.get("visible", True))
    visible = True
    path = vis_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "visible" in data:
                visible = bool(data.get("visible"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        visible = True
    _vis_cache["at"] = now
    _vis_cache["visible"] = visible
    return visible


def set_visible(visible: bool) -> bool:
    flag = bool(visible)
    path = vis_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"visible": flag}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    _vis_cache["at"] = time.time()
    _vis_cache["visible"] = flag
    return flag


def nvr_host() -> str:
    return (os.environ.get("HYC_NVR_HOST") or "").strip().rstrip("/")


def nvr_user() -> str:
    return (os.environ.get("HYC_NVR_USER") or "").strip()


def nvr_password() -> str:
    return os.environ.get("HYC_NVR_PASSWORD") or ""


def nvr_port() -> int:
    raw = (os.environ.get("HYC_NVR_PORT") or "80").strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 80
    return n if n > 0 else 80


def picture_url() -> str:
    host = nvr_host()
    if not host:
        return ""
    if "://" in host:
        base = host
    else:
        port = nvr_port()
        base = f"http://{host}" + ("" if port in (80, 0) else f":{port}")
    return f"{base}/ISAPI/Streaming/channels/{ISAPI_CHANNEL}/picture"


def _format_as_at(dt: datetime) -> str:
    return dt.astimezone(SAST).strftime("%H:%M")


def _opener():
    user = nvr_user()
    password = nvr_password()
    url = picture_url()
    if not url or not user:
        return None
    mgr = HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, url, user, password)
    return build_opener(HTTPDigestAuthHandler(mgr))


def fetch_snapshot() -> tuple[bytes, str]:
    """Return (jpeg_bytes, err). Empty bytes on failure."""
    now = time.time()
    if _snap_cache.get("body") and (now - float(_snap_cache.get("at") or 0)) < _SNAP_TTL:
        return bytes(_snap_cache.get("body") or b""), str(_snap_cache.get("err") or "")
    url = picture_url()
    if not url:
        _snap_cache.update({"at": now, "body": b"", "ok": False, "err": "HYC_NVR_HOST not set"})
        return b"", "HYC_NVR_HOST not set"
    req = Request(url, headers={"User-Agent": UA})
    body = b""
    err = ""
    opener = _opener()
    try:
        if opener is not None:
            with opener.open(req, timeout=8) as resp:
                body = resp.read() or b""
        else:
            with urlopen(req, timeout=8, context=ssl._create_unverified_context()) as resp:
                body = resp.read() or b""
        if not body or len(body) < 32:
            err = "empty nvr picture"
            body = b""
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        err = str(exc)[:200]
        body = b""
    _snap_cache.update({"at": now, "body": body, "ok": bool(body), "err": err})
    return body, err


def status_payload(*, allowed: bool, can_toggle: bool) -> dict:
    visible = is_visible()
    live = False
    err = ""
    as_at = None
    last_iso = None
    if allowed:
        body, err = fetch_snapshot()
        live = bool(body)
        if live:
            dt = datetime.now(timezone.utc)
            last_iso = dt.isoformat().replace("+00:00", "Z")
            as_at = _format_as_at(dt)
    else:
        err = "hidden"
    return {
        "ok": bool(allowed and live),
        "kind": KIND,
        "live": bool(allowed and live),
        "visible": visible,
        "allowed": allowed,
        "can_toggle": can_toggle,
        "label": LABEL,
        "channel": CAM_NO,
        "isapi_channel": ISAPI_CHANNEL,
        "interval_sec": INTERVAL_SEC,
        "src": SRC,
        "last_modified": last_iso,
        "as_at": as_at,
        "err": err or None,
    }
