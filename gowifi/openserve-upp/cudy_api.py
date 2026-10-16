#!/usr/bin/env python3
"""Read-only Cudy Cloud status for Murray's WR3000 on /dash/clients.html.

Credentials stay in /root/secrets/cudy.env. Browser never sees them.
Default GET is Murray WR3000 only. Never maps WR1300. No traffic gauges.
Cloud/API failure is not the same as the router being offline.
"""
from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENV_PATH = Path(os.environ.get("CUDY_ENV", "/root/secrets/cudy.env"))
LISTEN = os.environ.get("CUDY_API_LISTEN", "127.0.0.1:8803")
BASE = "https://i18n-wapi.cudycloud.com/web"
PASS_PREFIX = "cudwifi7[o4$"
LIST_TTL_S = 60.0
INFO_TTL_S = 300.0
SESSION_TTL_S = 25 * 60.0

PILOT_SN = "WR3000250613575"
PILOT_MODEL = "WR3000"
PILOT_MAC = "80:AF:CA:93:CB:E5"
PILOT_DEVID = "2040182040-10B5801818111B11"
FORBIDDEN_SN = "WR1300251209892"

RET_OK = 0
RET_TOKEN_MISMATCH = 100004
RET_REFRESH_EXPIRED = 100005
RET_WRONG_ENDPOINT = 100002
RET_DEVICE_TIMEOUT = 602002
RET_PASSWORD_ERROR = 600002
RET_ACCOUNT_OR_PASSWORD = 600601
RET_TEMP_LOCKED = 600602
RET_LOCK_CREDS = 502153
RET_LOCK_OFFLINE = 502156

AUTH_FAIL = {RET_PASSWORD_ERROR, RET_ACCOUNT_OR_PASSWORD}
AUTH_LOCK = {RET_TEMP_LOCKED, RET_LOCK_CREDS, RET_LOCK_OFFLINE}
TOKEN_STALE = {RET_TOKEN_MISMATCH, RET_REFRESH_EXPIRED}

_LOCK = threading.Lock()
_SESSION: dict = {"ok": False, "opener": None, "ts": 0.0}
_LIST_CACHE: dict = {}
_INFO_CACHE: dict[str, dict] = {}


def _load_env(path: Path | None = None) -> dict[str, str]:
    data: dict[str, str] = {}
    path = Path(os.environ.get("CUDY_ENV") or path or ENV_PATH)
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    data.setdefault("CUDY_EMAIL", os.environ.get("CUDY_EMAIL", ""))
    data.setdefault("CUDY_PASSWORD", os.environ.get("CUDY_PASSWORD", ""))
    if os.environ.get("CUDY_EMAIL"):
        data["CUDY_EMAIL"] = os.environ["CUDY_EMAIL"]
    if os.environ.get("CUDY_PASSWORD"):
        data["CUDY_PASSWORD"] = os.environ["CUDY_PASSWORD"]
    return data


def _as_at(when: datetime | None = None) -> str:
    now = when or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def password_hash(password: str) -> str:
    first = hashlib.md5((PASS_PREFIX + (password or "")).encode()).hexdigest()
    return hashlib.md5(first.encode()).hexdigest()


def fmt_mac(raw: str | None) -> str:
    hexed = "".join(c for c in (raw or "") if c.isalnum())
    if len(hexed) == 12:
        return ":".join(hexed[i : i + 2] for i in range(0, 12, 2)).upper()
    return (raw or "").strip()


def classify_ret(ret: int | None) -> str | None:
    if ret in (None, RET_OK):
        return None
    if ret in AUTH_LOCK:
        return "cloud_auth_locked"
    if ret in AUTH_FAIL:
        return "cloud_auth_failed"
    if ret in TOKEN_STALE:
        return "cloud_auth_failed"
    if ret == RET_DEVICE_TIMEOUT:
        return "device_offline"
    if ret == RET_WRONG_ENDPOINT:
        return "cloud_unreachable"
    return "cloud_unreachable"


def is_pilot_sn(sn: str | None) -> bool:
    return (sn or "").strip() == PILOT_SN


def is_forbidden_sn(sn: str | None) -> bool:
    return (sn or "").strip() == FORBIDDEN_SN


