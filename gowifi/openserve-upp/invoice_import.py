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
from datetime import date, datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
MAIL_ROOT = Path(os.environ.get("MAIL_ROOT", "/home/user-data/mail/mailboxes"))
COLLECT_DIR = Path(os.environ.get("OPENSERVE_MAIL_DIR", "/root/gowifi-upp/openserve-mail"))
MAILBOXES = [
    Path("/home/user-data/mail/mailboxes/gowifi.co.za/kevin"),
    Path("/home/user-data/mail/mailboxes/gowifi.co.za/openserve"),
    Path("/home/user-data/mail/mailboxes/gowifi.co.za/accounts"),
    Path("/home/user-data/mail/mailboxes/gowifi.co.za/robby"),
    Path("/home/user-data/mail/mailboxes/go-wifi.co.za/accounts"),
    Path("/home/user-data/mail/mailboxes/go-wifi.co.za/kevin"),
]
FIRST_FIBRE_MONTH = "2024-09"
INVOICE_FAMILIES = (
    ("webstream", "Webstream", "9400000004759"),
    ("office_connect", "Office Connect", "9400000004657"),
)
STATEMENT_ACCOUNTS = (
    "9400000004653",
    "9400000004655",
    "9400000004657",
    "9400000004759",
    "9400000004815",
)

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
CREATE TABLE IF NOT EXISTS mail_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT,
    mailbox TEXT,
    sent_on TEXT,
    kind TEXT,
    subject TEXT,
    account_number TEXT,
    invoice_number TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mail_items_dedup
    ON mail_items (COALESCE(message_id, ''), COALESCE(sent_on, ''), COALESCE(subject, ''));
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


def mailbox_roots() -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    if MAIL_ROOT.exists():
        for domain in sorted(MAIL_ROOT.iterdir()):
            if not domain.is_dir():
                continue
            for user in sorted(domain.iterdir()):
                if user.is_dir() and str(user) not in seen:
                    found.append(user)
                    seen.add(str(user))
    for extra in MAILBOXES:
        if extra.exists() and str(extra) not in seen:
            found.append(extra)
            seen.add(str(extra))
    return found


def _openserve_hit(msg) -> bool:
    frm = (msg.get("From") or "").lower()
    subj = (msg.get("Subject") or "").lower()
    atts = " ".join((part.get_filename() or "") for part in msg.walk()).lower()
    blob = f"{frm} {subj} {atts}"
    return any(
        token in blob
        for token in ("openserve", "nbcustnb@", "inats", "brinats", "940000000")
    )


def _keep_attachment(fname: str) -> bool:
    low = (fname or "").lower()
    if not low or low.endswith((".png", ".jpg", ".jpeg", ".gif", ".tiff", ".tif")):
        return False
    if "inats" in low or "brinats" in low or "detailed" in low:
        return True
    if re.match(r"cn\d", low) or "credit" in low:
        return True
    if low.endswith(".csv"):
        return True
    if low.endswith(".zip") and ("invoice" in low or "csv" in low or "inats" in low):
        return True
    return False


def _file_kind(fname: str, subject: str = "") -> str:
    low = f"{fname} {subject}".lower()
    if "detailed" in low or "statement" in low:
        return "statement"
    if "credit" in low or re.search(r"\bcn\d+", low):
        return "credit"
    if low.endswith(".csv") or low.endswith(".zip") or "invoice csv" in low:
        return "invoice_csv"
    if "brinats" in low or "invoice" in low:
        return "invoice"
    return "other"


def _family_of(fname: str, account: str | None = None) -> str | None:
    low = (fname or "").lower()
    if "webstream" in low or account == "9400000004759":
        return "webstream"
    if "officeconnect" in low or "office connect" in low or "ooc" in low or account == "9400000004657":
        return "office_connect"
    return None


