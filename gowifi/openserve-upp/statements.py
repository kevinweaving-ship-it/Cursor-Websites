#!/usr/bin/env python3
"""Client statements: invoices vs EFT / D/O. Forget QuickBooks open flags.

Three feeds. QB is not the books for paid / unpaid / D/O.
- QB invoice: yes or no, what it is for, amount. Not apply. Not D/O paid.
- EFT: FNB bank total, then EFT B/F down oldest invoices.
- D/O: named Netcash batch only (paid or unpaid). QB never shows that.

Simple books:
- First month (new fibre): install + pro-rata / first month. Payment is D/O
  only when a named Netcash batch collected it. Otherwise FNB EFT.
- Next months on D/O: invoice + D/O. Amounts still match after a price change.
- D/O on the statement is only a named Netcash batch row (paid or unpaid).
  Nothing is invented. No synth. No auto-clear.
- D/O matches the invoice for that Netcash batch (collection month). Never
  steal another month's invoice.
- Named FNB EFT is one bank total. First line shows that total and pays
  the oldest open invoice. Next lines are EFT B/F (what is left) on the
  next oldest invoice, until the EFT is used.
- Reconnection / un-suspend is a once-off penalty after non-payment — not a
  standard monthly invoice and not on the D/O. It stays due until a named EFT
  so the client sees the cost of not paying.
- Statement is every invoice vs every EFT or D/O. No invented unpaids from
  FNB Netcash clearing / HAVENGA REFUND.
"""
from __future__ import annotations

import json
import re
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
    is_offset,
    split_qb_name,
)
from invoice_canned import statement_on_invoice
from invoice_list import NAMED_INVOICES
from invoice_list import classify as classify_invoices
from invoice_list import is_do_return_text, is_reconnect_text

DATA_DIR = Path(__file__).resolve().parent / "data"
INVOICES_JSON = DATA_DIR / "qb_invoices.json"
SALES_JSON = DATA_DIR / "qb_sales.json"
PAYMENTS_JSON = DATA_DIR / "qb_payments.json"
NETCASH_JSON = DATA_DIR / "qb_do_payments.json"
SALES_XLS = DATA_DIR / "sales.xls"
SALES_REG_JSON = DATA_DIR / "qb_sales_register.json"
DELETED_STATUSES = {"deleted", "void", "voided"}
GRACE_DAYS = 7
RECONNECT_LABEL = "Reconnection after unpaid · un-suspend penalty"
DO_RETURN_LABEL = "D/O return · collect EFT"
# (date, client key) -> FNB bank EFT total for that day (splits summed).
BANK_EFT: dict[tuple[str, str], float] = {}
NOT_ON_MONTHLY_DO = frozenset({"reconnect", "install", "do-return", "equipment", "fee"})
# QB put these on the wrong client. Never show, never due.
NOT_CLIENT_INVOICE = frozenset(
    {
        "3055",  # Cupido 7/3.5 wireless R439 — he is Fibre 50/25 R759
    }
)

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
    if is_reconnect_text(blob):
        return "reconnect"
    if any(w in blob for w in ("install", "cabling", "setup fee", "fibre installation")):
        return "install"
    if any(w in blob for w in ("router", "hardware", "ubiquiti", "aircube", "cudy")):
        return "equipment"
    if re.search(r"\b(nano|ont|bracket)\b", blob):
        return "equipment"
    if "rental" in blob:
        return "rental"
    if any(w in blob for w in ("pro rata", "prorate", "pro-rata", "pro rate")):
        return "monthly"
    if "debit order return" in blob or "do return" in blob:
        return "do-return"
    if any(w in blob for w in ("cancel", "early cancellation")):
        return "fee"
    if any(w in blob for w in ("monthly", "webstream", "wifi -", "gowifi", "fibre", "fiber", "uncapped", "contribution")):
        return "monthly"
    return "other"


def _family_from_lines(line_kinds: list[str], memo: str = "", list_kind: str = "") -> str:
    kinds = {k for k in line_kinds if k}
    if "reconnect" in kinds or is_reconnect_text(memo):
        return "reconnect"
    if "do-return" in kinds or list_kind == "do-return" or is_do_return_text(memo):
        return "do-return"
    if list_kind == "monthly":
        return "monthly"
    if "install" in kinds:
        return "install"
    if "equipment" in kinds:
        return "equipment"
    if "fee" in kinds and not (kinds & {"monthly", "rental"}):
        return "fee"
    if list_kind and list_kind != "monthly":
        return "extra"
    return "monthly"


def _invoice_families(conn: sqlite3.Connection, kind_by_no: dict[str, str] | None = None) -> dict[str, str]:
    """monthly vs once-off (reconnect / install / D/O return). Memo + lines win over amount."""
    if kind_by_no is None:
        classified = classify_invoices()
        kind_by_no = {
            r["number"]: r.get("family") or r["kind"]
            for r in (classified.get("queries") or []) + (classified.get("monthly") or [])
        }
    by_no: dict[str, list[str]] = {}
    memos: dict[str, str] = {}
    try:
        for rec in conn.execute("SELECT invoice_number, kind FROM customer_invoice_lines"):
            by_no.setdefault(str(rec[0]), []).append(rec[1] or "")
        for rec in conn.execute("SELECT invoice_number, description FROM customer_invoices"):
            memos[str(rec[0])] = rec[1] or ""
    except sqlite3.OperationalError:
        pass
    out: dict[str, str] = {}
    for no in set(by_no) | set(memos) | set(kind_by_no):
        listed = kind_by_no.get(no) or ""
        if listed == "reconnect":
            list_kind = "query"
            memo = memos.get(no) or "reconnection"
        elif listed == "do-return":
            list_kind = "do-return"
            memo = memos.get(no) or "debit order return"
        else:
            list_kind = listed
            memo = memos.get(no) or ""
        out[no] = _family_from_lines(by_no.get(no) or [], memo, list_kind)
    return out


def _ingest_named_invoices(conn: sqlite3.Connection, kind_by_no: dict[str, str]) -> int:
    """Real QB invoices that landed after the last list dump. Do not invent paid."""
    n = 0
    for row in NAMED_INVOICES:
        no = str(row.get("number") or "")
        try:
            number = int(no)
        except (TypeError, ValueError):
            continue
        if not no or not row.get("name") or _money(row.get("amount")) <= 0.004:
            continue
        kind_by_no[no] = row.get("family") or "query"
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
                _money(row.get("open") if row.get("open") is not None else row.get("amount")),
                "open",
                "qb-named",
                row.get("memo") or "",
            ),
        )
        conn.execute(
            """INSERT OR REPLACE INTO customer_invoice_lines
               (invoice_number, line_no, product, description, qty, price, amount, kind)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                no,
                1,
                row.get("product") or "Other",
                row.get("memo") or "",
                row.get("qty") or 1,
                _money(row.get("price") if row.get("price") is not None else row.get("amount")),
                _money(row.get("amount")),
                row.get("family") or "other",
            ),
        )
        n += 1
    return n


def ingest(conn: sqlite3.Connection) -> dict:
    ensure(conn)
    try:
        from recon import ingest as recon_ingest

        recon_ingest(conn)
    except Exception:
        pass
    conn.execute("DELETE FROM customer_invoices WHERE source IN ('qb-list','qb-sales')")
    conn.execute("DELETE FROM customer_invoice_lines")
    conn.execute(
        "DELETE FROM customer_payments WHERE source IN "
        "('qb-eft','qb-cash','qb-do','qb-credit','qb-do-synth','netcash-alloc',"
        "'fnb-alloc','fnb-eft','netcash-do')"
    )
    conn.execute(
        "DELETE FROM customer_do_events WHERE source IN "
        "('fnb','qb-do-synth','netcash','netcash-alloc')"
    )

    invoices = list((_load(INVOICES_JSON).get("rows") or []))
    sales = _load(SALES_JSON)
    lines = list(sales.get("rows") or [])
    credits = list(sales.get("credits") or [])
    classified = classify_invoices()
    kind_by_no = {
        r["number"]: r.get("family") or r["kind"]
        for r in (classified.get("queries") or []) + (classified.get("monthly") or [])
    }

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
    n_inv += _ingest_named_invoices(conn, kind_by_no)

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
        book = client_row(name)
        # D/O clients: FNB + Netcash only. QB A/R payments are apply, not cash.
        if book and book.get("method") == "debit-order":
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

    n_nc = _apply_bank_matches(conn)
    _label_do_settlements(conn)
    _collapse_eft_to_bank(conn)
    n_synth = 0
    n_runs = 0
    conn.commit()
    from recon import checksum_real_money

    return {
        "invoices": n_inv,
        "lines": n_line,
        "eft": n_pay,
        "do": n_do,
        "credits": n_credit,
        "netcash": n_nc,
        "do_synth": n_synth,
        "do_runs": n_runs,
        "checksum": checksum_real_money(conn),
    }


def _apply_bank_matches(conn: sqlite3.Connection) -> int:
    """Sep invoice → Oct Netcash batch. Paid D/O or unpaid; named FNB EFT can catch up."""
    n = 0
    try:
        from recon import client_receipts, client_unpaid
    except Exception:
        return 0
    for rec in client_receipts(conn):
        name = display_name(rec.get("customer")) or rec.get("customer")
        if not name:
            continue
        day = rec.get("paid_on") or ""
        amt = abs(_money(rec.get("amount")))
        if _already_paid(conn, canon_key(name), day, amt):
            continue
        do = (rec.get("method") or "") == "do" or "netcash" in (rec.get("source") or "")
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, method)
               VALUES (?,?,?,?,?,?)""",
            (
                day,
                name,
                -amt,
                rec.get("note") or ("D/O paid" if do else "EFT"),
                rec.get("source") or ("netcash-alloc" if do else "fnb-alloc"),
                "do" if do else "eft",
            ),
        )
        n += 1
    for rec in client_unpaid(conn):
        name = display_name(rec.get("customer")) or rec.get("customer")
        if not name:
            continue
        conn.execute(
            """INSERT OR IGNORE INTO customer_do_events
               (action_date, customer, amount, result, note, source)
               VALUES (?,?,?,?,?,?)""",
            (
                rec.get("action_date"),
                name,
                _money(rec.get("amount")),
                "unpaid",
                rec.get("note") or "Debit order unpaid",
                "netcash-alloc",
            ),
        )
        n += 1
    return n


