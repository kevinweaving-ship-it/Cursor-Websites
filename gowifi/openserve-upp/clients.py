#!/usr/bin/env python3
"""Simple client cards for /dash/clients.html.

Incoming VK Pop fibre is not a client. Auto-suspend / WhatsApp / notes come later.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from billing import CLIENTS, canon_key, client_accounts
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


def _dot(we_suspended: bool, line: dict | None, access: str | None) -> tuple[str, str]:
    if we_suspended or (line and (line.get("line_status") or "").lower() == "suspended"):
        return "suspended", "Suspended"
    if access == "fibre" and _openserve_issue(line):
        return "issue", "Openserve issue"
    return "active", "Active"


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
        card.get("b_number"),
        card.get("package"),
        card.get("access"),
        card.get("pay"),
    ]
    return " ".join(str(b) for b in bits if b).lower()


def _package(acc: dict, line: dict | None) -> str | None:
    if acc.get("package"):
        return acc["package"]
    if line and (line.get("product") or line.get("speed")):
        return " · ".join(p for p in (line.get("product"), line.get("speed")) if p)
    if acc.get("access") == "wireless":
        amt = acc.get("billed") or acc.get("amount")
        return f"Wireless{f' R{amt:.0f}' if amt else ''}"
    return None


def _grace(acc: dict, today: date) -> dict:
    due = float(acc.get("due") or 0)
    paid_up = bool(acc.get("nil") or acc.get("status") == "paid-up")
    inv = _parse(acc.get("last_invoice_date"))
    days = (today - inv).days if inv else None
    in_grace = (not paid_up) and days is not None and 0 <= days <= GRACE_DAYS
    return {
        "grace_days": GRACE_DAYS,
        "in_grace": in_grace,
        "days_since_invoice": days,
        "balance_label": (
            "Paid up"
            if paid_up
            else (f"Grace · due {due:.2f}" if in_grace else f"Due {due:.2f}")
        ),
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

    used = set()
    cards = []
    for acc in accounts:
        key = canon_key(acc.get("name"))
        used.add(key)
        line = _pick_line(by_line.get(key) or [])
        hist = _invoice_profile(conn, acc.get("name") or "")
        started = (
            (line or {}).get("activated")
            or (line or {}).get("installed")
            or (line or {}).get("joined")
            or hist.get("first_invoice")
            or acc.get("started")
        )
        months = _months(_parse(started), today)
        we_suspended = bool(acc.get("suspended") or (line or {}).get("we_suspended"))
        dot, dot_label = _dot(we_suspended, line, acc.get("access"))
        grace = _grace(acc, today)
        due = acc.get("due")
        card = {
            "name": acc.get("name"),
            "address": acc.get("address") or (line or {}).get("address") or hist.get("address"),
            "phone": acc.get("phone") or (line or {}).get("phone"),
            "started": _parse(started).isoformat() if _parse(started) else None,
            "started_label": _day_label(started),
            "months": months,
            "tenure": _tenure(months),
            "b_number": (line or {}).get("service_number") if acc.get("access") == "fibre" else None,
            "package": _package(acc, line),
            "access": acc.get("access") or "wireless",
            "pay": acc.get("pay") or ("D/O" if acc.get("method") == "debit-order" else "EFT"),
            "discount": bool(acc.get("discount")),
            "billed": acc.get("billed"),
            "paid": acc.get("paid") or 0,
            "due": due,
            "paid_up": bool(acc.get("nil") or acc.get("status") == "paid-up"),
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
        card.update(grace)
        card["search"] = _haystack(card)
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
        dot, dot_label = _dot(we_suspended, line, "fibre")
        card = {
            "name": line.get("customer"),
            "address": line.get("address"),
            "phone": line.get("phone"),
            "started": _parse(started).isoformat() if _parse(started) else None,
            "started_label": _day_label(started),
            "months": months,
            "tenure": _tenure(months),
            "b_number": line.get("service_number"),
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
            "openserve_issue": _openserve_issue(line),
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
        card["search"] = _haystack(card)
        cards.append(card)

    cards.sort(key=lambda r: (r.get("name") or "").lower())
    return {
        "as_at": today.isoformat(),
        "grace_days": GRACE_DAYS,
        "count": len(cards),
        "active": sum(1 for c in cards if c["dot"] == "active"),
        "issue": sum(1 for c in cards if c["dot"] == "issue"),
        "suspended": sum(1 for c in cards if c["dot"] == "suspended"),
        "cards": cards,
        "note": (
            "Simple client cards. VK Pop incoming fibre is not a client. "
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
    pack = cards_for_export(None, [pop, hpp, broken, held], today)
    names = [c["name"] for c in pack["cards"]]
    by = {c["name"]: c for c in pack["cards"]}
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
    else:
        print("OK client-cards")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
