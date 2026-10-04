#!/usr/bin/env python3
"""Plain canned GoWiFi invoice — same fields as the old QuickBooks one, nothing extra."""
from __future__ import annotations

from html import escape

from company import COMPANY


def money(value) -> str:
    if value is None:
        return "—"
    return f"R{float(value):,.2f}"


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
.due {{ font-size:18px; font-weight:700; text-align:right; margin:12px 0 24px; }}
.bank {{ border-top:1px solid #111; padding-top:10px; font-size:13px; }}
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
<div class="due">BALANCE DUE {money(row.get("balance_due") if row.get("balance_due") is not None else row.get("amount"))}</div>
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
