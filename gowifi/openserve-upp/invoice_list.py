#!/usr/bin/env python3
"""QuickBooks invoice list: monthly line rental vs query for full invoice.

Repeating mid-month amounts that match a known client rate are monthly
line rental (wireless or fibre). Odd / once-off amounts are queries —
Kevin needs to send the full invoice PDF so we can split install /
equipment / fees. Do not invent line items.

5 Oct 2026 D/O is authorised, not collected. QB open is historical.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from billing import CLIENTS, canon_key, client_row, display_name
from customers import lookup as customer_lookup

DATA_DIR = Path(__file__).resolve().parent / "data"
INVOICES_JSON = DATA_DIR / "qb_invoices.json"

# Historical + current monthly line-rental amounts we already know.
KNOWN_MONTHLY = {
    "david wantling": (399.0, 439.0),
    "dirk de": (399.0,),
    "annette bing": (399.0, 429.0, 439.0),
    "stan hundermark": (299.0, 329.0),
    "phillip de": (999.0, 1219.0),
    "jean de": (550.0,),
    "havenga": (699.0,),
    "hermanus builders": (669.0, 699.0, 759.0),
    "geocorp": (699.0, 759.0),
    "bryant michael": (699.0, 759.0),
    "bing noordhoek": (599.0,),
    "g cupido": (759.0,),
    "gordon neethling": (759.0,),
    "lategan": (898.0, 999.0),
    "hpp control": (549.0, 599.0),
    "pearson philippa": (299.0, 329.0),
    "phillipus may": (399.0, 439.0),
    "amoroc doors": (199.0,),
    "wcc tech": (1000.0,),
    "paltco": (1399.0,),
    "marlene georg": (399.0, 439.0),
    "murray dh": (699.0, 759.0),
    "irene steyn": (599.0, 600.0),
    "terence pereira": (500.0,),
    "james such": (500.0,),
    "geran sukhraj": (300.0,),
    "aljo van": (699.0,),
}

ASK = "Need full invoice PDF — split install / equipment / fees"
MONTHLY_WHAT = {
    "fibre": "Fibre line rental (month in advance)",
    "wireless": "Wireless line rental (month in advance)",
    "offset": "Offset · Kevin loan (not a client)",
}


def _money(value) -> float:
    return round(float(value or 0), 2)


def _load() -> dict:
    if not INVOICES_JSON.exists():
        return {"rows": [], "count": 0, "billed": 0, "qb_open": 0}
    return json.loads(INVOICES_JSON.read_text())


def invoices() -> list[dict]:
    return [dict(r) for r in (_load().get("rows") or [])]


def _rates_for(key: str) -> set[float]:
    rates = set(KNOWN_MONTHLY.get(key) or ())
    row = client_row(key)
    if row and row.get("amount"):
        rates.add(_money(row["amount"]))
    return {_money(x) for x in rates}


def _closed(name: str) -> bool:
    return "deleted" in (name or "").lower()


def _classify_amount(key: str, amount: float, count: int, counts: Counter) -> str:
    amount = _money(amount)
    known = _rates_for(key)
    if amount in known:
        return "monthly"
    if count >= 3:
        return "monthly"
    # R1 rounding next to a known monthly (Pearson 300, Marlene 400).
    if count == 1 and any(abs(amount - rate) <= 1.0 for rate in known):
        return "monthly"
    if count >= 2 and amount == max(counts, key=lambda a: (counts[a], -a)):
        return "monthly"
    return "query"


def _why(inv: dict, kind: str, monthly_now: float | None, count: int) -> str:
    if kind == "monthly":
        what = MONTHLY_WHAT.get((client_row(inv["name"]) or {}).get("access") or "", "Monthly line rental")
        return f"{what} · R{_money(inv['amount']):.2f}"
    memo = (inv.get("memo") or "").strip()
    if "install" in memo.lower():
        return f"Memo says install — {ASK}"
    if count == 1 and monthly_now:
        return f"Once-off R{_money(inv['amount']):.2f} — not the monthly rental (R{monthly_now:.2f}). {ASK}"
    if count == 1:
        return f"Only invoice / odd amount R{_money(inv['amount']):.2f}. {ASK}"
    return f"Amount R{_money(inv['amount']):.2f} is not the known monthly rental. {ASK}"


def classify(as_at: date | None = None) -> dict:
    as_at = as_at or date(2026, 10, 5)
    pack = _load()
    rows = invoices()
    by_name: dict[str, list[dict]] = defaultdict(list)
    for inv in rows:
        by_name[inv.get("name") or ""].append(inv)

    monthly_rows = []
    query_rows = []
    clients_out = []

    for qb_name, items in sorted(by_name.items(), key=lambda kv: kv[0].lower()):
        key = canon_key(qb_name)
        book = client_row(qb_name)
        cust = customer_lookup(qb_name)
        counts = Counter(_money(i["amount"]) for i in items)
        monthly_now = _money(book["amount"]) if book else None
        if monthly_now is None:
            known = _rates_for(key)
            if known:
                monthly_now = max(known)
        access = (book or {}).get("access")
        pay = None
        if book:
            pay = "D/O" if book.get("method") == "debit-order" else "EFT"
        display = display_name(qb_name) if book else (qb_name or "").strip()
        if _closed(qb_name):
            display = qb_name
        m_n = q_n = 0
        history = sorted({_money(a) for a, n in counts.items() if _classify_amount(key, a, n, counts) == "monthly"})
        for inv in sorted(items, key=lambda r: (r.get("date") or "", r.get("number") or "")):
            amount = _money(inv["amount"])
            kind = _classify_amount(key, amount, counts[amount], counts)
            rec = {
                "number": str(inv.get("number") or ""),
                "date": inv.get("date"),
                "name": display,
                "qb_name": qb_name,
                "amount": amount,
                "open": _money(inv.get("open")),
                "memo": inv.get("memo") or "",
                "kind": kind,
                "access": access,
                "pay": pay,
                "monthly_now": monthly_now,
                "closed": _closed(qb_name),
                "why": _why(inv, kind, monthly_now, counts[amount]),
            }
            if kind == "query":
                rec["ask"] = ASK
                rec["lines"] = []
                q_n += 1
                query_rows.append(rec)
            else:
                rec["what"] = MONTHLY_WHAT.get(access or "", "Monthly line rental")
                m_n += 1
                monthly_rows.append(rec)
        clients_out.append(
            {
                "name": display,
                "qb_name": qb_name,
                "access": access,
                "pay": pay,
                "discount": bool((book or {}).get("discount")),
                "monthly": monthly_now,
                "history": history,
                "invoices": len(items),
                "monthly_count": m_n,
                "query_count": q_n,
                "first": min((i.get("date") or "") for i in items),
                "last": max((i.get("date") or "") for i in items),
                "billed": round(sum(_money(i["amount"]) for i in items), 2),
                "qb_open": round(sum(_money(i.get("open")) for i in items), 2),
                "address": (cust or {}).get("address"),
                "phone": (cust or {}).get("phone"),
                "email": (cust or {}).get("email"),
                "b_number": (cust or {}).get("b_number") or (book or {}).get("b_number"),
                "closed": _closed(qb_name),
                "what": MONTHLY_WHAT.get(access or "", None),
            }
        )

    query_rows.sort(key=lambda r: (r.get("date") or "", r.get("number") or ""))
    monthly_rows.sort(key=lambda r: (r.get("date") or "", r.get("number") or ""))
    return {
        "as_at": as_at.isoformat(),
        "source": pack.get("source") or "GoWifi (Pty) Ltd_Invoice List by Date.xlsx",
        "range": pack.get("range"),
        "count": len(rows),
        "monthly_count": len(monthly_rows),
        "query_count": len(query_rows),
        "billed": pack.get("billed") or round(sum(_money(r["amount"]) for r in rows), 2),
        "qb_open": pack.get("qb_open") or 0,
        "ask": ASK,
        "note": (
            "Repeating mid-month amounts are monthly line rental. "
            "Odd amounts are queries — send the full invoice PDF so we can "
            "split install / equipment / fees. Do not put those on the monthly D/O. "
            "QB open is historical, not current cycle due. "
            "5 Oct 2026 D/O is authorised, not collected."
        ),
        "customers": clients_out,
        "queries": query_rows,
        "monthly": monthly_rows,
    }


def for_export(as_at: date | None = None) -> dict:
    pack = classify(as_at)
    # Keep the JSON on the dash small: monthly rows summarised, queries in full.
    return {
        "as_at": pack["as_at"],
        "source": pack["source"],
        "range": pack["range"],
        "count": pack["count"],
        "monthly_count": pack["monthly_count"],
        "query_count": pack["query_count"],
        "billed": pack["billed"],
        "qb_open": pack["qb_open"],
        "ask": pack["ask"],
        "note": pack["note"],
        "customers": pack["customers"],
        "queries": pack["queries"],
    }


def self_test() -> int:
    failed = 0
    pack = classify(date(2026, 10, 5))
    by_no = {r["number"]: r for r in pack["queries"] + pack["monthly"]}
    query_nos = {r["number"] for r in pack["queries"]}
    monthly_nos = {r["number"] for r in pack["monthly"]}
    expect_query = {
        "2010",  # Dirk 1999
        "2205",  # Stan 1999
        "2660",  # Stan 100
        "2130",  # Marlene 1100
        "2219",  # Marlene 4123
        "2131",  # Annette HH 2500
        "2335",  # Amoroc 2345.25
        "2406",  # Phillipus 2398
        "2464",  # HM Builders 1168
        "2552",  # Aljo 1098
        "2566",  # Lategan 7570
        "2567",  # Lategan 2648
        "2996",  # Lategan 1591.55
        "2585",  # Murray install 2747
        "3020",  # Murray 454.25
        "2621",  # HPP 1337.61
        "2717",  # Paltco 1119.20
        "2715",  # Cupido 1467.25
        "3106",  # Cupido 200
        "3055",  # Cupido 439 (not his 759 rental)
        "2716",  # Bing Noordhoek 578.70
        "2550",  # Bryant 894
        "3082",  # Neethling 937.65
        "3083",  # Wessels 2956
        "3129",  # van Zyl 1284.50
        "2535",  # Dykman 899
    }
    expect_monthly = {
        "2020",  # Wantling 399
        "2425",  # De Gruchy first 999 — monthly start
        "2223",  # Pearson 300 rounding
        "2265",  # Marlene 400 rounding
    }
    if pack["count"] != 672:
        print("FAIL invoice-count", pack["count"])
        failed += 1
    elif not expect_query <= query_nos:
        print("FAIL missing-query", sorted(expect_query - query_nos))
        failed += 1
    elif expect_monthly & query_nos:
        print("FAIL monthly-marked-query", sorted(expect_monthly & query_nos))
        failed += 1
    elif not expect_monthly <= monthly_nos:
        print("FAIL missing-monthly", sorted(expect_monthly - monthly_nos))
        failed += 1
    elif by_no["2585"]["kind"] != "query" or "install" not in by_no["2585"]["why"].lower():
        print("FAIL murray-install", by_no["2585"])
        failed += 1
    elif by_no["2010"].get("lines"):
        print("FAIL invented-lines", by_no["2010"])
        failed += 1
    elif by_no["2425"]["kind"] != "monthly":
        print("FAIL degruchy-start", by_no["2425"])
        failed += 1
    elif any(r.get("ask") and r["kind"] != "query" for r in pack["monthly"]):
        print("FAIL ask-on-monthly")
        failed += 1
    elif (by_no.get("2772") or {}).get("access") != "offset" or "loan" not in (
        (by_no.get("2772") or {}).get("what") or (by_no.get("2772") or {}).get("why") or ""
    ).lower():
        print("FAIL paltco-offset-invoice", by_no.get("2772"))
        failed += 1
    else:
        print(
            "OK invoice-list",
            pack["monthly_count"],
            "monthly",
            pack["query_count"],
            "query",
        )
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
