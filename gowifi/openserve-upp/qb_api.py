#!/usr/bin/env python3
"""One-time read of GoWiFi QuickBooks Online invoices, customers, payments."""
from __future__ import annotations

import json
import os
import sqlite3
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from qb_import import _upsert_invoice, ensure_history_tables
from qb_oauth import access_token

DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
API = "https://quickbooks.api.intuit.com/v3/company"
PAGE = 1000


def _get(path: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        path,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"QBO {exc.code}: {exc.read().decode()[:400]}") from exc


def _query(realm: str, token: str, entity: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 1
    while True:
        sql = f"select * from {entity} STARTPOSITION {start} MAXRESULTS {PAGE}"
        url = f"{API}/{realm}/query?" + urllib.parse.urlencode({"query": sql})
        data = _get(url, token)
        chunk = (data.get("QueryResponse") or {}).get(entity) or []
        rows.extend(chunk)
        if len(chunk) < PAGE:
            break
        start += PAGE
    return rows


def _addr(blob: dict | None) -> str | None:
    if not blob:
        return None
    parts = [
        blob.get("Line1"),
        blob.get("Line2"),
        blob.get("City"),
        blob.get("CountrySubDivisionCode"),
        blob.get("PostalCode"),
        blob.get("Country"),
    ]
    text = ", ".join(str(p).strip() for p in parts if p)
    return text or None


def _lines(inv: dict) -> tuple[str | None, float | None, float | None]:
    desc = None
    qty = None
    rate = None
    for line in inv.get("Line") or []:
        if line.get("DetailType") != "SalesItemLineDetail":
            continue
        desc = line.get("Description") or desc
        detail = line.get("SalesItemLineDetail") or {}
        if detail.get("Qty") is not None:
            qty = float(detail["Qty"])
        if detail.get("UnitPrice") is not None:
            rate = float(detail["UnitPrice"])
        if desc:
            break
    return desc, qty, rate


def _invoice_number(inv: dict) -> int | None:
    raw = str(inv.get("DocNumber") or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def invoice_row(inv: dict) -> dict | None:
    number = _invoice_number(inv)
    if number is None:
        return None
    cust = ((inv.get("CustomerRef") or {}).get("name")) or None
    desc, qty, rate = _lines(inv)
    amount = inv.get("TotalAmt")
    return {
        "invoice_number": number,
        "invoice_date": inv.get("TxnDate"),
        "due_date": inv.get("DueDate"),
        "service_number": None,
        "customer": cust,
        "bill_to": cust,
        "address": _addr(inv.get("BillAddr")),
        "period": None,
        "description": desc,
        "qty": qty if qty is not None else 1,
        "rate": rate if rate is not None else amount,
        "amount": amount,
        "vat": None,
        "balance_due": inv.get("Balance"),
        "terms": ((inv.get("SalesTermRef") or {}).get("name")) or "Due on receipt",
        "status": "historical",
        "source": "quickbooks-api",
        "filename": f"qbo:{inv.get('Id')}",
    }


def pull(conn: sqlite3.Connection) -> dict[str, int]:
    ensure_history_tables(conn)
    token, realm = access_token()
    invoices = _query(realm, token, "Invoice")
    payments = _query(realm, token, "Payment")
    customers = _query(realm, token, "Customer")
    n_inv = 0
    for inv in invoices:
        row = invoice_row(inv)
        if not row:
            continue
        _upsert_invoice(conn, row)
        n_inv += 1
    n_pay = 0
    for pay in payments:
        cust = ((pay.get("CustomerRef") or {}).get("name")) or None
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, statement_number)
               VALUES (?,?,?,?,?,?)""",
            (
                pay.get("TxnDate"),
                cust,
                pay.get("TotalAmt"),
                pay.get("PrivateNote") or "QBO payment",
                "quickbooks-api",
                None,
            ),
        )
        n_pay += 1
    conn.commit()
    return {
        "invoices_read": len(invoices),
        "invoices_saved": n_inv,
        "payments_read": len(payments),
        "payments_saved": n_pay,
        "customers_read": len(customers),
        "realm": int(realm) if str(realm).isdigit() else 0,
    }


if __name__ == "__main__":
    db = sqlite3.connect(DB)
    print(json.dumps(pull(db), indent=2))
