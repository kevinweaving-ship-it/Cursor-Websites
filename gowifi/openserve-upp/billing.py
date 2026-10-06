#!/usr/bin/env python3
"""Month-in-advance billing: invoice on the 17th, D/O loaded then, collected next month.

Netcash fees come off the FNB settlement, not the client. A successful D/O
clears the invoice in full. A loaded-but-uncollected batch stays on the client.
"""
from __future__ import annotations

import re
import sqlite3
from calendar import monthrange
from datetime import date

from invoice_canned import client_key, statement_on_invoice
from packages import by_sku, extras as extra_charges

INVOICE_DAY = 17
# Normal collection is the 1st of the service month. 5 Oct 2026 was same-day
# after the 17 Sep load was missed.
DO_DAY = 1

# Monthly book: fibre + wireless, debit-order + EFT. D/O order matches the
# Monthly book. Amount is the line rental only —
# install / equipment / add-ons / reconnect are extras, not on the D/O.
CLIENTS = [
    {"ref": "Wantling", "name": "David Wantling", "amount": 439.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "DEV001", "name": "Dirk De Villiers", "amount": 399.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "BIN001", "name": "Annette Bing HH", "amount": 429.00, "method": "debit-order", "access": "wireless", "sku": None, "address": "13 Francolin Close, Hermanus Heights, Hermanus"},
    {"ref": "HUN001", "name": "Stan Hundermark", "amount": 329.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "De Gruchy OS Fiber 200", "name": "Phillip De Gruchy", "amount": 1219.00, "method": "debit-order", "access": "fibre", "sku": "OWS300M", "discount": True},
    {"ref": "Jean de Villiers", "name": "Jean de Villiers", "amount": 550.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "Havenga", "name": "Havenga", "amount": 699.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "HM Builders", "name": "Hermanus Builders", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "GeoCorp", "name": "GeoCorp", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Bryant Michael", "name": "Bryant Michael", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Murray DH", "name": "Murray DH", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Bing Noordhoek Fibre", "name": "Bing Noordhoek Fibre", "amount": 599.00, "method": "debit-order", "access": "fibre", "sku": "OWS25M", "address": "13 Sleepy Hollow Lane, Noordhoek, Cape Town"},
    {"ref": "G Cupido", "name": "G Cupido", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Gordon Neethling", "name": "Gordon Neethling", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": None, "name": "Lategan", "amount": 999.00, "method": "eft", "access": "fibre", "sku": "OWS100M"},
    {"ref": None, "name": "HPP Control Room", "amount": 599.00, "method": "eft", "access": "fibre", "sku": "OWS25M"},
    {"ref": None, "name": "Pearson, Philippa", "amount": 329.00, "method": "eft", "access": "wireless", "sku": None},
    {"ref": None, "name": "Phillipus May", "amount": 439.00, "method": "eft", "access": "wireless", "sku": None, "discount": True},
    {"ref": None, "name": "Amoroc Doors", "amount": 199.00, "method": "eft", "access": "wireless", "sku": None},
    {"ref": None, "name": "WCC Tech", "amount": 1000.00, "method": "eft", "access": "fibre", "sku": None},
    {
        "ref": None,
        "name": "Paltco",
        "amount": 1399.00,
        "method": "eft",
        "access": "offset",
        "sku": None,
        "not_a_client": True,
        "loan_account": "Share capital:Loan Account - Kevin Weaving 33%",
        "offset_note": (
            "Offset deal. Not a fibre or wifi client. No B-number. "
            "Cash in against Kevin Weaving loan. Openserve fibre stays cost of service."
        ),
    },
    {"ref": None, "name": "Mrs Marlene/Georg Van Eeden", "amount": 439.00, "method": "eft", "access": "wireless", "sku": None},
]

KEVIN_LOAN_ACCOUNT = "Share capital:Loan Account - Kevin Weaving 33%"


def is_offset(row: dict | None) -> bool:
    if not row:
        return False
    return bool(row.get("not_a_client") or (row.get("access") or "") == "offset")


def is_service_client(row: dict | None) -> bool:
    return bool(row) and not is_offset(row)


DO_CLIENTS = [row for row in CLIENTS if row["method"] == "debit-order"]
EFT_CLIENTS = [row for row in CLIENTS if row["method"] == "eft" and is_service_client(row)]
OFFSET_DEALS = [row for row in CLIENTS if is_offset(row)]
SERVICE_CLIENTS = [row for row in CLIENTS if is_service_client(row)]

_NAME_ALIASES = {
    "godfrey cupido": "g cupido",
    "g cupido": "g cupido",
    "gordon neethling": "gordon neethling",
    "stan hundermark": "stan hundermark",
    "hundermark stan": "stan hundermark",
    "annette bing": "annette bing",
    "bing annette": "annette bing",
    "dirk de": "dirk de",
    "de villers": "dirk de",
    "de villiers": "dirk de",
    "phillip de": "phillip de",
    "de gruchy": "phillip de",
    "david wantling": "david wantling",
    "wantling david": "david wantling",
    "bryant michael": "bryant michael",
    "michael bryant": "bryant michael",
    "murray dh": "murray dh",
    "jakobie murray": "murray dh",
    "murray jakobie": "murray dh",
    "hermanus builders": "hermanus builders",
    "hm builders": "hermanus builders",
    "bing noordhoek": "bing noordhoek",
    "annette bing nordhoek": "bing noordhoek",
    "jean de": "jean de",
    "lategan": "lategan",
    "johannes lategan": "lategan",
    "lategan johannes": "lategan",
    "hpp control": "hpp control",
    "hpp": "hpp control",
    "pearson philippa": "pearson philippa",
    "philippa pearson": "pearson philippa",
    "phillipus may": "phillipus may",
    "philliup": "phillipus may",
    "phillipus": "phillipus may",
    "amoroc doors": "amoroc doors",
    "amoroc": "amoroc doors",
    "wcc tech": "wcc tech",
    "wcc": "wcc tech",
    "wcc technologies": "wcc tech",
    "paltco": "paltco",
    "patriot sa": "paltco",
    "marlene georg": "marlene georg",
    "van eeden": "marlene georg",
    "georg van": "marlene georg",
    "havenga daniel": "havenga",
    "daniel havenga": "havenga",
    "geocorp cc": "geocorp",
    "geocorp": "geocorp",
    "steyn irene": "irene steyn",
    "irene steyn": "irene steyn",
    "terence pereira": "terence pereira",
    "james such": "james such",
    "such james": "james such",
    "geran sukhraj": "geran sukhraj",
    "sukhraj geran": "geran sukhraj",
    "aljo van": "aljo van",
    "derek van": "derek van",
    "van zyl": "derek van",
    "ruandr wessels": "ruandre wessels",
    "ruandre wessels": "ruandre wessels",
    "leon dykman": "leon dykman",
}


def canon_key(name: str | None) -> str:
    raw = " ".join(re.findall(r"[a-z0-9]+", (name or "").lower()))
    if "nordhoek" in raw or "noordhoek" in raw:
        return "bing noordhoek"
    if "aljo" in raw:
        return "aljo van"
    if "jean" in raw and "vill" in raw:
        return "jean de"
    if "dirk" in raw:
        return "dirk de"
    if "lategan" in raw:
        return "lategan"
    if "paltco" in raw or "patriot" in raw:
        return "paltco"
    if "deleted" in raw and "leon" in raw:
        return "leon dykman"
    if "deleted" in raw and "pereira" in raw:
        return "terence pereira"
    key = client_key(name)
    return _NAME_ALIASES.get(key, key)


def split_qb_name(name: str | None) -> tuple[str, str | None]:
    """QuickBooks master:sub. No colon = the master's own sub-account."""
    raw = re.sub(r"\s*\(deleted\)\s*", "", name or "", flags=re.I).strip()
    if ":" in raw:
        master, sub = raw.split(":", 1)
        return master.strip(), sub.strip() or None
    return raw, None


def display_name(name: str | None) -> str:
    key = canon_key(name)
    for row in CLIENTS:
        if canon_key(row["name"]) == key:
            return row["name"]
    return (name or "").strip()


def client_row(name: str | None) -> dict | None:
    key = canon_key(name)
    for row in CLIENTS:
        if canon_key(row["name"]) == key:
            return row
    return None


PENDING_DO = {
    "action_date": "2026-10-05",
    "batch_id": "2571994",
    "batch_name": "Debit batch for 2026-10-05",
    "status": "Collected",
    "volume": 14,
    "amount": 9217.00,
    "unpaid_value": 0.00,
    "unpaid_volume": 0,
    "collected": True,
    "normal_day": DO_DAY,
    "note": (
        "Same-day batch 2571994 on 5 Oct. "
        "Client paid/unpaid comes from the Netcash table, not this note."
    ),
}


def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def invoice_day_on(today: date) -> date:
    """Last (or today's) 17th — invoices go out on the 17th."""
    if today.day >= INVOICE_DAY:
        return date(today.year, today.month, INVOICE_DAY)
    return add_months(date(today.year, today.month, INVOICE_DAY), -1)


def period_for(inv_day: date) -> str:
    """Clients pay a month in advance: 17 Sep invoice is October service."""
    nxt = add_months(inv_day, 1)
    return f"{nxt.year:04d}-{nxt.month:02d}"


def period_label(period: str) -> str:
    year, month = period.split("-")
    names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{names[int(month) - 1]} {year}"


def do_action_date(inv_day: date) -> date:
    """D/O for the advance month. Normally the 1st; Oct 2026 was the 5th."""
    nxt = add_months(inv_day, 1)
    first = date(nxt.year, nxt.month, DO_DAY)
    if first == date(2026, 10, 1):
        return date(2026, 10, 5)
    return first


def line_label(row: dict, period: str) -> str:
    pkg = by_sku(row.get("sku"))
    if is_offset(row):
        head = "Offset · Kevin loan"
    elif pkg:
        head = pkg["label"]
    else:
        head = "Fibre" if row.get("access") == "fibre" else "Wireless"
    extra = " · discount" if row.get("discount") else ""
    return f"{head} {period_label(period)} (month in advance){extra}"


def apply_named_receipts(conn: sqlite3.Connection) -> int:
    """Bank/Netcash receipts named to a client. Lump NETCASH settlements are not a client payment."""
    conn.execute(
        "DELETE FROM customer_payments WHERE source IN ('fnb-eft','netcash-do')"
    )
    n = 0
    try:
        rows = conn.execute(
            """SELECT paid_on, payee, memo, deposit, source, account
               FROM book_entries
               WHERE deposit > 0
                 AND (
                   account LIKE '%Receivable%'
                   OR qb_type='Payment'
                 )"""
        ).fetchall()
    except sqlite3.OperationalError:
        return 0
    for paid_on, payee, memo, deposit, source, account in rows:
        name = display_name(payee)
        if not name or name.lower() == "netcash":
            continue
        if is_offset(client_row(name) or client_row(payee)):
            continue
        do = (source or "").startswith("qb_netcash") or "netcash" in (account or "").lower()
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, statement_number)
               VALUES (?,?,?,?,?,NULL)""",
            (
                paid_on,
                name,
                -abs(float(deposit)),
                "Debit order" if do else "Payment",
                "netcash-do" if do else "fnb-eft",
            ),
        )
        n += 1
    conn.commit()
    return n


def apply_collected_do(conn: sqlite3.Connection, action_date: str, clients: list[dict]) -> int:
    """Post the full D/O (not the FNB net after fees) as paid against each client."""
    have = set()
    try:
        for paid_on, customer, amount, source in conn.execute(
            "SELECT paid_on, customer, amount, source FROM customer_payments"
        ):
            if source not in {"netcash-do", "qb-do", "qb-do-synth"}:
                continue
            have.add((paid_on, canon_key(customer), round(abs(float(amount or 0)), 2)))
    except sqlite3.OperationalError:
        have = set()
    n = 0
    try:
        from recon import BATCH_UNPAID

        skip = BATCH_UNPAID.get(PENDING_DO.get("batch_id") or "", set())
    except Exception:
        skip = set()
    for row in clients:
        if canon_key(row["name"]) in skip:
            continue
        key = (action_date, canon_key(row["name"]), round(abs(float(row["amount"])), 2))
        if key in have:
            continue
        conn.execute(
            """INSERT INTO customer_payments
               (paid_on, customer, amount, note, source, statement_number)
               VALUES (?,?,?,?,?,NULL)""",
            (
                action_date,
                row["name"],
                -abs(float(row["amount"])),
                "Debit order",
                "netcash-do",
            ),
        )
        have.add(key)
        n += 1
    conn.commit()
    return n


def ensure_cycle_invoices(
    conn: sqlite3.Connection,
    today: date | None = None,
    clients: list[dict] | None = None,
) -> list[dict]:
    """Issue / keep the 17th invoice for the current advance month. No D/O credit yet."""
    today = today or date.today()
    inv_day = invoice_day_on(today)
    period = period_for(inv_day)
    clients = clients or SERVICE_CLIENTS
    created = []
    last = conn.execute("SELECT MAX(invoice_number) FROM customer_invoices").fetchone()
    number = int(last[0] or 3113)
    for row in clients:
        if is_offset(row):
            continue
        key = canon_key(row["name"])
        existing = None
        month = inv_day.isoformat()[:7]
        for rec in conn.execute(
            """SELECT invoice_number, customer, invoice_date FROM customer_invoices"""
        ):
            if canon_key(rec[1]) != key:
                continue
            if (rec[2] or "")[:7] == month:
                existing = rec
                break
        if existing:
            continue
        number += 1
        payload = {
            "invoice_number": number,
            "invoice_date": inv_day.isoformat(),
            "due_date": inv_day.isoformat(),
            "customer": row["name"],
            "period": period,
            "description": line_label(row, period),
            "qty": 1,
            "rate": row["amount"],
            "amount": row["amount"],
            "balance_due": row["amount"],
            "terms": (
                "Debit order following month"
                if row.get("method") == "debit-order"
                else "EFT month in advance"
            ),
            "status": "open",
            "source": "gowifi-do" if row.get("method") == "debit-order" else "gowifi-eft",
        }
        try:
            from qb_import import _upsert_invoice

            _upsert_invoice(conn, payload)
        except Exception:
            conn.execute(
                """INSERT OR IGNORE INTO customer_invoices
                   (invoice_number, invoice_date, service_number, customer, period,
                    amount, vat, status, source)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    number,
                    inv_day.isoformat(),
                    None,
                    row["name"],
                    period,
                    row["amount"],
                    None,
                    "open",
                    payload["source"],
                ),
            )
        created.append(payload)
    conn.commit()
    return created


