#!/usr/bin/env python3
"""Simple client cards for /dash/clients.html.

Incoming VK Pop fibre is not a client. Auto-suspend / WhatsApp / notes come later.
"""
from __future__ import annotations

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
    if "albertyn" in blob:
        return "geocorp"
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


def _offset_card(row: dict) -> dict:
    extra = customer_lookup(row.get("name"))
    note = row.get("offset_note") or (
        "Offset deal. Not a fibre or wifi client. No B-number. "
        "Cash against Kevin Weaving loan. Fibre stays cost of service."
    )
    return {
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
        "notes": [note],
        "search": " ".join(
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
        ).lower(),
    }


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
                    card["master"] = st.get("master")
                    card["sub"] = st.get("sub")
                    card["own_sub"] = st.get("own_sub")
                    card["other_subs"] = []
                    card["earlier_paid"] = st.get("earlier_paid") or 0
                    card.update(_grace(st, today))
            except Exception:
                pass
        _apply_os_margin(card, os_map, None)
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
    offsets = [_offset_card(row) for row in OFFSET_DEALS]
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
    pack = cards_for_export(None, [pop, hpp, broken, held, aljo, aman, johannes, georgala], today)
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
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
