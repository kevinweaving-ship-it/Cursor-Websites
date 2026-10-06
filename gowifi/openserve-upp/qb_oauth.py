#!/usr/bin/env python3
"""QuickBooks OAuth for GoWiFi Box. Tokens stay in /root/secrets."""
from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENV_PATH = Path(os.environ.get("QBO_ENV", "/root/secrets/qbo.env"))
TOKEN_PATH = Path(os.environ.get("QBO_TOKEN", "/root/secrets/qbo.token"))
LISTEN = os.environ.get("QBO_OAUTH_LISTEN", "127.0.0.1:8799")
AUTHORIZE = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
SCOPE = "com.intuit.quickbooks.accounting"
STATE = "gowifi-box"
BOX_REDIRECT = "https://gowifi.co.za/legal/qb-callback.html"
# Intuit Development Keys keep this URI. Custom host URIs often fail to save
# and Connect then dies with "redirect_uri query parameter value is invalid".
PLAYGROUND_REDIRECT = "https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl"
KNOWN_REALM = "9130354340040586"
# Janishia Noronha, Intuit Developer Group, 6 Oct 2026 — typos in the IDs we sent.
INTUIT_APP_ID = "29bf4b87-d9b1-438f-9e35-52362429db57"
INTUIT_DEV_CLIENT_ID = "ABs2E5POp4qzGRxLNEmMvP0LC2fGgXKzcHzYs1RUl4bsBhhvjD"
INTUIT_PROD_CLIENT_ID = "ABuRsGyeZTQuOqil7wEeIWsIjzSQU6UQv4hOg1R0vXzPDVEjXL"
API_PROD = "https://quickbooks.api.intuit.com/v3/company"
API_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"


def _load_env(path: Path = ENV_PATH) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    return data


def _save_env(data: dict[str, str], path: Path = ENV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={data[k]}" for k in data if data.get(k) is not None]
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def active_keyset(env: dict[str, str] | None = None) -> str:
    env = env or _load_env()
    raw = (env.get("QBO_KEYSET") or "production").strip().lower()
    if raw.startswith("dev"):
        return "development"
    return "production"


def use_box_callback(env: dict[str, str] | None = None) -> bool:
    env = env or _load_env()
    return (env.get("QBO_USE_CALLBACK") or "").strip().lower() in {
        "1",
        "yes",
        "true",
        "callback",
    }


def active_redirect(env: dict[str, str] | None = None) -> str:
    """Live company uses the box callback. Dev/sandbox uses Playground."""
    env = env or _load_env()
    if active_keyset(env) == "production" or use_box_callback(env):
        return (env.get("QBO_REDIRECT_URI") or BOX_REDIRECT).strip()
    return PLAYGROUND_REDIRECT


def client_pair(env: dict[str, str] | None = None) -> tuple[str, str, str]:
    """Return (client_id, client_secret, redirect) for the active keyset.

    Intuit's 2026 App Center often cannot resolve a Production client_id to an
    app name and shows "undefined didn't connect". Development client_ids still
    resolve and can reach the live company. Keep both pairs on disk; switch
    with QBO_KEYSET=development|production.
    """
    env = env or _load_env()
    redirect = active_redirect(env)
    keyset = active_keyset(env)
    if keyset == "production":
        client_id = env.get("QBO_PROD_CLIENT_ID") or env.get("QBO_CLIENT_ID") or ""
        secret = env.get("QBO_PROD_CLIENT_SECRET") or env.get("QBO_CLIENT_SECRET") or ""
    else:
        client_id = env.get("QBO_DEV_CLIENT_ID") or env.get("QBO_CLIENT_ID") or ""
        secret = env.get("QBO_DEV_CLIENT_SECRET") or env.get("QBO_CLIENT_SECRET") or ""
    return client_id, secret, redirect


def ids_match_intuit(env: dict[str, str] | None = None) -> dict:
    """Local check only. Does not call Intuit or pull books."""
    env = env or _load_env()
    dev = (env.get("QBO_DEV_CLIENT_ID") or "").strip()
    prod = (env.get("QBO_PROD_CLIENT_ID") or "").strip()
    app = (env.get("QBO_APP_ID") or "").strip()
    return {
        "ok": dev == INTUIT_DEV_CLIENT_ID
        and prod == INTUIT_PROD_CLIENT_ID
        and app == INTUIT_APP_ID,
        "dev": dev == INTUIT_DEV_CLIENT_ID,
        "prod": prod == INTUIT_PROD_CLIENT_ID,
        "app": app == INTUIT_APP_ID,
        "keyset": active_keyset(env),
        "has_dev_secret": bool((env.get("QBO_DEV_CLIENT_SECRET") or "").strip()),
        "has_prod_secret": bool((env.get("QBO_PROD_CLIENT_SECRET") or "").strip()),
        "connected": TOKEN_PATH.exists(),
        "redirect": active_redirect(env),
        "callback": use_box_callback(env),
    }


def authorize_url(env: dict[str, str] | None = None) -> str:
    env = env or _load_env()
    client_id, _secret, redirect = client_pair(env)
    if not client_id:
        raise SystemExit("QBO client id missing in /root/secrets/qbo.env")
    q = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "scope": SCOPE,
            "redirect_uri": redirect,
            "state": STATE,
        }
    )
    return f"{AUTHORIZE}?{q}"