def _month_from_name(fname: str) -> str | None:
    m = re.search(r"(20\d{2})(\d{2})\d{2}", fname or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def month_range(start: str, end: str) -> list[str]:
    y, m = [int(p) for p in start.split("-")[:2]]
    ey, em = [int(p) for p in end.split("-")[:2]]
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m = 1
            y += 1
    return out


def last_complete_month(today: date | None = None) -> str:
    today = today or date.today()
    y, m = today.year, today.month - 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}"


def iter_openserve_parts():
    """Every Openserve invoice / CSV / statement attachment on the box.

    Openserve resends the same file a few times — caller must hash-dedupe.
    """
    from email.utils import parsedate_to_datetime

    for root in mailbox_roots():
        mailbox = f"{root.parent.name}/{root.name}"
        for dirpath, _dirs, files in os.walk(root):
            if "/new" not in dirpath and "/cur" not in dirpath:
                continue
            folder = Path(dirpath).parent.name
            for name in files:
                if name.startswith("."):
                    continue
                path = Path(dirpath) / name
                try:
                    with path.open("rb") as fh:
                        msg = email.message_from_binary_file(fh)
                except OSError:
                    continue
                if not _openserve_hit(msg):
                    continue
                subj = " ".join((msg.get("Subject") or "").split())
                frm = msg.get("From") or ""
                sent = ""
                try:
                    sent = parsedate_to_datetime(msg.get("Date") or "").date().isoformat()
                except (TypeError, ValueError, IndexError):
                    sent = ""
                mid = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
                for part in msg.walk():
                    fname = part.get_filename() or ""
                    if not _keep_attachment(fname):
                        continue
                    payload = part.get_payload(decode=True) or b""
                    if not payload:
                        continue
                    accounts = re.findall(r"94\d{11}", f"{subj} {fname}")
                    invoices = [m.upper() for m in re.findall(r"INATS\d+", f"{subj} {fname}", flags=re.I)]
                    yield {
                        "filename": fname,
                        "payload": payload,
                        "mailbox": mailbox,
                        "folder": folder,
                        "sent_on": sent,
                        "subject": subj,
                        "from": frm,
                        "message_id": mid,
                        "kind": _file_kind(fname, subj),
                        "account_number": accounts[0] if accounts else None,
                        "invoice_number": invoices[0] if invoices else None,
                        "family": _family_of(fname, accounts[0] if accounts else None),
                        "month": _month_from_name(fname) or (sent[:7] if sent else None),
                    }


def _iter_mail_zips():
    for item in iter_openserve_parts():
        if item["kind"] != "invoice_csv":
            continue
        payload = item["payload"]
        if payload.startswith(b"PK") or item["filename"].lower().endswith(".csv"):
            yield item["filename"], payload


def _mail_kind(subject: str) -> str:
    low = (subject or "").lower()
    if "invoice csv" in low:
        return "invoice_csv"
    if "invoice" in low:
        return "invoice"
    if "statement" in low:
        return "statement"
    if "letter of demand" in low or "sysgen" in low:
        return "demand"
    if "credit" in low or re.search(r"\bcn\d+", low):
        return "credit"
    return "other"


def catalog_mail(conn: sqlite3.Connection) -> dict:
    """Index Openserve invoice/statement mail. Does not store bodies."""
    ensure_tables(conn)
    conn.execute("DELETE FROM mail_items")
    counted = 0
    seen_msg: set[str] = set()
    for item in iter_openserve_parts():
        key = item.get("message_id") or f"{item.get('mailbox')}|{item.get('sent_on')}|{item.get('subject')}"
        if key in seen_msg:
            continue
        seen_msg.add(key)
        conn.execute(
            """INSERT OR IGNORE INTO mail_items
               (message_id, mailbox, sent_on, kind, subject, account_number, invoice_number)
               VALUES (?,?,?,?,?,?,?)""",
            (
                item.get("message_id") or None,
                item.get("mailbox"),
                item.get("sent_on") or None,
                _mail_kind(item.get("subject") or ""),
                (item.get("subject") or "")[:180],
                item.get("account_number"),
                item.get("invoice_number"),
            ),
        )
        counted += 1
    conn.commit()
    row = conn.execute(
        "SELECT MIN(sent_on), MAX(sent_on), COUNT(*) FROM mail_items WHERE sent_on IS NOT NULL"
    ).fetchone()
    return {"indexed": counted, "from": row[0], "to": row[1], "stored": row[2]}


