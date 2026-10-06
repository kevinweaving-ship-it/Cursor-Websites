#!/usr/bin/env python3
"""Direct FNB Integration Channel client. Not QuickBooks.

Read-only Transaction History for 62860060278. Keys stay in /root/secrets.
Does not pay, collect, or go through Xero / Sage / QB bank feeds.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from company import COMPANY, GOWIFI_FNB

ENV_PATH = Path(os.environ.get("FNB_ENV", "/root/secrets/fnb.env"))
TOKEN_PATH = Path(os.environ.get("FNB_TOKEN", "/root/secrets/fnb.token"))
DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
LISTEN = os.environ.get("FNB_API_LISTEN", "127.0.0.1:8798")
CATALOGUE = "https://www.fnb.co.za/integration-channel/index.html"
# Official Integration Channel REST hosts. Override from the subscribe page
# if FNB showed different URLs. Never Intuit / QuickBooks.
TOKEN_CANDIDATES = (
    "https://api.fnb.co.za/oauth2/token",
    "https://api.fnb.co.za/oauth2/v1/token",
    "https://openapi.fnb.co.za/oauth2/token",
)
TX_GET_CANDIDATES = (
    "/transaction-history/v1/accounts/{account}/transactions",
    "/enterprise/transaction-history/v1/accounts/{account}/transactions",
    "/za/enterprise/transaction-history/v1/accounts/{account}/transactions",
)
TX_POST_CANDIDATES = (
    "/transaction-history/v1/transactions",
    "/enterprise/transaction-history/v1/transactions",
)
FNB_SOURCES = frozenset({"fnb_api", "fnb_live", "fnb_online", "fnb_history"})
QB_SOURCES = frozenset({"qb_fnb_history", "qb-fnb", "quickbooks"})


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
    keep = _load_env(path)
    keep.update({k: v for k, v in data.items() if v is not None})
    lines = [f"{k}={keep[k]}" for k in keep if keep.get(k) is not None]
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def _money(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).replace("R", "").replace(",", "").replace("\xa0", "").replace(" ", "").strip()
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def _day(value) -> str | None:
    if not value:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if "/" in text:
        parts = text.split("/")
        if len(parts) == 3 and len(parts[2]) == 4:
            return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    return None


def status(env: dict[str, str] | None = None) -> dict:
    env = _load_env() if env is None else env
    client_id = (env.get("FNB_CLIENT_ID") or "").strip()
    secret = (env.get("FNB_CLIENT_SECRET") or "").strip()
    username = (env.get("FNB_USERNAME") or "").strip()
    password = (env.get("FNB_PASSWORD") or "").strip()
    account = (env.get("FNB_ACCOUNT_NUMBER") or GOWIFI_FNB).strip()
    has_api = bool(client_id and secret)
    has_login = bool(username and password)
    via = "fnb-live" if has_login else "fnb-api"
    if has_login:
        note = (
            "FNB Online Banking live statement. Popup dismissed when it appears. "
            "New rows only — no duplicates. The box fetches FNB and allocates who paid."
        )
    elif has_api:
        note = "FNB Integration Channel Transaction History. Direct bank API, not QuickBooks."
    else:
        note = (
            "Save FNB Online Banking login at /legal/fnb.html (box secrets only), "
            "or Integration Channel Client ID and Secret. Not QuickBooks."
        )
    return {
        "ready": has_login or has_api,
        "has_login": has_login,
        "has_api": has_api,
        "account_number": account,
        "account_name": COMPANY["bank_account_name"],
        "has_token": TOKEN_PATH.exists(),
        "via": via,
        "note": note,
    }


def save_keys(
    client_id: str,
    client_secret: str,
    account_number: str | None = None,
    token_url: str | None = None,
    tx_url: str | None = None,
) -> dict:
    client_id = (client_id or "").strip()
    client_secret = (client_secret or "").strip()
    if not client_id or not client_secret:
        raise SystemExit("FNB Client ID and Client Secret are required")
    data = {
        "FNB_CLIENT_ID": client_id,
        "FNB_CLIENT_SECRET": client_secret,
        "FNB_ACCOUNT_NUMBER": (account_number or GOWIFI_FNB).strip() or GOWIFI_FNB,
    }
    if token_url:
        data["FNB_TOKEN_URL"] = token_url.strip()
    if tx_url:
        data["FNB_TX_URL"] = tx_url.strip()
    _save_env(data)
    return {**status(), "ok": True, "saved": True}


def _basic(client_id: str, secret: str) -> str:
    raw = f"{client_id}:{secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _http(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    data: bytes | None = None,
    timeout: int = 45,
) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:2000]


def _token_urls(env: dict[str, str]) -> list[str]:
    fixed = (env.get("FNB_TOKEN_URL") or "").strip()
    if fixed:
        return [fixed]
    return list(TOKEN_CANDIDATES)


def _api_bases(env: dict[str, str]) -> list[str]:
    fixed = (env.get("FNB_API_BASE") or "").strip()
    if fixed:
        return [fixed.rstrip("/")]
    return ["https://api.fnb.co.za", "https://openapi.fnb.co.za"]


def access_token(env: dict[str, str] | None = None) -> str:
    env = env or _load_env()
    if TOKEN_PATH.exists():
        try:
            cached = json.loads(TOKEN_PATH.read_text())
            exp = int(cached.get("obtained_at") or 0) + int(cached.get("expires_in") or 3600)
            if cached.get("access_token") and time.time() < exp - 60:
                return cached["access_token"]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    client_id = (env.get("FNB_CLIENT_ID") or "").strip()
    secret = (env.get("FNB_CLIENT_SECRET") or "").strip()
    if not client_id or not secret:
        raise SystemExit("FNB API not connected — /legal/fnb.html")
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    last = "no token host"
    for url in _token_urls(env):
        for headers in (
            {
                "Authorization": _basic(client_id, secret),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        ):
            payload = body
            if "Authorization" not in headers:
                payload = urllib.parse.urlencode(
                    {
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": secret,
                    }
                ).encode()
            code, raw = _http(url, "POST", headers, payload)
            if code != 200:
                last = f"{url} {code}: {raw[:180]}"
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                last = f"{url} not json"
                continue
            token = data.get("access_token")
            if not token:
                last = f"{url} no access_token"
                continue
            data["obtained_at"] = int(time.time())
            data["token_url"] = url
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_PATH.write_text(json.dumps(data))
            os.chmod(TOKEN_PATH, 0o600)
            if url != env.get("FNB_TOKEN_URL"):
                _save_env({"FNB_TOKEN_URL": url})
            return token
    raise SystemExit(f"FNB token failed: {last}")


def _headers(token: str, env: dict[str, str]) -> dict[str, str]:
    out = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    key = (env.get("FNB_API_KEY") or "").strip()
    if key:
        out["X-API-Key"] = key
    return out


def _first_list(payload) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in (
        "transactions",
        "transactionList",
        "accountTransactions",
        "items",
        "data",
        "results",
        "content",
    ):
        val = payload.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            inner = _first_list(val)
            if inner:
                return inner
    return []


def parse_transactions(payload, filename: str = "fnb-api") -> list[dict]:
    """Map FNB Transaction History JSON. Do not invent rows."""
    rows = []
    for item in _first_list(payload):
        if not isinstance(item, dict):
            continue
        paid_on = _day(
            item.get("date")
            or item.get("transactionDate")
            or item.get("postingDate")
            or item.get("valueDate")
            or item.get("actionDate")
        )
        amount = _money(
            item.get("amount")
            or item.get("transactionAmount")
            or item.get("txnAmount")
        )
        credit = _money(item.get("credit") or item.get("creditAmount") or item.get("received"))
        debit = _money(item.get("debit") or item.get("debitAmount") or item.get("spent"))
        if amount is None:
            if credit and not debit:
                amount = abs(credit)
            elif debit and not credit:
                amount = -abs(debit)
        if amount is None or not paid_on:
            continue
        kind = str(item.get("type") or item.get("transactionType") or item.get("creditDebit") or "").upper()
        if kind in {"DEBIT", "DR", "D"} and amount > 0:
            amount = -amount
        if kind in {"CREDIT", "CR", "C"} and amount < 0:
            amount = abs(amount)
        desc = (
            item.get("description")
            or item.get("narrative")
            or item.get("bankDescription")
            or item.get("particulars")
            or ""
        )
        ref = item.get("reference") or item.get("referenceNumber") or item.get("ref") or ""
        detail = str(desc).strip()
        if str(ref).strip() and str(ref).strip() not in detail:
            detail = f"{detail} / {str(ref).strip()}".strip(" /")
        rows.append(
            {
                "account_number": GOWIFI_FNB,
                "account_name": COMPANY["bank_account_name"],
                "ours": 1,
                "paid_on": paid_on,
                "amount": amount,
                "balance": _money(item.get("balance") or item.get("runningBalance") or item.get("availableBalance")),
                "description": detail,
                "source": "fnb_api",
                "filename": filename,
            }
        )
    return rows


def fetch_transactions(
    from_day: date,
    to_day: date,
    env: dict[str, str] | None = None,
) -> list[dict]:
    env = env or _load_env()
    token = access_token(env)
    account = (env.get("FNB_ACCOUNT_NUMBER") or GOWIFI_FNB).strip()
    fixed = (env.get("FNB_TX_URL") or "").strip()
    headers = _headers(token, env)
    params = {
        "accountNumber": account,
        "fromDate": from_day.isoformat(),
        "toDate": to_day.isoformat(),
        "transactionType": "ALL",
    }
    last = "no tx host"
    attempts: list[tuple[str, str, bytes | None]] = []
    if fixed:
        if "{account}" in fixed or "fromDate" in fixed:
            url = fixed.replace("{account}", account).replace("{from}", from_day.isoformat()).replace("{to}", to_day.isoformat())
            if "?" not in url:
                url = url + "?" + urllib.parse.urlencode(params)
            attempts.append((url, "GET", None))
        else:
            attempts.append((fixed, "POST", json.dumps(params).encode()))
            attempts.append((fixed + "?" + urllib.parse.urlencode(params), "GET", None))
    else:
        for base in _api_bases(env):
            for path in TX_GET_CANDIDATES:
                url = base + path.format(account=account) + "?" + urllib.parse.urlencode(params)
                attempts.append((url, "GET", None))
            for path in TX_POST_CANDIDATES:
                attempts.append((base + path, "POST", json.dumps(params).encode()))
    for url, method, data in attempts:
        code, raw = _http(url, method, headers, data)
        if code != 200:
            last = f"{method} {url} {code}: {raw[:180]}"
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            last = f"{url} not json"
            continue
        rows = parse_transactions(payload, "fnb-api")
        if rows or payload == [] or _first_list(payload) == []:
            if not env.get("FNB_TX_URL"):
                _save_env({"FNB_TX_URL": url.split("?")[0], "FNB_API_BASE": urllib.parse.urlparse(url).scheme + "://" + urllib.parse.urlparse(url).netloc})
            return rows
        last = f"{url} empty shape"
    raise SystemExit(f"FNB transactions failed: {last}")


def _upsert_bank(conn: sqlite3.Connection, rows: list[dict]) -> int:
    from books import ensure_tables

    ensure_tables(conn)
    n = 0
    for row in rows:
        if (row.get("source") or "") in QB_SOURCES:
            continue
        cur = conn.execute(
            """INSERT OR IGNORE INTO bank_tx
               (account_number, account_name, ours, paid_on, amount, balance, description, source, filename)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                row.get("account_number") or GOWIFI_FNB,
                row.get("account_name") or COMPANY["bank_account_name"],
                1,
                row["paid_on"],
                row["amount"],
                row.get("balance"),
                row.get("description"),
                "fnb_api",
                row.get("filename") or "fnb-api",
            ),
        )
        n += cur.rowcount or 0
    return n


