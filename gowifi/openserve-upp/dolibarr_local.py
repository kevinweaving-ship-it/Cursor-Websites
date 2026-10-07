#!/usr/bin/env python3
"""Loopback Dolibarr REST client. Never leaves the box."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_PATH = Path(os.environ.get("DOLIBARR_ENV", "/root/secrets/dolibarr.env"))
# Internal nginx, 127.0.0.1 only — not https://gowifi.co.za
BASE = os.environ.get("DOLIBARR_LOCAL_API", "http://127.0.0.1:8091/dolibarr/api/index.php")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key] = val
    return env


def api_key() -> str:
    key = os.environ.get("DOLIBARR_API_KEY") or load_env().get("DOLIBARR_API_KEY") or ""
    if not key:
        raise SystemExit("DOLIBARR_API_KEY missing")
    return key


def call(path: str, method: str = "GET", query: dict | None = None, body=None):
    url = BASE.rstrip("/") + "/" + path.lstrip("/")
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    data = None
    headers = {"DOLAPIKEY": api_key(), "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode() or "null")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"dolibarr local API {method} {path} -> {exc.code} {detail}") from exc


def thirdparties(limit: int = 100) -> list[dict]:
    rows = call("thirdparties", query={"limit": str(limit), "sortfield": "t.nom"})
    return rows if isinstance(rows, list) else []


def invoices(limit: int = 200, page: int = 0, thirdparty_ids: str = "") -> list[dict]:
    query = {"limit": str(limit), "page": str(page), "sortfield": "t.rowid"}
    if thirdparty_ids:
        query["thirdparty_ids"] = thirdparty_ids
    rows = call("invoices", query=query)
    return rows if isinstance(rows, list) else []


def all_invoices() -> list[dict]:
    out: list[dict] = []
    page = 0
    while True:
        chunk = invoices(limit=200, page=page)
        out.extend(chunk)
        if len(chunk) < 200:
            break
        page += 1
        if page > 40:
            break
    return out
