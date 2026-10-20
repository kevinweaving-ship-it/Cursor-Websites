"""Optional Google Indexing API ping after a weekend issue is written.

Google documents this API for JobPosting and livestream BroadcastEvent pages.
We still fire URL_UPDATED for first-party weekend-roundup URLs when credentials
exist, as requested. Failures are logged and never block publish.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def issue_url(monday: str) -> str:
    return f"https://sailingsa.co.za/sailing-roundup/issues/{monday}/"


def _access_token() -> str | None:
    path = os.environ.get("GOOGLE_INDEXING_SA_JSON") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not path or not os.path.isfile(path):
        return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        creds = service_account.Credentials.from_service_account_file(
            path,
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        creds.refresh(Request())
        return creds.token
    except Exception as exc:
        print(f"[google-index] credentials failed: {exc}")
        return None


def notify_url_updated(url: str) -> dict[str, Any]:
    token = _access_token()
    if not token:
        return {"ok": False, "skipped": True, "reason": "no_credentials", "url": url}
    body = json.dumps({"url": url, "type": "URL_UPDATED"}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", "replace")
        return {"ok": True, "url": url, "response": raw[:500]}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        print(f"[google-index] HTTP {exc.code} for {url}: {detail}")
        return {"ok": False, "url": url, "status": exc.code, "detail": detail}
    except Exception as exc:
        print(f"[google-index] {exc}")
        return {"ok": False, "url": url, "error": str(exc)[:200]}


def notify_issue(monday: str) -> dict[str, Any]:
    return notify_url_updated(issue_url(monday))