def pull_api(conn: sqlite3.Connection | None = None, days: int = 90) -> dict:
    env = _load_env()
    st = status(env)
    if not st.get("has_api"):
        return {"ok": False, "error": st["note"], "inserted": 0, "rows": 0, "via": "fnb-api"}
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    inserted = 0
    fetched = 0
    to_day = date.today()
    start = to_day - timedelta(days=max(1, days))
    window = 30
    day = start
    notes = []
    while day <= to_day:
        end = min(day + timedelta(days=window - 1), to_day)
        rows = fetch_transactions(day, end, env)
        fetched += len(rows)
        inserted += _upsert_bank(own, rows)
        notes.append(f"{day.isoformat()}:{end.isoformat()}={len(rows)}")
        day = end + timedelta(days=1)
    own.commit()
    if conn is None:
        own.close()
    return {
        "ok": True,
        "inserted": inserted,
        "rows": fetched,
        "via": "fnb-api",
        "account_number": st["account_number"],
        "note": "; ".join(notes),
    }


def _refresh_accounts() -> None:
    try:
        from audit_export import main as export_accounts

        export_accounts()
    except Exception:
        pass


def pull(conn: sqlite3.Connection | None = None, days: int = 90, live: bool = True) -> dict:
    """Live Online Banking first. Integration Channel only when there is no login."""
    env = _load_env()
    if live:
        from fnb_statement import login_ready
        from fnb_statement import pull as live_pull

        if login_ready(env):
            pack = live_pull(conn)
            _refresh_accounts()
            return pack
    if status(env).get("has_api"):
        pack = pull_api(conn, days=days)
        _refresh_accounts()
        return pack
    return {
        "ok": False,
        "error": status(env)["note"],
        "inserted": 0,
        "rows": 0,
        "via": "fnb-live",
    }


