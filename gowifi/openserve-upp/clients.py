#!/usr/bin/env python3
"""Simple client cards for /dash/clients.html.

Incoming VK Pop fibre is not a client. Auto-suspend / WhatsApp / notes come later.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

from billing import (
    CLIENTS,
    OFFSET_DEALS,
    canon_key,
    client_accounts,
    is_offset,
    is_service_client,
)
from customers import lookup as customer_lookup
from site_lines import is_incoming

GRACE_DAYS = 7
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _parse(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _day_label(value) -> str | None:
    day = _parse(value)
    if not day:
        return None
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def _months(joined: date | None, today: date) -> int | None:
    if not joined:
        return None
    months = (today.year - joined.year) * 12 + (today.month - joined.month)
    if today.day < joined.day:
        months -= 1
    return max(0, months)


def _tenure(months: int | None) -> str | None:
    if months is None:
        return None
    if months < 12:
        return "1 month" if months == 1 else f"{months} months"
    years, rem = divmod(months, 12)
    ys = "1 year" if years == 1 else f"{years} years"
    if not rem:
        return ys
    rs = "1 month" if rem == 1 else f"{rem} months"
    return f"{ys} {rs}"


def _openserve_issue(line: dict | None) -> bool:
    if not line:
        return False
    status = (line.get("line_status") or "").lower()
    if status in {"cancelled", "unknown"}:
        return True
    access = (line.get("access_status") or "").lower()
    partner = (line.get("partner_status") or "").lower()
    if access and access not in {"active", "in service", "inservice"}:
        return True
    if partner and "active" not in partner:
        return True
    return False


def _dot(we_suspended: bool, line: dict | None, access: str | None, acc: dict | None = None) -> tuple[str, str]:
    if _is_cancelled(line, acc):
        return "cancelled", "Cancelled"
    if we_suspended or (line and (line.get("line_status") or "").lower() == "suspended"):
        return "suspended", "Suspended"
    if access == "fibre" and _openserve_issue(line):
        return "issue", "Openserve issue"
    return "active", "Active"


def _is_cancelled(line: dict | None, acc: dict | None = None) -> bool:
    name = ((acc or {}).get("name") or (line or {}).get("customer") or "")
    if "deleted" in name.lower():
        return True
    if (acc or {}).get("cancelled") or (acc or {}).get("closed"):
        return True
    status = ((line or {}).get("line_status") or "").lower()
    return status == "cancelled"


def _pick_line(rows: list[dict]) -> dict | None:
    live = [r for r in rows if (r.get("line_status") or "") in {"active", "suspended"}]
    return (live or rows or [None])[0]


def _line_account_key(row: dict) -> str:
    """Fibre site wins over a shared customer name. Sleepy Hollow is Noordhoek, not HH."""
    blob = " ".join(
        str(row.get(k) or "") for k in ("customer", "address", "site", "location")
    ).lower()
    if any(w in blob for w in ("noordhoek", "nordhoek", "sleepy hollow")):
        return "bing noordhoek"
    if any(w in blob for w in ("hermanus heights", "francolin")):
        return "annette bing"
    if "riebeeck" in blob and any(w in blob for w in ("sandbaai", "sanbaai", "onrus")):
        return "hermanus builders"
    return canon_key(row.get("customer"))


def _invoice_profile(conn: sqlite3.Connection | None, name: str) -> dict:
    if conn is None:
        return {}
    want = canon_key(name)
    try:
        rows = conn.execute(
            "SELECT customer, address, invoice_date FROM customer_invoices WHERE customer IS NOT NULL"
        )
    except sqlite3.OperationalError:
        return {}
    address = None
    first = None
    for rec in rows:
        if canon_key(rec[0]) != want:
            continue
        if rec[1] and not address:
            address = str(rec[1]).strip()
        day = _parse(rec[2])
        if day and (first is None or day < first):
            first = day
    return {"address": address, "first_invoice": first.isoformat() if first else None}


def _attach_attention(conn: sqlite3.Connection | None, card: dict) -> None:
    """Open fault ticket, or an install that is still only an order."""
    if conn is None:
        return
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.Error:
        return
    sn = str(card.get("b_number") or "")
    fibre = (card.get("access") or "") == "fibre"
    if fibre and sn and "service_tickets" in tables and not card.get("cancelled"):
        tickets = []
        for row in conn.execute(
            """SELECT ticket_id, status, opened_on, progress_json
               FROM service_tickets WHERE service_number=?""",
            (sn,),
        ):
            try:
                notes = json.loads(row[3] or "[]")
            except json.JSONDecodeError:
                notes = []
            tickets.append(
                {"id": row[0], "status": row[1], "opened_on": row[2], "notes": notes}
            )
        if tickets:
            card["tickets"] = tickets
            # Ticket open ≠ line down. HPP is Active/IspActive with ticket
            # 63AWK081026 still Provisional — keep the green online dot.
            line_down = False
            if "services" in tables:
                try:
                    sn_row = conn.execute(
                        """SELECT access_status, partner_status, exclusive_status
                           FROM services WHERE service_number=?""",
                        (sn,),
                    ).fetchone()
                except sqlite3.OperationalError:
                    sn_row = conn.execute(
                        """SELECT access_status, partner_status, lifecycle
                           FROM services WHERE service_number=?""",
                        (sn,),
                    ).fetchone()
                if sn_row:
                    line_down = _openserve_issue(
                        {
                            "line_status": (sn_row[2] or "").lower() or "active",
                            "access_status": sn_row[0],
                            "partner_status": sn_row[1],
                        }
                    )
            if line_down and card.get("dot") != "cancelled":
                card["dot"] = "issue"
                card["dot_label"] = "Fault · " + (tickets[0].get("status") or "Open")
                card["openserve_issue"] = True
            elif tickets[0].get("id"):
                note = "Ticket " + tickets[0]["id"] + " · " + (tickets[0].get("status") or "Open")
                notes = list(card.get("notes") or [])
                if note not in notes:
                    notes.append(note)
                card["notes"] = notes
    if (
        fibre
        and sn
        and card.get("dot") not in {"issue", "suspended", "cancelled"}
        and "orders" in tables
    ):
        order = conn.execute(
            """SELECT order_number, order_status, order_type, created_on,
                      date_implemented, remark, message_for_isp
               FROM orders WHERE service_number=?
               ORDER BY created_on DESC LIMIT 1""",
            (sn,),
        ).fetchone()
        live = None
        if order and "services" in tables:
            live = conn.execute(
                "SELECT lifecycle, access_status FROM services WHERE service_number=?",
                (sn,),
            ).fetchone()
        installed = bool(
            live
            and (live[0] or "").lower() == "active"
            and (live[1] or "").lower() == "active"
        )
        status = (order[1] if order else "") or ""
        if order and status not in {"Accepted", "Cancelled"} and not installed:
            card["dot"] = "order"
            card["dot_label"] = "Order · not installed"
            card["order"] = {
                "number": order[0],
                "status": status,
                "type": order[2],
                "ordered": order[3],
                "installed": order[4],
                "remark": order[5],
                "note": order[6],
            }
    if "customer_invoices" not in tables:
        return
    key = canon_key(card.get("name"))
    chosen = None
    for rec in conn.execute(
        """SELECT invoice_number, invoice_date, amount, balance_due, status, source, description, customer
           FROM customer_invoices"""
    ):
        if canon_key(rec[7]) != key:
            continue
        status = (rec[4] or "").lower()
        source = (rec[5] or "").lower()
        if status in {"deleted", "void", "voided"}:
            continue
        if source.startswith("gowifi-") and source != "gowifi-cancel":
            continue
        amount = float(rec[2] or 0)
        due = float(rec[3] if rec[3] is not None else 0)
        if due <= amount + 0.01:
            continue
        if chosen is None or due > chosen["due"]:
            chosen = {
                "number": rec[0],
                "date": rec[1],
                "amount": rec[2],
                "due": due,
                "description": rec[6],
                "lines": [],
            }
    if not chosen:
        return
    if "customer_invoice_lines" in tables:
        for rec in conn.execute(
            """SELECT line_no, description, amount
               FROM customer_invoice_lines
               WHERE CAST(invoice_number AS TEXT)=?
               ORDER BY line_no""",
            (str(chosen["number"]),),
        ):
            chosen["lines"].append({"description": rec[1], "amount": rec[2]})
    card["invoice"] = chosen
    statement_due = float(card.get("due") or 0)
    if abs(statement_due) > 0.01:
        return
    card["due"] = chosen["due"]
    card["paid"] = card.get("paid") or 0
    card["paid_up"] = False
    card["balance_label"] = f"Due {chosen['due']:.2f}"
    if not card.get("billed"):
        card["billed"] = chosen["due"]



def _haystack(card: dict) -> str:
    bits = [
        card.get("name"),
        card.get("address"),
        card.get("phone"),
        card.get("email"),
        card.get("b_number"),
        card.get("package"),
        card.get("access"),
        "wifi" if (card.get("access") or "") != "fibre" else "fibre",
        card.get("pay"),
        "loss" if card.get("os_loss") else None,
        card.get("os_cost_label"),
        "cancelled" if card.get("cancelled") else None,
    ]
    return " ".join(str(b) for b in bits if b).lower()


def _package(acc: dict, line: dict | None) -> str | None:
    if acc.get("package"):
        return acc["package"]
    fibre = (acc.get("access") or "") == "fibre"
    if fibre and line and (line.get("product") or line.get("speed")):
        return " · ".join(p for p in (line.get("product"), line.get("speed")) if p)
    if not fibre:
        amt = acc.get("monthly") or acc.get("amount") or acc.get("do_amount") or acc.get("billed")
        return f"Wireless{f' R{amt:.0f}' if amt else ''}"
    return None


def _grace(acc: dict, today: date) -> dict:
    due = float(acc.get("due") or 0)
    paid_up = bool(acc.get("nil") or acc.get("status") == "paid-up")
    bounced = bool(acc.get("bounced") or acc.get("suspension_notice"))
    pending = acc.get("pending_do") or {}
    do_grace = bool(acc.get("in_do_grace") or (pending and not pending.get("reconciled") and not paid_up))
    inv = _parse(acc.get("last_invoice_date") or acc.get("last_paid_on"))
    days = (today - inv).days if inv else None
    in_grace = do_grace or ((not paid_up) and (not bounced) and days is not None and 0 <= days <= GRACE_DAYS)
    if bounced:
        label = f"D/O bounced · Due {due:.2f} · Suspension notice"
    elif paid_up:
        label = "Paid Up"
    elif do_grace:
        label = f"D/O pending · {pending.get('action_date')} · not due until reconciled"
    elif in_grace:
        label = f"Grace · due {due:.2f}"
    else:
        label = f"Due {due:.2f}"
    return {
        "grace_days": GRACE_DAYS,
        "in_grace": in_grace,
        "days_since_invoice": days,
        "bounced": bounced,
        "suspension_notice": bounced,
        "balance_label": label,
    }


def _offset_card(
    row: dict,
    conn: sqlite3.Connection | None = None,
    today: date | None = None,
) -> dict:
    extra = customer_lookup(row.get("name"))
    note = row.get("offset_note") or (
        "Offset deal. Not a fibre or wifi client. No B-number. "
        "Cash against Kevin Weaving loan. Fibre stays cost of service."
    )
    card = {
        "name": row.get("name"),
        "address": (extra or {}).get("address") or None,
        "phone": (extra or {}).get("phone") or None,
        "email": (extra or {}).get("email"),
        "started": None,
        "started_label": "—",
        "months": None,
        "tenure": None,
        "b_number": None,
        "package": "Offset · Office Connect contribution",
        "access": "offset",
        "not_a_client": True,
        "pay": "EFT",
        "discount": False,
        "billed": row.get("amount"),
        "paid": 0,
        "due": None,
        "paid_up": False,
        "charge": None,
        "os_cost": None,
        "os_on_invoice": False,
        "loan_account": row.get("loan_account"),
        "offset_note": note,
        "dot": "active",
        "dot_label": "Offset · KW loan",
        "balance_label": "Offset · KW loan",
        "ledger": [],
        "earlier_paid": 0,
        "notes": [note],
    }
    if conn is not None:
        try:
            from statements import account_as_at

            st = account_as_at(conn, row.get("name"), today)
            if not ((st.get("billed") or 0) > 0.004 or (st.get("ledger") or [])):
                card["search"] = " ".join(
                    p
                    for p in (
                        row.get("name"),
                        "paltco",
                        "patriot",
                        "offset",
                        "loan",
                        "kevin",
                        note,
                    )
                    if p
                ).lower()
                return card
            billed = st.get("billed")
            paid = st.get("paid") or 0
            due = st.get("due")
            card["billed"] = billed
            card["paid"] = paid
            card["due"] = due
            card["paid_up"] = bool(st.get("nil") or st.get("status") == "paid-up")
            card["ledger"] = st.get("ledger") or []
            card["ageing"] = st.get("ageing") or {}
            card["earlier_paid"] = st.get("earlier_paid") or 0
            card["status"] = st.get("status")
            first = next(
                (
                    r.get("date")
                    for r in reversed(card["ledger"])
                    if r.get("kind") == "invoice" and r.get("date")
                ),
                None,
            )
            if first:
                card["started"] = first
                card["started_label"] = _day_label(first)
                card["months"] = _months(_parse(first), today or date.today())
                card["tenure"] = _tenure(card["months"])
            due_amt = float(due or 0)
            if card["paid_up"] or due_amt <= 0.004:
                card["balance_label"] = "Paid Up"
            else:
                card["balance_label"] = f"Due {due_amt:.2f}"
        except Exception:
            pass
    card["search"] = " ".join(
        p
        for p in (
            row.get("name"),
            "paltco",
            "patriot",
            "offset",
            "loan",
            "kevin",
            note,
            card.get("balance_label"),
        )
        if p
    ).lower()
    return card


def _apply_os_margin(card: dict, os_map: dict, charge: float | None) -> None:
    """Openserve CSV cost (B-number lines + VAT) vs what we charge."""
    if (card.get("access") or "") != "fibre":
        return
    os_row = os_map.get(card.get("b_number") or "") if card.get("b_number") else None
    cost = (os_row or {}).get("cost")
    card["os_cost"] = cost
    card["os_ex_vat"] = (os_row or {}).get("ex_vat")
    card["os_vat"] = (os_row or {}).get("vat")
    card["os_cost_label"] = (os_row or {}).get("label")
    card["os_period"] = (os_row or {}).get("period")
    card["os_invoice"] = (os_row or {}).get("invoice_number")
    card["os_on_invoice"] = bool(os_row)
    card["charge"] = charge
    margin = None
    pct = None
    if cost is not None and charge:
        margin = round(float(charge) - float(cost), 2)
        pct = round(margin / float(charge) * 100, 1) if charge else None
    card["margin"] = margin
    card["margin_pct"] = pct
    card["os_loss"] = bool(margin is not None and margin < -0.004)


def cards_for_export(
    conn: sqlite3.Connection | None,
    fibre_rows: list[dict] | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    fibre_rows = fibre_rows or []
    os_map: dict = {}
    if conn is not None:
        try:
            from invoice_import import cost_by_service

            os_map = cost_by_service(conn)
        except Exception:
            os_map = {}
    by_line: dict[str, list[dict]] = {}
    unmatched: list[dict] = []
    for row in fibre_rows:
        if is_incoming(row=row):
            continue
        key = _line_account_key(row)
        if not key:
            unmatched.append(row)
            continue
        by_line.setdefault(key, []).append(row)

    billed = {}
    if conn is not None:
        try:
            billed = client_accounts(conn, today)
        except sqlite3.OperationalError:
            billed = {"accounts": []}
    accounts = list(billed.get("accounts") or [])
    if not accounts:
        accounts = [
            {
                "name": c["name"],
                "access": c.get("access"),
                "sku": c.get("sku"),
                "package": None,
                "pay": "D/O" if c.get("method") == "debit-order" else "EFT",
                "method": c.get("method"),
                "billed": c.get("amount"),
                "paid": 0,
                "due": c.get("amount"),
                "nil": False,
                "status": "owes",
                "last_invoice_date": None,
                "discount": bool(c.get("discount")),
                "phone": c.get("phone"),
                "address": c.get("address"),
                "suspended": bool(c.get("suspended")),
            }
            for c in CLIENTS
            if is_service_client(c)
        ]

    live_keys = {canon_key(c["name"]) for c in CLIENTS}
    used = set()
    cards = []
    cancelled = []
    for acc in accounts:
        key = canon_key(acc.get("name"))
        if key in used or is_offset(acc) or is_offset(next((c for c in CLIENTS if canon_key(c["name"]) == key), None)):
            continue
        used.add(key)
        fibre = (acc.get("access") or "") == "fibre"
        book = next((c for c in CLIENTS if canon_key(c["name"]) == key), None)
        line = _pick_line(by_line.get(key) or []) if fibre else None
        hist = _invoice_profile(conn, acc.get("name") or "")
        cust = customer_lookup(acc.get("name"))
        if conn is not None:
            try:
                from statements import account_as_at

                st = account_as_at(conn, acc.get("name"), today)
                if st.get("billed") is not None:
                    acc = {
                        **acc,
                        "billed": st.get("billed"),
                        "paid": st.get("paid"),
                        "due": st.get("due"),
                        "nil": st.get("nil"),
                        "status": st.get("status"),
                        "pending_do": st.get("pending_do"),
                        "bounced": st.get("bounced"),
                        "suspension_notice": st.get("suspension_notice"),
                        "in_do_grace": st.get("in_do_grace"),
                        "monthly": st.get("monthly"),
                        "ledger": st.get("ledger") or [],
                        "ageing": st.get("ageing") or {},
                        "master": st.get("master"),
                        "sub": st.get("sub"),
                        "own_sub": st.get("own_sub"),
                        "other_subs": [],
                        "earlier_paid": st.get("earlier_paid") or 0,
                        "last_paid_on": (st.get("last_payment") or {}).get("date")
                        if isinstance(st.get("last_payment"), dict)
                        else None,
                    }
            except Exception:
                pass
        started = (
            ((line or {}).get("activated") if fibre else None)
            or ((line or {}).get("installed") if fibre else None)
            or ((line or {}).get("joined") if fibre else None)
            or hist.get("first_invoice")
            or acc.get("started")
        )
        months = _months(_parse(started), today)
        we_suspended = bool(acc.get("suspended") or (line or {}).get("we_suspended"))
        gone = _is_cancelled(line, acc)
        dot, dot_label = _dot(we_suspended, line, acc.get("access"), acc)
        if gone:
            dot, dot_label = "cancelled", "Cancelled"
        grace = _grace(acc, today)
        due = acc.get("due")
        fibre_b = (line or {}).get("service_number") if fibre else None
        book_addr = (book or {}).get("address") or acc.get("address")
        cust_addr = (cust or {}).get("address")
        line_addr = (line or {}).get("address") if fibre else None
        card = {
            "name": acc.get("name"),
            "address": book_addr or cust_addr or line_addr or hist.get("address"),
            "phone": acc.get("phone") or (line or {}).get("phone") or (cust or {}).get("phone"),
            "email": acc.get("email") or (cust or {}).get("email"),
            "started": _parse(started).isoformat() if _parse(started) else None,
            "started_label": _day_label(started),
            "months": months,
            "tenure": _tenure(months),
            "b_number": fibre_b or ((cust or {}).get("b_number") if acc.get("access") == "fibre" else None),
            "package": _package(acc, line),
            "access": acc.get("access") or "wireless",
            "pay": acc.get("pay") or ("D/O" if acc.get("method") == "debit-order" else "EFT"),
            "discount": bool(acc.get("discount")),
            "billed": acc.get("billed"),
            "paid": acc.get("paid") or 0,
            "due": due,
            "paid_up": bool(acc.get("nil") or acc.get("status") == "paid-up"),
            "ledger": acc.get("ledger") or [],
            "ageing": acc.get("ageing") or {},
            "master": acc.get("master"),
            "sub": acc.get("sub"),
            "own_sub": acc.get("own_sub"),
            "other_subs": [],
            "earlier_paid": acc.get("earlier_paid") or 0,
            "dot": dot,
            "dot_label": dot_label,
            "we_suspended": we_suspended,
            "openserve_issue": _openserve_issue(line) if acc.get("access") == "fibre" else False,
            "notes": [],
            "later": {
                "auto_suspend": False,
                "whatsapp": False,
                "notify_admin": True,
                "note": "Later: auto suspend, WhatsApp, client reply notes — all copied to admin.",
            },
        }
        card["cancelled"] = gone
        if gone:
            card["dot"] = "cancelled"
            card["dot_label"] = "Cancelled"
            card["pay"] = acc.get("pay")
        card.update(grace)
        _apply_os_margin(
            card,
            os_map,
            float((book or {}).get("amount") or acc.get("do_amount") or acc.get("amount") or 0) or None,
        )
        _attach_attention(conn, card)
        card["search"] = _haystack(card)
        if gone:
            cancelled.append(card)
        else:
            cards.append(card)

    for key, rows in by_line.items():
        if key in used:
            continue
        line = _pick_line(rows)
        if not line:
            continue
        started = line.get("activated") or line.get("installed") or line.get("joined")
        months = _months(_parse(started), today)
        we_suspended = (line.get("line_status") or "") == "suspended"
        dot, dot_label = _dot(we_suspended, line, "fibre", None)
        extra = customer_lookup(line.get("customer"))
        gone = _is_cancelled(line, None)
        if gone:
            dot, dot_label = "cancelled", "Cancelled"
        card = {
            "name": line.get("customer"),
            "address": line.get("address") or (extra or {}).get("address"),
            "phone": line.get("phone") or (extra or {}).get("phone"),
            "email": (extra or {}).get("email"),
            "started": _parse(started).isoformat() if _parse(started) else None,
            "started_label": _day_label(started),
            "months": months,
            "tenure": _tenure(months),
            "b_number": line.get("service_number") or (extra or {}).get("b_number"),
            "package": _package({"access": "fibre"}, line),
            "access": "fibre",
            "pay": None,
            "discount": False,
            "billed": None,
            "paid": 0,
            "due": None,
            "paid_up": False,
            "dot": dot,
            "dot_label": dot_label,
            "we_suspended": we_suspended,
            "cancelled": gone,
            "openserve_issue": False if gone else _openserve_issue(line),
            "grace_days": GRACE_DAYS,
            "in_grace": False,
            "days_since_invoice": None,
            "balance_label": "—",
            "notes": [],
            "later": {
                "auto_suspend": False,
                "whatsapp": False,
                "notify_admin": True,
                "note": "Later: auto suspend, WhatsApp, client reply notes — all copied to admin.",
            },
        }
        if conn is not None:
            try:
                from statements import account_as_at

                st = account_as_at(conn, line.get("customer"), today)
                if st.get("billed"):
                    card["billed"] = st.get("billed")
                    card["paid"] = st.get("paid") or 0
                    card["due"] = st.get("due")
                    card["paid_up"] = bool(st.get("nil"))
                    card["ledger"] = st.get("ledger") or []
                    card["ageing"] = st.get("ageing") or {}
                    card["master"] = st.get("master")
                    card["sub"] = st.get("sub")
                    card["own_sub"] = st.get("own_sub")
                    card["other_subs"] = []
                    card["earlier_paid"] = st.get("earlier_paid") or 0
                    card.update(_grace(st, today))
            except Exception:
                pass
        _apply_os_margin(card, os_map, None)
        _attach_attention(conn, card)
        card["search"] = _haystack(card)
        if gone:
            cancelled.append(card)
        else:
            cards.append(card)

    cards.sort(
        key=lambda r: (
            0 if (r.get("access") or "") != "fibre" else 1,
            (r.get("name") or "").lower(),
        )
    )
    cancelled.sort(key=lambda r: (-float(r.get("due") or 0), (r.get("name") or "").lower()))
    still_owe = sum(1 for c in cancelled if float(c.get("due") or 0) > 0.004)
    fibre_cards = [c for c in cards if (c.get("access") or "") == "fibre"]
    missing_names = [c["name"] for c in fibre_cards if not c.get("os_on_invoice")]
    loss_names = [c["name"] for c in fibre_cards if c.get("os_loss")]
    invoice_date = next((v.get("invoice_date") for v in os_map.values()), None)
    offsets = [_offset_card(row, conn, today) for row in OFFSET_DEALS]
    fnb = None
    if conn is not None:
        try:
            from fnb_api import card as fnb_card

            fnb = fnb_card(conn)
        except Exception:
            fnb = None
    return {
        "as_at": today.isoformat(),
        "grace_days": GRACE_DAYS,
        "count": len(cards),
        "active": sum(1 for c in cards if c["dot"] == "active"),
        "issue": sum(1 for c in cards if c["dot"] == "issue"),
        "suspended": sum(1 for c in cards if c["dot"] == "suspended"),
        "cancelled_count": len(cancelled),
        "cancelled_due": still_owe,
        "cards": cards,
        "cancelled": cancelled,
        "offsets": offsets,
        "fnb": fnb,
        "os": {
            "invoice_date": invoice_date,
            "fibre": len(fibre_cards),
            "on_invoice": sum(1 for c in fibre_cards if c.get("os_on_invoice")),
            "missing": len(missing_names),
            "missing_names": missing_names,
            "loss": len(loss_names),
            "loss_names": loss_names,
        },
        "note": (
            "Simple client cards. Cancelled clients are not on this list — "
            "they sit in the Cancelled card at the bottom. "
            "VK Pop incoming fibre is not a client. "
            "Paltco is an offset deal — not fibre or wifi, no B-number; cash against Kevin loan. "
            "Fibre cost is the latest Openserve invoice CSV per B-number + VAT. "
            "Later: auto suspend, WhatsApp, notes to admin."
        ),
    }


def self_test() -> int:
    failed = 0
    today = date(2026, 10, 5)
    pop = {
        "service_number": "B110033875",
        "customer": "GoWiFi · VK Pop",
        "incoming_role": "primary",
        "line_status": "active",
        "address": "21A FOURTH AV, VOELKLIP",
        "product": "Webstream",
        "speed": "500/250",
    }
    hpp = {
        "service_number": "B110047678",
        "customer": "HPP Control Room",
        "line_status": "active",
        "access_status": "Active",
        "partner_status": "IspActive",
        "address": "10323 MUSSEL RD HERMANUS",
        "activated": "2025-10-08",
        "product": "Webstream",
        "speed": "25/25",
    }
    broken = {
        "service_number": "B110000001",
        "customer": "Annette Bing",
        "line_status": "active",
        "access_status": "Fault",
        "partner_status": "IspActive",
        "address": "13 SLEEPY HOLLOW LN, NOORDHOEK, NOORDHOEK",
        "activated": "2026-03-25",
        "product": "Webstream",
        "speed": "25/25",
    }
    held = {
        "service_number": "B110000002",
        "customer": "Lategan",
        "line_status": "suspended",
        "address": "2 Test",
        "activated": "2024-06-01",
        "product": "Webstream",
        "speed": "100/50",
    }
    aljo = {
        "service_number": "B110040916",
        "customer": "Aljo van Vreden",
        "line_status": "cancelled",
        "address": "177A TURTLE CL VERMONT",
        "activated": "2025-08-03",
        "product": "Webstream",
        "speed": "50/25",
    }
    aman = {
        "service_number": "B110062840",
        "customer": "Aman Breedt",
        "line_status": "cancelled",
        "address": "22 DISA SANDBAAI",
        "product": "Webstream",
        "speed": "20/10",
    }
    johannes = {
        "service_number": "B110058887",
        "customer": "Johannes Lategan",
        "line_status": "active",
        "address": "LE PARADIS",
        "activated": "2026-04-04",
        "product": "Webstream",
        "speed": "100/50",
    }
    georgala = {
        "service_number": "B110037269",
        "customer": "Michael Georgala",
        "line_status": "active",
        "access_status": "Active",
        "partner_status": "IspActive",
        "address": "26 ALBERTYN ST,HERMANUS,HERMANUS",
        "activated": "2025-03-20",
        "product": "Webstream",
        "speed": "50/25",
    }
    derek = {
        "service_number": "B110064628",
        "customer": "Derek van Zyl",
        "line_status": "active",
        "address": "42 ALBERTYN ST,HERMANUS,HERMANUS",
        "activated": "2026-09-26",
        "product": "Webstream",
        "speed": "50/25",
    }
    collette = {
        "service_number": "B110063819",
        "customer": "Collette Brink",
        "line_status": "active",
        "access_status": "Active",
        "partner_status": "IspActive",
        "address": "3 JAN VAN RIEBEECK CT,SANDBAAI,ONRUS RIVER",
        "activated": "2026-08-01",
        "product": "Webstream",
        "speed": "50/25",
    }
    pack = cards_for_export(None, [pop, hpp, broken, held, aljo, aman, johannes, georgala, derek, collette], today)
    names = [c["name"] for c in pack["cards"]]
    by = {c["name"]: c for c in pack["cards"]}
    cancelled_names = [c["name"] for c in pack.get("cancelled") or []]
    if any(c.get("b_number") == "B110033875" for c in pack["cards"]):
        print("FAIL pop-not-a-client", names)
        failed += 1
    elif "GoWiFi · VK Pop" in names:
        print("FAIL pop-name", names)
        failed += 1
    elif by["HPP Control Room"]["b_number"] != "B110047678":
        print("FAIL hpp-b", by["HPP Control Room"])
        failed += 1
    elif by["HPP Control Room"]["dot"] != "active":
        print("FAIL hpp-green", by["HPP Control Room"])
        failed += 1
    elif by["Bing Noordhoek Fibre"]["dot"] != "issue":
        print("FAIL noordhoek-fibre-red", by["Bing Noordhoek Fibre"])
        failed += 1
    elif (by["Annette Bing HH"].get("access") or "") == "fibre" or by["Annette Bing HH"].get("b_number"):
        print("FAIL bing-wifi-not-fibre", by["Annette Bing HH"])
        failed += 1
    elif not (by["Annette Bing HH"].get("package") or "").startswith("Wireless"):
        print("FAIL bing-wifi-package", by["Annette Bing HH"].get("package"))
        failed += 1
    elif (by["Bing Noordhoek Fibre"].get("access") or "") != "fibre":
        print("FAIL noordhoek-not-fibre", by["Bing Noordhoek Fibre"])
        failed += 1
    elif "hermanus heights" not in (by["Annette Bing HH"].get("address") or "").lower():
        print("FAIL hh-address-hermanus-heights", by["Annette Bing HH"].get("address"))
        failed += 1
    elif "sleepy" in (by["Annette Bing HH"].get("address") or "").lower() or "noordhoek" in (
        by["Annette Bing HH"].get("address") or ""
    ).lower():
        print("FAIL hh-not-noordhoek-address", by["Annette Bing HH"].get("address"))
        failed += 1
    elif "sleepy" not in (by["Bing Noordhoek Fibre"].get("address") or "").lower() and "noordhoek" not in (
        by["Bing Noordhoek Fibre"].get("address") or ""
    ).lower():
        print("FAIL noordhoek-address", by["Bing Noordhoek Fibre"].get("address"))
        failed += 1
    elif (by["Annette Bing HH"].get("started") or "") == "2026-03-25":
        print("FAIL hh-not-fibre-start", by["Annette Bing HH"])
        failed += 1
    elif by["Lategan"]["dot"] != "suspended":
        print("FAIL lategan-orange", by["Lategan"])
        failed += 1
    elif by["David Wantling"].get("b_number"):
        print("FAIL wireless-no-b", by["David Wantling"])
        failed += 1
    elif by["HPP Control Room"]["tenure"] != "11 months":
        print("FAIL tenure", by["HPP Control Room"])
        failed += 1
    elif "mussel" not in by["HPP Control Room"]["search"]:
        print("FAIL search", by["HPP Control Room"]["search"])
        failed += 1
    elif names.index("David Wantling") > names.index("HPP Control Room"):
        print("FAIL wifi-before-fibre", names)
        failed += 1
    elif "Aljo van Vreden" in names or "Aman Breedt" in names or "Johannes Lategan" in names:
        print("FAIL cancelled-or-dup-in-clients", names)
        failed += 1
    elif names.count("Lategan") != 1:
        print("FAIL lategan-dup", names)
        failed += 1
    elif set(cancelled_names) < {"Aljo van Vreden", "Aman Breedt"}:
        print("FAIL cancelled-list", cancelled_names)
        failed += 1
    elif canon_key("Johannes Lategan") != "lategan" or canon_key("Patriot SA / Paltco") != "paltco":
        print("FAIL alias-dedup", canon_key("Johannes Lategan"), canon_key("Patriot SA / Paltco"))
        failed += 1
    elif canon_key("Such, James (deleted)") != "james such":
        print("FAIL deleted-key", canon_key("Such, James (deleted)"))
        failed += 1
    elif "Michael Georgala" in names or "Michael Georgala" in cancelled_names:
        print("FAIL georgala-is-geocorp-not-own-card", names, cancelled_names)
        failed += 1
    elif by["GeoCorp"].get("b_number") != "B110037269":
        print("FAIL geocorp-b-from-georgala", by["GeoCorp"])
        failed += 1
    elif "Derek van Zyl" not in names or by["Derek van Zyl"].get("b_number") != "B110064628":
        print("FAIL derek-not-geocorp", names, by.get("Derek van Zyl"))
        failed += 1
    elif "Collette Brink" in names or "Collette Brink" in cancelled_names:
        print("FAIL collette-is-builders-not-own-card", names, cancelled_names)
        failed += 1
    elif by["Hermanus Builders"].get("b_number") != "B110063819":
        print("FAIL builders-b-from-collette", by["Hermanus Builders"])
        failed += 1
    elif _grace(
        {
            "nil": True,
            "status": "paid-up",
            "pending_do": {"action_date": "2026-10-05", "reconciled": True},
        },
        today,
    )["balance_label"] != "Paid Up":
        print("FAIL paid-up-plain-label")
        failed += 1
    else:
        print("OK client-cards")
        print("OK cancelled-own-list")
    conn = sqlite3.connect(":memory:")
    from invoice_import import ingest_csv_text

    ingest_csv_text(
        conn,
        (
            "Account Number,Invoice Number,Invoice Date,Service Name,Invoice Text,"
            "Charge Amount,Product,Capacity,Activation Date,Charge Date,"
            "Period Start Date,Period End Date\n"
            "9400000004759,INATS099,20260131,B110034779,Rental - Openserve Webstream 200 Mbps,"
            "775.00,Openserve Webstream,200,20240916,20260131,20260201,20260228\n"
            "9400000004759,INATS099,20260131,B110034779,Dynamic IPV4 Recurring,"
            "100.00,Openserve Webstream,200,20240916,20260131,20260201,20260228\n"
            "9400000004759,INATS099,20260131,B110047678,Rental - Openserve Webstream 25 Mbps,"
            "800.00,Openserve Webstream,25,20251008,20260131,20260201,20260228\n"
            "9400000004759,INATS099,20260131,B110047678,Dynamic IPV4 Recurring,"
            "100.00,Openserve Webstream,25,20251008,20260131,20260201,20260228\n"
            "9400000004759,INATS099,20260131,B110033875,Rental - Openserve Webstream 500 Mbps,"
            "1015.00,Openserve Webstream,500,20251224,20260131,20260201,20260228\n"
            "9400000004759,INATS099,20260131,B110033875,Dynamic IPV4 Recurring,"
            "100.00,Openserve Webstream,500,20251224,20260131,20260201,20260228\n"
            "9400000004657,INATS098,20260131,B110034814,Rental - OOC - 500 Mbps,"
            "1710.00,Openserve Office Connect,500,20250122,20260131,20260201,20260228\n"
            "9400000004657,INATS098,20260131,B110034814,Dynamic IPV4 Recurring,"
            "100.00,Openserve Office Connect,500,20250122,20260131,20260201,20260228\n"
        ),
        "multi.csv",
        "test",
    )
    phillip_line = {
        "service_number": "B110034779",
        "customer": "Phillip De Gruchy",
        "line_status": "active",
        "access_status": "Active",
        "partner_status": "IspActive",
        "address": "HERMANUS",
        "activated": "2024-09-16",
        "product": "Webstream",
        "speed": "200/100",
    }
    pack2 = cards_for_export(conn, [pop, hpp, phillip_line], today)
    by2 = {c["name"]: c for c in pack2["cards"]}
    ph = by2.get("Phillip De Gruchy") or {}
    hpp2 = by2.get("HPP Control Room") or {}
    os = pack2.get("os") or {}
    names2 = [c["name"] for c in pack2["cards"]]
    if any(c.get("b_number") in {"B110033875", "B110034814"} for c in pack2["cards"]):
        print("FAIL vk-pop-not-on-client-cards", names2)
        failed += 1
    elif abs(float(ph.get("os_ex_vat") or 0) - 875) > 0.01 or "IP" not in (ph.get("os_cost_label") or ""):
        print("FAIL phillip-200-ip", ph)
        failed += 1
    elif abs(float(ph.get("os_cost") or 0) - 1006.25) > 0.01:
        print("FAIL phillip-cost-vat", ph)
        failed += 1
    elif abs(float(ph.get("charge") or 0) - 1219) > 0.01:
        print("FAIL phillip-charge", ph)
        failed += 1
    elif abs(float(ph.get("margin") or 0) - 212.75) > 0.01 or ph.get("os_loss"):
        print("FAIL phillip-margin", ph)
        failed += 1
    elif abs(float(hpp2.get("os_cost") or 0) - 1035) > 0.01 or not hpp2.get("os_loss"):
        print("FAIL hpp-loss", hpp2)
        failed += 1
    elif "Phillip De Gruchy" in (os.get("missing_names") or []):
        print("FAIL phillip-should-be-on-invoice", os)
        failed += 1
    elif "HPP Control Room" in (os.get("missing_names") or []) or "HPP Control Room" not in (
        os.get("loss_names") or []
    ):
        print("FAIL hpp-loss-track", os)
        failed += 1
    elif "Bing Noordhoek Fibre" not in (os.get("missing_names") or []):
        print("FAIL fibre-missing-track", os)
        failed += 1
    elif "Paltco" in names2 or "Paltco" in (os.get("missing_names") or []):
        print("FAIL paltco-not-fibre-client", names2, os)
        failed += 1
    else:
        print("OK cost-vs-charge", ph.get("os_cost_label"), ph.get("margin"), hpp2.get("os_cost_label"))
    off = {c["name"]: c for c in pack2.get("offsets") or []}
    pal = off.get("Paltco") or {}
    if not pal or pal.get("b_number") or pal.get("access") != "offset" or not pal.get("not_a_client"):
        print("FAIL paltco-offset-card", pal)
        failed += 1
    elif "loan" not in (pal.get("offset_note") or "").lower():
        print("FAIL paltco-loan-note", pal)
        failed += 1
    else:
        print("OK paltco-offset-no-b")
    from statements import ingest as books_ingest

    books = sqlite3.connect(":memory:")
    books_ingest(books)
    pack3 = cards_for_export(books, [pop, hpp], today)
    names3 = [c["name"] for c in pack3["cards"]]
    pal3 = {c["name"]: c for c in pack3.get("offsets") or []}.get("Paltco") or {}
    pal_led = pal3.get("ledger") or []
    pal_inv = [r for r in pal_led if r.get("kind") == "invoice"]
    pal_pay = [r for r in pal_led if r.get("kind") == "payment"]
    pal_3111 = next((r for r in pal_inv if str(r.get("ref")) == "3111"), None)
    if "Paltco" in names3:
        print("FAIL paltco-not-on-client-list", names3)
        failed += 1
    elif abs(float(pal3.get("due") or 0) - 1399) > 0.02:
        print("FAIL paltco-due", pal3.get("due"), pal3.get("billed"), pal3.get("paid"))
        failed += 1
    elif "Due 1399" not in (pal3.get("balance_label") or ""):
        print("FAIL paltco-due-label", pal3.get("balance_label"))
        failed += 1
    elif abs(float(pal3.get("billed") or 0) - 16508.2) > 0.02:
        print("FAIL paltco-billed", pal3.get("billed"))
        failed += 1
    elif not pal_3111 or abs(float(pal_3111.get("open") or 0) - 1399) > 0.02:
        print("FAIL paltco-3111-open", pal_3111)
        failed += 1
    elif len(pal_inv) < 12 or len(pal_pay) < 2:
        print("FAIL paltco-full-statement", len(pal_inv), len(pal_pay))
        failed += 1
    elif any(not r.get("show") for r in pal_led):
        print("FAIL paltco-hide-applied", [r.get("what") for r in pal_led if not r.get("show")])
        failed += 1
    elif not any("EFT" in (r.get("what") or "") and "Invoice" in (r.get("what") or "") for r in pal_pay):
        print("FAIL paltco-eft-applied", [r.get("what") for r in pal_pay[:4]])
        failed += 1
    else:
        print("OK paltco-due-and-statement", pal3.get("due"), len(pal_inv), "inv", len(pal_pay), "pay")
    ticket_db = sqlite3.connect(":memory:")
    ticket_db.execute(
        """CREATE TABLE service_tickets (
            ticket_id TEXT, service_number TEXT, status TEXT,
            opened_on TEXT, progress_json TEXT, updated_at TEXT)"""
    )
    ticket_db.execute(
        """CREATE TABLE services (
            service_number TEXT, access_status TEXT, partner_status TEXT,
            exclusive_status TEXT, lifecycle TEXT)"""
    )
    ticket_db.execute(
        "INSERT INTO service_tickets VALUES (?,?,?,?,?,?)",
        ("63AWK081026", "B110047678", "Provisional", "2026-10-08", "[]", "2026-10-09"),
    )
    ticket_db.execute(
        "INSERT INTO services VALUES (?,?,?,?,?)",
        ("B110047678", "Active", "IspActive", "active", "active"),
    )
    hpp_card = {
        "name": "HPP Control Room",
        "b_number": "B110047678",
        "access": "fibre",
        "dot": "active",
        "dot_label": "Active",
        "openserve_issue": False,
        "notes": [],
        "cancelled": False,
    }
    _attach_attention(ticket_db, hpp_card)
    if hpp_card["dot"] != "active" or hpp_card.get("openserve_issue"):
        print("FAIL hpp-ticket-still-online", hpp_card.get("dot"), hpp_card.get("dot_label"))
        failed += 1
    else:
        print("OK hpp-ticket-still-online")
    ticket_db.close()
    books.close()
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
