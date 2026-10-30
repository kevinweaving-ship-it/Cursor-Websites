#!/usr/bin/env python3
"""Marine Megastore Facebook LIVE via Graph + Page webhooks.

Token rule: never store a Graph Explorer session. One Facebook login
(Connect) is exchanged for a long-lived User token, then /me/accounts
yields a never-expiring Page token (debug_token expires_at=0). A systemd
timer remints the Page token from the User token while that User token is
still valid. Expired tokens cannot be refreshed — Facebook will not issue
a new one without login.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.environ.get("MM_FB_DEPLOY_DIR") or "/var/www/sailingsa/deploy")

PAGE = "marin.megastoresa"
PAGE_ID = "159493827253568"
PAGE_NAMES = ("marine megastore", "marin.megastoresa")
WEBHOOK_URL = "https://sailingsa.co.za/api/facebook/mm-live-webhook"
GRAPH = "https://graph.facebook.com/v21.0"
APP_ENV_PATH = Path(os.environ.get("MM_FB_APP_ENV") or "/etc/sailingsa/mm-fb-app.env")


def data_dir() -> Path:
    return Path(os.environ.get("MM_FB_DATA_DIR") or "/var/www/sailingsa/api/data")


def token_path() -> Path:
    return data_dir() / "mm_fb_page.token"


def user_token_path() -> Path:
    return data_dir() / "mm_fb_user.token"


def verify_path() -> Path:
    return data_dir() / "mm_fb_verify.token"


def config_path() -> Path:
    return data_dir() / "mm_fb_config_id.txt"


def status_path() -> Path:
    return data_dir() / "mm_fb_token_status.json"


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def load_app_env() -> None:
    """Load MM_FB_* from the MM Live app file. Never use sailor-login FACEBOOK_APP_*."""
    if not APP_ENV_PATH.is_file():
        return
    try:
        raw = APP_ENV_PATH.read_text(encoding="utf-8")
    except Exception:
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not key.startswith("MM_FB_"):
            continue
        val = val.strip().strip('"').strip("'")
        if val:
            os.environ[key] = val


def app_id() -> str:
    load_app_env()
    return _env("MM_FB_APP_ID")


def app_secret() -> str:
    load_app_env()
    return _env("MM_FB_APP_SECRET")


def app_token() -> str:
    aid, sec = app_id(), app_secret()
    if not aid or not sec:
        return ""
    return f"{aid}|{sec}"


def _protect(path: Path) -> None:
    try:
        os.chmod(path, 0o660)
    except Exception:
        pass
    try:
        os.chown(path, 0, 33)
    except Exception:
        try:
            os.chown(path, 33, 33)
        except Exception:
            pass


def _write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value or "").strip() + "\n", encoding="utf-8")
    _protect(path)


def verify_token() -> str:
    path = verify_path()
    if path.is_file():
        val = path.read_text(encoding="utf-8").strip()
        if val:
            return val
    val = secrets.token_urlsafe(24)
    _write_secret(path, val)
    return val


def page_token() -> str:
    path = token_path()
    if path.is_file():
        val = path.read_text(encoding="utf-8").strip()
        if val:
            return val
    for key in ("MM_FB_PAGE_TOKEN", "FACEBOOK_PAGE_TOKEN", "MARINE_MEGASTORE_PAGE_TOKEN"):
        val = _env(key)
        if val:
            return val
    return ""


def user_token() -> str:
    path = user_token_path()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return _env("MM_FB_USER_TOKEN")


def save_page_token(token: str) -> None:
    _write_secret(token_path(), token)


def save_user_token(token: str) -> None:
    _write_secret(user_token_path(), token)


def graph(path: str, token: str, params: dict | None = None, method: str = "GET") -> dict:
    q = dict(params or {})
    if token:
        q["access_token"] = token
    url = f"{GRAPH}/{path.lstrip('/')}?{urllib.parse.urlencode(q, doseq=True)}"
    req = urllib.request.Request(url, method=method.upper())
    if method.upper() == "POST":
        req = urllib.request.Request(url, data=b"", method="POST")
    req.add_header("User-Agent", "SailingSA-MM-Live/1.0")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Graph {e.code} {path}: {body}") from e
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {"raw": raw}


def inspect_token(token: str) -> dict:
    """debug_token summary. Never includes the token value."""
    if not token:
        return {"is_valid": False, "type": "", "expires_at": None, "never_expires": False, "error": "missing"}
    tok = app_token()
    if not tok:
        return {"is_valid": False, "type": "", "expires_at": None, "never_expires": False, "error": "no_app_secret"}
    try:
        data = graph("debug_token", tok, {"input_token": token})
    except Exception as e:
        return {"is_valid": False, "type": "", "expires_at": None, "never_expires": False, "error": str(e)[:160]}
    d = data.get("data") or {}
    err = d.get("error") or {}
    expires_at = d.get("expires_at")
    try:
        exp_i = int(expires_at) if expires_at is not None else None
    except (TypeError, ValueError):
        exp_i = None
    valid = bool(d.get("is_valid"))
    kind = str(d.get("type") or "")
    return {
        "is_valid": valid,
        "type": kind,
        "expires_at": exp_i,
        "never_expires": valid and kind.upper() == "PAGE" and int(exp_i or 0) == 0,
        "app_id": str(d.get("app_id") or ""),
        "error": str(err.get("message") or "")[:120],
        "error_code": err.get("code"),
    }


def exchange_user_token(short: str) -> str:
    """Short or long User token -> long-lived User token. Empty on failure."""
    aid, sec, short = app_id(), app_secret(), str(short or "").strip()
    if not aid or not sec or not short:
        return ""
    try:
        data = graph(
            "oauth/access_token",
            "",
            {
                "grant_type": "fb_exchange_token",
                "client_id": aid,
                "client_secret": sec,
                "fb_exchange_token": short,
            },
        )
    except Exception:
        return ""
    return str(data.get("access_token") or "").strip()


def long_lived_user_token(short: str) -> str:
    return exchange_user_token(short) or str(short or "").strip()


def pick_mm_page(accounts: list) -> dict | None:
    for row in accounts or []:
        name = str((row or {}).get("name") or "").strip().lower()
        ident = str((row or {}).get("id") or "")
        uname = str((row or {}).get("username") or "").strip().lower()
        if ident == PAGE_ID or uname == PAGE or any(p in name for p in PAGE_NAMES):
            return row
    for row in accounts or []:
        link = str((row or {}).get("link") or (row or {}).get("username") or "").lower()
        if "megastoresa" in link or "marinemega" in link:
            return row
    return None


def mint_page_from_user(user_tok: str) -> dict:
    """Exchange User token, save it, mint never-expiring Page token, subscribe."""
    raw = str(user_tok or "").strip()
    if not raw:
        return {"ok": False, "error": "no_user_token"}
    long_tok = exchange_user_token(raw)
    if not long_tok:
        return {"ok": False, "error": "exchange_failed"}
    save_user_token(long_tok)
    try:
        accts = graph("me/accounts", long_tok, {"fields": "id,name,access_token,username,link", "limit": "50"})
    except Exception as e:
        return {"ok": False, "error": f"accounts:{e}"}
    page = pick_mm_page(accts.get("data") or [])
    if not page or not page.get("access_token"):
        names = [str(r.get("name") or "") for r in (accts.get("data") or [])]
        return {"ok": False, "error": "mm_page_not_in_accounts", "pages": names[:12]}
    tok = str(page.get("access_token") or "").strip()
    pid = str(page.get("id") or "").strip() or PAGE_ID
    dbg = inspect_token(tok)
    if not dbg.get("is_valid") or str(dbg.get("type") or "").upper() != "PAGE":
        return {"ok": False, "error": "not_page_token", "debug": dbg}
    save_page_token(tok)
    sub = subscribe_page(pid, tok)
    app_sub = register_app_webhook()
    live = {"ok": False, "skipped": True}
    try:
        live = commit_graph_now()
    except Exception as e:
        live = {"ok": False, "error": str(e)[:160]}
    return {
        "ok": True,
        "page_id": pid,
        "page_name": page.get("name"),
        "never_expires": bool(dbg.get("never_expires")),
        "expires_at": dbg.get("expires_at"),
        "subscribed": sub,
        "app_webhook": app_sub,
        "live": live,
        "page": dbg,
    }


def finish_page_oauth(user_token_value: str) -> dict:
    """OAuth callback: mint never-expiring Page token. Do not save the short session."""
    return mint_page_from_user(str(user_token_value or "").strip())


def subscribe_page(page_id: str, token: str) -> dict:
    try:
        return graph(f"{page_id}/subscribed_apps", token, {"subscribed_fields": "live_videos"}, method="POST")
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


def register_app_webhook() -> dict:
    tok = app_token()
    if not tok:
        return {"ok": False, "error": "no_app_token"}
    try:
        return graph(
            f"{app_id()}/subscriptions",
            tok,
            {
                "object": "page",
                "callback_url": WEBHOOK_URL,
                "fields": "live_videos",
                "include_values": "true",
                "verify_token": verify_token(),
            },
            method="POST",
        )
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


def commit_graph_now() -> dict:
    from mm_fb_fetch_cape import commit_videos, graph_fetch, page_token as fetch_token

    token = page_token() or fetch_token()
    if not token:
        return {"ok": False, "error": "no_page_token", "live": []}
    fetched = graph_fetch(token)
    row = commit_videos(fetched)
    return {
        "ok": True,
        "live": [v.get("id") for v in (row.get("videos") or []) if v.get("is_live")],
        "n": len(row.get("videos") or []),
    }


def apply_webhook_body(body: dict) -> dict:
    """Facebook Page live_videos change. LIVE_NOW starts live; anything else ends it."""
    from mm_fb_fetch_cape import commit_videos, graph_item

    live_now = []
    ended = False
    for entry in body.get("entry") or []:
        for ch in (entry or {}).get("changes") or []:
            if str((ch or {}).get("field") or "") != "live_videos":
                continue
            val = (ch or {}).get("value") or {}
            vid = str(val.get("id") or "").strip()
            status = str(val.get("status") or "").upper().replace(" ", "_")
            if not vid:
                continue
            if status in ("LIVE_NOW", "LIVE"):
                live_now.append(
                    graph_item(
                        {
                            "id": vid,
                            "title": val.get("title") or "Marine Megastore LIVE",
                            "status": "LIVE",
                            "permalink_url": f"https://www.facebook.com/marin.megastoresa/videos/{vid}/",
                        },
                        True,
                    )
                )
            else:
                ended = True
    if live_now:
        commit_videos(live_now)
        return {"ok": True, "action": "live", "live": [v.get("id") for v in live_now]}
    if ended:
        row = commit_videos([])
        return {"ok": True, "action": "ended", "n": len(row.get("videos") or [])}
    return commit_graph_now()


def valid_hub_signature(raw: bytes, header: str) -> bool:
    sec = app_secret()
    if not sec or not header:
        return False
    want = header.split("=", 1)[-1].strip()
    got = hmac.new(sec.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(got, want)


def webhook_verify(mode: str, token: str, challenge: str) -> str | None:
    if mode == "subscribe" and token and token == verify_token():
        return challenge
    return None


def html_esc(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def save_config_id(cid: str) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(cid or "").strip() + "\n", encoding="utf-8")
    _protect(path)


def config_id() -> str:
    path = config_path()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    load_app_env()
    return _env("MM_FB_CONFIG_ID")


def read_status() -> dict:
    path = status_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_status(status: dict) -> None:
    path = status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = dict(status or {})
    path.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")
    _protect(path)


def _status_age_seconds(status: dict) -> float | None:
    raw = str((status or {}).get("checked_at") or "")
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


def keep_tokens(force: bool = False) -> dict:
    """Server routine: remint Page token from stored User token. No Graph Explorer.

    Facebook cannot mint from an already-expired token. After one Connect
    login, the Page token should have expires_at=0 and this job only confirms
    it. If the User token is still valid, we re-fetch /me/accounts.
    """
    load_app_env()
    prev = read_status()
    age = _status_age_seconds(prev)
    if not force and age is not None and age < 120:
        return prev
    if not force and prev.get("needs_login") and age is not None and age < 600:
        return prev

    user = user_token()
    page = page_token()
    user_dbg = inspect_token(user)
    page_dbg = inspect_token(page)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    status = {
        "ok": False,
        "needs_login": False,
        "action": "none",
        "connect": "/api/super-admin/mm-fb/connect",
        "checked_at": now,
        "user": {k: user_dbg.get(k) for k in ("is_valid", "type", "expires_at", "never_expires", "error", "error_code")},
        "page": {k: page_dbg.get(k) for k in ("is_valid", "type", "expires_at", "never_expires", "error", "error_code")},
    }

    if user_dbg.get("is_valid") and str(user_dbg.get("type") or "").upper() in ("USER", "SYSTEM_USER", ""):
        minted = mint_page_from_user(user)
        status["action"] = "minted" if minted.get("ok") else "mint_failed"
        status["mint"] = {
            "ok": minted.get("ok"),
            "error": minted.get("error"),
            "never_expires": minted.get("never_expires"),
            "page_id": minted.get("page_id"),
            "page_name": minted.get("page_name"),
        }
        if minted.get("ok"):
            status["ok"] = True
            status["needs_login"] = not bool(minted.get("never_expires"))
            if minted.get("page"):
                status["page"] = {
                    k: minted["page"].get(k)
                    for k in ("is_valid", "type", "expires_at", "never_expires", "error", "error_code")
                }
        elif page_dbg.get("is_valid") and str(page_dbg.get("type") or "").upper() == "PAGE":
            status["ok"] = True
            status["needs_login"] = not bool(page_dbg.get("never_expires"))
            status["action"] = "page_still_valid"
        else:
            status["needs_login"] = True
    elif page_dbg.get("never_expires"):
        status["ok"] = True
        status["action"] = "page_never_expires"
        if page:
            subscribe_page(PAGE_ID, page)
    elif page_dbg.get("is_valid") and str(page_dbg.get("type") or "").upper() == "PAGE":
        status["ok"] = True
        status["action"] = "page_valid_expiring"
        status["needs_login"] = True
    else:
        status["needs_login"] = True
        status["action"] = "dead"

    if status.get("needs_login"):
        print(
            "[mm_fb] TOKEN LOGIN REQUIRED once: https://sailingsa.co.za/api/super-admin/mm-fb/connect",
            flush=True,
        )
    write_status(status)
    return status


def accept_page_token(raw: str) -> dict:
    """Accept a pasted token only as a last resort. Prefer User token -> mint Page."""
    tok = str(raw or "").strip()
    if not tok or len(tok) < 20:
        return {"ok": False, "error": "token_too_short"}
    minted = mint_page_from_user(tok)
    if minted.get("ok"):
        minted["via"] = "user_accounts"
        return minted
    dbg = inspect_token(tok)
    if dbg.get("is_valid") and str(dbg.get("type") or "").upper() == "PAGE":
        save_page_token(tok)
        pid = PAGE_ID
        try:
            me = graph("me", tok, {"fields": "id,name"})
            pid = str(me.get("id") or pid)
        except Exception:
            me = {}
        sub = subscribe_page(pid, tok)
        live = commit_graph_now()
        return {
            "ok": True,
            "via": "page_token",
            "page_id": pid,
            "page_name": me.get("name"),
            "never_expires": bool(dbg.get("never_expires")),
            "subscribed": sub,
            "live": live,
        }
    return {"ok": False, "error": minted.get("error") or "token_rejected", "debug": dbg}


def setup_html(has_page_token: bool) -> str:
    st = read_status() or {}
    page = st.get("page") or {}
    if page.get("never_expires"):
        has = "YES — never-expiring Page token. Server keeps it. You do not paste tokens."
    elif has_page_token and page.get("is_valid"):
        has = "YES — Page token is valid but it will expire. Click Connect once so the server can mint a never-expiring one."
    elif st.get("needs_login"):
        has = "EXPIRED — click Connect Marine Megastore LIVE once. The server fetches and stores its own Page token after that."
    elif has_page_token:
        has = "FILE PRESENT — not proven valid. Click Connect once."
    else:
        has = "NO — click Connect once. After that the server keeps the token."
    cfg = html_esc(config_id() or "")
    action = html_esc(str(st.get("action") or ""))
    checked = html_esc(str(st.get("checked_at") or ""))
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>MM Facebook LIVE</title>"
        "<link rel=\"stylesheet\" href=\"/css/main.css\"></head><body>"
        "<div class=\"container\"><div class=\"card\">"
        "<h1 class=\"section-title\">MM Facebook LIVE</h1>"
        "<p>App: <b>SailingSA MM Live</b>. The server fetches its own tokens. "
        "Do not use Graph Explorer.</p>"
        f"<p><b>Page token on server:</b> {html_esc(has)}</p>"
        f"<p>Last keeper run: {checked or 'never'} ({action or 'none'})</p>"
        "<p>Click Connect while logged into Facebook as a Marine Megastore Page admin. "
        "That is the only human step. The server exchanges the login for a never-expiring "
        "Page token and a timer keeps it.</p>"
        "<p><a class=\"btn\" href=\"/api/super-admin/mm-fb/connect-business\">"
        "Connect Marine Megastore LIVE</a></p>"
        "<h2 class=\"section-title\">Login for Business config id</h2>"
        "<p>Already saved. Do not change it unless Meta issues a new one.</p>"
        "<form method=\"post\" action=\"/api/super-admin/mm-fb/config-id\">"
        f"<p><input name=\"config_id\" value=\"{cfg}\" placeholder=\"config_id\" "
        "style=\"width:100%;min-height:44px\"></p>"
        "<p><button type=\"submit\" class=\"btn\">Save config id</button></p>"
        "</form>"
        "</div></div></body></html>"
    )
