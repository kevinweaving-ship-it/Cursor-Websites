"""OAuth 2.0 for Search Console API. No cookies, password, or 2FA stored.

One-time: Kevin consents as kevinweaving@gmail.com (webmasters write scope).
Daily: refresh_token → access_token on Ubuntu.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event, Thread

from .config import GSC_OAUTH_SCOPE, SERVER_SECRET_DIR

TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
LOOPBACK = ("127.0.0.1", 8765)


class NeedGoogleConsent(RuntimeError):
    pass


def _client_paths(secret_dir: Path | None = None) -> tuple[Path, Path]:
    d = secret_dir or SERVER_SECRET_DIR
    return d / "client_secret.json", d / "token.json"


def load_client(secret_dir: Path | None = None) -> dict:
    client_path, _ = _client_paths(secret_dir)
    if not client_path.is_file():
        raise NeedGoogleConsent(f"missing OAuth client file: {client_path}")
    raw = json.loads(client_path.read_text(encoding="utf-8"))
    installed = raw.get("installed") or raw.get("web") or raw
    if not installed.get("client_id") or not installed.get("client_secret"):
        raise NeedGoogleConsent("client_secret.json missing client_id/client_secret")
    return installed


def load_token(secret_dir: Path | None = None) -> dict:
    _, token_path = _client_paths(secret_dir)
    if not token_path.is_file():
        raise NeedGoogleConsent(f"missing token.json: {token_path}")
    tok = json.loads(token_path.read_text(encoding="utf-8"))
    if not tok.get("refresh_token"):
        raise NeedGoogleConsent("token.json has no refresh_token")
    return tok


def save_token(tok: dict, secret_dir: Path | None = None) -> Path:
    d = secret_dir or SERVER_SECRET_DIR
    d.mkdir(parents=True, exist_ok=True)
    _, token_path = _client_paths(secret_dir)
    token_path.write_text(json.dumps(tok, indent=2) + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    return token_path


def access_token(secret_dir: Path | None = None) -> str:
    client = load_client(secret_dir)
    tok = load_token(secret_dir)
    body = urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "refresh_token": tok["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        TOKEN_URI,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        raise NeedGoogleConsent(f"token refresh failed: {type(exc).__name__}") from exc
    if not data.get("access_token"):
        raise NeedGoogleConsent("token refresh returned no access_token")
    if data.get("refresh_token"):
        tok["refresh_token"] = data["refresh_token"]
        save_token(tok, secret_dir)
    return data["access_token"]


def auth_url(client: dict, redirect: str) -> str:
    q = urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": GSC_OAUTH_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
    )
    return f"{AUTH_URI}?{q}"


def exchange_code(client: dict, code: str, redirect: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        }
    ).encode()
    req = urllib.request.Request(
        TOKEN_URI,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if not data.get("refresh_token"):
        raise NeedGoogleConsent(
            "Google did not return refresh_token. Re-run with prompt=consent."
        )
    return {
        "refresh_token": data["refresh_token"],
        "token_uri": TOKEN_URI,
        "scopes": [GSC_OAUTH_SCOPE],
    }


def authorize_loopback(secret_dir: Path | None = None) -> Path:
    """Mac one-time: open browser, capture code on 127.0.0.1:8765."""
    client = load_client(secret_dir)
    host, port = LOOPBACK
    redirect = f"http://{host}:{port}/"
    url = auth_url(client, redirect)
    holder: dict = {}
    done = Event()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            holder["code"] = (qs.get("code") or [""])[0]
            holder["error"] = (qs.get("error") or [""])[0]
            body = b"SailingSA GSC OAuth: you can close this tab."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()

        def log_message(self, *_a):
            return

    httpd = HTTPServer((host, port), H)
    t = Thread(target=httpd.handle_request, daemon=True)
    t.start()
    print("OPEN_IN_BROWSER")
    print(url)
    print("Waiting for Google consent on", redirect)
    if not done.wait(300):
        raise NeedGoogleConsent("timed out waiting for Google consent")
    if holder.get("error") or not holder.get("code"):
        raise NeedGoogleConsent(holder.get("error") or "no code")
    tok = exchange_code(client, holder["code"], redirect)
    return save_token(tok, secret_dir)
