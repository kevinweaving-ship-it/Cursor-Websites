#!/usr/bin/env python3
"""Compact layman welcome splash — Google/Facebook stand out, less clutter."""
from pathlib import Path
import shutil
import time

SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(SIGNUP, Path(f"/root/backups/signup_splash_compact_{ts}.html"))
print("BACKUP", ts)
html = SIGNUP.read_text(encoding="utf-8", errors="replace")

CSS = """
            /* Compact welcome splash */
            .signup-splash-card {
                padding-bottom: 0.75rem !important;
            }
            .signup-splash-kicker {
                font-size: 1.65rem !important;
                margin-bottom: 0.35rem !important;
            }
            .signup-splash-subbar {
                font-size: 1rem !important;
                padding: 8px 12px !important;
                margin-bottom: 10px !important;
            }
            .signup-splash-copy {
                margin: 0 0 12px !important;
                font-size: 1.05rem !important;
                font-weight: 900 !important;
                color: #fef08a !important;
                text-align: center;
                line-height: 1.25;
            }
            .signup-splash-actions {
                gap: 10px !important;
            }
            .signup-splash-button {
                min-height: 62px !important;
                font-size: 15px !important;
                border: 3px solid rgba(0,0,0,0.15);
            }
            .signup-splash-button--google {
                border-color: #ca8a04 !important;
                box-shadow: 0 6px 0 #ca8a04, 0 10px 24px rgba(0,0,0,0.25) !important;
            }
            .signup-splash-button--facebook {
                border-color: #0b4fbf !important;
                box-shadow: 0 6px 0 #0b4fbf, 0 10px 24px rgba(0,0,0,0.25) !important;
            }
            .signup-splash-button-label {
                text-transform: none !important;
                font-size: 1.02rem !important;
            }
            .signup-splash-button--email-lite {
                min-height: 46px !important;
                background: transparent !important;
                color: rgba(255,255,255,0.95) !important;
                border: 2px solid rgba(255,255,255,0.55) !important;
                box-shadow: none !important;
                font-size: 0.92rem !important;
                font-weight: 700 !important;
            }
            .signup-splash-button--email-lite .signup-splash-button-arrow {
                display: none !important;
            }
            .signup-splash-button--email-lite svg {
                width: 22px !important;
                height: 22px !important;
            }
            .signup-splash-separator {
                margin: 2px 0 !important;
                font-size: 0.85rem !important;
                color: rgba(255,255,255,0.75) !important;
                font-weight: 700 !important;
            }
            .signup-splash-separator::before,
            .signup-splash-separator::after {
                background: rgba(255,255,255,0.35) !important;
                height: 1px !important;
            }
            .signup-splash-footer {
                display: none !important;
            }
            .signup-splash-apple-hidden {
                display: none !important;
            }
"""

if "signup-splash-button--email-lite" not in html:
    html = html.replace("    </style>", CSS + "    </style>", 1)
    print("ok css")

