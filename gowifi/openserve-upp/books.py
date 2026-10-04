#!/usr/bin/env python3
"""Simple GoWiFi books: Openserve + FNB + Netcash. No QuickBooks.

Money in:  we invoice → Netcash debit order → FNB credit
Money out: Openserve statement → FNB debit (and fees)
"""
from __future__ import annotations

import csv
import email
import io
import os
import re
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

from company import COMPANY, GOWIFI_FNB

MAIL_ROOT = Path(os.environ.get("MAIL_ROOT", "/home/user-data/mail/mailboxes"))
NETCASH_ENV = Path(os.environ.get("NETCASH_ENV", "/root/secrets/netcash.env"))
# Floor only. Live series continues after the highest imported QuickBooks invoice.
INVOICE_SERIES_AFTER = 3039

SCHEMA = """
CREATE TABLE IF NOT EXISTS bank_tx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    account_name TEXT,
    ours INTEGER NOT NULL DEFAULT 0,
    paid_on TEXT NOT NULL,
    amount REAL NOT NULL,
    balance REAL,
    description TEXT,
    source TEXT,
    filename TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_tx_dedup
    ON bank_tx (
        COALESCE(account_number, ''),
        paid_on,
        amount,
        COALESCE(description, '')
    );
CREATE TABLE IF NOT EXISTS customer_invoices (
    invoice_number INTEGER PRIMARY KEY,
    invoice_date TEXT,
    service_number TEXT,
    customer TEXT,
    period TEXT,
    amount REAL,
    vat REAL,
    status TEXT,
    source TEXT
);
CREATE TABLE IF NOT EXISTS netcash_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_ref TEXT,
    service_number TEXT,
    amount REAL,
    action_date TEXT,
    result TEXT,
    batch_id TEXT,
    source TEXT
);
"""


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def is_gowifi_account(name: str | None, number: str | None) -> bool:
    blob = f"{name or ''} {number or ''}".lower()
    return (
        "gowifi" in blob
        or "go-wifi" in blob
        or "go wifi" in blob
        or (number or "").replace(" ", "") == GOWIFI_FNB
    )


def parse_fnb_history(text: str, filename: str = "") -> dict:
    """FNB Online 'ACCOUNT TRANSACTION HISTORY' CSV (Date, Amount, Balance, Description)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    account_number = None
    account_name = None
    rows = []
    in_tx = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith("account:"):
            parts = [p.strip() for p in line.split(",")]
            digits = re.findall(r"\d{8,}", line)
            account_number = digits[0] if digits else None
            bracket = re.search(r"\[([^\]]+)\]", line)
            account_name = bracket.group(1).strip() if bracket else (parts[-1] if len(parts) > 2 else None)
        if line.lower().startswith("date,") and "amount" in line.lower():
            in_tx = True
            continue
        if not in_tx:
            continue
        try:
            rec = next(csv.reader([line]))
        except csv.Error:
            continue
        if len(rec) < 4:
            continue
        paid_on, amount, balance, desc = rec[0].strip(), rec[1].strip(), rec[2].strip(), rec[3].strip()
        if not re.match(r"\d{4}/\d{2}/\d{2}", paid_on):
            continue
        rows.append(
            {
                "account_number": account_number,
                "account_name": account_name,
                "ours": 1 if is_gowifi_account(account_name, account_number) else 0,
                "paid_on": paid_on.replace("/", "-"),
                "amount": float(amount.replace(" ", "")),
                "balance": float(balance.replace(" ", "")) if balance else None,
                "description": desc,
                "source": "fnb_history",
                "filename": filename,
            }
        )
    return {
        "account_number": account_number,
        "account_name": account_name,
        "ours": 1 if is_gowifi_account(account_name, account_number) else 0,
        "rows": rows,
    }


def _upsert_bank(conn: sqlite3.Connection, rows: list[dict]) -> int:
    n = 0
    for row in rows:
        cur = conn.execute(
            """INSERT OR IGNORE INTO bank_tx
               (account_number, account_name, ours, paid_on, amount, balance, description, source, filename)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                row.get("account_number"),
                row.get("account_name"),
                row.get("ours") or 0,
                row["paid_on"],
                row["amount"],
                row.get("balance"),
                row.get("description"),
                row.get("source") or "fnb_history",
                row.get("filename"),
            ),
        )
        n += cur.rowcount or 0
    return n


def _iter_mail_files() -> list[Path]:
    if not MAIL_ROOT.exists():
        return []
    out = []
    for path in MAIL_ROOT.rglob("*"):
        if path.is_file() and path.parent.name in {"cur", "new"} and "dovecot" not in path.name:
            out.append(path)
    return out


