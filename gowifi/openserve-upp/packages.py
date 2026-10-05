#!/usr/bin/env python3
"""Current Openserve wholesale rentals (ex VAT).

Source: Makgosi Mabaso partner letters —
  • Pricing Updates effective 1 April 2026 (Table 2 postpaid, Table 4 prepaid)
  • 1Gbps FTTH from 1 July 2026 (OFC 1000 Lite R1 160 / OWS 1000 R1 275)

Each March/April, watch for the next Openserve increase and WhatsApp
a mailshot to clients before the 1 April change.
"""
from __future__ import annotations

import sqlite3
from datetime import date

VAT = 1.15
APRIL_2026 = date(2026, 4, 1)
GIGABIT_FROM = date(2026, 7, 1)
SOURCE = "Openserve partner letter 1 Apr 2026 / 1 Gbps 1 Jul 2026"

# Every year: look in March, mailshot before 1 April.
INCREASE_WATCH = {
    "months": (3, 4),
    "channel": "whatsapp",
    "headline": "Openserve increase watch",
    "note": (
        "Each March/April, check Openserve wholesale increases so we can "
        "WhatsApp a mailshot to clients before 1 April."
    ),
}

FAMILIES = {
    "OFC": "Fibre Connect",
    "OFC-LITE": "Fibre Connect Lite",
    "OWS": "Webstream",
    "OFCP": "Fibre Connect Premium",
    "OOC": "Office Connect",
    "OCC": "Copper Connect",
    "OPC": "Pure Connect",
    "OWC": "Web Connect",
    "OWCW": "Web Connect Wireless",
    "OWCP": "Prepaid Web Connect",
    "OWSP": "Prepaid Webstream",
}

# Table 1 (old) and Table 2 (current from 1 Apr 2026). Amounts ex VAT.
# Blank cells in the letter are omitted.
POSTPAID = [
    # down, up, product, pre, current
    (5, 1, "OCC", 220, 240),
    (5, 1, "OPC", 220, 240),
    (10, 1, "OCC", 300, 330),
    (10, 1, "OPC", 300, 330),
    (10, 1, "OWC", 210, 215),
    (10, 5, "OFC", 220, 235),
    (10, 5, "OWS", 245, 260),
    (20, 2, "OCC", 430, 475),
    (20, 2, "OPC", 430, 475),
    (20, 10, "OWC", 240, 249),
    (20, 10, "OWCW", 240, 249),
    (25, 25, "OWS", 350, 370),
    (30, 10, "OWCW", 285, 295),
    (30, 30, "OFC", 325, 345),
    (40, 2, "OCC", 480, 530),
    (40, 2, "OPC", 480, 530),
    (40, 20, "OWC", 285, 295),
    (50, 25, "OFC", 475, 505),
    (50, 25, "OWS", 500, 530),
    (50, 50, "OFC", 530, 560),
    (50, 50, "OFCP", 630, 670),
    (50, 50, "OOC", 700, 740),
    (100, 50, "OFC", 575, 610),
    (100, 50, "OWS", 610, 650),
    (100, 100, "OFC", 630, 670),
    (100, 100, "OFCP", 720, 765),
    (100, 100, "OOC", 820, 870),
    (200, 100, "OFC", 730, 775),
    (200, 100, "OWS", 775, 820),
    (200, 200, "OFC", 775, 820),
    (200, 200, "OFCP", 915, 970),
    (200, 200, "OOC", 1065, 1130),
    (300, 150, "OFC", 830, 880),
    (300, 150, "OWS", 885, 940),
    (300, 150, "OFCP", 1020, 1080),
    (300, 150, "OOC", 1270, 1345),
    (500, 250, "OFC", 930, 990),
    (500, 250, "OWS", 1015, 1075),
    (500, 250, "OFCP", 1210, 1285),
    (500, 250, "OOC", 1710, 1815),
]

GIGABIT = [
    (1000, 500, "OFC-LITE", None, 1160.00, "OFC 1000Mbps Lite"),
    (1000, 500, "OWS", None, 1275.00, "OWS 1000Mbps"),
]

PREPAID = [
    {"product": "OWCP", "down": 20, "up": None, "install": 155.00, "d3": 42.00, "d7": 75.00, "d14": 140.00, "d30": 260.00},
    {"product": "OWSP", "down": 25, "up": None, "install": None, "d3": 65.00, "d7": 110.00, "d14": 200.00, "d30": 390.00},
    {"product": "OWSP", "down": 50, "up": None, "install": 370.00, "d3": 85.00, "d7": 160.00, "d14": 285.00, "d30": 550.00},
]

