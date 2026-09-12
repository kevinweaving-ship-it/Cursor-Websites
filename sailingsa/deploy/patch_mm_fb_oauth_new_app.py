#!/usr/bin/env python3
"""Point MM LIVE OAuth at SailingSA MM Live (MM_FB_APP_ID), not sailor Login."""
from pathlib import Path
import shutil
import subprocess
from datetime import datetime

API = Path("/var/www/sailingsa/api/api.py")

OLD_CONNECT = '''    if not FACEBOOK_APP_ID:
        raise HTTPException(status_code=500, detail="FACEBOOK_APP_ID missing")
    cid = _mm_fb_graph_mod().config_id()
    if not cid:
        return RedirectResponse("/api/super-admin/mm-fb/connect?error=noconfig", status_code=303)
    redirect_uri = f"{_public_https_origin(request)}/auth/facebook/callback"
    state = _build_facebook_state("mm_fb", "/regatta/2026-09-13-zvyc-cape-classic")
    params = {
        "client_id": FACEBOOK_APP_ID,
'''

NEW_CONNECT = '''    mod = _mm_fb_graph_mod()
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
'''

OLD_TOKEN = '''    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        return _redirect_with_query(landing_page, {"error": "facebook_not_configured", "returnTo": return_to})

    conn = None
    try:
        redirect_uri = f"{_public_https_origin(request)}/auth/facebook/callback"
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.get(
                FACEBOOK_TOKEN_URL,
                params={
                    "client_id": FACEBOOK_APP_ID,
                    "client_secret": FACEBOOK_APP_SECRET,
'''

NEW_TOKEN = '''    if flow == "mm_fb":
        _mm = _mm_fb_graph_mod()
        _fb_id, _fb_sec = _mm.app_id(), _mm.app_secret()
    else:
        _fb_id, _fb_sec = FACEBOOK_APP_ID, FACEBOOK_APP_SECRET
    if not _fb_id or not _fb_sec:
        return _redirect_with_query(landing_page, {"error": "facebook_not_configured", "returnTo": return_to})

    conn = None
    try:
        redirect_uri = f"{_public_https_origin(request)}/auth/facebook/callback"
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.get(
                FACEBOOK_TOKEN_URL,
                params={
                    "client_id": _fb_id,
                    "client_secret": _fb_sec,
'''


def main() -> None:
    t = API.read_text(encoding="utf-8")
    if "detail=\"MM_FB_APP_ID missing\"" in t and "_fb_id, _fb_sec = _mm.app_id()" in t:
        print("already")
        return
    if OLD_CONNECT not in t:
        raise SystemExit("connect block missing")
    if OLD_TOKEN not in t:
        raise SystemExit("token block missing")
    t = t.replace(OLD_CONNECT, NEW_CONNECT, 1).replace(OLD_TOKEN, NEW_TOKEN, 1)
    bak = Path(f"/root/backups/api.py.mmfboauth_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["chattr", "-i", str(API)])
    shutil.copy2(API, bak)
    API.write_text(t, encoding="utf-8")
    subprocess.check_call(["chown", "www-data:www-data", str(API)])
    subprocess.check_call(["chattr", "+i", str(API)])
    print("patched bak", bak)


if __name__ == "__main__":
    main()
