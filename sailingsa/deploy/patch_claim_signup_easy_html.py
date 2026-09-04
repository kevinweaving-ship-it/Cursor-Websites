#!/usr/bin/env python3
"""Signup.html ease pass (API already patched): optional WA/DOB, Google on claim path."""
from pathlib import Path
import shutil
import time
import re

SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
bak = Path(f"/root/backups/signup_easy_{ts}.html")
shutil.copy2(SIGNUP, bak)
print("BACKUP", bak)
html = SIGNUP.read_text(encoding="utf-8", errors="replace")

def must_replace(old, new, label):
    global html
    if old not in html:
        raise SystemExit(f"missing: {label}")
    html = html.replace(old, new, 1)
    print("ok", label)

must_replace(
    '<p class="signup-splash-copy">Email, Google, and Facebook sign up are available now. Apple is coming soon.</p>',
    '<p class="signup-splash-copy">Easiest: <b>Continue with Google</b> (about 30 seconds). Email works too. Facebook available. Apple soon.</p>',
    "splash copy",
)
must_replace(
    """                    <div class="signup-splash-footer">It's Free. It Takes <strong>30 Seconds.</strong></div>""",
    """                    <div class="signup-splash-footer">Free. Fastest with <strong>Google</strong>.</div>""",
    "splash footer",
)

must_replace(
    """                    <div class="btn-group" id="profileConfirmButtons">
                        <button class="btn-login btn-primary" onclick="handleProfileConfirm('me', currentProfile?.sas_id || '')">This is me</button>
                        <button class="btn-login btn-secondary" onclick="handleProfileConfirm('child', currentProfile?.sas_id || '')">This is my child / family member</button>
                        <button class="btn-login btn-back" onclick="showRegistrationForm()">Not me</button>
                    </div>""",
    """                    <div class="btn-group" id="profileConfirmButtons">
                        <button type="button" class="btn-login btn-google" onclick="loginWithGoogle()" style="margin-bottom:0.5rem;">Continue with Google — easiest</button>
                        <button class="btn-login btn-primary" onclick="handleProfileConfirm('me', currentProfile?.sas_id || '')">This is me — use email</button>
                        <button class="btn-login btn-secondary" onclick="handleProfileConfirm('child', currentProfile?.sas_id || '')">This is my child / family member</button>
                        <button class="btn-login btn-back" onclick="showRegistrationForm()">Not me</button>
                    </div>""",
    "confirm google CTA",
)

must_replace(
    """                <form id="regDataForm" onsubmit="handleRegistrationData(event)">""",
    """                <p id="regEasyGoogleNote" style="margin:0 0 0.75rem;padding:0.65rem 0.75rem;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;color:#1e3a8a;font-size:0.9rem;">
                    Prefer the easy path? <button type="button" class="btn-login btn-google" style="display:inline-block;width:auto;margin:0.35rem 0 0;padding:0.45rem 0.9rem;" onclick="loginWithGoogle()">Continue with Google</button>
                </p>
                <form id="regDataForm" onsubmit="handleRegistrationData(event)">""",
    "reg google note",
)

must_replace(
    """                        <label for="regWhatsApp" id="regWhatsAppLabel">WhatsApp Number <span style="color: red;">*</span></label>
                        <input type="text" id="regWhatsApp" name="whatsapp" required 
                               placeholder="082 123 4567" 
                               oninput="formatRegistrationWhatsApp(this)">
                        <div id="regWhatsAppHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666;">
                            Format: 082 123 4567 (10 digits)
                        </div>""",
    """                        <label for="regWhatsApp" id="regWhatsAppLabel">WhatsApp Number <span style="color: #666;">(optional)</span></label>
                        <input type="text" id="regWhatsApp" name="whatsapp"
                               placeholder="082 123 4567 (optional)" 
                               oninput="formatRegistrationWhatsApp(this)">
                        <div id="regWhatsAppHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666;">
                            Optional. Format if entered: 082 123 4567 (10 digits)
                        </div>""",
    "wa html optional",
)

