#!/usr/bin/env python3
"""One A4 GoWiFi invoice with a compact statement of account under it.

Layout follows the old QuickBooks invoice (letterhead, BILL TO, this month’s
line, FNB footer) plus a South African statement of account: opening balance,
Date / Reference / Description / Debit / Credit / Balance, ageing, closing.
Not a Tax Invoice — the old PDFs have no VAT number.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from html import escape

from company import COMPANY

TITLES = {"mr", "mrs", "ms", "miss", "dr"}
KEEP_MONTHS = 12
MAX_STATEMENT_LINES = 20
SPEED_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*Mbps\s+down\s*/\s*(\d+(?:\.\d+)?)\s*Mbps\s+Up"
    r"(?:\s*-\s*Uncapped(?:\s*\(FUP\s*\d+\))?)?",
    re.I,
)


def money(value, with_r: bool = True) -> str:
    if value is None or value == "":
        return ""
    number = float(value)
    sign = "-" if number < 0 else ""
    body = f"{abs(number):,.2f}"
    return f"{sign}{'R' if with_r else ''}{body}"


def client_key(name: str | None) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if w not in TITLES]
    return " ".join(words[:2])


def parse_day(value) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def fmt_date(value) -> str:
    day = parse_day(value)
    return day.strftime("%d/%m/%Y") if day else (str(value).strip() if value else "—")


def clean_description(text: str | None) -> str:
    """Undo mashed QuickBooks ACTIVITY+DESCRIPTION+qty/rate/amount lines."""
    if not text:
        return "Monthly service"
    blob = re.sub(r"\s+", " ", str(text)).strip()
    blob = re.sub(r"\s+\d+(?:\.\d+)?\s+[\d,]+\.\d{2}\s+[\d,]+\.\d{2}\s*$", "", blob)
    speeds = list(SPEED_RE.finditer(blob))
    if speeds:
        last = speeds[-1]
        head = blob[: last.start()]
        head = re.split(r"\d+(?:\.\d+)?\s*Mbps", head, maxsplit=1, flags=re.I)[0]
        head = re.sub(r"(?i)^old\s*$", "", head.strip(" -/—"))
        label = re.sub(r"\s+", " ", last.group(0)).strip(" -")
        if head and len(head) <= 28 and not re.match(r"(?i)gw\d", head):
            return f"{head} — {label}"
        return label
    blob = re.sub(r"\b(.{8,}?)\s+\1\b", r"\1", blob)
    blob = blob.replace("Fiber", "Fibre")
    blob = re.sub(r"\s+[-/]\s*$", "", blob).strip(" -")
    return blob or "Monthly service"


def _cutoff(as_at: date | None) -> date | None:
    if not as_at:
        return None
    year = as_at.year - KEEP_MONTHS // 12
    month = as_at.month - (KEEP_MONTHS % 12)
    if month <= 0:
        year -= 1
        month += 12
    day = min(as_at.day, 28)
    try:
        return date(year, month, as_at.day)
    except ValueError:
        return date(year, month, day)


def _signed(kind: str, amount: float) -> float:
    if kind == "payment":
        return -abs(amount)
    return float(amount)


def _apply_pay(open_inv: list[dict], pay: float) -> float:
    while pay > 0.004 and open_inv:
        take = min(pay, open_inv[0]["amount"])
        open_inv[0]["amount"] = round(open_inv[0]["amount"] - take, 2)
        pay = round(pay - take, 2)
        if open_inv[0]["amount"] <= 0.004:
            open_inv.pop(0)
    return pay


def _bucket(days: int) -> str:
    if days <= 0:
        return "current"
    if days <= 30:
        return "d30"
    if days <= 60:
        return "d60"
    if days <= 90:
        return "d90"
    return "older"


def _open_items(rows: list[dict]) -> tuple[list[dict], float]:
    open_inv: list[dict] = []
    credit = 0.0
    for row in rows:
        kind = row["kind"]
        signed = row["signed"]
        if kind in {"invoice", "forward"} and signed > 0:
            amount = signed
            if credit:
                take = min(credit, amount)
                amount = round(amount - take, 2)
                credit = round(credit - take, 2)
            if amount > 0.004:
                open_inv.append(
                    {
                        "date": row["date"],
                        "reference": row.get("reference") or "",
                        "amount": amount,
                    }
                )
            continue
        pay = abs(signed) if kind == "payment" or signed < 0 else 0.0
        leftover = _apply_pay(open_inv, pay)
        if leftover > 0.004:
            credit = round(credit + leftover, 2)
    return open_inv, credit


def _age_items(items: list[dict], age_on: date, credit: float = 0.0) -> tuple[list[dict], dict, float]:
    buckets = {"current": 0.0, "d30": 0.0, "d60": 0.0, "d90": 0.0, "older": 0.0}
    latest = None
    for item in items:
        day = parse_day(item["date"])
        if day and (latest is None or day > latest):
            latest = day
    lines = []
    running = 0.0
    for item in items:
        day = parse_day(item["date"]) or age_on
        days = (age_on - day).days
        # Latest bill is Current; older unpaid invoices age from today.
        bucket = "current" if latest and day == latest else _bucket(days)
        buckets[bucket] = round(buckets[bucket] + item["amount"], 2)
        running = round(running + item["amount"], 2)
        lines.append(
            {
                "date": item["date"],
                "date_fmt": fmt_date(item["date"]),
                "reference": item["reference"],
                "description": "Invoice" if item["reference"] else "Balance forward",
                "days": max(days, 0),
                "amount": item["amount"],
                "debit": item["amount"],
                "credit": None,
                "balance": running,
                "kind": "invoice" if item["reference"] else "forward",
                "bucket": bucket,
            }
        )
    if credit:
        buckets["current"] = round(buckets["current"] - credit, 2)
        running = round(running - credit, 2)
        lines.append(
            {
                "date": age_on.isoformat(),
                "date_fmt": fmt_date(age_on),
                "reference": "",
                "description": "Unallocated credit",
                "days": 0,
                "amount": -credit,
                "debit": None,
                "credit": credit,
                "balance": running,
                "kind": "credit",
                "bucket": "current",
            }
        )
    ageing = {key: round(val, 2) for key, val in buckets.items()}
    return lines, ageing, running


def _ageing(rows: list[dict], as_at: date | None) -> dict:
    items, credit = _open_items(rows)
    _lines, ageing, _total = _age_items(items, as_at or date.today(), credit)
    return ageing


def statement_on_invoice(
    invoices: list[dict],
    payments: list[dict],
    customer: str | None,
    as_at=None,
) -> dict:
    """Ledger as at the invoice date, compacted to fit under the invoice on A4."""
    key = client_key(customer)
    as_day = parse_day(as_at)
    if not key:
        return {
            "lines": [],
            "total_due": None,
            "as_at": as_day.isoformat() if as_day else None,
            "ageing": {"current": 0, "d30": 0, "d60": 0, "d90": 0, "older": 0},
        }
    rows = []
    for inv in invoices:
        if client_key(inv.get("customer")) != key:
            continue
        day = parse_day(inv.get("invoice_date"))
        if as_day and day and day > as_day:
            continue
        amount = float(inv.get("amount") or 0)
        rows.append(
            {
                "date": day.isoformat() if day else (inv.get("invoice_date") or ""),
                "reference": str(inv.get("invoice_number") or ""),
                "description": "Invoice",
                "kind": "invoice",
                "signed": _signed("invoice", amount),
            }
        )
    for pay in payments:
        if client_key(pay.get("customer")) != key:
            continue
        raw_note = (pay.get("note") or "Payment").strip()
        kind = "forward" if raw_note.lower() == "balance forward" else "payment"
        day = parse_day(pay.get("paid_on") or pay.get("invoice_date"))
        if as_day and day and day > as_day:
            continue
        amount = float(pay.get("amount") or 0)
        rows.append(
            {
                "date": day.isoformat() if day else (pay.get("paid_on") or ""),
                "reference": "",
                "description": "Balance forward" if kind == "forward" else "Payment",
                "kind": kind,
                "signed": _signed(kind, amount) if kind == "payment" else amount,
            }
        )
    rows.sort(key=lambda r: (r.get("date") or "", r.get("kind") or "", r.get("reference") or ""))
    age_on = as_day or date.today()
    items, credit = _open_items(rows)
    lines, ageing, balance = _age_items(items, age_on, credit)
    pay_days = [r for r in rows if r["kind"] == "payment"]
    last_pay = None
    if pay_days:
        last_day = max(r["date"] for r in pay_days)
        last_pay = {
            "date": last_day,
            "amount": round(sum(abs(r["signed"]) for r in pay_days if r["date"] == last_day), 2),
        }
    aged_sum = round(sum(ageing.values()), 2)
    return {
        "lines": lines,
        "total_due": balance,
        "as_at": age_on.isoformat(),
        "period_from": lines[0]["date"] if lines else None,
        "ageing": ageing,
        "ageing_sum": aged_sum,
        "last_payment": last_pay,
    }


def prepare_invoice(row: dict) -> dict:
    out = dict(row)
    out["description"] = clean_description(row.get("description"))
    out["invoice_date_fmt"] = fmt_date(row.get("invoice_date"))
    out["due_date_fmt"] = fmt_date(row.get("due_date") or row.get("invoice_date"))
    return out


def _address_html(address: str | None) -> str:
    parts = [p.strip() for p in str(address or "").split(",") if p.strip()]
    return "".join(f"<div>{escape(p)}</div>" for p in parts)


def render_invoice(row: dict) -> str:
    c = COMPANY
    row = prepare_invoice(row)
    lines = "".join(f"<div>{escape(x)}</div>" for x in c["lines"])
    desc = escape(row.get("description") or "Monthly service")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Invoice {escape(str(row.get("invoice_number") or ""))}</title>
<style>{DOCUMENT_CSS}</style>
</head>
<body>
<p class="screen-only"><a class="back" href="/dash/accounts.html">← Fibre accounts</a></p>
<article class="sheet">
  <header class="letterhead">
    <div>
      <div class="brand">{escape(c["name"])}</div>
      {lines}
      <div class="muted">{escape(c["phone"])} · {escape(c["email"])}</div>
      <div class="muted">Business ID No. {escape(c["reg"])}</div>
    </div>
    <div class="doc-title">INVOICE</div>
  </header>
  <section class="parties">
    <div>
      <div class="label">Bill to</div>
      <div class="who">{escape(row.get("customer") or "—")}</div>
      {_address_html(row.get("address"))}
    </div>
    <table class="meta">
      <tr><th>Invoice</th><td>{escape(str(row.get("invoice_number") or ""))}</td></tr>
      <tr><th>Date</th><td>{escape(row.get("invoice_date_fmt") or "—")}</td></tr>
      <tr><th>Terms</th><td>{escape(row.get("terms") or "Due on receipt")}</td></tr>
      <tr><th>Due date</th><td>{escape(row.get("due_date_fmt") or "—")}</td></tr>
    </table>
  </section>
  <table class="lines">
    <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Rate</th><th class="num">Amount</th></tr></thead>
    <tbody>
      <tr>
        <td>{desc}</td>
        <td class="num">{escape(str(row.get("qty") or 1))}</td>
        <td class="num">{money(row.get("rate") if row.get("rate") is not None else row.get("amount"), False)}</td>
        <td class="num">{money(row.get("amount"), False)}</td>
      </tr>
    </tbody>
  </table>
  <div class="due">This invoice {money(row.get("amount"))}</div>
  {statement_html(row)}
  <footer class="bank">
    <div class="label">Banking / EFT</div>
    <div>Account name {escape(c["bank_account_name"])}</div>
    <div>{escape(c["bank"])} · {escape(c["branch"])} · {escape(c["branch_code"])}</div>
    <div>Account {escape(c["account_number"])} · Reference {escape(str(row.get("invoice_number") or ""))}</div>
  </footer>
</article>
</body>
</html>
"""