def ingest_payload(conn: sqlite3.Connection, payload: bytes, filename: str, source: str) -> int:
    if filename.lower().endswith(".csv") and not payload.startswith(b"PK"):
        return ingest_csv_text(conn, payload.decode("utf-8-sig", "replace"), filename, source)
    if payload.startswith(b"PK"):
        return ingest_zip(conn, payload, filename, source)
    return 0


def collect_openserve_mail(dest: Path | None = None) -> dict:
    """Copy every Openserve attachment into one folder. Same file sent twice = one copy."""
    dest = dest or COLLECT_DIR
    dest.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict] = {}
    copies = 0
    extracted = 0
    for item in iter_openserve_parts():
        digest = hashlib.sha256(item["payload"]).hexdigest()
        if digest in files:
            files[digest]["copies"] += 1
            copies += 1
            continue
        name = Path(item["filename"]).name
        path = dest / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            path = dest / f"{digest[:8]}_{name}"
        path.write_bytes(item["payload"])
        row = {
            "filename": path.name,
            "sha256": digest,
            "kind": item["kind"],
            "invoice_number": item.get("invoice_number"),
            "account_number": item.get("account_number"),
            "family": item.get("family"),
            "month": item.get("month"),
            "sent_on": item.get("sent_on"),
            "mailbox": item.get("mailbox"),
            "copies": 1,
        }
        files[digest] = row
        if item["kind"] == "invoice_csv" and item["payload"].startswith(b"PK"):
            try:
                zf = zipfile.ZipFile(io.BytesIO(item["payload"]))
            except zipfile.BadZipFile:
                zf = None
            if zf is not None:
                for inner in zf.namelist():
                    if not inner.lower().endswith(".csv"):
                        continue
                    inner_name = Path(inner).name
                    inner_path = dest / inner_name
                    raw = zf.read(inner)
                    if not inner_path.exists():
                        inner_path.write_bytes(raw)
                        extracted += 1
    have: dict[str, set[str]] = {key: set() for key, _label, _acc in INVOICE_FAMILIES}
    statements: dict[str, set[str]] = {acc: set() for acc in STATEMENT_ACCOUNTS}
    for row in files.values():
        month = row.get("month")
        if row.get("kind") in {"invoice", "invoice_csv"} and row.get("family") and month:
            have.setdefault(row["family"], set()).add(month)
        if row.get("kind") == "statement" and row.get("account_number") and month:
            statements.setdefault(row["account_number"], set()).add(month)
    missing = missing_invoice_report(have)
    missing["statements"] = [
        {"account": acc, "months": month_range(FIRST_FIBRE_MONTH, last_complete_month())}
        for acc in STATEMENT_ACCOUNTS
    ]
    for block in missing["statements"]:
        block["months"] = [
            m for m in month_range(FIRST_FIBRE_MONTH, last_complete_month()) if m not in statements.get(block["account"], set())
        ]
    manifest = {
        "folder": str(dest),
        "unique_files": len(files),
        "duplicate_sends": copies,
        "csv_extracted": extracted,
        "files": sorted(files.values(), key=lambda r: (r.get("month") or "", r.get("filename") or "")),
        "missing": missing,
    }
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    (dest / "MISSING.txt").write_text(_missing_text(missing, dest, copies))
    return manifest


