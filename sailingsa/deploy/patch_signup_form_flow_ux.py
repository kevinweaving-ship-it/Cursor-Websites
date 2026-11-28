#!/usr/bin/env python3
"""Signup registration form: easy field flow (ticks, tab/enter, autofill, end validation)."""
from pathlib import Path
import shutil
import time

SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
bak = Path(f"/root/backups/signup_form_flow_ux_{ts}.html")
bak.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(SIGNUP, bak)
print("BACKUP", bak)
html = SIGNUP.read_text(encoding="utf-8", errors="replace")


def must_replace(old, new, label):
    global html
    if old not in html:
        raise SystemExit(f"missing: {label}")
    html = html.replace(old, new, 1)
    print("ok", label)


# --- CSS: field status ticks ---
CSS = """
            /* Easy signup field flow */
            #regDataForm .form-group { position: relative; }
            #regDataForm .reg-field-row {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            #regDataForm .reg-field-row input {
                flex: 1;
                min-width: 0;
            }
            #regDataForm .reg-tick {
                flex: 0 0 1.75rem;
                width: 1.75rem;
                height: 1.75rem;
                border-radius: 50%;
                border: 2px solid #cbd5e1;
                background: #f8fafc;
                color: transparent;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 0.95rem;
                font-weight: 800;
                line-height: 1;
            }
            #regDataForm .reg-tick.is-ok {
                border-color: #16a34a;
                background: #16a34a;
                color: #fff;
            }
            #regDataForm .reg-tick.is-bad {
                border-color: #dc2626;
                background: #fee2e2;
                color: #dc2626;
            }
            #regDataForm .reg-tick.is-skip {
                border-color: #94a3b8;
                background: #e2e8f0;
                color: #475569;
                font-size: 0.65rem;
                font-weight: 700;
            }
            #regDataForm input.reg-ok { border-color: #16a34a !important; }
            #regDataForm input.reg-bad { border-color: #dc2626 !important; }
            #regIssuesBox {
                display: none;
                margin: 0 0 0.85rem;
                padding: 0.75rem 0.85rem;
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                color: #7f1d1d;
                font-size: 0.9rem;
            }
            #regIssuesBox.show { display: block; }
            #regIssuesBox ul { margin: 0.35rem 0 0 1.1rem; padding: 0; }
            #regIssuesBox li { margin: 0.2rem 0; }
            #regIssuesBox a {
                color: #b91c1c;
                font-weight: 700;
                text-decoration: underline;
                cursor: pointer;
            }
            #regProgressHint {
                margin: 0 0 0.75rem;
                font-size: 0.85rem;
                color: #334155;
            }
"""

must_replace(
    """        }
    </style>
    <link rel="icon" href="/fav""",
    CSS
    + """        }
    </style>
    <link rel="icon" href="/fav""",
    "css field ticks",
)

