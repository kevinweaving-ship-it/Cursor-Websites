#!/usr/bin/env python3
"""Plain canned GoWiFi invoice — invoice on top, statement history under it. One page."""
from __future__ import annotations

import re
from html import escape

from company import COMPANY

TITLES = {"mr", "mrs", "ms", "miss", "dr"}


def money(value) -> str:
    if value is None:
        return "—"
    return f"R{float(value):,.2f}"


def client_key(name: str | None) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if w not in TITLES]
    return " ".join(words[:2])


def statement_on_invoice(invoices: list[dict], payments: list[dict], customer: str | None) -> dict:
    """Running invoice + payment history for one client. Lives on the invoice page."""
    key = client_key(customer)
    if not key:
        return {"lines": [], "total_due": None}
    rows = []
    for inv in invoices:
        if client_key(inv.get("customer")) != key:
            continue
        rows.append(
            {
                "date": inv.get("invoice_date"),
                "description": f"Invoice No.{inv.get('invoice_number')}",
                "amount": float(inv.get("amount") or 0),
            }
        )
    for pay in payments:
        if client_key(pay.get("customer")) != key:
            continue
        rows.append(
            {
                "date": pay.get("paid_on") or pay.get("invoice_date"),
                "description": pay.get("note") or "Payment",
                "amount": float(pay.get("amount") or 0),
            }
        )
    rows.sort(key=lambda r: (r.get("date") or "", r.get("description") or ""))
    balance = 0.0
    lines = []
    for row in rows:
        balance = round(balance + row["amount"], 2)
        lines.append({**row, "balance": balance})
    return {"lines": lines, "total_due": balance}


def render_invoice(row: dict) -> str:
    c = COMPANY
    lines = "".join(f"<div>{escape(x)}</div>" for x in c["lines"])
    addr = escape(row.get("address") or "")
    desc = escape(row.get("description") or "Monthly service")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Invoice {escape(str(row.get("invoice_number") or ""))}</title>
<style>
body {{ font: 14px/1.4 Georgia, "Times New Roman", serif; color:#111; margin:24px auto; max-width:760px; }}
h1 {{ font-size:28px; letter-spacing:.08em; margin:28px 0 12px; }}
.muted {{ color:#444; font-size:13px; }}
.row {{ display:flex; justify-content:space-between; gap:24px; }}
table {{ width:100%; border-collapse:collapse; margin:22px 0; }}
th {{ text-align:left; font-size:11px; letter-spacing:.05em; border-bottom:1px solid #111; padding:6px 4px; }}
td {{ padding:10px 4px; vertical-align:top; border-bottom:1px solid #ddd; }}
.num {{ text-align:right; white-space:nowrap; }}
.due {{ font-size:18px; font-weight:700; text-align:right; margin:12px 0 8px; }}
h2 {{ font-size:16px; letter-spacing:.08em; margin:28px 0 8px; }}
.bank {{ border-top:1px solid #111; padding-top:10px; font-size:13px; margin-top:20px; }}
a.back {{ font: 13px sans-serif; color:#345; }}
@media print {{ a.back {{ display:none; }} body {{ margin:12mm; }} }}
</style>
</head>
<body>
<p class="back"><a class="back" href="/dash/accounts.html">← Fibre accounts</a></p>
<div><strong>{escape(c["name"])}</strong></div>
{lines}
<div class="muted">{escape(c["phone"])} · {escape(c["email"])}</div>
<div class="muted">Business ID No. {escape(c["reg"])}</div>
<h1>INVOICE</h1>
<div class="row">
  <div>
    <div class="muted">BILL TO</div>
    <div><strong>{escape(row.get("customer") or "—")}</strong></div>
    <div>{addr}</div>
  </div>
  <div>
    <div>INVOICE {escape(str(row.get("invoice_number") or ""))}</div>
    <div>DATE {escape(row.get("invoice_date") or "—")}</div>
    <div>TERMS {escape(row.get("terms") or "Due on receipt")}</div>
    <div>DUE DATE {escape(row.get("due_date") or row.get("invoice_date") or "—")}</div>
  </div>
</div>
<table>
  <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Rate</th><th class="num">Amount</th></tr></thead>
  <tbody>
    <tr>
      <td>{desc}</td>
      <td class="num">{escape(str(row.get("qty") or 1))}</td>
      <td class="num">{money(row.get("rate") if row.get("rate") is not None else row.get("amount"))}</td>
      <td class="num">{money(row.get("amount"))}</td>
    </tr>
  </tbody>
</table>
<div class="due">THIS INVOICE {money(row.get("amount"))}</div>
{statement_html(row)}
<div class="bank">
  <div>Banking/EFT Details</div>
  <div>Account Name: {escape(c["bank_account_name"])}</div>
  <div>Bank: {escape(c["bank"])}</div>
  <div>Branch: {escape(c["branch"])}</div>
  <div>Branch Code: {escape(c["branch_code"])}</div>
  <div>Account Number: {escape(c["account_number"])}</div>
</div>
</body>
</html>
"""


def statement_html(row: dict) -> str:
    stmt = row.get("statement") or {}
    lines = stmt.get("lines") or []
    if not lines:
        return f'<div class="due">BALANCE DUE {money(row.get("balance_due") if row.get("balance_due") is not None else row.get("amount"))}</div>'
    body = "".join(
        f"<tr><td>{escape(line.get('date') or '—')}</td>"
        f"<td>{escape(line.get('description') or '')}</td>"
        f"<td class=\"num\">{money(line.get('amount'))}</td>"
        f"<td class=\"num\">{money(line.get('balance'))}</td></tr>"
        for line in lines
    )
    return f"""
<h2>STATEMENT</h2>
<table>
  <thead><tr><th>Date</th><th>Description</th><th class="num">Amount</th><th class="num">Balance</th></tr></thead>
  <tbody>{body}</tbody>
</table>
<div class="due">BALANCE DUE {money(stmt.get("total_due"))}</div>
"""


def self_test() -> int:
    failed = 0
    invoices = [
        {"invoice_number": 1, "invoice_date": "2026-01-01", "customer": "Mr Godfrey Cupido", "amount": 759},
        {"invoice_number": 2, "invoice_date": "2026-02-01", "customer": "Godfrey Cupido", "amount": 759},
        {"invoice_number": 9, "invoice_date": "2026-02-01", "customer": "Amoroc Doors", "amount": 199},
    ]
    payments = [{"paid_on": "2026-01-15", "customer": "Mr Godfrey Cupido", "amount": -759, "note": "Payment"}]
    stmt = statement_on_invoice(invoices, payments, "Godfrey Cupido")
    if len(stmt["lines"]) != 3 or stmt["total_due"] != 759:
        print("FAIL ledger", stmt)
        failed += 1
    elif stmt["lines"][0]["description"] != "Invoice No.1":
        print("FAIL first-line", stmt)
        failed += 1
    else:
        print("OK invoice-plus-statement")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())