def pick_pilot(devices: list[dict]) -> dict | None:
    for row in devices:
        if not isinstance(row, dict):
            continue
        if is_forbidden_sn(row.get("sn")):
            continue
        if is_pilot_sn(row.get("sn")):
            return row
    return None


def conn_status(row: dict | None) -> str:
    if not row:
        return ""
    raw = row.get("connstatus")
    try:
        code = int(raw)
    except (TypeError, ValueError):
        return ""
    if code == 1:
        return "online"
    if code == 2:
        return "offline"
    return ""


def _pack(
    *,
    ok: bool,
    live: bool,
    error_class: str | None = None,
    error: str | None = None,
    device: dict | None = None,
    as_at: str | None = None,
    cached: bool = False,
) -> dict:
    out = {
        "ok": ok,
        "live": live,
        "as_at": as_at or _as_at(),
        "pilot": {"serial": PILOT_SN, "model": PILOT_MODEL},
        "cached": cached,
    }
    if error_class:
        out["error_class"] = error_class
    if error:
        out["error"] = error[:200]
    if device:
        out["device"] = device
    return out


def _public_device(row: dict, info: dict | None = None) -> dict:
    status = conn_status(row)
    out = {
        "vendor": "cudy",
        "model": PILOT_MODEL,
        "nickname": (row.get("nickname") or PILOT_MODEL).strip() or PILOT_MODEL,
        "serial": PILOT_SN,
        "mac": fmt_mac(row.get("mac") or PILOT_MAC),
        "devid": (row.get("devid") or PILOT_DEVID).strip() or PILOT_DEVID,
        "connstatus": row.get("connstatus"),
        "status": status,
    }
    block = info if isinstance(info, dict) else {}
    firmware = (block.get("firmware") or "").strip()
    if firmware:
        out["firmware"] = firmware
    uptime = block.get("uptime")
    if uptime not in (None, ""):
        try:
            out["uptime_s"] = int(uptime)
        except (TypeError, ValueError):
            pass
    mem = block.get("memory") if isinstance(block.get("memory"), dict) else {}
    usage = mem.get("usage")
    if usage not in (None, ""):
        try:
            out["memory_pct"] = int(usage)
        except (TypeError, ValueError):
            pass
    return out


def _new_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _post(opener: urllib.request.OpenerDirector, path: str, payload: dict, timeout: int = 15) -> dict:
    url = BASE.rstrip("/") + "/" + path.lstrip("/")
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "lan": "en",
            "Origin": "https://cloud.cudy.com",
            "Referer": "https://cloud.cudy.com/",
            "Accept": "application/json",
        },
    )
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        http_code = getattr(resp, "status", 200)
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cudy non-JSON HTTP {http_code}") from exc
    if not isinstance(body, dict):
        raise RuntimeError("Cudy unexpected body")
    body.setdefault("http", http_code)
    return body


def _login(env: dict[str, str]) -> tuple[urllib.request.OpenerDirector | None, dict]:
    email = (env.get("CUDY_EMAIL") or "").strip()
    password = env.get("CUDY_PASSWORD") or ""
    if not email or not password:
        return None, _pack(
            ok=False,
            live=False,
            error_class="cloud_auth_failed",
            error="no CUDY_EMAIL / CUDY_PASSWORD in /root/secrets/cudy.env",
        )
    opener = _new_opener()
    try:
        body = _post(
            opener,
            "v1/account/e/login",
            {"email": email, "password": password_hash(password)},
        )
    except urllib.error.HTTPError as exc:
        return None, _pack(
            ok=False,
            live=False,
            error_class="cloud_auth_failed" if exc.code in {401, 403} else "cloud_unreachable",
            error=f"Cudy login HTTP {exc.code}",
        )
    except Exception as exc:
        return None, _pack(
            ok=False,
            live=False,
            error_class="cloud_unreachable",
            error=str(exc)[:200],
        )
    ret = body.get("ret")
    klass = classify_ret(ret)
    if ret != RET_OK:
        return None, _pack(
            ok=False,
            live=False,
            error_class=klass or "cloud_auth_failed",
            error=(body.get("msg") or f"Cudy login ret {ret}")[:200],
        )
    return opener, {"ok": True}