# --- Form HTML ---
OLD_FORM = """                <form id="regDataForm" onsubmit="handleRegistrationData(event)">
                    <div class="form-group" id="regEmailGroup">
                        <label for="regEmail" id="regEmailLabel">Email Address <span style="color: red;">*</span></label>
                        <input type="email" id="regEmail" name="email" required 
                               placeholder="your.email@example.com"
                               oninput="validateRegistrationEmail()">
                        <div id="reg-email-error" style="margin-top: 0.4rem; font-size: 0.75rem; color: #dc3545; display: none;">
                            Not valid email address
                        </div>
                    </div>
                    
                    <div class="form-group" id="regPasswordGroup">
                        <label for="regPassword">Password <span style="color: red;">*</span></label>
                        <input type="password" id="regPassword" name="password" required 
                               placeholder="Enter password" oninput="validateRegistrationPassword()">
                        <div id="reg-password-rules" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666; line-height: 1.3;">
                            <div id="reg-rule-length" style="color: #999;">✓ At least 7 characters</div>
                            <div id="reg-rule-capital" style="color: #999;">✓ One capital letter</div>
                            <div id="reg-rule-special" style="color: #999;">✓ One special character (#, @, !, etc.)</div>
                            <div id="reg-rule-number" style="color: #999;">✓ One number</div>
                        </div>
                    </div>
                    
                    <div class="form-group" id="regPasswordConfirmGroup">
                        <label for="regPasswordConfirm">Confirm Password <span style="color: red;">*</span></label>
                        <input type="password" id="regPasswordConfirm" name="passwordConfirm" required 
                               placeholder="Re-enter password" oninput="checkRegistrationPasswordMatch()">
                        <div id="reg-password-match" style="margin-top: 0.4rem; font-size: 0.75rem; display: none;"></div>
                    </div>
                    
                    <div class="form-group" id="regWhatsAppGroup">
                        <label for="regWhatsApp" id="regWhatsAppLabel">WhatsApp Number <span style="color: #666;">(optional)</span></label>
                        <input type="text" id="regWhatsApp" name="whatsapp"
                               placeholder="082 123 4567 (optional)" 
                               oninput="formatRegistrationWhatsApp(this)">
                        <div id="regWhatsAppHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666;">
                            Optional. Format if entered: 082 123 4567 (10 digits)
                        </div>
                    </div>
                    
                    <div class="form-group" id="regDobGroup">
                        <label for="regDob">Date of birth <span style="color: #666;">(optional)</span></label>
                        <input type="date" id="regDob" name="date_of_birth">
                    </div>

                    <div class="form-group" id="regClubGroup">
                        <label>Club</label>
                        <div id="regClubNow" style="display:flex;align-items:center;gap:6px;min-height:22px;font-size:13px;font-weight:700;color:#001f3f;"></div>
                    </div>
                    
                    <div class="form-group" id="regAvatarGroup">
                        <label>Profile photo <span style="color:#64748b;font-weight:600;">(optional)</span></label>
                        <div id="regAvatarCrop"></div>
                    </div>

                    <div class="form-group" id="regSkipperGroup">
                        <h3 style="margin:8px 0 4px;color:#001f3f;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;">Optional</h3>
                        <label for="regSkipperFile">SAMSA Skippers certificate</label>
                        <input id="regSkipperFile" type="file" accept="image/jpeg,image/png,application/pdf">
                        <div style="margin-top:0.35rem;font-size:0.75rem;color:#666;">Upload a photo or PDF if you got Skippers from a SAMSA authorised college.</div>
                    </div>
                    
                    <div class="btn-group">
                        <button type="submit" id="regSubmitBtn" class="btn-login btn-primary" disabled
                                onclick="if(this.disabled) { event.preventDefault(); showError('Please complete all required fields correctly'); return false; }">
                            Complete Registration
                        </button>
                        <button type="button" class="btn-login btn-back" onclick="showConfirmProfile()">Back</button>
                    </div>
                </form>"""

