#!/usr/bin/env python3
"""Loud Google + Facebook on registration form and confirm screen."""
from pathlib import Path
import shutil
import time

SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(SIGNUP, Path(f"/root/backups/signup_social_loud_{ts}.html"))
print("BACKUP", ts)
html = SIGNUP.read_text(encoding="utf-8", errors="replace")

GOOGLE_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>'
FB_SVG = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="12" r="12" fill="white"/><path d="M13.44 20V13.44H15.64L15.97 10.88H13.44V9.24C13.44 8.5 13.64 8 14.7 8H16V5.72C15.37 5.63 14.74 5.59 14.1 5.6C12.21 5.6 10.92 6.75 10.92 8.86V10.88H8.8V13.44H10.92V20H13.44Z" fill="#1877F2"/></svg>'

CSS = """
            /* Loud social sign-up — Google + Facebook */
            .reg-social-loud {
                margin: 0 0 1.15rem;
                padding: 1.05rem 1rem 1.1rem;
                background: linear-gradient(160deg, #fef08a 0%, #fde68a 40%, #bfdbfe 100%);
                border: 4px solid #ca8a04;
                border-radius: 14px;
                box-shadow: 0 8px 22px rgba(202, 138, 4, 0.42);
            }
            .reg-social-loud-title {
                margin: 0 0 0.35rem;
                font-size: 1.15rem;
                font-weight: 900;
                color: #713f12;
                text-align: center;
                letter-spacing: 0.03em;
                text-transform: uppercase;
            }
            .reg-social-loud-sub {
                margin: 0 0 0.85rem;
                font-size: 0.92rem;
                font-weight: 700;
                color: #1e3a8a;
                text-align: center;
                line-height: 1.35;
            }
            .reg-social-loud-stack {
                display: flex;
                flex-direction: column;
                gap: 0.65rem;
            }
            .reg-social-loud-btn {
                display: flex;
                width: 100%;
                align-items: center;
                justify-content: center;
                gap: 0.7rem;
                padding: 1.05rem 1.15rem;
                font-size: 1.14rem;
                font-weight: 900;
                line-height: 1.2;
                border-radius: 11px;
                cursor: pointer;
                border: 3px solid #1f2937;
                box-shadow: 0 4px 0 #1f2937;
            }
            .reg-social-loud-btn:active {
                transform: translateY(2px);
                box-shadow: 0 2px 0 #1f2937;
            }
            .reg-social-loud-btn svg {
                width: 1.45rem;
                height: 1.45rem;
                flex-shrink: 0;
            }
            .reg-social-loud-btn--google {
                background: #fff;
                color: #111827;
            }
            .reg-social-loud-btn--facebook {
                background: #1877F2;
                color: #fff;
                border-color: #0b4fbf;
                box-shadow: 0 4px 0 #0b4fbf;
            }
            .reg-social-loud-btn--facebook:active {
                box-shadow: 0 2px 0 #0b4fbf;
            }
            .confirm-social-loud {
                display: flex;
                flex-direction: column;
                gap: 0.55rem;
                margin-bottom: 0.75rem;
                width: 100%;
            }
            .confirm-social-loud .reg-social-loud-btn {
                font-size: 1.05rem;
                padding: 0.95rem 1rem;
            }
"""

if ".reg-social-loud" not in html:
    if "    </style>" not in html:
        raise SystemExit("missing style")
    html = html.replace("    </style>", CSS + "    </style>", 1)
    print("ok css")

OLD_LOUD = """                <div class="reg-google-loud" id="regGoogleLoud">
                    <p class="reg-google-loud-title">⚡ FASTEST WAY — USE GOOGLE</p>
                    <p class="reg-google-loud-sub">About 30 seconds. No password to remember.</p>
                    <button type="button" class="reg-google-loud-btn" onclick="loginWithGoogle()">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                        Continue with Google
                    </button>
                </div>
                <p style="margin:0 0 0.65rem;text-align:center;font-size:0.85rem;font-weight:700;color:#64748b;">— or fill in the form below —</p>"""

NEW_LOUD = f"""                <div class="reg-social-loud" id="regSocialLoud">
                    <p class="reg-social-loud-title">⚡ Easiest — Google or Facebook</p>
                    <p class="reg-social-loud-sub">About 30 seconds · no password to remember · tap one:</p>
                    <div class="reg-social-loud-stack">
                        <button type="button" class="reg-social-loud-btn reg-social-loud-btn--google" onclick="loginWithGoogle()">
                            {GOOGLE_SVG}
                            Continue with Google
                        </button>
                        <button type="button" class="reg-social-loud-btn reg-social-loud-btn--facebook" onclick="loginWithFacebook()">
                            {FB_SVG}
                            Continue with Facebook
                        </button>
                    </div>
                </div>
                <p style="margin:0 0 0.65rem;text-align:center;font-size:0.85rem;font-weight:700;color:#64748b;">— or fill in the email form below —</p>"""

if OLD_LOUD not in html:
    raise SystemExit("missing reg google loud block")
html = html.replace(OLD_LOUD, NEW_LOUD, 1)
print("ok reg form social")

OLD_CONFIRM = """                    <div class="btn-group" id="profileConfirmButtons">
                        <button type="button" class="btn-login btn-google confirm-google-loud" onclick="loginWithGoogle()">⚡ Continue with Google — fastest (30 sec)</button>
                        <button class="btn-login btn-primary" onclick="handleProfileConfirm('me', currentProfile?.sas_id || '')">This is me — use email</button>"""

NEW_CONFIRM = f"""                    <div class="confirm-social-loud" id="confirmSocialLoud">
                        <button type="button" class="reg-social-loud-btn reg-social-loud-btn--google" onclick="loginWithGoogle()">
                            {GOOGLE_SVG}
                            Continue with Google — fastest
                        </button>
                        <button type="button" class="reg-social-loud-btn reg-social-loud-btn--facebook" onclick="loginWithFacebook()">
                            {FB_SVG}
                            Continue with Facebook — easy
                        </button>
                    </div>
                    <div class="btn-group" id="profileConfirmButtons">
                        <button class="btn-login btn-primary" onclick="handleProfileConfirm('me', currentProfile?.sas_id || '')">This is me — use email form</button>"""

if OLD_CONFIRM not in html:
    raise SystemExit("missing confirm buttons")
html = html.replace(OLD_CONFIRM, NEW_CONFIRM, 1)
print("ok confirm social")

# Splash copy — mention both equally
html = html.replace(
    "Easiest: <b>Continue with Google</b> (about 30 seconds). Email works too. Facebook available. Apple soon.",
    "Easiest: <b>Google</b> or <b>Facebook</b> (about 30 seconds each). Or use the email form below.",
    1,
)

SIGNUP.write_text(html, encoding="utf-8")
for t in ["reg-social-loud", "Continue with Facebook", "reg-social-loud-btn--facebook", "confirm-social-loud"]:
    assert t in html, t
print("WROTE", len(html))