def _session(env: dict[str, str], force: bool = False):
    now = time.time()
    with _LOCK:
        opener = _SESSION.get("opener")
        if (
            not force
            and _SESSION.get("ok")
            and opener is not None
            and now - float(_SESSION.get("ts") or 0) < SESSION_TTL_S
        ):
            return opener, None
    opener, err = _login(env)
    if opener is None:
        return None, err
    with _LOCK:
        _SESSION["ok"] = True
        _SESSION["opener"] = opener
        _SESSION["ts"] = time.time()
    return opener, None


def _drop_session() -> None:
    with _LOCK:
        _SESSION["ok"] = False
        _SESSION["opener"] = None
        _SESSION["ts"] = 0.0


def _call(env: dict[str, str], path: str, payload: dict) -> dict:
    opener, err = _session(env)
    if opener is None:
        return err or _pack(ok=False, live=False, error_class="cloud_auth_failed", error="no session")
    try:
        body = _post(opener, path, payload)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            _drop_session()
            opener, err = _session(env, force=True)
            if opener is None:
                return err or _pack(ok=False, live=False, error_class="cloud_auth_failed", error="re-login failed")
            try:
                body = _post(opener, path, payload)
            except Exception as retry_exc:
                return _pack(ok=False, live=True, error_class="cloud_unreachable", error=str(retry_exc)[:200])
        elif exc.code >= 500:
            return _pack(ok=False, live=True, error_class="cloud_unreachable", error=f"Cudy HTTP {exc.code}")
        else:
            return _pack(ok=False, live=True, error_class="cloud_unreachable", error=f"Cudy HTTP {exc.code}")
    except Exception as exc:
        return _pack(ok=False, live=True, error_class="cloud_unreachable", error=str(exc)[:200])
    ret = body.get("ret")
    if ret in TOKEN_STALE:
        _drop_session()
        opener, err = _session(env, force=True)
        if opener is None:
            return err or _pack(ok=False, live=False, error_class="cloud_auth_failed", error="token refresh failed")
        try:
            body = _post(opener, path, payload)
        except Exception as retry_exc:
            return _pack(ok=False, live=True, error_class="cloud_unreachable", error=str(retry_exc)[:200])
        ret = body.get("ret")
    if ret in AUTH_LOCK:
        return _pack(
            ok=False,
            live=True,
            error_class="cloud_auth_locked",
            error=(body.get("msg") or f"Cudy locked ret {ret}")[:200],
        )
    if ret in AUTH_FAIL:
        return _pack(
            ok=False,
            live=True,
            error_class="cloud_auth_failed",
            error=(body.get("msg") or f"Cudy auth ret {ret}")[:200],
        )
    if ret == RET_DEVICE_TIMEOUT:
        return {
            "ok": False,
            "live": True,
            "error_class": "device_offline",
            "error": (body.get("msg") or "device timeout")[:200],
            "body": body,
        }
    if ret != RET_OK:
        return _pack(
            ok=False,
            live=True,
            error_class=classify_ret(ret) or "cloud_unreachable",
            error=(body.get("msg") or f"Cudy ret {ret}")[:200],
        )
    return {"ok": True, "live": True, "body": body}


def _list_devices(env: dict[str, str]) -> dict:
    now = time.time()
    with _LOCK:
        hit = _LIST_CACHE.get("pack")
        ts = float(_LIST_CACHE.get("ts") or 0)
        if hit and now - ts < LIST_TTL_S:
            out = dict(hit)
            out["cached"] = True
            return out
    pack = _call(env, "v1/device/list", {"page": 0, "protype": "router"})
    if not pack.get("ok"):
        return pack
    data = pack.get("body") or {}
    payload = data.get("data") if isinstance(data.get("data"), dict) else data
    devices = payload.get("devices") if isinstance(payload, dict) else None
    if devices is None and isinstance(payload, dict):
        devices = payload.get("list")
    if not isinstance(devices, list):
        devices = []
    out = {"ok": True, "live": True, "devices": devices, "cached": False}
    with _LOCK:
        _LIST_CACHE["ts"] = time.time()
        _LIST_CACHE["pack"] = {"ok": True, "live": True, "devices": devices}
    return out