def card(conn: sqlite3.Connection | None = None, limit: int = 80) -> dict:
    """FNB card from bank rows we fetched. Never QuickBooks history."""
    from fnb_statement import card_overlay

    st = status()
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    overlay = card_overlay(own)
    rows = []
    try:
        for rec in own.execute(
            """SELECT paid_on, amount, balance, description, source FROM bank_tx
               WHERE ours=1 AND source IN ('fnb_live','fnb_online','fnb_api','fnb_history')
               ORDER BY paid_on DESC, id DESC LIMIT ?""",
            (limit,),
        ):
            amount = rec[1]
            rows.append(
                {
                    "paid_on": rec[0],
                    "description": rec[3],
                    "spent": abs(amount) if amount is not None and amount < 0 else None,
                    "received": abs(amount) if amount is not None and amount > 0 else None,
                    "amount": amount,
                    "balance": rec[2],
                    "source": rec[4],
                }
            )
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        row["tone"] = "posted"
    posted_bal = overlay.get("system_balance")
    if posted_bal is None and rows:
        posted_bal = rows[0]["balance"]
    running = posted_bal
    pending_built = []
    for raw in reversed(overlay.get("pending") or []):
        amt = raw.get("amount")
        try:
            amt = float(amt or 0)
        except (TypeError, ValueError):
            amt = 0.0
        if running is not None:
            running = round(float(running) + amt, 2)
        desc = (raw.get("description") or "").strip()
        card = (raw.get("card") or "").strip()
        if card and card not in desc:
            desc = f"{desc} / {card}".strip(" /")
        pending_built.append(
            {
                "paid_on": raw.get("paid_on"),
                "description": desc,
                "spent": abs(amt) if amt < 0 else None,
                "received": abs(amt) if amt > 0 else None,
                "amount": amt,
                "balance": running,
                "source": "fnb_pending",
                "tone": "pending",
            }
        )
    pending_rows = list(reversed(pending_built))
    rows = pending_rows + rows
    if conn is None:
        own.close()
    latest = rows[0] if rows else None
    system_balance = latest["balance"] if latest else posted_bal
    matched = bool(overlay.get("matched")) and not pending_rows
    attention_amount = overlay.get("attention_amount") or 0
    if rows:
        note = (
            "FNB posted. Processed."
            if matched
            else f"New items not auto-reconciled · {attention_amount:.2f} needs attention."
        )
    else:
        note = st["note"]
    return {
        "name": "FNB",
        "account_number": st["account_number"],
        "account_name": COMPANY["bank_account_name"],
        "branch": COMPANY["branch"],
        "branch_code": COMPANY["branch_code"],
        "bank": COMPANY["bank"],
        "ready": st["ready"],
        "via": st["via"],
        "has_login": st.get("has_login"),
        "has_api": st.get("has_api"),
        "balance": system_balance,
        "system_balance": posted_bal,
        "as_at": latest["paid_on"] if latest else None,
        "last_fetched": overlay.get("last_fetched"),
        "last_fetched_label": overlay.get("last_fetched_label"),
        "matched": matched,
        "last_ok": overlay.get("last_ok"),
        "available": overlay.get("available"),
        "pending": overlay.get("pending") or [],
        "pending_amount": overlay.get("pending_amount") or 0,
        "attention": overlay.get("attention") or [],
        "attention_amount": attention_amount,
        "choices": overlay.get("choices") or [],
        "transactions": len(rows),
        "rows": rows,
        "note": note,
        "connect": "/legal/fnb.html",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("fnb-api: " + fmt % args + "\n")

    def _origin(self) -> str:
        origin = self.headers.get("Origin") or ""
        if origin in {"https://gowifi.co.za", "https://box.gowifi.co.za"}:
            return origin
        return "https://gowifi.co.za"

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", self._origin())
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self._origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in {"/status", "/legal/fnb-status"}:
            self._send(200, status())
            return
        if path in {"/card", "/legal/fnb-card"}:
            self._send(200, card())
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "bad json"})
            return
        try:
            if path in {"/save", "/legal/fnb-save"}:
                username = str(data.get("username") or data.get("user") or "").strip()
                password = str(data.get("password") or "").strip()
                if username and password:
                    from fnb_statement import save_login

                    pack = save_login(
                        username,
                        password,
                        str(data.get("account_number") or data.get("accountNumber") or "") or None,
                    )
                    pack["username"] = username
                    self._send(200, {**status(), **pack})
                    return
                self._send(
                    200,
                    save_keys(
                        str(data.get("client_id") or data.get("clientId") or ""),
                        str(data.get("client_secret") or data.get("clientSecret") or ""),
                        str(data.get("account_number") or data.get("accountNumber") or "") or None,
                        str(data.get("token_url") or "") or None,
                        str(data.get("tx_url") or "") or None,
                    ),
                )
                return
            if path in {"/pull", "/legal/fnb-pull"}:
                self._send(200, pull())
                return
            if path in {"/alloc", "/legal/fnb-alloc"}:
                from fnb_statement import apply_alloc

                own = sqlite3.connect(os.environ.get("UPP_DB", DB))
                pack = apply_alloc(
                    own,
                    int(data.get("id") or 0),
                    str(data.get("kind") or ""),
                    str(data.get("to") or data.get("label") or ""),
                )
                own.close()
                if pack.get("ok"):
                    _refresh_accounts()
                    pack.update(card())
                self._send(200, pack)
                return
        except SystemExit as exc:
            self._send(400, {"ok": False, "error": str(exc)})
            return
        self._send(404, {"error": "not found"})