NEW_FORM = """                <form id="regDataForm" novalidate autocomplete="on" onsubmit="handleRegistrationData(event)">
                    <p id="regProgressHint">Green tick = done. Optional fields can be left blank — tap <b>Skip</b> or press Tab.</p>
                    <div id="regIssuesBox" role="alert" aria-live="polite"></div>

                    <div class="form-group" id="regNameGroup">
                        <label for="regFullName">Your name <span style="color:#666;">(from your phone if available)</span></label>
                        <div class="reg-field-row">
                            <input type="text" id="regFullName" name="name" autocomplete="name"
                                   placeholder="Name Surname" tabindex="1"
                                   oninput="refreshRegFieldStatuses()">
                            <span class="reg-tick" id="tick-regFullName" aria-hidden="true">✓</span>
                        </div>
                    </div>

                    <div class="form-group" id="regEmailGroup">
                        <label for="regEmail" id="regEmailLabel">Email Address <span style="color: red;">*</span></label>
                        <div class="reg-field-row">
                            <input type="email" id="regEmail" name="email" required
                                   autocomplete="email" inputmode="email" enterkeyhint="next"
                                   placeholder="your.email@example.com" tabindex="2"
                                   oninput="validateRegistrationEmail()">
                            <span class="reg-tick" id="tick-regEmail" aria-hidden="true">✓</span>
                        </div>
                        <div id="reg-email-error" style="margin-top: 0.4rem; font-size: 0.75rem; color: #dc3545; display: none;">
                            Not a valid email yet
                        </div>
                    </div>
                    
                    <div class="form-group" id="regPasswordGroup">
                        <label for="regPassword">Password <span style="color: red;">*</span></label>
                        <div class="reg-field-row">
                            <input type="password" id="regPassword" name="password" required
                                   autocomplete="new-password" enterkeyhint="next"
                                   placeholder="At least 7 characters" tabindex="3"
                                   oninput="validateRegistrationPassword()">
                            <span class="reg-tick" id="tick-regPassword" aria-hidden="true">✓</span>
                        </div>
                        <div id="reg-password-rules" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666; line-height: 1.3;">
                            <div id="reg-rule-length" style="color: #999;">✓ At least 7 characters (needed)</div>
                            <div id="reg-rule-capital" style="color: #999;">○ Capital letter (nice to have)</div>
                            <div id="reg-rule-special" style="color: #999;">○ Special character (nice to have)</div>
                            <div id="reg-rule-number" style="color: #999;">○ A number (nice to have)</div>
                        </div>
                    </div>
                    
                    <div class="form-group" id="regPasswordConfirmGroup">
                        <label for="regPasswordConfirm">Confirm Password <span style="color: red;">*</span></label>
                        <div class="reg-field-row">
                            <input type="password" id="regPasswordConfirm" name="passwordConfirm" required
                                   autocomplete="new-password" enterkeyhint="next"
                                   placeholder="Type the same password again" tabindex="4"
                                   oninput="checkRegistrationPasswordMatch()">
                            <span class="reg-tick" id="tick-regPasswordConfirm" aria-hidden="true">✓</span>
                        </div>
                        <div id="reg-password-match" style="margin-top: 0.4rem; font-size: 0.75rem; display: none;"></div>
                    </div>
                    
                    <div class="form-group" id="regWhatsAppGroup">
                        <label for="regWhatsApp" id="regWhatsAppLabel">WhatsApp / phone <span style="color: #666;">(optional — skip OK)</span></label>
                        <div class="reg-field-row">
                            <input type="tel" id="regWhatsApp" name="tel" autocomplete="tel" inputmode="tel"
                                   enterkeyhint="next" placeholder="082 123 4567" tabindex="5"
                                   oninput="formatRegistrationWhatsApp(this)">
                            <span class="reg-tick" id="tick-regWhatsApp" aria-hidden="true">✓</span>
                        </div>
                        <div id="regWhatsAppHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666;">
                            Optional. Your phone may suggest your number. Or leave blank / press Tab.
                        </div>
                    </div>
                    
                    <div class="form-group" id="regDobGroup">
                        <label for="regDob">Date of birth <span style="color: #666;">(optional — skip OK)</span></label>
                        <div class="reg-field-row">
                            <input type="date" id="regDob" name="bday" autocomplete="bday"
                                   enterkeyhint="done" tabindex="6"
                                   oninput="refreshRegFieldStatuses()" onchange="refreshRegFieldStatuses()">
                            <span class="reg-tick" id="tick-regDob" aria-hidden="true">✓</span>
                        </div>
                    </div>

                    <div class="form-group" id="regClubGroup">
                        <label>Club</label>
                        <div id="regClubNow" style="display:flex;align-items:center;gap:6px;min-height:22px;font-size:13px;font-weight:700;color:#001f3f;"></div>
                    </div>
                    
                    <div class="form-group" id="regAvatarGroup">
                        <label>Profile photo <span style="color:#64748b;font-weight:600;">(optional)</span></label>
                        <div id="regAvatarCrop"></div>
                    </div>

                    <div class="form-group" id="regSkipperGroup">
                        <h3 style="margin:8px 0 4px;color:#001f3f;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;">Optional extras</h3>
                        <label for="regSkipperFile">SAMSA Skippers certificate</label>
                        <input id="regSkipperFile" type="file" accept="image/jpeg,image/png,application/pdf" tabindex="7">
                        <div style="margin-top:0.35rem;font-size:0.75rem;color:#666;">Upload a photo or PDF if you got Skippers from a SAMSA authorised college. Skip if you do not have one.</div>
                    </div>
                    
                    <div class="btn-group">
                        <button type="submit" id="regSubmitBtn" class="btn-login btn-primary" tabindex="8">
                            Complete Registration
                        </button>
                        <button type="button" class="btn-login btn-back" onclick="showConfirmProfile()" tabindex="9">Back</button>
                    </div>
                </form>"""