# GoWiFi sell (incl VAT) for speeds we actually invoice. Phillip De Gruchy
# 1219 on OWS300 is a client discount, not the list.
SELL = {
    "OWS-25-25": 429.00,  # Bing HH; HPP EFT 599
    "OWS-50-25": 759.00,
    "OWS-100-50": 999.00,
}

EXTRAS = [
    {"code": "new-install", "label": "New install", "amount": 0.00, "on_monthly_do": False, "kind": "once-off",
     "note": "Openserve Connect first install is usually free."},
    {"code": "activation", "label": "Service activation", "amount": 575.00, "on_monthly_do": False, "kind": "once-off",
     "note": "Openserve activation when an ONT is already on site."},
    {"code": "equipment", "label": "Equipment / router", "amount": 650.00, "on_monthly_do": False, "kind": "once-off",
     "note": "Client-owned router or extra AP. Not the monthly line."},
    {"code": "addon", "label": "Add-on", "amount": None, "on_monthly_do": False, "kind": "once-off",
     "note": "Static IP, extra AP. Invoice separately."},
    {"code": "reconnect", "label": "Reconnection", "amount": 250.00, "on_monthly_do": False, "kind": "once-off",
     "note": "Restore after a credit suspend. Not a new install."},
]

WHOLESALE_SCHEMA = """
CREATE TABLE IF NOT EXISTS openserve_wholesale (
    sku TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    family TEXT,
    down INTEGER,
    up INTEGER,
    speed TEXT,
    cost_ex_vat REAL,
    cost_incl_vat REAL,
    cost_pre_april REAL,
    increase REAL,
    effective_from TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT,
    install REAL,
    recharge_3 REAL,
    recharge_7 REAL,
    recharge_14 REAL,
    recharge_30 REAL
);
"""


def sku_for(product: str, down: int | None, up: int | None = None) -> str:
    if up:
        return f"{product}-{down}-{up}"
    return f"{product}-{down}"


def _money(ex: float | None) -> tuple[float | None, float | None]:
    if ex is None:
        return None, None
    return float(ex), round(float(ex) * VAT, 2)


def wholesale_rows(as_at: date | None = None) -> list[dict]:
    """Current Openserve wholesale card as a flat table."""
    as_at = as_at or date.today()
    rows = []
    for down, up, product, pre, current in POSTPAID:
        ex, incl = _money(current)
        pre_ex = float(pre) if pre is not None else None
        rows.append(
            {
                "sku": sku_for(product, down, up),
                "product": product,
                "family": FAMILIES.get(product, product),
                "down": down,
                "up": up,
                "speed": f"{down}/{up}",
                "cost_ex_vat": ex,
                "cost_incl_vat": incl,
                "cost_pre_april": pre_ex,
                "increase": round(ex - pre_ex, 2) if ex is not None and pre_ex is not None else None,
                "effective_from": APRIL_2026.isoformat(),
                "kind": "postpaid",
                "source": SOURCE,
                "sell": SELL.get(sku_for(product, down, up)),
                "label": f"{FAMILIES.get(product, product)} {down}/{up}",
            }
        )
    for down, up, product, pre, current, label in GIGABIT:
        live = as_at >= GIGABIT_FROM
        ex, incl = _money(current if live else None)
        rows.append(
            {
                "sku": sku_for(product, down, up),
                "product": product,
                "family": FAMILIES.get(product, product),
                "down": down,
                "up": up,
                "speed": f"{down}/{up}",
                "cost_ex_vat": ex,
                "cost_incl_vat": incl,
                "cost_pre_april": pre,
                "increase": None,
                "effective_from": GIGABIT_FROM.isoformat(),
                "kind": "gigabit",
                "source": SOURCE,
                "sell": None,
                "label": label,
                "available_from": GIGABIT_FROM.isoformat(),
            }
        )
    for item in PREPAID:
        rows.append(
            {
                "sku": sku_for(item["product"], item["down"]),
                "product": item["product"],
                "family": FAMILIES.get(item["product"], item["product"]),
                "down": item["down"],
                "up": item["up"],
                "speed": f"{item['down']}",
                "cost_ex_vat": item["d30"],
                "cost_incl_vat": round(item["d30"] * VAT, 2),
                "cost_pre_april": None,
                "increase": None,
                "effective_from": APRIL_2026.isoformat(),
                "kind": "prepaid",
                "source": SOURCE,
                "sell": None,
                "label": f"{FAMILIES.get(item['product'])} {item['down']} prepaid",
                "install": item["install"],
                "recharge_3": item["d3"],
                "recharge_7": item["d7"],
                "recharge_14": item["d14"],
                "recharge_30": item["d30"],
            }
        )
    rows.sort(key=lambda r: (0 if r["kind"] == "postpaid" else 1 if r["kind"] == "gigabit" else 2, r["down"] or 0, r["up"] or 0, r["product"]))
    return rows