DOCUMENT_CSS = """
@page { size: A4; margin: 12mm; }
body { font: 11px/1.35 "Helvetica Neue", Helvetica, Arial, sans-serif; color:#1a1a1a; background:#e8e8e8; margin:0; }
.sheet { width:210mm; min-height:297mm; margin:16px auto; background:#fff; padding:14mm 16mm; box-sizing:border-box; box-shadow:0 1px 8px rgba(0,0,0,.12); }
.letterhead { display:flex; justify-content:space-between; align-items:flex-start; gap:24px; border-bottom:2px solid #1a1a1a; padding-bottom:10px; }
.brand { font-size:18px; font-weight:700; letter-spacing:.02em; margin-bottom:4px; }
.doc-title { font-size:28px; font-weight:700; letter-spacing:.14em; }
.muted { color:#555; }
.label { font-size:9px; letter-spacing:.12em; text-transform:uppercase; color:#555; margin-bottom:3px; }
.parties { display:flex; justify-content:space-between; gap:28px; margin:16px 0 14px; }
.who { font-weight:700; font-size:13px; }
.meta { border-collapse:collapse; }
.meta th { text-align:left; font-weight:600; color:#555; padding:2px 16px 2px 0; }
.meta td { text-align:right; font-weight:600; }
table.lines, table.soa { width:100%; border-collapse:collapse; }
table.lines th, table.soa th { text-align:left; font-size:9px; letter-spacing:.08em; text-transform:uppercase; border-bottom:1px solid #1a1a1a; padding:6px 4px; }
table.lines td, table.soa td { padding:5px 4px; border-bottom:1px solid #e4e4e4; vertical-align:top; }
.num { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
.due { font-size:13px; font-weight:700; text-align:right; margin:10px 0 18px; }
h2 { font-size:12px; letter-spacing:.12em; text-transform:uppercase; margin:0 0 6px; display:flex; justify-content:space-between; }
.ageing { width:100%; border-collapse:collapse; margin:10px 0 4px; }
.ageing th { font-size:8px; letter-spacing:.06em; text-transform:uppercase; color:#555; text-align:right; padding:2px 6px; }
.ageing td { text-align:right; font-weight:600; padding:2px 6px; font-variant-numeric:tabular-nums; }
.ageing td.total, .ageing th.total { font-size:13px; }
.bank { border-top:1px solid #1a1a1a; padding-top:8px; margin-top:16px; color:#333; }
a.back { font: 13px/1.4 sans-serif; color:#345; }
.screen-only { max-width:210mm; margin:12px auto 0; padding:0 16px; }
@media print { body { background:#fff; } .sheet { margin:0; box-shadow:none; width:auto; min-height:0; padding:0; } .screen-only { display:none; } }
"""