must_replace(OLD_FORM, NEW_FORM, "reg form html")

# --- JS helpers: inject before validateRegistrationEmail ---
JS_HELPERS = r"""
        var REG_FIELD_ORDER = ['regFullName', 'regEmail', 'regPassword', 'regPasswordConfirm', 'regWhatsApp', 'regDob', 'regSkipperFile', 'regSubmitBtn'];

        function setRegTick(inputId, state) {
            var tick = document.getElementById('tick-' + inputId);
            var input = document.getElementById(inputId);
            if (tick) {
                tick.classList.remove('is-ok', 'is-bad', 'is-skip');
                if (state === 'ok') {
                    tick.classList.add('is-ok');
                    tick.textContent = '✓';
                } else if (state === 'bad') {
                    tick.classList.add('is-bad');
                    tick.textContent = '!';
                } else if (state === 'skip') {
                    tick.classList.add('is-skip');
                    tick.textContent = 'skip';
                } else {
                    tick.textContent = '✓';
                }
            }
            if (input && input.tagName === 'INPUT') {
                input.classList.remove('reg-ok', 'reg-bad');
                if (state === 'ok') input.classList.add('reg-ok');
                if (state === 'bad') input.classList.add('reg-bad');
            }
        }

        function refreshRegFieldStatuses() {
            var socialSignup = (typeof getSocialSignupContext === 'function') ? getSocialSignupContext() : null;
            var nameEl = document.getElementById('regFullName');
            var nameVal = (nameEl && nameEl.value || '').trim();
            if (nameVal.length >= 2) setRegTick('regFullName', 'ok');
            else if (nameVal.length === 1) setRegTick('regFullName', 'bad');
            else setRegTick('regFullName', 'skip');

            var email = document.getElementById('regEmail')?.value || '';
            var effectiveEmail = socialSignup ? (socialSignup.email || email || '') : email;
            if (!effectiveEmail) setRegTick('regEmail', '');
            else if (typeof isValidEmail === 'function' && isValidEmail(effectiveEmail)) setRegTick('regEmail', 'ok');
            else setRegTick('regEmail', 'bad');

            var password = document.getElementById('regPassword')?.value || '';
            if (socialSignup) setRegTick('regPassword', 'skip');
            else if (!password) setRegTick('regPassword', '');
            else if (password.length >= 7) setRegTick('regPassword', 'ok');
            else setRegTick('regPassword', 'bad');

            var confirm = document.getElementById('regPasswordConfirm')?.value || '';
            if (socialSignup) setRegTick('regPasswordConfirm', 'skip');
            else if (!confirm) setRegTick('regPasswordConfirm', '');
            else if (password.length >= 7 && password === confirm) setRegTick('regPasswordConfirm', 'ok');
            else setRegTick('regPasswordConfirm', 'bad');

            var wa = (document.getElementById('regWhatsApp')?.value || '').replace(/\D/g, '');
            if (!wa) setRegTick('regWhatsApp', 'skip');
            else if (wa.length === 10) setRegTick('regWhatsApp', 'ok');
            else setRegTick('regWhatsApp', 'bad');

            var dob = document.getElementById('regDob')?.value || '';
            if (!dob) setRegTick('regDob', 'skip');
            else if (/^\d{4}-\d{2}-\d{2}$/.test(dob)) setRegTick('regDob', 'ok');
            else setRegTick('regDob', 'bad');

            updateRegistrationSubmitButton();
        }

        function collectRegFormIssues() {
            var issues = [];
            var socialSignup = (typeof getSocialSignupContext === 'function') ? getSocialSignupContext() : null;
            var email = (document.getElementById('regEmail')?.value || '').trim();
            var effectiveEmail = (socialSignup ? (socialSignup.email || email || '') : email).trim();
            var password = document.getElementById('regPassword')?.value || '';
            var confirm = document.getElementById('regPasswordConfirm')?.value || '';
            var wa = (document.getElementById('regWhatsApp')?.value || '').replace(/\D/g, '');

            if (!socialSignup) {
                if (!isValidEmail(effectiveEmail)) {
                    issues.push({ id: 'regEmail', msg: 'Enter a valid email (your phone can suggest it)' });
                }
                if (password.length < 7) {
                    issues.push({ id: 'regPassword', msg: 'Password needs at least 7 characters' });
                }
                if (password.length >= 7 && password !== confirm) {
                    issues.push({ id: 'regPasswordConfirm', msg: 'Confirm password must match' });
                }
            } else if (effectiveEmail && !isValidEmail(effectiveEmail)) {
                issues.push({ id: 'regEmail', msg: 'Email looks wrong' });
            }
            if (wa.length > 0 && wa.length !== 10) {
                issues.push({ id: 'regWhatsApp', msg: 'WhatsApp must be 10 digits, or leave blank' });
            }
            return issues;
        }

        function showRegIssuesAndFocus(issues) {
            var box = document.getElementById('regIssuesBox');
            if (!box) {
                if (issues.length) showError(issues[0].msg);
                return;
            }
            if (!issues.length) {
                box.classList.remove('show');
                box.innerHTML = '';
                return;
            }
            var html = '<b>Almost there — please fix:</b><ul>';
            issues.forEach(function (it) {
                html += '<li><a href="javascript:void(0)" data-focus="' + it.id + '">' + it.msg + '</a></li>';
            });
            html += '</ul>';
            box.innerHTML = html;
            box.classList.add('show');
            box.querySelectorAll('a[data-focus]').forEach(function (a) {
                a.addEventListener('click', function () {
                    var el = document.getElementById(a.getAttribute('data-focus'));
                    if (el) { el.focus(); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                });
            });
            var first = document.getElementById(issues[0].id);
            if (first) {
                try { first.focus(); } catch (e) {}
                try { first.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e2) {}
            }
            showError(issues[0].msg);
        }

        function focusNextRegField(currentId) {
            var order = REG_FIELD_ORDER;
            var ix = order.indexOf(currentId);
            for (var i = ix + 1; i < order.length; i++) {
                var el = document.getElementById(order[i]);
                if (!el) continue;
                if (el.disabled) continue;
                if (el.offsetParent === null && el.id !== 'regSubmitBtn') continue;
                try { el.focus(); } catch (e) {}
                return;
            }
        }

        function wireRegFormFieldFlow() {
            var form = document.getElementById('regDataForm');
            if (!form || form.dataset.flowWired === '1') return;
            form.dataset.flowWired = '1';
            form.addEventListener('keydown', function (ev) {
                if (ev.key !== 'Enter') return;
                var t = ev.target;
                if (!t || !t.id) return;
                if (t.id === 'regSubmitBtn' || t.tagName === 'BUTTON') return;
                if (t.tagName === 'TEXTAREA') return;
                ev.preventDefault();
                focusNextRegField(t.id);
            });
            // Prefill name from selected sailor so the row is ready
            try {
                var nameEl = document.getElementById('regFullName');
                if (nameEl && !nameEl.value) {
                    var nm = (typeof claimSailorName !== 'undefined' && claimSailorName) ? claimSailorName : '';
                    if (!nm && typeof currentProfile !== 'undefined' && currentProfile) {
                        nm = currentProfile.name || currentProfile.full_name || [currentProfile.first_name, currentProfile.surname].filter(Boolean).join(' ');
                    }
                    if (nm) nameEl.value = String(nm).trim();
                }
            } catch (ePref) {}
            refreshRegFieldStatuses();
        }

"""

