#!/usr/bin/env python3
"""Pull old QuickBooks invoices and statements from box mail into books."""
from __future__ import annotations

import email
import hashlib
import os
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from books import SCHEMA, ensure_tables
from company import GOWIFI_FNB

MAIL_ROOT = Path(os.environ.get("MAIL_ROOT", "/home/user-data/mail/mailboxes"))
HISTORY_DIR = Path(os.environ.get("UPP_HISTORY", "/root/gowifi-upp/history"))
PDFTOTEXT = os.environ.get("PDFTOTEXT", "pdftotext")

EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS customer_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    customer TEXT,
    amount REAL,
    note TEXT,
    source TEXT,
    statement_number INTEGER
);
CREATE TABLE IF NOT EXISTS customer_statements (
    statement_number INTEGER PRIMARY KEY,
    statement_date TEXT,
    customer TEXT,
    total_due REAL,
    source TEXT,
    filename TEXT
);
CREATE TABLE IF NOT EXISTS package_prices (
    key TEXT PRIMARY KEY,
    description TEXT,
    rate REAL,
    source TEXT
);
"""


def ensure_history_tables(conn: sqlite3.Connection) -> None:
    ensure_tables(conn)
    conn.executescript(EXTRA_SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(customer_invoices)")}
    wanted = {
        "due_date": "TEXT",
        "bill_to": "TEXT",
        "address": "TEXT",
        "description": "TEXT",
        "qty": "REAL",
        "rate": "REAL",
        "balance_due": "REAL",
        "terms": "TEXT",
        "filename": "TEXT",
    }
    for name, typ in wanted.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE customer_invoices ADD COLUMN {name} {typ}")


def _money(text: str | None) -> float | None:
    if text is None:
        return None
    clean = re.sub(r"[R\s]", "", str(text)).replace(",", "")
    if not clean or clean == "-":
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def _iso(dmy: str | None) -> str | None:
    if not dmy:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(dmy.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_qb_invoice(text: str, filename: str = "") -> dict | None:
    if "INVOICE" not in text or "GoWifi" not in text:
        return None
    if re.search(r"^\s*Statement\b", text, re.I | re.M) and "INVOICE" not in text[:400]:
        return None
    num = re.search(r"INVOICE\s+(\d{3,5})", text)
    if not num:
        return None
    date = re.search(r"DATE\s+(\d{2}/\d{2}/\d{4})", text)
    due = re.search(r"DUE DATE\s+(\d{2}/\d{2}/\d{4})", text)
    terms = re.search(r"TERMS\s+([A-Za-z0-9 /]+)", text)
    bal = re.search(r"BALANCE DUE\s+R?\s*([\d,.]+)", text)
    bill = []
    capture = False
    for line in text.splitlines():
        if "BILL TO" in line:
            capture = True
            after = line.split("BILL TO", 1)[1]
            after = re.split(r"INVOICE\s+\d+", after)[0].strip()
            if after:
                bill.append(after)
            continue
        if capture:
            if re.search(r"\bDATE\b.*ACTIVITY|QTY\s+RATE|AMOUNT", line):
                break
            if re.search(r"INVOICE\s+\d+|DATE\s+\d{2}/|TERMS\s+|DUE DATE", line):
                left = re.split(r"\s{2,}INVOICE|\s{2,}DATE|\s{2,}TERMS|\s{2,}DUE", line)[0].strip()
                if left:
                    bill.append(left)
                continue
            stripped = line.strip()
            if stripped:
                bill.append(stripped)
    customer = bill[0] if bill else None
    rates = re.findall(r"(\d[\d,]*\.\d{2})\s+(\d[\d,]*\.\d{2})\s*$", text, re.M)
    rate = _money(rates[-1][0]) if rates else None
    amount = _money(rates[-1][1]) if rates else _money(bal.group(1) if bal else None)
    desc = None
    for line in text.splitlines():
        if "Mbps" in line or "Fibre" in line or "Fiber" in line or "Uncapped" in line:
            desc = re.sub(r"\s+", " ", line).strip()[:160]
            break
    return {
        "invoice_number": int(num.group(1)),
        "invoice_date": _iso(date.group(1) if date else None),
        "due_date": _iso(due.group(1) if due else None),
        "customer": customer,
        "bill_to": customer,
        "address": ", ".join(bill[1:6]) if len(bill) > 1 else None,
        "description": desc,
        "qty": 1,
        "rate": rate,
        "amount": amount,
        "balance_due": _money(bal.group(1) if bal else None),
        "terms": (terms.group(1).strip() if terms else None),
        "status": "historical",
        "source": "quickbooks",
        "filename": filename,
    }


def parse_qb_statement(text: str, filename: str = "") -> dict | None:
    if "Statement" not in text or "STATEMENT NO" not in text.upper():
        return None
    num = re.search(r"STATEMENT NO\.?\s*(\d+)", text, re.I)
    date = re.search(r"DATE\s+(\d{2}/\d{2}/\d{4})", text)
    due = re.search(r"TOTAL DUE\s+R?\s*([\d,.]+)", text)
    customer = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*TO\b", line):
            rest = re.sub(r"^\s*TO\s*", "", line)
            rest = re.split(r"STATEMENT", rest, maxsplit=1)[0].strip()
            if rest:
                customer = rest
            elif i + 1 < len(lines):
                nxt = re.split(r"\s{2,}DATE|\s{2,}TOTAL", lines[i + 1])[0].strip()
                if nxt and not nxt.upper().startswith("DATE"):
                    customer = nxt
            break
    invoices = []
    payments = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        inv = re.search(
            r"^(\d{2}/\d{2}/\d{4}) Invoice No\.(\d+)(?::\s*(.*?))?\s+(-?[\d,.]+)\s+(-?[\d,.]+)$",
            line,
        )
        if inv:
            invoices.append(
                {
                    "invoice_number": int(inv.group(2)),
                    "invoice_date": _iso(inv.group(1)),
                    "customer": customer,
                    "description": (inv.group(3) or "").strip() or None,
                    "amount": _money(inv.group(4)),
                    "balance_due": _money(inv.group(5)),
                    "status": "historical",
                    "source": "quickbooks-statement",
                    "filename": filename,
                }
            )
            continue
        pay = re.search(r"^(\d{2}/\d{2}/\d{4}) Payment\s+(-[\d,.]+)", line)
        if pay:
            payments.append(
                {
                    "paid_on": _iso(pay.group(1)),
                    "customer": customer,
                    "amount": _money(pay.group(2)),
                    "note": "Payment",
                    "source": "quickbooks-statement",
                    "statement_number": int(num.group(1)) if num else None,
                }
            )
    return {
        "statement_number": int(num.group(1)) if num else None,
        "statement_date": _iso(date.group(1) if date else None),
        "customer": customer,
        "total_due": _money(due.group(1) if due else None),
        "source": "quickbooks",
        "filename": filename,
        "invoices": invoices,
        "payments": payments,
    }


def _pdf_text(path: Path) -> str:
    try:
        proc = subprocess.run(
            [PDFTOTEXT, "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout or ""


def _upsert_invoice(conn: sqlite3.Connection, row: dict) -> None:
    existing = conn.execute(
        "SELECT source FROM customer_invoices WHERE invoice_number=?",
        (row["invoice_number"],),
    ).fetchone()
    if existing and existing[0] == "quickbooks" and row.get("source") == "quickbooks-statement":
        return
    conn.execute(
        """INSERT INTO customer_invoices
           (invoice_number, invoice_date, due_date, service_number, customer, bill_to,
            address, period, description, qty, rate, amount, vat, balance_due, terms,
            status, source, filename)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(invoice_number) DO UPDATE SET
             invoice_date=COALESCE(excluded.invoice_date, invoice_date),
             due_date=COALESCE(excluded.due_date, due_date),
             customer=COALESCE(excluded.customer, customer),
             bill_to=COALESCE(excluded.bill_to, bill_to),
             address=COALESCE(excluded.address, address),
             description=COALESCE(excluded.description, description),
             qty=COALESCE(excluded.qty, qty),
             rate=COALESCE(excluded.rate, rate),
             amount=COALESCE(excluded.amount, amount),
             balance_due=COALESCE(excluded.balance_due, balance_due),
             terms=COALESCE(excluded.terms, terms),
             status=excluded.status,
             source=CASE WHEN customer_invoices.source='quickbooks' THEN customer_invoices.source ELSE excluded.source END,
             filename=COALESCE(excluded.filename, filename)""",
        (
            row["invoice_number"],
            row.get("invoice_date"),
            row.get("due_date"),
            row.get("service_number"),
            row.get("customer"),
            row.get("bill_to"),
            row.get("address"),
            row.get("period"),
            row.get("description"),
            row.get("qty"),
            row.get("rate"),
            row.get("amount"),
            row.get("vat"),
            row.get("balance_due"),
            row.get("terms"),
            row.get("status") or "historical",
            row.get("source") or "quickbooks",
            row.get("filename"),
        ),
    )
    if row.get("description") and row.get("rate"):
        key = re.sub(r"[^a-z0-9]+", "-", (row["description"] or "").lower())[:80]
        conn.execute(
            """INSERT INTO package_prices(key, description, rate, source)
               VALUES (?,?,?,?)
               ON CONFLICT(key) DO UPDATE SET rate=excluded.rate""",
            (key, row.get("description"), row.get("rate"), row.get("source")),
        )


def ingest_qb_mail(conn: sqlite3.Connection) -> dict:
    ensure_history_tables(conn)
    if not MAIL_ROOT.exists():
        return {"invoices": 0, "statements": 0, "payments": 0, "files": 0}
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    (HISTORY_DIR / "invoices").mkdir(exist_ok=True)
    seen = set()
    files = 0
    for path in MAIL_ROOT.rglob("*"):
        if not path.is_file() or path.parent.name not in {"cur", "new"} or "dovecot" in path.name:
            continue
        if path.stat().st_size > 15_000_000:
            continue
        try:
            msg = email.message_from_bytes(path.read_bytes())
        except Exception:
            continue
        subj = (msg.get("Subject") or "").lower()
        frm = (msg.get("From") or "").lower()
        for part in msg.walk():
            name = (part.get_filename() or "").strip()
            if not name.lower().endswith(".pdf"):
                continue
            low = name.lower()
            if not (
                "invoice_" in low
                or "statement_" in low
                or "from_gowifi" in low
                or "intuit" in frm
                or "invoice" in subj
                and "gowifi" in (subj + low)
            ):
                continue
            payload = part.get_payload(decode=True) or b""
            digest = hashlib.sha256(payload).hexdigest()[:16]
            if digest in seen or not payload.startswith(b"%PDF"):
                continue
            seen.add(digest)
            dest = HISTORY_DIR / "invoices" / f"{digest}_{name.replace('/', '_')}"
            dest.write_bytes(payload)
            text = _pdf_text(dest)
            if "OpenServe" in text or "INATS" in name.upper() or "BRINATS" in name.upper():
                continue
            files += 1
            inv = parse_qb_invoice(text, dest.name)
            if inv:
                _upsert_invoice(conn, inv)
                continue
            stmt = parse_qb_statement(text, dest.name)
            if not stmt:
                continue
            if stmt.get("statement_number"):
                conn.execute(
                    "DELETE FROM customer_payments WHERE statement_number=?",
                    (stmt["statement_number"],),
                )
                conn.execute(
                    """INSERT INTO customer_statements
                       (statement_number, statement_date, customer, total_due, source, filename)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(statement_number) DO UPDATE SET
                         total_due=excluded.total_due, customer=excluded.customer""",
                    (
                        stmt["statement_number"],
                        stmt.get("statement_date"),
                        stmt.get("customer"),
                        stmt.get("total_due"),
                        "quickbooks",
                        dest.name,
                    ),
                )
            for row in stmt.get("invoices") or []:
                _upsert_invoice(conn, row)
            for pay in stmt.get("payments") or []:
                conn.execute(
                    """INSERT INTO customer_payments
                       (paid_on, customer, amount, note, source, statement_number)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        pay.get("paid_on"),
                        pay.get("customer"),
                        pay.get("amount"),
                        pay.get("note"),
                        pay.get("source"),
                        pay.get("statement_number"),
                    ),
                )
    conn.commit()
    inv_n = conn.execute("SELECT COUNT(*) FROM customer_invoices").fetchone()[0]
    st_n = conn.execute("SELECT COUNT(*) FROM customer_statements").fetchone()[0]
    pay_n = conn.execute("SELECT COUNT(*) FROM customer_payments").fetchone()[0]
    return {"invoices": inv_n, "statements": st_n, "payments": pay_n, "files": files, "fnb": GOWIFI_FNB}