def current_table(as_at: date | None = None) -> list[dict]:
    """Postpaid + gigabit current rentals only (the price table)."""
    return [r for r in wholesale_rows(as_at) if r["kind"] in {"postpaid", "gigabit"}]


def webstream(as_at: date | None = None) -> list[dict]:
    return [r for r in current_table(as_at) if r["product"] == "OWS"]


def office_connect(as_at: date | None = None) -> list[dict]:
    return [r for r in current_table(as_at) if r["product"] == "OOC"]


def fibre_connect(as_at: date | None = None) -> list[dict]:
    return [r for r in current_table(as_at) if r["product"] in {"OFC", "OFC-LITE", "OFCP"}]


def by_sku(sku: str | None, as_at: date | None = None) -> dict | None:
    if not sku:
        return None
    key = sku.strip().upper()
    aliases = {
        "OWS25M": "OWS-25-25",
        "OWS50M": "OWS-50-25",
        "OWS100M": "OWS-100-50",
        "OWS200M": "OWS-200-100",
        "OWS300M": "OWS-300-150",
        "OWS500M": "OWS-500-250",
        "OWS1000M": "OWS-1000-500",
        "OOCF50M": "OOC-50-50",
        "OOCF100M": "OOC-100-100",
        "OOCF200M": "OOC-200-200",
        "OOCF300M": "OOC-300-150",
        "OOCF500M": "OOC-500-250",
        "OFC1000M": "OFC-LITE-1000-500",
    }
    want = aliases.get(sku.strip().upper(), key)
    for row in wholesale_rows(as_at):
        if row["sku"] == want or row["sku"] == sku.strip().upper():
            return row
    return None


def extras() -> list[dict]:
    return [dict(row) for row in EXTRAS]


def increase_watch(as_at: date | None = None) -> dict:
    as_at = as_at or date.today()
    due = as_at.month in INCREASE_WATCH["months"]
    year = as_at.year if as_at.month >= 3 else as_at.year
    return {
        **INCREASE_WATCH,
        "due": due,
        "for_year": year,
        "effective": f"{year}-04-01",
        "action": (
            "Check the Openserve partner letter, update this wholesale table, "
            "then WhatsApp a mailshot to clients of the increase."
        ),
    }


def all_packages(as_at: date | None = None) -> list[dict]:
    return webstream(as_at) + office_connect(as_at)


