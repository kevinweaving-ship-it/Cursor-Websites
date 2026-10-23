#!/usr/bin/env python3
"""Surgical patches on a LIVE api.py copy. Never use the 1.4MB repo api.py."""
from pathlib import Path
import sys

IMPORT_MARK = "from typing import Union, Optional, List, Dict, Set, Tuple, FrozenSet, Any, Any"
IMPORT_ADD = """from typing import Union, Optional, List, Dict, Set, Tuple, FrozenSet, Any, Any
try:
    from modules import auth_identity as _auth_id
except Exception:
    try:
        from api.modules import auth_identity as _auth_id
    except Exception:
        _auth_id = None
"""

HELPER = '''
def _auth_store():
    return _auth_id.STORE if _auth_id else None

def _issue_oauth_proof(provider, provider_id, email="", email_verified=False, first_name="", last_name="", full_name="", picture=""):
    if not _auth_id:
        return ""
    try:
        _auth_id.ensure_tables  # attribute check
    except Exception:
        pass
    return _auth_id.issue_identity_proof(
        _auth_id.STORE,
        provider,
        {
            "provider_id": provider_id,
            "email": email,
            "email_verified": email_verified,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "picture": picture,
        },
    )

def _proof_from_request(request, body=None):
    body = body or {}
    token = (
        (body.get("identity_proof") or body.get("proof") or "")
        or request.cookies.get("ssa_id_proof")
        or request.query_params.get("proof")
        or ""
    )
    token = str(token).strip()
    if not token or not _auth_id:
        raise ValueError("Missing server identity proof")
    return _auth_id.consume_identity_proof(_auth_id.STORE, token)

'''

FB_OLD = '''        return _redirect_with_query(
            "/signup.html",
            {
                "facebook_signup": "1",
                "facebook_id": facebook_id,
                "facebook_email": facebook_email,
                "facebook_name": facebook_name,
                "facebook_first_name": first_name,
                "facebook_last_name": last_name,
                "facebook_picture": picture_url,
                "returnTo": return_to,
            },
        )'''

FB_NEW = '''        proof = _issue_oauth_proof(
            "facebook", facebook_id, facebook_email, bool(facebook_email),
            first_name, last_name, facebook_name, picture_url or "",
        )
        resp = _redirect_with_query(
            "/signup.html",
            {
                "facebook_signup": "1",
                "proof": proof,
                "facebook_name": facebook_name,
                "facebook_first_name": first_name,
                "facebook_last_name": last_name,
                "returnTo": return_to,
            },
        )
        if proof:
            resp.set_cookie("ssa_id_proof", proof, httponly=True, samesite="lax", max_age=900, path="/")
        return resp'''

GG_OLD = '''        return _redirect_with_query(
            "/signup.html",
            {
                "google_signup": "1",
                "google_id": google_id,
                "google_email": google_email,
                "google_email_verified": "1" if email_verified else "0",
                "google_name": google_name,
                "google_given_name": first_name,
                "google_family_name": last_name,
                "google_picture": picture_url,
                "returnTo": return_to,
            },
        )'''

GG_NEW = '''        proof = _issue_oauth_proof(
            "google", google_id, google_email, bool(email_verified),
            first_name, last_name, google_name, picture_url or "",
        )
        resp = _redirect_with_query(
            "/signup.html",
            {
                "google_signup": "1",
                "proof": proof,
                "google_name": google_name,
                "google_given_name": first_name,
                "google_family_name": last_name,
                "returnTo": return_to,
            },
        )
        if proof:
            resp.set_cookie("ssa_id_proof", proof, httponly=True, samesite="lax", max_age=900, path="/")
        return resp'''

FB_CONFIRM_START = '''        facebook_id = body.get('facebook_id')
        sas_id = body.get('sas_id')
        relationship = body.get('relationship')
        email = body.get('email')
        password = body.get('password')
        whatsapp = body.get('whatsapp')
        
        if not facebook_id:
            return {"error": "Missing facebook_id"}'''

FB_CONFIRM_START_NEW = '''        try:
            _proof = _proof_from_request(request, body)
            facebook_id = _proof.provider_id
            if _proof.provider != "facebook":
                return {"error": "Identity proof is not a Facebook session"}
        except Exception as _pe:
            return {"error": "Facebook sign-up must be completed from the Facebook login, not a posted id"}
        sas_id = body.get('sas_id')
        relationship = body.get('relationship')
        email = body.get('email')
        password = body.get('password')
        whatsapp = body.get('whatsapp')
        
        if not facebook_id:
            return {"error": "Missing facebook identity"}'''

GG_CONFIRM_START = '''    google_id = str(payload.get("google_id") or "").strip()
    sas_id = str(payload.get("sas_id") or "").strip()
    google_email = str(payload.get("google_email") or "").strip()
    google_email_verified = str(payload.get("google_email_verified") or "").strip().lower() in {"1", "true", "yes", "on"}'''

GG_CONFIRM_START_NEW = '''    try:
        _proof = _proof_from_request(request, payload)
        if _proof.provider != "google":
            return {"error": "Identity proof is not a Google session"}
        google_id = _proof.provider_id
        google_email = _proof.email
        google_email_verified = bool(_proof.email_verified)
    except Exception:
        return {"error": "Google sign-up must be completed from the Google login, not a posted id"}
    sas_id = str(payload.get("sas_id") or "").strip()'''

SESSION_BUG = '''        cols = ["session_id", "account_id", "sas_id", "login_method", "expires_at", "ip_address", "user_agent"]
        vals = [session_token, account_id, sas_id, expires_at, client_ip or None, user_agent or None]'''

