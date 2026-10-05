#!/usr/bin/env python3
"""GoWiFi fibre rate card: Openserve Webstream + Office Connect.

Openserve raised the mid-to-top uncapped home-fibre wholesale card on
1 April 2026 (+R20 to +R60). Gigabit Webstream 1000/500 is available to
ISPs from 1 July 2026. Office Connect stays 50–500 Mbps (no gigabit).

Two numbers per speed:
  cost_ex_vat  — what Openserve bills GoWiFi (ex VAT)
  sell         — what GoWiFi bills the client (incl VAT)

Invoice CSVs on the box only run to January 2026. Later INATS files
should overlay cost_ex_vat via overlay_invoice_costs().
"""
from __future__ import annotations

import sqlite3
from datetime import date

VAT = 1.15
APRIL_2026 = date(2026, 4, 1)
GIGABIT_FROM = date(2026, 7, 1)

# Last rental Openserve billed us (ex VAT) from imported invoice_lines.
COST_PRE_APRIL = {
    "OWS25M": 350.00,
    "OWS50M": 500.00,
    "OWS200M": 775.00,
    "OWS500M": 1015.00,
    "OOCF500M": 1710.00,
}

# Published 1 April 2026 wholesale card (incl VAT) for uncapped home fibre.
# Source: Openserve partner rate-card notices republished by ISPs.
PUBLISHED_APRIL = [
    {"down": 50, "up": 25, "old_incl": 799.00, "new_incl": 819.00, "increase": 20.00},
    {"down": 50, "up": 50, "old_incl": 849.00, "new_incl": 869.00, "increase": 20.00},
    {"down": 100, "up": 50, "old_incl": 939.00, "new_incl": 969.00, "increase": 30.00},
    {"down": 100, "up": 100, "old_incl": 1029.00, "new_incl": 1059.00, "increase": 30.00},
    {"down": 200, "up": 100, "old_incl": 1149.00, "new_incl": 1189.00, "increase": 40.00},
    {"down": 200, "up": 200, "old_incl": 1249.00, "new_incl": 1289.00, "increase": 40.00},
    {"down": 300, "up": 150, "old_incl": 1349.00, "new_incl": 1399.00, "increase": 50.00},
    {"down": 500, "up": 250, "old_incl": 1499.00, "new_incl": 1559.00, "increase": 60.00},
]

# Gigabit Webstream / Fibre Connect Lite — ISP wholesale from 1 Jul 2026.
GIGABIT_COST_EX = 1160.00

# GoWiFi sell (incl VAT) from the live 17th invoices / D/O / EFT book.
SELL = {
    "OWS25M": 429.00,  # Bing HH debit; HPP Control Room pays 599 EFT
    "OWS50M": 759.00,  # Cupido, Neethling, Bryant, Murray
    "OWS100M": 999.00,  # Lategan EFT
    "OWS300M": 1219.00,  # De Gruchy (UPP OWS300M; Netcash ref says 200)
}

# Once-off invoice choices. Never loaded on the monthly debit order.
EXTRAS = [
    {
        "code": "new-install",
        "label": "New install",
        "amount": 0.00,
        "note": "Openserve Connect first install is usually free. Charge only if we do the work or recover a truck roll.",
        "on_monthly_do": False,
        "kind": "once-off",
    },
    {
        "code": "activation",
        "label": "Service activation",
        "amount": 575.00,
        "note": "Openserve activation when an ONT is already on site or the client migrates ISP.",
        "on_monthly_do": False,
        "kind": "once-off",
    },
    {
        "code": "equipment",
        "label": "Equipment / router",
        "amount": 650.00,
        "note": "Client-owned router or extra AP. Not the monthly line.",
        "on_monthly_do": False,
        "kind": "once-off",
    },
    {
        "code": "addon",
        "label": "Add-on",
        "amount": None,
        "note": "Static IP, extra AP, extra month of a once-off product. Invoice separately.",
        "on_monthly_do": False,
        "kind": "once-off",
    },
    {
        "code": "reconnect",
        "label": "Reconnection",
        "amount": 250.00,
        "note": "Restore after a credit suspend. Not a new install.",
        "on_monthly_do": False,
        "kind": "once-off",
    },
]


def _published(down: int, up: int) -> dict | None:
    for row in PUBLISHED_APRIL:
        if row["down"] == down and row["up"] == up:
            return row
    return None


def _increase(down: int, up: int) -> float:
    pub = _published(down, up)
    if pub:
        return pub["increase"]
    if down >= 500:
        return 60.00
    if down >= 300:
        return 50.00
    if down >= 200:
        return 40.00
    if down >= 100:
        return 30.00
    return 20.00


