#!/usr/bin/env python3
"""GoWiFi books ledger from QuickBooks FNB Account History + Netcash.

Recreates client (A/R), expense, loan, and Netcash clearing accounts.
Does not upload debit batches.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from company import COMPANY, GOWIFI_FNB

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS book_accounts (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    parent TEXT
);
CREATE TABLE IF NOT EXISTS book_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT NOT NULL,
    payee TEXT,
    memo TEXT,
    payment REAL,
    deposit REAL,
    amount REAL NOT NULL,
    balance REAL,
    qb_type TEXT,
    account TEXT NOT NULL,
    source TEXT,
    filename TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_book_entries_dedup
    ON book_entries (
        paid_on,
        COALESCE(payee, ''),
        COALESCE(memo, ''),
        COALESCE(payment, 0),
        COALESCE(deposit, 0),
        COALESCE(balance, 0),
        account
    );
"""

_KIND_RULES = (
    ("loan", ("loan account", "share capital", "long-term debt", "long term debt")),
    ("ar", ("accounts receivable", "a/r")),
    ("clearing", ("netcash",)),
    ("bank", ("fnb", "cash and cash equivalents")),
    ("income", ("revenue", "sales", "income")),
    ("equity", ("dividend", "share capital")),
    ("asset", ("stock asset", "uncategorised asset", "equipment")),
    ("expense", ()),
)


def kind_for_account(name: str, qb_type: str = "") -> str:
    blob = f"{name} {qb_type}".lower()
    if "loan account" in blob or "long-term debt" in blob or "long term debt" in blob:
        return "loan"
    for kind, needles in _KIND_RULES:
        if kind == "expense":
            continue
        if any(n in blob for n in needles):
            return kind
    if (qb_type or "").lower() in {"expense", "payment", "deposit", "transfer"}:
        if (qb_type or "").lower() == "payment":
            return "ar"
        if (qb_type or "").lower() == "expense":
            return "expense"
    return "expense"


def _money(raw) -> float:
    if raw is None or raw == "":
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).replace("\u00a0", " ").replace("R", "").replace(",", "").strip()
    if not text or not re.match(r"^-?\d+(\.\d+)?$", text):
        return 0.0
    return float(text)


def _iso_date(raw: str) -> str | None:
    text = (raw or "").strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if m:
        return text
    return None


def parse_qb_account_history(text: str, filename: str = "") -> dict:
    """QuickBooks Account History.xls/csv for FNB 62860060278."""
    reader = csv.reader(io.StringIO(text))
    rows_in = list(reader)
    title = ""
    header_idx = 0
    if rows_in and "date" not in [c.lower() for c in rows_in[0]]:
        title = ",".join(rows_in[0])
        header_idx = 1
    if header_idx >= len(rows_in):
        return {"title": title, "rows": [], "balance": None}
    header = [re.sub(r"\s+", " ", (c or "").strip()) for c in rows_in[header_idx]]
    low = [h.lower() for h in header]

    def col(*names):
        for name in names:
            if name in low:
                return low.index(name)
        return None

    i_date = col("date")
    i_payee = col("payee", "from/to")
    i_memo = col("memo", "bank description", "description")
    i_pay = col("payment", "spent")
    i_dep = col("deposit", "received")
    i_bal = col("balance")
    i_type = col("type")
    i_acc = col("account", "transaction posted")
    if i_date is None:
        return {"title": title, "rows": [], "balance": None}

    bal = None
    m = re.search(r"Bank Balance:\s*([\d,.]+)", title)
    if m:
        bal = _money(m.group(1))
    m = re.search(r"(62860060278)", title)
    number = m.group(1) if m else GOWIFI_FNB

    rows = []
    for rec in rows_in[header_idx + 1 :]:
        if not rec or not any(rec):
            continue
        def cell(idx):
            if idx is None or idx >= len(rec):
                return ""
            return rec[idx]

        paid_on = _iso_date(str(cell(i_date)))
        if not paid_on:
            continue
        payment = _money(cell(i_pay))
        deposit = _money(cell(i_dep))
        account = str(cell(i_acc) or "").strip()
        if account.lower().startswith("added to:") or account.lower().startswith("matched to:"):
            account = re.sub(r"^(Added to:|Matched to:)\s*", "", account, flags=re.I)
            account = re.sub(r"\s+\d{2}/\d{2}/\d{4}.*$", "", account).strip()
            account = re.sub(r"^(Expense|Payment|Transfer|Deposit):\s*", "", account).strip()
        payee = str(cell(i_payee) or "").strip()
        memo = str(cell(i_memo) or "").strip()
        qb_type = str(cell(i_type) or "").strip()
        rows.append(
            {
                "paid_on": paid_on,
                "payee": payee or None,
                "memo": memo or None,
                "payment": payment,
                "deposit": deposit,
                "amount": round(deposit - payment, 2),
                "balance": _money(cell(i_bal)) if cell(i_bal) != "" else None,
                "qb_type": qb_type or None,
                "account": account or "Uncategorised",
                "account_number": number,
                "account_name": COMPANY["bank_account_name"],
                "ours": 1,
                "source": "qb_fnb_history",
                "filename": filename,
                "kind": kind_for_account(account, qb_type),
            }
        )
    return {
        "title": title,
        "account_number": number,
        "balance": bal,
        "rows": rows,
    }


