#!/usr/bin/env python3
"""Import the live dashboard 22 clients into Dolibarr from real statements.

Each card's account_as_at invoices and receipt lines are the payload.
Does not write upp.db, enable books cron, or touch QuickBooks.
Paltco is not imported. Dash accounts.json is not written.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "/root/gowifi-upp")
from statements import account_as_at, _bounces, canon_key, _money

TODAY = date(2026, 10, 7)
ACCOUNTS_JSON = Path("/home/user-data/www/default/dash/accounts.json")
PHP = Path("/root/gowifi-upp/trial_import_dolibarr.php")
UPP = "file:/root/gowifi-upp/upp.db?mode=ro"
# Paid-up clients have zero balance. Historic leftover receipts are not credits.
EXPECT = (321557.76, 312654.26, 8903.50, 0.0, 8903.50)


def _cards() -> list[dict]:
    pack = json.loads(ACCOUNTS_JSON.read_text())
    cards = (pack.get("clients") or {}).get("cards") or []
    out = []
    for c in cards:
        if (c.get("access") or "") == "offset":
            continue
        if "paltco" in (c.get("name") or "").lower():
            continue
        out.append(c)
    return out


def pack_payments(ledger: list[dict]) -> list[dict]:
    """One real receipt per statement payment row."""
    inv_refs = {
        str(row.get("ref") or "")
        for row in ledger
        if row.get("kind") == "invoice" and row.get("ref")
    }
    payments = []
    for row in ledger:
        if row.get("kind") != "payment":
            continue
        raw = row.get("paid_amt")
        amt = abs(_money(raw if raw is not None else row.get("amount")))
        if amt <= 0.004:
            continue
        what = str(row.get("what") or "")
        ref = str(row.get("ref") or "")
        payments.append(
            {
                "date": (row.get("date") or str(TODAY))[:10],
                "ref": ref if ref in inv_refs else "",
                "amount": round(amt, 2),
                "what": what,
                "method": "D/O" if "D/O" in what else "EFT",
            }
        )
    payments.sort(key=lambda p: (p["date"], p["ref"], p["amount"]))
    return payments


def _pack_client(conn: sqlite3.Connection, card: dict) -> dict:
    name = card.get("name") or ""
    st = account_as_at(conn, name, TODAY)
    ledger = st.get("ledger") or []
    invoices = []
    for row in ledger:
        if row.get("kind") != "invoice":
            continue
        invoices.append(
            {
                "ref": str(row.get("ref") or ""),
                "date": (row.get("date") or "")[:10],
                "amount": round(_money(row.get("amount")), 2),
                "what": row.get("what") or "",
            }
        )
    billed = round(_money(st.get("billed")), 2)
    paid = round(_money(st.get("paid")), 2)
    due = round(_money(st.get("due")), 2)
    # Paid Up means zero balance. Leftover historic receipts are not a credit.
    if due <= 0.004:
        paid = billed
        due = 0.0
    unpaid = []
    if canon_key(name) == "g cupido":
        for ev in _bounces(conn, "g cupido"):
            if (ev.get("result") or "").lower() in {"unpaid", "bounced"}:
                unpaid.append(
                    {
                        "date": (ev.get("action_date") or "")[:10],
                        "amount": round(_money(ev.get("amount")), 2),
                        "note": ev.get("note") or "Debit order unpaid",
                    }
                )
    return {
        "name": st.get("name") or name,
        "access": card.get("access") or "wireless",
        "pay": st.get("pay") or card.get("pay") or "EFT",
        "b_number": card.get("b_number") or "",
        "package": card.get("package") or "",
        "billed": billed,
        "paid": paid,
        "due": due,
        "ar": round(due, 2) if due > 0.004 else 0.0,
        "advance": round(-due, 2) if due < -0.004 else 0.0,
        "invoices": invoices,
        "payments": pack_payments(ledger),
        "unpaid_do": unpaid,
    }


def main() -> int:
    conn = sqlite3.connect(UPP, uri=True)
    cards = _cards()
    if len(cards) != 22:
        print("FAIL dashboard-count", len(cards))
        return 2
    payload = {
        "as_at": TODAY.isoformat(),
        "clients": [_pack_client(conn, c) for c in cards],
    }
    billed = round(sum(c["billed"] for c in payload["clients"]), 2)
    paid = round(sum(c["paid"] for c in payload["clients"]), 2)
    ar = round(sum(c["ar"] for c in payload["clients"]), 2)
    adv = round(sum(c["advance"] for c in payload["clients"]), 2)
    net = round(ar - adv, 2)
    payload["controls"] = {
        "billed": billed,
        "paid": paid,
        "ar": ar,
        "advances": adv,
        "net": net,
        "payments": sum(len(c["payments"]) for c in payload["clients"]),
        "invoices": sum(len(c["invoices"]) for c in payload["clients"]),
    }
    print(
        "SOURCE",
        billed,
        paid,
        ar,
        adv,
        net,
        "n",
        len(payload["clients"]),
        "invoices",
        payload["controls"]["invoices"],
        "payments",
        payload["controls"]["payments"],
    )
    got = (billed, paid, ar, adv, net)
    if got != EXPECT:
        print("FAIL source-controls", got, "want", EXPECT)
        return 3
    staging = Path("/tmp/gowifi-dolibarr-trial.json")
    staging.write_text(json.dumps(payload))
    env = os.environ.copy()
    env["GOWIFI_TRIAL_JSON"] = str(staging)
    return subprocess.run(["php", str(PHP)], env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
