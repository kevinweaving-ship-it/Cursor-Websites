#!/usr/bin/env python3
from pathlib import Path
import shutil
import subprocess
from datetime import datetime

API = Path("/var/www/sailingsa/api/api.py")

OLD = '''@app.get("/api/super-admin/mm-fb/connect")
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
'''

NEW = '''@app.get("/api/super-admin/mm-fb/connect")
async def api_super_admin_mm_fb_connect(request: Request):
    """Setup: Graph Explorer token or Login for Business. Page scopes are invalid on consumer Login."""
    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    mod = _mm_fb_graph_mod()
    return HTMLResponse(mod.setup_html(bool(mod.page_token())))


@app.post("/api/super-admin/mm-fb/page-token")
async def api_super_admin_mm_fb_page_token(request: Request):
    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    form = await request.form()
    raw = str(form.get("token") or "")
    if not raw.strip():
        try:
            body = await request.json()
            raw = str((body or {}).get("token") or "")
        except Exception:
            raw = ""
    res = _mm_fb_graph_mod().accept_page_token(raw)
    if res.get("ok"):
        return RedirectResponse("/api/super-admin/mm-fb/connect?saved=1", status_code=303)
    return RedirectResponse("/api/super-admin/mm-fb/connect?error=token", status_code=303)


@app.post("/api/super-admin/mm-fb/config-id")
async def api_super_admin_mm_fb_config_id(request: Request):
    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    form = await request.form()
    _mm_fb_graph_mod().save_config_id(str(form.get("config_id") or ""))
    return RedirectResponse("/api/super-admin/mm-fb/connect?config=1", status_code=303)


@app.get("/api/super-admin/mm-fb/connect-business")
async def api_super_admin_mm_fb_connect_business(request: Request):
    """Facebook Login for Business — config_id, never Page scopes on consumer Login."""
    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    mod = _mm_fb_graph_mod()
    aid = mod.app_id()
    if not aid:
        raise HTTPException(status_code=500, detail="MM_FB_APP_ID missing")
    cid = mod.config_id()
    if not cid:
        return RedirectResponse("/api/super-admin/mm-fb/connect?error=noconfig", status_code=303)
    redirect_uri = f"{_public_https_origin(request)}/auth/facebook/callback"
    state = _build_facebook_state("mm_fb", "/regatta/2026-09-13-zvyc-cape-classic")
    params = {
        "client_id": aid,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "override_default_response_type": "true",
        "config_id": cid,
    }
    return RedirectResponse(f"{FACEBOOK_AUTH_URL}?{urlencode(params)}")
'''


def main() -> None:
    t = API.read_text(encoding="utf-8")
    if "api_super_admin_mm_fb_page_token" in t:
        print("already")
        return
    if OLD not in t:
        raise SystemExit("connect block missing")
    t = t.replace(OLD, NEW, 1)
    bak = Path(f"/root/backups/api.py.mmfbsetup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    subprocess.check_call(["chattr", "-i", str(API)])
    shutil.copy2(API, bak)
    API.write_text(t, encoding="utf-8")
    subprocess.check_call(["chown", "www-data:www-data", str(API)])
    subprocess.check_call(["chattr", "+i", str(API)])
    print("patched bak", bak)


if __name__ == "__main__":
    main()
