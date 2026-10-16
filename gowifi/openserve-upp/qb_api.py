#!/usr/bin/env python3
"""QuickBooks Online invoices, payments, and credits for GoWiFi.

Accounting rules:
- Reconcile payments per transaction. Match bank to QBO only by namespaced
  QBO id, or by a unique same-day / same-amount / same-customer hit.
  A bank row for a customer never suppresses their other QBO payments or credits.
- Mark void/deleted only from verified QBO evidence (TxnStatus or CDC status
  of deleted/void/voided). Absence from an incremental or incomplete response
  is not evidence and must not void a stored row.
- Namespace ids as qbo:{realm}:{entity}:{id}.
- Advance the sync watermark only after a successful committed batch.

Fixture tests live in self_test(). Default CLI is self-test so an accidental
run does not write a production database. Live pull is explicit: qb_api.py pull
"""
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
from datetime import datetime, timezone
from typing import Any, Callable

from qb_oauth import TOKEN_PATH, access_token, load_tokens, save_tokens

DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
API_PROD = "https://quickbooks.api.intuit.com/v3/company"
API_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"
PAGE = 1000
ENTITY_INVOICE = "invoice"
ENTITY_PAYMENT = "payment"
ENTITY_CREDIT = "creditmemo"
VERIFIED_VOID = frozenset({"deleted", "void", "voided"})
SOURCE = "quickbooks-api"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customer_invoices (
    invoice_number INTEGER PRIMARY KEY,
    invoice_date TEXT,
    due_date TEXT,
    service_number TEXT,
    customer TEXT,
    bill_to TEXT,
    address TEXT,
    period TEXT,
    description TEXT,
    qty REAL,
    rate REAL,
    amount REAL,
    vat REAL,
    balance_due REAL,
    terms TEXT,
    status TEXT,
    source TEXT,
    filename TEXT,
    qbo_id TEXT
);
CREATE TABLE IF NOT EXISTS customer_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    customer TEXT,
    amount REAL,
    note TEXT,
    source TEXT,
    statement_number INTEGER,
    method TEXT,
    qbo_id TEXT,
    status TEXT
);
CREATE TABLE IF NOT EXISTS qb_sync_state (
    realm TEXT NOT NULL,
    entity TEXT NOT NULL,
    watermark TEXT,
    updated_at TEXT,
    PRIMARY KEY (realm, entity)
);
"""


def qbo_ref(realm: str | None, entity: str | None, raw_id: Any) -> str | None:
    realm_s = str(realm or "").strip()
    entity_s = str(entity or "").strip().lower()
    rid = str(raw_id or "").strip()
    if not realm_s or not entity_s or not rid:
        return None
    return f"qbo:{realm_s}:{entity_s}:{rid}"


def parse_qbo_ref(ref: str | None) -> tuple[str, str, str] | None:
    parts = str(ref or "").split(":")
    if len(parts) < 4 or parts[0] != "qbo":
        return None
    raw_id = parts[-1]
    entity = parts[-2].lower()
    realm = ":".join(parts[1:-2])
    if not realm or not entity or not raw_id:
        return None
    return realm, entity, raw_id


def _name_key(name: str | None) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (name or "").lower()))


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def void_evidence(entity: dict | None) -> bool:
    """True only when QBO itself marks the object deleted or void."""
    if not isinstance(entity, dict):
        return False
    for key in ("status", "Status", "TxnStatus"):
        if str(entity.get(key) or "").strip().lower() in VERIFIED_VOID:
            return True
    return False


def entity_updated_at(entity: dict | None) -> str | None:
    if not isinstance(entity, dict):
        return None
    meta = entity.get("MetaData") if isinstance(entity.get("MetaData"), dict) else {}
    stamp = meta.get("LastUpdatedTime") or entity.get("LastUpdatedTime")
    return str(stamp) if stamp else None


def ensure_qbo_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    inv_cols = {r[1] for r in conn.execute("PRAGMA table_info(customer_invoices)")}
    if "qbo_id" not in inv_cols:
        conn.execute("ALTER TABLE customer_invoices ADD COLUMN qbo_id TEXT")
    pay_cols = {r[1] for r in conn.execute("PRAGMA table_info(customer_payments)")}
    if "qbo_id" not in pay_cols:
        conn.execute("ALTER TABLE customer_payments ADD COLUMN qbo_id TEXT")
    if "status" not in pay_cols:
        conn.execute("ALTER TABLE customer_payments ADD COLUMN status TEXT")
    if "method" not in pay_cols:
        conn.execute("ALTER TABLE customer_payments ADD COLUMN method TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_invoices_qbo_id "
        "ON customer_invoices(qbo_id) WHERE qbo_id IS NOT NULL AND qbo_id != ''"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_payments_qbo_id "
        "ON customer_payments(qbo_id) WHERE qbo_id IS NOT NULL AND qbo_id != ''"
    )


def get_watermark(conn: sqlite3.Connection, realm: str, entity: str) -> str | None:
    row = conn.execute(
        "SELECT watermark FROM qb_sync_state WHERE realm=? AND entity=?",
        (realm, entity),
    ).fetchone()
    return row[0] if row and row[0] else None


def _write_watermarks(conn: sqlite3.Connection, realm: str, marks: dict[str, str]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for entity, stamp in marks.items():
        if not stamp:
            continue
        conn.execute(
            """INSERT INTO qb_sync_state (realm, entity, watermark, updated_at)
               VALUES (?,?,?,?)
               ON CONFLICT(realm, entity) DO UPDATE SET
                 watermark=excluded.watermark, updated_at=excluded.updated_at""",
            (realm, entity, stamp, now),
        )


def match_bank_to_qbo(bank: dict, qbo_rows: list[dict]) -> dict | None:
    """Explicit per-transaction match. Never suppress a customer's other QBO rows.

    Prefer a namespaced qbo_id on the bank line. Otherwise require exactly one
    QBO row with the same day, absolute amount, and customer key. Zero or many
    hits is not a match.
    """
    live = [r for r in qbo_rows if (r.get("status") or "").lower() not in VERIFIED_VOID]
    ref = bank.get("qbo_id") or bank.get("qbo_ref")
    if ref:
        hits = [r for r in live if r.get("qbo_id") == ref]
        return hits[0] if len(hits) == 1 else None
    day = (bank.get("paid_on") or "")[:10]
    amt = round(abs(_money(bank.get("amount"))), 2)
    key = _name_key(bank.get("customer"))
    if not day or not key:
        return None
    hits = []
    for row in live:
        if (row.get("paid_on") or "")[:10] != day:
            continue
        if round(abs(_money(row.get("amount"))), 2) != amt:
            continue
        if _name_key(row.get("customer")) != key:
            continue
        hits.append(row)
    return hits[0] if len(hits) == 1 else None


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


def query_pages(
    fetch_page: Callable[[int, int], list[dict] | None],
    page_size: int = PAGE,
) -> list[dict]:
    """Fetch every page. None or a raised error means incomplete — do not apply."""
    if page_size < 1:
        raise ValueError("page_size")
    start = 1
    out: list[dict] = []
    while True:
        chunk = fetch_page(start, page_size)
        if chunk is None:
            raise RuntimeError("incomplete QBO page")
        if not isinstance(chunk, list):
            raise RuntimeError("QBO page must be a list")
        out.extend(chunk)
        if len(chunk) < page_size:
            return out
        start += page_size


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


def invoice_status(inv: dict) -> str:
    if void_evidence(inv):
        return "void"
    if _money(inv.get("Balance")) <= 0.004:
        return "paid"
    return "open"


def invoice_row(inv: dict, realm: str = "") -> dict | None:
    number = _invoice_number(inv)
    if number is None and not void_evidence(inv):
        return None
    cust = ((inv.get("CustomerRef") or {}).get("name")) or None
    desc, qty, rate = _lines(inv)
    amount = inv.get("TotalAmt")
    ref = qbo_ref(realm, ENTITY_INVOICE, inv.get("Id"))
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
        "status": invoice_status(inv),
        "source": SOURCE,
        "filename": ref,
        "qbo_id": ref,
        "updated_at": entity_updated_at(inv),
    }


def payment_row(pay: dict, realm: str, entity: str = ENTITY_PAYMENT) -> dict | None:
    ref = qbo_ref(realm, entity, pay.get("Id"))
    if not ref:
        return None
    cust = ((pay.get("CustomerRef") or {}).get("name")) or None
    method = "credit" if entity == ENTITY_CREDIT else "eft"
    note = pay.get("PrivateNote") or (
        f"QBO credit {pay.get('DocNumber')}" if entity == ENTITY_CREDIT else "QBO payment"
    )
    status = "void" if void_evidence(pay) else "open"
    return {
        "qbo_id": ref,
        "paid_on": pay.get("TxnDate"),
        "customer": cust,
        "amount": -abs(_money(pay.get("TotalAmt"))),
        "note": note,
        "source": SOURCE,
        "method": method,
        "status": status,
        "updated_at": entity_updated_at(pay),
    }


def upsert_invoice(conn: sqlite3.Connection, row: dict) -> str:
    qbo_id = row.get("qbo_id")
    number = row.get("invoice_number")
    found = None
    if qbo_id:
        found = conn.execute(
            "SELECT invoice_number FROM customer_invoices WHERE qbo_id=?",
            (qbo_id,),
        ).fetchone()
    if found is None and number is not None:
        found = conn.execute(
            "SELECT invoice_number FROM customer_invoices WHERE invoice_number=?",
            (number,),
        ).fetchone()
    values = (
        row.get("invoice_date"),
        row.get("due_date"),
        row.get("customer"),
        row.get("bill_to") or row.get("customer"),
        row.get("address"),
        row.get("description"),
        row.get("qty") if row.get("qty") is not None else 1,
        row.get("rate") if row.get("rate") is not None else row.get("amount"),
        row.get("amount"),
        row.get("balance_due"),
        row.get("terms") or "Due on receipt",
        row.get("status") or "open",
        SOURCE,
        row.get("filename") or qbo_id,
        qbo_id,
    )
    if found:
        conn.execute(
            """UPDATE customer_invoices SET
                 invoice_date=?, due_date=?, customer=?, bill_to=?, address=?,
                 description=?, qty=?, rate=?, amount=?, balance_due=?, terms=?,
                 status=?, source=?, filename=?, qbo_id=?
               WHERE invoice_number=?""",
            values + (found[0],),
        )
        return "updated"
    if number is None:
        return "skipped"
    conn.execute(
        """INSERT INTO customer_invoices
           (invoice_number, invoice_date, due_date, customer, bill_to, address,
            description, qty, rate, amount, balance_due, terms, status, source,
            filename, qbo_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (number,) + values,
    )
    return "inserted"


