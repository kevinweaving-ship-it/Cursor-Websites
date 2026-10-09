#!/usr/bin/env python3
"""Build the compact fibre-accounts audit JSON from upp.db."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

from client_stories import (
    addrs_differ,
    classify,
    cluster_by_client,
    names_match,
    same_house_reorder_bit,
    tidy_customer,
)

DB_PATH = Path(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
JSON_PATH = Path(os.environ.get("UPP_ACCOUNTS_JSON", "/home/user-data/www/default/dash/accounts.json"))

DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d-%b-%Y %H:%M:%S",
    "%d-%B-%Y",
)


def _stamp_value(*values) -> str | None:
    """Newest ISO stamp wins. In-progress sync_runs are ignored by the caller."""
    texts = [str(v).strip() for v in values if v]
    return max(texts) if texts else None


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


def speed_mb(raw) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        value = int(raw)
        return int(round(value / 1024)) if value > 1000 else value
    digits = re.findall(r"\d+", str(raw))
    if not digits:
        return None
    value = int(digits[0])
    if "kb" in str(raw).lower() or value > 1000:
        return int(round(value / 1024)) if value > 1000 else value
    return value


def order_reason(order: dict) -> str | None:
    try:
        raw = json.loads(order.get("raw_json") or "{}")
    except json.JSONDecodeError:
        raw = {}
    blob = " ".join(
        filter(
            None,
            [
                order.get("order_status"),
                order.get("remark"),
                raw.get("stageComments"),
                raw.get("uaCaseComments"),
                raw.get("messageForIsp"),
            ],
        )
    ).lower()
    if "unverified" in blob or "ua case" in blob:
        return "unverified address"
    if "wrong address" in blob:
        return "wrong address"
    if "cbs taking control" in blob:
        return "cancelled before handover"
    if "holding pool" in blob:
        return "holding pool"
    if "cancel" in blob:
        return "cancelled"
    return None


def change_bits(orders: list[dict], current_speed: str | None, extras: list[dict], billed: dict | None) -> list[str]:
    bits = []
    accepted = sorted(
        accepted_orders(orders),
        key=lambda o: parse_date(o.get("date_implemented")) or parse_date(o.get("created_on")) or date.max,
    )
    prev_prod = None
    prev_mb = None
    last_mb = None
    for order in accepted:
        prod = short_product(None, order.get("product"))
        mb = speed_mb(order.get("speed"))
        when = parse_date(order.get("date_implemented")) or parse_date(order.get("created_on"))
        label = f"{prod} {mb}" if mb else prod
        if prev_prod is None:
            prev_prod, prev_mb, last_mb = prod, mb, mb
            continue
        elif prod != prev_prod or mb != prev_mb:
            if mb and prev_mb and mb > prev_mb:
                verb = "Upgraded"
            elif mb and prev_mb and mb < prev_mb:
                verb = "Downgraded"
            else:
                verb = "Changed"
            bits.append(f"{verb} to {label} {when.strftime('%d %b %Y')}" if when else f"{verb} to {label}")
        prev_prod, prev_mb, last_mb = prod, mb, mb
    now_mb = speed_mb(current_speed)
    if now_mb and last_mb and now_mb != last_mb:
        bits.append(f"line now {now_mb}")
    if billed and billed.get("capacity"):
        billed_mb = speed_mb(billed.get("capacity"))
        if billed_mb and now_mb and billed_mb != now_mb:
            bits.append(f"last billed {billed_mb}")
    cancelled = [
        order
        for order in orders
        if "cancel" in (order.get("order_status") or "").lower()
    ]
    if cancelled and accepted:
        last_c = max(
            cancelled,
            key=lambda o: parse_date(o.get("created_on")) or date.min,
        )
        first_a = accepted[0]
        if not addrs_differ(last_c.get("address"), first_a.get("address")):
            bits.append(same_house_reorder_bit(last_c.get("product")))
    for extra in extras:
        when = extra.get("added")
        try:
            when_lab = date.fromisoformat(when).strftime("%d %b %Y") if when else None
        except ValueError:
            when_lab = when
        if when_lab:
            bits.append(f"{extra.get('label')} added {when_lab}")
        else:
            bits.append(f"{extra.get('label')} added")
    return bits


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


def accepted_orders(orders: list[dict]) -> list[dict]:
    return [o for o in orders if (o.get("order_status") or "").lower() == "accepted"]


def first_gowifi_order(orders: list[dict]) -> dict | None:
    """Earliest GoWiFi accepted order. Ignore old Openserve circuit dates."""
    pool = accepted_orders(orders)
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
        first = None
        if orders:
            first = min(
                orders,
                key=lambda o: parse_date(o.get("created_on")) or date.max,
            )
        return {
            "ordered": parse_date((first or {}).get("created_on")) if first else None,
            "installed": None,
            "activated": None,
            "delay_days": None,
        }
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
            if not ev.get("at"):
                bits.append("Cancelled (holding pool)")
            else:
                bits.append(f"Cancelled {at_lab}")
    if exclusive == "suspended" and suspend_started:
        try:
            open_days = (today - date.fromisoformat(suspend_started[:10])).days
        except ValueError:
            open_days = None
        bits.append(f"open {fmt_days(open_days)}")
    return " · ".join(bits) if bits else "—"


def cancel_on(orders: list[dict], events: list[dict]) -> date | None:
    for ev in events:
        if ev.get("event") == "cancelled":
            parsed = parse_date(ev.get("at"))
            if parsed:
                return parsed
    for order in orders:
        if "cancel" in (order.get("order_status") or "").lower():
            return parse_date(order.get("date_implemented")) or parse_date(order.get("created_on"))
    return None


def ua_note(orders: list[dict]) -> str | None:
    for order in orders:
        try:
            raw = json.loads(order.get("raw_json") or "{}")
        except json.JSONDecodeError:
            raw = {}
        text = " ".join(
            filter(None, [str(raw.get("unverifiedAddress") or ""), str(raw.get("uaCaseComments") or "")])
        )
        if "granny" in text.lower():
            return "granny flat"
        if text.strip():
            tail = [p.strip() for p in text.split(",") if p.strip()]
            if tail:
                return tail[-1]
    return None


def story_label(row: dict, peers: list[dict] | None = None, story: dict | None = None) -> str:
    """Order facts plus redo / move / cease inferred from those orders."""
    story = story or classify(row, peers or [])
    if row.get("never_installed"):
        return story["headline"]

    bits = []
    if row.get("incoming_label"):
        bits.append(row["incoming_label"])
    if story["kind"] in {"redo", "move"} and row.get("line_status") != "cancelled":
        bits.append(story["headline"])
    if row.get("ordered_label") and row["ordered_label"] != "—":
        bits.append(f"Ordered {row['ordered_label']}")
    if row.get("installed_label") and row["installed_label"] != "—":
        bits.append(f"Installed {row['installed_label']}")
    if row.get("line_status") != "cancelled":
        if row.get("activated_label") and row["activated_label"] != "—":
            bits.append(f"Activated {row['activated_label']}")
        if row.get("delay_label") and row["delay_label"] not in {"", "—"}:
            bits.append(f"Delay {row['delay_label']}")
    for extra in row.get("change_bits") or []:
        bits.append(extra)
    if row.get("line_status") == "suspended":
        bits.append("Suspended (not active)")
        if row.get("stints_label") and row["stints_label"] != "—":
            bits.append(row["stints_label"])
    elif row.get("stints") and any(not stint.get("open") for stint in row["stints"]):
        bits.append(f"Suspended then restored · {row['stints_label']}")
    if row.get("line_status") == "cancelled":
        bits.append(story["headline"])
    elif story["kind"] == "live" and row.get("related_label"):
        bits.append(row["related_label"])
    return " · ".join(bit for bit in bits if bit)


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
    from invoice_import import (
        billed_speed_by_sn,
        billing_accounts_for_export,
        extras_by_sn,
        ingest_mail,
        invoices_for_export,
        line_charges_for_export,
        mail_coverage_for_export,
        cost_by_service,
    )

    from site_lines import apply_site_line, incoming_fibre_for_export, incoming_related_label, pop_cost
    from clients import cards_for_export

    from books import books_for_export
    from mail_forwards import forwards_for_export

    ingest_mail(conn)
    extras_map = extras_by_sn(conn)
    billed_map = billed_speed_by_sn(conn)
    invoice_rows = invoices_for_export(conn)
    billing_accounts = billing_accounts_for_export(conn)
    line_charges = line_charges_for_export(conn)
    mail_coverage = mail_coverage_for_export(conn)
    mail_forwards = forwards_for_export()
    org = conn.execute("SELECT * FROM organisations").fetchone()
    if not mail_forwards.get("mx_on_box"):
        mail_coverage["gap"] = (
            (mail_coverage.get("gap") or "")
            + " go-wifi.co.za has no public MX. Openserve profile is now"
            " accounts@gowifi.co.za / kevin@gowifi.co.za; leftover mail still"
            " addressed to @go-wifi.co.za will not hit the box."
        )
        mail_coverage["go_wifi_mx"] = False
    upp_emails = {
        "email_address": org["email_address"] if org else None,
        "bundle_transaction_email": org["bundle_transaction_email"] if org else None,
        "lead_response_email": org["lead_response_email"] if org else None,
        "support_email": org["support_email"] if org else None,
        "sales_email": org["sales_email"] if org else None,
        "users": [
            {
                "email": r["email"],
                "status": r["status"],
                "primary": bool(r["is_primary"]),
            }
            for r in conn.execute(
                "SELECT email, status, is_primary FROM users ORDER BY is_primary DESC, email"
            )
        ],
    }
    books = books_for_export(conn)
    services = [dict(r) for r in conn.execute("SELECT * FROM services")]
    orders = [dict(r) for r in conn.execute("SELECT * FROM orders")]
    # Skip the in-progress row (inserted ok=0 before write()). Prefer the
    # newest of last ok finish and the services just written this fetch.
    sync = conn.execute(
        """SELECT finished_at, ok FROM sync_runs
           WHERE finished_at IS NOT NULL AND ok=1
           ORDER BY id DESC LIMIT 1"""
    ).fetchone()
    last_svc = conn.execute("SELECT MAX(updated_at) FROM services").fetchone()
    by_sn: dict[str, list[dict]] = {}
    orphan_orders: list[dict] = []
    for order in orders:
        sn_key = order.get("service_number") or ""
        by_sn.setdefault(sn_key, []).append(order)
        if not sn_key:
            orphan_orders.append(order)

    active = []
    suspended = []
    cancelled_lines = []
    for svc in services:
        sn = svc["service_number"]
        related = list(by_sn.get(sn, []))
        latest = related[0] if related else {}
        if related:
            latest = sorted(related, key=lambda o: o.get("created_on") or "", reverse=True)[0]
        accepted = accepted_orders(related)
        customer = tidy_customer(
            clean_name(
                (accepted[-1] if accepted else latest).get("end_customer")
                if (accepted or latest)
                else None
            )
        )
        related.extend(
            order
            for order in orphan_orders
            if names_match(customer, tidy_customer(clean_name(order.get("end_customer"))))
        )
        circ = circuit_dates(svc.get("raw_circuit_json"))
        tl = gowifi_timeline(related, circ)
        exclusive = svc.get("exclusive_status") or "unknown"
        never_installed = exclusive == "cancelled" and not accepted
        ordered = tl["ordered"]
        installed = None if never_installed else tl["installed"]
        activated = None if never_installed else tl["activated"]
        joined = None if never_installed else (activated or installed)
        history = events_for(conn, sn)
        cancelled = cancel_on(related, history) if exclusive == "cancelled" else None
        if cancelled and str(cancelled) in {"", "—"}:
            cancelled = None
        tenure_end = cancelled or today
        months = months_as_client(joined, tenure_end) if joined else None
        reasons = []
        for order in related:
            reason = order_reason(order)
            if reason and reason not in reasons:
                reasons.append(reason)
        cancel_reason = None
        if exclusive == "cancelled":
            cancel_reason = " · ".join(r for r in reasons if r != "cancelled") or (
                "never installed" if never_installed else None
            )
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
            "access_status": svc.get("access_status"),
            "partner_status": svc.get("partner_status"),
            "fibre_fetched_at": svc.get("updated_at"),
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
            "cancelled": cancelled.isoformat() if cancelled else None,
            "cancelled_label": cancelled.strftime("%d %b %Y") if cancelled else None,
            "stints": stints,
            "stints_label": stint_label(stints),
            "history": history,
            "history_label": history_label(history, exclusive, started, today),
            "related_label": None,
            "story_kind": None,
            "story_label": "",
            "never_installed": never_installed,
            "ua_note": ua_note(related),
            "cancel_reason": cancel_reason,
            "change_bits": change_bits(
                related,
                fmt_speed(svc.get("download_kbps"), svc.get("upload_kbps")),
                extras_map.get(sn, []),
                billed_map.get(sn),
            ),
        }
        apply_site_line(row)
        if exclusive == "active":
            active.append(row)
        elif exclusive == "suspended":
            suspended.append(row)
        elif exclusive == "cancelled":
            cancelled_lines.append(row)

    active.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))
    suspended.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))
    cancelled_lines.sort(key=lambda r: (r["customer"].lower(), r["service_number"]))

    all_rows = active + suspended + cancelled_lines
    for group in cluster_by_client(all_rows):
        for row in group:
            others = [
                other
                for other in group
                if other["service_number"] != row["service_number"]
            ]
            story = classify(row, others)
            incoming_note = None
            if row.get("incoming_role"):
                for other in others:
                    incoming_note = incoming_related_label(other)
                    if incoming_note:
                        break
            row["story_kind"] = story["kind"]
            row["related_label"] = incoming_note or story["related_label"]
            row["story_label"] = story_label(row, others, story)

    incoming_fibre = incoming_fibre_for_export(all_rows)
    os_cost = cost_by_service(conn)
    for row in incoming_fibre:
        hit = os_cost.get(row.get("service_number") or "")
        if hit:
            row["cost"] = hit["cost"]
            row["cost_label"] = hit.get("label")
            row["cost_ex_vat"] = hit.get("ex_vat")
            row["cost_vat"] = hit.get("vat")
            row["cost_from"] = "invoice"
        elif os_cost:
            row["cost"] = None
            row["cost_label"] = "not on latest Openserve invoice"
            row["cost_from"] = "missing"
    billing = (books or {}).get("billing") or {}
    pop = pop_cost(incoming_fibre, billed_wireless=billing.get("billed_wireless"))

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

    # Incoming fibre stays on the POP card only — not a client row.
    active = [r for r in active if not r.get("incoming_role")]
    suspended = [r for r in suspended if not r.get("incoming_role")]
    cancelled_lines = [r for r in cancelled_lines if not r.get("incoming_role")]
    client_cards = cards_for_export(conn, active + suspended + cancelled_lines, today)

    return {
        "as_at": today.isoformat(),
        "synced_at": _stamp_value(
            sync["finished_at"] if sync and sync["finished_at"] else None,
            last_svc[0] if last_svc else None,
        ),
        "sync_ok": bool(sync and sync["ok"]) or bool(last_svc and last_svc[0]),
        "org": org["oms_name"] if org else "GOWIFI",
        "counts": {
            "active": len(active),
            "suspended": len(suspended),
            "cancelled_lines": len(cancelled_lines),
            "cancelled_orders": len(cancellations),
            "never_installed": sum(1 for r in cancelled_lines if r.get("never_installed")),
            "invoices": len(invoice_rows),
            "billing_accounts": len(billing_accounts),
            "incoming_fibre": len(incoming_fibre),
        },
        "incoming_fibre": incoming_fibre,
        "pop_cost": pop,
        "clients": client_cards,
        "invoice_list": books.get("invoice_list") or {},
        "active": active,
        "suspended": suspended,
        "cancelled_lines": cancelled_lines,
        "cancellations": cancellations,
        "invoices": invoice_rows,
        "billing_accounts": billing_accounts,
        "line_charges": line_charges,
        "mail_coverage": mail_coverage,
        "mail_forwards": mail_forwards,
        "upp_emails": upp_emails,
        "books": books,
        "payments": [],
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


def _self_test() -> int:
    if _stamp_value(None, None, "") is not None:
        print("FAIL stamp-empty", _stamp_value(None, None, ""))
        return 1
    prev = "2026-10-09T18:01:50+00:00"
    this_svc = "2026-10-09T18:15:34+00:00"
    this_fin = "2026-10-09T18:16:50+00:00"
    if _stamp_value(prev, this_svc) != this_svc:
        print("FAIL stamp-uses-this-fetch", _stamp_value(prev, this_svc))
        return 1
    if _stamp_value(this_fin, this_svc) != this_fin:
        print("FAIL stamp-uses-finished", _stamp_value(this_fin, this_svc))
        return 1
    print("OK stamp")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    payload = build(conn)
    conn.close()
    path = write(payload)
    print(json.dumps({"ok": True, "path": str(path), "counts": payload["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