def _auto_fetch_loop() -> None:
    time.sleep(8)
    while True:
        try:
            from fnb_statement import last_fetch, login_ready

            last = last_fetch() or {}
            stale = True
            if last.get("ok") and last.get("fetched_at"):
                try:
                    got = datetime.fromisoformat(last["fetched_at"])
                    stale = (datetime.now(got.tzinfo) - got).total_seconds() > 20 * 60
                except ValueError:
                    stale = True
            if login_ready() and stale:
                pull()
        except Exception as exc:
            sys.stderr.write(f"fnb-auto: {exc}\n")
        time.sleep(20 * 60)


def serve() -> None:
    import threading

    threading.Thread(target=_auto_fetch_loop, daemon=True, name="fnb-auto").start()
    host, port = LISTEN.split(":")
    httpd = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"fnb-api on {LISTEN}", flush=True)
    httpd.serve_forever()


def self_test() -> int:
    failed = 0
    st = status({"FNB_CLIENT_ID": "", "FNB_CLIENT_SECRET": ""})
    if st["ready"]:
        print("FAIL status-empty-not-ready", st)
        failed += 1
    payload = {
        "transactions": [
            {
                "date": "2026-10-05",
                "description": "PAYFAST Host Africa Oct",
                "reference": "PAYFAST",
                "amount": -520.0,
                "balance": 4554.66,
                "type": "DEBIT",
            },
            {
                "transactionDate": "2026-10-01",
                "narrative": "RSAWEB NETCASH",
                "debitAmount": 2223.94,
                "runningBalance": 5074.66,
                "transactionType": "DEBIT",
            },
            {
                "date": "2026-09-30",
                "description": "CAPITEC P PEARSON",
                "creditAmount": 329.0,
                "balance": 7298.60,
                "type": "CREDIT",
            },
        ]
    }
    rows = parse_transactions(payload)
    if len(rows) != 3 or rows[0]["source"] != "fnb_api" or rows[0]["amount"] != -520:
        print("FAIL parse", rows)
        failed += 1
    elif rows[1]["amount"] != -2223.94 or rows[2]["amount"] != 329:
        print("FAIL parse-signs", rows)
        failed += 1
    elif any(r["source"] in QB_SOURCES for r in rows):
        print("FAIL qb-source", rows)
        failed += 1
    else:
        print("OK fnb-api-parse")
    conn = sqlite3.connect(":memory:")
    n = _upsert_bank(conn, rows + [{"paid_on": "2026-01-01", "amount": 1, "description": "QB", "source": "qb_fnb_history"}])
    if n != 3:
        print("FAIL upsert-no-qb", n)
        failed += 1
    else:
        print("OK fnb-api-upsert-ignores-qb")
    pack = card(conn)
    if pack["balance"] != 4554.66 or pack["rows"][0]["spent"] != 520:
        print("FAIL card", pack)
        failed += 1
    elif pack["rows"][0]["source"] != "fnb_api":
        print("FAIL card-source", pack["rows"][0])
        failed += 1
    elif pack.get("last_fetched") is not None:
        print("FAIL card-no-fetch-yet", pack.get("last_fetched"))
        failed += 1
    elif pack.get("attention_amount"):
        print("FAIL card-matched", pack.get("matched"), pack.get("attention_amount"))
        failed += 1
    else:
        print("OK fnb-card-system-balance")
    from fnb_statement import replace_pending

    replace_pending(
        conn,
        [
            {
                "paid_on": "2026-10-03 15:00:39",
                "card": "485442******9008",
                "description": "WWW.UI.COM",
                "amount": -499.22,
            }
        ],
    )
    orange = card(conn)
    if (
        orange["rows"][0]["tone"] != "pending"
        or orange["rows"][0]["balance"] != 4055.44
        or orange["rows"][0]["paid_on"] != "2026-10-03 15:00:39"
        or "WWW.UI.COM" not in (orange["rows"][0]["description"] or "")
        or "485442" not in (orange["rows"][0]["description"] or "")
    ):
        print("FAIL pending-on-register", orange["rows"][0])
        failed += 1
    elif orange["rows"][1]["tone"] != "posted":
        print("FAIL posted-stays-blue", orange["rows"][1])
        failed += 1
    else:
        print("OK pending-orange-then-posted-blue")
    replace_pending(conn, [])
    cleared = card(conn)
    if cleared["rows"][0]["tone"] != "posted" or cleared["rows"][0]["source"] != "fnb_api":
        print("FAIL pending-cleared-blue", cleared["rows"][0])
        failed += 1
    else:
        print("OK pending-cleared-processed-blue")
    conn.close()
    return failed


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "test":
        raise SystemExit(self_test())
    if cmd == "status":
        print(json.dumps(status(), indent=2))
    elif cmd == "save":
        if len(sys.argv) < 4:
            raise SystemExit("save CLIENT_ID CLIENT_SECRET [ACCOUNT]")
        print(json.dumps(save_keys(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)))
    elif cmd == "pull":
        print(json.dumps(pull(), indent=2))
    elif cmd == "card":
        print(json.dumps(card(), indent=2))
    elif cmd == "serve":
        serve()
    else:
        raise SystemExit("status | save | pull | card | serve | test")