def history_for_export(conn: sqlite3.Connection) -> dict:
    ensure_history_tables(conn)
    invoices = [
        {
            "invoice_number": r[0],
            "invoice_date": r[1],
            "customer": r[2],
            "amount": r[3],
            "balance_due": r[4],
            "description": r[5],
            "source": r[6],
            "status": r[7],
        }
        for r in conn.execute(
            """SELECT invoice_number, invoice_date, customer, amount, balance_due,
                      description, source, status
               FROM customer_invoices ORDER BY invoice_number"""
        )
    ]
    last = invoices[-1]["invoice_number"] if invoices else 0
    return {
        "invoices": invoices,
        "count": len(invoices),
        "statements": conn.execute("SELECT COUNT(*) FROM customer_statements").fetchone()[0],
        "payments": conn.execute("SELECT COUNT(*) FROM customer_payments").fetchone()[0],
        "next": max(last, 3113) + 1,
        "fnb_account": GOWIFI_FNB,
    }


def self_test() -> int:
    failed = 0
    sample = """GoWifi (Pty) Ltd
INVOICE
BILL TO                                                                            INVOICE         2533
Mrs Marlene/Georg Van Eeden                                                        DATE            17/05/2025
Unit 1 - 63 6th Street                                                             TERMS           Due on receipt
Voelklip                                                                           DUE DATE        17/05/2025

                          Old - 7 Mbps down / 3.5 Mbps Up - Uncapped            1   399.00                 399.00
                                                                     BALANCE DUE                                    R197.00
  Account Number: 62860060278
"""
    inv = parse_qb_invoice(sample, "t.pdf")
    if not inv or inv["invoice_number"] != 2533 or inv["amount"] != 399:
        print("FAIL invoice", inv)
        failed += 1
    elif inv["customer"] != "Mrs Marlene/Georg Van Eeden":
        print("FAIL bill-to", inv)
        failed += 1
    else:
        print("OK qb-invoice")
    stmt = parse_qb_statement(
        """Statement
TO                                                            STATEMENT NO. 1369
Amoroc Doors                                                          DATE 18/09/2025
                                               TOTAL DUE R1,597.00
 17/03/2025               Invoice No.2477                                   199.00    199.00
 22/04/2025               Payment                                           -199.00   0.00
""",
        "s.pdf",
    )
    if not stmt or stmt["statement_number"] != 1369 or len(stmt["invoices"]) != 1:
        print("FAIL statement", stmt)
        failed += 1
    elif stmt["customer"] != "Amoroc Doors":
        print("FAIL statement-customer", stmt)
        failed += 1
    elif stmt["invoices"][0]["invoice_number"] != 2477 or stmt["payments"][0]["amount"] != -199:
        print("FAIL statement-rows", stmt)
        failed += 1
    else:
        print("OK qb-statement")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
