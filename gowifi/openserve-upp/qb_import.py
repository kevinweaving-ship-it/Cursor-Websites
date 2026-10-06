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
    from invoice_canned import clean_description

    desc = clean_description(desc)
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


def _left_col(line: str) -> str:
    return re.split(r"\s{2,}", (line or "").strip(), maxsplit=1)[0].strip()


def _blank(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _useful_description(text: str | None) -> str | None:
    from invoice_canned import clean_description

    cleaned = clean_description(text)
    if not cleaned or cleaned == "Monthly service":
        return None
    return cleaned


def _generic_description(text: str | None) -> bool:
    return _useful_description(text) is None


def _money_pair(text: str) -> tuple[float, float] | None:
    match = re.search(r"(-?[\d,.]+)\s+(-?[\d,.]+)\s*$", (text or "").strip())
    if not match:
        return None
    amount = _money(match.group(1))
    balance = _money(match.group(2))
    if amount is None or balance is None:
        return None
    return amount, balance


def _statement_invoice_line(line: str) -> dict | None:
    compact = re.sub(r"\s+", " ", line or "").strip()
    match = re.match(
        r"^(\d{2}/\d{2}/\d{4})\s+Invoice No\.(\d+)(?:[:\s]+(.*))?$",
        compact,
        re.I,
    )
    if not match:
        return None
    rest = (match.group(3) or "").strip()
    pair = _money_pair(rest)
    desc = rest
    if pair:
        desc = re.sub(r"(-?[\d,.]+)\s+(-?[\d,.]+)\s*$", "", rest).strip(" :-")
    return {
        "date": match.group(1),
        "invoice_number": int(match.group(2)),
        "description": _blank(desc),
        "amount": pair[0] if pair else None,
        "balance": pair[1] if pair else None,
    }


def fill_invoice_fields(invoices: list[dict]) -> list[dict]:
    """Recreate missing what-for / address from same-client known invoices."""
    from invoice_canned import clean_description, client_key

    known: dict[str, dict] = {}
    for inv in invoices:
        key = client_key(inv.get("customer"))
        if not key:
            continue
        bucket = known.setdefault(
            key, {"address": None, "by_rate": {}, "monthly": [], "rate_counts": {}}
        )
        address = _blank(inv.get("address"))
        if address and not bucket["address"]:
            bucket["address"] = address
        rate = inv.get("rate") if inv.get("rate") is not None else inv.get("amount")
        if rate is not None:
            rounded = round(float(rate), 2)
            bucket["rate_counts"][rounded] = bucket["rate_counts"].get(rounded, 0) + 1
        desc = clean_description(inv.get("description"))
        if _generic_description(desc):
            continue
        if rate is not None:
            bucket["by_rate"].setdefault(round(float(rate), 2), desc)
        if not re.match(r"(?i)install", desc):
            if desc not in bucket["monthly"]:
                bucket["monthly"].append(desc)

    for inv in invoices:
        key = client_key(inv.get("customer"))
        bucket = known.get(key) or {}
        if not _blank(inv.get("address")) and bucket.get("address"):
            inv["address"] = bucket["address"]
        desc = clean_description(inv.get("description"))
        if _generic_description(desc):
            rate = inv.get("rate") if inv.get("rate") is not None else inv.get("amount")
            filled = None
            rounded = round(float(rate), 2) if rate is not None else None
            if rounded is not None:
                filled = bucket.get("by_rate", {}).get(rounded)
            monthly = bucket.get("monthly") or []
            # Price-bumped monthly (399→439) can reuse the only known package.
            # One-off amounts (329, install) stay generic unless the statement said so.
            recurring = {
                amt for amt, n in (bucket.get("rate_counts") or {}).items() if n >= 2
            }
            if not filled and len(monthly) == 1 and rounded in recurring:
                filled = monthly[0]
            if filled:
                desc = filled
        inv["description"] = desc
        if inv.get("qty") is None:
            inv["qty"] = 1
        if inv.get("rate") is None and inv.get("amount") is not None:
            inv["rate"] = inv["amount"]
        if not _blank(inv.get("terms")):
            inv["terms"] = "Due on receipt"
        if not _blank(inv.get("due_date")):
            inv["due_date"] = inv.get("invoice_date")
        if not _blank(inv.get("bill_to")):
            inv["bill_to"] = inv.get("customer")
    return invoices


def _persist_filled_invoices(conn: sqlite3.Connection, invoices: list[dict]) -> int:
    updated = 0
    for inv in invoices:
        number = inv.get("invoice_number")
        if number is None:
            continue
        desc = _useful_description(inv.get("description"))
        cur = conn.execute(
            """UPDATE customer_invoices SET
                 address=CASE WHEN address IS NULL OR trim(address)='' THEN ? ELSE address END,
                 description=CASE
                   WHEN ? IS NOT NULL AND (
                     description IS NULL OR trim(description)='' OR description='Monthly service'
                   ) THEN ? ELSE description END,
                 qty=COALESCE(qty, ?),
                 rate=COALESCE(rate, ?),
                 terms=COALESCE(NULLIF(trim(COALESCE(terms,'')), ''), ?),
                 due_date=COALESCE(due_date, ?),
                 bill_to=COALESCE(NULLIF(trim(COALESCE(bill_to,'')), ''), ?)
               WHERE invoice_number=?""",
            (
                _blank(inv.get("address")),
                desc,
                desc,
                inv.get("qty") or 1,
                inv.get("rate") if inv.get("rate") is not None else inv.get("amount"),
                inv.get("terms") or "Due on receipt",
                inv.get("due_date") or inv.get("invoice_date"),
                inv.get("bill_to") or inv.get("customer"),
                number,
            ),
        )
        updated += cur.rowcount
    if updated:
        conn.commit()
    return updated


def recreate_invoices_from_statements(conn: sqlite3.Connection) -> int:
    """Every statement invoice number becomes a full invoice (what-for + amount)."""
    ensure_history_tables(conn)
    invoices = [
        {
            "invoice_number": r[0],
            "invoice_date": r[1],
            "due_date": r[2],
            "customer": r[3],
            "bill_to": r[4],
            "address": r[5],
            "description": r[6],
            "qty": r[7],
            "rate": r[8],
            "amount": r[9],
            "terms": r[10],
        }
        for r in conn.execute(
            """SELECT invoice_number, invoice_date, due_date, customer, bill_to, address,
                      description, qty, rate, amount, terms
               FROM customer_invoices ORDER BY invoice_number"""
        )
    ]
    fill_invoice_fields(invoices)
    return _persist_filled_invoices(conn, invoices)


def parse_qb_statement(text: str, filename: str = "") -> dict | None:
    if "Statement" not in text or "STATEMENT NO" not in text.upper():
        return None
    num = re.search(r"STATEMENT NO\.?\s*(\d+)", text, re.I)
    date = re.search(r"DATE\s+(\d{2}/\d{2}/\d{4})", text)
    due = re.search(r"TOTAL DUE\s+R?\s*([\d,.]+)", text)
    customer = None
    address_lines = []
    lines = text.splitlines()
    capture_to = False
    for i, line in enumerate(lines):
        if re.match(r"^\s*TO\b", line):
            rest = re.sub(r"^\s*TO\s*", "", line)
            rest = re.split(r"STATEMENT", rest, maxsplit=1)[0].strip()
            if rest:
                customer = rest
            capture_to = True
            continue
        if capture_to:
            if re.search(r"DATE\s+DESCRIPTION|AMOUNT\s+BALANCE", line, re.I):
                break
            if re.match(r"^\s*\d{2}/\d{2}/\d{4}", line):
                break
            if re.search(r"Invoice No\.|Balance Forward|^\s*Current\b", line, re.I):
                break
            left = _left_col(line)
            if not left or left.upper() in {"ENCLOSED", "DATE", "TOTAL DUE"}:
                continue
            if re.match(r"^DATE\b", left, re.I) or re.match(r"^TOTAL DUE\b", left, re.I):
                continue
            if customer is None:
                customer = left
            else:
                address_lines.append(left)
    address = ", ".join(address_lines) or None
    invoices = []
    payments = []
    i = 0
    while i < len(lines):
        line = re.sub(r"\s+", " ", lines[i]).strip()
        started = _statement_invoice_line(lines[i])
        if started:
            extra = []
            amount = started["amount"]
            balance = started["balance"]
            if started["description"]:
                extra.append(started["description"])
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if re.match(r"^\s*\d{2}/\d{2}/\d{4}", nxt) or re.match(r"^\s*Current\b", nxt, re.I):
                    break
                pair = _money_pair(re.sub(r"\s+", " ", nxt))
                if amount is None and pair:
                    amount, balance = pair
                    leftover = re.sub(r"(-?[\d,.]+)\s+(-?[\d,.]+)\s*$", "", nxt).strip()
                    left = _left_col(leftover) if leftover else ""
                    if left:
                        extra.append(left)
                    j += 1
                    continue
                left = _left_col(nxt)
                if left and not re.match(r"^(DATE|AMOUNT|BALANCE|Current)\b", left, re.I):
                    extra.append(left)
                j += 1
            desc = " ".join(x for x in extra if x) or None
            invoices.append(
                {
                    "invoice_number": started["invoice_number"],
                    "invoice_date": _iso(started["date"]),
                    "customer": customer,
                    "bill_to": customer,
                    "address": address,
                    "description": desc,
                    "qty": 1,
                    "rate": amount,
                    "amount": amount,
                    "balance_due": balance,
                    "terms": "Due on receipt",
                    "due_date": _iso(started["date"]),
                    "status": "historical",
                    "source": "quickbooks-statement",
                    "filename": filename,
                }
            )
            i = j
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
            i += 1
            continue
        fwd = re.search(r"^(\d{2}/\d{2}/\d{4}) Balance Forward\s+(-?[\d,.]+)\s*$", line)
        if fwd and _money(fwd.group(2)):
            payments.append(
                {
                    "paid_on": _iso(fwd.group(1)),
                    "customer": customer,
                    "amount": _money(fwd.group(2)),
                    "note": "Balance Forward",
                    "source": "quickbooks-statement",
                    "statement_number": int(num.group(1)) if num else None,
                }
            )
        i += 1
    return {
        "statement_number": int(num.group(1)) if num else None,
        "statement_date": _iso(date.group(1) if date else None),
        "customer": customer,
        "address": address,
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
        conn.execute(
            """UPDATE customer_invoices SET
                 address=CASE WHEN address IS NULL OR trim(address)='' THEN ? ELSE address END,
                 description=CASE
                   WHEN (description IS NULL OR trim(description)='' OR description='Monthly service')
                        AND ? IS NOT NULL THEN ? ELSE description END
               WHERE invoice_number=?""",
            (
                _blank(row.get("address")),
                _useful_description(row.get("description")),
                _useful_description(row.get("description")),
                row["invoice_number"],
            ),
        )
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
            _blank(row.get("customer")),
            _blank(row.get("bill_to")) or _blank(row.get("customer")),
            _blank(row.get("address")),
            row.get("period"),
            _useful_description(row.get("description")),
            row.get("qty") if row.get("qty") is not None else 1,
            row.get("rate") if row.get("rate") is not None else row.get("amount"),
            row.get("amount"),
            row.get("vat"),
            row.get("balance_due"),
            _blank(row.get("terms")) or "Due on receipt",
            row.get("status") or "historical",
            row.get("source") or "quickbooks",
            row.get("filename"),
        ),
    )
    useful = _useful_description(row.get("description"))
    if useful and row.get("rate"):
        key = re.sub(r"[^a-z0-9]+", "-", useful.lower())[:80]
        conn.execute(
            """INSERT INTO package_prices(key, description, rate, source)
               VALUES (?,?,?,?)
               ON CONFLICT(key) DO UPDATE SET rate=excluded.rate""",
            (key, useful, row.get("rate"), row.get("source")),
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
    recreate_invoices_from_statements(conn)
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
            "due_date": r[2],
            "customer": r[3],
            "address": r[4],
            "description": r[5],
            "qty": r[6],
            "rate": r[7],
            "amount": r[8],
            "balance_due": r[9],
            "terms": r[10],
            "source": r[11],
            "status": r[12],
        }
        for r in conn.execute(
            """SELECT invoice_number, invoice_date, due_date, customer, address,
                      description, qty, rate, amount, balance_due, terms, source, status
               FROM customer_invoices ORDER BY invoice_number"""
        )
    ]
    payments = [
        {
            "paid_on": r[0],
            "customer": r[1],
            "amount": r[2],
            "note": r[3] or "Payment",
        }
        for r in conn.execute(
            """SELECT paid_on, customer, amount, note FROM customer_payments
               ORDER BY paid_on, id"""
        )
    ]
    from invoice_canned import prepare_invoice

    fill_invoice_fields(invoices)
    _persist_filled_invoices(conn, invoices)
    for inv in invoices:
        inv.update(prepare_invoice(inv))
        inv.pop("statement", None)
    last = invoices[-1]["invoice_number"] if invoices else 0
    return {
        "invoices": invoices,
        "count": len(invoices),
        "payments": payments,
        "payment_count": len(payments),
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
 28/02/2025               Balance Forward                                             0.00
 17/03/2025               Invoice No.2477                                   199.00    199.00
 22/04/2025               Payment                                           -199.00   0.00
 29/02/2024               Balance Forward                                       1,197.00
""",
        "s.pdf",
    )
    if not stmt or stmt["statement_number"] != 1369 or len(stmt["invoices"]) != 1:
        print("FAIL statement", stmt)
        failed += 1
    elif stmt["customer"] != "Amoroc Doors":
        print("FAIL statement-customer", stmt)
        failed += 1
    elif stmt["invoices"][0]["invoice_number"] != 2477:
        print("FAIL statement-rows", stmt)
        failed += 1
    elif not any(p.get("note") == "Balance Forward" and p.get("amount") == 1197 for p in stmt["payments"]):
        print("FAIL balance-forward", stmt["payments"])
        failed += 1
    else:
        print("OK qb-statement")

    wrapped = parse_qb_statement(
        """Statement
TO                                                            STATEMENT NO. 1367
Mrs Jakobie Havenga                                                   DATE 18/09/2025
63 6th Street
Voelklip
                                               TOTAL DUE R1,500.00
 17/05/2025               Invoice No.2533                                   399.00    399.00
 18/08/2025               Invoice No.2585: Installation completed 29
                          August 2025 at Unit 1
                                                                    1,500.00  1,899.00
""",
        "wrap.pdf",
    )
    inst = (wrapped or {}).get("invoices") or []
    if (
        not wrapped
        or wrapped["customer"] != "Mrs Jakobie Havenga"
        or wrapped.get("address") != "63 6th Street, Voelklip"
        or len(inst) != 2
        or inst[1]["invoice_number"] != 2585
        or inst[1]["amount"] != 1500
        or "Installation completed 29 August 2025" not in (inst[1].get("description") or "")
    ):
        print("FAIL wrap-invoice", wrapped)
        failed += 1
    else:
        print("OK statement-recreate-wrap")

    conn = sqlite3.connect(":memory:")
    ensure_history_tables(conn)
    for row in (
        {
            "invoice_number": 2533,
            "invoice_date": "2025-05-17",
            "customer": "Mrs Marlene/Georg Van Eeden",
            "bill_to": "Mrs Marlene/Georg Van Eeden",
            "address": "Unit 1 - 63 6th Street, Voelklip",
            "description": "7 Mbps down / 3.5 Mbps Up",
            "qty": 1,
            "rate": 399,
            "amount": 399,
            "terms": "Due on receipt",
            "status": "historical",
            "source": "quickbooks",
            "filename": "inv.pdf",
        },
        {
            "invoice_number": 2373,
            "invoice_date": "2024-03-17",
            "customer": "Mrs Marlene/Georg Van Eeden",
            "amount": 399,
            "status": "historical",
            "source": "quickbooks-statement",
            "filename": "st.pdf",
        },
        {
            "invoice_number": 2585,
            "invoice_date": "2025-08-18",
            "customer": "Mrs Marlene/Georg Van Eeden",
            "description": "Installation completed 29 August 2025 at Unit 1",
            "amount": 1500,
            "status": "historical",
            "source": "quickbooks-statement",
            "filename": "st.pdf",
        },
        {
            "invoice_number": 3104,
            "invoice_date": "2026-08-20",
            "customer": "Mrs Marlene/Georg Van Eeden",
            "amount": 439,
            "status": "historical",
            "source": "quickbooks-statement",
            "filename": "st.pdf",
        },
        {
            "invoice_number": 3113,
            "invoice_date": "2026-09-21",
            "customer": "Mrs Marlene/Georg Van Eeden",
            "amount": 439,
            "status": "historical",
            "source": "quickbooks-statement",
            "filename": "st.pdf",
        },
        {
            "invoice_number": 3079,
            "invoice_date": "2026-07-17",
            "customer": "Mrs Marlene/Georg Van Eeden",
            "amount": 329,
            "status": "historical",
            "source": "quickbooks-statement",
            "filename": "st.pdf",
        },
        {
            "invoice_number": 2477,
            "invoice_date": "2025-03-17",
            "customer": "Amoroc Doors",
            "amount": 199,
            "status": "historical",
            "source": "quickbooks-statement",
            "filename": "st2.pdf",
        },
    ):
        _upsert_invoice(conn, row)
    conn.commit()
    recreate_invoices_from_statements(conn)
    hist = history_for_export(conn)
    by_n = {r["invoice_number"]: r for r in hist["invoices"]}
    if by_n[2373]["description"] != "7 Mbps down / 3.5 Mbps Up":
        print("FAIL backfill-desc", by_n[2373])
        failed += 1
    elif by_n[2373]["address"] != "Unit 1 - 63 6th Street, Voelklip":
        print("FAIL backfill-addr", by_n[2373])
        failed += 1
    elif by_n[3113]["description"] != "7 Mbps down / 3.5 Mbps Up":
        print("FAIL backfill-price-bump", by_n[3113])
        failed += 1
    elif by_n[3079]["description"] != "Monthly service":
        print("FAIL one-off-not-filled", by_n[3079])
        failed += 1
    elif "Installation" not in (by_n[2585]["description"] or ""):
        print("FAIL keep-install", by_n[2585])
        failed += 1
    elif by_n[2477]["description"] != "Monthly service":
        print("FAIL no-cross-client", by_n[2477])
        failed += 1
    elif by_n[2373]["qty"] != 1 or by_n[2373]["rate"] != 399:
        print("FAIL qty-rate", by_n[2373])
        failed += 1
    elif any(r.get("statement") for r in hist["invoices"]):
        print("FAIL history-has-qb-statement")
        failed += 1
    else:
        print("OK recreate-from-statement")
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
