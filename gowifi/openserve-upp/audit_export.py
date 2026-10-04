#!/usr/bin/env python3
"""Build the compact fibre-accounts audit JSON from upp.db."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
JSON_PATH = Path(os.environ.get("UPP_ACCOUNTS_JSON", "/home/user-data/www/default/dash/accounts.json"))

DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d-%b-%Y %H:%M:%S",
    "%d-%B-%Y",
)


def parse_date(value) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # 26-jan-2023 17:15:26 — month may be lower case
    try:
        return datetime.strptime(text[:11].title() + text[11:], "%d-%b-%Y %H:%M:%S").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(text.title(), "%d-%b-%Y").date()
    except ValueError:
        return None


def months_as_client(joined: date | None, today: date) -> int | None:
    if not joined:
        return None
    months = (today.year - joined.year) * 12 + (today.month - joined.month)
    if today.day < joined.day:
        months -= 1
    return max(0, months)


def fmt_months(months: int | None) -> str:
    if months is None:
        return "—"
    if months < 12:
        return f"{months} mo"
    years, rem = divmod(months, 12)
    if rem == 0:
        return f"{years} yr" if years == 1 else f"{years} yr"
    return f"{years} yr {rem} mo"


def fmt_speed(down, up) -> str:
    if not down:
        return "—"

    def mb(kb):
        mbps = int(round(int(kb) / 1024))
        return str(mbps)

    if up:
        return f"{mb(down)}/{mb(up)}"
    return mb(down)


def short_product(circuit_type: str | None, product: str | None) -> str:
    text = (circuit_type or product or "").upper()
    if "OFFICE CONNECT" in text:
        kind = "Office Connect"
    elif "WEBSTREAM" in text:
        kind = "Webstream"
    elif "WEB CONNECT" in text:
        kind = "Web Connect"
    else:
        kind = (product or circuit_type or "—").replace("OPENSERVE ", "").title()
    return kind


def clean_name(name: str | None) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()) or "—"


def circuit_dates(raw_json: str | None) -> dict:
    try:
        payload = json.loads(raw_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    data = payload.get("data") or {}
    circ = data.get("circuit") or {}
    attrs = (circ.get("circuitAttributes") or [{}])[0]
    return {
        "in_service": parse_date(attrs.get("inServiceDate")),
        "completed": parse_date(attrs.get("completionDate")),
        "created": parse_date(attrs.get("unibaseCreationDate")),
    }


def join_date(circ: dict, orders: list[dict]) -> date | None:
    accepted = [o for o in orders if (o.get("order_status") or "").lower() == "accepted"]
    implemented = [parse_date(o.get("date_implemented")) for o in accepted]
    implemented = [d for d in implemented if d]
    created = [parse_date(o.get("created_on")) for o in accepted]
    created = [d for d in created if d]
    for candidate in (
        circ.get("in_service"),
        circ.get("completed"),
        min(implemented) if implemented else None,
        min(created) if created else None,
        circ.get("created"),
    ):
        if candidate:
            return candidate
    return None


def build(conn: sqlite3.Connection) -> dict:
    today = date.today()
    conn.row_factory = sqlite3.Row
    services = [dict(r) for r in conn.execute("SELECT * FROM services")]
    orders = [dict(r) for r in conn.execute("SELECT * FROM orders")]
    org = conn.execute("SELECT * FROM organisations").fetchone()
    sync = conn.execute(
        "SELECT finished_at, ok FROM sync_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    by_sn: dict[str, list[dict]] = {}
    for order in orders:
        by_sn.setdefault(order.get("service_number") or "", []).append(order)

    active = []
    inactive = []
    for svc in services:
        sn = svc["service_number"]
        related = by_sn.get(sn, [])
        latest = related[0] if related else {}
        if related:
            latest = sorted(related, key=lambda o: o.get("created_on") or "", reverse=True)[0]
        accepted = [o for o in related if (o.get("order_status") or "").lower() == "accepted"]
        customer = clean_name(
            (accepted[-1] if accepted else latest).get("end_customer")
            if (accepted or latest)
            else None
        )
        circ = circuit_dates(svc.get("raw_circuit_json"))
        joined = join_date(circ, related)
        months = months_as_client(joined, today)
        row = {
            "service_number": sn,
            "customer": customer,
            "address": (svc.get("address") or latest.get("address") or "").strip(" ,"),
            "product": short_product(svc.get("circuit_type"), latest.get("product")),
            "speed": fmt_speed(svc.get("download_kbps"), svc.get("upload_kbps")),
            "line_status": svc.get("access_status") or "—",
            "partner_status": svc.get("partner_status") or "—",
            "lifecycle": svc.get("lifecycle"),
            "order_status": svc.get("latest_order_status"),
            "joined": joined.isoformat() if joined else None,
            "joined_label": joined.strftime("%d %b %Y") if joined else "—",
            "months": months,
            "months_label": fmt_months(months),
        }
        if svc.get("lifecycle") == "active":
            active.append(row)
        else:
            inactive.append(row)

    active.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))
    inactive.sort(key=lambda r: (r["lifecycle"], r["customer"].lower()))

    cancellations = []
    for order in orders:
        status = (order.get("order_status") or "")
        if status.lower() not in {"cancelled", "unverified address", "pending cancellation", "to be cancelled"}:
            continue
        cancellations.append(
            {
                "order_number": order.get("order_number") or "—",
                "customer": clean_name(order.get("end_customer")),
                "service_number": order.get("service_number") or "—",
                "product": short_product(None, order.get("product")),
                "speed": order.get("speed") or "—",
                "status": status,
                "created": (parse_date(order.get("created_on")).strftime("%d %b %Y")
                            if parse_date(order.get("created_on")) else "—"),
                "implemented": (parse_date(order.get("date_implemented")).strftime("%d %b %Y")
                                if parse_date(order.get("date_implemented")) else "—"),
                "remark": (order.get("remark") or order.get("message_for_isp") or "").strip(),
            }
        )
    cancellations.sort(key=lambda r: r["created"], reverse=True)

    return {
        "as_at": today.isoformat(),
        "synced_at": sync["finished_at"] if sync else None,
        "sync_ok": bool(sync["ok"]) if sync else False,
        "org": org["oms_name"] if org else "GOWIFI",
        "counts": {
            "active": len(active),
            "suspended": sum(1 for r in inactive if r["lifecycle"] == "suspended"),
            "cancelled_lines": sum(1 for r in inactive if r["lifecycle"] == "cancelled"),
            "cancelled_orders": len(cancellations),
        },
        "active": active,
        "inactive": inactive,
        "cancellations": cancellations,
    }


def write(payload: dict, dest: Path = JSON_PATH) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(dest)
    try:
        dest.chmod(0o644)
    except OSError:
        pass
    return dest


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    payload = build(conn)
    conn.close()
    path = write(payload)
    print(json.dumps({"ok": True, "path": str(path), "counts": payload["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
