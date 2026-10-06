#!/usr/bin/env python3
"""FNB + Netcash transaction tables. Allocate what we can; leftover needs recon."""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from billing import (
    CLIENTS,
    DO_CLIENTS,
    KEVIN_LOAN_ACCOUNT,
    PENDING_DO,
    canon_key,
    client_row,
    display_name,
    is_offset,
)
from invoice_canned import parse_day

DATA_DIR = Path(__file__).resolve().parent / "data"
FNB_XLS = DATA_DIR / "Account_History_FNB.xls"
NETCASH_XLS = DATA_DIR / "Account_History_Netcash.xls"

SCHEMA = """
CREATE TABLE IF NOT EXISTS fnb_tx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    ref TEXT,
    payee TEXT,
    memo TEXT,
    payment REAL,
    deposit REAL,
    amount REAL,
    balance REAL,
    qb_type TEXT,
    account TEXT,
    bank_status TEXT,
    alloc_kind TEXT,
    alloc_to TEXT,
    alloc_key TEXT,
    result TEXT,
    source TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fnb_tx_dedup
    ON fnb_tx (
        COALESCE(paid_on,''), COALESCE(payee,''), COALESCE(memo,''),
        COALESCE(payment,0), COALESCE(deposit,0), COALESCE(account,''),
        COALESCE(balance,0)
    );
CREATE TABLE IF NOT EXISTS netcash_tx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    ref TEXT,
    payee TEXT,
    memo TEXT,
    payment REAL,
    deposit REAL,
    amount REAL,
    balance REAL,
    qb_type TEXT,
    account TEXT,
    bank_status TEXT,
    alloc_kind TEXT,
    alloc_to TEXT,
    alloc_key TEXT,
    result TEXT,
    batch_id TEXT,
    account_ref TEXT,
    tracking_ref TEXT,
    extra_ref TEXT,
    unpaid_amount REAL,
    source TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_netcash_tx_dedup
    ON netcash_tx (
        COALESCE(paid_on,''), COALESCE(payee,''), COALESCE(memo,''),
        COALESCE(payment,0), COALESCE(deposit,0), COALESCE(account,''),
        COALESCE(batch_id,''), COALESCE(result,'')
    );
"""

# Paid / unpaid per batch. Only what Netcash named. 2571994 has no unpaids.
BATCH_UNPAID: dict[str, set[str]] = {}
BATCH_ITEM_REFS = {
    ("2571994", "bing noordhoek"): {
        "account_ref": "1311699279",
        "tracking_ref": "198765",
        "extra_ref": "429604040",
    },
    ("2571994", "g cupido"): {
        "account_ref": "1763102147",
        "tracking_ref": "4338169411",
        "extra_ref": None,
    },
}

# Debit masterfile · G Cupido Fibre 50-25 · account 1763102147.
# Kevin screenshot 6 Oct 2026. 5 Oct is Processed. Do not invent unpaid.
NAMED_DO = [
    {
        "paid_on": "2026-10-05",
        "customer": "Bing Noordhoek Fibre",
        "amount": 599.00,
        "result": "paid",
        "batch_id": "2571994",
        "account_ref": "1311699279",
        "tracking_ref": "198765",
        "extra_ref": "429604040",
        "service": "Same day debit order",
    },
    {
        "paid_on": "2026-10-05",
        "customer": "G Cupido",
        "amount": 759.00,
        "result": "paid",
        "batch_id": "2571994",
        "account_ref": "1763102147",
        "tracking_ref": "4338169411",
        "service": "Same day debit order",
    },
    {
        "paid_on": "2026-09-01",
        "customer": "G Cupido",
        "amount": 759.00,
        "result": "unpaid",
        "batch_id": "20260901",
        "account_ref": "1763102147",
        "tracking_ref": "4296190922",
        "service": "Two day debit order",
    },
    {
        "paid_on": "2026-08-03",
        "customer": "G Cupido",
        "amount": 759.00,
        "result": "unpaid",
        "batch_id": "20260803",
        "account_ref": "1763102147",
        "tracking_ref": "4230985580",
        "service": "Two day debit order",
    },
    {
        "paid_on": "2026-07-01",
        "customer": "G Cupido",
        "amount": 759.00,
        "result": "paid",
        "batch_id": "20260701",
        "account_ref": "1763102147",
        "tracking_ref": "417420631",
        "service": "Two day debit order",
    },
    {
        "paid_on": "2026-06-01",
        "customer": "G Cupido",
        "amount": 759.00,
        "result": "paid",
        "batch_id": "20260601",
        "account_ref": "1763102147",
        "tracking_ref": "411331048",
        "service": "Two day debit order",
    },
    {
        "paid_on": "2026-05-04",
        "customer": "G Cupido",
        "amount": 759.00,
        "result": "unpaid",
        "batch_id": "20260504",
        "account_ref": "1763102147",
        "tracking_ref": "404830634",
        "service": "Two day debit order",
    },
]