def statement_html(row: dict) -> str:
    stmt = row.get("statement") or {}
    lines = stmt.get("lines") or []
    due = stmt.get("total_due")
    if due is None:
        due = row.get("balance_due") if row.get("balance_due") is not None else row.get("amount")
    if not lines:
        return f'<div class="due">Balance due {money(due)}</div>'
    body = "".join(
        "<tr>"
        f"<td>{escape(line.get('date_fmt') or fmt_date(line.get('date')))}</td>"
        f"<td>{escape(str(line.get('reference') or ''))}</td>"
        f"<td class=\"num\">{escape(str(line.get('days') if line.get('days') is not None else ''))}</td>"
        f"<td class=\"num\">{money(line.get('amount') if line.get('amount') is not None else line.get('debit'), False)}</td>"
        "</tr>"
        for line in lines
    )
    ageing = stmt.get("ageing") or {}
    as_at = fmt_date(stmt.get("as_at") or row.get("invoice_date"))
    last = stmt.get("last_payment") or {}
    last_html = (
        f'<div class="muted">Last payment {escape(fmt_date(last.get("date")))} {money(last.get("amount"))}</div>'
        if last.get("date")
        else ""
    )
    return f"""
<h2><span>Outstanding</span><span class="muted">as at {escape(as_at)}</span></h2>
{last_html}
<table class="soa">
  <thead><tr><th>Date</th><th>Invoice</th><th class="num">Days</th><th class="num">Amount</th></tr></thead>
  <tbody>{body}</tbody>
</table>
<table class="ageing">
  <tr><th>Current</th><th>1–30 days</th><th>31–60 days</th><th>61–90 days</th><th>90+ days</th><th class="total">= Balance due</th></tr>
  <tr>
    <td>{money(ageing.get("current"), False) or "0.00"}</td>
    <td>{money(ageing.get("d30"), False) or "0.00"}</td>
    <td>{money(ageing.get("d60"), False) or "0.00"}</td>
    <td>{money(ageing.get("d90"), False) or "0.00"}</td>
    <td>{money(ageing.get("older"), False) or "0.00"}</td>
    <td class="total">{money(due)}</td>
  </tr>
</table>
"""


