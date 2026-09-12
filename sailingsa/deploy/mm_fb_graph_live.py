#!/usr/bin/env python3
"""Marine Megastore Facebook LIVE via Graph + Page webhooks (not scrape).

Page token lives in mm_fb_page.token (from super-admin OAuth).
Webhook: GET/POST /api/facebook/mm-live-webhook
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/var/www/sailingsa/deploy")

PAGE = "marin.megastoresa"
PAGE_NAMES = ("marine megastore", "marin.megastoresa")
TOKEN_PATH = Path("/var/www/sailingsa/api/data/mm_fb_page.token")
VERIFY_PATH = Path("/var/www/sailingsa/api/data/mm_fb_verify.token")
CONFIG_PATH = Path("/var/www/sailingsa/api/data/mm_fb_config_id.txt")
WEBHOOK_URL = "https://sailingsa.co.za/api/facebook/mm-live-webhook"
GRAPH = "https://graph.facebook.com/v21.0"


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def app_id() -> str:
    return _env("MM_FB_APP_ID") or _env("FACEBOOK_APP_ID")


def app_secret() -> str:
    return _env("MM_FB_APP_SECRET") or _env("FACEBOOK_APP_SECRET")


def app_token() -> str:
    aid, sec = app_id(), app_secret()
    if not aid or not sec:
        return ""
    return f"{aid}|{sec}"


def verify_token() -> str:
    if VERIFY_PATH.is_file():
        val = VERIFY_PATH.read_text(encoding="utf-8").strip()
        if val:
            return val
    val = secrets.token_urlsafe(24)
    VERIFY_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERIFY_PATH.write_text(val + "\n", encoding="utf-8")
    try:
        os.chmod(VERIFY_PATH, 0o600)
    except Exception:
        pass
    return val


def page_token() -> str:
    if TOKEN_PATH.is_file():
        val = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if val:
            return val
    for key in ("MM_FB_PAGE_TOKEN", "FACEBOOK_PAGE_TOKEN", "MARINE_MEGASTORE_PAGE_TOKEN"):
        val = _env(key)
        if val:
            return val
    return ""


def save_page_token(token: str) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(TOKEN_PATH, 0o640)
        os.chown(TOKEN_PATH, 33, 33)
        os.chown(TOKEN_PATH, 33, 33)
    except Exception:
        pass


def graph(path: str, token: str, params: dict | None = None, method: str = "GET") -> dict:
    q = dict(params or {})
    q["access_token"] = token
    url = f"{GRAPH}/{path.lstrip('/')}?{urllib.parse.urlencode(q, doseq=True)}"
    req = urllib.request.Request(url, method=method.upper())
    if method.upper() == "POST":
        req = urllib.request.Request(url, data=b"", method="POST")
    req.add_header("User-Agent", "SailingSA-MM-Live/1.0")
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {"raw": raw}


def long_lived_user_token(short: str) -> str:
    aid, sec = app_id(), app_secret()
    if not aid or not sec or not short:
        return short
    try:
        data = graph(
            "oauth/access_token",
            short,
            {
                "grant_type": "fb_exchange_token",
                "client_id": aid,
                "client_secret": sec,
                "fb_exchange_token": short,
            },
        )
        return str(data.get("access_token") or short)
    except Exception:
        return short


def pick_mm_page(accounts: list) -> dict | None:
    for row in accounts or []:
        name = str((row or {}).get("name") or "").strip().lower()
        uname = str((row or {}).get("id") or "")
        if any(p in name for p in PAGE_NAMES) or uname == PAGE:
            return row
    for row in accounts or []:
        link = str((row or {}).get("link") or (row or {}).get("username") or "").lower()
        if "megastoresa" in link or "marinemega" in link:
            return row
    return None


def finish_page_oauth(user_token: str) -> dict:
    """Exchange admin user token for MM Page token and subscribe live_videos."""
    user_token = long_lived_user_token(str(user_token or "").strip())
    if not user_token:
        return {"ok": False, "error": "no_user_token"}
    try:
        accts = graph("me/accounts", user_token, {"fields": "id,name,access_token,username,link", "limit": "50"})
    except Exception as e:
        return {"ok": False, "error": f"accounts:{e}"}
    page = pick_mm_page(accts.get("data") or [])
    if not page or not page.get("access_token"):
        names = [str(r.get("name") or "") for r in (accts.get("data") or [])]
        return {"ok": False, "error": "mm_page_not_in_accounts", "pages": names[:12]}
    tok = str(page.get("access_token") or "").strip()
    pid = str(page.get("id") or "").strip()
    save_page_token(tok)
    sub = subscribe_page(pid, tok)
    app_sub = register_app_webhook()
    live = commit_graph_now()
    return {
        "ok": True,
        "page_id": pid,
        "page_name": page.get("name"),
        "subscribed": sub,
        "app_webhook": app_sub,
        "live": live,
    }


def subscribe_page(page_id: str, token: str) -> dict:
    try:
        return graph(f"{page_id}/subscribed_apps", token, {"subscribed_fields": "live_videos"}, method="POST")
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
        return {"ok": False, "error": str(e)}


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
        row = commit_videos(live_now)
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
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(str(cid or "").strip() + "\n", encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o640)
        os.chown(CONFIG_PATH, 33, 33)
    except Exception:
        pass


def config_id() -> str:
    if CONFIG_PATH.is_file():
        return CONFIG_PATH.read_text(encoding="utf-8").strip()
    return _env("MM_FB_CONFIG_ID")


def accept_page_token(raw: str) -> dict:
    """Save a Graph Explorer / Page token and subscribe live_videos."""
    tok = str(raw or "").strip()
    if not tok or len(tok) < 20:
        return {"ok": False, "error": "token_too_short"}
    try:
        accts = graph(
            "me/accounts",
            tok,
            {"fields": "id,name,access_token,username,link", "limit": "50"},
        )
        page = pick_mm_page(accts.get("data") or [])
        if page and page.get("access_token"):
            tok = str(page.get("access_token") or tok)
            pid = str(page.get("id") or "")
            save_page_token(tok)
            sub = subscribe_page(pid, tok) if pid else {}
            live = commit_graph_now()
            return {
                "ok": True,
                "via": "user_accounts",
                "page_id": pid,
                "page_name": page.get("name"),
                "subscribed": sub,
                "live": live,
            }
    except Exception:
        pass
    try:
        me = graph("me", tok, {"fields": "id,name"})
    except Exception as e:
        return {"ok": False, "error": f"token_rejected:{e}"}
    save_page_token(tok)
    pid = str(me.get("id") or "")
    sub = subscribe_page(pid, tok) if pid else {}
    live = commit_graph_now()
    return {
        "ok": True,
        "via": "page_token",
        "page_id": pid,
        "page_name": me.get("name"),
        "subscribed": sub,
        "live": live,
    }


def setup_html(has_page_token: bool) -> str:
    has = "YES — Graph LIVE is armed" if has_page_token else "NO — still scraping"
    cfg = html_esc(config_id() or "")
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>MM Facebook LIVE</title>"
        "<link rel=\"stylesheet\" href=\"/css/main.css\"></head><body>"
        "<div class=\"container\"><div class=\"card\">"
        "<h1 class=\"section-title\">MM Facebook LIVE</h1>"
        "<p>SailingSA Login is consumer Facebook Login. Page scopes are invalid there. "
        "That wrench dialog is Facebook blocking pages_show_list on that product. "
        "Use Graph API Explorer or Facebook Login for Business.</p>"
        f"<p><b>Page token on server:</b> {has}</p>"
        "<h2 class=\"section-title\">Paste a Page token</h2>"
        "<ol><li>Open <a href=\"https://developers.facebook.com/tools/explorer/\" "
        "target=\"_blank\" rel=\"noopener\">Graph API Explorer</a></li>"
        "<li>Meta App: <b>SailingSA Login</b></li>"
        "<li>Get token → User token or the <b>Marine Megastore</b> Page</li>"
        "<li>If the permissions picker shows them, add pages_show_list, "
        "pages_read_engagement, pages_manage_metadata</li>"
        "<li>Paste the token below.</li></ol>"
        "<form method=\"post\" action=\"/api/super-admin/mm-fb/page-token\">"
        "<p><textarea name=\"token\" rows=\"5\" required "
        "style=\"width:100%;min-height:96px\" placeholder=\"Page access token\"></textarea></p>"
        "<p><button type=\"submit\" class=\"btn\">Save MM Page token</button></p>"
        "</form>"
        "<h2 class=\"section-title\">Or Login for Business config id</h2>"
        "<p>developers.facebook.com → SailingSA Login → Facebook Login for Business → "
        "Configurations. User token. Assets: Pages. Permissions: pages_show_list, "
        "pages_read_engagement, pages_manage_metadata, pages_read_user_content.</p>"
        "<form method=\"post\" action=\"/api/super-admin/mm-fb/config-id\">"
        f"<p><input name=\"config_id\" value=\"{cfg}\" placeholder=\"config_id\" "
        "style=\"width:100%;min-height:44px\"></p>"
        "<p><button type=\"submit\" class=\"btn\">Save config id</button></p>"
        "</form>"
        "<p><a href=\"/api/super-admin/mm-fb/connect-business\">"
        "Continue with Facebook Login for Business</a> (needs config id)</p>"
        "</div></div></body></html>"
    )