def named_unpaid_months() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in NAMED_DO:
        if (row.get("result") or "").lower() != "unpaid":
            continue
        out.setdefault(canon_key(row["customer"]), set()).add((row.get("paid_on") or "")[:7])
    return out


def _money(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).replace("R", "").replace(",", "").replace("\xa0", "").strip()
    try:
        return round(float(text), 2)
    except ValueError:
        return 0.0


def _xls_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        import xlrd
    except ImportError:
        return []
    sh = xlrd.open_workbook(str(path)).sheet_by_index(0)
    header = 1
    for r in range(min(5, sh.nrows)):
        vals = [str(sh.cell_value(r, c)).strip().lower() for c in range(min(sh.ncols, 12))]
        if "date" in vals and ("payee" in vals or "deposit" in vals):
            header = r
            break
    cols = {str(sh.cell_value(header, c)).strip().lower(): c for c in range(sh.ncols)}

    def cell(row, *names):
        for n in names:
            if n in cols:
                return sh.cell_value(row, cols[n])
        return ""

    out = []
    for r in range(header + 1, sh.nrows):
        day = parse_day(cell(r, "date"))
        payee = str(cell(r, "payee") or "").strip()
        memo = str(cell(r, "memo") or "").strip()
        payment = _money(cell(r, "payment"))
        deposit = _money(cell(r, "deposit"))
        if not day and not payee and not memo and not payment and not deposit:
            continue
        out.append(
            {
                "paid_on": day.isoformat() if day else "",
                "ref": str(cell(r, "ref no.", "ref no", "ref") or "").strip(),
                "payee": payee,
                "memo": memo,
                "payment": payment,
                "deposit": deposit,
                "amount": round(deposit - payment, 2),
                "balance": _money(cell(r, "balance")),
                "qb_type": str(cell(r, "type") or "").strip(),
                "account": str(cell(r, "account") or "").strip(),
                "bank_status": str(cell(r, "reconciliation status") or "").strip(),
            }
        )
    return out


def _client_for(payee: str, memo: str = "") -> tuple[str, str] | None:
    blob = f"{payee} {memo}".strip()
    if not blob:
        return None
    row = client_row(blob)
    if row:
        return row["name"], canon_key(row["name"])
    key = canon_key(blob)
    if not key:
        return None
    for item in CLIENTS:
        if canon_key(item["name"]) == key:
            return item["name"], key
    name = display_name(payee) if payee else ""
    if name and canon_key(name) == key and key != canon_key(""):
        # display_name falls back to raw if unknown — only accept known keys
        if any(canon_key(item["name"]) == key for item in CLIENTS):
            return name, key
        # cancelled / deleted names still allocate
        if "deleted" in blob.lower() or key in {
            "irene steyn",
            "terence pereira",
            "james such",
            "geran sukhraj",
            "leon dykman",
            "aljo van",
        }:
            return display_name(payee) or payee, key
    return None


