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


def first_gowifi_order(orders: list[dict]) -> dict | None:
    """Earliest GoWiFi accepted order. Ignore old Openserve circuit dates."""
    accepted = [o for o in orders if (o.get("order_status") or "").lower() == "accepted"]
    pool = accepted or orders
    if not pool:
        return None

    def sort_key(order):
        return parse_date(order.get("created_on")) or parse_date(order.get("date_implemented")) or date.max

    return min(pool, key=sort_key)


def gowifi_order_dates(orders: list[dict]) -> tuple[date | None, date | None]:
    """Order placed, then install/activation on our side."""
    timeline = gowifi_timeline(orders)
    return timeline["ordered"], timeline["installed"]


def gowifi_timeline(orders: list[dict], circ: dict | None = None) -> dict:
    """GoWiFi order → install → activate. Never a previous-ISP circuit date."""
    empty = {
        "ordered": None,
        "installed": None,
        "activated": None,
        "delay_days": None,
    }
    order = first_gowifi_order(orders)
    if not order:
        return empty
    ordered = parse_date(order.get("created_on"))
    installed = parse_date(order.get("date_implemented")) or ordered
    activated = installed
    ins = (circ or {}).get("in_service")
    if ins and ordered and ins >= ordered:
        if installed and abs((ins - installed).days) <= 14:
            activated = ins
    delay = None
    if ordered and installed:
        delay = max(0, (installed - ordered).days)
    return {
        "ordered": ordered,
        "installed": installed,
        "activated": activated,
        "delay_days": delay,
    }


def fmt_delay(days: int | None) -> str:
    if days is None:
        return "—"
    if days == 0:
        return "0 days"
    if days == 1:
        return "1 day"
    return f"{days} days"


def fmt_days(days: int | None) -> str:
    if days is None:
        return "—"
    if days < 30:
        return f"{days} d"
    months, rem = divmod(days, 30)
    if rem == 0:
        return f"{months} mo"
    return f"{months} mo {rem} d"


def fmt_date(raw) -> str:
    if not raw:
        return "—"
    try:
        return date.fromisoformat(str(raw)[:10]).strftime("%d %b %Y")
    except ValueError:
        return str(raw)


def history_label(events: list[dict], exclusive: str, suspend_started: str | None, today: date) -> str:
    bits = []
    for ev in events:
        kind = ev.get("event")
        at_lab = fmt_date(ev.get("at"))
        if kind == "joined":
            bits.append(f"Joined {at_lab}")
        elif kind == "fibre_since":
            continue
        elif kind == "takeover":
            bits.append(f"Takeover {at_lab}")
        elif kind == "reprovisioned":
            bits.append(f"Re-provisioned {at_lab}")
        elif kind == "suspended":
            if ev.get("source") == "first-seen" or "no historical" in (ev.get("note") or "").lower():
                bits.append(f"Suspended (date unknown · first seen {at_lab})")
            else:
                bits.append(f"Suspended {at_lab}")
        elif kind == "restored":
            dur = ev.get("duration_days")
            extra = f" after {fmt_days(dur)}" if dur is not None else ""
            bits.append(f"Restored {at_lab}{extra}")
        elif kind == "cancelled":
            bits.append(f"Cancelled {at_lab}")
    if exclusive == "suspended" and suspend_started:
        try:
            open_days = (today - date.fromisoformat(suspend_started[:10])).days
        except ValueError:
            open_days = None
        bits.append(f"open {fmt_days(open_days)}")
    return " · ".join(bits) if bits else "—"


def stint_label(stints: list[dict]) -> str:
    if not stints:
        return "—"
    bits = []
    for stint in stints:
        start = fmt_date(stint.get("start"))
        if stint.get("unknown_start"):
            seen = fmt_date(stint.get("seen"))
            extra = f" (seen {seen})" if seen != "—" else ""
            bits.append(f"#{stint['n']} start unknown{extra}")
        elif stint.get("open"):
            bits.append(f"#{stint['n']} {start}–now ({fmt_days(stint.get('days'))})")
        else:
            bits.append(
                f"#{stint['n']} {start}–{fmt_date(stint.get('end'))} ({fmt_days(stint.get('days'))})"
            )
    return " · ".join(bits)


