#!/usr/bin/env python3
"""Surgical live patch: email signup is link-then-create. WhatsApp stays PIN-then-create."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
AUTH = Path("/var/www/sailingsa/api/modules/auth_identity.py")
SIGNUP = Path("/var/www/sailingsa/signup.html")

COMPLETE_FN = '''
def _complete_register_from_email_link(request, ch):
    """Create the member only after the email Confirm link is used."""
    raw = str(ch.account_hint or "")
    if not raw.startswith("register-link:"):
        raise ValueError("Not an email signup link")
    data = json.loads(raw[len("register-link:"):])
    email = str(data.get("email") or "").strip().lower()
    password_hash = str(data.get("password_hash") or "")
    requested_sas = str(data.get("sas_id") or "").strip()
    relationship = str(data.get("relationship") or "pending")
    full_name = str(data.get("full_name") or "").strip()[:200]
    if not email or email != str(ch.destination or "").strip().lower():
        raise ValueError("Signup email does not match this link")
    if not password_hash:
        raise ValueError("Signup link is missing a password. Submit the form again.")
    ownership, sailor = _resolve_signup_identity(relationship, requested_sas)
    writes_sas = _auth_id.account_writes_sas(ownership)
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("ssa:register:email:" + email,))
        cur.execute("""SELECT account_id FROM public.user_accounts
            WHERE lower(email) = %s OR (login_method = 'email' AND lower(provider_id) = %s)
            LIMIT 1""", (email, email))
        if cur.fetchone():
            raise ValueError("That email is already registered — sign in instead")
        if writes_sas:
            _require_sailor_contact(cur, sailor, "email", email)
            if _sas_profile_claimed(cur, sailor):
                raise PermissionError(_CLAIMED_PROFILE_ERROR)
            account_sas = sailor
        else:
            account_sas = _ensure_public_member_sas(
                cur, email=email, full_name=full_name,
                relationship="public" if ownership == "general_public" else "pending_match")
        cur.execute("""INSERT INTO public.user_accounts
            (sas_id, login_method, provider_id, email, email_verified, password_hash)
            VALUES (%s, 'email', %s, %s, TRUE, %s) RETURNING account_id""",
            (account_sas, email, email, password_hash))
        account_id = cur.fetchone()["account_id"]
        if writes_sas:
            cur.execute("""INSERT INTO public.user_accounts
                (sas_id, login_method, provider_id, password_hash)
                VALUES (%s, 'sas_id', %s, %s)""", (sailor, sailor, password_hash))
        cur.execute("""INSERT INTO public.auth_verified_contacts
            (account_key, email, phone, provenance, ownership, sas_id, verified_at)
            VALUES (%s, %s, '', 'signup_email', %s, %s, NOW())
            ON CONFLICT (account_key) DO UPDATE SET
              email = EXCLUDED.email, provenance = EXCLUDED.provenance,
              ownership = EXCLUDED.ownership, sas_id = EXCLUDED.sas_id, verified_at = EXCLUDED.verified_at""",
            (str(account_id), email, ownership, sailor if writes_sas else ""))
        token = _create_login_session_record(cur, request, account_id, account_sas, "email")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        return_db_connection(conn)
    return {
        "success": True, "session_token": token, "session": token,
        "account_id": account_id, "login_method": "email", "_remember_sas_id": account_sas,
        "sas_id": account_sas if writes_sas else None, "ownership": ownership,
        "sailor_choice_required": not writes_sas, "claimed": bool(writes_sas),
    }, token


'''

OLD_ISSUE = """        if not challenge_id:
            cid, pin = _auth_id.issue_pin_challenge(
                _auth_store(), purpose="signup", channel=channel,
                destination=destination, account_hint=binding,
                worker_id=str(os.getenv("HOSTNAME") or ""))
            text = f"Your SailingSA signup code is {pin}. Expires in 10 minutes. Do not share it."
            if channel == "whatsapp":
                sent, error = _send_via_whatsapp_engine(_auth_id.phone_intl(destination), text)
                if not sent:
                    return JSONResponse({"error": error or "Could not send WhatsApp"}, status_code=502)
            else:
                _send_auth_email(destination, "Your SailingSA signup code", text)
            return {"verification_required": True, "challenge_id": cid, "channel": channel}
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        ch = _auth_id.recovery_consume_pin(cur, challenge_id,
            str(body.get("pin") or ""), expected_purpose="signup")
"""

NEW_ISSUE = """        if not challenge_id:
            if channel == "email":
                pending = {
                    "email": email,
                    "phone": phone,
                    "sas_id": requested_sas,
                    "relationship": relationship,
                    "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                    "full_name": str(body.get("full_name") or "").strip()[:200],
                }
                hint = "register-link:" + json.dumps(pending, separators=(",", ":"))
                cid, raw = _auth_id.issue_link_challenge(
                    _auth_store(), purpose="signup", channel="email",
                    destination=destination, account_hint=hint)
                base = "https://sailingsa.co.za"
                try:
                    base = _canonical_base_url() if "_canonical_base_url" in globals() else base
                except Exception:
                    pass
                link = f"{base}/auth/verify-link?token={raw}"
                text = (
                    "Confirm your SailingSA email to create your account.\\n\\n"
                    f"{link}\\n\\n"
                    "No account is created until you click Confirm. "
                    "This link expires in 30 minutes."
                )
                try:
                    _send_auth_email(destination, "Confirm your SailingSA email", text)
                except Exception:
                    return JSONResponse(
                        {"error": "Could not send the confirmation email. Use WhatsApp, Google, or Facebook."},
                        status_code=502,
                    )
                return {"verification_required": True, "challenge_id": cid, "channel": "email", "via": "link"}
            cid, pin = _auth_id.issue_pin_challenge(
                _auth_store(), purpose="signup", channel=channel,
                destination=destination, account_hint=binding,
                worker_id=str(os.getenv("HOSTNAME") or ""))
            text = f"Your SailingSA signup code is {pin}. Expires in 10 minutes. Do not share it."
            sent, error = _send_via_whatsapp_engine(_auth_id.phone_intl(destination), text)
            if not sent:
                return JSONResponse({"error": error or "Could not send WhatsApp"}, status_code=502)
            return {"verification_required": True, "challenge_id": cid, "channel": channel, "via": "pin"}
        if channel == "email":
            return JSONResponse({
                "error": "Check your email and click Confirm. An email account is not created until that link is used."
            }, status_code=400)
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        ch = _auth_id.recovery_consume_pin(cur, challenge_id,
            str(body.get("pin") or ""), expected_purpose="signup")
