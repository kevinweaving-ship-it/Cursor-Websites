#!/usr/bin/env python3
"""Live FNB statement fetch. Direct Online Banking, not QuickBooks.

Login can show a popup or not. Dismiss it when it is there, then open
the live statement. Only new rows go into bank_tx / fnb_tx. New money
is allocated (client payment, deposit, bank charge, expense) or flagged
as needs attention.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from company import COMPANY, GOWIFI_FNB

ENV_PATH = Path(os.environ.get("FNB_ENV", "/root/secrets/fnb.env"))
DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
LOGIN_URLS = (
    "https://www.online.fnb.co.za/",
    "https://www.fnb.co.za/",
)
ACCOUNT = GOWIFI_FNB
FNB_DIRECT = frozenset({"fnb_live", "fnb_online", "fnb_api", "fnb_history"})
QB_SOURCES = frozenset({"qb_fnb_history", "qb-fnb", "quickbooks"})
SAFE_DISMISS = (
    "close",
    "later",
    "not now",
    "no thanks",
    "maybe later",
    "skip",
    "got it",
    "ok",
    "okay",
    "dismiss",
    "continue",
    "don't show again",
    "do not show again",
    "no",
    "cancel",
    "x",
)
UNSAFE_CLICK = (
    "apply",
    "buy",
    "pay",
    "transfer",
    "subscribe",
    "accept offer",
    "upgrade",
    "open now",
    "get started",
)
BANK_WORDS = frozenset(
    {
        "capitec",
        "fnb",
        "absa",
        "standard",
        "nedbank",
        "investec",
        "tyme",
        "discovery",
        "bank",
        "eft",
        "pay",
        "from",
        "to",
        "netcash",
    }
)
FEE_WORDS = (
    "account fee",
    "bank charge",
    "service fee",
    "int pymt fee",
    "#int",
    "intuity",
    "monthly account fee",
)
EXPENSE_WORDS = (
    "payfast",
    "host africa",
    "rsaweb",
    "rsa web",
    "openserve",
    "dues and subscriptions",
)

FETCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS fnb_fetch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    rows_seen INTEGER,
    inserted INTEGER,
    allocated INTEGER,
    need_recon INTEGER,
    need_recon_amount REAL,
    balance REAL,
    ok INTEGER,
    note TEXT
);
"""


def _load_env(path: Path = ENV_PATH) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    for key in ("FNB_USERNAME", "FNB_PASSWORD", "FNB_ACCOUNT_NUMBER"):
        if os.environ.get(key):
            data[key] = os.environ[key]
    return data


