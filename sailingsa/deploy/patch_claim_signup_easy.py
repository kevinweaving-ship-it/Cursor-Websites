#!/usr/bin/env python3
"""Make claim/sign-up easier: optional WhatsApp/DOB, Google on claim path, plain errors."""
from pathlib import Path
import shutil
import time
import re

API = Path("/var/www/sailingsa/api/api.py")
SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
bak = Path(f"/root/backups/claim_easy_{ts}")
bak.mkdir(parents=True, exist_ok=True)
shutil.copy2(API, bak / "api.py")
shutil.copy2(SIGNUP, bak / "signup.html")
print("BACKUP", bak)

# ---- API: WhatsApp optional + plain English errors ----
api = API.read_text(encoding="utf-8", errors="replace")

old_req = '''        if not email or not password or not whatsapp:
            return {"error": "Email, password, and WhatsApp number are required"}
'''
new_req = '''        if not email or not password:
            return {"error": "Please enter your email and a password"}
'''
if old_req not in api:
    raise SystemExit("register required-fields anchor missing")
api = api.replace(old_req, new_req, 1)

# plain error helper near register_account except
old_exc = '''    except Exception as e:
        print(f"Error registering account: {e}")
        traceback.print_exc()
        try:
            _lean_record_funnel_event(
                funnel_name="claim_profile",
                step_key="verification_failed",
                visitor_id="",
                sas_id=str(locals().get("sas_id") or ""),
                url_path="/signup.html",
                ok=False,
                error_code=str(e)[:120],
                meta={"source": "register_account"},
            )
        except Exception:
            pass
        return {"error": str(e)}
'''
new_exc = '''    except Exception as e:
        print(f"Error registering account: {e}")
        traceback.print_exc()
        try:
            _lean_record_funnel_event(
                funnel_name="claim_profile",
                step_key="verification_failed",
                visitor_id="",
                sas_id=str(locals().get("sas_id") or ""),
                url_path="/signup.html",
                ok=False,
                error_code=str(e)[:120],
                meta={"source": "register_account"},
            )
        except Exception:
            pass
        msg = str(e or "")
        ml = msg.lower()
        if "unique" in ml or "duplicate" in ml or "already exists" in ml:
            plain = "That email is already registered — try Sign in instead"
        elif "more target columns" in ml or "login_method" in ml:
            plain = "Sign-up hit a server problem — please try Continue with Google, or try again in a minute"
        else:
            plain = "Could not create your account. Please try Continue with Google, or try again."
        return {"error": plain}
'''
if old_exc not in api:
    raise SystemExit("register except anchor missing")
api = api.replace(old_exc, new_exc, 1)

# Google complete: funnel + plain error
old_g = '''        session_token = _create_login_session_record(cur, request, google_account_id, sas_id, "google")
        conn.commit()
        cur.close()
        return_db_connection(conn)
        conn = None
        return {"success": True, "session_token": session_token, "sas_id": sas_id}
    except Exception as e:
        print(f"Error confirming Google signup: {e}")
        traceback.print_exc()
        return {"error": str(e)}
'''
new_g = '''        session_token = _create_login_session_record(cur, request, google_account_id, sas_id, "google")
        conn.commit()
        cur.close()
        return_db_connection(conn)
        conn = None
        try:
            _lean_record_funnel_event(
                funnel_name="claim_profile",
                step_key="claim_completed",
                visitor_id="",
                sas_id=str(sas_id or ""),
                url_path="/signup.html",
                ok=True,
                error_code="",
                meta={"source": "google_signup", "login_method": "google"},
            )
        except Exception:
            pass
        return {"success": True, "session_token": session_token, "sas_id": sas_id}
    except Exception as e:
        print(f"Error confirming Google signup: {e}")
        traceback.print_exc()
        try:
            _lean_record_funnel_event(
                funnel_name="claim_profile",
                step_key="verification_failed",
                visitor_id="",
                sas_id=str(locals().get("sas_id") or ""),
                url_path="/signup.html",
                ok=False,
                error_code=str(e)[:120],
                meta={"source": "google_signup"},
            )
        except Exception:
            pass
        return {"error": "Could not finish Google sign-up. Please try again, or use email."}
'''
if old_g not in api:
    raise SystemExit("google complete anchor missing")
api = api.replace(old_g, new_g, 1)

API.write_text(api, encoding="utf-8")
print("API OK")

# ---- signup.html ----
html = SIGNUP.read_text(encoding="utf-8", errors="replace")