OLD_BLOCK = """                    <div class="signup-splash-subbar">Let's Create Your Account</div>
                    <p class="signup-splash-copy">Easiest: <b>Google</b> or <b>Facebook</b> (about 30 seconds each). Or use the email form below.</p>
                    <div class="signup-splash-actions">
                        <button type="button" class="signup-splash-button signup-splash-button--google" onclick="loginWithGoogle()">
                            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            <span class="signup-splash-button-label">Continue with Google</span>
                            <span class="signup-splash-button-arrow" aria-hidden="true">›</span>
                        </button>
                        <button type="button" class="signup-splash-button signup-splash-button--facebook" onclick="loginWithFacebook()">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <circle cx="12" cy="12" r="12" fill="white"/>
                                <path d="M13.44 20V13.44H15.64L15.97 10.88H13.44V9.24C13.44 8.5 13.64 8 14.7 8H16V5.72C15.37 5.63 14.74 5.59 14.1 5.6C12.21 5.6 10.92 6.75 10.92 8.86V10.88H8.8V13.44H10.92V20H13.44Z" fill="#0F39C9"/>
                            </svg>
                            <span class="signup-splash-button-label">Continue with Facebook</span>
                            <span class="signup-splash-button-arrow" aria-hidden="true">›</span>
                        </button>
                        <button type="button" class="signup-splash-button signup-splash-button--apple signup-splash-button--disabled" disabled aria-disabled="true">
                            <svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <path d="M16.86 12.36C16.89 15.35 19.48 16.35 19.51 16.36C19.49 16.43 19.11 17.73 18.18 19.09C17.37 20.27 16.53 21.45 15.2 21.47C13.89 21.49 13.47 20.69 11.98 20.69C10.49 20.69 10.03 21.45 8.79 21.49C7.5 21.54 6.52 20.2 5.7 19.03C4.03 16.61 2.74 12.19 4.45 9.22C5.3 7.74 6.82 6.8 8.47 6.78C9.73 6.76 10.92 7.63 11.69 7.63C12.46 7.63 13.92 6.59 15.43 6.74C16.06 6.77 17.84 6.99 18.98 8.66C18.89 8.72 16.84 9.91 16.86 12.36ZM14.43 5.17C15.1 4.36 15.55 3.23 15.43 2.11C14.46 2.15 13.29 2.76 12.59 3.57C11.97 4.29 11.42 5.44 11.56 6.54C12.64 6.62 13.76 5.98 14.43 5.17Z"/>
                            </svg>
                            <span class="signup-splash-button-label">Apple Coming Soon</span>
                            <span class="signup-splash-button-arrow" aria-hidden="true">›</span>
                        </button>
                        <div class="signup-splash-separator">Or</div>
                        <button type="button" class="signup-splash-button signup-splash-button--email" onclick="showRegistrationForm(event)">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <path d="M4 6.5H20C20.83 6.5 21.5 7.17 21.5 8V16C21.5 16.83 20.83 17.5 20 17.5H4C3.17 17.5 2.5 16.83 2.5 16V8C2.5 7.17 3.17 6.5 4 6.5Z" stroke="#091427" stroke-width="1.8"/>
                                <path d="M3 8L12 14L21 8" stroke="#091427" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                            <span class="signup-splash-button-label">Sign Up With Email</span>
                            <span class="signup-splash-button-arrow" aria-hidden="true">›</span>
                        </button>
                    </div>
                    <div class="signup-splash-footer">Free. Fastest with <strong>Google</strong>.</div>"""

NEW_BLOCK = """                    <div class="signup-splash-subbar">Free sign-up · 30 seconds</div>
                    <p class="signup-splash-copy">Tap Google or Facebook ↓</p>
                    <div class="signup-splash-actions">
                        <button type="button" class="signup-splash-button signup-splash-button--google" onclick="loginWithGoogle()">
                            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            <span class="signup-splash-button-label">Google — sign up</span>
                            <span class="signup-splash-button-arrow" aria-hidden="true">›</span>
                        </button>
                        <button type="button" class="signup-splash-button signup-splash-button--facebook" onclick="loginWithFacebook()">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <circle cx="12" cy="12" r="12" fill="white"/>
                                <path d="M13.44 20V13.44H15.64L15.97 10.88H13.44V9.24C13.44 8.5 13.64 8 14.7 8H16V5.72C15.37 5.63 14.74 5.59 14.1 5.6C12.21 5.6 10.92 6.75 10.92 8.86V10.88H8.8V13.44H10.92V20H13.44Z" fill="#0F39C9"/>
                            </svg>
                            <span class="signup-splash-button-label">Facebook — sign up</span>
                            <span class="signup-splash-button-arrow" aria-hidden="true">›</span>
                        </button>
                        <div class="signup-splash-separator">or</div>
                        <button type="button" class="signup-splash-button signup-splash-button--email-lite" onclick="showRegistrationForm(event)">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                <path d="M4 6.5H20C20.83 6.5 21.5 7.17 21.5 8V16C21.5 16.83 20.83 17.5 20 17.5H4C3.17 17.5 2.5 16.83 2.5 16V8C2.5 7.17 3.17 6.5 4 6.5Z" stroke="currentColor" stroke-width="1.8"/>
                                <path d="M3 8L12 14L21 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                            <span class="signup-splash-button-label">Use email instead</span>
                        </button>
                    </div>"""

if OLD_BLOCK not in html:
    raise SystemExit("missing splash block")
html = html.replace(OLD_BLOCK, NEW_BLOCK, 1)
print("ok splash html")

# Top duplicate line — shorten
html = html.replace(
    "Create your SailingSA account here",
    "Join SailingSA",
    1,
)

SIGNUP.write_text(html, encoding="utf-8")
for t in ["Tap Google or Facebook", "Google — sign up", "Facebook — sign up", "Use email instead", "30 seconds"]:
    assert t in html, t
assert "Apple Coming Soon" not in html.split("signup-splash-actions")[1].split("registrationForm")[0]
print("WROTE", len(html))
