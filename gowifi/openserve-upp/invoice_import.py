#!/usr/bin/env python3
"""Import Openserve invoice CSVs from box mail for payment reconcile.

Read-only on mail. Does not print amounts to stdout in normal runs.
"""
from __future__ import annotations

import csv
import email
import hashlib
import io
import json
import os
import re
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
MAILBOXES = [
    Path("/home/user-data/mail/mailboxes/gowifi.co.za/kevin"),
    Path("/home/user-data/mail/mailboxes/gowifi.co.za/openserve"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
    invoice_number TEXT PRIMARY KEY,
    invoice_date TEXT,
    account_number TEXT,
    product_family TEXT,
    total REAL,
    vat REAL,
    source TEXT,
    filename TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL,
    service_number TEXT,
    end_customer TEXT,
    product TEXT,
    invoice_text TEXT,
    charge_amount REAL,
    currency TEXT,
    event_type TEXT,
    extra_kind TEXT,
    capacity TEXT,
    activation_date TEXT,
    charge_date TEXT,
    period_start TEXT,
    period_end TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_lines_dedup
    ON invoice_lines (
        invoice_number,
        COALESCE(service_number, ''),
        COALESCE(invoice_text, ''),
        COALESCE(charge_amount, 0),
        COALESCE(period_start, ''),
        COALESCE(charge_date, '')
    );
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    amount REAL,
    reference TEXT,
    source TEXT,
    matched_invoice TEXT,
    note TEXT
);
"""


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def _cell(row: dict, *names: str) -> str:
    want = {n.lower() for n in names}
    for key, val in row.items():
        if key and key.strip().lower() in want:
            return str(val or "").strip()
    return ""


def _ymd(raw: str | None) -> str | None:
    text = re.sub(r"\D", "", raw or "")
    if len(text) >= 8:
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return None


def extra_kind(text: str | None) -> str:
    t = (text or "").lower()
    if "ipv4" in t or "ipv6" in t or "dynamic ip" in t:
        return "ipv4"
    if "bridge" in t:
        return "bridge"
    if "penalty" in t or "notice period" in t:
        return "penalty"
    if "vat" in t:
        return "vat"
    if "rental" in t:
        return "rental"
    return "other"


def extra_label(kind: str) -> str:
    return {
        "ipv4": "IPv4",
        "bridge": "ONT bridge",
        "penalty": "notice penalty",
        "rental": "rental",
        "vat": "VAT",
    }.get(kind, kind)


def _money(raw: str | None) -> float | None:
    text = (raw or "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def ingest_csv_text(conn: sqlite3.Connection, text: str, filename: str, source: str) -> int:
    ensure_tables(conn)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return 0
    added = 0
    by_inv: dict[str, list[dict]] = {}
    for row in reader:
        inv = _cell(row, "Invoice Number")
        if not inv:
            continue
        by_inv.setdefault(inv, []).append(row)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for inv, rows in by_inv.items():
        account = _cell(rows[0], "Account Number")
        inv_date = _ymd(_cell(rows[0], "Invoice Date"))
        family = _cell(rows[0], "Product")
        total = 0.0
        vat = 0.0
        conn.execute("DELETE FROM invoice_lines WHERE invoice_number=?", (inv,))
        for row in rows:
            amount = _money(_cell(row, "Charge Amount")) or 0.0
            text_line = _cell(row, "Invoice Text")
            kind = extra_kind(text_line)
            total += amount
            if kind == "vat":
                vat += amount
            conn.execute(
                """INSERT OR IGNORE INTO invoice_lines
                   (invoice_number, service_number, end_customer, product, invoice_text,
                    charge_amount, currency, event_type, extra_kind, capacity,
                    activation_date, charge_date, period_start, period_end)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    inv,
                    _cell(row, "Service Name") or None,
                    _cell(row, "End Customer Name") or None,
                    _cell(row, "Product") or None,
                    text_line or None,
                    amount,
                    _cell(row, "Currency") or "ZAR",
                    _cell(row, "Event Type") or None,
                    kind,
                    _cell(row, "Capacity") or None,
                    _ymd(_cell(row, "Activation Date")),
                    _ymd(_cell(row, "Charge Date")),
                    _ymd(_cell(row, "Period Start Date")),
                    _ymd(_cell(row, "Period End Date")),
                ),
            )
            added += 1
        conn.execute(
            """INSERT INTO invoices
               (invoice_number, invoice_date, account_number, product_family,
                total, vat, source, filename, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(invoice_number) DO UPDATE SET
                 invoice_date=excluded.invoice_date,
                 account_number=excluded.account_number,
                 product_family=excluded.product_family,
                 total=excluded.total, vat=excluded.vat,
                 source=excluded.source, filename=excluded.filename,
                 updated_at=excluded.updated_at""",
            (inv, inv_date, account, family, total, vat, source, filename, now),
        )
    conn.commit()
    return added


def ingest_zip(conn: sqlite3.Connection, payload: bytes, filename: str, source: str) -> int:
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile:
        return 0
    n = 0
    for inner in zf.namelist():
        if not inner.lower().endswith(".csv"):
            continue
        raw = zf.read(inner)
        text = raw.decode("utf-8-sig", "replace")
        n += ingest_csv_text(conn, text, inner or filename, source)
    return n