def _save_env(data: dict[str, str], path: Path = ENV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = _load_env(path)
    keep.update({k: v for k, v in data.items() if v is not None})
    lines = [f"{k}={keep[k]}" for k in keep if keep.get(k) is not None]
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def login_ready(env: dict[str, str] | None = None) -> bool:
    env = env or _load_env()
    return bool((env.get("FNB_USERNAME") or "").strip() and (env.get("FNB_PASSWORD") or "").strip())


def save_login(username: str, password: str, account_number: str | None = None) -> dict:
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        raise SystemExit("FNB username and password are required")
    _save_env(
        {
            "FNB_USERNAME": username,
            "FNB_PASSWORD": password,
            "FNB_ACCOUNT_NUMBER": (account_number or ACCOUNT).strip() or ACCOUNT,
        }
    )
    return {"ok": True, "ready": True, "via": "fnb-live", "username": username}


def pick_dismiss(labels: list[str]) -> str | None:
    """Choose a safe popup dismiss. Empty list = no popup this login."""
    for raw in labels:
        label = " ".join((raw or "").lower().split())
        if not label:
            continue
        if any(bad in label for bad in UNSAFE_CLICK):
            continue
        if label in SAFE_DISMISS or any(label.startswith(s) or s in label for s in SAFE_DISMISS):
            return raw
    return None


def normalize_desc(text: str | None) -> str:
    blob = " ".join(str(text or "").lower().replace("\u00a0", " ").split())
    if " / " in blob:
        blob = blob.split(" / ", 1)[0]
    return blob.strip()


def row_key(row: dict) -> tuple:
    acct = re.sub(r"\D", "", str(row.get("account_number") or ACCOUNT))
    day = str(row.get("paid_on") or "")[:10]
    amt = round(float(row.get("amount") or 0), 2)
    bal = row.get("balance")
    try:
        bal = round(float(bal), 2) if bal is not None and bal != "" else None
    except (TypeError, ValueError):
        bal = None
    return (acct, day, amt, bal)


def existing_keys(conn: sqlite3.Connection) -> set[tuple]:
    keys: set[tuple] = set()
    try:
        recs = conn.execute(
            """SELECT account_number, paid_on, amount, balance, description, source
               FROM bank_tx WHERE ours=1"""
        )
    except sqlite3.OperationalError:
        return keys
    for rec in recs:
        if (rec[5] or "") in QB_SOURCES:
            continue
        keys.add(
            row_key(
                {
                    "account_number": rec[0],
                    "paid_on": rec[1],
                    "amount": rec[2],
                    "balance": rec[3],
                    "description": rec[4],
                }
            )
        )
    try:
        for rec in conn.execute(
            """SELECT paid_on, amount, balance, payee, memo, source FROM fnb_tx"""
        ):
            if (rec[5] or "") in {"fnb-xls"}:
                keys.add(
                    row_key(
                        {
                            "account_number": ACCOUNT,
                            "paid_on": rec[0],
                            "amount": rec[1],
                            "balance": rec[2],
                            "description": rec[3],
                        }
                    )
                )
            elif (rec[5] or "") in FNB_DIRECT:
                keys.add(
                    row_key(
                        {
                            "account_number": ACCOUNT,
                            "paid_on": rec[0],
                            "amount": rec[1],
                            "balance": rec[2],
                            "description": rec[3],
                        }
                    )
                )
    except sqlite3.OperationalError:
        pass
    return keys


def to_fnb_row(row: dict) -> dict:
    amount = round(float(row.get("amount") or 0), 2)
    desc = (row.get("description") or "").strip()
    payee = desc.split(" / ")[0].strip() if " / " in desc else desc
    memo = desc.split(" / ", 1)[1].strip() if " / " in desc else ""
    return {
        "paid_on": str(row.get("paid_on") or "")[:10],
        "ref": memo,
        "payee": payee,
        "memo": memo,
        "payment": abs(amount) if amount < 0 else 0.0,
        "deposit": amount if amount > 0 else 0.0,
        "amount": amount,
        "balance": row.get("balance"),
        "qb_type": "",
        "account": f"FNB {ACCOUNT}",
        "bank_status": "",
        "source": row.get("source") or "fnb_live",
        "description": desc,
        "account_number": row.get("account_number") or ACCOUNT,
        "account_name": row.get("account_name") or COMPANY["bank_account_name"],
        "ours": 1,
        "filename": row.get("filename") or "fnb-live",
    }


def _live_client(row: dict):
    from billing import CLIENTS, canon_key, client_row

    blob = f"{row.get('payee') or ''} {row.get('memo') or ''} {row.get('description') or ''}"
    hit = client_row(blob)
    if hit:
        return hit
    words = [
        w
        for w in re.findall(r"[A-Za-z']+", blob)
        if w.lower() not in BANK_WORDS and len(w) > 1
    ]
    for guess in ((" ".join(words[-2:]) if len(words) >= 2 else ""), words[-1] if words else ""):
        if not guess:
            continue
        hit = client_row(guess)
        if hit:
            return hit
        key = canon_key(guess)
        hits = [c for c in CLIENTS if key and key in canon_key(c["name"])]
        if len(hits) == 1:
            return hits[0]
    return None


def allocate_live(row: dict) -> dict:
    from recon import _fnb_alloc

    alloc = _fnb_alloc(row)
    blob = f"{row.get('payee') or ''} {row.get('memo') or ''} {row.get('description') or ''}".lower()
    client = _live_client(row)
    if alloc.get("alloc_kind") == "unallocated" and client and (row.get("deposit") or 0) > 0.004:
        return {
            "alloc_kind": "client_paid",
            "alloc_to": client["name"],
            "alloc_key": "",
            "result": "allocated",
        }
    if alloc.get("alloc_kind") == "unallocated":
        if any(w in blob for w in FEE_WORDS):
            return {
                "alloc_kind": "fee",
                "alloc_to": "FNB bank charge",
                "alloc_key": "",
                "result": "allocated",
            }
        if any(w in blob for w in EXPENSE_WORDS):
            return {
                "alloc_kind": "expense",
                "alloc_to": row.get("payee") or row.get("description"),
                "alloc_key": "",
                "result": "allocated",
            }
        if "netcash" in blob:
            return {
                "alloc_kind": "clearing",
                "alloc_to": "Netcash",
                "alloc_key": "",
                "result": "allocated",
            }
        if (row.get("deposit") or 0) > 0.004:
            return {
                "alloc_kind": "deposit",
                "alloc_to": row.get("payee") or "FNB credit",
                "alloc_key": "",
                "result": "need-recon",
                "what": f"{row.get('payee') or row.get('description') or 'Unknown credit'} · needs recon",
            }
    return alloc


def insert_new(conn: sqlite3.Connection, rows: list[dict]) -> dict:
    """Add only rows not already on the FNB tables. Allocate each new one."""
    from books import ensure_tables
    from recon import ensure as ensure_fnb

    ensure_tables(conn)
    ensure_fnb(conn)
    have = existing_keys(conn)
    inserted = 0
    allocated = 0
    attention: list[dict] = []
    for raw in rows:
        if (raw.get("source") or "") in QB_SOURCES:
            continue
        rec = to_fnb_row(raw)
        key = row_key(rec)
        if key in have:
            continue
        have.add(key)
        alloc = allocate_live(rec)
        rec.update(alloc)
        conn.execute(
            """INSERT OR IGNORE INTO bank_tx
               (account_number, account_name, ours, paid_on, amount, balance, description, source, filename)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                rec["account_number"],
                rec["account_name"],
                1,
                rec["paid_on"],
                rec["amount"],
                rec.get("balance"),
                rec.get("description"),
                rec.get("source") or "fnb_live",
                rec.get("filename"),
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO fnb_tx
               (paid_on, ref, payee, memo, payment, deposit, amount, balance, qb_type,
                account, bank_status, alloc_kind, alloc_to, alloc_key, result, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec["paid_on"],
                rec.get("ref"),
                rec.get("payee"),
                rec.get("memo"),
                rec.get("payment"),
                rec.get("deposit"),
                rec["amount"],
                rec.get("balance"),
                rec.get("qb_type"),
                rec.get("account"),
                rec.get("bank_status"),
                alloc["alloc_kind"],
                alloc["alloc_to"],
                alloc.get("alloc_key") or "",
                alloc["result"],
                rec.get("source") or "fnb_live",
            ),
        )
        inserted += 1
        if alloc.get("result") == "allocated":
            allocated += 1
        else:
            attention.append(
                {
                    "paid_on": rec["paid_on"],
                    "description": rec.get("description"),
                    "amount": rec["amount"],
                    "kind": alloc.get("alloc_kind") or "unallocated",
                    "what": alloc.get("what")
                    or alloc.get("alloc_to")
                    or rec.get("payee")
                    or "Needs recon",
                }
            )
    conn.commit()
    return {
        "inserted": inserted,
        "allocated": allocated,
        "need_recon": len(attention),
        "need_recon_amount": round(sum(abs(float(a["amount"])) for a in attention), 2),
        "attention": attention,
    }


def _record_fetch(conn: sqlite3.Connection, pack: dict) -> None:
    conn.executescript(FETCH_SCHEMA)
    conn.execute(
        """INSERT INTO fnb_fetch
           (fetched_at, rows_seen, inserted, allocated, need_recon, need_recon_amount,
            balance, ok, note)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            pack.get("fetched_at"),
            pack.get("rows_seen") or 0,
            pack.get("inserted") or 0,
            pack.get("allocated") or 0,
            pack.get("need_recon") or 0,
            pack.get("need_recon_amount") or 0,
            pack.get("balance"),
            1 if pack.get("ok") else 0,
            pack.get("note") or "",
        ),
    )
    conn.commit()