def missing_invoice_report(
    have: dict[str, set[str]],
    today: date | None = None,
    first: str = FIRST_FIBRE_MONTH,
) -> dict:
    """Months we should have a Webstream + Office Connect invoice for, but don't."""
    end = last_complete_month(today)
    expected = month_range(first, end)
    families = []
    all_missing = []
    for key, label, account in INVOICE_FAMILIES:
        got = set(have.get(key) or [])
        miss = [m for m in expected if m not in got]
        families.append(
            {
                "family": key,
                "label": label,
                "account": account,
                "have": sorted(got),
                "missing": miss,
            }
        )
        all_missing.extend({"family": label, "account": account, "month": m} for m in miss)
    recent = [r for r in all_missing if r["month"] >= "2026-08"]
    return {
        "from": first,
        "to": end,
        "expected_months": expected,
        "families": families,
        "missing": all_missing,
        "recent_missing": recent,
        "aug_sep_missing": [r for r in all_missing if r["month"][5:] in {"08", "09"}],
    }


def _missing_text(missing: dict, dest: Path, copies: int) -> str:
    lines = [
        "Openserve mail — one folder, duplicates collapsed.",
        f"Folder: {dest}",
        f"Expected invoices {missing.get('from')} → {missing.get('to')} (first fibre to last complete month).",
        f"Same invoice sent more than once: {copies} extra copies kept as one file.",
        "",
    ]
    for fam in missing.get("families") or []:
        lines.append(f"{fam['label']} {fam['account']}")
        lines.append(f"  have: {', '.join(fam.get('have') or []) or 'none'}")
        lines.append(f"  missing: {', '.join(fam.get('missing') or []) or 'none'}")
        lines.append("")
    recent = missing.get("recent_missing") or []
    lines.append("Aug / Sep (and later) still missing from the box:")
    if recent:
        for row in recent:
            lines.append(f"  {row['month']} {row['family']} {row['account']}")
    else:
        lines.append("  none")
    lines.append("")
    lines.append(
        "Box mail after 4 Feb 2026 has no nbcustnb@openserve.co.za invoices. "
        "kevin@ still received other mail through October, so the mailbox is live — "
        "Openserve is not delivering Aug/Sep (or Feb–Jul) copies here. "
        "Check the Openserve portal / another inbox (iCloud / Multitrack) and drop the files in this folder."
    )
    return "\n".join(lines) + "\n"


def ingest_mail(conn: sqlite3.Connection) -> dict:
    ensure_tables(conn)
    collected = collect_openserve_mail()
    seen: set[str] = set()
    files = 0
    lines = 0
    for item in iter_openserve_parts():
        if item["kind"] != "invoice_csv":
            continue
        digest = hashlib.sha256(item["payload"]).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        files += 1
        lines += ingest_payload(conn, item["payload"], item["filename"], "mail")
    coverage = catalog_mail(conn)
    coverage["folder"] = collected.get("folder")
    coverage["unique_files"] = collected.get("unique_files")
    coverage["duplicate_sends"] = collected.get("duplicate_sends")
    coverage["missing"] = collected.get("missing")
    counts = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    return {
        "files": files,
        "lines_read": lines,
        "invoices": counts,
        "mail": coverage,
        "collected": {
            "folder": collected.get("folder"),
            "unique_files": collected.get("unique_files"),
            "duplicate_sends": collected.get("duplicate_sends"),
        },
    }


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


def billing_accounts_for_export(conn: sqlite3.Connection) -> list[dict]:
    ensure_tables(conn)
    rows = conn.execute(
        """SELECT account_number, product_family, COUNT(*), ROUND(SUM(total),2),
                  MIN(invoice_date), MAX(invoice_date)
           FROM invoices
           WHERE account_number IS NOT NULL AND account_number != ''
           GROUP BY account_number
           ORDER BY account_number"""
    )
    out = []
    for account, family, n, total, first, last in rows:
        sns = [
            r[0]
            for r in conn.execute(
                """SELECT DISTINCT l.service_number
                   FROM invoice_lines l
                   JOIN invoices i USING (invoice_number)
                   WHERE i.account_number=? AND l.service_number IS NOT NULL
                   ORDER BY l.service_number""",
                (account,),
            )
        ]
        out.append(
            {
                "account_number": account,
                "product_family": family,
                "invoices": n,
                "total": total,
                "from": first,
                "to": last,
                "services": sns,
            }
        )
    return out