def _basic(client_id: str, secret: str) -> str:
    raw = f"{client_id}:{secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _token_error(exc: urllib.error.HTTPError) -> str:
    return exc.read().decode()[:400]


def _post_token(client_id: str, secret: str, body: dict[str, str]) -> dict:
    """Intuit sometimes 401s Basic-only on a real code. Retry with body creds."""
    attempts = (
        (dict(body), True),
        ({**body, "client_id": client_id, "client_secret": secret}, True),
        ({**body, "client_id": client_id, "client_secret": secret}, False),
    )
    last = ""
    last_code = 0
    ctx = ssl.create_default_context()
    for payload, use_basic in attempts:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "GoWiFiBox/1.0",
        }
        if use_basic:
            headers["Authorization"] = _basic(client_id, secret)
        req = urllib.request.Request(
            TOKEN_URL,
            data=urllib.parse.urlencode(payload).encode(),
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            last_code = exc.code
            last = _token_error(exc)
            if "invalid_client" not in last:
                raise SystemExit(f"token exchange failed {last_code}: {last}") from exc
    raise SystemExit(f"token exchange failed {last_code}: {last}")


def exchange_code(code: str, realm_id: str) -> dict:
    env = _load_env()
    client_id, secret, redirect = client_pair(env)
    if not client_id or not secret:
        raise SystemExit("QBO client id/secret missing in /root/secrets/qbo.env")
    code = str(code or "").strip()
    if not code:
        raise SystemExit("missing authorization code")
    realm_id = (realm_id or env.get("QBO_REALM_ID") or KNOWN_REALM).strip()
    payload = _post_token(
        client_id,
        secret,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
        },
    )
    payload["realmId"] = realm_id or payload.get("realmId")
    payload["obtained_at"] = int(time.time())
    payload["keyset"] = active_keyset(env)
    if not payload.get("realmId"):
        raise SystemExit("Intuit sent no company id (realmId)")
    save_tokens(payload)
    return {"ok": True, "realmId": payload.get("realmId"), "keyset": payload["keyset"]}


def ingest_tokens(
    refresh_token: str,
    realm_id: str,
    access_token: str | None = None,
    expires_in: int = 3600,
) -> dict:
    env = _load_env()
    if not refresh_token or not realm_id:
        raise SystemExit("refresh_token and realmId are required")
    payload = {
        "refresh_token": refresh_token,
        "access_token": access_token or "",
        "expires_in": int(expires_in or 3600),
        "realmId": realm_id,
        "obtained_at": int(time.time()) - (0 if access_token else 4000),
        "keyset": active_keyset(env),
        "source": "ingest",
    }
    save_tokens(payload)
    return {"ok": True, "realmId": realm_id, "keyset": payload["keyset"]}