def last_fetch(conn: sqlite3.Connection | None = None) -> dict | None:
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    try:
        own.executescript(FETCH_SCHEMA)
        rec = own.execute(
            """SELECT fetched_at, rows_seen, inserted, allocated, need_recon,
                      need_recon_amount, balance, ok, note
               FROM fnb_fetch ORDER BY id DESC LIMIT 1"""
        ).fetchone()
    except sqlite3.OperationalError:
        rec = None
    if conn is None:
        own.close()
    if not rec:
        return None
    return {
        "fetched_at": rec[0],
        "rows_seen": rec[1],
        "inserted": rec[2],
        "allocated": rec[3],
        "need_recon": rec[4],
        "need_recon_amount": rec[5],
        "balance": rec[6],
        "ok": bool(rec[7]),
        "note": rec[8],
    }


def attention_open(conn: sqlite3.Connection) -> list[dict]:
    out = []
    try:
        for rec in conn.execute(
            """SELECT paid_on, payee, memo, amount, alloc_kind, alloc_to, result
               FROM fnb_tx
               WHERE source IN ('fnb_live','fnb_online','fnb_api')
                 AND (result='need-recon' OR alloc_kind='unallocated')
               ORDER BY paid_on DESC, id DESC LIMIT 40"""
        ):
            out.append(
                {
                    "paid_on": rec[0],
                    "description": " / ".join(p for p in (rec[1], rec[2]) if p),
                    "amount": rec[3],
                    "kind": rec[4],
                    "what": rec[5] or "Needs recon",
                }
            )
    except sqlite3.OperationalError:
        return []
    return out