def _system_info(env: dict[str, str], devid: str) -> dict:
    if not devid:
        return {"ok": False, "error_class": "device_online_partial", "error": "no devid"}
    now = time.time()
    with _LOCK:
        hit = _INFO_CACHE.get(devid)
        if hit and now - float(hit.get("ts") or 0) < INFO_TTL_S and hit.get("info") is not None:
            return {"ok": True, "info": hit["info"], "cached": True}
    pack = _call(env, "v1/device/system/info", {"devid": devid})
    if not pack.get("ok"):
        return pack
    data = pack.get("body") or {}
    info = data.get("data") if isinstance(data.get("data"), dict) else {}
    with _LOCK:
        _INFO_CACHE[devid] = {"ts": time.time(), "info": info}
    return {"ok": True, "info": info, "cached": False}


def device_status(want_sn: str | None = None) -> dict:
    sn = (want_sn or PILOT_SN).strip() or PILOT_SN
    if is_forbidden_sn(sn) or not is_pilot_sn(sn):
        return _pack(
            ok=False,
            live=True,
            error_class="not_pilot",
            error="Murray WR3000 only — WR1300 is not mapped",
        )
    env = _load_env()
    if not (env.get("CUDY_EMAIL") or "").strip() or not (env.get("CUDY_PASSWORD") or ""):
        return _pack(
            ok=False,
            live=False,
            error_class="cloud_auth_failed",
            error="no CUDY_EMAIL / CUDY_PASSWORD in /root/secrets/cudy.env",
        )
    listed = _list_devices(env)
    if not listed.get("ok"):
        return _pack(
            ok=False,
            live=bool(listed.get("live")),
            error_class=listed.get("error_class") or "cloud_unreachable",
            error=listed.get("error") or "Cudy list failed",
            cached=bool(listed.get("cached")),
        )
    row = pick_pilot(listed.get("devices") or [])
    if not row:
        return _pack(
            ok=False,
            live=True,
            error_class="device_missing",
            error="WR3000 not in Cudy cloud list",
            cached=bool(listed.get("cached")),
        )
    status = conn_status(row)
    if status == "offline":
        return _pack(
            ok=True,
            live=True,
            error_class="device_offline",
            error="router offline",
            device=_public_device(row),
            cached=bool(listed.get("cached")),
        )
    info_pack = _system_info(env, (row.get("devid") or "").strip())
    if info_pack.get("ok"):
        return _pack(
            ok=True,
            live=True,
            device=_public_device(row, info_pack.get("info")),
            cached=bool(listed.get("cached") or info_pack.get("cached")),
        )
    klass = info_pack.get("error_class") or "device_online_partial"
    if klass == "device_offline":
        klass = "device_online_partial"
    return _pack(
        ok=True,
        live=True,
        error_class=klass,
        error=info_pack.get("error") or "system info unavailable",
        device=_public_device(row),
        cached=bool(listed.get("cached")),
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("cudy-api: " + fmt % args + "\n")

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        want = (qs.get("sn") or qs.get("serial") or [""])[0]
        if path in {"/", "/summary", "/dash/api/cudy", "/device"}:
            pack = device_status(want)
            if pack.get("error_class") == "not_pilot":
                code = 404
            elif pack.get("ok") or pack.get("error_class") == "device_offline":
                code = 200
            elif not pack.get("live"):
                code = 503
            else:
                code = 200
            self._send(code, pack)
            return
        self._send(404, {"ok": False, "error": "not found"})


def serve() -> None:
    host, port = LISTEN.split(":")
    httpd = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"cudy-api on {LISTEN}", flush=True)
    httpd.serve_forever()


