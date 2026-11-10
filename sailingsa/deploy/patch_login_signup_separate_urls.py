#!/usr/bin/env python3
"""Separate sign-up (/signup.html) from sign-in (/login.html) — distinct URLs and cross-links."""
from pathlib import Path
import shutil
import time

LOGIN = Path("/var/www/sailingsa/login.html")
SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
for p in (LOGIN, SIGNUP):
    if p.exists():
        shutil.copy2(p, Path(f"/root/backups/{p.name}.separate_urls_{ts}"))
        print("BACKUP", p.name, ts)

CSS = """
            /* Sign-in / sign-up page switch links */
            .auth-page-switch {
                text-align: center;
                margin-top: 1rem;
                padding-top: 0.75rem;
                border-top: 1px solid rgba(0,0,0,0.08);
                font-size: 0.95rem;
                color: #64748b;
            }
            .auth-page-switch a {
                color: #1a365d;
                font-weight: 700;
                margin-left: 0.35rem;
                text-decoration: none;
            }
            .auth-page-switch a:hover {
                text-decoration: underline;
            }
            .signup-splash-card .auth-page-switch {
                border-top-color: rgba(255,255,255,0.25);
                color: rgba(255,255,255,0.85);
            }
            .signup-splash-card .auth-page-switch a {
                color: #fef08a;
            }
"""

LOGIN_SWITCH_HTML = """
                        <div class="auth-page-switch">
                            <span>New here?</span>
                            <a href="/signup.html" id="goToSignupLink" onclick="goToSignup(event)">Sign up</a>
                        </div>"""

SIGNUP_SWITCH_HTML = """
                    <div class="auth-page-switch">
                        <span>Already registered?</span>
                        <a href="/login.html" id="goToLoginLink" onclick="goToLogin(event)">Sign in</a>
                    </div>"""

SIGNUP_REG_SWITCH = """
                    <div class="auth-page-switch" style="margin-top:0.75rem;border-top:none;padding-top:0;">
                        <span>Already registered?</span>
                        <a href="/login.html" onclick="goToLogin(event)">Sign in</a>
                    </div>"""

LOGIN_HELPERS = """
        function buildSignupUrl(extra) {
            var u = new URL((window.location.origin || '') + '/signup.html');
            var returnTo = getAuthReturnToValue();
            if (returnTo) u.searchParams.set('returnTo', returnTo);
            extra = extra || {};
            Object.keys(extra).forEach(function(k) {
                if (extra[k]) u.searchParams.set(k, extra[k]);
            });
            return u.toString();
        }

        function goToSignup(e) {
            if (e) e.preventDefault();
            window.location.href = buildSignupUrl({});
        }
        window.goToSignup = goToSignup;
"""

SIGNUP_HELPERS = """
        function buildLoginUrl() {
            var u = new URL((window.location.origin || '') + '/login.html');
            var returnTo = getAuthReturnToValue();
            if (returnTo) u.searchParams.set('returnTo', returnTo);
            return u.toString();
        }

        function goToLogin(e) {
            if (e) e.preventDefault();
            window.location.href = buildLoginUrl();
        }
        window.goToLogin = goToLogin;
"""

LOGIN_DOM_REDIRECT = """
                if (params.get('signup') || params.get('register') || params.get('sas_id') || params.get('sasId') || params.get('sas')) {
                    var signupTarget = buildSignupUrl({
                        sas_id: params.get('sas_id') || params.get('sasId') || params.get('sas') || '',
                        name: params.get('name') || '',
                        returnTo: params.get('returnTo') || ''
                    });
                    window.location.replace(signupTarget);
                    return;
                }
"""

OLD_LOGIN_SHOW_REG = """        function showRegistrationForm(e) {
            if (e) e.preventDefault();
            showSection('registrationForm');
        }"""

NEW_LOGIN_SHOW_REG = """        function showRegistrationForm(e) {
            if (e) e.preventDefault();
            goToSignup(e);
        }"""