def _dismiss_popups(page) -> int:
    """Login sometimes has a popup, sometimes not. Never fail if none."""
    closed = 0
    for _ in range(4):
        labels = []
        try:
            labels = page.locator(
                "button, [role='button'], a, [aria-label='Close'], .close, .modal-close"
            ).all_text_contents()
        except Exception:
            labels = []
        extra = []
        try:
            extra = page.locator("[aria-label]").evaluate_all(
                "els => els.map(e => e.getAttribute('aria-label') || '')"
            )
        except Exception:
            extra = []
        choice = pick_dismiss([*(labels or []), *(extra or [])])
        if not choice:
            break
        try:
            loc = page.get_by_role("button", name=re.compile(re.escape(choice), re.I))
            if loc.count():
                loc.first.click(timeout=1500)
                closed += 1
                page.wait_for_timeout(400)
                continue
        except Exception:
            pass
        try:
            page.locator("button, [aria-label='Close'], .close").filter(
                has_text=re.compile(re.escape(choice), re.I)
            ).first.click(timeout=1500)
            closed += 1
            page.wait_for_timeout(400)
        except Exception:
            break
    return closed


def _fill_login(page, username: str, password: str) -> None:
    user_sel = (
        "input[name='username'], input[name='user'], input#username, "
        "input[type='text'][id*='user' i], input[autocomplete='username']"
    )
    pass_sel = "input[type='password'], input[name='password'], input#password"
    page.wait_for_timeout(500)
    if page.locator(user_sel).count():
        page.locator(user_sel).first.fill(username)
    else:
        page.get_by_label(re.compile("user", re.I)).first.fill(username)
    if page.locator(pass_sel).count():
        page.locator(pass_sel).first.fill(password)
    else:
        page.get_by_label(re.compile("pass", re.I)).first.fill(password)
    clicked = False
    for name in ("Log on", "Log in", "Login", "Sign in", "Continue"):
        try:
            btn = page.get_by_role("button", name=re.compile(name, re.I))
            if btn.count():
                btn.first.click()
                clicked = True
                break
        except Exception:
            continue
    if not clicked:
        page.locator(pass_sel).first.press("Enter")


def _open_statement(page, account: str) -> None:
    for name in (
        "Accounts",
        "My Bank Accounts",
        "Bank accounts",
        "Transactional",
        "Account summary",
    ):
        try:
            link = page.get_by_role("link", name=re.compile(name, re.I))
            if link.count():
                link.first.click(timeout=3000)
                page.wait_for_timeout(600)
                _dismiss_popups(page)
                break
        except Exception:
            continue
    try:
        acc = page.get_by_text(account)
        if acc.count():
            acc.first.click(timeout=4000)
            page.wait_for_timeout(600)
    except Exception:
        pass
    for name in (
        "Transaction history",
        "Transactions",
        "Live statement",
        "Statement",
        "Account activity",
    ):
        try:
            link = page.get_by_role("link", name=re.compile(name, re.I))
            if link.count():
                link.first.click(timeout=3000)
                page.wait_for_timeout(800)
                _dismiss_popups(page)
                break
            btn = page.get_by_role("button", name=re.compile(name, re.I))
            if btn.count():
                btn.first.click(timeout=3000)
                page.wait_for_timeout(800)
                break
        except Exception:
            continue