def ensure_wholesale(conn: sqlite3.Connection, as_at: date | None = None) -> int:
    """Replace the current wholesale table in SQLite."""
    conn.executescript(WHOLESALE_SCHEMA)
    conn.execute("DELETE FROM openserve_wholesale")
    n = 0
    for row in wholesale_rows(as_at):
        conn.execute(
            """INSERT INTO openserve_wholesale
               (sku, product, family, down, up, speed, cost_ex_vat, cost_incl_vat,
                cost_pre_april, increase, effective_from, kind, source,
                install, recharge_3, recharge_7, recharge_14, recharge_30)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["sku"],
                row["product"],
                row["family"],
                row.get("down"),
                row.get("up"),
                row.get("speed"),
                row.get("cost_ex_vat"),
                row.get("cost_incl_vat"),
                row.get("cost_pre_april"),
                row.get("increase"),
                row["effective_from"],
                row["kind"],
                row.get("source"),
                row.get("install"),
                row.get("recharge_3"),
                row.get("recharge_7"),
                row.get("recharge_14"),
                row.get("recharge_30"),
            ),
        )
        n += 1
    conn.commit()
    return n


def overlay_invoice_costs(conn: sqlite3.Connection, rows: list[dict] | None = None) -> list[dict]:
    """Keep official card; only stamp when an invoice rental matches a SKU."""
    rows = [dict(r) for r in (rows or current_table())]
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
        code = "OWS" if "WEBSTREAM" in blob else "OOC" if "OFFICE" in blob else "OFC" if "FIBRE CONNECT" in blob else None
        cap = "".join(ch for ch in str(capacity or "") if ch.isdigit())
        if code and cap:
            latest[(code, cap)] = (float(amount), inv_date or "")
    for row in rows:
        hit = latest.get((row["product"] if row["product"] != "OFC-LITE" else "OFC", str(row["down"])))
        if not hit:
            continue
        amount, inv_date = hit
        row["invoice_ex_vat"] = amount
        row["invoice_date"] = inv_date
    return rows


def for_export(conn: sqlite3.Connection | None = None, as_at: date | None = None) -> dict:
    as_at = as_at or date.today()
    if conn is not None:
        ensure_wholesale(conn, as_at)
    rows = wholesale_rows(as_at)
    if conn is not None:
        rows = overlay_invoice_costs(conn, rows)
    watch = increase_watch(as_at)
    return {
        "as_at": as_at.isoformat(),
        "effective": APRIL_2026.isoformat(),
        "gigabit_from": GIGABIT_FROM.isoformat(),
        "source": SOURCE,
        "currency": "ZAR ex VAT",
        "note": (
            "Current Openserve wholesale (ex VAT) from the 1 April 2026 partner letter. "
            "Gigabit from 1 July 2026: OFC 1000 Lite R1 160, OWS 1000 R1 275. "
            "Each March/April watch for the next increase and WhatsApp clients."
        ),
        "increase_watch": watch,
        "table": [r for r in rows if r["kind"] in {"postpaid", "gigabit"}],
        "webstream": [r for r in rows if r["product"] == "OWS"],
        "office_connect": [r for r in rows if r["product"] == "OOC"],
        "fibre_connect": [r for r in rows if r["product"] in {"OFC", "OFC-LITE", "OFCP"}],
        "prepaid": [r for r in rows if r["kind"] == "prepaid"],
        "extras": extras(),
        "vat": VAT,
        "count": sum(1 for r in rows if r["kind"] in {"postpaid", "gigabit"}),
    }


def self_test() -> int:
    failed = 0
    table = current_table(date(2026, 10, 5))
    ows50 = by_sku("OWS50M", date(2026, 4, 1))
    if not ows50 or ows50["cost_ex_vat"] != 530 or ows50["cost_pre_april"] != 500:
        print("FAIL ows50-official", ows50)
        failed += 1
    else:
        print("OK ows50-official-530")
    ows25 = by_sku("OWS25M", date(2026, 10, 5))
    ows300 = by_sku("OWS300M", date(2026, 10, 5))
    ooc500 = by_sku("OOCF500M", date(2026, 10, 5))
    ooc300 = by_sku("OOCF300M", date(2026, 10, 5))
    if not ows25 or ows25["cost_ex_vat"] != 370:
        print("FAIL ows25", ows25)
        failed += 1
    elif not ows300 or ows300["cost_ex_vat"] != 940:
        print("FAIL ows300", ows300)
        failed += 1
    elif not ooc500 or ooc500["cost_ex_vat"] != 1815 or ooc500["cost_pre_april"] != 1710:
        print("FAIL ooc500", ooc500)
        failed += 1
    elif not ooc300 or ooc300["cost_ex_vat"] != 1345:
        print("FAIL ooc300-sep-fnb", ooc300)
        failed += 1
    else:
        print("OK official-ows-ooc")
    gig_ows = by_sku("OWS1000M", date(2026, 7, 1))
    gig_ofc = by_sku("OFC1000M", date(2026, 7, 1))
    gig_jun = by_sku("OWS1000M", date(2026, 6, 30))
    if not gig_ows or gig_ows["cost_ex_vat"] != 1275:
        print("FAIL ows-gig-1275", gig_ows)
        failed += 1
    elif not gig_ofc or gig_ofc["cost_ex_vat"] != 1160:
        print("FAIL ofc-lite-1160", gig_ofc)
        failed += 1
    elif gig_jun and gig_jun["cost_ex_vat"] is not None:
        print("FAIL gig-before-july", gig_jun)
        failed += 1
    else:
        print("OK gigabit-ows-1275-ofc-1160")
    products = {r["product"] for r in table if r["kind"] == "postpaid"}
    want = {"OFC", "OWS", "OFCP", "OOC", "OCC", "OPC", "OWC", "OWCW"}
    if not want <= products:
        print("FAIL all-products", products)
        failed += 1
    elif len(table) < 40:
        print("FAIL table-short", len(table))
        failed += 1
    else:
        print("OK wholesale-table", len(table))
    watch_mar = increase_watch(date(2026, 3, 15))
    watch_oct = increase_watch(date(2026, 10, 5))
    if not watch_mar["due"] or watch_mar["channel"] != "whatsapp":
        print("FAIL watch-mar", watch_mar)
        failed += 1
    elif watch_oct["due"]:
        print("FAIL watch-oct", watch_oct)
        failed += 1
    else:
        print("OK increase-watch-mar-apr-whatsapp")
    conn = sqlite3.connect(":memory:")
    n = ensure_wholesale(conn, date(2026, 10, 5))
    stored = conn.execute("SELECT COUNT(*), SUM(cost_ex_vat) FROM openserve_wholesale WHERE kind='postpaid'").fetchone()
    if n < 40 or not stored or stored[0] < 35:
        print("FAIL store", n, stored)
        failed += 1
    else:
        print("OK stored-in-sqlite", stored[0])
    conn.close()
    if any(x["on_monthly_do"] for x in extras()):
        print("FAIL extras-on-do")
        failed += 1
    else:
        print("OK extras-not-on-monthly-do")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