must_replace(
    """                        <label for="regDob">Date of birth <span style="color: red;">*</span></label>
                        <input type="date" id="regDob" name="date_of_birth" required>""",
    """                        <label for="regDob">Date of birth <span style="color: #666;">(optional)</span></label>
                        <input type="date" id="regDob" name="date_of_birth">""",
    "dob html optional",
)

must_replace(
    """            if (whatsappLabel) whatsappLabel.innerHTML = 'WhatsApp Number <span style="color: red;">*</span>';
            if (whatsappInput) whatsappInput.required = true;
            if (whatsappHelp) whatsappHelp.textContent = 'Format: 082 123 4567 (10 digits)';""",
    """            if (whatsappLabel) whatsappLabel.innerHTML = 'WhatsApp Number <span style="color: #666;">(optional)</span>';
            if (whatsappInput) whatsappInput.required = false;
            if (whatsappHelp) whatsappHelp.textContent = 'Optional. Format if entered: 082 123 4567 (10 digits)';""",
    "wa js optional",
)

must_replace(
    "const whatsappValid = socialSignup ? (whatsappDigits.length === 0 || whatsappDigits.length === 10) : whatsappDigits.length === 10;",
    "const whatsappValid = (whatsappDigits.length === 0 || whatsappDigits.length === 10);",
    "whatsappValid",
)

must_replace(
    "const dobValid = /^\\d{4}-\\d{2}-\\d{2}$/.test(dob);",
    "const dobValid = true; // DOB optional — do not block sign-up",
    "dobValid",
)

must_replace(
    """            if ((!socialSignup && whatsappDigits.length !== 10) || (socialSignup && whatsappDigits.length > 0 && whatsappDigits.length !== 10)) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
                showError('WhatsApp number must be 10 digits');
                return;
            }""",
    """            if (whatsappDigits.length > 0 && whatsappDigits.length !== 10) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
                showError('WhatsApp number looks wrong — use 10 digits like 082 123 4567, or leave it blank');
                return;
            }""",
    "wa submit check",
)

must_replace(
    """            if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) {
                showError('Date of birth is required');
                return;
            }""",
    """            // Date of birth is optional — do not block sign-up
            if (false && !/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) {
                showError('Date of birth is required');
                return;
            }""",
    "dob submit check",
)

# plain error helper
if "function plainSignupError" not in html:
    must_replace(
        "        function trackClaimFunnel(",
        """        function plainSignupError(raw) {
            var e = String(raw || '').trim();
            var el = e.toLowerCase();
            if (!e) return 'Something went wrong — please try again';
            if (el.indexOf('more target columns') >= 0 || el.indexOf('login_method') >= 0)
                return 'Sign-up hit a server problem. Please use Continue with Google, or try again in a minute.';
            if (el.indexOf('already') >= 0 && (el.indexOf('email') >= 0 || el.indexOf('exist') >= 0 || el.indexOf('claim') >= 0))
                return (e.indexOf('Sign in') >= 0) ? e : (e + ' — try Sign in instead');
            if (el.indexOf('password') >= 0) return 'Check your password (and that both password fields match).';
            if (el.indexOf('whatsapp') >= 0 || el.indexOf('phone') >= 0)
                return 'WhatsApp number looks wrong — use 10 digits like 082 123 4567, or leave it blank.';
            if (el.indexOf('insert') >= 0 || el.indexOf('syntax') >= 0 || el.indexOf('sql') >= 0)
                return 'Could not create your account right now. Please try Continue with Google.';
            return e.length > 160 ? e.slice(0, 160) : e;
        }

        function trackClaimFunnel(""",
        "plainSignupError",
    )

# wrap showError for registration failure paths
html2 = html
# common patterns
for a, b in [
    ("showError(data.error || 'Registration failed. Please try again.');",
     "showError(plainSignupError(data.error || 'Registration failed. Please try again.'));"),
    ("showError(data.error || 'Registration failed');",
     "showError(plainSignupError(data.error || 'Registration failed'));"),
    ("showError(data.error);",
     "showError(plainSignupError(data.error));"),
]:
    if a in html2:
        html2 = html2.replace(a, b)
        print("ok showError wrap", a[:40])
html = html2

SIGNUP.write_text(html, encoding="utf-8")
print("DONE", SIGNUP.stat().st_size)
