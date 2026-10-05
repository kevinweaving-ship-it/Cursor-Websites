#!/usr/bin/env python3
"""QuickBooks Customers.xls — address, phone, email, B number on the name.

qb_open is historical QuickBooks, not the current billing-cycle due.
Do not invent licence numbers or phone numbers.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
CUSTOMERS_JSON = DATA_DIR / "qb_customers.json"
CUSTOMERS_XLS = DATA_DIR / "Customers.xls"


def _load_json() -> dict:
    if not CUSTOMERS_JSON.exists():
        return {"source": "Customers.xls", "rows": [], "count": 0}
    return json.loads(CUSTOMERS_JSON.read_text())


def rows() -> list[dict]:
    return list(_load_json().get("rows") or [])


def lookup(name: str | None) -> dict | None:
    from billing import canon_key

    want = canon_key(name)
    if not want:
        return None
    for row in rows():
        if canon_key(row.get("name")) == want or canon_key(row.get("company")) == want:
            return dict(row)
    return None


def for_export() -> dict:
    pack = _load_json()
    out_rows = []
    for row in rows():
        item = dict(row)
        item["qb_open_note"] = "Historical QuickBooks open — not current cycle due"
        out_rows.append(item)
    return {
        "source": pack.get("source") or "Customers.xls",
        "as_at": pack.get("as_at"),
        "count": len(out_rows),
        "note": pack.get("note")
        or "QuickBooks customer list. qb_open is historical, not current cycle due.",
        "rows": out_rows,
    }


def self_test() -> int:
    failed = 0
    pack = for_export()
    by = {r["name"]: r for r in pack["rows"]}
    if pack["count"] != 24:
        print("FAIL customer-count", pack["count"])
        failed += 1
    elif by["Amoroc Doors"]["phone"] != "028 313 1338":
        print("FAIL amoroc-phone", by["Amoroc Doors"])
        failed += 1
    elif by["De Gruchy - Phillip B110034779"]["b_number"] != "B110034779":
        print("FAIL degruchy-b", by["De Gruchy - Phillip B110034779"])
        failed += 1
    elif by["Hermanus Builders B110039414"]["b_number"] != "B110039414":
        print("FAIL builders-b", by["Hermanus Builders B110039414"])
        failed += 1
    elif "mussel" not in (by["HPP Control Room"].get("address") or "").lower():
        print("FAIL hpp-addr", by["HPP Control Room"])
        failed += 1
    elif lookup("Wantling, David")["email"] != "david@macd.co.za":
        print("FAIL wantling-email", lookup("Wantling, David"))
        failed += 1
    elif lookup("Annette Bing Nordhoek")["name"] != "Annette Bing Nordhoek":
        print("FAIL nordhoek-lookup", lookup("Annette Bing Nordhoek"))
        failed += 1
    elif lookup("Bing, Annette - HH")["name"] == lookup("Annette Bing Nordhoek")["name"]:
        print("FAIL hh-vs-nordhoek")
        failed += 1
    elif lookup("Mr Derek van Zyl") is None or lookup("Mr Ruandré Wessels") is None:
        print("FAIL new-customers")
        failed += 1
    else:
        print("OK customers")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