# Splash copy
old_copy = '''                    <p class="signup-splash-copy">Email, Google, and Facebook sign up are available now. Apple is coming soon.</p>'''
new_copy = '''                    <p class="signup-splash-copy">Easiest: <b>Continue with Google</b> (about 30 seconds). Email works too. Facebook available. Apple soon.</p>'''
if old_copy in html:
    html = html.replace(old_copy, new_copy, 1)

old_footer = '''                    <div class="signup-splash-footer">It's Free. It Takes <strong>30 Seconds.</strong></div>'''
new_footer = '''                    <div class="signup-splash-footer">Free. Fastest with <strong>Google</strong>.</div>'''
if old_footer in html:
    html = html.replace(old_footer, new_footer, 1)

# WhatsApp optional for email path in configureRegistrationFormForContext
old_wa = '''                if (whatsappLabel) whatsappLabel.innerHTML = 'WhatsApp Number <span style="color: red;">*</span>';
                if (whatsappInput) whatsappInput.required = true;
                if (whatsappHelp) whatsappHelp.textContent = 'Format: 082 123 4567 (10 digits)';'''
new_wa = '''                if (whatsappLabel) whatsappLabel.innerHTML = 'WhatsApp Number <span style="color: #666;">(optional)</span>';
                if (whatsappInput) whatsappInput.required = false;
                if (whatsappHelp) whatsappHelp.textContent = 'Optional. Format if entered: 082 123 4567 (10 digits)';'''
if old_wa not in html:
    raise SystemExit("whatsapp required UI anchor missing")
html = html.replace(old_wa, new_wa, 1)

# DOB optional label in HTML
html = html.replace(
    '''<label for="regDob">Date of Birth <span style="color: red;">*</span></label>
                        <input type="date" id="regDob" name="date_of_birth" required>''',
    '''<label for="regDob">Date of Birth <span style="color: #666;">(optional)</span></label>
                        <input type="date" id="regDob" name="date_of_birth">''',
    1,
)

# Validation: whatsapp + dob optional for email
old_val = '''            const whatsappValid = socialSignup ? (whatsappDigits.length === 0 || whatsappDigits.length === 10) : whatsappDigits.length === 10;'''
new_val = '''            const whatsappValid = (whatsappDigits.length === 0 || whatsappDigits.length === 10);'''
if old_val not in html:
    raise SystemExit("whatsappValid anchor missing")
html = html.replace(old_val, new_val, 1)

# Find dobValid in updateRegistrationSubmitButton
# typically: const dobValid = !!dob; or similar
m = re.search(r"const dobValid = [^;]+;", html)
if not m:
    # try other patterns
    print("dobValid search...")
    for line in html.splitlines():
        if "dobValid" in line:
            print(" ", line.strip()[:120])
else:
    html = html.replace(m.group(0), "const dobValid = true; // DOB optional — do not block sign-up", 1)
    print("dobValid relaxed")

# handleRegistrationData: don't block on missing whatsapp/dob
old_wa_check = '''            if ((!socialSignup && whatsappDigits.length !== 10) || (socialSignup && whatsappDigits.length > 0 && whatsappDigits.length !== 10)) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
'''
# read exact block from file via soft replace of showError for whatsapp
# Soften DOB required check
html = html.replace(
    '''            if (!dob) {
                showError('Date of birth is required');
''',
    '''            if (false && !dob) {
                showError('Date of birth is required');
''',
    1,
)

# Soften whatsapp hard-require for non-social: allow empty; only reject bad length
# Find the whatsapp validation block more carefully
old_wa_block = None
idx = html.find("whatsappDigits.length !== 10")
print("whatsappDigits idx", idx)

# Add Google CTA on confirm profile buttons
old_btns = '''                    <div class="btn-group" id="profileConfirmButtons">
                        <button class="btn-login btn-primary" onclick="handleProfileConfirm('me', currentProfile?.sas_id || '')">This is me</button>
                        <button class="btn-login btn-secondary" onclick="handleProfileConfirm('child', currentProfile?.sas_id || '')">This is my child / family member</button>
                        <button class="btn-login btn-back" onclick="showRegistrationForm()">Not me</button>
                    </div>'''
new_btns = '''                    <div class="btn-group" id="profileConfirmButtons">
                        <button type="button" class="btn-login btn-google" onclick="loginWithGoogle()" style="margin-bottom:0.5rem;">Continue with Google — easiest</button>
                        <button class="btn-login btn-primary" onclick="handleProfileConfirm('me', currentProfile?.sas_id || '')">This is me — use email</button>
                        <button class="btn-login btn-secondary" onclick="handleProfileConfirm('child', currentProfile?.sas_id || '')">This is my child / family member</button>
                        <button class="btn-login btn-back" onclick="showRegistrationForm()">Not me</button>
                    </div>'''
