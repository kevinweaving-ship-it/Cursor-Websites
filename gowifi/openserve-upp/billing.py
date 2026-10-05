#!/usr/bin/env python3
"""Month-in-advance billing: invoice on the 17th, D/O loaded then, collected next month.

Netcash fees come off the FNB settlement, not the client. A successful D/O
clears the invoice in full. A loaded-but-uncollected batch stays on the client.
"""
from __future__ import annotations

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
# Netcash masterfile (batch 2571994). Amount is the line rental only —
# install / equipment / add-ons / reconnect are extras, not on the D/O.
CLIENTS = [
    {"ref": "Wantling", "name": "David Wantling", "amount": 439.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "DEV001", "name": "Dirk De Villiers", "amount": 399.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "BIN001", "name": "Annette Bing HH", "amount": 429.00, "method": "debit-order", "access": "fibre", "sku": "OWS25M"},
    {"ref": "HUN001", "name": "Stan Hundermark", "amount": 329.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "De Gruchy OS Fiber 200", "name": "Phillip De Gruchy", "amount": 1219.00, "method": "debit-order", "access": "fibre", "sku": "OWS300M", "discount": True},
    {"ref": "Jean de Villiers", "name": "Jean de Villiers", "amount": 550.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "Havenga", "name": "Havenga", "amount": 699.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "HM Builders", "name": "Hermanus Builders", "amount": 759.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "GeoCorp", "name": "GeoCorp", "amount": 759.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "Bryant Michael", "name": "Bryant Michael", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Murray DH", "name": "Murray DH", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Bing Noordhoek Fibre", "name": "Bing Noordhoek Fibre", "amount": 599.00, "method": "debit-order", "access": "wireless", "sku": None},
    {"ref": "G Cupido", "name": "G Cupido", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": "Gordon Neethling", "name": "Gordon Neethling", "amount": 759.00, "method": "debit-order", "access": "fibre", "sku": "OWS50M"},
    {"ref": None, "name": "Lategan", "amount": 999.00, "method": "eft", "access": "fibre", "sku": "OWS100M"},
    {"ref": None, "name": "HPP Control Room", "amount": 599.00, "method": "eft", "access": "fibre", "sku": "OWS25M"},
    {"ref": None, "name": "Pearson, Philippa", "amount": 329.00, "method": "eft", "access": "wireless", "sku": None},
    {"ref": None, "name": "Phillipus May", "amount": 439.00, "method": "eft", "access": "wireless", "sku": None, "discount": True},
    {"ref": None, "name": "Amoroc Doors", "amount": 199.00, "method": "eft", "access": "wireless", "sku": None},
    {"ref": None, "name": "WCC Tech", "amount": 1000.00, "method": "eft", "access": "wireless", "sku": None},
    {"ref": None, "name": "Paltco", "amount": 1399.00, "method": "eft", "access": "wireless", "sku": None},
    {"ref": None, "name": "Mrs Marlene/Georg Van Eeden", "amount": 439.00, "method": "eft", "access": "wireless", "sku": None},
]

DO_CLIENTS = [row for row in CLIENTS if row["method"] == "debit-order"]
EFT_CLIENTS = [row for row in CLIENTS if row["method"] == "eft"]

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
    "paltco": "paltco",
    "marlene georg": "marlene georg",
    "van eeden": "marlene georg",
    "georg van": "marlene georg",
}


def canon_key(name: str | None) -> str:
    key = client_key(name)
    return _NAME_ALIASES.get(key, key)


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
    "batch_name": "Debit batch for 05 Oct 2026",
    "status": "Authorised",
    "volume": 14,
    "amount": 9217.00,
    "collected": False,
    "normal_day": DO_DAY,
    "note": (
        "Normally collected on the 1st. This cycle the 17 Sep load was missed, "
        "so the first same-day slot was 5 Oct. Authorised, not collected."
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
    head = pkg["label"] if pkg else ("Fibre" if row.get("access") == "fibre" else "Wireless")
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
    n = 0
    for row in clients:
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
    clients = clients or CLIENTS
    created = []
    last = conn.execute("SELECT MAX(invoice_number) FROM customer_invoices").fetchone()
    number = int(last[0] or 3113)
    for row in clients:
        key = canon_key(row["name"])
        existing = None
        for rec in conn.execute(
            """SELECT invoice_number, customer FROM customer_invoices
               WHERE invoice_date=?""",
            (inv_day.isoformat(),),
        ):
            if canon_key(rec[1]) == key:
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
    pending["collected"] = False
    pending["note"] = (
        f"D/O {pending['action_date']} authorised, not collected. "
        f"Normally the 1st; this cycle was 5 Oct. "
        f"September invoices stay on the client. Fees do not reduce the D/O."
    )
    by_key = {}
    for row in CLIENTS:
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
        }
    for pay in payments:
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
        due = round(inv_amt - cycle_credit, 2)
        pending_do = None
        if meta["method"] == "debit-order" and not pending["collected"]:
            pending_do = {
                "action_date": pending["action_date"],
                "amount": meta["do_amount"],
                "status": "authorised · not collected",
            }
        accounts.append(
            {
                "name": meta["name"],
                "ref": meta["ref"],
                "method": meta["method"],
                "access": meta.get("access"),
                "sku": meta.get("sku"),
                "package": (meta.get("package") or {}).get("label") if meta.get("package") else None,
                "discount": bool(meta.get("discount")),
                "do_amount": meta["do_amount"],
                "last_invoice": (cycle_inv or {}).get("invoice_number"),
                "last_invoice_date": (cycle_inv or {}).get("invoice_date"),
                "period": (cycle_inv or {}).get("period") or period,
                "invoice_amount": inv_amt or None,
                "due": due,
                "nil": abs(due) <= 0.004,
                "pending_do": pending_do,
                "last_payment": stmt.get("last_payment"),
            }
        )
    accounts.sort(
        key=lambda r: (
            0 if r["method"] == "debit-order" else 1,
            0 if r.get("access") == "fibre" else 1,
            r["name"] or "",
        )
    )
    return {
        "invoice_day": inv_day.isoformat(),
        "period": period,
        "period_label": period_label(period),
        "rule": (
            "Invoice on the 17th, month in advance. D/O is loaded with the invoice "
            "and collected next month on the 1st (5 Oct this cycle only). "
            "Full D/O clears the invoice; Netcash fees are a company cost. "
            "Wireless and EFT clients are on the same 17th cycle. "
            "Install, equipment, add-ons and reconnection are once-off, not on the D/O."
        ),
        "pending_do": pending,
        "do_action_date": do_action_date(inv_day).isoformat(),
        "extras": extra_charges(),
        "accounts": accounts,
        "open": sum(1 for a in accounts if not a["nil"] and a["due"] not in (None, 0)),
        "do_clients": sum(1 for a in accounts if a["method"] == "debit-order"),
        "eft_clients": sum(1 for a in accounts if a["method"] == "eft"),
        "fibre": sum(1 for a in accounts if a.get("access") == "fibre"),
        "wireless": sum(1 for a in accounts if a.get("access") == "wireless"),
    }


def run_cycle(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    created = ensure_cycle_invoices(conn, today)
    receipts = apply_named_receipts(conn)
    # Never apply PENDING_DO — 5 Oct is loaded, not paid.
    return {
        "invoices_created": len(created),
        "receipts": receipts,
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
    if len(DO_CLIENTS) != 14 or not fibre_do or not wireless_do:
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
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
