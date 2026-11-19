#!/usr/bin/env python3
"""One-time read of GoWiFi QuickBooks Online invoices, customers, payments."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from qb_import import _upsert_invoice, ensure_history_tables
from qb_oauth import TOKEN_PATH, access_token, load_tokens, save_tokens

DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
API_PROD = "https://quickbooks.api.intuit.com/v3/company"
API_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"
PAGE = 1000


def _hosts() -> list[tuple[str, str]]:
    preferred = None
    if TOKEN_PATH.exists():
        try:
            preferred = load_tokens().get("api_host")
        except Exception:
            preferred = None
    order = [("production", API_PROD), ("sandbox", API_SANDBOX)]
    if preferred == "sandbox":
        order = list(reversed(order))
    return order


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
    last_err: Exception | None = None
    for name, base in _hosts():
        try:
            rows: list[dict[str, Any]] = []
            start = 1
            while True:
                sql = f"select * from {entity} STARTPOSITION {start} MAXRESULTS {PAGE}"
                url = f"{base}/{realm}/query?" + urllib.parse.urlencode({"query": sql})
                data = _get(url, token)
                chunk = (data.get("QueryResponse") or {}).get(entity) or []
                rows.extend(chunk)
                if len(chunk) < PAGE:
                    break
                start += PAGE
            if TOKEN_PATH.exists():
                tokens = load_tokens()
                tokens["api_host"] = name
                save_tokens(tokens)
            return rows
        except SystemExit as exc:
            last_err = exc
            continue
    raise SystemExit(str(last_err) if last_err else "QBO query failed")


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


def _report(realm: str, token: str, name: str, params: dict[str, str]) -> dict[str, Any]:
    last_err: Exception | None = None
    q = urllib.parse.urlencode(params)
    for host, base in _hosts():
        url = f"{base}/{realm}/reports/{name}?{q}&minorversion=75"
        try:
            data = _get(url, token)
            if TOKEN_PATH.exists():
                tokens = load_tokens()
                tokens["api_host"] = host
                save_tokens(tokens)
            return data
        except SystemExit as exc:
            last_err = exc
            continue
    raise SystemExit(str(last_err) if last_err else "QBO report failed")


def find_fnb_account(accounts: list[dict[str, Any]]) -> dict[str, Any] | None:
    want = "62860060278"
    scored: list[tuple[int, dict[str, Any]]] = []
    for acc in accounts:
        blob = " ".join(
            str(acc.get(k) or "")
            for k in ("AcctNum", "Name", "FullyQualifiedName", "Description")
        ).lower()
        score = 0
        if want in re.sub(r"\D", "", blob):
            score += 10
        if "fnb" in blob:
            score += 3
        if "gowifi" in blob or "go-wifi" in blob:
            score += 2
        if (acc.get("AccountType") or "") == "Bank":
            score += 1
        if score:
            scored.append((score, acc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else None


_SKIP_QB_TYPES = frozenset(
    {"invoice", "bill", "credit memo", "creditmemo", "estimate", "sales receipt"}
)


def parse_qb_fnb_report(payload: dict[str, Any], account_number: str = "62860060278") -> list[dict]:
    """FNB bank lines from a QBO TransactionList. Invoices stay out of the FNB table."""
    titles = [c.get("ColTitle") or "" for c in ((payload.get("Columns") or {}).get("Column") or [])]
    has_account = any(t.lower() == "account" for t in titles)
    want = re.sub(r"\D", "", account_number or "")
    out: list[dict] = []

    def walk(rows: list[dict]) -> None:
        for row in rows:
            kids = ((row.get("Rows") or {}).get("Row")) or []
            if kids:
                walk(kids)
            data = row.get("ColData") or []
            if not data:
                continue
            cells = {}
            for i, title in enumerate(titles):
                cells[title.lower()] = (data[i].get("value") if i < len(data) else "") or ""
            day = (cells.get("date") or "")[:10]
            if len(day) < 10 or day[4] != "-":
                continue
            txn_type = (cells.get("transaction type") or cells.get("type") or "").strip().lower()
            if txn_type in _SKIP_QB_TYPES:
                continue
            account_cell = cells.get("account") or ""
            if has_account:
                digits = re.sub(r"\D", "", account_cell)
                if want not in digits and "fnb" not in account_cell.lower():
                    continue
            raw_amt = cells.get("amount") or cells.get("foreign amount") or ""
            if raw_amt in ("", "-"):
                continue
            try:
                amount = float(str(raw_amt).replace(",", "").replace("R", "").strip())
            except ValueError:
                continue
            name = (cells.get("name") or "").strip()
            memo = (cells.get("memo/description") or cells.get("memo") or cells.get("description") or "").strip()
            desc = " / ".join(p for p in (name, memo) if p) or name or memo
            raw_bal = cells.get("balance") or cells.get("foreign balance") or ""
            balance = None
            if raw_bal not in ("", "-"):
                try:
                    balance = float(str(raw_bal).replace(",", "").replace("R", "").strip())
                except ValueError:
                    balance = None
            out.append(
                {
                    "paid_on": day,
                    "amount": round(amount, 2),
                    "balance": balance,
                    "description": desc,
                    "source": "fnb_qb",
                    "account_number": account_number,
                    "filename": "qb-fnb-bank",
                    "qb_type": txn_type,
                }
            )

    walk(((payload.get("Rows") or {}).get("Row")) or [])
    from fnb_statement import collapse_same_day_client_credits

    return collapse_same_day_client_credits(out)


def pull_fnb_bank(conn: sqlite3.Connection | None = None, days: int = 90) -> dict:
    """Read FNB 62860060278 from QuickBooks bank into the same FNB table."""
    from datetime import date, datetime, timedelta

    from company import COMPANY, GOWIFI_FNB
    from fnb_statement import (
        _record_fetch,
        checksum_table,
        insert_new,
        refresh_table_balances,
        set_progress,
    )

    set_progress("Opening QuickBooks FNB")
    token, realm = access_token()
    accounts = _query(realm, token, "Account")
    acc = find_fnb_account(accounts)
    if not acc:
        err = "No FNB bank account on QuickBooks"
        set_progress(err, done=True, error=err)
        return {"ok": False, "error": err, "inserted": 0, "rows": 0, "via": "fnb-qb"}
    acct_id = str(acc.get("Id") or "")
    number = str(acc.get("AcctNum") or GOWIFI_FNB).strip() or GOWIFI_FNB
    qb_bal = acc.get("CurrentBalance")
    try:
        qb_bal = float(qb_bal) if qb_bal is not None else None
    except (TypeError, ValueError):
        qb_bal = None
    set_progress(f"Reading FNB {number} from QB")
    end = date.today()
    start = end - timedelta(days=max(1, days))
    report = _report(
        realm,
        token,
        "TransactionList",
        {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "account": acct_id,
        },
    )
    rows = parse_qb_fnb_report(report, number)
    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB), timeout=60)
    if conn is None:
        own.execute("PRAGMA busy_timeout=60000")
    added = insert_new(own, rows)
    rolled = refresh_table_balances(own)
    table_bal = rolled.get("table_balance")
    check = checksum_table(table_bal, qb_bal)
    pack = {
        "ok": True,
        "via": "fnb-qb",
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "inserted": added["inserted"],
        "allocated": added.get("allocated") or 0,
        "need_recon": added.get("need_recon") or 0,
        "need_recon_amount": added.get("need_recon_amount") or 0,
        "attention": added.get("attention") or [],
        "rows": len(rows),
        "rows_seen": len(rows),
        "balance": table_bal,
        "external_balance": qb_bal,
        "checksum": check,
        "account_number": number,
        "account_name": COMPANY["bank_account_name"],
        "note": (
            f"QB FNB {number} · table {table_bal} · QB {qb_bal} · "
            + ("checksum match" if check.get("ok") else "checksum not matched")
        ),
    }
    _record_fetch(own, pack)
    if conn is None:
        own.close()
    set_progress(f"Done · {added['inserted']} new of {len(rows)} from QB", done=True)
    return pack


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
