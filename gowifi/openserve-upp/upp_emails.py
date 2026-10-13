#!/usr/bin/env python3
"""Replace obsolete @go-wifi.co.za contact emails on Openserve UPP org 955.

Does not place orders or change services. Secrets stay in /root/secrets.
Correct mailbox: accounts@gowifi.co.za (Kevin + openserve@gowifi.co.za).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = os.environ.get(
    "OPENSERVE_UPP_API",
    "https://partners.openserve.co.za/api/end-points/upp-service-api",
)
ORG_ID = int(os.environ.get("OPENSERVE_ORG_ID", "955"))
TOKEN_PATH = Path(os.environ.get("UPP_TOKEN_FILE", "/root/secrets/upp.token"))
ENV_PATH = Path("/root/secrets/openserve-upp.env")

# Live gowifi addresses. go-wifi is obsolete and has no public MX.
ORG_EMAIL = "accounts@gowifi.co.za"
USER_EMAIL = "kevin@gowifi.co.za"
KEEP_ICLOUD = "kevinweaving@icloud.com"
OBSOLETE = "go-wifi.co.za"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
TENANT = "efb1320a-d627-4304-b0ca-2e84b7039c2e"
CLIENT_ID = "b9f77276-e613-4e3a-b944-2fbcd2e94579"
POLICY = "b2c_1_signin1_upp"
REDIRECT = "https://partners.openserve.co.za"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            env[key] = val
    return env


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-ZA,en-GB;q=0.9,en;q=0.8",
        }
    )
    return s


def authorize_url(response_type: str, nonce: str) -> str:
    mode = "fragment" if "id_token" in response_type else "query"
    return (
        f"https://openserveapp.b2clogin.com/{TENANT}/{POLICY}/oauth2/v2.0/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type={response_type}"
        f"&redirect_uri={REDIRECT}"
        f"&response_mode={mode}"
        f"&scope=openid%20profile%20offline_access"
        f"&state=gowifi-email-fix"
        f"&nonce={nonce}"
    )


def fill_login(form, user: str, password: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        typ = (inp.get("type") or "text").lower()
        val = inp.get("value") or ""
        if typ == "password" or "password" in name.lower():
            payload[name] = password
        elif typ == "email" or re.search(r"email|username|signinname", name, re.I):
            payload[name] = user
        elif typ == "submit":
            payload[name] = val or "Sign in"
        else:
            payload[name] = val
    for key in list(payload):
        if payload[key] == "" and re.search(r"email|username|signinname", key, re.I):
            payload[key] = user
    return payload


def extract_token(url: str, html: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if parsed.fragment:
        qs.update(parse_qs(parsed.fragment))
    for key in ("id_token", "access_token"):
        if qs.get(key):
            return qs[key][0]
    code = (qs.get("code") or [None])[0]
    if code:
        token = exchange_code(code)
        if token:
            return token
    m = re.search(r'id_token=([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)', html)
    if m:
        return m.group(1)
    return None


def exchange_code(code: str) -> str | None:
    token_url = (
        f"https://openserveapp.b2clogin.com/{TENANT}/{POLICY}/oauth2/v2.0/token"
    )
    for extra in (
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT,
        },
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT,
            "scope": "openid profile offline_access",
        },
    ):
        r = requests.post(token_url, data=extra, timeout=30, headers={"User-Agent": UA})
        print(f"token_exchange {r.status_code} {r.text[:180].replace(chr(10), ' ')}", flush=True)
        if r.status_code < 400:
            body = r.json()
            return body.get("id_token") or body.get("access_token")
    return None


def _settings(html: str) -> dict:
    match = re.search(r"var SETTINGS\s*=\s*(\{.*?\})\s*;", html, re.S)
    if not match:
        raise SystemExit("B2C SETTINGS not found")
    return json.loads(match.group(1))


def b2c_self_asserted(s: requests.Session, authorize_html: str, user: str, password: str) -> str | None:
    settings = _settings(authorize_html)
    csrf = settings["csrf"]
    tx = settings["transId"]
    policy = settings["hosts"]["policy"]
    tenant = settings["hosts"]["tenant"]
    api_name = settings.get("api") or "CombinedSigninAndSignup"
    origin = "https://openserveapp.b2clogin.com"
    self_url = f"{origin}{tenant}/SelfAsserted?tx={tx}&p={policy}"
    time.sleep(1.0)
    r = s.post(
        self_url,
        data={
            "request_type": "RESPONSE",
            "email": user,
            "password": password,
        },
        headers={
            "X-CSRF-TOKEN": csrf,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": origin,
        },
        timeout=35,
    )
    print(f"self_asserted {r.status_code} {r.text[:220].replace(chr(10), ' ')}", flush=True)
    if r.status_code >= 400:
        return None
    try:
        body = r.json()
    except Exception:
        body = {}
    if body.get("status") not in (None, "200", 200, "success") and body.get("error"):
        print("self_asserted_error", body, flush=True)
        return None
    confirmed = (
        f"{origin}{tenant}/api/{api_name}/confirmed"
        f"?rememberMe=false&csrf_token={csrf}&tx={tx}&p={policy}"
    )
    time.sleep(0.8)
    r2 = s.get(confirmed, timeout=35, allow_redirects=True)
    print(f"confirmed {r2.status_code} {r2.url[:180]}", flush=True)
    tok = extract_token(r2.url, r2.text)
    if tok:
        return tok
    soup = BeautifulSoup(r2.text, "html.parser")
    hidden = {
        inp.get("name"): inp.get("value")
        for inp in soup.find_all("input")
        if inp.get("name")
    }
    if hidden.get("id_token"):
        return hidden["id_token"]
    if hidden.get("code"):
        return exchange_code(hidden["code"])
    return extract_token(r2.url, r2.text)


def login_and_token() -> str:
    env = load_env()
    user = env["OPENSERVE_UPP_USER"]
    password = env["OPENSERVE_UPP_PASS"]
    s = session()
    nonce = str(uuid.uuid4())
    for response_type in ("id_token", "code"):
        url = authorize_url(response_type, nonce)
        print(f"GET authorize {response_type}", flush=True)
        time.sleep(1.1)
        r1 = s.get(url, timeout=30, allow_redirects=True)
        print(f"authorize {r1.status_code} {r1.url[:140]} bytes={len(r1.text)}", flush=True)
        tok = extract_token(r1.url, r1.text)
        if tok:
            return tok
        if "SETTINGS" in r1.text:
            tok = b2c_self_asserted(s, r1.text, user, password)
            if tok:
                return tok
        soup = BeautifulSoup(r1.text, "html.parser")
        form = None
        for candidate in soup.find_all("form"):
            if candidate.find("input", {"type": "password"}) or candidate.find(
                "input", {"name": re.compile("password", re.I)}
            ):
                form = candidate
                break
        if not form and soup.find_all("form"):
            form = soup.find_all("form")[0]
        if not form:
            print("NO_FORM", flush=True)
            continue
        action = urljoin(r1.url, form.get("action") or r1.url)
        payload = fill_login(form, user, password)
        time.sleep(1.4)
        r2 = s.post(
            action,
            data=payload,
            timeout=35,
            allow_redirects=True,
            headers={
                "Origin": f"{urlparse(r1.url).scheme}://{urlparse(r1.url).netloc}",
                "Referer": r1.url,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        print(f"login {r2.status_code} {r2.url[:160]}", flush=True)
        tok = extract_token(r2.url, r2.text)
        if tok:
            return tok
        soup2 = BeautifulSoup(r2.text, "html.parser")
        hidden = {
            inp.get("name"): inp.get("value")
            for inp in soup2.find_all("input")
            if inp.get("name")
        }
        if "id_token" in hidden:
            return hidden["id_token"]
        if "code" in hidden:
            exchanged = exchange_code(hidden["code"])
            if exchanged:
                return exchanged
        print("no token after login", flush=True)
    raise SystemExit("login did not return a UPP token")


def api(s: requests.Session, method: str, path: str, body=None):
    r = s.request(method, BASE + path, json=body, timeout=45)
    print(f"{method} {path} {r.status_code} {r.text[:240].replace(chr(10), ' ')}", flush=True)
    return r


def api_ok(r) -> bool:
    if r.status_code >= 400:
        return False
    text = (r.text or "").lstrip()
    if text.startswith("<") or "Request Rejected" in text:
        return False
    return True


def save_token(token: str) -> None:
    TOKEN_PATH.write_text(token.strip() + "\n")
    TOKEN_PATH.chmod(0o600)
    print(f"wrote {TOKEN_PATH}", flush=True)


def wanted_org_fields(org: dict) -> dict:
    patch = dict(org)
    patch["emailAddress"] = ORG_EMAIL
    patch["bundleTransactionEmail"] = ORG_EMAIL
    # Keep iCloud for human alerts; billing/statements must hit the box.
    return patch


def token_fresh(token: str) -> bool:
    try:
        payload = token.split(".")[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        import base64

        data = json.loads(base64.urlsafe_b64decode(payload))
        return int(data.get("exp") or 0) > time.time() + 60
    except Exception:
        return False


def main() -> int:
    existing = TOKEN_PATH.read_text().strip() if TOKEN_PATH.exists() else ""
    if existing and token_fresh(existing):
        token = existing
        print("reusing fresh UPP token", flush=True)
    else:
        token = login_and_token()
        save_token(token)
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": UA,
        }
    )
    org_r = api(s, "GET", f"/organisations/{ORG_ID}")
    if org_r.status_code >= 400:
        return 1
    org = (org_r.json() or {}).get("data") or {}
    print(
        json.dumps(
            {
                "before": {
                    "emailAddress": org.get("emailAddress"),
                    "bundleTransactionEmail": org.get("bundleTransactionEmail"),
                    "leadResponseEmail": org.get("leadResponseEmail"),
                    "supportEmailAddress": org.get("supportEmailAddress"),
                    "salesEmailAddress": org.get("salesEmailAddress"),
                }
            },
            indent=2,
        ),
        flush=True,
    )
    users_r = api(s, "GET", f"/organisations/{ORG_ID}/users")
    users = (users_r.json() or {}).get("data") or []
    print("users_before", json.dumps(users, indent=2)[:2000], flush=True)
    contacts_r = api(s, "GET", f"/contacts/{ORG_ID}")
    contacts = (contacts_r.json() or {}).get("data") or contacts_r.json()
    print("contacts_before", str(contacts)[:1500], flush=True)

    body = wanted_org_fields(org)
    wrote = False
    for method, path, payload in (
        (
            "PATCH",
            f"/organisations/{ORG_ID}",
            {
                "emailAddress": ORG_EMAIL,
                "bundleTransactionEmail": ORG_EMAIL,
            },
        ),
        (
            "PUT",
            f"/organisations/{ORG_ID}",
            {
                "emailAddress": ORG_EMAIL,
                "bundleTransactionEmail": ORG_EMAIL,
            },
        ),
        ("PATCH", f"/organisations/{ORG_ID}", body),
        ("PUT", f"/organisations/{ORG_ID}", body),
    ):
        r = api(s, method, path, payload)
        if api_ok(r):
            wrote = True
            break
    if not wrote:
        print("ORG_EMAIL_WRITE_FAILED", flush=True)

    # Replace obsolete kevin@go-wifi user with kevin@gowifi.co.za.
    obsolete = [u for u in users if OBSOLETE in str(u.get("email") or "").lower()]
    have_gowifi = any(
        str(u.get("email") or "").lower() == USER_EMAIL for u in users
    )
    for user in obsolete:
        uid = user.get("userId") or user.get("id")
        updated = dict(user)
        updated["email"] = USER_EMAIL
        for method, path, payload in (
            ("PATCH", f"/organisations/{ORG_ID}/users/{uid}", {"email": USER_EMAIL}),
            ("PATCH", f"/organisations/{ORG_ID}/users/{uid}", updated),
            ("PATCH", f"/users/{uid}", {"email": USER_EMAIL}),
            ("PUT", f"/users/{uid}", updated),
            ("PUT", f"/organisations/{ORG_ID}/users/{uid}", updated),
        ):
            r = api(s, method, path, payload)
            if api_ok(r):
                have_gowifi = True
                break
    # Billing / statement contacts still on obsolete go-wifi.
    if isinstance(contacts, list):
        for contact in contacts:
            email = str(
                contact.get("email")
                or contact.get("emailAddress")
                or ""
            ).lower()
            if OBSOLETE not in email:
                continue
            cid = contact.get("id") or contact.get("contactId")
            updated = dict(contact)
            if "email" in updated:
                updated["email"] = USER_EMAIL if "kevin@" in email else ORG_EMAIL
            if "emailAddress" in updated:
                updated["emailAddress"] = (
                    USER_EMAIL if "kevin@" in email else ORG_EMAIL
                )
            for method, path, payload in (
                ("PATCH", f"/contacts/{cid}", updated),
                ("PUT", f"/contacts/{cid}", updated),
            ):
                r = api(s, method, path, payload)
                if api_ok(r):
                    break

    if not have_gowifi:
        invite = {
            "email": USER_EMAIL,
            "firstName": "Kevin",
            "lastName": "Weaving",
            "mobile": "0720821111",
            "role": "ISP_USER",
            "primary": 0,
        }
        for method, path in (
            ("POST", f"/organisations/{ORG_ID}/users"),
            ("PUT", f"/organisations/{ORG_ID}/users"),
        ):
            r = api(s, method, path, invite)
            if api_ok(r):
                have_gowifi = True
                break

    after = api(s, "GET", f"/organisations/{ORG_ID}")
    after_users = api(s, "GET", f"/organisations/{ORG_ID}/users")
    org2 = (after.json() or {}).get("data") or {}
    users2 = (after_users.json() or {}).get("data") or []
    summary = {
        "ok": (
            org2.get("emailAddress") == ORG_EMAIL
            and org2.get("bundleTransactionEmail") == ORG_EMAIL
            and not any(OBSOLETE in str(u.get("email") or "").lower() for u in users2)
        ),
        "after": {
            "emailAddress": org2.get("emailAddress"),
            "bundleTransactionEmail": org2.get("bundleTransactionEmail"),
            "users": [
                {
                    "email": u.get("email"),
                    "status": u.get("status"),
                    "primary": u.get("primary"),
                }
                for u in users2
            ],
        },
        "keep_icloud": KEEP_ICLOUD,
    }
    print(json.dumps(summary, indent=2), flush=True)
    persist_local_db(org2, users2)
    return 0 if summary["ok"] else 2


def persist_local_db(org: dict, users: list) -> None:
    db = Path(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
    if not db.exists() or not org:
        return
    import sqlite3

    conn = sqlite3.connect(db)
    conn.execute(
        """UPDATE organisations
           SET email_address=?, bundle_transaction_email=?,
               lead_response_email=?, support_email=?, sales_email=?
           WHERE id=?""",
        (
            org.get("emailAddress"),
            org.get("bundleTransactionEmail"),
            org.get("leadResponseEmail"),
            org.get("supportEmailAddress"),
            org.get("salesEmailAddress"),
            org.get("id") or ORG_ID,
        ),
    )
    for user in users:
        conn.execute(
            "UPDATE users SET email=?, status=?, is_primary=? WHERE user_id=?",
            (
                user.get("email"),
                user.get("status"),
                1 if user.get("primary") else 0,
                user.get("userId") or user.get("id"),
            ),
        )
    conn.commit()
    conn.close()
    print(f"updated {db} emails", flush=True)


if __name__ == "__main__":
    sys.exit(main())