def _fnb_alloc(row: dict) -> dict:
    payee = row.get("payee") or ""
    memo = row.get("memo") or ""
    account = (row.get("account") or "").lower()
    qb = (row.get("qb_type") or "").lower()
    blob = f"{payee} {memo} {account}".lower()
    client = _client_for(payee, memo)
    if client and is_offset(client_row(client[0])):
        return {
            "alloc_kind": "loan",
            "alloc_to": (client_row(client[0]) or {}).get("loan_account") or KEVIN_LOAN_ACCOUNT,
            "alloc_key": client[1],
            "result": "allocated",
        }
    if client and (row.get("deposit") or 0) > 0.004:
        name, key = client
        deposit = abs(float(row.get("deposit") or 0))
        book = client_row(name)
        # Tiny named deposit on a D/O client is the collection cost, not client money.
        if deposit < 10 and book and book.get("method") == "debit-order":
            return {
                "alloc_kind": "fee",
                "alloc_to": "D/O collection cost",
                "alloc_key": "",
                "result": "allocated",
            }
        return {
            "alloc_kind": "client_paid",
            "alloc_to": name,
            "alloc_key": key,
            "result": "paid",
        }
    if client and ("insufficient" in blob or "bounce" in blob or "recoveries" in blob):
        name, key = client
        return {
            "alloc_kind": "client_unpaid",
            "alloc_to": name,
            "alloc_key": key,
            "result": "unpaid",
        }
    if "accounts receivable" in account or account.startswith("a/r"):
        if client:
            name, key = client
            kind = "client_paid" if (row.get("deposit") or 0) > 0.004 else "client_unpaid"
            return {
                "alloc_kind": kind,
                "alloc_to": name,
                "alloc_key": key,
                "result": "paid" if kind == "client_paid" else "unpaid",
            }
        return {"alloc_kind": "unallocated", "alloc_to": payee or memo, "alloc_key": "", "result": "need-recon"}
    if "loan" in account or "share capital" in account:
        return {"alloc_kind": "loan", "alloc_to": row.get("account") or payee, "alloc_key": "", "result": "allocated"}
    if "netcash" in blob:
        return {"alloc_kind": "clearing", "alloc_to": "Netcash", "alloc_key": "", "result": "allocated"}
    if qb == "expense" or any(
        w in account
        for w in (
            "bank charge",
            "dues",
            "subscription",
            "openserve",
            "rsa web",
            "advert",
            "insurance",
            "fuel",
            "repair",
            "telephone",
            "office",
            "uncategoris",
        )
    ):
        return {
            "alloc_kind": "expense",
            "alloc_to": row.get("account") or payee or memo,
            "alloc_key": "",
            "result": "allocated",
        }
    if qb in {"transfer", "deposit"} and ("fnb" in account or "cash" in account):
        return {"alloc_kind": "clearing", "alloc_to": row.get("account") or "Bank", "alloc_key": "", "result": "allocated"}
    if qb == "transfer":
        return {"alloc_kind": "clearing", "alloc_to": row.get("account") or payee, "alloc_key": "", "result": "allocated"}
    if "revenue" in account or qb == "deposit":
        return {"alloc_kind": "income", "alloc_to": row.get("account") or payee or memo, "alloc_key": "", "result": "allocated"}
    return {"alloc_kind": "unallocated", "alloc_to": payee or memo or row.get("account"), "alloc_key": "", "result": "need-recon"}