def _read_page_rows(page) -> list[dict]:
    from books import parse_fnb_history, parse_fnb_online_table

    text = page.inner_text("body")
    parsed = parse_fnb_online_table(text, "fnb-live")
    rows = parsed.get("rows") or []
    if not rows:
        parsed = parse_fnb_history(text, "fnb-live")
        rows = parsed.get("rows") or []
    for row in rows:
        row["source"] = "fnb_live"
        row["account_number"] = row.get("account_number") or ACCOUNT
        row["account_name"] = row.get("account_name") or COMPANY["bank_account_name"]
        row["ours"] = 1
        row["filename"] = "fnb-live"
    if rows:
        return rows
    # Table scrape when FNB paints a real HTML table.
    tables = page.locator("table").all()
    out = []
    for table in tables:
        try:
            html_text = table.inner_text()
        except Exception:
            continue
        parsed = parse_fnb_online_table(html_text, "fnb-live")
        if parsed.get("rows"):
            for row in parsed["rows"]:
                row["source"] = "fnb_live"
            out.extend(parsed["rows"])
    return out


def fetch_live(env: dict[str, str] | None = None) -> dict:
    env = env or _load_env()
    user = (env.get("FNB_USERNAME") or "").strip()
    password = (env.get("FNB_PASSWORD") or "").strip()
    account = (env.get("FNB_ACCOUNT_NUMBER") or ACCOUNT).strip()
    if not user or not password:
        return {"ok": False, "error": "FNB username/password missing in /root/secrets/fnb.env", "rows": []}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "error": "playwright not installed on the box", "rows": []}
    rows: list[dict] = []
    note = ""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        last = ""
        for url in LOGIN_URLS:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                last = url
                break
            except Exception as exc:
                last = f"{url}: {exc}"
                continue
        try:
            _fill_login(page, user, password)
            page.wait_for_timeout(2500)
            _dismiss_popups(page)
            page.wait_for_timeout(800)
            _dismiss_popups(page)
            _open_statement(page, account)
            page.wait_for_timeout(1200)
            _dismiss_popups(page)
            rows = _read_page_rows(page)
            note = f"live {last} rows={len(rows)}"
        except Exception as exc:
            note = f"live-failed: {exc}"
            rows = []
        browser.close()
    return {"ok": bool(rows), "rows": rows, "note": note, "via": "fnb-live"}


def pull(conn: sqlite3.Connection | None = None) -> dict:
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    fetched_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    live = fetch_live()
    rows = live.get("rows") or []
    added = insert_new(own, rows)
    balance = None
    if rows:
        with_bal = [r for r in rows if r.get("balance") is not None]
        if with_bal:
            balance = with_bal[0].get("balance")
    if balance is None:
        try:
            rec = own.execute(
                """SELECT balance FROM bank_tx WHERE ours=1 AND source IN ('fnb_live','fnb_online','fnb_api')
                   ORDER BY paid_on DESC, id DESC LIMIT 1"""
            ).fetchone()
            balance = rec[0] if rec else None
        except sqlite3.OperationalError:
            balance = None
    pack = {
        "ok": bool(live.get("ok") or added.get("inserted")),
        "via": "fnb-live",
        "fetched_at": fetched_at,
        "rows_seen": len(rows),
        "inserted": added["inserted"],
        "allocated": added["allocated"],
        "need_recon": added["need_recon"],
        "need_recon_amount": added["need_recon_amount"],
        "attention": added["attention"],
        "balance": balance,
        "note": live.get("note") or live.get("error") or "",
        "error": None if live.get("ok") or rows else (live.get("error") or live.get("note")),
    }
    _record_fetch(own, pack)
    if conn is None:
        own.close()
    return pack


def _when_label(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return iso


def system_balance(conn: sqlite3.Connection) -> float | None:
    for sql in (
        """SELECT balance FROM bank_tx
           WHERE ours=1 AND source IN ('fnb_live','fnb_online','fnb_api','fnb_history')
           ORDER BY paid_on DESC, id DESC LIMIT 1""",
        """SELECT balance FROM fnb_tx
           WHERE source IN ('fnb_live','fnb_online','fnb_api')
           ORDER BY paid_on DESC, id DESC LIMIT 1""",
    ):
        try:
            rec = conn.execute(sql).fetchone()
        except sqlite3.OperationalError:
            rec = None
        if rec and rec[0] is not None:
            try:
                return round(float(rec[0]), 2)
            except (TypeError, ValueError):
                return None
    return None


def card_overlay(conn: sqlite3.Connection | None = None) -> dict:
    """Last fetch + unmatched items for the FNB card."""
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB))
    fetch = last_fetch(own) or {}
    attention = attention_open(own)
    need_amt = round(sum(abs(float(a.get("amount") or 0)) for a in attention), 2)
    bal = system_balance(own)
    if conn is None:
        own.close()
    return {
        "last_fetched": fetch.get("fetched_at"),
        "last_fetched_label": _when_label(fetch.get("fetched_at")),
        "last_inserted": fetch.get("inserted") or 0,
        "last_ok": fetch.get("ok"),
        "system_balance": bal,
        "matched": need_amt <= 0.004,
        "attention": attention,
        "attention_amount": need_amt,
        "daily": "Daily autofetch 06:15 SAST",
    }