VAT_RATE = 0.15


def cost_by_service(conn: sqlite3.Connection) -> dict[str, dict]:
    """Latest invoice CSV: per B-number, forward-month lines + VAT = cost.

    A client can have more than one cost line (Phillip 200 + IP;
    VK Pop 500 + IP and the Office Connect line). Pro-rata / prior
    periods on the same invoice are dropped — we take the latest
    period_start per B-number.
    """
    ensure_tables(conn)
    latest = conn.execute("SELECT MAX(invoice_date) FROM invoices").fetchone()[0]
    if not latest:
        return {}
    rows = conn.execute(
        """SELECT l.service_number, l.extra_kind, l.invoice_text, l.capacity,
                  l.charge_amount, l.period_start, l.period_end, l.invoice_number
           FROM invoice_lines l
           JOIN invoices i USING (invoice_number)
           WHERE i.invoice_date=?
             AND IFNULL(l.extra_kind,'') != 'vat'
             AND l.service_number IS NOT NULL AND l.service_number != ''
           ORDER BY l.service_number, l.extra_kind""",
        (latest,),
    ).fetchall()
    by: dict[str, list[dict]] = {}
    for sn, kind, text, cap, amount, start, end, inv in rows:
        by.setdefault(sn, []).append(
            {
                "kind": kind,
                "text": text,
                "capacity": cap,
                "amount": float(amount or 0),
                "period_start": start,
                "period_end": end,
                "invoice_number": inv,
            }
        )
    out: dict[str, dict] = {}
    for sn, items in by.items():
        periods = [i["period_start"] for i in items if i.get("period_start")]
        target = max(periods) if periods else None
        chosen = [i for i in items if not target or i.get("period_start") == target]
        if not chosen:
            chosen = items
        kind_rank = {"rental": 0, "ipv4": 1, "bridge": 2}
        chosen.sort(key=lambda i: (kind_rank.get(i.get("kind") or "", 9), i.get("kind") or ""))
        ex_vat = round(sum(i["amount"] for i in chosen), 2)
        vat = round(ex_vat * VAT_RATE, 2)
        cost = round(ex_vat + vat, 2)
        bits = []
        for i in chosen:
            if i["kind"] == "rental":
                bits.append(f"{i['capacity']} Mbps" if i.get("capacity") else (i.get("text") or "Rental"))
            elif i["kind"] == "ipv4":
                bits.append("IP")
            elif i["kind"] == "bridge" and i["amount"]:
                bits.append("bridge")
            elif i["amount"]:
                bits.append(extra_label(i["kind"] or "") or i.get("text") or "extra")
        out[sn] = {
            "service_number": sn,
            "ex_vat": ex_vat,
            "vat": vat,
            "cost": cost,
            "period": target,
            "invoice_date": latest,
            "invoice_number": chosen[0]["invoice_number"] if chosen else None,
            "lines": chosen,
            "label": " + ".join(bits) or "Openserve",
        }
    return out


def line_charges_for_export(conn: sqlite3.Connection) -> list[dict]:
    ensure_tables(conn)
    rows = conn.execute(
        """SELECT l.service_number, ROUND(SUM(l.charge_amount),2),
                  COUNT(DISTINCT l.invoice_number), MIN(i.invoice_date), MAX(i.invoice_date)
           FROM invoice_lines l
           JOIN invoices i USING (invoice_number)
           WHERE l.service_number IS NOT NULL AND l.service_number != ''
             AND IFNULL(l.extra_kind,'') != 'vat'
           GROUP BY l.service_number
           ORDER BY l.service_number"""
    )
    return [
        {
            "service_number": sn,
            "total": total,
            "invoices": n,
            "from": first,
            "to": last,
        }
        for sn, total, n, first, last in rows
    ]


