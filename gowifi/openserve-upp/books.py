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
import sys
import zipfile
from datetime import date
from pathlib import Path

from company import COMPANY, GOWIFI_FNB
from invoice_canned import clean_description

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


_MONTHS = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def _fnb_money(raw: str) -> float | None:
    text = (raw or "").replace("\u00a0", " ").replace(",", "").replace(" ", "").strip()
    if not re.match(r"^-?\d+(\.\d+)?$", text):
        return None
    return float(text)


def _fnb_date(raw: str) -> str | None:
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$", (raw or "").strip())
    if not m:
        return None
    mon = _MONTHS.get(m.group(2)[:3].lower())
    if not mon:
        return None
    return f"{m.group(3)}-{mon}-{int(m.group(1)):02d}"


def parse_fnb_online_table(text: str, filename: str = "") -> dict:
    """FNB Online transaction table paste: Date, Description, Reference, Fee, Amount, Balance."""
    lines = [ln.replace("\u00a0", " ").rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    rows = []
    i = 0
    while i < len(lines):
        paid_on = _fnb_date(lines[i])
        if not paid_on:
            i += 1
            continue
        block = lines[i + 1 : i + 6]
        if len(block) < 5:
            break
        desc, ref, _fee, amount_s, balance_s = block
        amount = _fnb_money(amount_s)
        balance = _fnb_money(balance_s)
        if amount is None or balance is None:
            i += 1
            continue
        detail = desc.strip()
        if ref.strip():
            detail = f"{detail} / {ref.strip()}"
        rows.append(
            {
                "account_number": GOWIFI_FNB,
                "account_name": COMPANY["bank_account_name"],
                "ours": 1,
                "paid_on": paid_on,
                "amount": amount,
                "balance": balance,
                "description": detail,
                "source": "fnb_online",
                "filename": filename,
            }
        )
        i += 6
    return {
        "account_number": GOWIFI_FNB,
        "account_name": COMPANY["bank_account_name"],
        "ours": 1,
        "rows": rows,
    }


def ingest_fnb_text(conn: sqlite3.Connection, text: str, filename: str = "fnb-online") -> dict:
    ensure_tables(conn)
    parsed = parse_fnb_online_table(text, filename)
    if not parsed["rows"]:
        parsed = parse_fnb_history(text, filename)
        for row in parsed["rows"]:
            row["account_number"] = row.get("account_number") or GOWIFI_FNB
            row["account_name"] = row.get("account_name") or COMPANY["bank_account_name"]
            row["ours"] = 1 if is_gowifi_account(row.get("account_name"), row.get("account_number")) else row.get("ours") or 0
    inserted = _upsert_bank(conn, parsed["rows"])
    conn.commit()
    return {"rows": len(parsed["rows"]), "inserted": inserted}


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


def netcash_status(conn: sqlite3.Connection | None = None) -> dict:
    from netcash import items_for_export, status as nc_status

    out = nc_status()
    out["items"] = 0
    out["rows"] = []
    if conn is not None:
        try:
            rows = items_for_export(conn)
            out["items"] = len(rows)
            out["rows"] = rows
        except sqlite3.Error:
            pass
    return out


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
    """One draft per active fibre line, dated the 17th, month in advance."""
    ensure_tables(conn)
    from billing import invoice_day_on, period_for, period_label
    from invoice_canned import client_key

    today = today or date.today()
    inv_day = invoice_day_on(today)
    period = period_for(inv_day)
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
        desc = clean_description(
            hist_desc or product or f"Fibre {period_label(period)} (month in advance)"
        )
        already = False
        if customer:
            for rec in conn.execute(
                "SELECT customer FROM customer_invoices WHERE invoice_date=?",
                (inv_day.isoformat(),),
            ):
                if client_key(rec[0]) == client_key(customer):
                    already = True
                    break
        if already:
            continue
        rows.append(
            {
                "invoice_number": number,
                "invoice_date": inv_day.isoformat(),
                "due_date": inv_day.isoformat(),
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


def ingest_local_history(conn: sqlite3.Connection) -> dict:
    """Load the QuickBooks FNB Account History.csv sitting next to the app."""
    ensure_tables(conn)
    from ledger import ensure_ledger, ingest_qb_history

    ensure_ledger(conn)
    roots = [
        Path(os.environ.get("UPP_DATA", "/root/gowifi-upp/data")),
        Path(__file__).resolve().parent / "data",
    ]
    out = {"files": 0, "inserted": 0}
    seen: set[str] = set()
    for root in roots:
        paths = (
            list(root.glob("fnb-account-history*.csv"))
            + list(root.glob("netcash-account-history*.csv"))
        )
        for path in paths:
            if path.name in seen:
                continue
            seen.add(path.name)
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            got = ingest_qb_history(conn, text, path.name)
            out["files"] += 1
            out["inserted"] += got.get("inserted") or 0
    return out


def books_for_export(conn: sqlite3.Connection) -> dict:
    ensure_tables(conn)
    ingest_fnb_mail(conn)
    ingest_local_history(conn)
    from qb_import import history_for_export, ingest_qb_mail

    ingest_qb_mail(conn)
    from billing import run_cycle

    billing = run_cycle(conn)
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
    from invoice_canned import prepare_invoice, statement_on_invoice

    all_inv = (history.get("invoices") or []) + drafts
    pays = history.get("payments") or []
    for row in drafts:
        row.update(prepare_invoice(row))
        row["statement"] = statement_on_invoice(all_inv, pays, row.get("customer"))
        if row["statement"].get("total_due") is not None:
            row["balance_due"] = row["statement"]["total_due"]
    try:
        from netcash import pull as netcash_pull
        from netcash import status as nc_ready

        if nc_ready().get("ready"):
            netcash_pull(conn)
    except Exception:
        pass
    nc = netcash_status(conn)
    from ledger import ledger_for_export
    from packages import for_export as packages_for_export

    ledger = ledger_for_export(conn)
    packages = packages_for_export(conn)
    next_no = max(history.get("next") or INVOICE_SERIES_AFTER + 1, INVOICE_SERIES_AFTER + 1)
    if drafts:
        next_no = drafts[0]["invoice_number"]
    return {
        "quickbooks": "skip — FNB + Netcash + Openserve/UISP cover the books",
        "company": COMPANY,
        "ledger": ledger,
        "billing": billing.get("clients") if isinstance(billing, dict) else billing,
        "packages": packages,
        "loop": (
            "Invoice on the 17th, month in advance. D/O is loaded with the invoice "
            "and collected next month. Full D/O clears the client; Netcash fees "
            "come off the FNB settlement, not the invoice."
        ),
        "openserve": {
            "invoices": openserve[0] if openserve else 0,
            "charged": openserve[1] if openserve else 0,
        },
        "fnb": {
            "accounts": bank_accounts,
            "gowifi_account": any(a["ours"] for a in bank_accounts),
            "transactions": max(
                conn.execute("SELECT COUNT(*) FROM bank_tx WHERE ours=1").fetchone()[0],
                (ledger.get("bank") or {}).get("rows") or 0,
            ),
            "rows": [
                {
                    "paid_on": r[0],
                    "amount": r[1],
                    "balance": r[2],
                    "description": r[3],
                }
                for r in conn.execute(
                    """SELECT paid_on, amount, balance, description FROM bank_tx
                       WHERE ours=1 ORDER BY paid_on DESC, id DESC LIMIT 80"""
                )
            ],
            "note": (
                "QuickBooks FNB Account History (62860060278) from 27 Jul 2020. "
                "Expense and loan accounts recreated from the same register."
                if (ledger.get("bank") or {}).get("rows")
                else (
                    "Daily CSV: FNB Online scheduled export to accounts@go-wifi.co.za "
                    "(ACCOUNT TRANSACTION HISTORY). GoWiFi operating account not on the box yet."
                    if not any(a["ours"] for a in bank_accounts)
                    else "GoWiFi FNB history is on the box."
                )
            ),
        },
        "netcash": nc,
        "customer_invoices": {
            "series_after_quickbooks": INVOICE_SERIES_AFTER,
            "next": next_no,
            "drafts": len(drafts),
            "rows": drafts,
            "note": "One A4 page: invoice + statement of account. /dash/invoice.html",
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
    online = parse_fnb_online_table(
        "Date\nDescription\nReference\nService Fee\nAmount\nBalance\n"
        "01 Oct 2026\nRSAWEB 436784018 NETCASH\n\n0.00\n-2,223.94\n5,074.66\n"
        "01 Sep 2026\nNETCASH 431379977NETCASH\n431379977NETCASH\n0.00\n6,967.28\n13,649.29\n"
    )
    if (
        len(online["rows"]) != 2
        or online["rows"][0]["amount"] != -2223.94
        or online["rows"][0]["paid_on"] != "2026-10-01"
        or online["rows"][1]["amount"] != 6967.28
    ):
        print("FAIL fnb-online", online)
        failed += 1
    else:
        print("OK fnb-online-table")
    conn = sqlite3.connect(":memory:")
    ensure_tables(conn)
    conn.execute(
        "CREATE TABLE services (service_number TEXT, exclusive_status TEXT)"
    )
    conn.execute("INSERT INTO services VALUES ('B110033875','active')")
    drafts = draft_customer_invoices(conn, date(2026, 10, 4))
    if (
        not drafts
        or drafts[0]["invoice_number"] != 3040
        or drafts[0]["invoice_date"] != "2026-09-17"
        or drafts[0]["period"] != "2026-10"
    ):
        print("FAIL invoice-series", drafts)
        failed += 1
    else:
        print("OK invoice-series")
    from billing import self_test as billing_test

    failed += billing_test()
    if netcash_status()["ready"]:
        print("OK netcash-key-present")
    else:
        print("OK netcash-awaiting-key")
    from ledger import self_test as ledger_test
    from packages import self_test as packages_test

    failed += ledger_test()
    failed += packages_test()
    conn.close()
    return failed


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest-fnb":
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        if not path or not path.exists():
            raise SystemExit("ingest-fnb FILE")
        db = sqlite3.connect(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
        print(ingest_fnb_text(db, path.read_text(), path.name))
        raise SystemExit(0)
    raise SystemExit(self_test())
