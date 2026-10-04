#!/usr/bin/env python3
"""Exclusive line status and suspend/restore history.

A line is never both active and suspended. Access status wins over partner
status. Empty/unowned circuits with a cancelled order are cancelled.
Each service number keeps its own stint history: suspend, then restore.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

HOLDING_MARKERS = (
    "TRANSITION",
    "WHOLESALE STAGING",
    "WS TELKOM",
)

SCHEMA_EXTRAS = """
CREATE TABLE IF NOT EXISTS service_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_number TEXT NOT NULL,
    event_type TEXT NOT NULL,
    at TEXT NOT NULL,
    source TEXT,
    note TEXT,
    duration_days INTEGER
);
CREATE INDEX IF NOT EXISTS idx_service_events_sn ON service_events(service_number, at);
"""


def ensure_columns(conn) -> None:
    conn.executescript(SCHEMA_EXTRAS)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(services)")}
    extras = {
        "exclusive_status": "TEXT",
        "suspend_started_at": "TEXT",
        "last_restored_at": "TEXT",
        "suspend_count": "INTEGER DEFAULT 0",
    }
    for name, decl in extras.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE services ADD COLUMN {name} {decl}")


def _holding(customer: str | None, isp: str | None) -> bool:
    text = f"{customer or ''} {isp or ''}".upper()
    return any(marker in text for marker in HOLDING_MARKERS)


def exclusive_status(svc: dict) -> str:
    """One bucket only: active | suspended | cancelled | unknown."""
    access = (svc.get("access_status") or "").strip().lower()
    customer = (svc.get("customer") or "").strip()
    isp = (svc.get("isp_name") or "").strip()
    order = (svc.get("latest_order_status") or "").strip().lower()
    holding = _holding(customer, isp)
    owned = bool(customer) and not holding
    cancelled_order = "cancel" in order or order == "unverified address"
    empty_circuit = not customer and not isp

    # Unowned empty circuit + cancelled order is ceased, even if access still
    # says Active or partner still says IspActive.
    if empty_circuit and cancelled_order:
        return "cancelled"
    # Access Suspended always wins over partner IspActive.
    if access == "suspended" and not (empty_circuit and cancelled_order):
        return "suspended"
    if cancelled_order and not owned:
        return "cancelled"
    if access == "active" and owned:
        return "active"
    if cancelled_order:
        return "cancelled"
    if access == "active":
        return "active"
    return "unknown"


def _iso_today() -> str:
    return date.today().isoformat()


DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d-%b-%Y %H:%M:%S",
    "%d-%B-%Y",
)


def _date_only(raw) -> str | None:
    if not raw:
        return None
    text = re.sub(r"\s+", " ", str(raw).strip())
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.strptime(text[:11].title() + text[11:], "%d-%b-%Y %H:%M:%S").date().isoformat()
    except ValueError:
        pass
    try:
        return datetime.strptime(text.title(), "%d-%b-%Y").date().isoformat()
    except ValueError:
        return None


def _days_between(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        a = date.fromisoformat(start[:10])
        b = date.fromisoformat(end[:10])
    except ValueError:
        return None
    return max(0, (b - a).days)


def _has_event(conn, sn: str, event_type: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM service_events WHERE service_number=? AND event_type=? LIMIT 1",
        (sn, event_type),
    ).fetchone()
    return bool(row)


def _add_event(conn, sn, event_type, at, source, note=None, duration_days=None):
    conn.execute(
        """INSERT INTO service_events
           (service_number, event_type, at, source, note, duration_days)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sn, event_type, at, source, note, duration_days),
    )


def _event_at(conn, sn: str, event_type: str) -> str | None:
    row = conn.execute(
        """SELECT at FROM service_events
           WHERE service_number=? AND event_type=?
           ORDER BY id LIMIT 1""",
        (sn, event_type),
    ).fetchone()
    return row[0] if row else None


def _repair_event_date(conn, sn: str, event_type: str, better_at: str | None) -> None:
    """If we seeded 'today' and a real order date is earlier, keep the real date."""
    if not better_at:
        return
    current = _event_at(conn, sn, event_type)
    if not current:
        return
    if _date_only(current) and better_at < current[:10]:
        conn.execute(
            """UPDATE service_events SET at=?, note=COALESCE(note, '')
               WHERE service_number=? AND event_type=? AND id=(
                 SELECT id FROM service_events
                 WHERE service_number=? AND event_type=? ORDER BY id LIMIT 1
               )""",
            (better_at, sn, event_type, sn, event_type),
        )