def self_test() -> int:
    failed = 0
    if pick_dismiss([]) is not None:
        print("FAIL no-popup")
        failed += 1
    elif pick_dismiss(["Apply now", "Buy"]) is not None:
        print("FAIL unsafe-popup")
        failed += 1
    elif pick_dismiss(["What's new", "Close"]) != "Close":
        print("FAIL dismiss-close", pick_dismiss(["What's new", "Close"]))
        failed += 1
    elif pick_dismiss(["Got it"]) != "Got it":
        print("FAIL dismiss-got-it")
        failed += 1
    else:
        print("OK popup-optional")
    from books import ensure_tables
    from recon import ensure

    conn = sqlite3.connect(":memory:")
    ensure_tables(conn)
    ensure(conn)
    first = [
        {
            "paid_on": "2026-10-05",
            "amount": -520.0,
            "balance": 4554.66,
            "description": "PAYFAST*Host Africa Oct",
            "source": "fnb_live",
        },
        {
            "paid_on": "2026-10-01",
            "amount": -2223.94,
            "balance": 5074.66,
            "description": "RSAWEB 436784018 NETCASH",
            "source": "fnb_live",
        },
        {
            "paid_on": "2026-09-30",
            "amount": 329.0,
            "balance": 7298.60,
            "description": "CAPITEC P PEARSON",
            "source": "fnb_live",
        },
    ]
    a = insert_new(conn, first)
    b = insert_new(conn, first)
    n = conn.execute("SELECT COUNT(*) FROM bank_tx").fetchone()[0]
    fn = conn.execute("SELECT COUNT(*) FROM fnb_tx WHERE source='fnb_live'").fetchone()[0]
    kinds = {
        r[0]: r[1]
        for r in conn.execute("SELECT payee, alloc_kind FROM fnb_tx WHERE source='fnb_live'")
    }
    if a["inserted"] != 3 or b["inserted"] != 0 or n != 3 or fn != 3:
        print("FAIL dedup", a, b, n, fn)
        failed += 1
    elif kinds.get("PAYFAST*Host Africa Oct") != "expense":
        print("FAIL alloc-payfast", kinds)
        failed += 1
    elif kinds.get("RSAWEB 436784018 NETCASH") != "clearing":
        print("FAIL alloc-netcash", kinds)
        failed += 1
    elif kinds.get("CAPITEC P PEARSON") != "client_paid":
        print("FAIL alloc-pearson", kinds)
        failed += 1
    else:
        print("OK dedup-and-alloc")
    mystery = insert_new(
        conn,
        [
            {
                "paid_on": "2026-10-06",
                "amount": 88.0,
                "balance": 4642.66,
                "description": "UNKNOWN CREDIT XYZ",
                "source": "fnb_live",
            }
        ],
    )
    if mystery["need_recon"] != 1 or mystery["need_recon_amount"] != 88:
        print("FAIL attention", mystery)
        failed += 1
    else:
        print("OK needs-attention", mystery["attention"][0]["what"])
    overlay = card_overlay(conn)
    if overlay["matched"] or overlay["attention_amount"] != 88 or overlay["system_balance"] != 4642.66:
        print("FAIL overlay", overlay)
        failed += 1
    else:
        print("OK card-overlay-attention")
    live_before = conn.execute("SELECT COUNT(*) FROM fnb_tx WHERE source='fnb_live'").fetchone()[0]
    conn.execute(
        "DELETE FROM fnb_tx WHERE COALESCE(source,'') NOT IN ('fnb_live','fnb_online','fnb_api')"
    )
    live_after = conn.execute("SELECT COUNT(*) FROM fnb_tx WHERE source='fnb_live'").fetchone()[0]
    if live_before != live_after or live_after != 4:
        print("FAIL preserve-live", live_before, live_after)
        failed += 1
    else:
        print("OK preserve-live")
    conn.close()
    return failed


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "test":
        raise SystemExit(self_test())
    if cmd == "pull":
        print(json.dumps(pull(), indent=2))
    elif cmd == "last":
        print(json.dumps(last_fetch(), indent=2))
    else:
        print(json.dumps({"ready": login_ready(), "via": "fnb-live"}, indent=2))