"""

OLD_FULFILL = """    if str(ch.account_hint or "").startswith("register:"):
        raise ValueError("Finish verification on the signup form")
"""

NEW_FULFILL = """    if str(ch.account_hint or "").startswith("register-link:"):
        return _complete_register_from_email_link(request, ch)
    if str(ch.account_hint or "").startswith("register:"):
        raise ValueError("Finish verification on the signup form")
"""

OLD_CONFIRM = """        ch = _auth_id.confirm_link_challenge(store, token)
        return_to = (
"""

NEW_CONFIRM = """        ch = _auth_id.confirm_link_challenge(store, token)
        if str(ch.account_hint or "").startswith("register-link:"):
            payload, session_token = _complete_register_from_email_link(request, ch)
            resp = _auth_session_response(payload, session_token)
            if form:
                redir = RedirectResponse(url="https://sailingsa.co.za/?signup=verified", status_code=303)
                for key, val in resp.headers.items():
                    if str(key).lower() == "set-cookie":
                        redir.headers.append("set-cookie", val)
                return redir
            return resp
        return_to = (
"""

OLD_LINK_HINT = """        if str(existing.account_hint or "") != str(account_hint or ""):
            raise ValueError("Finish or cancel the existing verification first")
"""

NEW_LINK_HINT = """        if str(existing.account_hint or "") != str(account_hint or ""):
            if purpose == "signup" and str(existing.account_hint).startswith("register-link:") and str(account_hint).startswith("register-link:"):
                existing.account_hint = account_hint
            else:
                raise ValueError("Finish or cancel the existing verification first")
"""

OLD_JS = """                if (data.verification_required) {
                    window.__registrationCode = {id: data.challenge_id, key: JSON.stringify(registrationBody)};
                    showSection('registrationDataForm');
                    document.getElementById('regVerificationGroup').hidden = false;
                    document.getElementById('regVerificationHint').textContent = 'Code sent by ' + (data.channel === 'whatsapp' ? 'WhatsApp' : 'email') + '. Enter it to finish signing up.';
                    document.getElementById('regSubmitBtn').textContent = 'Verify and create account';
                    document.getElementById('regVerificationPin').focus();
                    return;
                }
"""

NEW_JS = """                if (data.verification_required) {
                    showSection('registrationDataForm');
                    document.getElementById('regVerificationGroup').hidden = false;
                    if (data.via === 'link' || data.channel === 'email') {
                        window.__registrationCode = null;
                        document.getElementById('regVerificationHint').textContent = 'Check your email. Click Confirm in the message we sent. No account is created until you do that.';
                        document.getElementById('regVerificationPin').hidden = true;
                        document.getElementById('regSubmitBtn').textContent = 'Email sent — click the link';
                        document.getElementById('regSubmitBtn').disabled = true;
                        return;
                    }
                    window.__registrationCode = {id: data.challenge_id, key: JSON.stringify(registrationBody)};
                    document.getElementById('regVerificationPin').hidden = false;
                    document.getElementById('regVerificationHint').textContent = 'Code sent by WhatsApp. Enter it to finish signing up.';
                    document.getElementById('regSubmitBtn').textContent = 'Verify and create account';
                    document.getElementById('regVerificationPin').focus();
                    return;
                }
"""


def must_replace(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"MISSING block in {path}: {label}")
    if text.count(old) != 1:
        raise SystemExit(f"AMBIGUOUS block in {path}: {label} count={text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("patched", path, label)


def main() -> None:
    api = API.read_text(encoding="utf-8")
    if "_complete_register_from_email_link" not in api:
        marker = "def _fulfill_verified_challenge(request, ch, *, relationship=\"\", sas_id=\"\", return_to=\"\", slug=\"\"):"
        if marker not in api:
            raise SystemExit("missing _fulfill_verified_challenge")
        API.write_text(api.replace(marker, COMPLETE_FN + marker, 1), encoding="utf-8")
        print("inserted _complete_register_from_email_link")
    must_replace(API, OLD_ISSUE, NEW_ISSUE, "register-account email-link")
    must_replace(API, OLD_FULFILL, NEW_FULFILL, "fulfill register-link")
    must_replace(API, OLD_CONFIRM, NEW_CONFIRM, "verify-link confirm")
    must_replace(AUTH, OLD_LINK_HINT, NEW_LINK_HINT, "link hint resend")
    must_replace(SIGNUP, OLD_JS, NEW_JS, "signup email-link UI")
    print("OK")


if __name__ == "__main__":
    main()