def parse_netcash_history(text: str, filename: str = "") -> dict:
    """Netcash Account History / merchant statement export."""
    reader = csv.reader(io.StringIO(text))
    rows_in = list(reader)
    header_idx = 0
    for i, rec in enumerate(rows_in[:8]):
        low = [c.lower().strip() for c in rec]
        if any(x in low for x in ("date", "action date", "transaction date")):
            header_idx = i
            break
    header = [re.sub(r"\s+", " ", (c or "").strip().lower()) for c in rows_in[header_idx]]

    def col(*names):
        for name in names:
            if name in header:
                return header.index(name)
        for i, h in enumerate(header):
            if any(name in h for name in names):
                return i
        return None

    i_date = col("date", "action date", "transaction date")
    i_ref = col("account reference", "reference", "account ref", "debtor")
    i_name = col("account name", "name", "client")
    i_amt = col("amount", "value")
    i_result = col("result", "status", "unpaid reason", "code")
    i_batch = col("batch id", "batch")
    if i_date is None:
        return {"rows": []}
    rows = []
    for rec in rows_in[header_idx + 1 :]:
        if not rec or not any(rec):
            continue
        def cell(idx):
            if idx is None or idx >= len(rec):
                return ""
            return rec[idx]

        paid_on = _iso_date(str(cell(i_date)))
        if not paid_on:
            continue
        rows.append(
            {
                "action_date": paid_on,
                "account_ref": str(cell(i_ref) or "").strip() or None,
                "account_name": str(cell(i_name) or "").strip() or None,
                "amount": _money(cell(i_amt)),
                "result": str(cell(i_result) or "").strip() or None,
                "batch_id": str(cell(i_batch) or "").strip() or None,
                "source": "netcash_history",
                "filename": filename,
            }
        )
    return {"rows": rows}


def ensure_ledger(conn: sqlite3.Connection) -> None:
    conn.executescript(LEDGER_SCHEMA)


def _upsert_accounts(conn: sqlite3.Connection, rows: list[dict]) -> None:
    seen = set()
    for row in rows:
        name = row.get("account")
        if not name or name in seen:
            continue
        seen.add(name)
        parent = name.rsplit(":", 1)[0] if ":" in name else None
        conn.execute(
            """INSERT OR IGNORE INTO book_accounts (name, kind, parent) VALUES (?,?,?)""",
            (name, row.get("kind") or kind_for_account(name, row.get("qb_type") or ""), parent),
        )
    # always keep the bank and loan shells
    for name, kind in (
        (f"FNB - {GOWIFI_FNB}", "bank"),
        ("Cash and cash equivalents:Netcash - Debit Orders", "clearing"),
        ("Share capital:Loan Account - Kevin Weaving 33%", "loan"),
        ("Share capital:Loan Account - Walter Esterhuizen 33%", "loan"),
        ("Long-term debt", "loan"),
        ("Accounts Receivable (A/R)", "ar"),
    ):
        conn.execute(
            "INSERT OR IGNORE INTO book_accounts (name, kind, parent) VALUES (?,?,?)",
            (name, kind, name.rsplit(":", 1)[0] if ":" in name else None),
        )


