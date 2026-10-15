#!/usr/bin/env python3
"""Read-only Netcash NIWS_NIF client. Tokens stay in /root/secrets.

Does not upload debit batches. Pulls batch status, unauthorised items,
and merchant statements into netcash_items.
"""
from __future__ import annotations

import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

ENV_PATH = Path(os.environ.get("NETCASH_ENV", "/root/secrets/netcash.env"))
DB = os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db")
ENDPOINT = "https://ws.netcash.co.za/NIWS/NIWS_NIF.svc"
NS = "http://tempuri.org/"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
DEFAULT_VENDOR = "24ade73c-98cf-47b3-99be-cc7b867b3080"

SCHEMA = """
CREATE TABLE IF NOT EXISTS netcash_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_ref TEXT,
    service_number TEXT,
    amount REAL,
    action_date TEXT,
    result TEXT,
    batch_id TEXT,
    source TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_netcash_items_dedup
    ON netcash_items (
        COALESCE(account_ref, ''),
        COALESCE(action_date, ''),
        COALESCE(amount, 0),
        COALESCE(batch_id, ''),
        COALESCE(result, ''),
        COALESCE(source, '')
    );
"""


def _load_env(path: Path = ENV_PATH) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    return data


def service_key(env: dict[str, str] | None = None) -> str:
    env = env or _load_env()
    return (
        env.get("NETCASH_SERVICE_KEY")
        or env.get("NETCASH_DEBIT_KEY")
        or env.get("SERVICE_KEY")
        or ""
    ).strip()


def status(env: dict[str, str] | None = None) -> dict:
    env = env or _load_env()
    key = service_key(env)
    user = env.get("NETCASH_USERNAME") or ""
    if key:
        return {
            "ready": True,
            "username": user or None,
            "note": "Debit service key on the box. Read-only NIWS_NIF pull.",
        }
    if user:
        return {
            "ready": False,
            "username": user,
            "note": "Username saved. Need the Netcash debit service key (or password + PIN to fetch it).",
        }
    return {
        "ready": False,
        "username": None,
        "note": "Put NETCASH_SERVICE_KEY in /root/secrets/netcash.env.",
    }


def _soap(method: str, fields: dict[str, str]) -> str:
    inner = "".join(
        f"<{name}>{_xml(val)}</{name}>" for name, val in fields.items() if val is not None
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<s:Envelope xmlns:s="{SOAP_NS}">'
        "<s:Body>"
        f'<{method} xmlns="{NS}">{inner}</{method}>'
        "</s:Body></s:Envelope>"
    )


def _xml(val: str) -> str:
    return (
        str(val)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def call(method: str, fields: dict[str, str], timeout: int = 45) -> str:
    body = _soap(method, fields).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{NS}INIWS_NIF/{method}"',
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"Netcash {method} failed {exc.code}: {detail}") from exc
    return _result_text(raw, method)


def _result_text(xml: str, method: str) -> str:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml.strip()
    want = f"{method}Result"
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == want:
            if list(el) and not (el.text or "").strip():
                parts = [c.text or "" for c in el]
                return "\t".join(parts).strip()
            return (el.text or "").strip()
        if tag == "string" and el.text:
            return el.text.strip()
    fault = next((el for el in root.iter() if el.tag.split("}")[-1] == "faultstring"), None)
    if fault is not None and fault.text:
        raise SystemExit(f"Netcash SOAP fault: {fault.text.strip()}")
    return xml.strip()


def _rows_from_tab(text: str, source: str, batch_id: str | None = None) -> list[dict]:
    rows: list[dict] = []
    if not text or text.upper() in {"FILE NOT READY", "100", "101", "102", "200"}:
        return rows
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) == 1 and "," in line and line.count(",") >= 2:
            parts = [p.strip() for p in line.split(",")]
        if parts[0].upper() in {"H", "K", "F", "HEADER", "ACCOUNT", "REFERENCE"}:
            continue
        account_ref = None
        amount = None
        action_date = None
        result = None
        for part in parts:
            if account_ref is None and re.match(r"^[A-Za-z0-9][A-Za-z0-9._/-]{2,}$", part):
                if not re.match(r"^\d{8}$", part) and not re.match(r"^-?\d+(\.\d+)?$", part):
                    account_ref = part
                    continue
            if action_date is None and re.match(r"^\d{8}$", part):
                action_date = f"{part[:4]}-{part[4:6]}-{part[6:8]}"
                continue
            if action_date is None and re.match(r"^\d{4}-\d{2}-\d{2}", part):
                action_date = part[:10]
                continue
            if amount is None and re.match(r"^-?\d+(\.\d+)?$", part.replace(" ", "")):
                try:
                    amount = float(part.replace(" ", ""))
                    continue
                except ValueError:
                    pass
            if result is None and part and not re.match(r"^-?\d+(\.\d+)?$", part):
                result = part
        if not any((account_ref, amount, action_date, result)):
            continue
        rows.append(
            {
                "account_ref": account_ref,
                "service_number": None,
                "amount": amount,
                "action_date": action_date,
                "result": result or source,
                "batch_id": batch_id,
                "source": source,
            }
        )
    return rows