def self_test() -> int:
    failed = 0
    hashed = password_hash("x")
    again = password_hash("x")
    if hashed != again or len(hashed) != 32 or hashed == "x":
        print("FAIL hash-stable")
        failed += 1
    else:
        print("OK hash-stable")
    if classify_ret(RET_PASSWORD_ERROR) != "cloud_auth_failed":
        print("FAIL auth-fail")
        failed += 1
    elif classify_ret(RET_TEMP_LOCKED) != "cloud_auth_locked":
        print("FAIL auth-lock")
        failed += 1
    elif classify_ret(RET_DEVICE_TIMEOUT) != "device_offline":
        print("FAIL device-timeout")
        failed += 1
    elif classify_ret(RET_TOKEN_MISMATCH) != "cloud_auth_failed":
        print("FAIL token-stale")
        failed += 1
    else:
        print("OK error-class")
    if fmt_mac("80AFCA93CBE5") != PILOT_MAC or fmt_mac(PILOT_MAC) != PILOT_MAC:
        print("FAIL mac")
        failed += 1
    else:
        print("OK mac")
    devices = [
        {"sn": FORBIDDEN_SN, "devmodel": "WR1300", "connstatus": 2, "nickname": "WR1300"},
        {
            "sn": PILOT_SN,
            "devmodel": "WR3000",
            "connstatus": 1,
            "nickname": "WR3000",
            "mac": "80AFCA93CBE5",
            "devid": PILOT_DEVID,
        },
    ]
    row = pick_pilot(devices)
    if not row or row.get("sn") != PILOT_SN or pick_pilot([devices[0]]) is not None:
        print("FAIL pick-pilot")
        failed += 1
    else:
        print("OK pick-pilot")
    if is_forbidden_sn(FORBIDDEN_SN) is False or is_pilot_sn(FORBIDDEN_SN):
        print("FAIL forbid-wr1300")
        failed += 1
    else:
        print("OK forbid-wr1300")
    offline = _public_device({"sn": PILOT_SN, "connstatus": 2, "mac": "80AFCA93CBE5", "devid": PILOT_DEVID})
    if offline.get("status") != "offline" or "firmware" in offline or "uptime_s" in offline:
        print("FAIL omit-empty-info", offline)
        failed += 1
    else:
        print("OK omit-empty-info")
    online = _public_device(
        {"sn": PILOT_SN, "connstatus": 1, "mac": "80AFCA93CBE5", "devid": PILOT_DEVID},
        {"firmware": "2.4.7-20250529-181923", "uptime": 3981002, "memory": {"usage": 66}},
    )
    if online.get("status") != "online" or online.get("firmware") != "2.4.7-20250529-181923":
        print("FAIL online-info", online)
        failed += 1
    elif online.get("uptime_s") != 3981002 or online.get("memory_pct") != 66:
        print("FAIL online-mem-uptime", online)
        failed += 1
    elif "wan" in online or "traffic" in online:
        print("FAIL no-traffic", online)
        failed += 1
    else:
        print("OK online-info")
    refused = device_status(FORBIDDEN_SN)
    if refused.get("error_class") != "not_pilot" or refused.get("ok"):
        print("FAIL refuse-wr1300", refused)
        failed += 1
    else:
        print("OK refuse-wr1300")
    old = os.environ.get("CUDY_EMAIL")
    old_pw = os.environ.get("CUDY_PASSWORD")
    old_env = os.environ.get("CUDY_ENV")
    os.environ["CUDY_EMAIL"] = ""
    os.environ["CUDY_PASSWORD"] = ""
    os.environ["CUDY_ENV"] = "/tmp/missing-cudy.env"
    empty = device_status(PILOT_SN)
    if old is None:
        os.environ.pop("CUDY_EMAIL", None)
    else:
        os.environ["CUDY_EMAIL"] = old
    if old_pw is None:
        os.environ.pop("CUDY_PASSWORD", None)
    else:
        os.environ["CUDY_PASSWORD"] = old_pw
    if old_env is None:
        os.environ.pop("CUDY_ENV", None)
    else:
        os.environ["CUDY_ENV"] = old_env
    if empty.get("live") or empty.get("error_class") != "cloud_auth_failed":
        print("FAIL empty-env", empty)
        failed += 1
    else:
        print("OK empty-env-not-live")
    stamped = _as_at(datetime(2026, 10, 16, 8, 50, 0, tzinfo=timezone.utc))
    if stamped != "2026-10-16 08:50:00":
        print("FAIL as-at", stamped)
        failed += 1
    else:
        print("OK as-at")
    blob = Path(__file__).read_text()
    if "CUDY_PASSWORD=" in blob and "os.environ" not in blob.split("CUDY_PASSWORD=", 1)[1][:40]:
        print("FAIL secrets-in-source")
        failed += 1
    elif "/root/secrets/cudy.env" not in blob:
        print("FAIL secrets-path")
        failed += 1
    else:
        print("OK no-secrets-in-source")
    return failed


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] == "self-test":
        return self_test()
    if args[0] == "status":
        print(json.dumps(device_status(args[1] if len(args) > 1 else PILOT_SN), indent=2))
        return 0
    if args[0] == "serve":
        serve()
        return 0
    print("usage: cudy_api.py self-test|status [sn]|serve")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
