#!/usr/bin/env python3
"""Loud Google CTA + required phone & date of birth on signup form."""
from pathlib import Path
import shutil
import time

SIGNUP = Path("/var/www/sailingsa/signup.html")
API = Path("/var/www/sailingsa/api/api.py")
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(SIGNUP, Path(f"/root/backups/signup_google_loud_{ts}.html"))
print("BACKUP signup", ts)
html = SIGNUP.read_text(encoding="utf-8", errors="replace")


def must_replace(old, new, label):
    global html
    if old not in html:
        raise SystemExit(f"missing signup: {label}")
    html = html.replace(old, new, 1)
    print("ok", label)


LOUD_CSS = """
            /* Loud Google — hard to miss */
            .reg-google-loud {
                margin: 0 0 1.1rem;
                padding: 1rem 1rem 1.05rem;
                background: linear-gradient(135deg, #fef08a 0%, #fde047 55%, #facc15 100%);
                border: 3px solid #ca8a04;
                border-radius: 12px;
                box-shadow: 0 6px 18px rgba(202, 138, 4, 0.45);
            }
            .reg-google-loud-title {
                margin: 0 0 0.55rem;
                font-size: 1.05rem;
                font-weight: 900;
                color: #713f12;
                text-align: center;
                letter-spacing: 0.02em;
            }
            .reg-google-loud-sub {
                margin: 0 0 0.75rem;
                font-size: 0.88rem;
                font-weight: 700;
                color: #854d0e;
                text-align: center;
                line-height: 1.35;
            }
            .reg-google-loud-btn {
                display: flex;
                width: 100%;
                align-items: center;
                justify-content: center;
                gap: 0.65rem;
                padding: 1rem 1.1rem;
                font-size: 1.12rem;
                font-weight: 900;
                line-height: 1.2;
                border: 2px solid #1f2937;
                border-radius: 10px;
                background: #fff;
                color: #111827;
                cursor: pointer;
                box-shadow: 0 3px 0 #1f2937;
            }
            .reg-google-loud-btn:active {
                transform: translateY(2px);
                box-shadow: 0 1px 0 #1f2937;
            }
            .reg-google-loud-btn svg {
                width: 1.35rem;
                height: 1.35rem;
                flex-shrink: 0;
            }
            .confirm-google-loud {
                margin-bottom: 0.85rem !important;
                padding: 1rem 1.1rem !important;
                font-size: 1.08rem !important;
                font-weight: 900 !important;
                border: 3px solid #ca8a04 !important;
                background: linear-gradient(135deg, #fef08a, #fde047) !important;
                color: #713f12 !important;
                box-shadow: 0 4px 12px rgba(202, 138, 4, 0.4) !important;
            }
"""

must_replace(
    "            #regProgressHint {",
    LOUD_CSS + "            #regProgressHint {",
    "css loud google",
)