def upsert_payment(conn: sqlite3.Connection, row: dict) -> str:
    qbo_id = row.get("qbo_id")
    if not qbo_id:
        return "skipped"
    found = conn.execute(
        "SELECT id FROM customer_payments WHERE qbo_id=?",
        (qbo_id,),
    ).fetchone()
    values = (
        row.get("paid_on"),
        row.get("customer"),
        row.get("amount"),
        row.get("note"),
        SOURCE,
        row.get("method") or "eft",
        qbo_id,
        row.get("status") or "open",
    )
    if found:
        conn.execute(
            """UPDATE customer_payments SET
                 paid_on=?, customer=?, amount=?, note=?, source=?, method=?,
                 qbo_id=?, status=?
               WHERE id=?""",
            values + (found[0],),
        )
        return "updated"
    conn.execute(
        """INSERT INTO customer_payments
           (paid_on, customer, amount, note, source, method, qbo_id, status)
           VALUES (?,?,?,?,?,?,?,?)""",
        values,
    )
    return "inserted"


def mark_void(conn: sqlite3.Connection, qbo_id: str, entity: str) -> bool:
    if entity == ENTITY_INVOICE:
        cur = conn.execute(
            "UPDATE customer_invoices SET status='void' WHERE qbo_id=?",
            (qbo_id,),
        )
        return cur.rowcount > 0
    cur = conn.execute(
        "UPDATE customer_payments SET status='void' WHERE qbo_id=?",
        (qbo_id,),
    )
    return cur.rowcount > 0