OLD_LOGIN_REDIRECT = """        function redirectToLogin() {
            window.location.href = (window.location.origin || '') + '/login.html';
        }"""

NEW_SIGNUP_REDIRECT = """        function redirectToLogin() {
            window.location.href = buildLoginUrl();
        }"""


def patch_login(html: str) -> str:
    if "auth-page-switch" not in html:
        html = html.replace("    </style>", CSS + "    </style>", 1)
        print("login: ok css")

    anchor = '<div class="login-art-forgot">\n                            <a href="#" onclick="handleForgotPassword(event)">Forgot Password?</a>\n                        </div>'
    if anchor in html and "goToSignupLink" not in html:
        html = html.replace(anchor, anchor + LOGIN_SWITCH_HTML, 1)
        print("login: ok switch link")

    if "function buildSignupUrl" not in html:
        html = html.replace("        function getAuthReturnToValue() {", LOGIN_HELPERS + "\n        function getAuthReturnToValue() {", 1)
        print("login: ok helpers")

    if OLD_LOGIN_SHOW_REG in html:
        html = html.replace(OLD_LOGIN_SHOW_REG, NEW_LOGIN_SHOW_REG, 1)
        print("login: ok showRegistrationForm redirect")

    if "params.get('signup')" not in html:
        needle = "                if (urlReturnTo) sessionStorage.setItem('auth_returnTo', urlReturnTo);"
        if needle in html:
            html = html.replace(needle, needle + LOGIN_DOM_REDIRECT, 1)
            print("login: ok dom redirect")

    # Clearer sign-in labels (distinct from signup page)
    html = html.replace("<span>Continue with Google</span>", "<span>Sign in with Google</span>", 1)
    html = html.replace("<span>Continue with Facebook</span>", "<span>Sign in with Facebook</span>", 1)
    print("login: ok social labels")
    return html


def patch_signup(html: str) -> str:
    if "auth-page-switch" not in html:
        html = html.replace("    </style>", CSS + "    </style>", 1)
        print("signup: ok css")

    splash_end = """                        </button>
                    </div>
                </div>
            </div>

            <!-- Registration: Find Profile -->"""
    if splash_end in html and "goToLoginLink" not in html:
        html = html.replace(
            splash_end,
            """                        </button>""" + SIGNUP_SWITCH_HTML + """
                    </div>
                </div>
            </div>

            <!-- Registration: Find Profile -->""",
            1,
        )
        print("signup: ok splash switch")

    reg_anchor = """                    <div class="login-art-forgot">
                        <a href="#" onclick="goBackToReturnUrl(); return false;">Home</a>
                    </div>"""
    if reg_anchor in html and SIGNUP_REG_SWITCH.strip() not in html:
        html = html.replace(reg_anchor, reg_anchor + SIGNUP_REG_SWITCH, 1)
        print("signup: ok reg form switch")

    if "function buildLoginUrl" not in html:
        html = html.replace("        function getAuthReturnToValue() {", SIGNUP_HELPERS + "\n        function getAuthReturnToValue() {", 1)
        print("signup: ok helpers")

    if OLD_LOGIN_REDIRECT in html:
        html = html.replace(OLD_LOGIN_REDIRECT, NEW_SIGNUP_REDIRECT, 1)
        print("signup: ok redirectToLogin")

    return html


if LOGIN.exists():
    login_html = patch_login(LOGIN.read_text(encoding="utf-8", errors="replace"))
    LOGIN.write_text(login_html, encoding="utf-8")
    print("WROTE", LOGIN)
else:
    print("SKIP missing", LOGIN)

if SIGNUP.exists():
    signup_html = patch_signup(SIGNUP.read_text(encoding="utf-8", errors="replace"))
    SIGNUP.write_text(signup_html, encoding="utf-8")
    print("WROTE", SIGNUP)
else:
    print("SKIP missing", SIGNUP)

print("DONE separate login/signup URLs")