def ingest_qb_history(conn: sqlite3.Connection, text: str, filename: str = "") -> dict:
    ensure_ledger(conn)
    parsed = parse_qb_account_history(text, filename)
    _upsert_accounts(conn, parsed["rows"])
    n = 0
    for row in parsed["rows"]:
        cur = conn.execute(
            """INSERT OR IGNORE INTO book_entries
               (paid_on, payee, memo, payment, deposit, amount, balance, qb_type, account, source, filename)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["paid_on"],
                row.get("payee"),
                row.get("memo"),
                row.get("payment") or 0,
                row.get("deposit") or 0,
                row["amount"],
                row.get("balance"),
                row.get("qb_type"),
                row["account"],
                row.get("source"),
                filename,
            ),
        )
        n += cur.rowcount or 0
        conn.execute(
            """INSERT OR IGNORE INTO bank_tx
               (account_number, account_name, ours, paid_on, amount, balance, description, source, filename)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                row.get("account_number") or GOWIFI_FNB,
                row.get("account_name") or COMPANY["bank_account_name"],
                1,
                row["paid_on"],
                row["amount"],
                row.get("balance"),
                " | ".join(p for p in (row.get("payee"), row.get("memo"), row["account"]) if p),
                "qb_fnb_history",
                filename,
            ),
        )
    conn.commit()
    return {"filename": filename, "rows": len(parsed["rows"]), "inserted": n, "balance": parsed.get("balance")}


def ingest_netcash_history(conn: sqlite3.Connection, text: str, filename: str = "") -> dict:
    from netcash import SCHEMA as NC_SCHEMA

    conn.executescript(NC_SCHEMA)
    parsed = parse_netcash_history(text, filename)
    n = 0
    for row in parsed["rows"]:
        result = row.get("result") or "unknown"
        cur = conn.execute(
            """INSERT OR IGNORE INTO netcash_items
               (account_ref, service_number, amount, action_date, result, batch_id, source)
               VALUES (?,?,?,?,?,?,?)""",
            (
                row.get("account_ref") or row.get("account_name"),
                None,
                row.get("amount"),
                row.get("action_date"),
                result,
                row.get("batch_id"),
                "netcash_history",
            ),
        )
        n += cur.rowcount or 0
    conn.commit()
    return {"filename": filename, "rows": len(parsed["rows"]), "inserted": n}


def _sum(conn, sql, args=()) -> float:
    row = conn.execute(sql, args).fetchone()
    return float(row[0] or 0) if row else 0.0


def checksum_fnb_netcash(conn: sqlite3.Connection) -> dict:
    """FNB Netcash clearing vs Netcash history totals."""
    fnb_in = _sum(
        conn,
        """SELECT COALESCE(SUM(deposit),0) FROM book_entries
           WHERE account LIKE '%Netcash%' AND deposit>0""",
    )
    fnb_out = _sum(
        conn,
        """SELECT COALESCE(SUM(payment),0) FROM book_entries
           WHERE account LIKE '%Netcash%' AND payment>0""",
    )
    fnb_bounce_fees = _sum(
        conn,
        """SELECT COALESCE(SUM(payment),0) FROM book_entries
           WHERE memo LIKE '%Insufficient Fund%' OR memo LIKE '%Recoveries%'""",
    )
    nc_all = _sum(conn, "SELECT COALESCE(SUM(amount),0) FROM netcash_items")
    nc_unpaid = _sum(
        conn,
        """SELECT COALESCE(SUM(amount),0) FROM netcash_items
           WHERE lower(COALESCE(result,'')) LIKE '%unpaid%'
              OR lower(COALESCE(result,'')) LIKE '%unauth%'
              OR lower(COALESCE(result,'')) LIKE '%bounce%'
              OR lower(COALESCE(result,'')) LIKE '%reject%'""",
    )
    nc_paid = _sum(
        conn,
        """SELECT COALESCE(SUM(amount),0) FROM netcash_items
           WHERE lower(COALESCE(result,'')) LIKE '%paid%'
             AND lower(COALESCE(result,'')) NOT LIKE '%unpaid%'""",
    )
    return {
        "fnb_netcash_in": round(fnb_in, 2),
        "fnb_netcash_out": round(fnb_out, 2),
        "fnb_bounce_fees": round(fnb_bounce_fees, 2),
        "netcash_items": round(nc_all, 2),
        "netcash_paid": round(nc_paid, 2),
        "netcash_unpaid": round(nc_unpaid, 2),
        "match_paid": round(fnb_in - nc_paid, 2) if nc_paid else None,
        "note": (
            "Checksum FNB Netcash credits against Netcash paid collections. "
            "Unpaids stay on the client; bounce recoveries are FNB fees."
        ),
    }