def _circuit_dates(raw_json: str | None) -> dict[str, str]:
    """Original circuit dates. inService/completion beat a later takeover order."""
    try:
        payload = json.loads(raw_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    data = payload.get("data") or {}
    circ = data.get("circuit") or {}
    attrs = (circ.get("circuitAttributes") or [{}])
    attrs = attrs[0] if attrs else {}
    out: dict[str, str] = {}
    for key, name in (
        ("inServiceDate", "in_service"),
        ("completionDate", "completed"),
        ("unibaseCreationDate", "created"),
    ):
        parsed = _date_only(attrs.get(key))
        if parsed:
            out[name] = parsed
    return out


def _order_stage(raw_json: str | None) -> str:
    try:
        payload = json.loads(raw_json or "{}")
    except json.JSONDecodeError:
        return ""
    return str(payload.get("stageComments") or payload.get("remark") or "")


def _order_dates(conn) -> tuple[dict[str, str], dict[str, str], list[tuple]]:
    """Join date (circuit first), cancel date, and later accepted orders."""
    join: dict[str, str] = {}
    cancel: dict[str, str] = {}
    fallback: dict[str, str] = {}
    later: list[tuple] = []
    unibase: dict[str, str] = {}
    for sn, raw in conn.execute("SELECT service_number, raw_circuit_json FROM services"):
        circ = _circuit_dates(raw)
        if circ.get("in_service"):
            join[sn] = circ["in_service"]
        elif circ.get("completed"):
            join[sn] = circ["completed"]
        if circ.get("created"):
            unibase[sn] = circ["created"]
    for sn, status, created, implemented, raw in conn.execute(
        """SELECT service_number, order_status, created_on, date_implemented, raw_json
           FROM orders WHERE service_number IS NOT NULL"""
    ):
        st = (status or "").lower()
        impl = _date_only(implemented)
        created_d = _date_only(created)
        best = impl or created_d
        if not best:
            continue
        if st == "accepted":
            if sn not in join or best < join[sn]:
                join[sn] = best
            later.append((sn, best, _order_stage(raw)))
        if "cancel" in st or st == "unverified address":
            if sn not in cancel or best < cancel[sn]:
                cancel[sn] = best
        if sn not in fallback or best < fallback[sn]:
            fallback[sn] = best
    for sn, when in unibase.items():
        join.setdefault(sn, when)
    for sn, when in fallback.items():
        join.setdefault(sn, when)
    return join, cancel, later


def apply_events(conn, join_dates: dict[str, str | None] | None = None) -> None:
    """Write exclusive status and append history only on change."""
    conn.execute("PRAGMA busy_timeout=30000")
    ensure_columns(conn)
    computed_join, cancel_dates, later_orders = _order_dates(conn)
    if join_dates:
        for key, value in join_dates.items():
            parsed = _date_only(value)
            if parsed and (key not in computed_join or parsed < computed_join[key]):
                computed_join[key] = parsed
    today = _iso_today()
    rows = conn.execute(
        """SELECT service_number, access_status, partner_status, customer, isp_name,
                  latest_order_status, exclusive_status, suspend_started_at,
                  last_restored_at, suspend_count, first_seen_at
           FROM services"""
    ).fetchall()
    for row in rows:
        keys = [
            "service_number",
            "access_status",
            "partner_status",
            "customer",
            "isp_name",
            "latest_order_status",
            "exclusive_status",
            "suspend_started_at",
            "last_restored_at",
            "suspend_count",
            "first_seen_at",
        ]
        svc = dict(zip(keys, row))
        sn = svc["service_number"]
        new = exclusive_status(svc)
        prev = svc["exclusive_status"]
        started = svc["suspend_started_at"]
        count = svc["suspend_count"] or 0
        joined = computed_join.get(sn)
        cancel_at = cancel_dates.get(sn) or today

        if joined:
            if not _has_event(conn, sn, "joined"):
                _add_event(conn, sn, "joined", joined, "circuit", "Circuit in-service / first order")
            else:
                current = _event_at(conn, sn, "joined")
                if current != joined:
                    conn.execute(
                        """UPDATE service_events SET at=?, source='circuit',
                           note='Circuit in-service / first order'
                           WHERE service_number=? AND event_type='joined' AND id=(
                             SELECT id FROM service_events
                             WHERE service_number=? AND event_type='joined'
                             ORDER BY id LIMIT 1
                           )""",
                        (joined, sn, sn),
                    )
            conn.execute(
                """DELETE FROM service_events
                   WHERE service_number=? AND event_type IN ('reprovisioned','takeover')
                     AND at < date(?, '+14 days')
                     AND IFNULL(note,'') NOT LIKE '%Receive Ownership%'""",
                (sn, joined),
            )

        for later_sn, later_at, stage in later_orders:
            if later_sn != sn or not joined or later_at <= joined:
                continue
            ownership = "receive ownership" in (stage or "").lower()
            gap = _days_between(joined, later_at)
            if not ownership and gap is not None and gap < 14:
                continue
            kind = "takeover" if ownership else "reprovisioned"
            exists = conn.execute(
                """SELECT 1 FROM service_events
                   WHERE service_number=? AND event_type=? AND at=? LIMIT 1""",
                (sn, kind, later_at),
            ).fetchone()
            if not exists:
                _add_event(conn, sn, kind, later_at, "order", (stage or "")[:180] or "Later accepted order")

        if new == "cancelled":
            if not _has_event(conn, sn, "cancelled"):
                _add_event(conn, sn, "cancelled", cancel_at, "order", svc.get("latest_order_status"))
            else:
                _repair_event_date(conn, sn, "cancelled", cancel_dates.get(sn))

        conn.execute(
            """UPDATE service_events SET source='first-seen'
               WHERE service_number=? AND event_type='suspended'
                 AND note LIKE '%no historical%'""",
            (sn,),
        )

        if prev is None:
            if new == "suspended":
                started = None
                count = max(1, count)
                if not _has_event(conn, sn, "suspended"):
                    _add_event(
                        conn,
                        sn,
                        "suspended",
                        today,
                        "first-seen",
                        "Observed suspended (Openserve has no historical suspend date)",
                    )
        elif prev != new:
            if new == "suspended":
                started = today
                count += 1
                _add_event(conn, sn, "suspended", today, "accessStatus", f"Was {prev}")
            elif prev == "suspended" and new == "active":
                duration = _days_between(started, today)
                _add_event(
                    conn,
                    sn,
                    "restored",
                    today,
                    "accessStatus",
                    "Restored from suspend",
                    duration,
                )
                conn.execute(
                    "UPDATE services SET last_restored_at=? WHERE service_number=?",
                    (today, sn),
                )
                started = None
            elif new == "cancelled" and prev == "suspended" and started:
                duration = _days_between(started, cancel_at)
                conn.execute(
                    """UPDATE service_events SET duration_days=?, note=?
                       WHERE service_number=? AND event_type='cancelled'
                         AND id=(SELECT id FROM service_events
                                 WHERE service_number=? AND event_type='cancelled'
                                 ORDER BY id DESC LIMIT 1)""",
                    (duration, "Cancelled while suspended", sn, sn),
                )
                started = None

        if new == "suspended" and started == today:
            first_seen = conn.execute(
                """SELECT 1 FROM service_events
                   WHERE service_number=? AND event_type='suspended'
                     AND source='first-seen' LIMIT 1""",
                (sn,),
            ).fetchone()
            if first_seen:
                started = None

        conn.execute(
            """UPDATE services SET exclusive_status=?, suspend_started_at=?,
               suspend_count=? WHERE service_number=?""",
            (new, started, count, sn),
        )
    conn.commit()


def events_for(conn, sn: str) -> list[dict]:
    rows = conn.execute(
        """SELECT event_type, at, source, note, duration_days
           FROM service_events WHERE service_number=?
           ORDER BY at,
             CASE event_type
               WHEN 'joined' THEN 0
               WHEN 'takeover' THEN 1
               WHEN 'reprovisioned' THEN 1
               WHEN 'suspended' THEN 2
               WHEN 'restored' THEN 3
               WHEN 'cancelled' THEN 4
               ELSE 5
             END, id""",
        (sn,),
    ).fetchall()
    return [
        {
            "event": r[0],
            "at": r[1],
            "source": r[2],
            "note": r[3],
            "duration_days": r[4],
        }
        for r in rows
    ]


def stints_from(events: list[dict], exclusive: str, suspend_started: str | None, today: date) -> list[dict]:
    """Closed restore stints plus one open stint if still suspended."""
    stints: list[dict] = []
    open_start = None
    unknown_start = False
    n = 0
    for ev in events:
        kind = ev.get("event")
        if kind == "suspended":
            open_start = ev.get("at")
            unknown_start = (ev.get("source") == "first-seen") or (
                "no historical" in (ev.get("note") or "").lower()
            )
        elif kind == "restored" and open_start:
            n += 1
            stints.append(
                {
                    "n": n,
                    "start": open_start,
                    "end": ev.get("at"),
                    "days": ev.get("duration_days"),
                    "open": False,
                    "unknown_start": False,
                }
            )
            open_start = None
            unknown_start = False
    if exclusive == "suspended":
        n += 1
        if unknown_start or not (open_start or suspend_started):
            stints.append(
                {
                    "n": n,
                    "start": None,
                    "seen": open_start,
                    "end": None,
                    "days": None,
                    "open": True,
                    "unknown_start": True,
                }
            )
        else:
            start = open_start or suspend_started
            try:
                days = (today - date.fromisoformat(start[:10])).days
            except ValueError:
                days = None
            stints.append(
                {
                    "n": n,
                    "start": start,
                    "end": None,
                    "days": days,
                    "open": True,
                    "unknown_start": False,
                }
            )
    return stints


def assert_exclusive(groups: dict[str, list[str]]) -> None:
    """Raise if any service number appears in more than one status bucket."""
    seen: dict[str, str] = {}
    for bucket, numbers in groups.items():
        for sn in numbers:
            if not sn:
                continue
            if sn in seen and seen[sn] != bucket:
                raise SystemExit(f"{sn} is both {seen[sn]} and {bucket}")
            seen[sn] = bucket


def self_test() -> int:
    cases = [
        (
            "aljo-suspended-not-active",
            {
                "access_status": "Suspended",
                "partner_status": "IspActive",
                "customer": "WHOLESALE STAGING / TRANSITION AREA",
                "isp_name": "WS TELKOM SP",
                "latest_order_status": "Accepted",
            },
            "suspended",
        ),
        (
            "herman-holding-pool",
            {
                "access_status": "Suspended",
                "partner_status": "IspSuspended",
                "customer": "WHOLESALE STAGING / TRANSITION AREA",
                "isp_name": "WS TELKOM SP",
                "latest_order_status": "Accepted",
            },
            "suspended",
        ),
        (
            "hpp-empty-cancelled-not-suspended",
            {
                "access_status": "Suspended",
                "partner_status": "IspActive",
                "customer": "",
                "isp_name": "",
                "latest_order_status": "Cancelled",
            },
            "cancelled",
        ),
        (
            "aman-empty-cancelled-not-active",
            {
                "access_status": "Active",
                "partner_status": "IspActive",
                "customer": "",
                "isp_name": "",
                "latest_order_status": "Cancelled",
            },
            "cancelled",
        ),
        (
            "collette-active-despite-sibling-cancel-order",
            {
                "access_status": "Active",
                "partner_status": "IspActive",
                "customer": "GOWIFI (PTY) LTD",
                "isp_name": "WS GOWIFI (PTY) LTD",
                "latest_order_status": "Accepted",
            },
            "active",
        ),
        (
            "normal-active",
            {
                "access_status": "Active",
                "partner_status": "IspActive",
                "customer": "GOWIFI (PTY) LTD",
                "isp_name": "WS GOWIFI (PTY) LTD",
                "latest_order_status": "Accepted",
            },
            "active",
        ),
    ]
    failed = 0
    for name, svc, expect in cases:
        got = exclusive_status(svc)
        ok = got == expect
        print(f"{'OK' if ok else 'FAIL'} {name}: {got} (want {expect})")
        failed += 0 if ok else 1
    assert_exclusive(
        {
            "active": ["B1"],
            "suspended": ["B2"],
            "cancelled": ["B3"],
        }
    )
    try:
        assert_exclusive({"active": ["B1"], "suspended": ["B1"]})
        print("FAIL overlap-guard")
        failed += 1
    except SystemExit:
        print("OK overlap-guard")
    today = date(2026, 10, 4)
    stints = stints_from(
        [
            {"event": "joined", "at": "2025-01-29"},
            {"event": "suspended", "at": "2026-03-01"},
            {"event": "restored", "at": "2026-03-15", "duration_days": 14},
            {"event": "suspended", "at": "2026-10-04"},
        ],
        "suspended",
        "2026-10-04",
        today,
    )
    if len(stints) != 2 or stints[0]["days"] != 14 or stints[1]["open"] is not True:
        print("FAIL stints", stints)
        failed += 1
    else:
        print("OK stints")

    # Annette-style: circuit in-service 2020, later 2026 "Receive Ownership" order
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE services (
            service_number TEXT PRIMARY KEY, lifecycle TEXT NOT NULL,
            access_status TEXT, partner_status TEXT, customer TEXT, isp_name TEXT,
            latest_order_status TEXT, raw_circuit_json TEXT,
            first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            exclusive_status TEXT, suspend_started_at TEXT, last_restored_at TEXT,
            suspend_count INTEGER DEFAULT 0
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY, order_status TEXT, service_number TEXT,
            created_on TEXT, date_implemented TEXT, raw_json TEXT NOT NULL,
            first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """
    )
    circuit = {
        "data": {
            "circuit": {
                "circuitAttributes": [{"inServiceDate": "12-Mar-2020", "completionDate": "12-mar-2020 15:30:56"}]
            }
        }
    }
    order = {
        "stageComments": "SVOrderType: Sales Order Reason: Receive Ownership Product: Speed Mbps:25",
        "orderStatus": "Accepted",
    }
    conn.execute(
        """INSERT INTO services (service_number, lifecycle, access_status, partner_status,
           customer, isp_name, latest_order_status, raw_circuit_json, first_seen_at, updated_at)
           VALUES ('B140017953','active','Active','IspActive','GOWIFI','WS GOWIFI','Accepted',?,?,?)""",
        (json.dumps(circuit), "2026-10-04", "2026-10-04"),
    )
    conn.execute(
        """INSERT INTO orders (id, order_status, service_number, created_on, date_implemented,
           raw_json, first_seen_at, updated_at)
           VALUES (1,'Accepted','B140017953','2026-03-19','2026-03-25',?,?,?)""",
        (json.dumps(order), "x", "x"),
    )
    ensure_columns(conn)
    # seed the wrong 2026 join like the first export did
    _add_event(conn, "B140017953", "joined", "2026-03-25", "circuit/order", "Became a client")
    conn.commit()
    apply_events(conn)
    evs = events_for(conn, "B140017953")
    joined = [e for e in evs if e["event"] == "joined"]
    take = [e for e in evs if e["event"] == "takeover"]
    if not joined or joined[0]["at"] != "2020-03-12":
        print("FAIL annette-join", evs)
        failed += 1
    elif not take or take[0]["at"] != "2026-03-25":
        print("FAIL annette-takeover", evs)
        failed += 1
    else:
        print("OK annette-join-from-circuit")
    conn.close()
    return failed


def main() -> int:
    import sqlite3
    import sys
    from pathlib import Path

    if "--self-test" in sys.argv:
        return self_test()

    db = Path("/root/gowifi-upp/upp.db")
    conn = sqlite3.connect(db, timeout=30)
    apply_events(conn)
    rows = conn.execute(
        "SELECT exclusive_status, COUNT(*) FROM services GROUP BY exclusive_status"
    ).fetchall()
    print({"exclusive": dict(rows)})
    overlap = conn.execute(
        """SELECT exclusive_status, service_number FROM services
           WHERE exclusive_status IN ('active','suspended','cancelled')"""
    ).fetchall()
    by = {}
    for status, sn in overlap:
        by.setdefault(status, []).append(sn)
    assert_exclusive(by)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