if old_btns not in html:
    raise SystemExit("confirm buttons missing")
html = html.replace(old_btns, new_btns, 1)

# Note above reg form
old_reg_h = None
if 'id="registrationDataForm"' in html:
    html = html.replace(
        '''<div id="registrationDataForm" class="login-section">''',
        '''<div id="registrationDataForm" class="login-section">''',
        1,
    )
# inject easy google note into registration data card if possible
html = html.replace(
    '''                <form id="regDataForm" onsubmit="handleRegistrationData(event)">''',
    '''                <p id="regEasyGoogleNote" style="margin:0 0 0.75rem;padding:0.65rem 0.75rem;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;color:#1e3a8a;font-size:0.9rem;">
                    Prefer the easy path? <button type="button" class="btn-login btn-google" style="display:inline-block;width:auto;margin:0.35rem 0 0;padding:0.45rem 0.9rem;" onclick="loginWithGoogle()">Continue with Google</button>
                </p>
                <form id="regDataForm" onsubmit="handleRegistrationData(event)">''',
    1,
)

# Plain-English client error sanitizer for API errors
old_show_fail = '''                    try { trackClaimFunnel('verification_failed', currentProfile.sas_id || claimSelectedSasId || '', false, String(data.error || '').slice(0, 120), {}); } catch (e6) {}
'''
# find showError(data.error) nearby
if "showError(data.error" in html or "showError(data.error ||" in html:
    html = html.replace(
        "showError(data.error || 'Registration failed')",
        "showError(plainSignupError(data.error || 'Registration failed'))",
    )
    html = html.replace(
        "showError(data.error)",
        "showError(plainSignupError(data.error))",
    )

# Add plainSignupError function near trackClaimFunnel
marker = "        function trackClaimFunnel("
plain_fn = '''        function plainSignupError(raw) {
            var e = String(raw || '').trim();
            var el = e.toLowerCase();
            if (!e) return 'Something went wrong — please try again';
            if (el.indexOf('more target columns') >= 0 || el.indexOf('login_method') >= 0)
                return 'Sign-up hit a server problem. Please use Continue with Google, or try again in a minute.';
            if (el.indexOf('already') >= 0 && (el.indexOf('email') >= 0 || el.indexOf('exist') >= 0 || el.indexOf('claim') >= 0))
                return e.indexOf('Sign in') >= 0 ? e : (e + ' — try Sign in instead');
            if (el.indexOf('password') >= 0) return 'Check your password (and that both password fields match).';
            if (el.indexOf('whatsapp') >= 0 || el.indexOf('phone') >= 0) return 'WhatsApp number looks wrong — use 10 digits like 082 123 4567, or leave it blank.';
            if (el.indexOf('insert') >= 0 || el.indexOf('syntax') >= 0 || el.indexOf('sql') >= 0)
                return 'Could not create your account right now. Please try Continue with Google.';
            return e.length > 160 ? e.slice(0, 160) : e;
        }

'''
if marker in html and "function plainSignupError" not in html:
    html = html.replace(marker, plain_fn + marker, 1)
    print("plainSignupError added")

# Fix whatsapp client hard-require: change non-social require to optional empty OK
# Exact block from earlier read
old_block = '''            if ((!socialSignup && whatsappDigits.length !== 10) || (socialSignup && whatsappDigits.length > 0 && whatsappDigits.length !== 10)) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
'''
# Need full block with showError - get from file
import re as _re
pat = _re.compile(
    r"if \(\(!socialSignup && whatsappDigits\.length !== 10\) \|\| \(socialSignup && whatsappDigits\.length > 0 && whatsappDigits\.length !== 10\)\) \{[\s\S]*?return;\s*\}",
    _re.M,
)
m2 = pat.search(html)
if not m2:
    raise SystemExit("whatsapp submit check block missing")
html = html[: m2.start()] + '''if (whatsappDigits.length > 0 && whatsappDigits.length !== 10) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
                showError('WhatsApp number looks wrong — use 10 digits like 082 123 4567, or leave it blank');
                return;
            }''' + html[m2.end() :]
print("whatsapp submit check relaxed")

SIGNUP.write_text(html, encoding="utf-8")
print("SIGNUP OK")
print("DONE")