def _upsert(conn: sqlite3.Connection, rows: list[dict]) -> int:
    n = 0
    for row in rows:
        cur = conn.execute(
            """INSERT OR IGNORE INTO netcash_items
               (account_ref, service_number, amount, action_date, result, batch_id, source)
               VALUES (?,?,?,?,?,?,?)""",
            (
                row.get("account_ref"),
                row.get("service_number"),
                row.get("amount"),
                row.get("action_date"),
                row.get("result"),
                row.get("batch_id"),
                row.get("source"),
            ),
        )
        n += cur.rowcount or 0
    return n


def _poll(method: str, key: str, token_field: str, token: str, tries: int = 8) -> str:
    if not token or token in {"100", "101", "102", "200"}:
        return token
    for _ in range(tries):
        text = call(method, {"ServiceKey": key, token_field: token})
        if text.upper() != "FILE NOT READY":
            return text
        time.sleep(2)
    return "FILE NOT READY"


def pull(conn: sqlite3.Connection, days: int = 900) -> dict:
    conn.executescript(SCHEMA)
    env = _load_env()
    key = service_key(env)
    if not key:
        return {"ok": False, "error": status(env)["note"], "inserted": 0, "items": 0}
    inserted = 0
    notes: list[str] = []
    batches = call("RetrieveBatchStatus", {"ServiceKey": key})
    rows = _rows_from_tab(batches, "batch-status")
    inserted += _upsert(conn, rows)
    notes.append(f"batches={len(rows)}")

    unauth = call("RetrieveUnauthorisedBatches", {"ServiceKey": key})
    urows = _rows_from_tab(unauth, "unauthorised")
    inserted += _upsert(conn, urows)
    notes.append(f"unauthorised={len(urows)}")

    today = date.today()
    for offset in range(days):
        day = today - timedelta(days=offset)
        stamp = day.strftime("%Y%m%d")
        token = call(
            "RequestMerchantStatement",
            {"ServiceKey": key, "FromActionDate": stamp},
        )
        if token in {"100", "101", "102", "200"}:
            notes.append(f"statement-{stamp}={token}")
            continue
        text = _poll("RetrieveMerchantStatement", key, "PollingId", token)
        srows = _rows_from_tab(text, "statement", batch_id=stamp)
        n = _upsert(conn, srows)
        inserted += n
        if srows:
            notes.append(f"statement-{stamp}={len(srows)}")
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM netcash_items").fetchone()[0]
    return {
        "ok": True,
        "inserted": inserted,
        "items": total,
        "username": env.get("NETCASH_USERNAME") or None,
        "note": "; ".join(notes),
    }


def items_for_export(conn: sqlite3.Connection, limit: int = 80) -> list[dict]:
    conn.executescript(SCHEMA)
    out = []
    for rec in conn.execute(
        """SELECT account_ref, amount, action_date, result, batch_id, source
           FROM netcash_items
           ORDER BY COALESCE(action_date,'' ) DESC, id DESC LIMIT ?""",
        (limit,),
    ):
        out.append(
            {
                "account_ref": rec[0],
                "amount": rec[1],
                "action_date": rec[2],
                "result": rec[3],
                "batch_id": rec[4],
                "source": rec[5],
            }
        )
    return out


def self_test() -> int:
    failed = 0
    sample = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
        "<s:Body>"
        '<RetrieveBatchStatusResponse xmlns="http://tempuri.org/">'
        "<RetrieveBatchStatusResult>REF01\t250.00\t20261001\tPaid</RetrieveBatchStatusResult>"
        "</RetrieveBatchStatusResponse></s:Body></s:Envelope>"
    )
    text = _result_text(sample, "RetrieveBatchStatus")
    rows = _rows_from_tab(text, "batch-status")
    if not rows or rows[0]["account_ref"] != "REF01" or rows[0]["amount"] != 250:
        print("FAIL parse", rows)
        failed += 1
    else:
        print("OK parse-tab")
    env = {"NETCASH_USERNAME": "Kevin106069"}
    st = status(env)
    if st["ready"] or st.get("username") != "Kevin106069":
        print("FAIL status-user", st)
        failed += 1
    else:
        print("OK status-awaiting-key")
    return failed


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "test":
        raise SystemExit(self_test())
    if cmd == "status":
        print(status())
    elif cmd == "pull":
        db = sqlite3.connect(DB)
        print(pull(db))
    else:
        raise SystemExit("status | pull | test")