def ledger_for_export(conn: sqlite3.Connection) -> dict:
    ensure_ledger(conn)
    accounts = []
    for name, kind, parent, n, spent, recvd in conn.execute(
        """SELECT a.name, a.kind, a.parent, COUNT(e.id),
                  COALESCE(SUM(e.payment),0), COALESCE(SUM(e.deposit),0)
           FROM book_accounts a
           LEFT JOIN book_entries e ON e.account=a.name
           GROUP BY a.name
           ORDER BY a.kind, a.name"""
    ):
        accounts.append(
            {
                "name": name,
                "kind": kind,
                "parent": parent,
                "rows": n,
                "spent": spent,
                "received": recvd,
                "net": round((recvd or 0) - (spent or 0), 2),
            }
        )
    clients = []
    for payee, n, recvd in conn.execute(
        """SELECT COALESCE(payee,'(no name)'), COUNT(*), COALESCE(SUM(deposit),0)
           FROM book_entries
           WHERE account LIKE '%Receivable%' OR qb_type='Payment'
           GROUP BY payee
           ORDER BY SUM(deposit) DESC"""
    ):
        clients.append({"name": payee, "payments": n, "received": recvd})
    expenses = [a for a in accounts if a["kind"] == "expense" and a["rows"]]
    loans = [a for a in accounts if a["kind"] == "loan"]
    bounces = []
    for rec in conn.execute(
        """SELECT paid_on, payee, memo, payment, deposit, account
           FROM book_entries
           WHERE memo LIKE '%Insufficient Fund%'
              OR memo LIKE '%Recoveries%'
              OR memo LIKE '%unpaid%'
              OR memo LIKE '%bounce%'
              OR memo LIKE '%HAVENGA REFUND%'
           ORDER BY paid_on DESC"""
    ):
        bounces.append(
            {
                "paid_on": rec[0],
                "payee": rec[1],
                "memo": rec[2],
                "amount": rec[3] or rec[4],
                "account": rec[5],
            }
        )
    bank = conn.execute(
        """SELECT COUNT(*), MIN(paid_on), MAX(paid_on),
                  COALESCE(SUM(payment),0), COALESCE(SUM(deposit),0)
           FROM book_entries"""
    ).fetchone()
    latest_bal = conn.execute(
        """SELECT balance FROM book_entries
           WHERE balance IS NOT NULL ORDER BY paid_on DESC, id DESC LIMIT 1"""
    ).fetchone()
    return {
        "bank": {
            "account_number": GOWIFI_FNB,
            "account_name": COMPANY["bank_account_name"],
            "rows": bank[0] if bank else 0,
            "from": bank[1] if bank else None,
            "to": bank[2] if bank else None,
            "spent": bank[3] if bank else 0,
            "received": bank[4] if bank else 0,
            "balance": latest_bal[0] if latest_bal else None,
        },
        "accounts": accounts,
        "clients": clients,
        "expenses": expenses,
        "loans": loans,
        "bounces": bounces,
        "checksum": checksum_fnb_netcash(conn),
    }