def _cost(sku: str, down: int, up: int, as_at: date, family: str) -> dict:
    pre = COST_PRE_APRIL.get(sku)
    inc = _increase(down, up)
    pub = _published(down, up)
    if sku in {"OWS1000M", "OWS1G"}:
        available = as_at >= GIGABIT_FROM
        return {
            "cost_ex_vat": GIGABIT_COST_EX if available else None,
            "cost_incl_vat": round(GIGABIT_COST_EX * VAT, 2) if available else None,
            "cost_pre_april": None,
            "cost_source": "Telecompaper / Openserve ISP notice 1 Jul 2026" if available else "not launched",
            "available_from": GIGABIT_FROM.isoformat(),
        }
    if as_at < APRIL_2026:
        cost = pre
        source = "Openserve invoice rental (pre-April 2026)"
    elif pre is not None:
        cost = round(pre + inc, 2)
        source = f"Jan invoice {pre:.0f} + April +{inc:.0f}"
    elif pub:
        cost = round(pub["new_incl"] / VAT, 2)
        source = "April 2026 published card ÷ 1.15 (no invoice yet)"
    else:
        cost = None
        source = "awaiting Openserve invoice"
    return {
        "cost_ex_vat": cost,
        "cost_incl_vat": round(cost * VAT, 2) if cost is not None else None,
        "cost_pre_april": pre,
        "cost_source": source,
        "available_from": None,
    }


def _row(
    family: str,
    sku: str,
    down: int,
    up: int,
    *,
    sell: float | None = None,
    as_at: date | None = None,
) -> dict:
    as_at = as_at or date.today()
    pub = _published(down, up)
    money = _cost(sku, down, up, as_at, family)
    sell_amt = SELL.get(sku) if sell is None else sell
    cost_incl = money["cost_incl_vat"]
    margin = (
        round(sell_amt - cost_incl, 2)
        if sell_amt is not None and cost_incl is not None
        else None
    )
    return {
        "family": family,
        "sku": sku,
        "down": down,
        "up": up,
        "speed": f"{down}/{up}",
        "label": f"{'Webstream' if family == 'webstream' else 'Office Connect'} {down}/{up}",
        "sell": sell_amt,
        "published_old_incl": pub["old_incl"] if pub else None,
        "published_new_incl": pub["new_incl"] if pub else None,
        "published_increase": pub["increase"] if pub else None,
        "margin": margin,
        **money,
    }


def webstream(as_at: date | None = None) -> list[dict]:
    """All Webstream packages we can sell, 25 Mbps through gigabit."""
    as_at = as_at or date.today()
    rows = [
        _row("webstream", "OWS25M", 25, 25, as_at=as_at),
        _row("webstream", "OWS50M", 50, 25, as_at=as_at),
        _row("webstream", "OWS50S", 50, 50, as_at=as_at),
        _row("webstream", "OWS100M", 100, 50, as_at=as_at),
        _row("webstream", "OWS100S", 100, 100, as_at=as_at),
        _row("webstream", "OWS200M", 200, 100, as_at=as_at),
        _row("webstream", "OWS200S", 200, 200, as_at=as_at),
        _row("webstream", "OWS300M", 300, 150, as_at=as_at),
        _row("webstream", "OWS500M", 500, 250, as_at=as_at),
        _row("webstream", "OWS1000M", 1000, 500, as_at=as_at),
    ]
    return rows


def office_connect(as_at: date | None = None) -> list[dict]:
    """Office Connect 50–500. Openserve does not offer an OOC gigabit tier."""
    as_at = as_at or date.today()
    return [
        _row("office-connect", "OOCF50M", 50, 50, as_at=as_at),
        _row("office-connect", "OOCF100M", 100, 100, as_at=as_at),
        _row("office-connect", "OOCF200M", 200, 200, as_at=as_at),
        _row("office-connect", "OOCF300M", 300, 150, as_at=as_at),
        _row("office-connect", "OOCF500M", 500, 250, as_at=as_at),
    ]


def all_packages(as_at: date | None = None) -> list[dict]:
    return webstream(as_at) + office_connect(as_at)


def by_sku(sku: str | None, as_at: date | None = None) -> dict | None:
    if not sku:
        return None
    key = sku.strip().upper()
    for row in all_packages(as_at):
        if row["sku"] == key:
            return row
    return None


def extras() -> list[dict]:
    return [dict(row) for row in EXTRAS]