must_replace(
    "        function validateRegistrationEmail() {",
    JS_HELPERS + "        function validateRegistrationEmail() {",
    "js helpers",
)

# Soften password: only length required for enable + visual strength optional
must_replace(
    """            const passwordValid = socialSignup ? true : (
                password.length >= 7 &&
                /[A-Z]/.test(password) &&
                /[#@!$%^&*()_+\\-=\\[\\]{};':"\\\\|,.<>\\/?]/.test(password) &&
                /[0-9]/.test(password) &&
                password === confirm
            );""",
    """            const passwordValid = socialSignup ? true : (
                password.length >= 7 &&
                password === confirm
            );""",
    "passwordValid easy",
)

# End of updateRegistrationSubmitButton — keep button enabled so user can tap and see issues
# Find the assign disabled line
must_replace(
    """            const submitBtn = document.getElementById('regSubmitBtn');
            if (submitBtn) {
                const wasDisabled = submitBtn.disabled;
                submitBtn.disabled = !allValid;""",
    """            const submitBtn = document.getElementById('regSubmitBtn');
            if (submitBtn) {
                const wasDisabled = submitBtn.disabled;
                // Always allow tap — incomplete fields show a fix-list and jump to the first issue
                submitBtn.disabled = false;
                submitBtn.setAttribute('data-all-valid', allValid ? '1' : '0');""",
    "submit always enabled",
)