def apply_entity(conn: sqlite3.Connection, realm: str, entity: str, raw: dict) -> str:
    ref = qbo_ref(realm, entity, raw.get("Id"))
    if void_evidence(raw):
        if not ref:
            return "skipped"
        return "voided" if mark_void(conn, ref, entity) else "void-miss"
    if entity == ENTITY_INVOICE:
        row = invoice_row(raw, realm)
        return upsert_invoice(conn, row) if row else "skipped"
    if entity in {ENTITY_PAYMENT, ENTITY_CREDIT}:
        row = payment_row(raw, realm, entity)
        return upsert_payment(conn, row) if row else "skipped"
    return "skipped"


def apply_batch(
    conn: sqlite3.Connection,
    realm: str,
    items: list[tuple[str, dict]],
    *,
    on_progress: Callable[[int, tuple[str, dict]], None] | None = None,
) -> dict[str, int]:
    """Apply one batch, commit, then write watermarks. Failure rolls back data
    and leaves watermarks unchanged.
    """
    ensure_qbo_schema(conn)
    before = {
        entity: get_watermark(conn, realm, entity)
        for entity in {ENTITY_INVOICE, ENTITY_PAYMENT, ENTITY_CREDIT}
    }
    counts = {"inserted": 0, "updated": 0, "voided": 0, "skipped": 0}
    marks: dict[str, str] = {}
    try:
        for i, (entity, raw) in enumerate(items):
            if on_progress:
                on_progress(i, (entity, raw))
            action = apply_entity(conn, realm, entity, raw)
            if action in counts:
                counts[action] += 1
            elif action == "void-miss":
                counts["skipped"] += 1
            stamp = entity_updated_at(raw)
            if stamp and (stamp > (marks.get(entity) or "")):
                marks[entity] = stamp
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    try:
        if marks:
            _write_watermarks(conn, realm, marks)
            conn.commit()
    except Exception:
        conn.rollback()
        # Data batch already committed; retry is idempotent. Watermark stays.
        return {**counts, "ok": 0, "watermark_advanced": 0}
    advanced = 0
    for entity, stamp in marks.items():
        if stamp and stamp != (before.get(entity) or ""):
            advanced += 1
    return {**counts, "ok": 1, "watermark_advanced": advanced}


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
    """Live company pull. Tests never call this against a production database."""
    from qb_import import ensure_history_tables

    ensure_history_tables(conn)
    ensure_qbo_schema(conn)
    token, realm = access_token()
    invoices = _query(realm, token, "Invoice")
    payments = _query(realm, token, "Payment")
    credits = _query(realm, token, "CreditMemo")
    customers = _query(realm, token, "Customer")
    items: list[tuple[str, dict]] = []
    items.extend((ENTITY_INVOICE, row) for row in invoices)
    items.extend((ENTITY_PAYMENT, row) for row in payments)
    items.extend((ENTITY_CREDIT, row) for row in credits)
    stats = apply_batch(conn, str(realm), items)
    return {
        "invoices_read": len(invoices),
        "payments_read": len(payments),
        "credits_read": len(credits),
        "customers_read": len(customers),
        "invoices_saved": stats.get("inserted", 0) + stats.get("updated", 0),
        "payments_saved": 0,
        "realm": int(realm) if str(realm).isdigit() else 0,
        **stats,
    }