def build(conn: sqlite3.Connection) -> dict:
    today = date.today()
    conn.row_factory = sqlite3.Row
    from status_events import apply_events, assert_exclusive, events_for, stints_from

    apply_events(conn)
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
    suspended = []
    cancelled_lines = []
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
        tl = gowifi_timeline(related, circ)
        ordered = tl["ordered"]
        installed = tl["installed"]
        activated = tl["activated"]
        joined = activated or installed or ordered
        months = months_as_client(joined, today)
        exclusive = svc.get("exclusive_status") or "unknown"
        history = events_for(conn, sn)
        started = svc.get("suspend_started_at")
        open_days = None
        if exclusive == "suspended" and started:
            try:
                open_days = (today - date.fromisoformat(started[:10])).days
            except ValueError:
                open_days = None
        stints = stints_from(history, exclusive, started, today)
        row = {
            "service_number": sn,
            "customer": customer,
            "address": (svc.get("address") or latest.get("address") or "").strip(" ,"),
            "product": short_product(svc.get("circuit_type"), latest.get("product")),
            "speed": fmt_speed(svc.get("download_kbps"), svc.get("upload_kbps")),
            "line_status": exclusive,
            "lifecycle": exclusive,
            "order_status": svc.get("latest_order_status"),
            "joined": joined.isoformat() if joined else None,
            "joined_label": joined.strftime("%d %b %Y") if joined else "—",
            "ordered": ordered.isoformat() if ordered else None,
            "ordered_label": ordered.strftime("%d %b %Y") if ordered else "—",
            "installed": installed.isoformat() if installed else None,
            "installed_label": installed.strftime("%d %b %Y") if installed else "—",
            "activated": activated.isoformat() if activated else None,
            "activated_label": activated.strftime("%d %b %Y") if activated else "—",
            "delay_days": tl["delay_days"],
            "delay_label": fmt_delay(tl["delay_days"]),
            "months": months,
            "months_label": fmt_months(months),
            "suspend_stints": len(stints) or (svc.get("suspend_count") or 0),
            "suspend_for": (
                fmt_days(open_days)
                if exclusive == "suspended" and open_days is not None
                else ("unknown" if exclusive == "suspended" else "—")
            ),
            "stints": stints,
            "stints_label": stint_label(stints),
            "history": history,
            "history_label": history_label(history, exclusive, started, today),
        }
        if exclusive == "active":
            active.append(row)
        elif exclusive == "suspended":
            suspended.append(row)
        elif exclusive == "cancelled":
            cancelled_lines.append(row)

    active.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))
    suspended.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))
    cancelled_lines.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))

    live_sns = {r["service_number"] for r in active} | {r["service_number"] for r in suspended}
    cancelled_sns = {r["service_number"] for r in cancelled_lines}
    listed_names = {
        r["customer"].lower()
        for r in active + suspended + cancelled_lines
        if r.get("customer") and r["customer"] != "—"
    }
    cancellations = []
    for order in orders:
        status = (order.get("order_status") or "")
        if status.lower() not in {"cancelled", "unverified address", "pending cancellation", "to be cancelled"}:
            continue
        sn = order.get("service_number") or ""
        name = clean_name(order.get("end_customer")).lower()
        if sn and (sn in live_sns or sn in cancelled_sns):
            continue
        if name in listed_names:
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

    assert_exclusive(
        {
            "active": [r["service_number"] for r in active],
            "suspended": [r["service_number"] for r in suspended],
            "cancelled": [r["service_number"] for r in cancelled_lines],
        }
    )

    return {
        "as_at": today.isoformat(),
        "synced_at": sync["finished_at"] if sync else None,
        "sync_ok": bool(sync["ok"]) if sync else False,
        "org": org["oms_name"] if org else "GOWIFI",
        "counts": {
            "active": len(active),
            "suspended": len(suspended),
            "cancelled_lines": len(cancelled_lines),
            "cancelled_orders": len(cancellations),
        },
        "active": active,
        "suspended": suspended,
        "cancelled_lines": cancelled_lines,
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
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    payload = build(conn)
    conn.close()
    path = write(payload)
    print(json.dumps({"ok": True, "path": str(path), "counts": payload["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