SESSION_FIX = '''        cols = ["session_id", "account_id", "sas_id", "login_method", "expires_at", "ip_address", "user_agent"]
        vals = [session_token, account_id, sas_id, "facebook", expires_at, client_ip or None, user_agent or None]'''

ROUTES = '''
@app.get("/auth/verify-link")
async def auth_verify_link_preview(request: Request, token: str = ""):
    token = (token or request.query_params.get("token") or "").strip()
    if not _auth_id or not token:
        return HTMLResponse("<html><body class=\\"card container\\"><p>Missing verification link.</p></body></html>", status_code=400)
    try:
        _auth_id.preview_link_challenge(_auth_id.STORE, token)
    except Exception as e:
        return HTMLResponse(f"<html><body class=\\"card container\\"><p>{e}</p></body></html>", status_code=400)
    return FileResponse("/var/www/sailingsa/verify-link.html") if Path("/var/www/sailingsa/verify-link.html").exists() else HTMLResponse(
        """<html><body class="container card"><h1 class="section-title">Confirm verification</h1>
        <p>Email scanners cannot complete this. Click confirm if you requested it.</p>
        <form method="post" action="/auth/verify-link/confirm">
        <input type="hidden" name="token" value=\"""" + token + """\">
        <button type="submit" class="btn-login btn-primary">Confirm</button></form></body></html>"""
    )

@app.post("/auth/verify-link/confirm")
async def auth_verify_link_confirm(request: Request):
    form = await request.form() if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else {}
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    token = str((form.get("token") if form else None) or body.get("token") or request.query_params.get("token") or "").strip()
    if not _auth_id:
        return JSONResponse({"error": "auth module missing"}, status_code=500)
    try:
        ch = _auth_id.confirm_link_challenge(_auth_id.STORE, token)
        return {"ok": True, "purpose": ch.purpose, "destination": ch.destination}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.post("/auth/challenge/send")
async def auth_challenge_send(request: Request):
    body = await request.json()
    if not _auth_id:
        return JSONResponse({"error": "auth module missing"}, status_code=500)
    channel = str(body.get("channel") or "email").strip()
    dest = str(body.get("destination") or body.get("email") or body.get("whatsapp") or "").strip()
    purpose = str(body.get("purpose") or "login").strip()
    try:
        cid, pin = _auth_id.issue_pin_challenge(
            _auth_id.STORE, purpose=purpose, channel=channel, destination=dest,
            worker_id=str(os.getenv("HOSTNAME") or ""),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    text = f"SailingSA code {pin}. Expires in 10 minutes. Do not share it."
    sent = False
    err = ""
    if channel == "whatsapp":
        local = _auth_id.normalize_phone(dest)
        sent, err = _send_via_whatsapp_engine(_auth_id.phone_intl(local), text)
    else:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(text)
            msg["Subject"] = "Your SailingSA verification code"
            msg["From"] = os.getenv("MAIL_FROM", "noreply@sailingsa.co.za")
            msg["To"] = dest
            s = smtplib.SMTP(os.getenv("SMTP_HOST", "localhost"), int(os.getenv("SMTP_PORT", "25")))
            s.send_message(msg)
            s.quit()
            sent = True
        except Exception as e:
            err = str(e)[:180]
    if not sent:
        return JSONResponse({"error": err or "Could not send"}, status_code=502)
    return {"ok": True, "challenge_id": cid}

@app.post("/auth/challenge/verify")
async def auth_challenge_verify(request: Request):
    body = await request.json()
    if not _auth_id:
        return JSONResponse({"error": "auth module missing"}, status_code=500)
    try:
        ch = _auth_id.verify_pin(
            _auth_id.STORE,
            str(body.get("challenge_id") or ""),
            str(body.get("pin") or body.get("code") or ""),
            worker_id=str(os.getenv("HOSTNAME") or ""),
        )
        return {"ok": True, "purpose": ch.purpose, "destination": ch.destination}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/auth/remember/check")
async def auth_remember_check(request: Request):
    raw = (request.cookies.get("ssa_remember") or "").strip()
    if not raw or not _auth_id:
        return {"recognised": False}
    try:
        rem = _auth_id.recognise_remembered_device(_auth_id.STORE, raw)
        return {
            "recognised": True,
            "sas_id": rem.sas_id,
            "login_method": rem.login_method,
            "display_name": rem.display_name,
        }
    except Exception:
        return {"recognised": False}

'''


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/live-sailingsa/api.py")
    text = path.read_text(encoding="utf-8")
    replacements = [
        (IMPORT_MARK, IMPORT_ADD, 1),
        (FB_OLD, FB_NEW, 1),
        (GG_OLD, GG_NEW, 1),
        (FB_CONFIRM_START, FB_CONFIRM_START_NEW, 1),
        (GG_CONFIRM_START, GG_CONFIRM_START_NEW, 1),
        (SESSION_BUG, SESSION_FIX, 1),
    ]
    missing = []
    for old, new, n in replacements:
        if old not in text:
            missing.append(old[:80])
        else:
            text = text.replace(old, new, n)
    if "def _issue_oauth_proof" not in text:
        text = text.replace("def _create_login_session_record", HELPER + "def _create_login_session_record", 1)
    if '@app.get("/auth/verify-link")' not in text:
        text = text.replace('@app.post("/auth/login")', ROUTES + '\n@app.post("/auth/login")', 1)
    if missing:
        print("MISSING blocks:")
        for m in missing:
            print(" -", m)
        return 1
    path.write_text(text, encoding="utf-8")
    print("patched", path, "bytes", path.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