def overlay_invoice_costs(conn: sqlite3.Connection, rows: list[dict] | None = None) -> list[dict]:
    """Replace estimated cost with the latest rental on invoice_lines when present."""
    rows = [dict(r) for r in (rows or all_packages())]
    try:
        billed = conn.execute(
            """SELECT product, capacity, charge_amount, invoice_date
               FROM invoice_lines il
               JOIN invoices i ON i.invoice_number = il.invoice_number
               WHERE extra_kind='rental' AND charge_amount > 0
               ORDER BY invoice_date"""
        ).fetchall()
    except sqlite3.OperationalError:
        return rows
    latest: dict[tuple[str, str], tuple[float, str]] = {}
    for product, capacity, amount, inv_date in billed:
        blob = f"{product or ''} {capacity or ''}".upper()
        family = "webstream" if "WEBSTREAM" in blob else "office-connect" if "OFFICE" in blob else None
        if not family:
            continue
        cap = "".join(ch for ch in str(capacity or "") if ch.isdigit())
        if not cap:
            continue
        latest[(family, cap)] = (float(amount), inv_date or "")
    for row in rows:
        hit = latest.get((row["family"], str(row["down"])))
        if not hit:
            continue
        amount, inv_date = hit
        row["cost_ex_vat"] = amount
        row["cost_incl_vat"] = round(amount * VAT, 2)
        row["cost_source"] = f"Openserve invoice {inv_date}"
        if row.get("sell") is not None:
            row["margin"] = round(row["sell"] - row["cost_incl_vat"], 2)
    return rows


def for_export(conn: sqlite3.Connection | None = None, as_at: date | None = None) -> dict:
    as_at = as_at or date.today()
    rows = all_packages(as_at)
    if conn is not None:
        rows = overlay_invoice_costs(conn, rows)
    return {
        "as_at": as_at.isoformat(),
        "effective": APRIL_2026.isoformat(),
        "gigabit_from": GIGABIT_FROM.isoformat(),
        "note": (
            "Openserve Webstream and Office Connect went up 1 April 2026. "
            "Webstream now runs 25 Mbps through gigabit (1000/500 from 1 July). "
            "Office Connect stays 50–500. Monthly D/O is the line rental only — "
            "install, equipment, add-ons and reconnection are once-off invoices."
        ),
        "webstream": [r for r in rows if r["family"] == "webstream"],
        "office_connect": [r for r in rows if r["family"] == "office-connect"],
        "extras": extras(),
        "vat": VAT,
    }


def self_test() -> int:
    failed = 0
    before = by_sku("OWS50M", date(2026, 3, 31))
    after = by_sku("OWS50M", date(2026, 4, 1))
    if not before or before["cost_ex_vat"] != 500:
        print("FAIL ws50-pre", before)
        failed += 1
    elif not after or after["cost_ex_vat"] != 520:
        print("FAIL ws50-apr", after)
        failed += 1
    else:
        print("OK webstream-50-april")
    gig_jun = by_sku("OWS1000M", date(2026, 6, 30))
    gig_jul = by_sku("OWS1000M", date(2026, 7, 1))
    if gig_jun and gig_jun["cost_ex_vat"] is not None:
        print("FAIL gig-before-july", gig_jun)
        failed += 1
    elif not gig_jul or gig_jul["cost_ex_vat"] != 1160:
        print("FAIL gig-july", gig_jul)
        failed += 1
    else:
        print("OK webstream-gigabit-july")
    ooc = office_connect(date(2026, 10, 5))
    if [r["speed"] for r in ooc] != ["50/50", "100/100", "200/200", "300/150", "500/250"]:
        print("FAIL ooc-ladder", ooc)
        failed += 1
    elif any(r["down"] >= 1000 for r in ooc):
        print("FAIL ooc-no-gigabit", ooc)
        failed += 1
    elif ooc[-1]["cost_pre_april"] != 1710:
        print("FAIL ooc500-invoice", ooc[-1])
        failed += 1
    else:
        print("OK office-connect-50-to-500")
    ws = webstream(date(2026, 10, 5))
    if ws[0]["down"] != 25 or ws[-1]["down"] != 1000:
        print("FAIL ws-span", [r["speed"] for r in ws])
        failed += 1
    elif by_sku("OWS300M")["sell"] != 1219 or by_sku("OWS50M")["sell"] != 759:
        print("FAIL sell", by_sku("OWS300M"), by_sku("OWS50M"))
        failed += 1
    else:
        print("OK webstream-25-to-gigabit")
    if any(x["on_monthly_do"] for x in extras()):
        print("FAIL extras-on-do", extras())
        failed += 1
    else:
        print("OK extras-not-on-monthly-do")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