def self_test() -> int:
    failed = 0
    invoices = [
        {"invoice_number": 1, "invoice_date": "2026-01-01", "customer": "Mr Godfrey Cupido", "amount": 759},
        {"invoice_number": 2, "invoice_date": "2026-02-01", "customer": "Godfrey Cupido", "amount": 759},
        {"invoice_number": 9, "invoice_date": "2026-02-01", "customer": "Amoroc Doors", "amount": 199},
    ]
    payments = [{"paid_on": "2026-01-15", "customer": "Mr Godfrey Cupido", "amount": -759, "note": "Payment"}]
    stmt = statement_on_invoice(invoices, payments, "Godfrey Cupido", as_at="2026-02-01")
    if stmt["total_due"] != 759 or len(stmt["lines"]) != 1:
        print("FAIL ledger", stmt)
        failed += 1
    elif stmt["lines"][0]["reference"] != "2" or stmt["lines"][0]["days"] != 0:
        print("FAIL first-line", stmt["lines"][0])
        failed += 1
    else:
        print("OK invoice-plus-statement")

    mashed = [
        ("Old - 7 Mbps down / 3.5 7 Mbps down / 3.5 Mbps Up - 1 399.00 399.00", "7 Mbps down / 3.5 Mbps Up"),
        ("NC Pop - 10 Mbps down / NC Pop - 10 Mbps down / 5 Mbps Up - 1 550.00 550.00", "NC Pop — 10 Mbps down / 5 Mbps Up"),
        ("WCC Tech - RSA Web WCC Tech - RSA Web Fiber Monthly 1 1,000.00 1,000.00", "WCC Tech - RSA Web Fibre Monthly"),
        ("Installation", "Installation"),
    ]
    clean_ok = True
    for raw, want in mashed:
        got = clean_description(raw)
        again = clean_description(got)
        if got != want or again != want:
            print("FAIL clean", raw, "->", got, "again", again, "want", want)
            failed += 1
            clean_ok = False
    if clean_ok:
        print("OK clean-description")

    who = "Mrs Marlene/Georg Van Eeden"
    marlene_inv = [
        (2373, "2024-03-17", 399),
        (2380, "2024-04-19", 399),
        (2388, "2024-05-18", 399),
        (2390, "2024-06-17", 399),
        (2398, "2024-07-17", 399),
        (2414, "2024-08-19", 399),
        (2423, "2024-09-17", 399),
        (2426, "2024-10-25", 399),
        (2443, "2024-11-17", 399),
        (2452, "2024-12-17", 399),
        (2460, "2025-01-25", 399),
        (2472, "2025-02-17", 399),
        (2487, "2025-03-17", 399),
        (2499, "2025-04-17", 399),
        (2533, "2025-05-17", 399),
        (2536, "2025-06-16", 399),
        (2551, "2025-07-15", 399),
        (2582, "2025-08-18", 399),
        (2601, "2025-09-18", 399),
        (2618, "2025-10-17", 399),
        (2639, "2025-11-17", 399),
        (2657, "2025-12-17", 399),
        (2675, "2026-01-17", 399),
        (2693, "2026-02-17", 399),
        (2712, "2026-03-17", 399),
        (2997, "2026-04-17", 399),
        (2998, "2026-05-17", 399),
        (2999, "2026-06-17", 439),
        (3000, "2026-07-17", 439),
        (3079, "2026-07-17", 329),
        (3104, "2026-08-20", 439),
        (3113, "2026-09-21", 439),
    ]
    marlene_inv = [
        {"invoice_number": n, "invoice_date": d, "customer": who, "amount": amt} for n, d, amt in marlene_inv
    ]
    marlene_pay = [{"paid_on": "2024-02-29", "customer": who, "amount": 1197, "note": "Balance Forward"}]
    for day, amounts in (
        ("2024-06-18", [-399, -399, -399, -399, -399, -5]),
        ("2024-10-15", [-394, -399, -399, -399, -399, -10]),
        ("2024-12-18", [-389, -399, -399]),
        ("2025-03-05", [-399, -399]),
        ("2025-07-18", [-399, -399, -202]),
    ):
        for amt in amounts:
            marlene_pay.append({"paid_on": day, "customer": who, "amount": amt, "note": "Payment"})
    stmt_m = statement_on_invoice(marlene_inv, marlene_pay, who, as_at="2026-10-04")
    line_sum = round(sum(l["amount"] for l in stmt_m["lines"]), 2)
    aged_sum = round(sum(stmt_m["ageing"].values()), 2)
    if stmt_m["total_due"] != 7070:
        print("FAIL marlene-due", stmt_m["total_due"], len(stmt_m["lines"]))
        failed += 1
    elif line_sum != 7070 or aged_sum != 7070:
        print("FAIL outstanding-sum", line_sum, aged_sum, stmt_m["ageing"])
        failed += 1
    elif stmt_m["ageing"] != {"current": 439.0, "d30": 0.0, "d60": 439.0, "d90": 768.0, "older": 5424.0}:
        print("FAIL ageing", stmt_m["ageing"])
        failed += 1
    elif aged_sum != stmt_m["total_due"]:
        print("FAIL ageing-not-to-current", aged_sum, stmt_m["total_due"])
        failed += 1
    elif not all(l.get("days", 0) >= 0 for l in stmt_m["lines"]):
        print("FAIL days", stmt_m["lines"])
        failed += 1
    elif (stmt_m.get("last_payment") or {}).get("amount") != 1000:
        print("FAIL last-payment", stmt_m.get("last_payment"))
        failed += 1
    elif fmt_date("2026-09-21") != "21/09/2026":
        print("FAIL date-fmt")
        failed += 1
    else:
        print("OK outstanding-days", len(stmt_m["lines"]), stmt_m["ageing"])

    # Same-day invoices are Current, 31-day-old unpaid is 31-60, matching QB 1369.
    amoroc = [
        {"invoice_number": 2568, "invoice_date": "2025-08-18", "customer": "Amoroc Doors", "amount": 199},
        {"invoice_number": 2569, "invoice_date": "2025-08-18", "customer": "Amoroc Doors", "amount": 699},
        {"invoice_number": 2586, "invoice_date": "2025-09-18", "customer": "Amoroc Doors", "amount": 199},
        {"invoice_number": 2587, "invoice_date": "2025-09-18", "customer": "Amoroc Doors", "amount": 699},
    ]
    amoroc_pay = [{"paid_on": "2025-09-01", "customer": "Amoroc Doors", "amount": -199, "note": "Payment"}]
    stmt_a = statement_on_invoice(amoroc, amoroc_pay, "Amoroc Doors", as_at="2025-09-18")
    if stmt_a["total_due"] != 1597 or stmt_a["ageing"]["current"] != 898 or stmt_a["ageing"]["d30"] != 0 or stmt_a["ageing"]["d60"] != 699:
        print("FAIL amoroc-ageing", stmt_a)
        failed += 1
    else:
        print("OK ageing-buckets")

    # Historical invoice must not list later bills.
    early = statement_on_invoice(invoices, payments, "Godfrey Cupido", as_at="2026-01-01")
    if early["total_due"] != 759 or any(l.get("reference") == "2" for l in early["lines"]):
        print("FAIL as-at-cutoff", early)
        failed += 1
    else:
        print("OK as-at-cutoff")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
