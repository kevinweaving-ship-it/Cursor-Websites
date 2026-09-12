#!/usr/bin/env python3
"""Surgical live api.py patch: MM Facebook Graph webhook + Page connect OAuth."""
from pathlib import Path
import shutil
import subprocess
from datetime import datetime

API = Path("/var/www/sailingsa/api/api.py")

OLD_BUILD = '''def _build_facebook_state(flow: str, return_to: Optional[str]) -> str:
    payload = {
        "flow": "signup" if str(flow or "").lower() == "signup" else "login",
        "returnTo": _safe_auth_return_to(return_to),
        "ts": int(time.time()),
    }
'''

NEW_BUILD = '''def _build_facebook_state(flow: str, return_to: Optional[str]) -> str:
    raw_flow = str(flow or "").lower()
    if raw_flow in ("mm_fb", "mm_fb_page"):
        flow_val = "mm_fb"
    elif raw_flow == "signup":
        flow_val = "signup"
    else:
        flow_val = "login"
    payload = {
        "flow": flow_val,
        "returnTo": _safe_auth_return_to(return_to),
        "ts": int(time.time()),
    }
'''

OLD_PARSE = '''        data["returnTo"] = _safe_auth_return_to(data.get("returnTo"))
        data["flow"] = "signup" if str(data.get("flow") or "").lower() == "signup" else "login"
        return data
'''

NEW_PARSE = '''        data["returnTo"] = _safe_auth_return_to(data.get("returnTo"))
        fl = str(data.get("flow") or "").lower()
        if fl in ("mm_fb", "mm_fb_page"):
            data["flow"] = "mm_fb"
        elif fl == "signup":
            data["flow"] = "signup"
        else:
            data["flow"] = "login"
        return data
'''

OLD_TOKEN = '''            access_token = token_data.get("access_token")
            if not access_token:
                return _redirect_with_query(landing_page, {"error": "facebook_token_failed", "returnTo": return_to})

            profile_response = await client.get(
'''

NEW_TOKEN = '''            access_token = token_data.get("access_token")
            if not access_token:
                return _redirect_with_query(landing_page, {"error": "facebook_token_failed", "returnTo": return_to})

            if flow == "mm_fb":
                import importlib.util as _ilu
                _sp = _ilu.spec_from_file_location(
                    "mm_fb_graph_live",
                    "/var/www/sailingsa/deploy/mm_fb_graph_live.py",
                )
                _mod = _ilu.module_from_spec(_sp)
                _sp.loader.exec_module(_mod)
                _res = _mod.finish_page_oauth(str(access_token))
                _dest = "/regatta/2026-09-13-zvyc-cape-classic"
                if _res.get("ok"):
                    return RedirectResponse(_dest + "?mm_fb=connected")
                return RedirectResponse(_dest + "?mm_fb=error")

            profile_response = await client.get(
'''

OLD_FEED = '''@app.get("/api/regatta/{regatta_id}/mm-live-fb-feed")
async def api_regatta_mm_live_fb_feed(regatta_id: str):
    rid = str(regatta_id or "").strip()
    if rid == _LIPTON_MM_REGATTA_ID:
        return _lipton_mm_reels_payload()
    if rid == _CAPE_CLASSIC_MM_REGATTA_ID:
        return _cape_classic_mm_reels_payload()
    raise HTTPException(status_code=404, detail="not found")
'''

NEW_FEED = '''@app.get("/api/regatta/{regatta_id}/mm-live-fb-feed")
async def api_regatta_mm_live_fb_feed(regatta_id: str):
    rid = str(regatta_id or "").strip()
    if rid == _LIPTON_MM_REGATTA_ID:
        return _lipton_mm_reels_payload()
    if rid == _CAPE_CLASSIC_MM_REGATTA_ID:
        return _cape_classic_mm_reels_payload()
    raise HTTPException(status_code=404, detail="not found")


def _mm_fb_graph_mod():
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location(
        "mm_fb_graph_live",
        "/var/www/sailingsa/deploy/mm_fb_graph_live.py",
    )
    _mod = _ilu.module_from_spec(_sp)
    _sp.loader.exec_module(_mod)
    return _mod


@app.get("/api/facebook/mm-live-webhook")
async def api_facebook_mm_live_webhook_verify(request: Request):
    """Meta hub challenge for Page live_videos."""
    q = request.query_params
    challenge = _mm_fb_graph_mod().webhook_verify(
        str(q.get("hub.mode") or ""),
        str(q.get("hub.verify_token") or ""),
        str(q.get("hub.challenge") or ""),
    )
    if challenge is None:
        raise HTTPException(status_code=403, detail="verify failed")
    return PlainTextResponse(challenge)


@app.post("/api/facebook/mm-live-webhook")
async def api_facebook_mm_live_webhook_event(request: Request):
    """Push: MM Page went LIVE_NOW or the broadcast ended."""
    raw = await request.body()
    sig = request.headers.get("x-hub-signature-256") or request.headers.get("X-Hub-Signature-256") or ""
    mod = _mm_fb_graph_mod()
    if not mod.valid_hub_signature(raw, sig):
        raise HTTPException(status_code=403, detail="bad signature")
    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="bad json")
    return mod.apply_webhook_body(body if isinstance(body, dict) else {})


@app.get("/api/super-admin/mm-fb/connect")
async def api_super_admin_mm_fb_connect(request: Request):
    """One-time: MM Facebook Page admin grants a Page token for LIVE push."""
    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    if not FACEBOOK_APP_ID:
        raise HTTPException(status_code=500, detail="FACEBOOK_APP_ID missing")
    redirect_uri = f"{_public_https_origin(request)}/auth/facebook/callback"
    state = _build_facebook_state("mm_fb", "/regatta/2026-09-13-zvyc-cape-classic")
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "pages_show_list,pages_read_engagement,pages_manage_metadata,pages_read_user_content",
        "response_type": "code",
        "auth_type": "rerequest",
    }
    return RedirectResponse(f"{FACEBOOK_AUTH_URL}?{urlencode(params)}")


@app.get("/api/super-admin/mm-fb/status")
async def api_super_admin_mm_fb_status(request: Request):
    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    mod = _mm_fb_graph_mod()
    return {
        "ok": True,
        "has_page_token": bool(mod.page_token()),
        "has_app": bool(mod.app_id()),
        "webhook": "https://sailingsa.co.za/api/facebook/mm-live-webhook",
        "connect": "/api/super-admin/mm-fb/connect",
    }
'''


def main() -> None:
    t = API.read_text(encoding="utf-8")
    orig_len = len(t)
    if "api_facebook_mm_live_webhook_event" in t:
        print("already patched")
        return
    for old, label in (
        (OLD_BUILD, "build_state"),
        (OLD_PARSE, "parse_state"),
        (OLD_TOKEN, "callback_token"),
        (OLD_FEED, "feed_routes"),
    ):
        if old not in t:
            raise SystemExit(f"missing {label}")
    t = t.replace(OLD_BUILD, NEW_BUILD, 1)
    t = t.replace(OLD_PARSE, NEW_PARSE, 1)
    t = t.replace(OLD_TOKEN, NEW_TOKEN, 1)
    t = t.replace(OLD_FEED, NEW_FEED, 1)
    bak = Path(f"/root/backups/api.py.mmfbgraph_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["chattr", "-i", str(API)])
    shutil.copy2(API, bak)
    API.write_text(t, encoding="utf-8")
    subprocess.check_call(["chown", "www-data:www-data", str(API)])
    subprocess.check_call(["chattr", "+i", str(API)])
    print("patched", orig_len, "->", len(t), "bak", bak)


if __name__ == "__main__":
    main()
