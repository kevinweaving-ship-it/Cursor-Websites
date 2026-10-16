#!/usr/bin/env python3
"""One-time read of GoWiFi QuickBooks Online invoices, customers, payments."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from datetime import date

from qb_import import _upsert_invoice, ensure_history_tables
from qb_oauth import TOKEN_PATH, access_token, load_tokens, save_tokens

DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
API_PROD = "https://quickbooks.api.intuit.com/v3/company"
API_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"
PAGE = 1000
WHALE_CUSTOMER_ID = "55"
WHALE_NAME = "Whale Rock Lodge"
WHALE_DO_START = date(2026, 11, 1)


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


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def is_whale_rock(name: str | None) -> bool:
    """Exact Whale Rock Lodge card. Does not match hermanus whalec / May."""
    key = " ".join(re.findall(r"[a-z0-9]+", (name or "").lower()))
    return key == "whale rock lodge" or key.startswith("whale rock lodge ")


def _is_whale_invoice(inv: dict) -> bool:
    ref = inv.get("CustomerRef") if isinstance(inv.get("CustomerRef"), dict) else {}
    if str(ref.get("value") or "").strip() == WHALE_CUSTOMER_ID:
        return True
    return is_whale_rock(ref.get("name"))


def _whale_void(inv: dict) -> bool:
    if str(inv.get("status") or inv.get("Status") or "").strip().lower() == "deleted":
        return True
    note = str(inv.get("PrivateNote") or "").strip()
    return note.lower() == "voided" and _money(inv.get("TotalAmt")) <= 0.004


def whale_invoice_row(inv: dict) -> dict | None:
    """Live QBO invoice for Whale Rock. Not the historical PDF placeholder."""
    if not _is_whale_invoice(inv):
        return None
    row = invoice_row(inv)
    if not row:
        return None
    if _whale_void(inv):
        row["status"] = "void"
        row["amount"] = _money(inv.get("TotalAmt"))
        row["balance_due"] = 0.0
    elif _money(inv.get("Balance")) <= 0.004:
        row["status"] = "paid"
        row["balance_due"] = 0.0
    else:
        row["status"] = "open"
        row["balance_due"] = _money(inv.get("Balance"))
    row["amount"] = _money(inv.get("TotalAmt"))
    row["source"] = "quickbooks-api"
    row["customer"] = WHALE_NAME
    return row


def _upsert_whale_invoice(conn: sqlite3.Connection, row: dict) -> None:
    """Same invoice number as the PDF — API wins. Not a new handmade row."""
    conn.execute(
        """INSERT INTO customer_invoices
           (invoice_number, invoice_date, due_date, customer, bill_to, address,
            description, qty, rate, amount, balance_due, terms, status, source, filename)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(invoice_number) DO UPDATE SET
             invoice_date=excluded.invoice_date,
             due_date=excluded.due_date,
             customer=excluded.customer,
             bill_to=excluded.bill_to,
             description=COALESCE(excluded.description, customer_invoices.description),
             amount=excluded.amount,
             balance_due=excluded.balance_due,
             status=excluded.status,
             source='quickbooks-api',
             filename=excluded.filename""",
        (
            row["invoice_number"],
            row.get("invoice_date"),
            row.get("due_date"),
            WHALE_NAME,
            WHALE_NAME,
            row.get("address"),
            row.get("description"),
            row.get("qty") if row.get("qty") is not None else 1,
            row.get("rate") if row.get("rate") is not None else row.get("amount"),
            row.get("amount"),
            row.get("balance_due"),
            row.get("terms") or "Due on receipt",
            row.get("status") or "open",
            "quickbooks-api",
            row.get("filename"),
        ),
    )


def refresh_whale_rock(conn: sqlite3.Connection | None = None) -> dict:
    """Pull only Whale Rock Lodge invoices. Does not write QBO Payments as cash."""
    from qb_import import ensure_history_tables as _ensure

    own = conn or sqlite3.connect(os.environ.get("UPP_DB", DB), timeout=60)
    _ensure(own)
    token, realm = access_token()
    invoices = _query(realm, token, "Invoice")
    saved = 0
    skipped = 0
    for inv in invoices:
        row = whale_invoice_row(inv)
        if not row:
            continue
        if row.get("status") == "void":
            _upsert_whale_invoice(own, row)
            skipped += 1
            continue
        _upsert_whale_invoice(own, row)
        saved += 1
    own.commit()
    if conn is None:
        own.close()
    return {
        "ok": True,
        "customer": WHALE_NAME,
        "invoices_saved": saved,
        "voided": skipped,
        "invoices_read": len(invoices),
    }


def _whale_netcash(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    paid: list[dict] = []
    unpaid: list[dict] = []
    try:
        from recon import client_receipts, client_unpaid
    except Exception:
        return paid, unpaid
    for rec in client_receipts(conn):
        if not is_whale_rock(rec.get("customer")):
            continue
        if (rec.get("method") or "") != "do" and "netcash" not in (rec.get("source") or ""):
            continue
        day = (rec.get("paid_on") or "")[:10]
        if day < WHALE_DO_START.isoformat():
            continue
        paid.append(rec)
    for rec in client_unpaid(conn):
        if not is_whale_rock(rec.get("customer")):
            continue
        day = (rec.get("action_date") or "")[:10]
        if day < WHALE_DO_START.isoformat():
            continue
        unpaid.append(rec)
    return paid, unpaid


def whale_rock_account(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """QB invoices + live QB outstanding. EFT until the first November D/O."""
    today = today or date.today()
    invoices = []
    try:
        rows = conn.execute(
            """SELECT invoice_number, invoice_date, due_date, amount, balance_due,
                      status, source, description
               FROM customer_invoices WHERE customer=? ORDER BY invoice_date, invoice_number""",
            (WHALE_NAME,),
        )
    except sqlite3.OperationalError:
        rows = []
    for rec in rows:
        src = (rec[6] or "").lower()
        status = (rec[5] or "").lower()
        if src != "quickbooks-api":
            continue
        if status in {"void", "deleted", "voided", "historical"}:
            continue
        invoices.append(
            {
                "invoice_number": rec[0],
                "invoice_date": rec[1],
                "due_date": rec[2],
                "amount": _money(rec[3]),
                "balance_due": _money(rec[4]),
                "status": rec[5],
                "description": rec[7],
            }
        )
    nc_paid, nc_unpaid = _whale_netcash(conn)
    first_do = bool(nc_paid or nc_unpaid)
    pay = "D/O" if first_do else "EFT"
    nc_paid_months = {(r.get("paid_on") or "")[:7] for r in nc_paid}
    nc_unpaid_months = {(r.get("action_date") or "")[:7] for r in nc_unpaid}
    ledger = []
    billed = 0.0
    due = 0.0
    bounced = False
    for inv in invoices:
        amt = inv["amount"]
        billed = round(billed + amt, 2)
        month = (inv.get("invoice_date") or "")[:7]
        collect_month = month
        try:
            day = date.fromisoformat(str(inv.get("invoice_date") or "")[:10])
            nxt = date(day.year + (1 if day.month == 12 else 0), 1 if day.month == 12 else day.month + 1, 1)
            collect_month = nxt.isoformat()[:7]
        except ValueError:
            collect_month = month
        # First bill stays on QB outstanding (EFT). Later monthlies can be Netcash.
        first_bill = (inv.get("invoice_date") or "") < WHALE_DO_START.isoformat()
        if not first_bill and first_do and collect_month in nc_paid_months:
            open_amt = 0.0
        elif not first_bill and first_do and collect_month in nc_unpaid_months:
            open_amt = amt
            bounced = True
        else:
            open_amt = inv["balance_due"]
        due = round(due + open_amt, 2)
        running = due
        ledger.append(
            {
                "date": inv.get("invoice_date"),
                "kind": "invoice",
                "ref": str(inv["invoice_number"]),
                "what": f"Invoice {inv['invoice_number']}"
                + (f" · {inv['description']}" if inv.get("description") else ""),
                "amount": amt,
                "open": open_amt,
                "balance": running,
                "show": True,
            }
        )
        if not first_bill and first_do and collect_month in nc_paid_months:
            rec = next((r for r in nc_paid if (r.get("paid_on") or "")[:7] == collect_month), None)
            ledger.append(
                {
                    "date": (rec or {}).get("paid_on"),
                    "kind": "payment",
                    "ref": str(inv["invoice_number"]),
                    "what": f"D/O paid · Invoice {inv['invoice_number']}",
                    "amount": -amt,
                    "open": 0.0,
                    "balance": running,
                    "show": True,
                }
            )
        elif not first_bill and first_do and collect_month in nc_unpaid_months:
            rec = next((r for r in nc_unpaid if (r.get("action_date") or "")[:7] == collect_month), None)
            ledger.append(
                {
                    "date": (rec or {}).get("action_date"),
                    "kind": "unpaid",
                    "ref": str(inv["invoice_number"]),
                    "what": f"D/O unpaid · Invoice {inv['invoice_number']}",
                    "amount": 0.0,
                    "open": open_amt,
                    "balance": running,
                    "show": True,
                    "tone": "overdue",
                }
            )
    paid = round(max(0.0, billed - due), 2)
    paid_up = due <= 0.004 and not bounced
    ledger.reverse()
    return {
        "name": WHALE_NAME,
        "billed": billed if invoices else None,
        "paid": paid,
        "due": due if invoices else None,
        "nil": paid_up,
        "status": "bounced" if bounced else ("paid-up" if paid_up else "owes"),
        "pay": pay,
        "method": "debit-order" if first_do else "eft",
        "bounced": bounced,
        "ledger": ledger,
        "ageing": {},
        "earlier_paid": 0,
        "last_invoice_date": invoices[-1]["invoice_date"] if invoices else None,
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


def _whale_sample(**over: Any) -> dict:
    row = {
        "Id": "2139",
        "DocNumber": "3131",
        "TxnDate": "2026-10-07",
        "DueDate": "2026-10-07",
        "TotalAmt": 3213.4,
        "Balance": 3213.4,
        "CustomerRef": {"value": "55", "name": "Whale Rock Lodge"},
        "Line": [
            {
                "DetailType": "SalesItemLineDetail",
                "Description": "Fibre & Wifi Installation",
                "Amount": 399.0,
                "SalesItemLineDetail": {"Qty": 1, "UnitPrice": 399},
            }
        ],
    }
    row.update(over)
    return row


def whale_self_test() -> int:
    failed = 0

    def check(name: str, ok: bool, detail: Any = None) -> None:
        nonlocal failed
        if ok:
            print("OK", name)
        else:
            failed += 1
            print("FAIL", name, detail if detail is not None else "")

    check("whale-name", is_whale_rock("Whale Rock Lodge") and not is_whale_rock("Phillipus May"))
    check("not-hermanus-whalec", not is_whale_rock("hermanus whalec") and not is_whale_rock("ABSA BANK 3110 hermanus whalec"))
    parsed = whale_invoice_row(_whale_sample())
    check(
        "whale-3213",
        parsed is not None
        and parsed["amount"] == 3213.4
        and parsed["balance_due"] == 3213.4
        and parsed["status"] == "open"
        and parsed["source"] == "quickbooks-api"
        and parsed["amount"] != 1759,
        parsed,
    )
    check("paid-balance-zero", whale_invoice_row(_whale_sample(Balance=0))["status"] == "paid")
    check(
        "void-privatenote",
        whale_invoice_row(_whale_sample(PrivateNote="Voided", TotalAmt=0, Balance=0))["status"] == "void",
    )
    check("may-invoice-skipped", whale_invoice_row(_whale_sample(CustomerRef={"value": "9", "name": "Phillipus May"})) is None)

    from qb_import import ensure_history_tables

    conn = sqlite3.connect(":memory:")
    ensure_history_tables(conn)
    conn.execute(
        """INSERT INTO customer_invoices
           (invoice_number, invoice_date, customer, amount, balance_due, status, source)
           VALUES (3131,'2026-10-07','Whale Rock Lodge',1759,3463,'historical','quickbooks')"""
    )
    hist = whale_rock_account(conn)
    check("pdf-placeholder-hidden", hist.get("billed") in {None, 0} and not (hist.get("ledger") or []))
    _upsert_whale_invoice(conn, parsed)
    live = whale_rock_account(conn, date(2026, 10, 16))
    check(
        "api-overwrites-pdf",
        abs((live.get("billed") or 0) - 3213.4) < 0.02
        and abs((live.get("due") or 0) - 3213.4) < 0.02
        and live.get("pay") == "EFT"
        and live.get("status") == "owes",
        live,
    )
    check("not-1759-or-3463", live.get("billed") != 1759 and live.get("due") != 3463)
    _upsert_whale_invoice(conn, whale_invoice_row(_whale_sample(Balance=0)))
    cleared = whale_rock_account(conn)
    check("paid-up-when-qb-zero", cleared.get("nil") is True and (cleared.get("due") or 0) <= 0.004)
    _upsert_whale_invoice(conn, whale_invoice_row(_whale_sample(Balance=3213.4)))
    conn.execute(
        """INSERT INTO customer_invoices
           (invoice_number, invoice_date, customer, amount, balance_due, status, source)
           VALUES (3200,'2026-11-17','Whale Rock Lodge',1759,1759,'open','quickbooks-api')"""
    )
    from recon import SCHEMA as NC_SCHEMA
    from recon import ensure as nc_ensure

    nc_ensure(conn)
    conn.executescript(NC_SCHEMA)
    conn.execute(
        """INSERT INTO netcash_tx
           (paid_on, alloc_to, alloc_key, amount, alloc_kind, result, source, batch_id)
           VALUES ('2026-12-01','Whale Rock Lodge','whale rock lodge',1759,'client_paid','paid','netcash-items','20261201')"""
    )
    after_do = whale_rock_account(conn, date(2026, 12, 2))
    check("nov-do-label", after_do.get("pay") == "D/O", after_do)
    check(
        "nov-do-not-double",
        abs((after_do.get("due") or 0) - 3213.4) < 0.02
        and abs((after_do.get("billed") or 0) - 4972.4) < 0.02,
        after_do,
    )
    conn.close()
    return failed


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"self-test", "whale-test"}:
        raise SystemExit(1 if whale_self_test() else 0)
    db = sqlite3.connect(DB)
    print(json.dumps(pull(db), indent=2))
