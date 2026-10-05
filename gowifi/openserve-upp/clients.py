#!/usr/bin/env python3
"""Simple client cards for /dash/clients.html.

Incoming VK Pop fibre is not a client. Auto-suspend / WhatsApp / notes come later.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from billing import CLIENTS, canon_key, client_accounts
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
        "cancelled" if card.get("cancelled") else None,
    ]
    return " ".join(str(b) for b in bits if b).lower()


def _package(acc: dict, line: dict | None) -> str | None:
    if acc.get("package"):
        return acc["package"]
    if line and (line.get("product") or line.get("speed")):
        return " · ".join(p for p in (line.get("product"), line.get("speed")) if p)
    if acc.get("access") == "wireless":
        amt = acc.get("monthly") or acc.get("amount") or acc.get("do_amount")
        return f"Wireless{f' R{amt:.0f}' if amt else ''}"
    return None


def _grace(acc: dict, today: date) -> dict:
    due = float(acc.get("due") or 0)
    paid_up = bool(acc.get("nil") or acc.get("status") == "paid-up")
    bounced = bool(acc.get("bounced") or acc.get("suspension_notice"))
    pending = acc.get("pending_do") or {}
    do_grace = bool(acc.get("in_do_grace") or (pending and not pending.get("reconciled") and not paid_up))
    collected = bool(pending.get("reconciled"))
    inv = _parse(acc.get("last_invoice_date") or acc.get("last_paid_on"))
    days = (today - inv).days if inv else None
    in_grace = do_grace or ((not paid_up) and (not bounced) and days is not None and 0 <= days <= GRACE_DAYS)
    if bounced:
        label = f"D/O bounced · Due {due:.2f} · Suspension notice"
    elif paid_up:
        label = "Paid up"
        if collected:
            label = f"Paid up · D/O {pending.get('action_date')}"
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


def cards_for_export(
    conn: sqlite3.Connection | None,
    fibre_rows: list[dict] | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    fibre_rows = fibre_rows or []
    by_line: dict[str, list[dict]] = {}
    unmatched: list[dict] = []
    for row in fibre_rows:
        if is_incoming(row=row):
            continue
        key = canon_key(row.get("customer"))
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
        ]

    live_keys = {canon_key(c["name"]) for c in CLIENTS}
    used = set()
    cards = []
    cancelled = []
    for acc in accounts:
        key = canon_key(acc.get("name"))
        if key in used:
            continue
        used.add(key)
        line = _pick_line(by_line.get(key) or [])
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
            (line or {}).get("activated")
            or (line or {}).get("installed")
            or (line or {}).get("joined")
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
        fibre_b = (line or {}).get("service_number") if acc.get("access") == "fibre" else None
        card = {
            "name": acc.get("name"),
            "address": acc.get("address")
            or (line or {}).get("address")
            or (cust or {}).get("address")
            or hist.get("address"),
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
        "note": (
            "Simple client cards. Cancelled clients are not on this list — "
            "they sit in the Cancelled card at the bottom. "
            "VK Pop incoming fibre is not a client. "
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
        "customer": "Annette Bing HH",
        "line_status": "active",
        "access_status": "Fault",
        "partner_status": "IspActive",
        "address": "1 Test",
        "activated": "2024-01-01",
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
    pack = cards_for_export(None, [pop, hpp, broken, held, aljo, aman, johannes], today)
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
    elif by["Annette Bing HH"]["dot"] != "issue":
        print("FAIL bing-red", by["Annette Bing HH"])
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
    else:
        print("OK client-cards")
        print("OK cancelled-own-list")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