GOOGLE_SVG = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>"""

must_replace(
    """                <p id="regEasyGoogleNote" style="margin:0 0 0.75rem;padding:0.65rem 0.75rem;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;color:#1e3a8a;font-size:0.9rem;">
                    Prefer the easy path? <button type="button" class="btn-login btn-google" style="display:inline-block;width:auto;margin:0.35rem 0 0;padding:0.45rem 0.9rem;" onclick="loginWithGoogle()">Continue with Google</button>
                </p>""",
    f"""                <div class="reg-google-loud" id="regGoogleLoud">
                    <p class="reg-google-loud-title">⚡ FASTEST WAY — USE GOOGLE</p>
                    <p class="reg-google-loud-sub">About 30 seconds. No password to remember.</p>
                    <button type="button" class="reg-google-loud-btn" onclick="loginWithGoogle()">
                        {GOOGLE_SVG}
                        Continue with Google
                    </button>
                </div>
                <p style="margin:0 0 0.65rem;text-align:center;font-size:0.85rem;font-weight:700;color:#64748b;">— or fill in the form below —</p>""",
    "loud google banner",
)

must_replace(
    """                    <p id="regProgressHint">Green tick = done. Optional fields: leave blank and press Tab (or Enter) to move on.</p>""",
    """                    <p id="regProgressHint">Green tick = done. Fields with <span style="color:#dc2626">*</span> are required.</p>""",
    "progress hint",
)

must_replace(
    """                        <label for="regWhatsApp" id="regWhatsAppLabel">WhatsApp / phone <span style="color: #666;">(optional — skip OK)</span></label>
                        <div class="reg-field-row">
                            <input type="tel" id="regWhatsApp" name="tel" autocomplete="tel" inputmode="tel"
                                   enterkeyhint="next" placeholder="082 123 4567" tabindex="5"
                                   oninput="formatRegistrationWhatsApp(this)">
                            <span class="reg-tick" id="tick-regWhatsApp" aria-hidden="true">✓</span>
                        </div>
                        <div id="regWhatsAppHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666;">
                            Optional. Your phone may suggest your number. Or leave blank / press Tab.
                        </div>""",
    """                        <label for="regWhatsApp" id="regWhatsAppLabel">WhatsApp / phone <span style="color: red;">*</span></label>
                        <div class="reg-field-row">
                            <input type="tel" id="regWhatsApp" name="tel" autocomplete="tel" inputmode="tel" required
                                   enterkeyhint="next" placeholder="082 123 4567" tabindex="5"
                                   oninput="formatRegistrationWhatsApp(this)">
                            <span class="reg-tick" id="tick-regWhatsApp" aria-hidden="true">✓</span>
                        </div>
                        <div id="regWhatsAppHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666;">
                            Required — 10 digits (e.g. 082 123 4567). Your phone can suggest your number.
                        </div>""",
    "wa required html",
)

must_replace(
    """                        <label for="regDob">Date of birth <span style="color: #666;">(optional — skip OK)</span></label>
                        <div class="reg-field-row">
                            <input type="date" id="regDob" name="bday" autocomplete="bday"
                                   enterkeyhint="done" tabindex="6"
                                   oninput="refreshRegFieldStatuses()" onchange="refreshRegFieldStatuses()">
                            <span class="reg-tick" id="tick-regDob" aria-hidden="true">✓</span>
                        </div>""",
    """                        <label for="regDob">Date of birth <span style="color: red;">*</span></label>
                        <div class="reg-field-row">
                            <input type="date" id="regDob" name="bday" autocomplete="bday" required
                                   enterkeyhint="done" tabindex="6"
                                   oninput="refreshRegFieldStatuses()" onchange="refreshRegFieldStatuses()">
                            <span class="reg-tick" id="tick-regDob" aria-hidden="true">✓</span>
                        </div>
                        <div id="regDobHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666; line-height: 1.4;">
                            Required — tap to pick <b>Year</b>, then <b>Month</b>, then <b>Day</b> (e.g. 1998 / March / 15).
                        </div>""",
    "dob required html",
)

must_replace(
    """                        <button type="button" class="btn-login btn-google" onclick="loginWithGoogle()" style="margin-bottom:0.5rem;">Continue with Google — easiest</button>""",
    """                        <button type="button" class="btn-login btn-google confirm-google-loud" onclick="loginWithGoogle()">⚡ Continue with Google — fastest (30 sec)</button>""",
    "confirm google loud",
)

# JS validation
must_replace(
    """            var wa = (document.getElementById('regWhatsApp')?.value || '').replace(/\\D/g, '');
            if (!wa) setRegTick('regWhatsApp', 'skip');
            else if (wa.length === 10) setRegTick('regWhatsApp', 'ok');
            else setRegTick('regWhatsApp', 'bad');

            var dob = document.getElementById('regDob')?.value || '';
            if (!dob) setRegTick('regDob', 'skip');
            else if (/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) setRegTick('regDob', 'ok');
            else setRegTick('regDob', 'bad');""",
    """            var wa = (document.getElementById('regWhatsApp')?.value || '').replace(/\\D/g, '');
            if (!wa) setRegTick('regWhatsApp', '');
            else if (wa.length === 10) setRegTick('regWhatsApp', 'ok');
            else setRegTick('regWhatsApp', 'bad');

            var dob = document.getElementById('regDob')?.value || '';
            if (!dob) setRegTick('regDob', '');
            else if (/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) setRegTick('regDob', 'ok');
            else setRegTick('regDob', 'bad');""",
    "tick wa dob required",
)

must_replace(
    """            if (wa.length > 0 && wa.length !== 10) {
                issues.push({ id: 'regWhatsApp', msg: 'WhatsApp must be 10 digits, or leave blank' });
            }
            return issues;""",
    """            if (wa.length !== 10) {
                issues.push({ id: 'regWhatsApp', msg: 'Enter your WhatsApp / phone — 10 digits like 082 123 4567' });
            }
            var dob = (document.getElementById('regDob')?.value || '').trim();
            if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) {
                issues.push({ id: 'regDob', msg: 'Enter date of birth — Year, then Month, then Day' });
            }
            return issues;""",
    "issues wa dob",
)

must_replace(
    "const whatsappValid = (whatsappDigits.length === 0 || whatsappDigits.length === 10);",
    "const whatsappValid = (whatsappDigits.length === 10);",
    "whatsappValid required",
)

must_replace(
    "const dobValid = true; // DOB optional — do not block sign-up",
    "const dobValid = /^\\d{4}-\\d{2}-\\d{2}$/.test(dob);",
    "dobValid required",
)

must_replace(
    """            if (whatsappDigits.length > 0 && whatsappDigits.length !== 10) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
                showError('WhatsApp number looks wrong — use 10 digits like 082 123 4567, or leave it blank');
                return;
            }""",
    """            if (whatsappDigits.length !== 10) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'whatsapp_digits', {}); } catch (e2) {}
                showRegIssuesAndFocus(collectRegFormIssues());
                return;
            }""",
    "submit wa required",
)

must_replace(
    """            const dob = document.getElementById('regDob')?.value || '';
            // Date of birth is optional — do not block sign-up
            if (false && !/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) {
                showError('Date of birth is required');
                return;
            }""",
    """            const dob = document.getElementById('regDob')?.value || '';
            if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(dob)) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'dob_missing', {}); } catch (eDob) {}
                showRegIssuesAndFocus(collectRegFormIssues());
                return;
            }""",
    "submit dob required",
)

SIGNUP.write_text(html, encoding="utf-8")
print("WROTE signup", len(html))

# --- API: persist date_of_birth ---
if API.exists():
    import py_compile

    shutil.copy2(API, Path(f"/root/backups/api_dob_required_{ts}.py"))
    api = API.read_text(encoding="utf-8", errors="replace")
    dob_snippet_reg = (
        "        date_of_birth = str(body.get('date_of_birth') or '').strip()\n"
        "        if date_of_birth and re.match(r'^\\d{4}-\\d{2}-\\d{2}$', date_of_birth) and sas_id:\n"
        "            try:\n"
        '                cur.execute(\n'
        '                    "UPDATE public.sas_id_personal SET date_of_birth = %s WHERE sa_sailing_id::text = %s",\n'
        "                    (date_of_birth, str(sas_id)),\n"
        "                )\n"
        "            except Exception:\n"
        "                pass\n"
    )
    reg_anchor = "        try:\n            rel = str(relationship or \"self\").strip().lower() or \"self\""
    reg_pos = api.find("async def register_account")
    if reg_pos >= 0 and "date_of_birth = str(body.get('date_of_birth')" not in api[reg_pos : reg_pos + 6000]:
        api = api.replace(reg_anchor, dob_snippet_reg + reg_anchor, 1)
        print("ok api register dob")
    dob_snippet_google = (
        '        date_of_birth = str(payload.get("date_of_birth") or "").strip()\n'
        '        if date_of_birth and re.match(r"^\\d{4}-\\d{2}-\\d{2}$", date_of_birth) and sas_id:\n'
        "            try:\n"
        '                cur.execute(\n'
        '                    "UPDATE public.sas_id_personal SET date_of_birth = %s WHERE sa_sailing_id::text = %s",\n'
        "                    (date_of_birth, str(sas_id)),\n"
        "                )\n"
        "            except Exception:\n"
        "                pass\n\n"
    )
    g_anchor = "\n        if password:"
    gpos = api.find("async def google_confirm_link")
    if gpos >= 0 and 'payload.get("date_of_birth")' not in api[gpos : gpos + 6000]:
        sub = api[gpos : gpos + 6000]
        idx = sub.find(g_anchor)
        if idx >= 0:
            abs_idx = gpos + idx
            api = api[:abs_idx] + "\n" + dob_snippet_google + api[abs_idx + 1 :]
            print("ok api google dob")
    API.write_text(api, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("WROTE api")

for token in ["reg-google-loud", "FASTEST WAY", "Required — tap to pick", "whatsappValid = (whatsappDigits.length === 10)"]:
    assert token in html or token.replace("whatsappValid = (whatsappDigits.length === 10)", "const whatsappValid = (whatsappDigits.length === 10)") in html, token
print("SANITY_OK")
