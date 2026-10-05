#!/usr/bin/env python3
"""Client statements from QB invoices + FNB EFT/cash + Netcash D/O.

Due on the day viewed is invoices minus allocated payments. A pending
D/O is grace (not due) until it is reconciled. A bounce stays due and
raises a suspension notice. 5 Oct 2026 batch 2571994 collected (unpaid R0).
"""
from __future__ import annotations

import json
import sqlite3
from calendar import monthrange
from datetime import date
from pathlib import Path

from billing import (
    CLIENTS,
    PENDING_DO,
    add_months,
    canon_key,
    client_row,
    display_name,
    split_qb_name,
)
from invoice_canned import statement_on_invoice
from invoice_list import classify as classify_invoices

DATA_DIR = Path(__file__).resolve().parent / "data"
INVOICES_JSON = DATA_DIR / "qb_invoices.json"
SALES_JSON = DATA_DIR / "qb_sales.json"
PAYMENTS_JSON = DATA_DIR / "qb_payments.json"
NETCASH_JSON = DATA_DIR / "qb_do_payments.json"

SCHEMA = """
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
    filename TEXT
);
CREATE TABLE IF NOT EXISTS customer_invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT,
    line_no INTEGER,
    product TEXT,
    description TEXT,
    qty REAL,
    price REAL,
    amount REAL,
    kind TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_lines_no
    ON customer_invoice_lines (invoice_number, line_no);
CREATE TABLE IF NOT EXISTS customer_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    customer TEXT,
    amount REAL,
    note TEXT,
    source TEXT,
    statement_number INTEGER,
    method TEXT
);
CREATE TABLE IF NOT EXISTS customer_do_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_date TEXT,
    customer TEXT,
    amount REAL,
    result TEXT,
    note TEXT,
    source TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_do_events_dedup
    ON customer_do_events (action_date, customer, amount, result);
"""

# Named D/O bounce / refund from the FNB register. Oct 5 is not a bounce.
KNOWN_BOUNCES = [
    {
        "action_date": "2026-03-25",
        "customer": "Havenga, Daniel",
        "amount": 699.00,
        "result": "bounced",
        "note": "HAVENGA REFUND · D/O bounced",
        "source": "fnb",
    },
]


def _money(value) -> float:
    return round(float(value or 0), 2)


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(customer_payments)")}
    if "method" not in cols:
        conn.execute("ALTER TABLE customer_payments ADD COLUMN method TEXT")


def collection_for(inv_day: date) -> date:
    nxt = add_months(date(inv_day.year, inv_day.month, 1), 1)
    first = date(nxt.year, nxt.month, 1)
    if first == date(2026, 10, 1):
        return date(2026, 10, 5)
    return first


def _kind_of_line(product: str, description: str, amount: float) -> str:
    blob = f"{product} {description}".lower()
    if amount < 0:
        return "credit"
    if any(w in blob for w in ("install", "cabling", "setup fee", "fibre installation")):
        return "install"
    if any(w in blob for w in ("router", "hardware", "ubiquiti", "aircube", "nano", "cudy", "bracket", "ont")):
        return "equipment"
    if "rental" in blob:
        return "rental"
    if any(w in blob for w in ("pro rata", "prorate", "pro-rata", "pro rate")):
        return "monthly"
    if "debit order return" in blob or "do return" in blob:
        return "do-return"
    if any(w in blob for w in ("cancel", "reconnection", "reconnect")):
        return "fee"
    if any(w in blob for w in ("monthly", "webstream", "wifi -", "gowifi", "fibre", "fiber", "uncapped", "contribution")):
        return "monthly"
    return "other"