def save_tokens(payload: dict, path: Path = TOKEN_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    os.chmod(path, 0o600)


def load_tokens(path: Path = TOKEN_PATH) -> dict:
    if not path.exists():
        raise SystemExit("no QBO tokens yet — connect first")
    return json.loads(path.read_text())


def refresh_tokens() -> dict:
    env = _load_env()
    client_id, secret, _redirect = client_pair(env)
    tokens = load_tokens()
    payload = _post_token(
        client_id,
        secret,
        {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
    )
    payload["realmId"] = tokens.get("realmId")
    payload["obtained_at"] = int(time.time())
    payload["keyset"] = tokens.get("keyset") or active_keyset(env)
    save_tokens(payload)
    return payload


def access_token() -> tuple[str, str]:
    tokens = load_tokens()
    obtained = int(tokens.get("obtained_at") or 0)
    expires = int(tokens.get("expires_in") or 3600)
    if not tokens.get("access_token") or time.time() > obtained + expires - 60:
        tokens = refresh_tokens()
    return tokens["access_token"], str(tokens["realmId"])


def _http_json(url: str, token: str) -> tuple[int, dict | str]:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:400]


def probe_company() -> dict:
    token, realm = access_token()
    result = {"realmId": realm, "hosts": {}}
    for name, base in (("production", API_PROD), ("sandbox", API_SANDBOX)):
        url = f"{base}/{realm}/companyinfo/{realm}?minorversion=75"
        status, body = _http_json(url, token)
        company = None
        if isinstance(body, dict):
            info = body.get("CompanyInfo") or {}
            company = info.get("CompanyName") or info.get("LegalName")
        result["hosts"][name] = {
            "status": status,
            "company": company,
            "ok": status == 200 and bool(company),
        }
    ok_host = next((n for n, h in result["hosts"].items() if h["ok"]), None)
    result["ok"] = bool(ok_host)
    result["api_host"] = ok_host
    tokens = load_tokens()
    tokens["api_host"] = ok_host
    save_tokens(tokens)
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("qb-oauth: " + fmt % args + "\n")

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "https://gowifi.co.za")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/start":
            try:
                env = _load_env()
                self._send(
                    200,
                    {
                        "url": authorize_url(env),
                        "keyset": active_keyset(env),
                        "redirect": active_redirect(env),
                    },
                )
            except SystemExit as exc:
                self._send(400, {"error": str(exc)})
            return
        if path == "/status":
            token_ok = TOKEN_PATH.exists()
            env = _load_env()
            body: dict = {
                "connected": token_ok,
                "keyset": active_keyset(env),
                "realmId": env.get("QBO_REALM_ID") or KNOWN_REALM,
                "appId": env.get("QBO_APP_ID") or INTUIT_APP_ID,
                "redirect": active_redirect(env),
                "ids": ids_match_intuit(env),
            }
            if token_ok:
                try:
                    tokens = load_tokens()
                    body["realmId"] = tokens.get("realmId") or body["realmId"]
                    body["api_host"] = tokens.get("api_host")
                except Exception:
                    pass
            self._send(200, body)
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path != "/token":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "bad json"})
            return
        try:
            if data.get("refresh_token") and data.get("realmId"):
                self._send(
                    200,
                    ingest_tokens(
                        str(data.get("refresh_token") or ""),
                        str(data.get("realmId") or ""),
                        str(data.get("access_token") or "") or None,
                        int(data.get("expires_in") or 3600),
                    ),
                )
                return
            self._send(
                200,
                exchange_code(str(data.get("code") or ""), str(data.get("realmId") or "")),
            )
        except SystemExit as exc:
            self._send(400, {"error": str(exc)})


def serve() -> None:
    host, port = LISTEN.split(":")
    httpd = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"qb-oauth on {LISTEN}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if cmd == "url":
        print(authorize_url())
    elif cmd == "ids":
        print(json.dumps(ids_match_intuit(), indent=2))
    elif cmd == "serve":
        serve()
    elif cmd == "refresh":
        refresh_tokens()
        print("refreshed")
    elif cmd == "redeem":
        if len(sys.argv) < 4:
            raise SystemExit("redeem CODE REALMID")
        print(json.dumps(exchange_code(sys.argv[2], sys.argv[3])))
    elif cmd == "ingest":
        if len(sys.argv) < 4:
            raise SystemExit("ingest REFRESH_TOKEN REALMID [ACCESS_TOKEN]")
        access = sys.argv[4] if len(sys.argv) > 4 else ""
        print(json.dumps(ingest_tokens(sys.argv[2], sys.argv[3], access or None)))
    elif cmd == "probe":
        print(json.dumps(probe_company(), indent=2))
    else:
        raise SystemExit("url | ids | serve | refresh | redeem | ingest | probe")