def ingest_fnb_mail(conn: sqlite3.Connection) -> dict:
    """Pull FNB transaction-history zip/csv attachments from box mail."""
    ensure_tables(conn)
    files = 0
    inserted = 0
    for path in _iter_mail_files():
        try:
            msg = email.message_from_bytes(path.read_bytes())
        except Exception:
            continue
        for part in msg.walk():
            name = (part.get_filename() or "").strip()
            low = name.lower()
            if not name:
                continue
            payload = part.get_payload(decode=True) or b""
            texts: list[tuple[str, str]] = []
            if low.endswith(".zip"):
                try:
                    zf = zipfile.ZipFile(io.BytesIO(payload))
                except zipfile.BadZipFile:
                    continue
                for inner in zf.namelist():
                    if inner.lower().endswith(".csv"):
                        texts.append((inner, zf.read(inner).decode("utf-8-sig", "replace")))
            elif low.endswith(".csv") and ("transaction" in low or "fnb" in low or "history" in low):
                texts.append((name, payload.decode("utf-8-sig", "replace")))
            for fname, text in texts:
                if "ACCOUNT TRANSACTION HISTORY" not in text.upper() and "Date, Amount, Balance" not in text:
                    if "date" not in text.lower() or "amount" not in text.lower():
                        continue
                parsed = parse_fnb_history(text, fname)
                if not parsed["rows"]:
                    continue
                files += 1
                inserted += _upsert_bank(conn, parsed["rows"])
    conn.commit()
    return {"files": files, "inserted": inserted}


def netcash_status() -> dict:
    if NETCASH_ENV.exists():
        return {
            "ready": True,
            "note": "Service key on the box. Debit batches + unpaid reports via NIWS_NIF.",
        }
    return {
        "ready": False,
        "note": "Put the Netcash debit service key in /root/secrets/netcash.env. API is NIWS_NIF BatchFileUpload / RequestFileUploadReport.",
    }


def _last_rate(conn: sqlite3.Connection, customer: str | None) -> tuple[float | None, str | None]:
    if not customer:
        return None, None
    key = " ".join(customer.lower().split()[:2])
    try:
        rows = conn.execute(
            """SELECT customer, rate, amount, description FROM customer_invoices
               WHERE source LIKE 'quickbooks%' AND customer IS NOT NULL
               ORDER BY invoice_date DESC"""
        )
    except sqlite3.OperationalError:
        return None, None
    for rec in rows:
        other = " ".join((rec[0] or "").lower().split()[:2])
        if other and other == key:
            return rec[1] or rec[2], rec[3]
    return None, None


def draft_customer_invoices(conn: sqlite3.Connection, today: date | None = None) -> list[dict]:
    """One draft per active fibre line. Rate from last QuickBooks invoice for that client."""
    ensure_tables(conn)
    today = today or date.today()
    period = today.strftime("%Y-%m")
    rows = []
    try:
        services = conn.execute(
            """SELECT service_number FROM services
               WHERE exclusive_status='active' ORDER BY service_number"""
        ).fetchall()
    except sqlite3.OperationalError:
        services = []
    number = INVOICE_SERIES_AFTER
    try:
        last = conn.execute("SELECT MAX(invoice_number) FROM customer_invoices").fetchone()
        if last and last[0]:
            number = max(number, int(last[0]))
    except sqlite3.OperationalError:
        pass
    for svc in services:
        number += 1
        sn = svc[0]
        customer = None
        product = None
        try:
            order = conn.execute(
                """SELECT end_customer, product FROM orders
                   WHERE service_number=? ORDER BY created_on DESC LIMIT 1""",
                (sn,),
            ).fetchone()
            if order:
                customer, product = order[0], order[1]
        except sqlite3.OperationalError:
            pass
        rate, hist_desc = _last_rate(conn, customer)
        desc = hist_desc or (product or "Monthly service")
        rows.append(
            {
                "invoice_number": number,
                "invoice_date": today.isoformat(),
                "due_date": today.isoformat(),
                "service_number": sn,
                "customer": customer,
                "description": desc,
                "period": period,
                "qty": 1,
                "rate": rate,
                "amount": rate,
                "balance_due": rate,
                "terms": "Due on receipt",
                "status": "draft",
                "source": "gowifi",
            }
        )
    return rows