def mail_coverage_for_export(conn: sqlite3.Connection) -> dict:
    ensure_tables(conn)
    row = conn.execute(
        """SELECT MIN(sent_on), MAX(sent_on), COUNT(*) FROM mail_items
           WHERE kind IN ('invoice','invoice_csv','statement','credit')"""
    ).fetchone()
    kinds = {
        k: n
        for k, n in conn.execute("SELECT kind, COUNT(*) FROM mail_items GROUP BY kind")
    }
    statement_accounts = [
        r[0]
        for r in conn.execute(
            """SELECT DISTINCT account_number FROM mail_items
               WHERE account_number IS NOT NULL ORDER BY account_number"""
        )
    ]
    have: dict[str, set[str]] = {key: set() for key, _label, _acc in INVOICE_FAMILIES}
    for inv, inv_date, account, family in conn.execute(
        "SELECT invoice_number, invoice_date, account_number, product_family FROM invoices"
    ):
        month = (inv_date or "")[:7]
        key = _family_of(family or "", account)
        if key and month:
            have.setdefault(key, set()).add(month)
    manifest = {}
    if (COLLECT_DIR / "MANIFEST.json").exists():
        try:
            manifest = json.loads((COLLECT_DIR / "MANIFEST.json").read_text())
        except json.JSONDecodeError:
            manifest = {}
    for item in manifest.get("files") or []:
        key = item.get("family") or _family_of(item.get("filename") or "", item.get("account_number"))
        month = item.get("month")
        if key and month and item.get("kind") in {"invoice", "invoice_csv"}:
            have.setdefault(key, set()).add(month)
    missing = missing_invoice_report(have)
    recent = missing.get("recent_missing") or []
    gap = (
        f"All Openserve attachments are in {COLLECT_DIR} "
        f"({manifest.get('unique_files') or 0} unique, "
        f"{manifest.get('duplicate_sends') or 0} repeat sends collapsed). "
        f"Mail on the box {row[0] or '—'} → {row[1] or '—'}. "
    )
    if recent:
        gap += "Missing latest: " + ", ".join(f"{r['month']} {r['family']}" for r in recent) + "."
    elif missing.get("missing"):
        gap += f"{len(missing['missing'])} earlier months still have no invoice copy."
    else:
        gap += "No missing months."
    return {
        "from": row[0],
        "to": row[1],
        "messages": row[2] or 0,
        "kinds": kinds,
        "statement_accounts": statement_accounts,
        "mailbox": "all gowifi.co.za / go-wifi.co.za boxes",
        "folder": str(COLLECT_DIR),
        "unique_files": manifest.get("unique_files"),
        "duplicate_sends": manifest.get("duplicate_sends"),
        "pop_status": "awaiting bank proof of payment",
        "missing": missing,
        "gap": gap,
    }


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
    accounts = billing_accounts_for_export(conn)
    lines = line_charges_for_export(conn)
    if not accounts or accounts[0]["account_number"] != "9400000004653":
        print("FAIL billing-account", accounts)
        failed += 1
    elif not lines or lines[0]["service_number"] != "B110033875":
        print("FAIL line-charges", lines)
        failed += 1
    else:
        print("OK per-account-reconcile")
    multi = (
        "Account Number,Invoice Number,Invoice Date,Service Name,Invoice Text,"
        "Charge Amount,Product,Capacity,Activation Date,Charge Date,"
        "Period Start Date,Period End Date\n"
        "9400000004759,INATS099,20260131,B110034779,Rental - Openserve Webstream 200 Mbps,"
        "775.00,Openserve Webstream,200,20240916,20260131,20260201,20260228\n"
        "9400000004759,INATS099,20260131,B110034779,Dynamic IPV4 Recurring,"
        "100.00,Openserve Webstream,200,20240916,20260131,20260201,20260228\n"
        "9400000004759,INATS099,20260131,B110033875,Rental - Openserve Webstream 500 Mbps,"
        "261.94,Openserve Webstream,500,20251224,20260131,20251224,20251231\n"
        "9400000004759,INATS099,20260131,B110033875,Rental - Openserve Webstream 500 Mbps,"
        "1015.00,Openserve Webstream,500,20251224,20260131,20260201,20260228\n"
        "9400000004759,INATS099,20260131,B110033875,Dynamic IPV4 Recurring,"
        "100.00,Openserve Webstream,500,20251224,20260131,20260201,20260228\n"
        "9400000004657,INATS098,20260131,B110034814,Rental - OOC - 500 Mbps,"
        "1710.00,Openserve Office Connect,500,20250122,20260131,20260201,20260228\n"
        "9400000004657,INATS098,20260131,B110034814,Dynamic IPV4 Recurring,"
        "100.00,Openserve Office Connect,500,20250122,20260131,20260201,20260228\n"
        "9400000004759,INATS099,20260131,,VAT @ 15%,165.00,Openserve Webstream,,,,20260131,\n"
    )
    conn2 = sqlite3.connect(":memory:")
    ingest_csv_text(conn2, multi, "multi.csv", "test")
    by = cost_by_service(conn2)
    phillip = by.get("B110034779") or {}
    pop500 = by.get("B110033875") or {}
    pop_oc = by.get("B110034814") or {}
    if abs((phillip.get("ex_vat") or 0) - 875) > 0.01 or "IP" not in (phillip.get("label") or ""):
        print("FAIL phillip-200-ip", phillip)
        failed += 1
    elif abs((phillip.get("cost") or 0) - 1006.25) > 0.01:
        print("FAIL phillip-cost-vat", phillip)
        failed += 1
    elif abs((pop500.get("ex_vat") or 0) - 1115) > 0.01 or abs((pop500.get("cost") or 0) - 1282.25) > 0.01:
        print("FAIL vk-500-ip-not-prorata", pop500)
        failed += 1
    elif abs((pop_oc.get("ex_vat") or 0) - 1810) > 0.01 or "IP" not in (pop_oc.get("label") or ""):
        print("FAIL vk-oc-ip", pop_oc)
        failed += 1
    else:
        print("OK cost-per-b-plus-vat", phillip["label"], pop500["label"], pop_oc["label"])
    miss = missing_invoice_report(
        {
            "webstream": {"2025-09", "2025-10", "2026-01"},
            "office_connect": {"2025-09"},
        },
        today=date(2026, 10, 5),
        first="2025-08",
    )
    ws_miss = next(f["missing"] for f in miss["families"] if f["family"] == "webstream")
    if "2025-08" not in ws_miss or "2026-08" not in ws_miss or "2026-09" not in ws_miss:
        print("FAIL missing-aug-sep", ws_miss)
        failed += 1
    elif "2025-09" in ws_miss or "2026-01" in ws_miss:
        print("FAIL missing-should-have", ws_miss)
        failed += 1
    elif not any(r["month"] == "2026-08" for r in miss["aug_sep_missing"]):
        print("FAIL aug-sep-flag", miss["aug_sep_missing"])
        failed += 1
    elif _month_from_name("INATS0117669_GOWIFI_20260131_OpenserveWebstreamRental.csv.zip") != "2026-01":
        print("FAIL month-from-name")
        failed += 1
    elif _family_of("INATS0117643_GOWIFI_20260131_OpenServeOfficeConnectRental.csv.zip") != "office_connect":
        print("FAIL family-from-name")
        failed += 1
    else:
        print("OK missing-aug-sep", ",".join(miss["aug_sep_missing"][0][k] for k in ("month", "family")))
    conn2.close()
    conn.close()
    return failed


def main() -> int:
    import sys

    if "--self-test" in sys.argv:
        return self_test()
    if "--collect" in sys.argv:
        report = collect_openserve_mail()
        print(json.dumps({"ok": True, "folder": report.get("folder"), "unique_files": report.get("unique_files"), "duplicate_sends": report.get("duplicate_sends"), "missing": (report.get("missing") or {}).get("recent_missing")}))
        return 0
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    report = ingest_mail(conn)
    print(json.dumps({"ok": True, **report}))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