def _iter_mail_zips():
    for root in MAILBOXES:
        if not root.exists():
            continue
        for dirpath, _dirs, files in os.walk(root):
            if "/new" not in dirpath and "/cur" not in dirpath:
                continue
            for name in files:
                if name.startswith("."):
                    continue
                path = Path(dirpath) / name
                try:
                    with path.open("rb") as fh:
                        msg = email.message_from_binary_file(fh)
                except OSError:
                    continue
                frm = (msg.get("From") or "").lower()
                subj = (msg.get("Subject") or "").lower()
                if "openserve" not in frm and "openserve" not in subj:
                    continue
                for part in msg.walk():
                    fname = part.get_filename() or ""
                    if not fname.lower().endswith(".zip"):
                        continue
                    if "invoice" not in fname.lower() and "inats" not in fname.lower():
                        if "csv" not in fname.lower():
                            continue
                    payload = part.get_payload(decode=True) or b""
                    if not payload.startswith(b"PK"):
                        continue
                    yield fname, payload


def ingest_mail(conn: sqlite3.Connection) -> dict:
    ensure_tables(conn)
    seen: set[str] = set()
    files = 0
    lines = 0
    for fname, payload in _iter_mail_zips():
        digest = hashlib.sha256(payload).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        files += 1
        lines += ingest_zip(conn, payload, fname, "mail")
    counts = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    return {"files": files, "lines_read": lines, "invoices": counts}


def extras_by_sn(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    ensure_tables(conn)
    out: dict[str, list[dict]] = {}
    rows = conn.execute(
        """SELECT service_number, extra_kind, MIN(activation_date), MIN(invoice_text)
           FROM invoice_lines
           WHERE extra_kind IN ('ipv4','bridge','penalty')
             AND service_number IS NOT NULL AND service_number != ''
           GROUP BY service_number, extra_kind
           ORDER BY service_number, extra_kind"""
    )
    for sn, kind, at, text in rows:
        out.setdefault(sn, []).append(
            {
                "kind": kind,
                "label": extra_label(kind),
                "added": at,
                "text": text,
            }
        )
    return out


def billed_speed_by_sn(conn: sqlite3.Connection) -> dict[str, dict]:
    ensure_tables(conn)
    out: dict[str, dict] = {}
    rows = conn.execute(
        """SELECT service_number, capacity, invoice_date, invoice_text
           FROM invoice_lines
           JOIN invoices USING (invoice_number)
           WHERE extra_kind='rental' AND service_number IS NOT NULL
             AND capacity IS NOT NULL AND capacity != ''
           ORDER BY invoice_date DESC"""
    )
    for sn, capacity, inv_date, text in rows:
        if sn in out:
            continue
        out[sn] = {"capacity": capacity, "invoice_date": inv_date, "text": text}
    return out


def invoices_for_export(conn: sqlite3.Connection) -> list[dict]:
    ensure_tables(conn)
    rows = conn.execute(
        """SELECT invoice_number, invoice_date, account_number, product_family,
                  total, vat FROM invoices ORDER BY invoice_date DESC, invoice_number DESC"""
    )
    out = []
    for inv, inv_date, account, family, total, vat in rows:
        sns = [
            r[0]
            for r in conn.execute(
                """SELECT DISTINCT service_number FROM invoice_lines
                   WHERE invoice_number=? AND service_number IS NOT NULL
                   ORDER BY service_number""",
                (inv,),
            )
        ]
        extras = [
            r[0]
            for r in conn.execute(
                """SELECT DISTINCT extra_kind FROM invoice_lines
                   WHERE invoice_number=? AND extra_kind IN ('ipv4','bridge','penalty')""",
                (inv,),
            )
        ]
        out.append(
            {
                "invoice_number": inv,
                "invoice_date": inv_date,
                "account_number": account,
                "product_family": family,
                "total": total,
                "vat": vat,
                "services": sns,
                "extras": extras,
            }
        )
    return out


def self_test() -> int:
    conn = sqlite3.connect(":memory:")
    csv_text = (
        "Account Number,Invoice Number,Invoice Date,Service Name,Invoice Text,"
        "Charge Amount,Product,Capacity,Activation Date,Charge Date,Period Start Date\n"
        "9400000004653,INATS0117669,20260131,B110033875,Rental - Openserve Webstream 500 Mbps,"
        "1000.00,Openserve Webstream,500,20251224,20260131,20260101\n"
        "9400000004653,INATS0117669,20260131,B110033875,Dynamic IPV4 Recurring,"
        "100.00,Openserve Webstream,,20251224,20260131,20260101\n"
        "9400000004653,INATS0117669,20260131,,VAT @ 15%,165.00,Openserve Webstream,,,,20260131,\n"
    )
    ingest_csv_text(conn, csv_text, "test.csv", "test")
    extras = extras_by_sn(conn)
    billed = billed_speed_by_sn(conn)
    invs = invoices_for_export(conn)
    failed = 0
    if not extras.get("B110033875") or extras["B110033875"][0]["kind"] != "ipv4":
        print("FAIL ipv4-extra", extras)
        failed += 1
    elif extras["B110033875"][0]["added"] != "2025-12-24":
        print("FAIL ipv4-date", extras)
        failed += 1
    else:
        print("OK ipv4-added")
    if not billed.get("B110033875") or billed["B110033875"]["capacity"] != "500":
        print("FAIL billed-speed", billed)
        failed += 1
    else:
        print("OK billed-speed")
    if len(invs) != 1 or abs((invs[0]["total"] or 0) - 1265.0) > 0.01:
        print("FAIL invoice-total", invs)
        failed += 1
    else:
        print("OK invoice-import")
    conn.close()
    return failed


def main() -> int:
    import sys

    if "--self-test" in sys.argv:
        return self_test()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    report = ingest_mail(conn)
    print(json.dumps({"ok": True, **report}))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