# validateRegistrationEmail / password / match should refresh ticks
must_replace(
    """            if (errorDiv) {
                if (email.length > 0 && !isValid) {
                    errorDiv.style.display = 'block';
                    if (emailInput) {
                        emailInput.style.borderColor = '#dc3545';
                    }
                } else {
                    errorDiv.style.display = 'none';
                    if (emailInput) {
                        emailInput.style.borderColor = isValid && email.length > 0 ? '#28a745' : '#ddd';
                    }
                }""",
    """            if (errorDiv) {
                if (email.length > 0 && !isValid) {
                    errorDiv.style.display = 'block';
                } else {
                    errorDiv.style.display = 'none';
                }
                try { refreshRegFieldStatuses(); } catch (eTick) {}""",
    "email tick refresh",
)

must_replace(
    """            if (ruleLength) ruleLength.style.color = rules.length ? '#28a745' : '#999';
            if (ruleCapital) ruleCapital.style.color = rules.capital ? '#28a745' : '#999';""",
    """            if (ruleLength) {
                ruleLength.style.color = rules.length ? '#28a745' : '#999';
                ruleLength.textContent = (rules.length ? '✓' : '○') + ' At least 7 characters (needed)';
            }
            if (ruleCapital) {
                ruleCapital.style.color = rules.capital ? '#28a745' : '#999';
                ruleCapital.textContent = (rules.capital ? '✓' : '○') + ' Capital letter (nice to have)';
            }
            try { refreshRegFieldStatuses(); } catch (eTickP) {}
            // keep legacy special/number colour updates below
            if (false && ruleCapital) ruleCapital.style.color = rules.capital ? '#28a745' : '#999';""",
    "password tick refresh",
)

must_replace(
    """            if (password === confirm) {
                matchDiv.textContent = '✓ Passwords match';
                matchDiv.style.color = '#28a745';
            } else {
                matchDiv.textContent = '✗ Passwords do not match';
                matchDiv.style.color = '#dc3545';
            }
            
            updateRegistrationSubmitButton();""",
    """            if (password === confirm) {
                matchDiv.textContent = '✓ Passwords match';
                matchDiv.style.color = '#28a745';
            } else {
                matchDiv.textContent = '✗ Passwords do not match';
                matchDiv.style.color = '#dc2626';
            }
            try { refreshRegFieldStatuses(); } catch (eTickM) {}
            updateRegistrationSubmitButton();""",
    "confirm tick refresh",
)

must_replace(
    """            input.value = value;
            updateRegistrationSubmitButton();
        }
        
        function updateRegistrationSubmitButton() {""",
    """            input.value = value;
            try { refreshRegFieldStatuses(); } catch (eTickW) {}
            updateRegistrationSubmitButton();
        }
        
        function updateRegistrationSubmitButton() {""",
    "wa tick refresh",
)

