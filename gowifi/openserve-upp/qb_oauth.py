#!/usr/bin/env python3
"""Production QuickBooks OAuth for GoWiFi Box. Tokens stay in /root/secrets."""
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


def authorize_url(env: dict[str, str] | None = None) -> str:
    env = env or _load_env()
    client_id = env.get("QBO_CLIENT_ID") or ""
    redirect = env.get("QBO_REDIRECT_URI") or "https://gowifi.co.za/legal/qb-callback.html"
    if not client_id:
        raise SystemExit("QBO_CLIENT_ID missing in /root/secrets/qbo.env")
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


def _basic(env: dict[str, str]) -> str:
    raw = f"{env['QBO_CLIENT_ID']}:{env['QBO_CLIENT_SECRET']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _post_token(env: dict[str, str], body: dict[str, str]) -> dict:
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(body).encode(),
        method="POST",
        headers={
            "Authorization": _basic(env),
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:400]
        raise SystemExit(f"token exchange failed {exc.code}: {detail}") from exc


def exchange_code(code: str, realm_id: str) -> dict:
    env = _load_env()
    if not env.get("QBO_CLIENT_SECRET"):
        raise SystemExit("QBO_CLIENT_SECRET missing in /root/secrets/qbo.env")
    payload = _post_token(
        env,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": env.get("QBO_REDIRECT_URI")
            or "https://gowifi.co.za/legal/qb-callback.html",
        },
    )
    payload["realmId"] = realm_id or payload.get("realmId")
    payload["obtained_at"] = int(time.time())
    save_tokens(payload)
    return {"ok": True, "realmId": payload.get("realmId")}


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
    tokens = load_tokens()
    payload = _post_token(
        env,
        {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
    )
    payload["realmId"] = tokens.get("realmId")
    payload["obtained_at"] = int(time.time())
    save_tokens(payload)
    return payload


def access_token() -> tuple[str, str]:
    tokens = load_tokens()
    obtained = int(tokens.get("obtained_at") or 0)
    expires = int(tokens.get("expires_in") or 3600)
    if not tokens.get("access_token") or time.time() > obtained + expires - 60:
        tokens = refresh_tokens()
    return tokens["access_token"], str(tokens["realmId"])


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
                self._send(200, {"url": authorize_url()})
            except SystemExit as exc:
                self._send(400, {"error": str(exc)})
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
    elif cmd == "serve":
        serve()
    elif cmd == "refresh":
        refresh_tokens()
        print("refreshed")
    else:
        raise SystemExit("url | serve | refresh")