def _netcash_alloc(row: dict) -> dict:
    payee = row.get("payee") or ""
    memo = (row.get("memo") or "").lower()
    account = (row.get("account") or "").lower()
    qb = (row.get("qb_type") or "").lower()
    client = _client_for(payee, row.get("memo") or "")
    if "interest" in memo or "interest" in account:
        return {"alloc_kind": "expense", "alloc_to": "Netcash interest", "alloc_key": "", "result": "allocated"}
    if "service fee" in memo or ("fee" in account and "insufficient" not in memo):
        return {"alloc_kind": "fee", "alloc_to": "Netcash fee", "alloc_key": "", "result": "allocated"}
    if "recoveries" in memo:
        return {"alloc_kind": "clearing", "alloc_to": "D/O recoveries", "alloc_key": "", "result": "unpaid"}
    if "insufficient" in memo or "bounce" in memo:
        if client:
            name, key = client
            return {
                "alloc_kind": "client_unpaid",
                "alloc_to": name,
                "alloc_key": key,
                "result": "unpaid",
            }
        return {"alloc_kind": "clearing", "alloc_to": "D/O unpaid", "alloc_key": "", "result": "unpaid"}
    if "fnb" in account or "62860060278" in account or memo.startswith("netcash"):
        return {"alloc_kind": "clearing", "alloc_to": "FNB settlement", "alloc_key": "", "result": "allocated"}
    if client:
        name, key = client
        paid = (row.get("deposit") or 0) > 0.004 or "receivable" in account or qb == "payment"
        if paid or (row.get("payment") or 0) > 0.004 and "receivable" in account:
            return {
                "alloc_kind": "client_paid",
                "alloc_to": name,
                "alloc_key": key,
                "result": "paid",
            }
        if (row.get("payment") or 0) > 0.004 and "receivable" in account:
            return {
                "alloc_kind": "client_paid",
                "alloc_to": name,
                "alloc_key": key,
                "result": "paid",
            }
        # Named D/O against A/R is a successful collection (amount on payment column in QB Netcash register)
        if payee:
            return {
                "alloc_kind": "client_paid",
                "alloc_to": name,
                "alloc_key": key,
                "result": "paid",
            }
    if qb == "transfer" or "cash and cash" in account:
        return {"alloc_kind": "clearing", "alloc_to": "FNB settlement", "alloc_key": "", "result": "allocated"}
    return {"alloc_kind": "unallocated", "alloc_to": payee or row.get("memo") or row.get("account"), "alloc_key": "", "result": "need-recon"}


def ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.execute("DROP INDEX IF EXISTS idx_fnb_tx_dedup")
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_fnb_tx_dedup
           ON fnb_tx (
               COALESCE(paid_on,''), COALESCE(payee,''), COALESCE(memo,''),
               COALESCE(payment,0), COALESCE(deposit,0), COALESCE(account,''),
               COALESCE(balance,0)
           )"""
    )
    have = {r[1] for r in conn.execute("PRAGMA table_info(netcash_tx)")}
    for col, typ in (
        ("account_ref", "TEXT"),
        ("tracking_ref", "TEXT"),
        ("extra_ref", "TEXT"),
        ("unpaid_amount", "REAL"),
    ):
        if col not in have:
            conn.execute(f"ALTER TABLE netcash_tx ADD COLUMN {col} {typ}")


def ingest(conn: sqlite3.Connection) -> dict:
    ensure(conn)
    conn.execute("DELETE FROM fnb_tx")
    conn.execute("DELETE FROM netcash_tx")
    fnb_n = 0
    for row in _xls_rows(FNB_XLS):
        alloc = _fnb_alloc(row)
        conn.execute(
            """INSERT OR IGNORE INTO fnb_tx
               (paid_on, ref, payee, memo, payment, deposit, amount, balance, qb_type,
                account, bank_status, alloc_kind, alloc_to, alloc_key, result, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["paid_on"],
                row["ref"],
                row["payee"],
                row["memo"],
                row["payment"],
                row["deposit"],
                row["amount"],
                row["balance"],
                row["qb_type"],
                row["account"],
                row["bank_status"],
                alloc["alloc_kind"],
                alloc["alloc_to"],
                alloc["alloc_key"],
                alloc["result"],
                "fnb-xls",
            ),
        )
        fnb_n += 1
    nc_n = 0
    for row in _xls_rows(NETCASH_XLS):
        alloc = _netcash_alloc(row)
        xls_batch = (
            str(row.get("paid_on") or "").replace("-", "")
            if alloc.get("alloc_key") and row.get("paid_on")
            else None
        )
        conn.execute(
            """INSERT OR IGNORE INTO netcash_tx
               (paid_on, ref, payee, memo, payment, deposit, amount, balance, qb_type,
                account, bank_status, alloc_kind, alloc_to, alloc_key, result, batch_id,
                account_ref, tracking_ref, extra_ref, unpaid_amount, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["paid_on"],
                row["ref"],
                row["payee"],
                row["memo"],
                row["payment"],
                row["deposit"],
                row["amount"],
                row["balance"],
                row["qb_type"],
                row["account"],
                row["bank_status"],
                alloc["alloc_kind"],
                alloc["alloc_to"],
                alloc["alloc_key"],
                alloc["result"],
                xls_batch,
                alloc.get("alloc_key") and str(row.get("paid_on") or "").replace("-", "") or None,
                None,
                None,
                0 if alloc["result"] == "paid" else abs(_money(row.get("payment")) or _money(row.get("amount"))),
                "netcash-xls",
            ),
        )
        nc_n += 1
    named_n = _ingest_named_do(conn)
    nc_n += named_n
    conn.commit()
    return {"fnb": fnb_n, "netcash": nc_n, "named_do": named_n, "oct5": 0, **summary(conn)}


def _ingest_named_do(conn: sqlite3.Connection) -> int:
    """Named Netcash debit-masterfile rows. Beats invented batch unpaid."""
    n = 0
    for row in NAMED_DO:
        key = canon_key(row["customer"])
        amt = abs(float(row["amount"]))
        unpaid = (row.get("result") or "").lower() == "unpaid"
        name = display_name(row["customer"]) or row["customer"]
        exists = conn.execute(
            """SELECT 1 FROM netcash_tx
               WHERE paid_on=? AND alloc_key=? AND ABS(amount)>=? - 0.02
                 AND result=? AND COALESCE(batch_id,'')=?""",
            (row["paid_on"], key, amt, row["result"], row.get("batch_id") or ""),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT OR IGNORE INTO netcash_tx
               (paid_on, ref, payee, memo, payment, deposit, amount, balance, qb_type,
                account, bank_status, alloc_kind, alloc_to, alloc_key, result, batch_id,
                account_ref, tracking_ref, extra_ref, unpaid_amount, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["paid_on"],
                row.get("account_ref") or row.get("batch_id"),
                name,
                f"{row.get('service') or 'Debit order'} · {row.get('tracking_ref') or ''} · "
                f"{'Unpaid' if unpaid else 'Processed'}".strip(" ·"),
                amt if unpaid else 0,
                0 if unpaid else amt,
                amt,
                None,
                "Payment",
                "Accounts Receivable (A/R)",
                "Unpaid" if unpaid else "Collected",
                "client_unpaid" if unpaid else "client_paid",
                name,
                key,
                row["result"],
                row.get("batch_id"),
                row.get("account_ref"),
                row.get("tracking_ref"),
                row.get("extra_ref"),
                amt if unpaid else 0,
                "netcash-masterfile",
            ),
        )
        n += 1
    return n


def summary(conn: sqlite3.Connection) -> dict:
    def counts(table: str) -> dict:
        out = {"rows": 0, "allocated": 0, "unallocated": 0, "client_paid": 0, "client_unpaid": 0}
        try:
            rows = conn.execute(
                f"SELECT alloc_kind, COUNT(*) FROM {table} GROUP BY alloc_kind"
            ).fetchall()
        except sqlite3.OperationalError:
            return out
        for kind, n in rows:
            out["rows"] += n
            if kind == "unallocated":
                out["unallocated"] += n
            else:
                out["allocated"] += n
            if kind == "client_paid":
                out["client_paid"] += n
            if kind == "client_unpaid":
                out["client_unpaid"] += n
        return out

    return {"fnb_alloc": counts("fnb_tx"), "netcash_alloc": counts("netcash_tx")}


def batch_items(conn: sqlite3.Connection) -> list[dict]:
    """Named client paid / unpaid per batch. No synth. Newest batch at the top."""
    try:
        rows = conn.execute(
            """SELECT paid_on, batch_id, alloc_to, payee, amount, unpaid_amount,
                      result, account_ref, tracking_ref, extra_ref, ref, alloc_key, source
               FROM netcash_tx
               WHERE alloc_kind IN ('client_paid','client_unpaid')
                 AND COALESCE(alloc_key,'') != ''
                 AND source IN ('netcash-masterfile','netcash-xls','netcash-batch')
               ORDER BY paid_on DESC, CASE result WHEN 'unpaid' THEN 0 ELSE 1 END, alloc_to"""
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    out = []
    for rec in rows:
        out.append(
            {
                "paid_on": rec[0],
                "batch_id": rec[1],
                "account_name": rec[2] or rec[3],
                "payee": rec[3],
                "amount": abs(_money(rec[4])),
                "unpaid_amount": _money(rec[5]),
                "result": rec[6] or "paid",
                "account_ref": rec[7] or rec[10],
                "tracking_ref": rec[8],
                "extra_ref": rec[9],
                "alloc_key": rec[11],
                "source": rec[12] if len(rec) > 12 else "",
            }
        )
    return out


def leftover(conn: sqlite3.Connection, limit: int = 80) -> list[dict]:
    out = []
    for table, book in (("fnb_tx", "FNB"), ("netcash_tx", "Netcash")):
        try:
            rows = conn.execute(
                f"""SELECT paid_on, payee, memo, amount, account, qb_type
                    FROM {table} WHERE alloc_kind='unallocated'
                    ORDER BY paid_on DESC, id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for rec in rows:
            out.append(
                {
                    "book": book,
                    "date": rec[0],
                    "payee": rec[1],
                    "memo": rec[2],
                    "amount": rec[3],
                    "account": rec[4],
                    "type": rec[5],
                }
            )
    return out


def client_receipts(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for table, method, source in (
        ("fnb_tx", "eft", "fnb-alloc"),
        ("netcash_tx", "do", "netcash-alloc"),
    ):
        try:
            rows = conn.execute(
                f"""SELECT paid_on, alloc_to, amount, deposit, payment
                    FROM {table} WHERE alloc_kind='client_paid' ORDER BY paid_on, id"""
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for rec in rows:
            amt = abs(_money(rec[2]) or _money(rec[3]) or _money(rec[4]))
            if amt <= 0.004:
                continue
            out.append(
                {
                    "paid_on": rec[0],
                    "customer": rec[1],
                    "amount": -amt,
                    "note": "EFT" if method == "eft" else "Debit order",
                    "source": source,
                    "method": method,
                }
            )
    return out


def mirror_do_runs(conn: sqlite3.Connection) -> int:
    """Do not invent Netcash rows from synth D/O. Table is named / seeded only."""
    ensure(conn)
    return 0


def client_unpaid(conn: sqlite3.Connection) -> list[dict]:
    out = []
    try:
        rows = conn.execute(
            """SELECT paid_on, alloc_to, amount, payment, deposit
               FROM netcash_tx WHERE alloc_kind='client_unpaid' ORDER BY paid_on"""
        ).fetchall()
    except sqlite3.OperationalError:
        return out
    for rec in rows:
        amt = abs(_money(rec[2]) or _money(rec[3]) or _money(rec[4]))
        out.append(
            {
                "action_date": rec[0],
                "customer": rec[1],
                "amount": amt,
                "result": "unpaid",
                "note": "Debit order unpaid",
                "source": "netcash-alloc",
            }
        )
    return out


def self_test() -> int:
    failed = 0
    conn = sqlite3.connect(":memory:")
    pack = ingest(conn)
    fnb = pack["fnb_alloc"]
    nc = pack["netcash_alloc"]
    left = leftover(conn)
    if fnb["rows"] < 700:
        print("FAIL fnb-rows", fnb)
        failed += 1
    elif nc["rows"] < 100:
        print("FAIL netcash-rows", nc)
        failed += 1
    elif fnb["unallocated"] > 80:
        print("FAIL fnb-leftover-too-big", fnb["unallocated"], left[:8])
        failed += 1
    elif nc["unallocated"] > 20:
        print("FAIL netcash-leftover-too-big", nc["unallocated"])
        failed += 1
    elif fnb["client_paid"] < 200:
        print("FAIL fnb-client-paid", fnb)
        failed += 1
    else:
        bing = conn.execute(
            """SELECT result, account_ref, tracking_ref, extra_ref, unpaid_amount
               FROM netcash_tx
               WHERE batch_id='2571994' AND alloc_key='bing noordhoek'"""
        ).fetchone()
        cup = conn.execute(
            """SELECT result, unpaid_amount, tracking_ref, account_ref, source FROM netcash_tx
               WHERE batch_id='2571994' AND alloc_key='g cupido'"""
        ).fetchone()
        cup_hist = {
            (r[0], r[1]): r[2]
            for r in conn.execute(
                """SELECT paid_on, result, tracking_ref FROM netcash_tx
                   WHERE alloc_key='g cupido' AND source='netcash-masterfile'"""
            )
        }
        n_batches = conn.execute(
            "SELECT COUNT(DISTINCT batch_id) FROM netcash_tx WHERE COALESCE(batch_id,'')!=''"
        ).fetchone()[0]
        oct_unpaid = conn.execute(
            """SELECT alloc_to FROM netcash_tx
               WHERE batch_id='2571994' AND result='unpaid'"""
        ).fetchall()
        if not bing or bing[0] != "paid" or bing[1] != "1311699279" or bing[4]:
            print("FAIL bing-batch-paid", bing)
            failed += 1
        elif not cup or cup[0] != "paid" or cup[1] or cup[2] != "4338169411":
            print("FAIL cupido-oct-must-be-processed", cup)
            failed += 1
        elif oct_unpaid:
            print("FAIL oct5-has-unpaid", oct_unpaid)
            failed += 1
        elif cup_hist.get(("2026-05-04", "unpaid")) != "404830634":
            print("FAIL cupido-may-unpaid", cup_hist)
            failed += 1
        elif cup_hist.get(("2026-08-03", "unpaid")) != "4230985580":
            print("FAIL cupido-aug-unpaid", cup_hist)
            failed += 1
        elif cup_hist.get(("2026-09-01", "unpaid")) != "4296190922":
            print("FAIL cupido-sep-unpaid", cup_hist)
            failed += 1
        elif n_batches < 6:
            print("FAIL netcash-history-batches", n_batches)
            failed += 1
        else:
            print(
                "OK recon",
                "fnb",
                fnb["rows"],
                "alloc",
                fnb["allocated"],
                "left",
                fnb["unallocated"],
                "nc",
                nc["rows"],
                "left",
                nc["unallocated"],
                "oct5",
                pack.get("oct5"),
            )
            print("OK bing-netcash-paid", bing[1], bing[2], bing[3])
            print("OK cupido-oct-processed", cup[2], cup[3])
            kinds = Counter()
            for rec in conn.execute("SELECT alloc_kind FROM fnb_tx"):
                kinds[rec[0]] += 1
            print("OK fnb-kinds", dict(kinds))
            fee275 = conn.execute(
                """SELECT alloc_kind, alloc_to FROM fnb_tx
                   WHERE paid_on='2026-04-10' AND ABS(deposit-2.75)<0.01"""
            ).fetchone()
            if not fee275 or fee275[0] != "fee":
                print("FAIL cupido-2.75-must-be-do-fee", fee275)
                failed += 1
            else:
                print("OK cupido-2.75-do-fee")
    sample = _fnb_alloc(
        {
            "payee": "Patriot SA / Paltco",
            "memo": "Contribution",
            "account": "Accounts Receivable (A/R)",
            "deposit": 1399,
            "payment": 0,
            "qb_type": "Payment",
        }
    )
    if sample.get("alloc_kind") != "loan" or "Kevin" not in (sample.get("alloc_to") or ""):
        print("FAIL paltco-to-kw-loan", sample)
        failed += 1
    else:
        print("OK paltco-fnb-to-kw-loan")
    conn.close()
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
