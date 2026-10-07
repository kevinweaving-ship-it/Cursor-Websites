#!/usr/bin/env python3
"""Trial-import the live dashboard 22 clients into Dolibarr 24.0.2.

Uses each card's account_as_at statement invoices, allocations and carried due.
Does not write upp.db, enable books cron, or touch QuickBooks.
Paltco is not imported.
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
                "open": round(_money(row.get("open")), 2),
                "what": row.get("what") or "",
            }
        )
    billed = round(_money(st.get("billed")), 2)
    paid = round(_money(st.get("paid")), 2)
    due = round(_money(st.get("due")), 2)
    ar = round(due, 2) if due > 0.004 else 0.0
    advance = round(-due, 2) if due < -0.004 else 0.0
    # Account due is truth: pay every invoice down so remaintopay sums to AR.
    # If due <= 0, all invoices are fully allocated and leftover is the advance.
    if due <= 0.004:
        for inv in invoices:
            inv["to_pay"] = inv["amount"]
            inv["remain"] = 0.0
    else:
        remain_budget = ar
        for inv in invoices:
            # newest-first ledger; keep remain on the currently open rows
            open_amt = inv["open"] if inv["open"] > 0.004 else 0.0
            take = min(open_amt, remain_budget)
            inv["remain"] = round(take, 2)
            inv["to_pay"] = round(inv["amount"] - take, 2)
            remain_budget = round(remain_budget - take, 2)
        if abs(remain_budget) > 0.02:
            # fallback: put leftover remain on last invoice
            invoices[-1]["remain"] = round(invoices[-1]["remain"] + remain_budget, 2)
            invoices[-1]["to_pay"] = round(invoices[-1]["amount"] - invoices[-1]["remain"], 2)
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
        "ar": ar,
        "advance": advance,
        "invoices": invoices,
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
    )
    expect = (321557.76, 317654.91, 8903.50, 5000.65, 3902.85)
    got = (billed, paid, ar, adv, net)
    if got != expect:
        print("FAIL source-controls", got, "want", expect)
        return 3
    staging = Path("/tmp/gowifi-dolibarr-trial.json")
    staging.write_text(json.dumps(payload))
    env = os.environ.copy()
    env["GOWIFI_TRIAL_JSON"] = str(staging)
    proc = subprocess.run(["php", str(PHP)], env=env)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