def _invoices(conn) -> list[dict]:
    out = []
    try:
        rows = conn.execute(
            """SELECT invoice_number, invoice_date, customer, amount, period, source
               FROM customer_invoices ORDER BY invoice_date, invoice_number"""
        )
    except sqlite3.OperationalError:
        return out
    for rec in rows:
        out.append(
            {
                "invoice_number": rec[0],
                "invoice_date": rec[1],
                "customer": rec[2],
                "amount": rec[3],
                "period": rec[4],
                "source": rec[5],
            }
        )
    return out


def _payments(conn) -> list[dict]:
    out = []
    try:
        rows = conn.execute(
            """SELECT paid_on, customer, amount, note, source
               FROM customer_payments ORDER BY paid_on, id"""
        )
    except sqlite3.OperationalError:
        return out
    for rec in rows:
        out.append(
            {
                "paid_on": rec[0],
                "customer": rec[1],
                "amount": rec[2],
                "note": rec[3],
                "source": rec[4],
            }
        )
    return out


def client_accounts(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    inv_day = invoice_day_on(today)
    period = period_for(inv_day)
    invoices = _invoices(conn)
    payments = _payments(conn)
    pending = dict(PENDING_DO)
    by_key = {}
    for row in SERVICE_CLIENTS:
        by_key[canon_key(row["name"])] = {
            "name": row["name"],
            "ref": row.get("ref"),
            "do_amount": row["amount"] if row.get("method") == "debit-order" else None,
            "amount": row["amount"],
            "method": row.get("method") or "eft",
            "access": row.get("access"),
            "sku": row.get("sku"),
            "package": by_sku(row.get("sku")),
            "discount": bool(row.get("discount")),
            "address": row.get("address"),
        }
    for pay in payments:
        if is_offset(client_row(pay.get("customer"))):
            continue
        key = canon_key(pay.get("customer"))
        if key and key not in by_key:
            by_key[key] = {
                "name": display_name(pay.get("customer")),
                "ref": None,
                "do_amount": None,
                "amount": None,
                "method": "eft",
                "access": None,
                "sku": None,
                "package": None,
                "discount": False,
                "address": None,
            }
    aliased_inv = [{**i, "customer": display_name(i.get("customer")) or i.get("customer")} for i in invoices]
    aliased_pay = [{**p, "customer": display_name(p.get("customer")) or p.get("customer")} for p in payments]
    accounts = []
    for key, meta in by_key.items():
        stmt = statement_on_invoice(aliased_inv, aliased_pay, meta["name"], as_at=today)
        last_inv = None
        for inv in reversed(invoices):
            if canon_key(inv.get("customer")) == key:
                last_inv = inv
                break
        cycle_inv = None
        for inv in invoices:
            if canon_key(inv.get("customer")) == key and inv.get("invoice_date") == inv_day.isoformat():
                cycle_inv = inv
                break
        cycle_inv = cycle_inv or last_inv
        cycle_credit = 0.0
        for pay in aliased_pay:
            if canon_key(pay.get("customer")) != key:
                continue
            paid = pay.get("paid_on") or ""
            if paid < inv_day.isoformat():
                continue
            cycle_credit += abs(float(pay.get("amount") or 0))
        inv_amt = float(
            (cycle_inv or {}).get("amount")
            or meta.get("amount")
            or meta.get("do_amount")
            or 0
        )
        paid = round(cycle_credit, 2)
        due = round(inv_amt - cycle_credit, 2)
        paid_up = abs(due) <= 0.004
        last_pay = stmt.get("last_payment") or {}
        pending_do = None
        if meta["method"] == "debit-order" and pending.get("collected"):
            pending_do = {
                "action_date": pending["action_date"],
                "amount": meta["do_amount"],
                "status": "collected",
                "reconciled": True,
            }
        elif meta["method"] == "debit-order" and not pending.get("collected"):
            pending_do = {
                "action_date": pending["action_date"],
                "amount": meta["do_amount"],
                "status": "authorised · not collected",
                "reconciled": False,
            }
        pkg = meta.get("package") or {}
        accounts.append(
            {
                "name": meta["name"],
                "ref": meta["ref"],
                "method": meta["method"],
                "pay": "D/O" if meta["method"] == "debit-order" else "EFT",
                "access": meta.get("access") or "wireless",
                "sku": meta.get("sku"),
                "package": pkg.get("label") if pkg else None,
                "speed": pkg.get("speed"),
                "discount": bool(meta.get("discount")),
                "do_amount": meta["do_amount"],
                "billed": meta.get("amount") or inv_amt or None,
                "paid": paid,
                "last_invoice": (cycle_inv or {}).get("invoice_number"),
                "last_invoice_date": (cycle_inv or {}).get("invoice_date"),
                "period": (cycle_inv or {}).get("period") or period,
                "invoice_amount": inv_amt or None,
                "due": due,
                "nil": paid_up,
                "status": "paid-up" if paid_up else "owes",
                "pending_do": pending_do,
                "last_payment": last_pay,
                "last_paid_on": (last_pay.get("date") or last_pay.get("paid_on")) if isinstance(last_pay, dict) else None,
                "address": meta.get("address"),
            }
        )
    accounts.sort(
        key=lambda r: (
            0 if r.get("access") == "fibre" else 1,
            0 if r["method"] == "debit-order" else 1,
            r["name"] or "",
        )
    )
    def _split(rows):
        owes = [a for a in rows if a["status"] == "owes"]
        settled = [a for a in rows if a["status"] == "paid-up"]
        owes.sort(key=lambda r: (-(r.get("due") or 0), r["name"] or ""))
        settled.sort(key=lambda r: r["name"] or "")
        return owes, settled

    wireless = [a for a in accounts if a.get("access") != "fibre"]
    fibre = [a for a in accounts if a.get("access") == "fibre"]
    wireless_owes, wireless_paid = _split(wireless)
    fibre_owes, fibre_paid = _split(fibre)
    return {
        "invoice_day": inv_day.isoformat(),
        "period": period,
        "period_label": period_label(period),
        "rule": (
            "Invoice on the 17th, month in advance. D/O is loaded with the invoice "
            "and collected next month on the 1st (5 Oct this cycle only). "
            "Full D/O clears the invoice; Netcash fees are a company cost. "
            "Wireless and EFT clients are on the same 17th cycle. "
            "Install, equipment, add-ons and reconnection (un-suspend after non-payment) "
            "are once-off penalties, not on the D/O."
        ),
        "pending_do": pending,
        "do_action_date": do_action_date(inv_day).isoformat(),
        "extras": extra_charges(),
        "accounts": accounts,
        "wireless": wireless,
        "fibre": fibre,
        "wireless_owes": wireless_owes,
        "wireless_paid": wireless_paid,
        "fibre_owes": fibre_owes,
        "fibre_paid": fibre_paid,
        "open": sum(1 for a in accounts if a["status"] == "owes"),
        "paid_up": sum(1 for a in accounts if a["status"] == "paid-up"),
        "do_clients": sum(1 for a in accounts if a["method"] == "debit-order"),
        "eft_clients": sum(1 for a in accounts if a["method"] == "eft"),
        "fibre_count": len(fibre),
        "wireless_count": len(wireless),
        "due_wireless": round(sum(a["due"] or 0 for a in wireless_owes), 2),
        "due_fibre": round(sum(a["due"] or 0 for a in fibre_owes), 2),
        "billed_wireless": round(sum(a.get("billed") or 0 for a in wireless), 2),
        "billed_fibre": round(sum(a.get("billed") or 0 for a in fibre), 2),
        "paid_wireless": round(sum(a.get("paid") or 0 for a in wireless), 2),
        "paid_fibre": round(sum(a.get("paid") or 0 for a in fibre), 2),
    }


def run_cycle(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    created = ensure_cycle_invoices(conn, today)
    receipts = apply_named_receipts(conn)
    do_n = 0
    if PENDING_DO.get("collected") and today >= date.fromisoformat(PENDING_DO["action_date"]):
        do_n = apply_collected_do(conn, PENDING_DO["action_date"], DO_CLIENTS)
    return {
        "invoices_created": len(created),
        "receipts": receipts,
        "debit_orders": do_n,
        "pending_do": PENDING_DO,
        "clients": client_accounts(conn, today),
    }


def self_test() -> int:
    failed = 0
    if invoice_day_on(date(2026, 10, 5)) != date(2026, 9, 17):
        print("FAIL invoice-day", invoice_day_on(date(2026, 10, 5)))
        failed += 1
    elif period_for(date(2026, 9, 17)) != "2026-10":
        print("FAIL period")
        failed += 1
    else:
        print("OK cycle-17th-advance")
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE customer_invoices (
            invoice_number INTEGER PRIMARY KEY,
            invoice_date TEXT, due_date TEXT, service_number TEXT, customer TEXT,
            bill_to TEXT, address TEXT, period TEXT, description TEXT,
            qty REAL, rate REAL, amount REAL, vat REAL, balance_due REAL,
            terms TEXT, status TEXT, source TEXT, filename TEXT
        );
        CREATE TABLE customer_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paid_on TEXT, customer TEXT, amount REAL, note TEXT,
            source TEXT, statement_number INTEGER
        );
        CREATE TABLE book_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paid_on TEXT, payee TEXT, memo TEXT, payment REAL, deposit REAL,
            amount REAL, balance REAL, qb_type TEXT, account TEXT,
            source TEXT, filename TEXT
        );
        """
    )
    created = ensure_cycle_invoices(conn, date(2026, 10, 5), DO_CLIENTS[:2])
    if len(created) != 2 or created[0]["invoice_date"] != "2026-09-17":
        print("FAIL sep-invoice", created)
        failed += 1
    else:
        print("OK sep-17-invoices")
    # Named EFT receipt clears one client; the other waits on 5 Oct D/O.
    conn.execute(
        """INSERT INTO book_entries
           (paid_on, payee, memo, payment, deposit, amount, balance, qb_type, account, source)
           VALUES ('2026-09-30','David Wantling','EFT',0,439,439,0,'Payment',
                   'Accounts Receivable (A/R)','qb_fnb_history')"""
    )
    apply_named_receipts(conn)
    acc = client_accounts(conn, date(2026, 10, 5))
    want = next(a for a in acc["accounts"] if a["name"] == "David Wantling")
    dirk = next(a for a in acc["accounts"] if a["name"] == "Dirk De Villiers")
    if not want["nil"]:
        print("FAIL wantling-should-be-nil", want)
        failed += 1
    elif dirk["nil"] or abs((dirk["due"] or 0) - 399) > 0.01:
        print("FAIL dirk-still-due-until-do", dirk)
        failed += 1
    elif not dirk.get("pending_do") or dirk["pending_do"]["action_date"] != "2026-10-05":
        print("FAIL pending-do", dirk)
        failed += 1
    else:
        print("OK do-not-off-until-collected")
    # After collection, full D/O (not net of fees) clears the invoice.
    apply_collected_do(conn, "2026-10-05", [DO_CLIENTS[1]])
    acc2 = client_accounts(conn, date(2026, 10, 6))
    dirk2 = next(a for a in acc2["accounts"] if a["name"] == "Dirk De Villiers")
    if not dirk2["nil"]:
        print("FAIL do-clears-invoice", dirk2)
        failed += 1
    else:
        print("OK do-full-amount-nil-vs-inv")
    if do_action_date(date(2026, 9, 17)) != date(2026, 10, 5):
        print("FAIL oct-do-exception", do_action_date(date(2026, 9, 17)))
        failed += 1
    elif do_action_date(date(2026, 10, 17)) != date(2026, 11, 1):
        print("FAIL nov-do-first", do_action_date(date(2026, 10, 17)))
        failed += 1
    else:
        print("OK do-1st-except-oct5")
    fibre_do = [c for c in DO_CLIENTS if c["access"] == "fibre"]
    wireless_do = [c for c in DO_CLIENTS if c["access"] == "wireless"]
    nord = next(c for c in CLIENTS if c["name"] == "Bing Noordhoek Fibre")
    bing_wifi = next(c for c in CLIENTS if c["name"] == "Annette Bing HH")
    builders = next(c for c in CLIENTS if c["name"] == "Hermanus Builders")
    geo = next(c for c in CLIENTS if c["name"] == "GeoCorp")
    if nord["access"] != "fibre" or nord.get("sku") != "OWS25M":
        print("FAIL noordhoek-is-fibre", nord)
        failed += 1
    elif bing_wifi["access"] != "wireless" or bing_wifi.get("sku"):
        print("FAIL bing-hh-is-wifi", bing_wifi)
        failed += 1
    elif "hermanus heights" not in (bing_wifi.get("address") or "").lower():
        print("FAIL bing-hh-hermanus-heights", bing_wifi.get("address"))
        failed += 1
    elif "sleepy" in (bing_wifi.get("address") or "").lower() or "noordhoek" in (bing_wifi.get("address") or "").lower():
        print("FAIL bing-hh-not-noordhoek", bing_wifi.get("address"))
        failed += 1
    elif "noordhoek" not in (nord.get("address") or "").lower() and "sleepy" not in (nord.get("address") or "").lower():
        print("FAIL noordhoek-address", nord.get("address"))
        failed += 1
    elif builders["access"] != "fibre" or geo["access"] != "fibre":
        print("FAIL builders-geocorp-fibre", builders, geo)
        failed += 1
    elif len(DO_CLIENTS) != 14 or not fibre_do or not wireless_do:
        print("FAIL do-mix", len(DO_CLIENTS), len(fibre_do), len(wireless_do))
        failed += 1
    elif not EFT_CLIENTS or not any(c["access"] == "fibre" for c in EFT_CLIENTS):
        print("FAIL eft-fibre", EFT_CLIENTS)
        failed += 1
    else:
        print("OK fibre-wireless-do-and-eft")
    extra = extra_charges()
    if any(x["on_monthly_do"] for x in extra) or {x["code"] for x in extra} < {
        "new-install",
        "equipment",
        "addon",
        "reconnect",
    }:
        print("FAIL extras", extra)
        failed += 1
    else:
        print("OK once-off-extras")
    rec = next((x for x in extra if x["code"] == "reconnect"), None)
    if rec and "penalty" not in (rec.get("note") or "").lower():
        print("FAIL reconnect-penalty-note", rec)
        failed += 1
    else:
        print("OK reconnect-not-on-do")
    paltco = next(c for c in CLIENTS if c["name"] == "Paltco")
    if paltco.get("access") != "offset" or not paltco.get("not_a_client") or paltco.get("sku"):
        print("FAIL paltco-offset", paltco)
        failed += 1
    elif any(a.get("name") == "Paltco" for a in acc.get("fibre", []) + acc.get("wireless", []) + acc.get("accounts", [])):
        print("FAIL paltco-not-a-service-client", acc.get("fibre_count"), acc.get("wireless_count"))
        failed += 1
    elif paltco.get("loan_account") != KEVIN_LOAN_ACCOUNT:
        print("FAIL paltco-kw-loan", paltco.get("loan_account"))
        failed += 1
    else:
        print("OK paltco-offset-kw-loan")
    de = next(c for c in CLIENTS if c["name"] == "Phillip De Gruchy")
    may = next(c for c in CLIENTS if c["name"] == "Phillipus May")
    if not by_sku(de["sku"]) or by_sku(de["sku"])["down"] != 300:
        print("FAIL de-gruchy-package", de)
        failed += 1
    elif not de.get("discount") or not may.get("discount"):
        print("FAIL phillip-discount", de, may)
        failed += 1
    else:
        print("OK package-on-client")
        print("OK phillipus-discount")
    acc = client_accounts(conn, date(2026, 10, 5))
    if not acc.get("wireless") or not acc.get("fibre"):
        print("FAIL access-lists", acc.get("wireless_count"), acc.get("fibre_count"))
        failed += 1
    elif not any(a["pay"] == "D/O" for a in acc["wireless"]) or not any(a["pay"] == "EFT" for a in acc["wireless"]):
        print("FAIL wireless-pay", acc["wireless"])
        failed += 1
    elif not any(a["pay"] == "D/O" for a in acc["fibre"]) or not any(a["pay"] == "EFT" for a in acc["fibre"]):
        print("FAIL fibre-pay", acc["fibre"])
        failed += 1
    else:
        print("OK wireless-fibre-do-eft-lists")
    if want["status"] != "paid-up" or (want.get("paid") or 0) < 438:
        print("FAIL wantling-paid-up-status", want)
        failed += 1
    elif dirk["status"] != "owes" or abs((dirk["due"] or 0) - 399) > 0.01:
        print("FAIL dirk-owes-status", dirk)
        failed += 1
    elif not any(a["name"] == "David Wantling" for a in acc.get("wireless_paid") or []):
        print("FAIL wireless-paid-list", acc.get("wireless_paid"))
        failed += 1
    elif not acc.get("fibre_owes"):
        print("FAIL fibre-owes-list", acc.get("fibre_owes"))
        failed += 1
    else:
        print("OK paid-up-vs-owes")
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