# handleRegistrationData: replace early disabled check + password validation with collect issues
must_replace(
    """            // Double-check button state
            const submitBtn = document.getElementById('regSubmitBtn');
            if (submitBtn && submitBtn.disabled) {
                console.warn('[DEBUG] handleRegistrationData: Button is disabled, preventing submission');
                showError('Please complete all required fields correctly');
                return;
            }
            
            if (!currentProfile) {
                showError('No profile selected. Please try again.');
                return;
            }
            try {
                var _em = '';
                try { _em = (document.getElementById('emailInput') || document.getElementById('email') || {}).value || ''; } catch (eEm) {}
                trackClaimFunnel('submission_attempted', currentProfile.sas_id || claimSelectedSasId || '', true, '', {
                    email: String(_em || '').trim().slice(0, 120),
                    sailor_name: claimSailorName || '',
                    entry: claimEntry
                });
            } catch (e0) {}""",
    """            if (!currentProfile) {
                showError('No profile selected. Please try again.');
                return;
            }
            try { wireRegFormFieldFlow(); } catch (eWire) {}
            var _issuesEarly = collectRegFormIssues();
            if (_issuesEarly.length) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'form_incomplete', { count: _issuesEarly.length }); } catch (eIss) {}
                showRegIssuesAndFocus(_issuesEarly);
                return;
            }
            showRegIssuesAndFocus([]);
            try {
                var _em = '';
                try { _em = (document.getElementById('regEmail') || document.getElementById('emailInput') || document.getElementById('email') || {}).value || ''; } catch (eEm) {}
                trackClaimFunnel('submission_attempted', currentProfile.sas_id || claimSelectedSasId || '', true, '', {
                    email: String(_em || '').trim().slice(0, 120),
                    sailor_name: claimSailorName || '',
                    entry: claimEntry
                });
            } catch (e0) {}""",
    "submit issues gate",
)

must_replace(
    """            // Validate
            if (!socialSignup && (password.length < 7 || !/[A-Z]/.test(password) || !/[#@!$%^&*()_+\\-=\\[\\]{};':"\\\\|,.<>\\/?]/.test(password) || !/[0-9]/.test(password))) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'password_requirements', {}); } catch (e1) {}
                showError('Password does not meet requirements');
                return;
            }""",
    """            // Validate (easy rules — length + match; strength tips are optional)
            if (!socialSignup && password.length < 7) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'password_requirements', {}); } catch (e1) {}
                showRegIssuesAndFocus(collectRegFormIssues());
                return;
            }
            if (!socialSignup && password !== (document.getElementById('regPasswordConfirm')?.value || '')) {
                try { trackClaimFunnel('validation_error', currentProfile.sas_id || claimSelectedSasId || '', false, 'password_mismatch', {}); } catch (e1b) {}
                showRegIssuesAndFocus(collectRegFormIssues());
                return;
            }""",
    "password validate easy",
)

# Wire flow when registration form is shown — hook showRegistrationForm or similar
# Find showRegistrationData / display of regDataForm
for needle, label in [
    ("function showRegistrationForm()", "showRegistrationForm"),
    ("function showRegistrationData", "showRegistrationData"),
]:
    if needle in html:
        print("found", label, html.find(needle))

# Inject wire call after common show paths
if "function showRegistrationForm()" in html:
    # add wire at start of function body if we can find a unique snippet
    idx = html.find("function showRegistrationForm()")
    brace = html.find("{", idx)
    if brace > 0 and "wireRegFormFieldFlow" not in html[brace : brace + 80]:
        html = html[: brace + 1] + "\n            try { setTimeout(wireRegFormFieldFlow, 50); } catch (eFlow) {}\n" + html[brace + 1 :]
        print("ok wire showRegistrationForm")

# Also wire on DOMContentLoaded near end of existing listener if present
if "wireRegFormFieldFlow" not in html[html.find("DOMContentLoaded") : html.find("DOMContentLoaded") + 800]:
    html = html.replace(
        "document.addEventListener('DOMContentLoaded'",
        "document.addEventListener('DOMContentLoaded', function(){ try { setTimeout(wireRegFormFieldFlow, 100); } catch(e) {} });\n        document.addEventListener('DOMContentLoaded'",
        1,
    )
    print("ok wire DOMContentLoaded")

SIGNUP.write_text(html, encoding="utf-8")
print("WROTE", SIGNUP, "bytes", len(html))
# sanity
for token in [
    "reg-tick",
    "autocomplete=\"email\"",
    "autocomplete=\"tel\"",
    "collectRegFormIssues",
    "wireRegFormFieldFlow",
    "novalidate",
    "regFullName",
]:
    assert token in html, token
print("SANITY_OK")