def _do_unpaid_months(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    """Unpaid D/O months from Netcash tables only. Not a typed list."""
    out: set[tuple[str, str]] = set()
    try:
        for rec in conn.execute(
            "SELECT action_date, customer, result, source FROM customer_do_events"
        ):
            if (rec[2] or "").lower() not in {"unpaid", "bounced"}:
                continue
            if "netcash" not in (rec[3] or "").lower():
                continue
            out.add((canon_key(rec[1]), (rec[0] or "")[:7]))
        for rec in conn.execute(
            """SELECT paid_on, alloc_to, result, source FROM netcash_tx
               WHERE alloc_kind='client_unpaid'
                 AND source IN ('netcash-xls','netcash-items','netcash-masterfile')
                 AND COALESCE(batch_id,'') != ''"""
        ):
            if (rec[2] or "").lower() not in {"unpaid", "bounced"}:
                continue
            out.add((canon_key(rec[1]), (rec[0] or "")[:7]))
    except sqlite3.OperationalError:
        pass
    return out


def _collapse_eft_to_bank(conn: sqlite3.Connection) -> None:
    """One EFT per client per day when FNB split the bank credit. FNB total wins."""
    BANK_EFT.clear()
    fnb: dict[tuple[str, str], tuple[float, int, str]] = {}
    real_src = {"fnb_live", "fnb_online", "fnb_api", "fnb_history", "fnb_qb"}
    try:
        grouped: dict[tuple[str, str], list] = {}
        for rec in conn.execute(
            """SELECT paid_on, alloc_to, alloc_key, ABS(COALESCE(deposit, amount)), source
               FROM fnb_tx WHERE alloc_kind='client_paid'"""
        ):
            day = str(rec[0] or "")[:10]
            key = canon_key(rec[2] or rec[1])
            grouped.setdefault((day, key), []).append(rec)
        for (day, key), items in grouped.items():
            bank_items = [r for r in items if (r[4] or "") in real_src]
            use = bank_items or items
            total = round(sum(abs(_money(r[3])) for r in use), 2)
            name = display_name((bank_items or items)[0][1]) or (bank_items or items)[0][1]
            fnb[(day, key)] = (total, len(use), name)
            if len(use) >= 2 or bank_items:
                BANK_EFT[(day, key)] = total
    except sqlite3.OperationalError:
        return
    from collections import defaultdict

    by: dict[tuple[str, str], list] = defaultdict(list)
    for rec in conn.execute(
        "SELECT id, paid_on, customer, amount, source, method FROM customer_payments"
    ):
        method = (rec[5] or "eft").lower()
        src = rec[4] or ""
        if method in {"do", "debit", "debit-order"} or src in {"qb-credit", "qb-cash"}:
            continue
        if "netcash" in src or src.startswith("qb-do"):
            continue
        by[(str(rec[1] or "")[:10], canon_key(rec[2]))].append(rec)
    for (day, key), items in by.items():
        bank = fnb.get((day, key))
        name = bank[2] if bank else (display_name(items[0][2]) or items[0][2])
        if bank:
            total = bank[0]
        else:
            total = _day_eft_total(
                [{"amount": item[3], "source": item[4]} for item in items]
            )
        if total <= 0.004:
            continue
        BANK_EFT[(day, key)] = total
        if len(items) == 1 and abs(abs(_money(items[0][3])) - total) <= 0.02:
            continue
        for item in items:
            conn.execute("DELETE FROM customer_payments WHERE id=?", (item[0],))
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, method)
               VALUES (?,?,?,?,?,?)""",
            (day, name, -total, "EFT", "fnb-alloc" if bank else "qb-eft", "eft"),
        )


def _label_do_settlements(conn: sqlite3.Connection) -> None:
    """Named Netcash paid only. No invented D/O."""
    named = set()
    try:
        for rec in conn.execute(
            """SELECT paid_on, alloc_key, amount FROM netcash_tx
               WHERE alloc_kind='client_paid'"""
        ):
            named.add((str(rec[0] or "")[:10], canon_key(rec[1]), round(abs(_money(rec[2])), 2)))
    except sqlite3.OperationalError:
        pass
    for rec in conn.execute(
        "SELECT id, paid_on, customer, amount, method FROM customer_payments"
    ):
        day = str(rec[1] or "")[:10]
        key = canon_key(rec[2])
        amt = round(abs(_money(rec[3])), 2)
        book = client_row(rec[2])
        if not book or book.get("method") != "debit-order":
            continue
        hit = (day, key, amt) in named
        if not hit:
            continue
        conn.execute(
            """UPDATE customer_payments
               SET method='do', note='D/O paid'
               WHERE id=?""",
            (rec[0],),
        )


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
    """Do not invent D/O. Netcash named paid / unpaid only."""
    return 0


def _rows(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    invoices = [
        {
            "invoice_number": r[0],
            "invoice_date": r[1],
            "customer": r[2],
            "amount": r[3],
            "source": r[4] if len(r) > 4 else "",
            "status": r[5] if len(r) > 5 else "",
        }
        for r in conn.execute(
            """SELECT invoice_number, invoice_date, customer, amount,
                      COALESCE(source,''), COALESCE(status,'')
               FROM customer_invoices ORDER BY invoice_date"""
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


def _bank_money(row: dict) -> bool:
    """FNB EFT or named Netcash D/O. Not a QuickBooks apply/split row."""
    src = str(row.get("source") or "").lower()
    return src.startswith("fnb") or "netcash" in src


def _payment_bucket(source: str | None) -> str:
    src = str(source or "").lower()
    if src in {"fnb_live", "fnb_online", "fnb_api", "fnb_qb"}:
        return "fnb_live"
    if src.startswith("fnb"):
        return "fnb_xls"
    if "netcash" in src:
        return "netcash"
    return "qb"


def _day_eft_total(items: list[dict]) -> float:
    """One bank EFT for the day. QB apply splits are not extra deposits."""
    buckets = {"fnb_live": 0.0, "fnb_xls": 0.0, "qb": 0.0}
    for row in items:
        src = _payment_bucket(row.get("source"))
        if src == "netcash":
            continue
        buckets[src] += abs(_money(row.get("amount")))
    return round(buckets["fnb_live"] or buckets["fnb_xls"] or buckets["qb"] or 0.0, 2)


def _pay_is_do(row: dict) -> bool:
    return (row.get("method") or "").lower() in {"do", "debit", "debit-order"} or (
        row.get("note") or ""
    ).lower().startswith("debit")


def _collapse_client_day_efts(pays: list[dict], name: str) -> list[dict]:
    """One EFT per day. Same-day QB/FNB apply rows are one bank payment."""
    from collections import defaultdict

    kept: list[dict] = []
    by_day: dict[str, list[dict]] = defaultdict(list)
    for row in pays:
        method = (row.get("method") or "").lower()
        if _pay_is_do(row) or method in {"credit", "cash"}:
            kept.append(row)
            continue
        by_day[str(row.get("paid_on") or "")[:10]].append(row)
    for day, items in by_day.items():
        if not day:
            kept.extend(items)
            continue
        amt = _day_eft_total(items)
        if amt <= 0.004:
            continue
        src = next((i.get("source") for i in items if _bank_money(i)), items[0].get("source") or "qb-eft")
        kept.append(
            {
                "paid_on": day,
                "customer": name,
                "amount": -amt,
                "note": "EFT",
                "method": "eft",
                "source": src,
            }
        )
    return kept


def _books_invoice(row: dict) -> bool:
    no = str(row.get("invoice_number") or row.get("number") or row.get("ref") or "")
    if no in NOT_CLIENT_INVOICE:
        return False
    src = (row.get("source") or "qb-list").lower()
    if src.startswith("gowifi-"):
        return False
    if src == "quickbooks" and (row.get("status") or "").lower() == "historical":
        return False
    return True


def _invoice_deleted(row: dict) -> bool:
    """Deleted invoices never show and cannot carry an amount due."""
    status = (row.get("status") or "").strip().lower()
    if status in DELETED_STATUSES:
        return True
    typ = (row.get("type") or "").strip().lower()
    return typ in DELETED_STATUSES


def _xls_day(value):
    from invoice_canned import parse_day

    day = parse_day(value)
    if day:
        return day
    if isinstance(value, (int, float)) and value > 20000:
        try:
            import xlrd

            parts = xlrd.xldate_as_tuple(value, 0)
            return date(*parts[:3])
        except Exception:
            return None
    return None


def _read_sales_xls(path: Path) -> list[dict]:
    try:
        import xlrd
    except ImportError:
        return []
    sh = xlrd.open_workbook(str(path)).sheet_by_index(0)
    header = 1
    for r in range(min(5, sh.nrows)):
        vals = [str(sh.cell_value(r, c)).strip().lower() for c in range(sh.ncols)]
        if "type" in vals and ("amount" in vals or "no." in vals or "no" in vals):
            header = r
            break
    cols = {str(sh.cell_value(header, c)).strip().lower(): c for c in range(sh.ncols)}

    def cell(row, *names):
        for n in names:
            if n in cols:
                return sh.cell_value(row, cols[n])
        return ""

    out = []
    for r in range(header + 1, sh.nrows):
        typ = str(cell(r, "type") or "").strip()
        if typ.lower() == "deposit":
            continue
        if typ.lower() not in {"invoice", "payment", "credit"}:
            continue
        if _invoice_deleted({"type": typ, "status": cell(r, "status")}):
            continue
        day = _xls_day(cell(r, "date"))
        out.append(
            {
                "date": day.isoformat() if day else str(cell(r, "date") or ""),
                "type": typ,
                "invoice_number": str(cell(r, "no.", "no") or "").strip(),
                "customer": str(cell(r, "customer") or "").strip(),
                "amount": _money(cell(r, "amount")),
                "memo": str(cell(r, "memo") or "").strip(),
                "status": str(cell(r, "status") or "").strip().lower(),
                "source": "qb-sales-xls",
            }
        )
    return out


def load_sales_register(path: Path | None = None) -> list[dict]:
    """QB Sales register: living invoices + applied payments. Deleted and deposits stay off."""
    xls = path or SALES_XLS
    if xls.exists() and xls.suffix.lower() in {".xls", ".xlsx"}:
        rows = _read_sales_xls(xls)
        if rows:
            return rows
    if SALES_REG_JSON.exists():
        return list((_load(SALES_REG_JSON).get("rows") or []))
    return []


def living_books(name: str, path: Path | None = None) -> tuple[list[dict], list[dict]] | None:
    """Only invoices still on the sales register. Deleted never show and never due."""
    rows = load_sales_register(path)
    if not rows:
        return None
    key = canon_key(name)
    mine = [r for r in rows if canon_key(r.get("customer")) == key and not _invoice_deleted(r)]
    if not mine:
        return None
    invoices = [
        {
            "invoice_number": r["invoice_number"],
            "invoice_date": r["date"],
            "customer": r["customer"],
            "amount": abs(r["amount"]),
            "source": "qb-sales-xls",
            "status": r.get("status") or "paid",
        }
        for r in mine
        if r["type"].lower() == "invoice"
    ]
    payments = [
        {
            "paid_on": r["date"],
            "customer": r["customer"],
            "amount": -abs(r["amount"]),
            "note": r.get("memo") or "Payment",
            "source": "qb-sales-xls",
            "method": "eft",
        }
        for r in mine
        if r["type"].lower() == "payment"
    ]
    return invoices, payments


def _stmt_desc(text: str | None, line_kind: str | None = None) -> str:
    """One short label. We are GoWiFi — never repeat the name on a line."""
    from invoice_canned import clean_description

    if (line_kind or "") == "reconnect" or is_reconnect_text(text):
        return RECONNECT_LABEL
    if (line_kind or "") == "do-return" or is_do_return_text(text):
        return DO_RETURN_LABEL
    t = clean_description(text)
    t = re.sub(r"(?i)\bgowifi\b", "", t)
    t = t.replace("Fiber", "Fibre")
    t = re.sub(r"\s+", " ", t).strip(" -·")
    low = t.lower()
    if (line_kind or "") == "reconnect" or is_reconnect_text(low):
        return RECONNECT_LABEL
    if any(
        w in low
        for w in (
            "month-to-month",
            "one-time setup",
            "free fibre installation",
            "early cancellation",
        )
    ):
        return "Fibre installation"
    return t


def _fold_invoice_what(lines: list[dict], conn: sqlite3.Connection | None) -> list[dict]:
    """Invoice is one line: date, number, what, amount. No extra item rows."""
    out = []
    for row in lines:
        if row.get("kind") == "line":
            continue
        if row.get("kind") != "invoice":
            out.append(row)
            continue
        no = str(row.get("ref") or "")
        bits = []
        for item in _sales_lines(no, conn):
            text = _stmt_desc(item.get("what") or "", item.get("line_kind"))
            if text and text not in bits:
                bits.append(text)
        rec = dict(row)
        if (row.get("family") or "") == "reconnect" or is_reconnect_text(row.get("what"), " ".join(bits)):
            rec["what"] = f"Invoice {no} · {RECONNECT_LABEL}"
        elif (row.get("family") or "") == "do-return" or is_do_return_text(row.get("what"), " ".join(bits)):
            rec["what"] = f"Invoice {no} · {DO_RETURN_LABEL}"
        else:
            rec["what"] = f"Invoice {no} {' · '.join(bits)}".strip() if bits else f"Invoice {no}"
        out.append(rec)
    return out


def _ledger_blocks(lines: list[dict]) -> list[dict]:
    """Invoice + its lines + the payment(s) that clear it. Oldest block first."""
    blocks: list[dict] = []
    cur = None
    leading = []
    for row in lines:
        kind = row.get("kind")
        if kind == "invoice":
            if cur is not None:
                blocks.append(cur)
            cur = {
                "invoice": row,
                "items": [],
                "payments": [],
                "open": _money(row.get("amount")),
            }
        elif kind == "line" and cur is not None:
            cur["items"].append(row)
        elif kind == "payment":
            if cur is None:
                leading.append(row)
            else:
                cur["payments"].append(row)
                cur["open"] = round(cur["open"] + _money(row.get("amount")), 2)
        elif cur is not None:
            cur["items"].append(row)
    if cur is not None:
        blocks.append(cur)
    if leading and blocks:
        blocks[0]["payments"] = leading + blocks[0]["payments"]
    elif leading:
        blocks.append({"invoice": None, "items": [], "payments": leading, "open": 0.0})
    return blocks


def invoice_due_on(inv: dict, book: dict | None) -> date | None:
    from invoice_canned import parse_day

    raw = inv.get("due_date") or inv.get("due") or inv.get("due_on")
    family = (inv.get("family") or "").lower()
    if family in NOT_ON_MONTHLY_DO:
        return parse_day(raw) or parse_day(inv.get("invoice_date") or inv.get("date"))
    if book and book.get("method") == "debit-order":
        inv_day = parse_day(inv.get("invoice_date") or inv.get("date"))
        if inv_day:
            return collection_for(inv_day)
    return parse_day(raw) or parse_day(inv.get("invoice_date") or inv.get("date"))


def invoice_tone(rec: dict, today: date) -> str:
    """Blue matched; orange pending; purple unpaid invoice; red D/O unpaid."""
    if rec.get("kind") == "unpaid":
        return "overdue"
    if rec.get("kind") != "invoice":
        return ""
    if _money(rec.get("open")) <= 0.004:
        return "matched"
    from invoice_canned import parse_day

    due = parse_day(rec.get("due_on")) or parse_day(rec.get("date"))
    if due and (today - due).days > GRACE_DAYS:
        return "unpaid"
    return "pending"


def present_ledger(
    lines: list[dict],
    today: date | None = None,
    show_money: bool = False,
) -> list[dict]:
    """Date order, newest at the top. Running balance after each row; top = amount due."""
    from invoice_canned import parse_day

    today = today or date.today()
    tagged = [dict(r) for r in lines if r.get("kind") != "line"]

    def _day(rec: dict):
        return parse_day(rec.get("date")) or date.min

    # Oldest first to rebuild the running balance, then flip for display.
    tagged.sort(
        key=lambda r: (
            _day(r),
            0 if r.get("kind") == "invoice" else 1 if r.get("kind") == "unpaid" else 2,
            str(r.get("ref") or ""),
        )
    )
    bal = 0.0
    for rec in tagged:
        if rec.get("kind") == "unpaid":
            rec["balance"] = bal
        else:
            bal = round(bal + _money(rec.get("amount")), 2)
            rec["balance"] = bal
    tagged.reverse()
    last_inv = next((r for r in tagged if r.get("kind") == "invoice"), None)
    last_pay = next((r for r in tagged if r.get("kind") == "payment"), None)
    for rec in tagged:
        due = _money(rec.get("open")) > 0.004 or rec.get("kind") == "unpaid"
        pin = rec is last_inv or rec is last_pay
        rec["due_row"] = due
        do_paid = rec.get("kind") == "payment" and (
            "D/O paid" in (rec.get("what") or "") or (rec.get("what") or "").startswith("Debit")
        )
        same_eft = (
            rec.get("kind") == "payment"
            and last_pay
            and (rec.get("date") or "") == (last_pay.get("date") or "")
        )
        rec["show"] = bool(
            due or pin or do_paid or same_eft or (show_money and rec.get("kind") == "payment")
        )
        rec["reconciled"] = not rec["show"]
        rec["tone"] = invoice_tone(rec, today)
    return tagged


def _sales_lines(number: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    from invoice_canned import clean_description

    out = []
    if conn is not None:
        try:
            for rec in conn.execute(
                """SELECT product, description, amount, kind FROM customer_invoice_lines
                   WHERE invoice_number=? ORDER BY line_no""",
                (str(number),),
            ):
                out.append(
                    {
                        "what": clean_description(rec[1] or rec[0]),
                        "amount": _money(rec[2]),
                        "kind": "line",
                        "line_kind": rec[3] or "",
                    }
                )
        except sqlite3.OperationalError:
            out = []
    if out:
        return out
    for row in _load(SALES_JSON).get("rows") or []:
        if str(row.get("number") or "") != str(number):
            continue
        out.append(
            {
                "what": clean_description(row.get("description") or row.get("product")),
                "amount": _money(row.get("amount")),
                "kind": "line",
                "line_kind": _kind_of_line(
                    row.get("product") or "",
                    row.get("description") or "",
                    _money(row.get("amount")),
                ),
            }
        )
    return out


def fifo_statement(
    invoices: list[dict],
    payments: list[dict],
    name: str,
    today: date | None = None,
    unpaid_do: list[dict] | None = None,
) -> dict:
    """D/O matches its batch invoice. EFT is one bank amount, oldest invoice first.

    Not QuickBooks apply. Full EFT on the first invoice, then EFT B/F on the
    next. FNB + Netcash are the money. QB is the invoice list / checksum.
    """
    from invoice_canned import fmt_date

    key = canon_key(name)
    book = client_row(name)
    unpaid_months = {
        (canon_key(u.get("customer") or name), (u.get("action_date") or "")[:7])
        for u in (unpaid_do or [])
        if (u.get("result") or "").lower() in {"unpaid", "bounced"}
    }
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
    pays = sorted(
        _collapse_client_day_efts(pays, name),
        key=lambda p: (p.get("paid_on") or "", str(p.get("note") or "")),
    )
    pool = [
        {
            "date": p.get("paid_on"),
            "left": abs(_money(p.get("amount"))),
            "orig": abs(_money(p.get("amount"))),
            "method": (p.get("method") or "eft").lower(),
            "note": p.get("note") or "Payment",
        }
        for p in pays
    ]
    lines: list[dict] = []
    balance = 0.0
    billed = 0.0
    paid = 0.0

    def pay_what(note: str, method: str) -> str:
        n = (note or "").lower()
        m = (method or "").lower()
        if m in {"do", "debit", "debit-order"} or n.startswith("debit") or n.startswith("d/o"):
            return "D/O paid"
        if m == "cash":
            return "Cash"
        if m == "credit":
            return note or "Credit"
        return "EFT"

    def _is_do(p: dict) -> bool:
        return (p.get("method") or "").lower() in {"do", "debit", "debit-order"} or (
            p.get("note") or ""
        ).lower().startswith("debit")

    def _pay_line(p: dict, no: str, use: float) -> dict:
        how = pay_what(p["note"], p["method"])
        left = p["left"]
        note = p.get("note") or ""
        batch = ""
        if "batch" in note.lower():
            parts = note.split("Batch", 1)
            if len(parts) == 2:
                batch = parts[1].strip().split()[0].strip("·")
        if how == "D/O paid":
            what = f"D/O paid · Invoice {no}"
            if batch:
                what = f"D/O paid · Batch {batch} · Invoice {no}"
        else:
            what = f"{how} {p['orig']:.2f} · Invoice {no}"
            if abs(p["orig"] - use) > 0.02:
                what = f"{how} {p['orig']:.2f} · Invoice {no} · paid {use:.2f}"
        rec = {
            "date": p["date"],
            "date_fmt": fmt_date(p["date"]),
            "kind": "payment",
            "ref": no,
            "what": what,
            "amount": -use,
            "balance": 0.0,
            "paid_amt": use,
            "leftover": left if left > 0.004 else 0.0,
        }
        return rec

    def _apply_do(inv_amt: float, need: float, family: str, collect_day: str | None, no: str):
        nonlocal paid, balance
        while need > 0.004:
            pick = None
            for i, p in enumerate(pool):
                if p["left"] <= 0.004 or not _is_do(p):
                    continue
                month_ok = collect_day and (p.get("date") or "")[:7] == collect_day[:7]
                # Same-amount match is only for once-off / install. Monthly D/O
                # stays on its collection month so Oct 599 cannot steal July.
                amt_ok = (not collect_day) and (
                    abs(p["left"] - need) <= 0.02 or abs(p["orig"] - inv_amt) <= 0.02
                )
                if month_ok or amt_ok:
                    pick = i
                    break
            if pick is None:
                break
            use = min(pool[pick]["left"], need)
            pool[pick]["left"] = round(pool[pick]["left"] - use, 2)
            paid = round(paid + use, 2)
            balance = round(balance - use, 2)
            rec = _pay_line(pool[pick], no, use)
            rec["balance"] = balance
            leftover = 0.0
            if pool[pick]["left"] > 0.004 and pool[pick]["left"] < 10:
                leftover = pool[pick]["left"]
                pool[pick]["left"] = 0.0
                rec["leftover"] = leftover
                rec["what"] = (
                    f"{pay_what(pool[pick]['note'], pool[pick]['method'])} "
                    f"{pool[pick]['orig']:.2f} · Invoice {no} · paid {use:.2f}"
                )
            lines.append(rec)
            if leftover > 0.004:
                paid = round(paid + leftover, 2)
                balance = round(balance - leftover, 2)
                lines.append(
                    {
                        "date": pool[pick]["date"],
                        "date_fmt": fmt_date(pool[pick]["date"]),
                        "kind": "payment",
                        "ref": no,
                        "what": f"{pay_what(pool[pick]['note'], pool[pick]['method'])} leftover {leftover:.2f}",
                        "amount": -leftover,
                        "balance": balance,
                        "leftover": leftover,
                    }
                )
            need = round(need - use, 2)
        return need

    for inv in invs:
        amt = _money(inv.get("amount"))
        billed = round(billed + amt, 2)
        balance = round(balance + amt, 2)
        no = str(inv.get("invoice_number") or "")
        family = (inv.get("family") or "monthly").lower()
        due_on = invoice_due_on(inv, book)
        inv_row = {
            "date": inv.get("invoice_date"),
            "date_fmt": fmt_date(inv.get("invoice_date")),
            "kind": "invoice",
            "ref": no,
            "what": (
                f"Invoice {no} · {RECONNECT_LABEL}"
                if family == "reconnect"
                else f"Invoice {no} · {DO_RETURN_LABEL}"
                if family == "do-return"
                else f"Invoice {no}"
            ),
            "amount": amt,
            "balance": balance,
            "open": amt,
            "due_on": due_on.isoformat() if due_on else None,
            "family": family,
        }
        lines.append(inv_row)
        need = amt
        monthly_do = (
            book
            and book.get("method") == "debit-order"
            and family not in NOT_ON_MONTHLY_DO
        )
        collect_day = due_on.isoformat() if due_on and monthly_do else None
        need = _apply_do(amt, need, family, collect_day, no)
        inv_row["open"] = need
        if monthly_do:
            try:
                inv_day = date.fromisoformat(str(inv.get("invoice_date") or "")[:10])
                collect = collection_for(inv_day)
            except ValueError:
                collect = None
            as_at = today or date.today()
            if (
                collect
                and collect <= as_at
                and (key, collect.isoformat()[:7]) in unpaid_months
            ):
                unpaid_day = collect.isoformat()
                for u in unpaid_do or []:
                    if (u.get("action_date") or "")[:7] == collect.isoformat()[:7]:
                        unpaid_day = u.get("action_date") or unpaid_day
                        break
                lines.append(
                    {
                        "date": unpaid_day,
                        "date_fmt": fmt_date(unpaid_day),
                        "kind": "unpaid",
                        "ref": no,
                        "what": f"D/O unpaid · Invoice {no}",
                        "amount": 0.0,
                        "balance": balance,
                        "open": need,
                        "tone": "overdue",
                    }
                )
    open_invs = [r for r in lines if r.get("kind") == "invoice" and _money(r.get("open")) > 0.004]
    for p in pool:
        if _is_do(p) or p["left"] <= 0.004:
            continue
        first = True
        while p["left"] > 0.004:
            def _eft_rank(r: dict) -> tuple:
                fam = (r.get("family") or "monthly").lower()
                extra = 1 if fam in {"extra", "other", "query"} or fam in NOT_ON_MONTHLY_DO else 0
                return (extra, r.get("date") or "", str(r.get("ref") or ""))

            def _eft_due(r: dict) -> bool:
                if not (book and book.get("method") == "debit-order"):
                    return True
                pay_day = (p.get("date") or "")[:10]
                inv_day = (r.get("date") or "")[:10]
                due = (r.get("due_on") or inv_day)[:10]
                fam = (r.get("family") or "monthly").lower()
                if fam in NOT_ON_MONTHLY_DO or fam in {"extra", "other", "query"}:
                    return bool(inv_day) and inv_day <= pay_day
                return bool(due) and due <= pay_day

            inv_row = next(
                (
                    r
                    for r in sorted(open_invs, key=_eft_rank)
                    if _money(r.get("open")) > 0.004 and _eft_due(r)
                ),
                None,
            )
            if inv_row is None:
                break
            need = _money(inv_row.get("open"))
            use = min(p["left"], need)
            pot = p["orig"] if first else p["left"]
            p["left"] = round(p["left"] - use, 2)
            inv_row["open"] = round(need - use, 2)
            paid = round(paid + use, 2)
            balance = round(balance - use, 2)
            no = str(inv_row.get("ref") or "")
            if first:
                what = f"EFT {p['orig']:.2f} · Invoice {no} · paid -{use:.2f}"
            else:
                what = f"EFT B/F {pot:.2f} · Invoice {no} · paid -{use:.2f}"
            lines.append(
                {
                    "date": p["date"],
                    "date_fmt": fmt_date(p["date"]),
                    "kind": "payment",
                    "ref": no,
                    "what": what,
                    "amount": -use,
                    "balance": balance,
                    "paid_amt": use,
                    "leftover": p["left"],
                    "bank": p["orig"],
                }
            )
            first = False
        leftover = p["left"]
        if leftover > 0.004:
            paid = round(paid + leftover, 2)
            balance = round(balance - leftover, 2)
            lines.append(
                {
                    "date": p["date"],
                    "date_fmt": fmt_date(p["date"]),
                    "kind": "payment",
                    "ref": "",
                    "what": f"EFT B/F {leftover:.2f} leftover",
                    "amount": -leftover,
                    "balance": balance,
                    "leftover": leftover,
                    "bank": p["orig"],
                }
            )
            p["left"] = 0.0
    for p in pool:
        left = p["left"]
        if left <= 0.004 or _is_do(p):
            continue
        paid = round(paid + left, 2)
        balance = round(balance - left, 2)
        lines.append(
            {
                "date": p["date"],
                "date_fmt": fmt_date(p["date"]),
                "kind": "payment",
                "ref": "",
                "what": f"{pay_what(p['note'], p['method'])} {left:.2f}",
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
    all_inv, all_pay = _rows(conn)
    living = living_books(name)
    if living:
        invoices = [i for i in living[0] if _books_invoice(i) and not _invoice_deleted(i)]
        # D/O clients: money is FNB + Netcash. QB sales "Payment" rows are apply.
        if book and book.get("method") == "debit-order":
            payments = [p for p in all_pay if _bank_money(p)]
        else:
            payments = living[1]
    else:
        invoices = [i for i in all_inv if _books_invoice(i) and not _invoice_deleted(i)]
        if book and book.get("method") == "debit-order":
            payments = [p for p in all_pay if _bank_money(p)]
        else:
            payments = all_pay
    display = display_name(name) or name
    cut = today.isoformat()
    invoices = [i for i in invoices if (i.get("invoice_date") or "")[:10] <= cut]
    payments = [p for p in payments if (p.get("paid_on") or "")[:10] <= cut]
    all_inv = [i for i in all_inv if (i.get("invoice_date") or "")[:10] <= cut]
    all_pay = [p for p in all_pay if (p.get("paid_on") or "")[:10] <= cut]
    families = _invoice_families(conn)
    for row in invoices + all_inv:
        no = str(row.get("invoice_number") or "")
        if no in families:
            row["family"] = families[no]
    do_events = _bounces(conn, key)
    unpaid_do = [
        b
        for b in do_events
        if (b.get("result") or "").lower() in {"unpaid", "bounced"}
        and (b.get("action_date") or "")[:10] <= cut
    ]
    ledger = fifo_statement(invoices, payments, display, today, unpaid_do=unpaid_do)
    meta = fifo_statement(all_inv, all_pay, display, today, unpaid_do=unpaid_do)
    ledger["other_subs"] = meta.get("other_subs") or ledger.get("other_subs") or []
    ledger["master"] = meta.get("master") or ledger.get("master")
    ledger["sub"] = meta.get("sub") or ledger.get("sub")
    ledger["own_sub"] = meta.get("own_sub") if "own_sub" in meta else ledger.get("own_sub")
    ledger["lines"] = present_ledger(
        _fold_invoice_what(ledger.get("lines") or [], conn),
        today,
        show_money=bool(book and book.get("method") == "debit-order"),
    )
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
    elif due_today <= 0.004 and not in_do_grace:
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
        "nil": due_today <= 0.004 and not bounced,
        "statement": stmt,
        "ledger": ledger.get("lines") or [],
        "master": ledger.get("master"),
        "sub": ledger.get("sub"),
        "own_sub": ledger.get("own_sub"),
        "other_subs": [],
        "earlier_paid": sum(
            1
            for r in (ledger.get("lines") or [])
            if not r.get("show") and r.get("kind") in {"invoice", "payment"}
        ),
        "last_payment": stmt.get("last_payment"),
    }


def for_export(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    ingest(conn)
    cards = []
    seen = set()
    for row in CLIENTS:
        if is_offset(row):
            continue
        pack = account_as_at(conn, row["name"], today)
        seen.add(canon_key(row["name"]))
        cards.append(pack)
    invoices, _payments = _rows(conn)
    for inv in invoices:
        key = canon_key(inv.get("customer"))
        if key in seen or is_offset(client_row(inv.get("customer"))):
            continue
        seen.add(key)
        cards.append(account_as_at(conn, inv.get("customer"), today))
    cards.sort(key=lambda r: (r.get("name") or "").lower())
    return {
        "as_at": today.isoformat(),
        "note": (
            "Due is as at today. D/O is grace until reconciled. "
            "A bounce stays due and raises a suspension notice. "
            "Reconnection / un-suspend is a once-off penalty, not on the monthly D/O. "
            "Money is FNB EFT and named Netcash table rows only."
        ),
        "count": len(cards),
        "accounts": cards,
    }


def self_test() -> int:
    failed = 0
    conn = sqlite3.connect(":memory:")
    pack = ingest(conn)
    if pack.get("checksum"):
        print("FAIL money-checksum", pack.get("checksum"))
        failed += 1
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
    marlene_pays = [
        r
        for r in (marlene.get("ledger") or [])
        if r.get("kind") == "payment"
    ]
    marlene_jun18 = [r for r in marlene_pays if (r.get("date") or "") == "2024-06-18"]
    marlene_jul18 = [r for r in marlene_pays if (r.get("date") or "") == "2025-07-18"]
    jun18_sum = round(sum(abs(_money(r.get("amount"))) for r in marlene_jun18), 2)
    jul18_sum = round(sum(abs(_money(r.get("amount"))) for r in marlene_jul18), 2)
    if jun18_sum != 2000:
        print("FAIL marlene-jun18-one-eft-2000", jun18_sum, [r.get("what") for r in marlene_jun18])
        failed += 1
    elif jul18_sum != 1000:
        print("FAIL marlene-jul18-one-eft-1000", jul18_sum, [r.get("what") for r in marlene_jul18])
        failed += 1
    elif not any("EFT 2000.00" in (r.get("what") or "") for r in marlene_jun18):
        print("FAIL marlene-jun18-not-split", [r.get("what") for r in marlene_jun18])
        failed += 1
    elif len(marlene_jun18) < 2:
        print("FAIL marlene-jun18-must-bf-invoices", [r.get("what") for r in marlene_jun18])
        failed += 1
    else:
        print("OK marlene-one-eft-many-invoices", "jun18", jun18_sum, "jul18", jul18_sum)
    want = account_as_at(conn, "Wantling, David", today)
    want_unpaid = [r for r in (want.get("ledger") or []) if r.get("kind") == "unpaid"]
    if want_unpaid:
        print("FAIL wantling-invented-unpaid", want_unpaid)
        failed += 1
    else:
        print("OK wantling-no-invented-unpaid", want["due"])
    hav = account_as_at(conn, "Havenga, Daniel", today)
    hav_unpaid = [r for r in (hav.get("ledger") or []) if r.get("kind") == "unpaid"]
    if hav.get("bounces") or hav_unpaid:
        print("FAIL havenga-invented-unpaid", hav.get("due"), hav.get("bounces"), hav_unpaid)
        failed += 1
    else:
        print("OK havenga-no-invented-unpaid", hav.get("due"))
    if not PENDING_DO.get("collected"):
        print("FAIL oct5-not-collected", PENDING_DO)
        failed += 1
    else:
        print("OK oct5-batch-collected")
    amoroc = account_as_at(conn, "Amoroc Doors", today)
    lines = amoroc.get("ledger") or []
    living = living_books("Amoroc Doors")
    living_nos = {str(i.get("invoice_number")) for i in (living[0] if living else [])}
    all_inv = [r for r in lines if r.get("kind") == "invoice"]
    preview = [r for r in lines if r.get("show") and r.get("kind") in {"invoice", "payment"}]
    preview_inv = [r for r in preview if r.get("kind") == "invoice"]
    preview_pay = [r for r in preview if r.get("kind") == "payment"]
    oldest = next((r for r in reversed(all_inv) if str(r.get("ref")) == "2335"), None)
    conn.execute(
        """INSERT OR REPLACE INTO customer_invoices
           (invoice_number, invoice_date, customer, amount, balance_due, status, source)
           VALUES (9999,'2024-01-01','Amoroc Doors',5000,5000,'deleted','qb-list')"""
    )
    ghost = account_as_at(conn, "Amoroc Doors", today)
    ghost_lines = ghost.get("ledger") or []
    marlene_open = [
        r
        for r in (marlene.get("ledger") or [])
        if r.get("kind") == "invoice" and r.get("show") and r.get("due_row")
    ]
    if abs((amoroc["billed"] or 0) - 9310.25) > 0.02 or abs((amoroc["paid"] or 0) - 9310.25) > 0.02:
        print("FAIL amoroc-totals", amoroc["billed"], amoroc["paid"], amoroc["due"])
        failed += 1
    elif abs(amoroc["due"] or 0) > 0.02:
        print("FAIL amoroc-due", amoroc["due"])
        failed += 1
    elif not all_inv or str(all_inv[0].get("ref")) != "3107" or abs((all_inv[0].get("amount") or 0) - 199) > 0.02:
        print("FAIL amoroc-newest-top", all_inv[:2] if all_inv else lines[:3])
        failed += 1
    elif not oldest or not oldest.get("reconciled") or oldest.get("show"):
        print("FAIL amoroc-oldest-hidden", oldest)
        failed += 1
    elif len(preview_inv) != 1 or str(preview_inv[0].get("ref")) != "3107":
        print("FAIL amoroc-default-last-invoice", preview_inv)
        failed += 1
    elif len(preview_pay) != 1 or abs((preview_pay[0].get("amount") or 0) + 199) > 0.02:
        print("FAIL amoroc-default-last-payment", preview_pay)
        failed += 1
    elif any(abs((r.get("amount") or 0)) == 699 and r.get("kind") == "invoice" for r in lines):
        print("FAIL amoroc-has-aljo", [r for r in lines if abs((r.get("amount") or 0)) == 699])
        failed += 1
    elif any(abs(abs(r.get("amount") or 0) - 2544.25) < 0.02 for r in lines):
        print("FAIL amoroc-deposit-double-count")
        failed += 1
    elif living_nos and {str(r.get("ref")) for r in all_inv} - living_nos:
        print("FAIL deleted-invoices-shown", sorted({str(r.get("ref")) for r in all_inv} - living_nos))
        failed += 1
    elif any(str(r.get("ref")) == "9999" for r in ghost_lines) or abs(ghost.get("due") or 0) > 0.02:
        print("FAIL deleted-invoice-due", ghost.get("due"), [r for r in ghost_lines if str(r.get("ref")) == "9999"])
        failed += 1
    elif amoroc.get("other_subs"):
        print("FAIL amoroc-aljo-on-card", amoroc.get("other_subs"))
        failed += 1
    elif abs((marlene["due"] or 0) - 7180) <= 0.5 and len(marlene_open) < 2:
        print("FAIL arrears-must-show", len(marlene_open), marlene["due"])
        failed += 1
    elif any(r.get("kind") == "line" for r in lines):
        print("FAIL invoice-not-one-line")
        failed += 1
    elif any("gowifi" in (r.get("what") or "").lower() for r in lines):
        print("FAIL gowifi-on-line", [r.get("what") for r in lines if "gowifi" in (r.get("what") or "").lower()])
        failed += 1
    else:
        print("OK amoroc-statement", amoroc["due"], "newest", all_inv[0].get("ref"), "default", len(preview))
        print("OK deleted-invoices-never-show")
        print("OK arrears-show", len(marlene_open))
    nord = account_as_at(conn, "Bing Noordhoek Fibre", today)
    nord_led = nord.get("ledger") or []
    nord_inv = [r for r in nord_led if r.get("kind") == "invoice"]
    nord_prev = [r for r in nord_led if r.get("show") and r.get("kind") in {"invoice", "payment"}]
    nord_first_pay = next((r for r in reversed(nord_led) if r.get("kind") == "payment"), None)
    nord_last_pay = next((r for r in nord_led if r.get("kind") == "payment"), None)
    if any(r.get("kind") == "line" for r in nord_led):
        print("FAIL nord-not-one-line")
        failed += 1
    elif any("gowifi" in (r.get("what") or "").lower() for r in nord_led):
        print("FAIL nord-gowifi-on-line", [r.get("what") for r in nord_led if "gowifi" in (r.get("what") or "").lower()])
        failed += 1
    elif not nord_inv or str(nord_inv[0].get("ref")) != "3115" or "WebStream" not in (nord_inv[0].get("what") or ""):
        print("FAIL nord-3115-one-line", nord_inv[0] if nord_inv else None)
        failed += 1
    elif any(r.get("kind") == "unpaid" for r in nord_led):
        print("FAIL nord-invented-unpaid", [r for r in nord_led if r.get("kind") == "unpaid"])
        failed += 1
    elif nord_inv and nord_inv[0].get("tone") != "matched":
        print("FAIL nord-3115-not-blue", nord_inv[0])
        failed += 1
    elif not nord_last_pay or "D/O paid" not in (nord_last_pay.get("what") or "") or "3115" not in (
        nord_last_pay.get("what") or ""
    ):
        print("FAIL nord-last-do-for-3115", nord_last_pay)
        failed += 1
    elif abs((nord_led[0].get("balance") if nord_led else 0) or 0) - abs(nord.get("due") or 0) > 0.02:
        print("FAIL nord-top-balance-is-due", nord_led[0] if nord_led else None, nord.get("due"))
        failed += 1
    else:
        from invoice_canned import parse_day as _pd

        days = [_pd(r.get("date")) for r in nord_led if r.get("kind") in {"invoice", "payment"}]
        if any(days[i] < days[i + 1] for i in range(len(days) - 1) if days[i] and days[i + 1]):
            print("FAIL nord-not-newest-top", [(r.get("date_fmt"), r.get("kind"), r.get("what")) for r in nord_led[:8]])
            failed += 1
        else:
            print("OK nordhoek-one-line", nord_inv[0].get("what"), nord_last_pay.get("what"))
            print("OK newest-top")
            print("OK nord-matched-blue")
    matched = fifo_statement(
        [
            {"invoice_number": "3063", "invoice_date": "2026-07-17", "customer": "Bing Noordhoek Fibre", "amount": 599, "source": "qb-list"},
            {"invoice_number": "3090", "invoice_date": "2026-08-20", "customer": "Bing Noordhoek Fibre", "amount": 599, "source": "qb-list"},
            {"invoice_number": "3115", "invoice_date": "2026-09-21", "customer": "Bing Noordhoek Fibre", "amount": 599, "source": "qb-list"},
        ],
        [
            {
                "paid_on": "2026-10-05",
                "customer": "Bing Noordhoek Fibre",
                "amount": -599,
                "note": "Debit order",
                "method": "do",
                "source": "netcash-alloc",
            }
        ],
        "Bing Noordhoek Fibre",
        date(2026, 10, 5),
    )
    pay_3115 = [
        r
        for r in (matched.get("lines") or [])
        if r.get("kind") == "payment" and "3115" in (r.get("what") or "")
    ]
    if not pay_3115:
        print("FAIL bing-oct5-must-match-3115", matched.get("lines"))
        failed += 1
    early = account_as_at(conn, "Bing Noordhoek Fibre", date(2026, 9, 22))
    early_3115 = next(
        (r for r in (early.get("ledger") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "3115"),
        None,
    )
    cup = account_as_at(conn, "G Cupido", today)
    cup_unpaid = [r for r in (cup.get("ledger") or []) if r.get("kind") == "unpaid"]
    cup_3125 = next(
        (r for r in (cup.get("ledger") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "3125"),
        None,
    )
    amoroc_3107 = next((r for r in all_inv if str(r.get("ref")) == "3107"), None)
    marlene_over = [
        r
        for r in (marlene.get("ledger") or [])
        if r.get("kind") == "invoice" and r.get("tone") == "unpaid"
    ]
    cup_3125_unpaid = [
        r for r in cup_unpaid if str(r.get("ref")) == "3125"
    ]
    if not early_3115 or early_3115.get("tone") != "pending":
        print("FAIL nord-3115-should-be-orange-before-due", early_3115)
        failed += 1
    elif not cup_3125 or _money(cup_3125.get("open")) > 0.02 or cup_3125_unpaid:
        print("FAIL cupido-oct-must-be-paid", cup.get("due"), cup_3125, cup_3125_unpaid)
        failed += 1
    elif abs((cup.get("due") or 0) - 760) > 0.02:
        print("FAIL cupido-due", cup.get("due"))
        failed += 1
    elif not amoroc_3107 or amoroc_3107.get("tone") != "matched":
        print("FAIL amoroc-3107-not-blue", amoroc_3107)
        failed += 1
    elif abs((marlene["due"] or 0) - 7180) <= 0.5 and not marlene_over:
        print("FAIL marlene-unpaid-purple", [r.get("tone") for r in (marlene.get("ledger") or []) if r.get("kind") == "invoice"][:6])
        failed += 1
    else:
        print("OK invoice-tones", "matched", "pending", "unpaid")
        print("OK cupido-oct-processed", cup.get("due"))
    cup_2715 = next(
        (r for r in (cup.get("ledger") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "2715"),
        None,
    )
    cup_2715_pay = [
        r
        for r in (cup.get("ledger") or [])
        if r.get("kind") == "payment" and str(r.get("ref")) == "2715"
    ]
    cup_3013 = next(
        (r for r in (cup.get("ledger") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "3013"),
        None,
    )
    cup_3013_unpaid = next(
        (r for r in cup_unpaid if str(r.get("ref")) == "3013"),
        None,
    )
    cup_275 = [
        r
        for r in (cup.get("ledger") or [])
        if abs(abs(_money(r.get("amount"))) - 2.75) < 0.01
    ]
    if cup_275:
        print("FAIL cupido-2.75-is-do-fee-not-client", cup_275)
        failed += 1
    elif not cup_2715 or _money(cup_2715.get("open")) > 0.02:
        print("FAIL cupido-2715-must-be-nil", cup_2715)
        failed += 1
    elif not cup_2715_pay or any("D/O" in (r.get("what") or "") for r in cup_2715_pay):
        print("FAIL cupido-2715-must-be-eft", cup_2715_pay)
        failed += 1
    elif not cup_2715_pay or "EFT 1467.25" not in (cup_2715_pay[0].get("what") or ""):
        print("FAIL cupido-2715-eft-amount", cup_2715_pay)
        failed += 1
    elif not cup_2715_pay or abs(abs(_money(cup_2715_pay[0].get("amount"))) - 1467.25) > 0.02:
        print("FAIL cupido-2715-eft-rand", cup_2715_pay)
        failed += 1
    elif not cup_3013_unpaid or cup_3013_unpaid.get("tone") != "overdue":
        print("FAIL cupido-do-unpaid-must-stay-red", cup_3013_unpaid)
        failed += 1
    elif not cup_3013_unpaid or abs(_money(cup_3013_unpaid.get("amount"))) > 0.02:
        print("FAIL cupido-3013-unpaid-must-be-zero", cup_3013_unpaid)
        failed += 1
    elif any(str(r.get("ref")) == "3055" for r in (cup.get("ledger") or [])):
        print("FAIL cupido-3055-not-his-line")
        failed += 1
    else:
        print("OK cupido-2715-eft-nil", "3013 unpaid 0")
    cup_3130 = next(
        (r for r in (cup.get("ledger") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "3130"),
        None,
    )
    cup_3130_do = [
        r
        for r in (cup.get("ledger") or [])
        if str(r.get("ref")) == "3130" and r.get("kind") == "payment" and "D/O" in (r.get("what") or "")
    ]
    if (
        not cup_3130
        or abs(_money(cup_3130.get("open")) - 233) > 0.02
        or cup_3130.get("family") != "do-return"
        or cup_3130_do
    ):
        print("FAIL cupido-3130-do-return-eft", cup_3130, cup_3130_do)
        failed += 1
    elif DO_RETURN_LABEL not in (cup_3130.get("what") or ""):
        print("FAIL cupido-3130-label", cup_3130)
        failed += 1
    else:
        print("OK cupido-3130-do-return-unpaid", cup_3130.get("open"))
    cup_sep8 = [
        r
        for r in (cup.get("ledger") or [])
        if r.get("kind") == "payment" and (r.get("date") or "") == "2026-09-08"
    ]
    cup_sep8_chrono = list(reversed(cup_sep8))
    sep8_what = [r.get("what") or "" for r in cup_sep8_chrono]
    sep8_sum = round(sum(abs(_money(r.get("amount"))) for r in cup_sep8), 2)
    if sep8_sum != 1950:
        print("FAIL cupido-sep8-not-1950", sep8_sum, sep8_what)
        failed += 1
    elif len(cup_sep8) != 3:
        print("FAIL cupido-sep8-must-be-eft-then-bf", sep8_what)
        failed += 1
    elif "EFT 1950.00 · Invoice 3013" not in sep8_what[0]:
        print("FAIL cupido-sep8-oldest-first", sep8_what)
        failed += 1
    elif "EFT B/F 1191.00 · Invoice 3074" not in sep8_what[1]:
        print("FAIL cupido-sep8-bf-3074", sep8_what)
        failed += 1
    elif "EFT B/F 432.00 · Invoice 3101" not in sep8_what[2]:
        print("FAIL cupido-sep8-bf-3101", sep8_what)
        failed += 1
    else:
        print("OK cupido-sep8-eft-bf", sep8_what)
    live_path = DATA_DIR / "qbo_cupido_live.json"
    if live_path.exists():
        live = json.loads(live_path.read_text())
        qb_pays = live.get("payments") or []
        qb_sep = [p for p in qb_pays if (p.get("date") or "") == "2026-09-08"]
        qb_pay_sum = round(sum(float(p.get("total") or 0) for p in qb_pays), 2)
        qb_sep_sum = round(sum(float(p.get("total") or 0) for p in qb_sep), 2)
        if abs(qb_pay_sum - 3417.25) > 0.02 or abs(qb_sep_sum - 1950) > 0.02:
            print("FAIL cupido-qb-bank-checksum", qb_pay_sum, qb_sep_sum)
            failed += 1
        elif len(qb_sep) == 4 and len(cup_sep8) != 3:
            print("FAIL cupido-must-not-copy-qb-splits", len(qb_sep), len(cup_sep8))
            failed += 1
        else:
            print("OK cupido-qb-checksum-not-qb-apply", qb_pay_sum, "sep8", qb_sep_sum)
    cup_shown = [
        r.get("what") or ""
        for r in (cup.get("ledger") or [])
        if r.get("show") and r.get("kind") == "payment"
    ]
    if not any("EFT 1950.00" in w for w in cup_shown):
        print("FAIL cupido-eft-must-show", cup_shown)
        failed += 1
    elif not any("D/O paid" in w and "3125" in w for w in cup_shown):
        print("FAIL cupido-oct-do-must-show", cup_shown)
        failed += 1
    elif not any("EFT 1467.25" in w and "2715" in w for w in cup_shown):
        print("FAIL cupido-2715-eft-must-show", cup_shown)
        failed += 1
    else:
        print("OK cupido-eft-and-do-show")
    cup_jun_do = [
        r
        for r in (cup.get("ledger") or [])
        if r.get("kind") == "payment"
        and (r.get("date") or "") == "2026-06-01"
        and "D/O paid" in (r.get("what") or "")
    ]
    if not cup_jun_do or "3034" not in (cup_jun_do[0].get("what") or ""):
        print("FAIL cupido-june-do-must-match-batch-inv", cup_jun_do)
        failed += 1
    elif "3013" in (cup_jun_do[0].get("what") or ""):
        print("FAIL cupido-june-do-stole-oldest", cup_jun_do)
        failed += 1
    else:
        print("OK cupido-do-matches-batch-invoice", cup_jun_do[0].get("what"))
    ann = account_as_at(conn, "Annette Bing HH", today)
    ann_old = [
        r
        for r in (ann.get("ledger") or [])
        if r.get("kind") == "invoice" and r.get("show") and (r.get("date") or "") < "2026-01-01"
    ]
    ann_do = [
        r
        for r in (ann.get("ledger") or [])
        if r.get("kind") == "payment" and "D/O paid" in (r.get("what") or "")
    ]
    ann_unpaid = [r for r in (ann.get("ledger") or []) if r.get("kind") == "unpaid"]
    if ann_unpaid:
        print("FAIL ann-invented-unpaid", ann_unpaid)
        failed += 1
    else:
        print("OK ann-hh-named-netcash-only", len(ann_do), "due", ann.get("due"))
    invented = []
    for row in (
        "David Wantling",
        "Annette Bing HH",
        "Murray DH",
        "G Cupido",
        "Bing Noordhoek Fibre",
        "Stan Hundermark",
        "Dirk De Villiers",
        "Jean de Villiers",
        "GeoCorp",
        "Havenga",
    ):
        pack = account_as_at(conn, row, today)
        fake = [r for r in (pack.get("ledger") or []) if r.get("kind") == "unpaid"]
        if row == "G Cupido":
            fake = [r for r in fake if (r.get("date") or "")[:7] not in {"2026-05", "2026-08", "2026-09"}]
        if fake:
            invented.append((row, fake))
    cup_opens = [
        (r.get("ref"), r.get("open"))
        for r in (cup.get("ledger") or [])
        if r.get("kind") == "invoice" and _money(r.get("open")) > 0.004
    ]
    if invented:
        print("FAIL invented-unpaid-rows", invented)
        failed += 1
    elif any(str(ref) == "3125" for ref, _open in cup_opens):
        print("FAIL cupido-3125-oct-still-open", cup_opens)
        failed += 1
    else:
        print("OK no-invented-unpaid", cup_opens)
    jean = account_as_at(conn, "Jean de Villiers", today)
    geo = account_as_at(conn, "GeoCorp", today)
    if any(r.get("kind") == "unpaid" for r in (jean.get("ledger") or [])):
        print("FAIL jean-invented-unpaid", jean.get("due"))
        failed += 1
    elif any(r.get("kind") == "unpaid" for r in (geo.get("ledger") or [])):
        print("FAIL geocorp-invented-unpaid", geo.get("due"))
        failed += 1
    else:
        print("OK jean-geocorp-named-only", jean.get("due"), geo.get("due"))
    if _kind_of_line("Reconnection", "Un-suspend after credit suspend", 250) != "reconnect":
        print("FAIL reconnect-line-kind")
        failed += 1
    elif _kind_of_line("WebStream", "50/25 Uncapped", 759) != "monthly":
        print("FAIL monthly-not-reconnect")
        failed += 1
    elif _stmt_desc("Reconnection fee") != RECONNECT_LABEL:
        print("FAIL reconnect-label", _stmt_desc("Reconnection fee"))
        failed += 1
    else:
        rec_open = fifo_statement(
            [
                {
                    "invoice_number": "4001",
                    "invoice_date": "2026-08-17",
                    "customer": "G Cupido",
                    "amount": 759,
                    "source": "qb-list",
                    "family": "monthly",
                },
                {
                    "invoice_number": "4002",
                    "invoice_date": "2026-09-10",
                    "customer": "G Cupido",
                    "amount": 250,
                    "source": "qb-list",
                    "family": "reconnect",
                    "description": "Reconnection after unpaid",
                },
            ],
            [],
            "G Cupido",
            date(2026, 10, 5),
        )
        rec_inv = next(
            (r for r in (rec_open.get("lines") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "4002"),
            None,
        )
        rec_do = [
            r
            for r in (rec_open.get("lines") or [])
            if str(r.get("ref")) == "4002" and r.get("kind") == "payment"
        ]
        mon_inv = next(
            (r for r in (rec_open.get("lines") or []) if r.get("kind") == "invoice" and str(r.get("ref")) == "4001"),
            None,
        )
        rec_paid = fifo_statement(
            [
                {
                    "invoice_number": "4002",
                    "invoice_date": "2026-09-10",
                    "customer": "G Cupido",
                    "amount": 250,
                    "source": "qb-list",
                    "family": "reconnect",
                }
            ],
            [
                {
                    "paid_on": "2026-09-12",
                    "customer": "G Cupido",
                    "amount": -250,
                    "note": "EFT",
                    "method": "eft",
                    "source": "fnb-eft",
                }
            ],
            "G Cupido",
            date(2026, 10, 5),
        )
        if not rec_inv or _money(rec_inv.get("open")) != 250 or rec_do:
            print("FAIL reconnect-must-stay-due", rec_inv, rec_do, rec_open.get("due"))
            failed += 1
        elif RECONNECT_LABEL not in (rec_inv.get("what") or ""):
            print("FAIL reconnect-penalty-label", rec_inv)
            failed += 1
        elif abs(_money(rec_open.get("due")) - 1009) > 0.02:
            print("FAIL reconnect-due", rec_open.get("due"))
            failed += 1
        elif rec_inv.get("tone") == "matched" or rec_inv.get("due_on") != "2026-09-10":
            print("FAIL reconnect-due-now-not-do", rec_inv)
            failed += 1
        elif abs(_money(rec_paid.get("due"))) > 0.02:
            print("FAIL reconnect-eft-clears", rec_paid.get("due"), rec_paid.get("lines"))
            failed += 1
        else:
            print("OK reconnect-once-off-penalty", rec_open.get("due"))
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