def _mem() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_qbo_schema(conn)
    return conn


def _whale_invoice(**over: Any) -> dict:
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
            },
            {
                "DetailType": "SalesItemLineDetail",
                "Description": "GoWifi Fibre Gigabit > ProRate Oct 2026",
                "Amount": 1055.4,
                "SalesItemLineDetail": {"Qty": 18, "UnitPrice": 58.6333},
            },
            {
                "DetailType": "SalesItemLineDetail",
                "Description": "GoWifi Fibre Gigabit - Nov 2026",
                "Amount": 1759.0,
                "SalesItemLineDetail": {"Qty": 1, "UnitPrice": 1759},
            },
        ],
        "MetaData": {"LastUpdatedTime": "2026-10-16T08:00:00-07:00"},
    }
    row.update(over)
    return row


def self_test() -> int:
    failed = 0
    realm = "9130354340040586"

    def check(name: str, ok: bool, detail: Any = None) -> None:
        nonlocal failed
        if ok:
            print("OK", name)
        else:
            failed += 1
            print("FAIL", name, detail if detail is not None else "")

    inv_ref = qbo_ref(realm, ENTITY_INVOICE, "2139")
    pay_ref = qbo_ref(realm, ENTITY_PAYMENT, "2139")
    check("namespace-entity", inv_ref != pay_ref and parse_qbo_ref(inv_ref) == (realm, ENTITY_INVOICE, "2139"))
    check("void-evidence-only", void_evidence({"status": "Deleted"}) and not void_evidence({"Id": "2139", "Balance": 0}))
    check("missing-is-not-void", not void_evidence({}) and not void_evidence(None))

    parsed = invoice_row(_whale_invoice(), realm)
    check(
        "whale-3213",
        parsed is not None
        and parsed["amount"] == 3213.4
        and parsed["balance_due"] == 3213.4
        and parsed["status"] == "open"
        and parsed["qbo_id"] == inv_ref
        and parsed["amount"] != 1759
        and parsed["balance_due"] != 3463,
        parsed,
    )

    conn = _mem()
    first = apply_batch(
        conn,
        realm,
        [
            (ENTITY_INVOICE, _whale_invoice()),
            (
                ENTITY_PAYMENT,
                {
                    "Id": "9001",
                    "TxnDate": "2026-10-10",
                    "TotalAmt": 500,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T09:00:00-07:00"},
                },
            ),
            (
                ENTITY_CREDIT,
                {
                    "Id": "88",
                    "DocNumber": "C-88",
                    "TxnDate": "2026-10-11",
                    "TotalAmt": 100,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T09:30:00-07:00"},
                },
            ),
        ],
    )
    mark = get_watermark(conn, realm, ENTITY_INVOICE)
    second = apply_batch(
        conn,
        realm,
        [
            (ENTITY_INVOICE, _whale_invoice()),
            (
                ENTITY_PAYMENT,
                {
                    "Id": "9001",
                    "TxnDate": "2026-10-10",
                    "TotalAmt": 500,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T09:00:00-07:00"},
                },
            ),
            (
                ENTITY_CREDIT,
                {
                    "Id": "88",
                    "DocNumber": "C-88",
                    "TxnDate": "2026-10-11",
                    "TotalAmt": 100,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T09:30:00-07:00"},
                },
            ),
        ],
    )
    invs = list(conn.execute("SELECT * FROM customer_invoices"))
    pays = list(conn.execute("SELECT * FROM customer_payments ORDER BY qbo_id"))
    check("repeat-one-invoice", len(invs) == 1 and invs[0]["amount"] == 3213.4)
    check("repeat-one-payment-one-credit", len(pays) == 2)
    check("repeat-updated-not-inserted", second.get("inserted") == 0 and second.get("updated") == 3)
    check("first-batch-watermark", bool(mark) and first.get("ok") == 1)

    apply_batch(
        conn,
        realm,
        [
            (
                ENTITY_INVOICE,
                _whale_invoice(TotalAmt=3000.0, Balance=3000.0, MetaData={"LastUpdatedTime": "2026-10-16T10:00:00-07:00"}),
            ),
            (
                ENTITY_PAYMENT,
                {
                    "Id": "9001",
                    "TxnDate": "2026-10-12",
                    "TotalAmt": 250,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T10:05:00-07:00"},
                },
            ),
            (
                ENTITY_CREDIT,
                {
                    "Id": "88",
                    "DocNumber": "C-88",
                    "TxnDate": "2026-10-11",
                    "TotalAmt": 80,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T10:06:00-07:00"},
                },
            ),
        ],
    )
    edited = conn.execute("SELECT amount, balance_due FROM customer_invoices WHERE qbo_id=?", (inv_ref,)).fetchone()
    pay_e = conn.execute(
        "SELECT amount, paid_on FROM customer_payments WHERE qbo_id=?",
        (qbo_ref(realm, ENTITY_PAYMENT, "9001"),),
    ).fetchone()
    cr_e = conn.execute(
        "SELECT amount, method FROM customer_payments WHERE qbo_id=?",
        (qbo_ref(realm, ENTITY_CREDIT, "88"),),
    ).fetchone()
    check("edit-invoice-amount", edited is not None and edited["amount"] == 3000.0 and edited["balance_due"] == 3000.0)
    check("edit-payment", pay_e is not None and abs(pay_e["amount"]) == 250.0 and pay_e["paid_on"] == "2026-10-12")
    check("edit-credit", cr_e is not None and abs(cr_e["amount"]) == 80.0 and cr_e["method"] == "credit")
    check("still-two-money-rows", conn.execute("SELECT COUNT(*) FROM customer_payments").fetchone()[0] == 2)

    apply_batch(
        conn,
        realm,
        [(ENTITY_INVOICE, {"Id": "2139", "status": "Deleted", "MetaData": {"LastUpdatedTime": "2026-10-16T11:00:00-07:00"}})],
    )
    check(
        "void-from-qbo-status",
        conn.execute("SELECT status FROM customer_invoices WHERE qbo_id=?", (inv_ref,)).fetchone()[0] == "void",
    )
    apply_batch(
        conn,
        realm,
        [
            (
                ENTITY_PAYMENT,
                {
                    "Id": "9002",
                    "TxnDate": "2026-10-13",
                    "TotalAmt": 10,
                    "CustomerRef": {"name": "Whale Rock Lodge"},
                    "MetaData": {"LastUpdatedTime": "2026-10-16T11:10:00-07:00"},
                },
            )
        ],
    )
    kept = conn.execute(
        "SELECT status FROM customer_payments WHERE qbo_id=?",
        (qbo_ref(realm, ENTITY_PAYMENT, "9001"),),
    ).fetchone()
    check("missing-id-not-void", kept is not None and (kept["status"] or "open") != "void")
    check(
        "unknown-delete-no-row",
        apply_entity(conn, realm, ENTITY_INVOICE, {"Id": "no-such", "status": "Deleted"}) == "void-miss",
    )

    pages = [
        [{"Id": "1", "DocNumber": "1"}, {"Id": "2", "DocNumber": "2"}],
        [{"Id": "3", "DocNumber": "3"}, {"Id": "4", "DocNumber": "4"}],
    ]

    def fetch(start: int, page_size: int) -> list[dict]:
        idx = (start - 1) // page_size
        return pages[idx] if 0 <= idx < len(pages) else []

    check("pagination-join", [r["Id"] for r in query_pages(fetch, 2)] == ["1", "2", "3", "4"])

    def fail_page(start: int, page_size: int) -> list[dict]:
        idx = (start - 1) // page_size
        if idx == 1:
            raise RuntimeError("page 2 failed")
        return pages[idx]

    page_failed = False
    try:
        query_pages(fail_page, 2)
    except RuntimeError:
        page_failed = True
    check("pagination-incomplete-raises", page_failed)

    def none_page(start: int, page_size: int) -> list[dict] | None:
        if start > 1:
            return None
        return pages[0]

    none_failed = False
    try:
        query_pages(none_page, 2)
    except RuntimeError:
        none_failed = True
    check("pagination-none-is-incomplete", none_failed)

    recover = _mem()
    apply_batch(
        recover,
        realm,
        [(ENTITY_INVOICE, _whale_invoice())],
    )
    old_wm = get_watermark(recover, realm, ENTITY_INVOICE)
    old_n = recover.execute("SELECT COUNT(*) FROM customer_invoices").fetchone()[0]

    def boom(i: int, _item: tuple[str, dict]) -> None:
        if i == 1:
            raise RuntimeError("fail mid-batch")

    mid_failed = False
    try:
        apply_batch(
            recover,
            realm,
            [
                (ENTITY_INVOICE, _whale_invoice(DocNumber="3132", Id="2140", TotalAmt=100, Balance=100)),
                (
                    ENTITY_PAYMENT,
                    {
                        "Id": "boom",
                        "TxnDate": "2026-10-14",
                        "TotalAmt": 1,
                        "CustomerRef": {"name": "Whale Rock Lodge"},
                    },
                ),
            ],
            on_progress=boom,
        )
    except RuntimeError:
        mid_failed = True
    check("failed-batch-raises", mid_failed)
    check(
        "failed-batch-no-partial",
        recover.execute("SELECT COUNT(*) FROM customer_invoices").fetchone()[0] == old_n
        and recover.execute("SELECT COUNT(*) FROM customer_invoices WHERE invoice_number=3132").fetchone()[0] == 0,
    )
    check("failed-batch-watermark-held", get_watermark(recover, realm, ENTITY_INVOICE) == old_wm)
    retry = apply_batch(
        recover,
        realm,
        [(ENTITY_INVOICE, _whale_invoice(DocNumber="3132", Id="2140", TotalAmt=100, Balance=100))],
    )
    check(
        "failed-batch-retry",
        retry.get("ok") == 1
        and recover.execute("SELECT COUNT(*) FROM customer_invoices WHERE invoice_number=3132").fetchone()[0] == 1,
    )

    may_pay = {
        "qbo_id": qbo_ref(realm, ENTITY_PAYMENT, "77"),
        "paid_on": "2026-09-30",
        "customer": "Phillipus May",
        "amount": -439.0,
        "status": "open",
    }
    whale_pay = {
        "qbo_id": qbo_ref(realm, ENTITY_PAYMENT, "9001"),
        "paid_on": "2026-10-10",
        "customer": "Whale Rock Lodge",
        "amount": -500.0,
        "status": "open",
    }
    bank_may = {"paid_on": "2026-09-30", "amount": 439.0, "customer": "Phillipus May"}
    bank_whale_id = {"paid_on": "2026-10-10", "amount": 500.0, "customer": "Whale Rock Lodge", "qbo_id": whale_pay["qbo_id"]}
    twin = [
        whale_pay,
        {"qbo_id": qbo_ref(realm, ENTITY_PAYMENT, "9003"), "paid_on": "2026-10-10", "customer": "Whale Rock Lodge", "amount": -500.0, "status": "open"},
    ]
    check("match-explicit-id", match_bank_to_qbo(bank_whale_id, [may_pay, whale_pay]) == whale_pay)
    check("match-unique-day-amount-customer", match_bank_to_qbo(bank_may, [may_pay, whale_pay]) == may_pay)
    check("match-ambiguous-no-guess", match_bank_to_qbo({"paid_on": "2026-10-10", "amount": 500, "customer": "Whale Rock Lodge"}, twin) is None)
    check(
        "bank-does-not-suppress-other-qbo",
        match_bank_to_qbo(bank_may, [may_pay, whale_pay]) == may_pay and whale_pay not in [match_bank_to_qbo(bank_may, [may_pay, whale_pay])],
    )

    conn.close()
    recover.close()
    return failed


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"self-test", "test"}:
        failed = self_test()
        return 1 if failed else 0
    if args[0] == "pull":
        db = sqlite3.connect(DB)
        try:
            print(json.dumps(pull(db), indent=2))
        finally:
            db.close()
        return 0
    print("usage: qb_api.py self-test|pull")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