def ingest(conn: sqlite3.Connection) -> dict:
    ensure(conn)
    conn.execute("DELETE FROM customer_invoices WHERE source IN ('qb-list','qb-sales')")
    conn.execute("DELETE FROM customer_invoice_lines")
    conn.execute(
        "DELETE FROM customer_payments WHERE source IN ('qb-eft','qb-cash','qb-do','qb-credit','qb-do-synth')"
    )
    conn.execute("DELETE FROM customer_do_events WHERE source IN ('fnb','qb-do-synth','netcash')")

    invoices = list((_load(INVOICES_JSON).get("rows") or []))
    sales = _load(SALES_JSON)
    lines = list(sales.get("rows") or [])
    credits = list(sales.get("credits") or [])
    classified = classify_invoices()
    kind_by_no = {r["number"]: r["kind"] for r in (classified.get("queries") or []) + (classified.get("monthly") or [])}

    n_inv = 0
    for row in invoices:
        try:
            number = int(row["number"])
        except (TypeError, ValueError):
            continue
        cust = display_name(row.get("name")) or row.get("name")
        conn.execute(
            """INSERT OR REPLACE INTO customer_invoices
               (invoice_number, invoice_date, due_date, customer, amount, balance_due,
                status, source, description)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                number,
                row.get("date"),
                row.get("due"),
                cust,
                _money(row.get("amount")),
                _money(row.get("open")),
                "open" if _money(row.get("open")) else "paid",
                "qb-list",
                row.get("memo") or "",
            ),
        )
        n_inv += 1

    n_line = 0
    by_no: dict[str, list[dict]] = {}
    for i, line in enumerate(lines):
        no = str(line.get("number") or "")
        by_no.setdefault(no, []).append(line)
        kind = _kind_of_line(line.get("product") or "", line.get("description") or "", _money(line.get("amount")))
        conn.execute(
            """INSERT OR REPLACE INTO customer_invoice_lines
               (invoice_number, line_no, product, description, qty, price, amount, kind)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                no,
                len(by_no[no]),
                line.get("product"),
                line.get("description"),
                line.get("qty") or 1,
                _money(line.get("price")),
                _money(line.get("amount")),
                kind,
            ),
        )
        n_line += 1

    n_pay = 0
    for row in _load(PAYMENTS_JSON).get("rows") or []:
        name = display_name(row.get("payee")) or row.get("payee")
        if not name:
            continue
        method = row.get("method") or "eft"
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, method)
               VALUES (?,?,?,?,?,?)""",
            (
                row.get("date"),
                name,
                -abs(_money(row.get("amount"))),
                "Cash" if method == "cash" else "Payment",
                "qb-cash" if method == "cash" else "qb-eft",
                method,
            ),
        )
        n_pay += 1

    n_do = 0
    for row in _load(NETCASH_JSON).get("rows") or []:
        name = display_name(row.get("payee")) or row.get("payee")
        if not name:
            continue
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, method)
               VALUES (?,?,?,?,?,?)""",
            (
                row.get("date"),
                name,
                -abs(_money(row.get("amount"))),
                "Debit order",
                "qb-do",
                "do",
            ),
        )
        n_do += 1

    n_credit = 0
    for row in credits:
        name = display_name(row.get("name")) or row.get("name")
        if not name or not _money(row.get("amount")):
            continue
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, method)
               VALUES (?,?,?,?,?,?)""",
            (
                row.get("date"),
                name,
                -abs(_money(row.get("amount"))),
                f"Credit note {row.get('number') or ''}".strip(),
                "qb-credit",
                "credit",
            ),
        )
        n_credit += 1

    n_bounce = 0
    for row in KNOWN_BOUNCES:
        name = display_name(row["customer"]) or row["customer"]
        conn.execute(
            """INSERT OR IGNORE INTO customer_do_events
               (action_date, customer, amount, result, note, source)
               VALUES (?,?,?,?,?,?)""",
            (
                row["action_date"],
                name,
                _money(row["amount"]),
                row["result"],
                row["note"],
                row["source"],
            ),
        )
        n_bounce += 1

    n_synth = _synth_do(conn, kind_by_no)
    conn.commit()
    return {
        "invoices": n_inv,
        "lines": n_line,
        "eft": n_pay,
        "do": n_do,
        "credits": n_credit,
        "bounces": n_bounce,
        "do_synth": n_synth,
    }


def _already_paid(conn: sqlite3.Connection, key: str, day: str, amount: float) -> bool:
    for paid_on, customer, amt in conn.execute(
        "SELECT paid_on, customer, amount FROM customer_payments"
    ):
        if canon_key(customer) != key:
            continue
        if paid_on == day and abs(abs(_money(amt)) - abs(amount)) <= 0.02:
            return True
    return False


def _synth_do(conn: sqlite3.Connection, kind_by_no: dict[str, str]) -> int:
    """Collected D/O for monthly invoices. Skip pending 5 Oct and bounced months."""
    bounced = {
        (canon_key(r["customer"]), r["action_date"][:7])
        for r in KNOWN_BOUNCES
    }
    cutoff = date.fromisoformat(PENDING_DO["action_date"])
    if PENDING_DO.get("collected"):
        cutoff = add_months(cutoff, 0)
        from datetime import timedelta

        cutoff = cutoff + timedelta(days=1)
    n = 0
    rows = conn.execute(
        "SELECT invoice_number, invoice_date, customer, amount FROM customer_invoices"
    ).fetchall()
    for number, inv_date, customer, amount in rows:
        book = client_row(customer)
        if not book or book.get("method") != "debit-order":
            continue
        if kind_by_no.get(str(number)) != "monthly":
            continue
        try:
            day = date.fromisoformat(inv_date)
        except (TypeError, ValueError):
            continue
        collect = collection_for(day)
        if collect >= cutoff:
            continue
        key = canon_key(customer)
        if (key, collect.isoformat()[:7]) in bounced:
            continue
        if _already_paid(conn, key, collect.isoformat(), _money(amount)):
            continue
        month_paid = 0.0
        for rec in conn.execute("SELECT paid_on, customer, amount FROM customer_payments"):
            if canon_key(rec[1]) == key and (rec[0] or "")[:7] == collect.isoformat()[:7]:
                month_paid += abs(_money(rec[2]))
        if month_paid >= abs(_money(amount)) - 0.02:
            continue
        billed = 0.0
        paid = 0.0
        for rec in conn.execute("SELECT customer, amount FROM customer_invoices"):
            if canon_key(rec[0]) == key:
                billed += _money(rec[1])
        for rec in conn.execute("SELECT customer, amount FROM customer_payments"):
            if canon_key(rec[0]) == key:
                paid += abs(_money(rec[1]))
        if paid + abs(_money(amount)) > billed + 0.02:
            continue
        name = display_name(customer) or customer
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, method)
               VALUES (?,?,?,?,?,?)""",
            (
                collect.isoformat(),
                name,
                -abs(_money(amount)),
                "Debit order",
                "qb-do-synth",
                "do",
            ),
        )
        n += 1
    return n