def books_for_export(conn: sqlite3.Connection) -> dict:
    ensure_tables(conn)
    ingest_fnb_mail(conn)
    from qb_import import history_for_export, ingest_qb_mail

    ingest_qb_mail(conn)
    history = history_for_export(conn)
    openserve = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(total),0) FROM invoices"
    ).fetchone()
    bank_accounts = []
    for row in conn.execute(
        """SELECT account_number, account_name, ours, COUNT(*), MIN(paid_on), MAX(paid_on)
           FROM bank_tx GROUP BY account_number, account_name, ours ORDER BY ours DESC, account_number"""
    ):
        bank_accounts.append(
            {
                "account_number": row[0],
                "account_name": row[1],
                "ours": bool(row[2]),
                "transactions": row[3],
                "from": row[4],
                "to": row[5],
            }
        )
    drafts = draft_customer_invoices(conn)
    from invoice_canned import statement_on_invoice

    all_inv = (history.get("invoices") or []) + drafts
    pays = history.get("payments") or []
    for row in drafts:
        row["statement"] = statement_on_invoice(all_inv, pays, row.get("customer"))
        if row["statement"].get("total_due") is not None:
            row["balance_due"] = row["statement"]["total_due"]
    nc = netcash_status()
    next_no = max(history.get("next") or INVOICE_SERIES_AFTER + 1, INVOICE_SERIES_AFTER + 1)
    if drafts:
        next_no = drafts[0]["invoice_number"]
    return {
        "quickbooks": "cancel after this history is on the box",
        "company": COMPANY,
        "loop": (
            "Old QuickBooks invoices and statements are imported from mail. "
            "New invoices are one page: this month’s line plus the statement history under it."
        ),
        "openserve": {
            "invoices": openserve[0] if openserve else 0,
            "charged": openserve[1] if openserve else 0,
        },
        "fnb": {
            "accounts": bank_accounts,
            "gowifi_account": any(a["ours"] for a in bank_accounts),
            "note": (
                "Daily CSV: FNB Online scheduled export to accounts@go-wifi.co.za "
                "(ACCOUNT TRANSACTION HISTORY). GoWiFi operating account not on the box yet."
                if not any(a["ours"] for a in bank_accounts)
                else "GoWiFi FNB history is on the box."
            ),
        },
        "netcash": nc,
        "customer_invoices": {
            "series_after_quickbooks": INVOICE_SERIES_AFTER,
            "next": next_no,
            "drafts": len(drafts),
            "rows": drafts,
            "note": "One page: invoice + statement. /dash/invoice.html",
        },
        "history": history,
    }


def self_test() -> int:
    failed = 0
    sample = (
        "ACCOUNT TRANSACTION HISTORY\n\n"
        "Name:, Kevin, Weaving\n"
        "Account:, 62353027016, [Smart Tracker Pty - Main]\n"
        "Balance:, 1.00, 2.00\n\n"
        "Date, Amount, Balance, Description\n"
        "2025/10/10, -1000.00, 92564.31, FLICKSWITCH MTRACK\n"
        "2025/10/08, 500.00, 93564.31, FNB OB PMT            CLIENT\n"
    )
    parsed = parse_fnb_history(sample, "test.csv")
    if parsed["ours"]:
        print("FAIL smart-tracker-not-ours", parsed)
        failed += 1
    elif len(parsed["rows"]) != 2 or parsed["rows"][0]["amount"] != -1000:
        print("FAIL parse", parsed)
        failed += 1
    else:
        print("OK fnb-history-parse")
    gowifi = parse_fnb_history(
        "ACCOUNT TRANSACTION HISTORY\nAccount:, 111, [GoWiFi Pty Ltd]\n\n"
        "Date, Amount, Balance, Description\n2026/01/02, 250.00, 250.00, NETCASH\n",
        "g.csv",
    )
    if not gowifi["ours"] or gowifi["rows"][0]["description"] != "NETCASH":
        print("FAIL gowifi-ours", gowifi)
        failed += 1
    else:
        print("OK gowifi-account")
    conn = sqlite3.connect(":memory:")
    ensure_tables(conn)
    conn.execute(
        "CREATE TABLE services (service_number TEXT, exclusive_status TEXT)"
    )
    conn.execute("INSERT INTO services VALUES ('B110033875','active')")
    drafts = draft_customer_invoices(conn, date(2026, 10, 4))
    if not drafts or drafts[0]["invoice_number"] != 3040:
        print("FAIL invoice-series", drafts)
        failed += 1
    else:
        print("OK invoice-series")
    if netcash_status()["ready"]:
        print("OK netcash-key-present")
    else:
        print("OK netcash-awaiting-key")
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