def self_test() -> int:
    failed = 0
    sample = Path("/tmp/fnb-account-history-sample.csv")
    text = sample.read_text() if sample.exists() else (
        "Date,Payee,Memo,Payment,Deposit,Balance,Type,Account\n"
        "01/10/2026,RSA Webb,RSAWEB NETCASH,2223.94,,5074.66,Expense,Dues and subscriptions:RSA Web ISP 2\n"
        "01/09/2026,,NETCASH in,,6967.28,11425.35,Transfer,Cash and cash equivalents:Netcash - Debit Orders\n"
        "14/09/2020,Kevin Weaving,Capex,,30000,30235,Deposit,Share capital:Loan Account - Kevin Weaving 33%\n"
        "06/07/2022,,Recoveries - Insufficient Fund - Netcash,270.65,,100,Transfer,Cash and cash equivalents:Netcash - Debit Orders\n"
        '30/09/2026,"Pearson, Philippa",,,329,6859.6,Payment,Accounts Receivable (A/R)\n'
    )
    parsed = parse_qb_account_history(text, "sample.csv")
    if len(parsed["rows"]) != 5 or parsed["rows"][0]["amount"] != -2223.94:
        print("FAIL parse", parsed)
        failed += 1
    else:
        print("OK qb-fnb-parse")
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """CREATE TABLE bank_tx (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT, account_name TEXT, ours INTEGER,
            paid_on TEXT, amount REAL, balance REAL, description TEXT, source TEXT, filename TEXT
        );
        CREATE UNIQUE INDEX idx_bank_tx_dedup ON bank_tx (
            COALESCE(account_number,''), paid_on, amount, COALESCE(description,'')
        );
        CREATE TABLE netcash_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_ref TEXT, service_number TEXT, amount REAL,
            action_date TEXT, result TEXT, batch_id TEXT, source TEXT
        );
        CREATE UNIQUE INDEX idx_netcash_items_dedup ON netcash_items (
            COALESCE(account_ref,''), COALESCE(action_date,''), COALESCE(amount,0),
            COALESCE(batch_id,''), COALESCE(result,''), COALESCE(source,'')
        );
        """
    )
    ingest_qb_history(conn, text, "sample.csv")
    out = ledger_for_export(conn)
    if out["bank"]["rows"] != 5:
        print("FAIL rows", out["bank"])
        failed += 1
    elif not any(c["name"] == "Pearson, Philippa" for c in out["clients"]):
        print("FAIL client", out["clients"])
        failed += 1
    elif not any(l["name"].startswith("Share capital:Loan Account - Kevin") for l in out["loans"]):
        print("FAIL loan", out["loans"])
        failed += 1
    elif not out["bounces"]:
        print("FAIL bounce", out["bounces"])
        failed += 1
    else:
        print("OK ledger-accounts")
    nc = parse_netcash_history(
        "Date,Account reference,Amount,Result,Batch ID\n"
        "01/09/2026,Wantling,439,Paid,2528146\n"
        "03/08/2026,GeoCorp,759,Unpaid,2498285\n"
    )
    if len(nc["rows"]) != 2 or nc["rows"][1]["result"] != "Unpaid":
        print("FAIL netcash-parse", nc)
        failed += 1
    else:
        print("OK netcash-history-parse")
    ingest_netcash_history(
        conn,
        "Date,Account reference,Amount,Result,Batch ID\n"
        "01/09/2026,Wantling,6967.28,Paid,2528146\n",
        "nc.csv",
    )
    chk = checksum_fnb_netcash(conn)
    if chk["fnb_netcash_in"] != 6967.28 or chk["match_paid"] != 0:
        print("FAIL checksum", chk)
        failed += 1
    else:
        print("OK fnb-netcash-checksum")
    conn.close()
    return failed


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        path = Path(sys.argv[2])
        db = sqlite3.connect(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
        from books import ensure_tables

        ensure_tables(db)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        print(ingest_qb_history(db, text, path.name))
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "ingest-netcash":
        path = Path(sys.argv[2])
        db = sqlite3.connect(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        print(ingest_netcash_history(db, text, path.name))
        print(checksum_fnb_netcash(db))
        raise SystemExit(0)
    raise SystemExit(self_test())
