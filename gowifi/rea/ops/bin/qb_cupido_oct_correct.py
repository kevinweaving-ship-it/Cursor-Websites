#!/usr/bin/env python3
"""Correct Cupido October payment + unpaid journal as a pair.

Background (verified 2026-11-09):
- Payment 2457 (2026-10-05, R759) cleared invoice 3125 via Netcash D/O recon.
- JournalEntry 2473 (Doc 438377703, 2026-10-06, R759) re-debited A/R as
  "Netcash unpaid", leaving a floating customer A/R balance.
- Customer Balance is already R2477 = open inv 3150 (759) + inv 3137 (959)
  + JE float (759). Invoice open sum alone is R1718.
- Removing BOTH restores invoice 3125 to open (759) and drops the JE float.
  Balance stays R2477, now entirely on invoices 3125+3150+3137.

Usage:
  python3 qb_cupido_oct_correct.py plan
  python3 qb_cupido_oct_correct.py apply
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path[:0] = ["/opt/gowifi-billing", "/root/gowifi-upp"]
os.chdir("/root/gowifi-upp")
os.environ.setdefault("UPP_DB", "/root/gowifi-upp/upp.db")

from qb_oauth import access_token  # noqa: E402
from qb_api import _get, _query  # noqa: E402

CUSTOMER_ID = "50"
CUSTOMER_NAME = "Mr Godfrey Cupido"
PAYMENT_ID = "2457"
JOURNAL_ID = "2473"
EXPECTED_BALANCE = 2477.0
EXPECTED_OPEN_INVOICES = {
    "2112": 759.0,  # Doc 3125 — reopened after payment delete
    "2161": 759.0,  # Doc 3150
    "2497": 959.0,  # Doc 3137
}
EVIDENCE = Path("/opt/rea/ops/audit/cupido-oct-correct-20261109.json")


def post(realm: str, token: str, entity: str, payload: dict, operation: str | None = None) -> dict:
    base = "https://quickbooks.api.intuit.com/v3/company"
    url = f"{base}/{realm}/{entity}?minorversion=75"
    if operation:
        url += f"&operation={operation}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:1200]
        raise RuntimeError(f"QBO {exc.code}: {body}") from exc


def snapshot(token: str, realm: str) -> dict:
    cust = next(
        (
            c
            for c in _query(realm, token, "Customer")
            if str(c.get("Id")) == CUSTOMER_ID
        ),
        None,
    )
    if not cust:
        raise RuntimeError("customer_missing")
    invs = [
        i
        for i in _query(realm, token, "Invoice")
        if str((i.get("CustomerRef") or {}).get("value")) == CUSTOMER_ID
    ]
    open_inv = {
        str(i.get("Id")): float(i.get("Balance") or 0)
        for i in invs
        if float(i.get("Balance") or 0) > 0.0001
    }
    def _entity(kind: str, eid: str):
        try:
            data = _get(
                f"https://quickbooks.api.intuit.com/v3/company/{realm}/{kind}/{eid}?minorversion=65",
                token,
            )
        except SystemExit as exc:
            return None, str(exc)
        key = "Payment" if kind == "payment" else "JournalEntry"
        return data.get(key), None

    pay, pay_error = _entity("payment", PAYMENT_ID)
    je, je_error = _entity("journalentry", JOURNAL_ID)
    return {
        "customer": {
            "Id": cust.get("Id"),
            "DisplayName": cust.get("DisplayName"),
            "Balance": float(cust.get("Balance") or 0),
        },
        "open_invoices": open_inv,
        "open_invoice_sum": round(sum(open_inv.values()), 2),
        "payment_2457": None
        if not pay
        else {
            "Id": pay.get("Id"),
            "SyncToken": pay.get("SyncToken"),
            "TxnDate": pay.get("TxnDate"),
            "TotalAmt": pay.get("TotalAmt"),
            "PrivateNote": pay.get("PrivateNote"),
            "Linked": [
                (ln.get("LinkedTxn") or [])
                for ln in (pay.get("Line") or [])
            ],
        },
        "payment_error": pay_error,
        "journal_2473": None
        if not je
        else {
            "Id": je.get("Id"),
            "SyncToken": je.get("SyncToken"),
            "DocNumber": je.get("DocNumber"),
            "TxnDate": je.get("TxnDate"),
            "PrivateNote": je.get("PrivateNote"),
            "TotalAmtLines": sum(
                float(ln.get("Amount") or 0)
                for ln in (je.get("Line") or [])
                if (ln.get("JournalEntryLineDetail") or {}).get("PostingType") == "Debit"
            ),
        },
        "journal_error": je_error,
    }


def validate_pre(snap: dict) -> list[str]:
    errs: list[str] = []
    if snap["customer"]["DisplayName"] != CUSTOMER_NAME:
        errs.append("customer_name_mismatch")
    if abs(snap["customer"]["Balance"] - EXPECTED_BALANCE) > 0.01:
        errs.append(f"balance_not_2477:{snap['customer']['Balance']}")
    pay = snap.get("payment_2457")
    if not pay:
        errs.append("payment_2457_missing")
    else:
        if float(pay.get("TotalAmt") or 0) != 759.0:
            errs.append("payment_amount")
        if pay.get("TxnDate") != "2026-10-05":
            errs.append("payment_date")
        if "Netcash D/O recon" not in (pay.get("PrivateNote") or ""):
            errs.append("payment_note")
    je = snap.get("journal_2473")
    if not je:
        errs.append("journal_2473_missing")
    else:
        if je.get("DocNumber") != "438377703":
            errs.append("journal_doc")
        if je.get("TxnDate") != "2026-10-06":
            errs.append("journal_date")
        if "Netcash unpaid" not in (je.get("PrivateNote") or ""):
            errs.append("journal_note")
    return errs


def validate_post(snap: dict) -> list[str]:
    errs: list[str] = []
    if abs(snap["customer"]["Balance"] - EXPECTED_BALANCE) > 0.01:
        errs.append(f"balance_not_2477:{snap['customer']['Balance']}")
    if snap.get("payment_2457"):
        errs.append("payment_still_present")
    if snap.get("journal_2473"):
        errs.append("journal_still_present")
    open_inv = snap.get("open_invoices") or {}
    for iid, amt in EXPECTED_OPEN_INVOICES.items():
        if abs(float(open_inv.get(iid, 0)) - amt) > 0.01:
            errs.append(f"invoice_{iid}_balance:{open_inv.get(iid)}")
    if abs(float(snap.get("open_invoice_sum") or 0) - EXPECTED_BALANCE) > 0.01:
        errs.append(f"open_sum:{snap.get('open_invoice_sum')}")
    return errs


def apply(token: str, realm: str, snap: dict) -> dict:
    pay = snap["payment_2457"]
    je = snap["journal_2473"]
    deleted = {}
    # Delete payment first (reopens invoice 3125), then delete journal (removes float).
    deleted["payment"] = post(
        realm,
        token,
        "payment",
        {"Id": pay["Id"], "SyncToken": pay["SyncToken"]},
        operation="delete",
    )
    deleted["journal"] = post(
        realm,
        token,
        "journalentry",
        {"Id": je["Id"], "SyncToken": je["SyncToken"]},
        operation="delete",
    )
    return deleted


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "plan").strip().lower()
    if mode not in {"plan", "apply"}:
        print(json.dumps({"ok": False, "error": "usage", "message": "plan|apply"}))
        return 2
    token, realm = access_token()
    before = snapshot(token, realm)
    pre_errs = validate_pre(before)
    result = {
        "ok": not pre_errs,
        "mode": mode,
        "writes_to_qb": mode == "apply",
        "before": before,
        "pre_errors": pre_errs,
        "expected_balance": EXPECTED_BALANCE,
        "recipe": "cupido-oct-2026",
    }
    if pre_errs:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, ensure_ascii=True))
        return 2
    if mode == "plan":
        result["planned"] = [
            f"DELETE payment {PAYMENT_ID}",
            f"DELETE journalentry {JOURNAL_ID}",
            "Expect Balance R2477 on invoices 3125+3150+3137",
        ]
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, ensure_ascii=True))
        return 0
    deleted = apply(token, realm, before)
    after = snapshot(token, realm)
    post_errs = validate_post(after)
    result.update(
        {
            "ok": not post_errs,
            "deleted": {
                "payment_status": list(deleted.get("payment", {}).keys()),
                "journal_status": list(deleted.get("journal", {}).keys()),
            },
            "after": after,
            "post_errors": post_errs,
        }
    )
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