def _rows(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    invoices = [
        {
            "invoice_number": r[0],
            "invoice_date": r[1],
            "customer": r[2],
            "amount": r[3],
            "source": r[4] if len(r) > 4 else "",
        }
        for r in conn.execute(
            """SELECT invoice_number, invoice_date, customer, amount,
                      COALESCE(source,'') FROM customer_invoices ORDER BY invoice_date"""
        )
    ]
    payments = [
        {
            "paid_on": r[0],
            "customer": r[1],
            "amount": r[2],
            "note": r[3],
            "source": r[4],
            "method": r[5] if len(r) > 5 else None,
        }
        for r in conn.execute(
            "SELECT paid_on, customer, amount, note, source, method FROM customer_payments ORDER BY paid_on, id"
        )
    ]
    return invoices, payments


def _books_invoice(row: dict) -> bool:
    src = (row.get("source") or "qb-list").lower()
    return not src.startswith("gowifi-")


def fifo_statement(
    invoices: list[dict],
    payments: list[dict],
    name: str,
    today: date | None = None,
) -> dict:
    """Oldest invoice, then the payment(s) that clear it, then the next invoice."""
    from invoice_canned import fmt_date

    key = canon_key(name)
    invs = sorted(
        (
            i
            for i in invoices
            if canon_key(i.get("customer")) == key and _books_invoice(i)
        ),
        key=lambda i: (i.get("invoice_date") or "", str(i.get("invoice_number") or "")),
    )
    pays = sorted(
        (p for p in payments if canon_key(p.get("customer")) == key),
        key=lambda p: (p.get("paid_on") or "", str(p.get("note") or "")),
    )
    pool = [
        {
            "date": p.get("paid_on"),
            "left": abs(_money(p.get("amount"))),
            "method": (p.get("method") or "eft").lower(),
            "note": p.get("note") or "Payment",
        }
        for p in pays
    ]
    idx = 0
    lines: list[dict] = []
    balance = 0.0
    billed = 0.0
    paid = 0.0

    def pay_what(note: str, method: str) -> str:
        n = (note or "").lower()
        if n.startswith("debit"):
            return "Debit order"
        if method == "cash":
            return "Cash"
        if method == "credit":
            return note or "Credit"
        return "Payment"

    for inv in invs:
        amt = _money(inv.get("amount"))
        billed = round(billed + amt, 2)
        balance = round(balance + amt, 2)
        no = str(inv.get("invoice_number") or "")
        lines.append(
            {
                "date": inv.get("invoice_date"),
                "date_fmt": fmt_date(inv.get("invoice_date")),
                "kind": "invoice",
                "ref": no,
                "what": f"Invoice {no}",
                "amount": amt,
                "balance": balance,
            }
        )
        need = amt
        while need > 0.004:
            pick = None
            for i, p in enumerate(pool):
                if p["left"] > 0.004 and abs(p["left"] - need) <= 0.02:
                    pick = i
                    break
            if pick is None:
                for i, p in enumerate(pool):
                    if p["left"] > 0.004:
                        pick = i
                        break
            if pick is None:
                break
            use = min(pool[pick]["left"], need)
            pool[pick]["left"] = round(pool[pick]["left"] - use, 2)
            paid = round(paid + use, 2)
            balance = round(balance - use, 2)
            lines.append(
                {
                    "date": pool[pick]["date"],
                    "date_fmt": fmt_date(pool[pick]["date"]),
                    "kind": "payment",
                    "ref": "",
                    "what": pay_what(pool[pick]["note"], pool[pick]["method"]),
                    "amount": -use,
                    "balance": balance,
                }
            )
            need = round(need - use, 2)
    for p in pool:
        left = p["left"]
        if left <= 0.004:
            continue
        paid = round(paid + left, 2)
        balance = round(balance - left, 2)
        lines.append(
            {
                "date": p["date"],
                "date_fmt": fmt_date(p["date"]),
                "kind": "payment",
                "ref": "",
                "what": pay_what(p["note"], p["method"]),
                "amount": -left,
                "balance": balance,
            }
        )
    master, sub = split_qb_name(name)
    others = []
    seen_subs = {key}
    for inv in invoices:
        cust = inv.get("customer") or ""
        m, s = split_qb_name(cust)
        if canon_key(m) != canon_key(master):
            continue
        ck = canon_key(cust)
        if ck in seen_subs:
            continue
        seen_subs.add(ck)
        others.append(
            {
                "name": s or m,
                "key": ck,
                "cancelled": "deleted" in cust.lower() or ck == "aljo van",
            }
        )
    return {
        "as_at": (today or date.today()).isoformat(),
        "master": master or display_name(name) or name,
        "sub": sub or master or (display_name(name) or name),
        "own_sub": sub is None,
        "other_subs": others,
        "lines": lines,
        "billed": billed,
        "paid": paid,
        "due": balance,
    }


def _bounces(conn: sqlite3.Connection, key: str) -> list[dict]:
    out = []
    try:
        rows = conn.execute(
            "SELECT action_date, customer, amount, result, note FROM customer_do_events ORDER BY action_date"
        )
    except sqlite3.OperationalError:
        return out
    for rec in rows:
        if canon_key(rec[1]) != key:
            continue
        out.append(
            {
                "action_date": rec[0],
                "customer": rec[1],
                "amount": _money(rec[2]),
                "result": rec[3],
                "note": rec[4],
            }
        )
    return out


def account_as_at(
    conn: sqlite3.Connection,
    name: str,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    key = canon_key(name)
    book = client_row(name)
    invoices, payments = _rows(conn)
    display = display_name(name) or name
    ledger = fifo_statement(invoices, payments, display, today)
    stmt = statement_on_invoice(invoices, payments, display, as_at=today)
    billed = ledger["billed"]
    paid = ledger["paid"]
    balance = ledger["due"]
    bounces = _bounces(conn, key)
    open_bounce = [b for b in bounces if (b.get("result") or "").lower() == "bounced"]
    pending = None
    method = (book or {}).get("method") or "eft"
    monthly = _money((book or {}).get("amount")) if book else None
    if method == "debit-order":
        pending_day = date.fromisoformat(PENDING_DO["action_date"])
        if PENDING_DO.get("collected") and today >= pending_day:
            pending = {
                "action_date": PENDING_DO["action_date"],
                "amount": monthly,
                "status": "collected",
                "reconciled": True,
                "unpaid_value": PENDING_DO.get("unpaid_value") or 0,
            }
        elif not PENDING_DO.get("collected") and (
            today >= pending_day or today >= date(pending_day.year, pending_day.month, 1)
        ):
            pending = {
                "action_date": PENDING_DO["action_date"],
                "amount": monthly,
                "status": "authorised · not collected",
                "reconciled": False,
            }
    pending_amt = _money((pending or {}).get("amount")) if pending else 0
    due_today = balance
    in_do_grace = False
    if pending and not pending.get("reconciled") and due_today >= pending_amt - 0.02:
        due_today = round(due_today - pending_amt, 2)
        in_do_grace = True
    bounced = bool(open_bounce) and due_today > 0.004
    if bounced:
        status = "bounced"
    elif abs(due_today) <= 0.004 and not in_do_grace:
        status = "paid-up"
    elif in_do_grace and abs(due_today) <= 0.004:
        status = "do-pending"
    elif abs(due_today) <= 0.004:
        status = "paid-up"
    else:
        status = "owes"
    return {
        "name": display,
        "as_at": today.isoformat(),
        "billed": billed,
        "paid": paid,
        "balance": balance,
        "due": due_today,
        "monthly": monthly,
        "method": method,
        "pay": "D/O" if method == "debit-order" else "EFT",
        "pending_do": pending,
        "in_do_grace": in_do_grace,
        "bounces": open_bounce,
        "bounced": bounced,
        "suspension_notice": bounced,
        "status": status,
        "nil": abs(due_today) <= 0.004 and not bounced,
        "statement": stmt,
        "ledger": ledger.get("lines") or [],
        "master": ledger.get("master"),
        "sub": ledger.get("sub"),
        "own_sub": ledger.get("own_sub"),
        "other_subs": ledger.get("other_subs") or [],
        "last_payment": stmt.get("last_payment"),
    }


def for_export(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    ingest(conn)
    cards = []
    seen = set()
    for row in CLIENTS:
        pack = account_as_at(conn, row["name"], today)
        seen.add(canon_key(row["name"]))
        cards.append(pack)
    invoices, _payments = _rows(conn)
    for inv in invoices:
        key = canon_key(inv.get("customer"))
        if key in seen:
            continue
        seen.add(key)
        cards.append(account_as_at(conn, inv.get("customer"), today))
    cards.sort(key=lambda r: (r.get("name") or "").lower())
    return {
        "as_at": today.isoformat(),
        "note": (
            "Due is as at today. D/O is grace until reconciled. "
            "A bounce stays due and raises a suspension notice. "
            "5 Oct 2026 batch 2571994 collected — unpaid R0."
        ),
        "count": len(cards),
        "accounts": cards,
    }


def self_test() -> int:
    failed = 0
    conn = sqlite3.connect(":memory:")
    ingest(conn)
    today = date(2026, 10, 5)
    marlene = account_as_at(conn, "Van Eeden, Marlene/Georg", today)
    if abs((marlene["due"] or 0) - 7180) > 0.5:
        print("FAIL marlene-due", marlene["due"], marlene["billed"], marlene["paid"])
        failed += 1
    elif marlene["status"] != "owes" or marlene.get("in_do_grace"):
        print("FAIL marlene-eft-due", marlene)
        failed += 1
    else:
        print("OK marlene-real-due", marlene["due"])
    want = account_as_at(conn, "Wantling, David", today)
    if not (want.get("pending_do") or {}).get("reconciled"):
        print("FAIL wantling-oct5-not-applied", want.get("pending_do"), want["due"])
        failed += 1
    elif (want["due"] or 0) > 50:
        print("FAIL wantling-still-due", want["due"], want["billed"], want["paid"])
        failed += 1
    else:
        print("OK wantling-oct5-collected", want["due"])
    hav = account_as_at(conn, "Havenga, Daniel", today)
    if not hav.get("bounces"):
        print("FAIL havenga-bounce", hav)
        failed += 1
    else:
        print("OK havenga-bounce-recorded")
    if not PENDING_DO.get("collected") or (PENDING_DO.get("unpaid_volume") or 0) != 0:
        print("FAIL oct5-not-collected", PENDING_DO)
        failed += 1
    else:
        print("OK oct5-collected-unpaid-0")
    amoroc = account_as_at(conn, "Amoroc Doors", today)
    lines = amoroc.get("ledger") or []
    if abs((amoroc["billed"] or 0) - 9310.25) > 0.02 or abs((amoroc["paid"] or 0) - 9310.25) > 0.02:
        print("FAIL amoroc-totals", amoroc["billed"], amoroc["paid"], amoroc["due"])
        failed += 1
    elif abs(amoroc["due"] or 0) > 0.02:
        print("FAIL amoroc-due", amoroc["due"])
        failed += 1
    elif not lines or str(lines[0].get("ref")) != "2335" or abs((lines[0].get("amount") or 0) - 2345.25) > 0.02:
        print("FAIL amoroc-first-invoice", lines[:2] if lines else None)
        failed += 1
    elif lines[1].get("kind") != "payment" or abs((lines[1].get("amount") or 0) + 2345.25) > 0.02:
        print("FAIL amoroc-first-payment", lines[1] if len(lines) > 1 else None)
        failed += 1
    elif any("699" in str(r.get("amount")) and r.get("kind") == "invoice" and abs((r.get("amount") or 0) - 699) < 0.02 for r in lines):
        print("FAIL amoroc-has-aljo", [r for r in lines if abs((r.get("amount") or 0)) == 699])
        failed += 1
    elif not amoroc.get("own_sub") or (amoroc.get("master") or "") != "Amoroc Doors":
        print("FAIL amoroc-own-sub", amoroc.get("master"), amoroc.get("own_sub"))
        failed += 1
    elif not any(s.get("cancelled") and "aljo" in (s.get("key") or "") for s in amoroc.get("other_subs") or []):
        print("FAIL amoroc-aljo-other-sub", amoroc.get("other_subs"))
        failed += 1
    else:
        print("OK amoroc-statement", amoroc["due"], "lines", len(lines))
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
