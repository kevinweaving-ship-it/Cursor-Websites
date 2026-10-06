#!/usr/bin/env python3
"""Set the kevin@gowifi.co.za Openserve UPP password.

Reads the current temp password and the new password from the environment
or /root/secrets/openserve-upp.env. Does not print secrets.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

USER = os.environ.get("OPENSERVE_UPP_GOWIFI_USER", "kevin@gowifi.co.za")
OLD_PASS = os.environ.get("OPENSERVE_UPP_TEMP_PASS", "")
NEW_PASS = os.environ.get("OPENSERVE_UPP_NEW_PASS", "")
ENV_PATH = Path("/root/secrets/openserve-upp.env")
TOKEN_PATH = Path(os.environ.get("UPP_TOKEN_FILE", "/root/secrets/upp.token"))

TENANT = "efb1320a-d627-4304-b0ca-2e84b7039c2e"
CLIENT_ID = "b9f77276-e613-4e3a-b944-2fbcd2e94579"
POLICY = "b2c_1_signin1_upp"
REDIRECT = "https://partners.openserve.co.za"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key] = val
    return env


def settings(html: str) -> dict:
    match = re.search(r"var SETTINGS\s*=\s*(\{.*?\})\s*;", html, re.S)
    if not match:
        raise SystemExit("B2C SETTINGS not found")
    return json.loads(match.group(1))


def field_ids(html: str) -> list[str]:
    match = re.search(r"var SA_FIELDS\s*=\s*(\{.*?\})\s*;", html, re.S)
    if not match:
        return []
    data = json.loads(match.group(1))
    return [f.get("ID") for f in data.get("AttributeFields") or [] if f.get("ID")]


def extract_token(url: str, html: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if parsed.fragment:
        qs.update(parse_qs(parsed.fragment))
    for key in ("id_token", "access_token"):
        if qs.get(key):
            return qs[key][0]
    soup = BeautifulSoup(html, "html.parser")
    for inp in soup.find_all("input"):
        if inp.get("name") in ("id_token", "access_token") and inp.get("value"):
            return inp.get("value")
    return None


def self_asserted(s: requests.Session, html: str, payload: dict) -> requests.Response:
    cfg = settings(html)
    origin = "https://openserveapp.b2clogin.com"
    url = f"{origin}{cfg['hosts']['tenant']}/SelfAsserted?tx={cfg['transId']}&p={cfg['hosts']['policy']}"
    body = {"request_type": "RESPONSE", **payload}
    print("self_asserted_fields", sorted(payload), flush=True)
    time.sleep(0.8)
    return s.post(
        url,
        data=body,
        headers={
            "X-CSRF-TOKEN": cfg["csrf"],
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": origin,
        },
        timeout=35,
    )


def confirmed(s: requests.Session, html: str) -> requests.Response:
    cfg = settings(html)
    origin = "https://openserveapp.b2clogin.com"
    api_name = cfg.get("api") or "CombinedSigninAndSignup"
    url = (
        f"{origin}{cfg['hosts']['tenant']}/api/{api_name}/confirmed"
        f"?rememberMe=false&csrf_token={cfg['csrf']}&tx={cfg['transId']}&p={cfg['hosts']['policy']}"
    )
    time.sleep(0.6)
    return s.get(url, timeout=35, allow_redirects=True)


def authorize(s: requests.Session, policy: str = POLICY) -> requests.Response:
    nonce = str(uuid.uuid4())
    url = (
        f"https://openserveapp.b2clogin.com/{TENANT}/{policy}/oauth2/v2.0/authorize"
        f"?client_id={CLIENT_ID}&response_type=id_token&redirect_uri={REDIRECT}"
        f"&response_mode=fragment&scope=openid%20profile%20offline_access"
        f"&state=gowifi-pw&nonce={nonce}"
    )
    print("GET authorize", policy, flush=True)
    return s.get(url, timeout=30, allow_redirects=True)


def save_gowifi_secret(password: str) -> None:
    env = load_env()
    env["OPENSERVE_UPP_GOWIFI_USER"] = USER
    env["OPENSERVE_UPP_GOWIFI_PASS"] = password
    lines = [f"{k}={v}" for k, v in env.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n")
    ENV_PATH.chmod(0o600)
    print("updated env keys", sorted(env), flush=True)


def login_with(s: requests.Session, password: str) -> tuple[str | None, str]:
    r = authorize(s)
    print("authorize", r.status_code, "bytes", len(r.text), "ids", field_ids(r.text), flush=True)
    Path("/tmp/upp_pw_auth.html").write_text(r.text)
    if "SETTINGS" not in r.text:
        tok = extract_token(r.url, r.text)
        return tok, r.text
    post = self_asserted(s, r.text, {"email": USER, "password": password})
    print("login_status", post.status_code, post.text[:220].replace("\n", " "), flush=True)
    if post.status_code >= 400:
        return None, post.text
    try:
        body = post.json()
    except Exception:
        body = {}
    if str(body.get("status")) not in ("200", "success") and body.get("error"):
        return None, post.text
    r2 = confirmed(s, r.text)
    print("confirmed", r2.status_code, r2.url[:180], "ids", field_ids(r2.text), flush=True)
    Path("/tmp/upp_pw_after.html").write_text(r2.text)
    tok = extract_token(r2.url, r2.text)
    return tok, r2.text


def change_if_prompted(s: requests.Session, html: str, old: str, new: str) -> str | None:
    ids = field_ids(html)
    print("prompt_fields", ids, flush=True)
    if not ids:
        return extract_token("", html)
    payload = {}
    for field in ids:
        low = field.lower()
        if low in ("email", "signinname", "username"):
            payload[field] = USER
        elif low in ("newpassword",) or low.startswith("new"):
            payload[field] = new
        elif "reenter" in low or "confirm" in low or "repeat" in low:
            payload[field] = new
        elif low in ("password", "oldpassword", "currentpassword") or "old" in low or "current" in low:
            payload[field] = old
    if not payload:
        return None
    post = self_asserted(s, html, payload)
    print("change_status", post.status_code, post.text[:220].replace("\n", " "), flush=True)
    if post.status_code >= 400:
        return None
    r2 = confirmed(s, html)
    print("change_confirmed", r2.status_code, r2.url[:180], "ids", field_ids(r2.text), flush=True)
    Path("/tmp/upp_pw_changed.html").write_text(r2.text)
    if field_ids(r2.text) and extract_token(r2.url, r2.text) is None:
        return change_if_prompted(s, r2.text, old, new)
    return extract_token(r2.url, r2.text)


def main() -> int:
    env = load_env()
    old = OLD_PASS or env.get("OPENSERVE_UPP_TEMP_PASS") or env.get("OPENSERVE_UPP_GOWIFI_PASS") or ""
    new = NEW_PASS or env.get("OPENSERVE_UPP_NEW_PASS") or ""
    if not old or not new:
        print("missing OPENSERVE_UPP_TEMP_PASS or OPENSERVE_UPP_NEW_PASS", flush=True)
        return 2
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-ZA,en;q=0.9",
        }
    )
    tok, html = login_with(s, old)
    if tok is None and field_ids(html):
        tok = change_if_prompted(s, html, old, new)
    if tok is None:
        print("TEMP_LOGIN_FAILED", flush=True)
        return 1
    print("temp_login_ok", flush=True)
    # If login succeeded without a change prompt, try the same sign-in page again
    # after posting new password fields if the HTML still has them.
    if field_ids(html):
        changed = change_if_prompted(s, html, old, new)
        if changed:
            tok = changed
            print("password_changed_during_login", flush=True)
    # Verify new password in a fresh session.
    s2 = requests.Session()
    s2.headers.update(s.headers)
    tok2, html2 = login_with(s2, new)
    if tok2 is None and field_ids(html2):
        tok2 = change_if_prompted(s2, html2, old, new)
    if tok2:
        print("NEW_PASSWORD_LOGIN_OK", flush=True)
        save_gowifi_secret(new)
        return 0
    # New password not accepted yet — try password-change policies.
    for policy in (
        "b2c_1_passwordchange",
        "B2C_1_PasswordChange",
        "b2c_1_passwordreset",
        "B2C_1_PasswordReset",
    ):
        r = authorize(s, policy)
        print("try_policy", policy, r.status_code, r.url[:120], "ids", field_ids(r.text), flush=True)
        if r.status_code >= 400 or "SETTINGS" not in r.text:
            continue
        tok3 = change_if_prompted(s, r.text, old, new)
        if tok3:
            s3 = requests.Session()
            s3.headers.update(s.headers)
            tok4, _ = login_with(s3, new)
            if tok4:
                print("NEW_PASSWORD_LOGIN_OK", policy, flush=True)
                save_gowifi_secret(new)
                return 0
    print("NEW_PASSWORD_LOGIN_FAILED", flush=True)
    return 3


if __name__ == "__main__":
    sys.exit(main())
