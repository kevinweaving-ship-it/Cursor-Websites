#!/usr/bin/env python3
"""Read-only Openserve UPP mirror into SQLite.

Does not place orders, change speed, cease, suspend, or run diagnostics.
Secrets stay in the environment / /root/secrets — never in git.
"""
from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = os.environ.get(
    "OPENSERVE_UPP_API",
    "https://partners.openserve.co.za/api/end-points/upp-service-api",
)
ORG_ID = int(os.environ.get("OPENSERVE_ORG_ID", "955"))
DB_PATH = Path(os.environ.get("UPP_DB", "/root/gowifi-upp/upp.db"))
SCHEMA = Path(__file__).with_name("schema.sql")
TOKEN_PATH = Path(os.environ.get("UPP_TOKEN_FILE", "/root/secrets/upp.token"))
SOCKS = os.environ.get("UPP_SOCKS", "")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_token() -> str:
    if os.environ.get("UPP_TOKEN"):
        return os.environ["UPP_TOKEN"].strip()
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    raise SystemExit(f"missing token: set UPP_TOKEN or {TOKEN_PATH}")


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {load_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        }
    )
    if SOCKS:
        s.proxies.update({"http": SOCKS, "https": SOCKS})
    return s


def api_get(s: requests.Session, path: str):
    r = s.get(BASE + path, timeout=45)
    r.raise_for_status()
    return r.json()


def api_post(s: requests.Session, path: str, body: dict):
    r = s.post(BASE + path, json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def kbps(text) -> int | None:
    if not text:
        return None
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return int(digits) if digits else None


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text())
    from status_events import ensure_columns

    ensure_columns(conn)
    return conn


def track_org_field(conn: sqlite3.Connection, org_id: int, field: str, old, new):
    if old == new:
        return
    conn.execute(
        """INSERT INTO organisation_history
           (organisation_id, changed_at, field, old_value, new_value)
           VALUES (?, ?, ?, ?, ?)""",
        (org_id, now(), field, None if old is None else str(old), None if new is None else str(new)),
    )


def upsert_org(conn: sqlite3.Connection, org: dict):
    prev = conn.execute("SELECT * FROM organisations WHERE id=?", (org["id"],)).fetchone()
    fields = {
        "oms_name": org.get("omsName"),
        "oms_code": org.get("omsCode"),
        "cbs_name": org.get("cbsName"),
        "cbs_id": org.get("cbsId"),
        "clarify_ban": org.get("clarifyBan"),
        "customer_code": org.get("customerCode"),
        "status": org.get("status"),
        "isp_volume": org.get("ispVolume"),
        "email_address": org.get("emailAddress"),
        "bundle_transaction_email": org.get("bundleTransactionEmail"),
        "lead_response_email": org.get("leadResponseEmail"),
        "support_email": org.get("supportEmailAddress"),
        "sales_email": org.get("salesEmailAddress"),
    }
    if prev:
        for col, val in fields.items():
            track_org_field(conn, org["id"], col, prev[col], val)
    conn.execute(
        """INSERT INTO organisations (
            id, oms_name, oms_code, cbs_name, cbs_id, clarify_ban, customer_code,
            status, isp_volume, email_address, bundle_transaction_email,
            lead_response_email, support_email, sales_email, raw_json, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            oms_name=excluded.oms_name, oms_code=excluded.oms_code,
            cbs_name=excluded.cbs_name, cbs_id=excluded.cbs_id,
            clarify_ban=excluded.clarify_ban, customer_code=excluded.customer_code,
            status=excluded.status, isp_volume=excluded.isp_volume,
            email_address=excluded.email_address,
            bundle_transaction_email=excluded.bundle_transaction_email,
            lead_response_email=excluded.lead_response_email,
            support_email=excluded.support_email, sales_email=excluded.sales_email,
            raw_json=excluded.raw_json, updated_at=excluded.updated_at
        """,
        (
            org["id"],
            fields["oms_name"],
            fields["oms_code"],
            fields["cbs_name"],
            fields["cbs_id"],
            fields["clarify_ban"],
            fields["customer_code"],
            fields["status"],
            fields["isp_volume"],
            fields["email_address"],
            fields["bundle_transaction_email"],
            fields["lead_response_email"],
            fields["support_email"],
            fields["sales_email"],
            json.dumps(org),
            now(),
        ),
    )


def upsert_user(conn: sqlite3.Connection, user: dict):
    conn.execute(
        """INSERT INTO users (
            user_id, organisation_id, email, first_name, last_name, mobile,
            role, status, is_primary, raw_json, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            organisation_id=excluded.organisation_id, email=excluded.email,
            first_name=excluded.first_name, last_name=excluded.last_name,
            mobile=excluded.mobile, role=excluded.role, status=excluded.status,
            is_primary=excluded.is_primary, raw_json=excluded.raw_json,
            updated_at=excluded.updated_at
        """,
        (
            user.get("userId") or user.get("id"),
            user.get("organisationId"),
            user.get("email"),
            user.get("firstName"),
            user.get("lastName"),
            user.get("mobile"),
            user.get("role"),
            user.get("status"),
            1 if user.get("primary") else 0,
            json.dumps(user),
            now(),
        ),
    )


def upsert_order(conn: sqlite3.Connection, order: dict):
    existing = conn.execute("SELECT id FROM orders WHERE id=?", (order["id"],)).fetchone()
    conn.execute(
        """INSERT INTO orders (
            id, order_number, order_type, order_status, service_number, product,
            speed, end_customer, external_reference, address, placed_by,
            customer_email, created_on, date_implemented, remark, message_for_isp,
            raw_json, first_seen_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            order_number=excluded.order_number, order_type=excluded.order_type,
            order_status=excluded.order_status, service_number=excluded.service_number,
            product=excluded.product, speed=excluded.speed,
            end_customer=excluded.end_customer, external_reference=excluded.external_reference,
            address=excluded.address, placed_by=excluded.placed_by,
            customer_email=excluded.customer_email, created_on=excluded.created_on,
            date_implemented=excluded.date_implemented, remark=excluded.remark,
            message_for_isp=excluded.message_for_isp, raw_json=excluded.raw_json,
            updated_at=excluded.updated_at
        """,
        (
            order["id"],
            order.get("orderNumber"),
            order.get("orderType"),
            order.get("orderStatus"),
            order.get("serviceNumber"),
            order.get("product"),
            order.get("speed"),
            order.get("endCustomer"),
            order.get("externalReference"),
            order.get("address"),
            order.get("placedBy"),
            order.get("customerEmail"),
            order.get("createdOn"),
            order.get("dateImplemented"),
            order.get("remark"),
            order.get("messageForIsp"),
            json.dumps(order),
            now() if not existing else conn.execute(
                "SELECT first_seen_at FROM orders WHERE id=?", (order["id"],)
            ).fetchone()[0],
            now(),
        ),
    )


def lifecycle_of(
    order_status: str | None,
    access: str | None,
    can_access: bool | None,
    customer: str | None = None,
    isp_name: str | None = None,
    validator_message: str | None = None,
    circuit_admin: str | None = None,
) -> str:
    from status_events import exclusive_status

    return exclusive_status(
        {
            "access_status": access,
            "customer": customer,
            "isp_name": isp_name,
            "latest_order_status": order_status,
            "validator_message": validator_message,
            "circuit_admin": circuit_admin,
        }
    )


def record_service_history(conn: sqlite3.Connection, sn: str, lifecycle, access, partner, down, up, note=None):
    prev = conn.execute(
        """SELECT lifecycle, access_status, partner_status, download_kbps, upload_kbps
           FROM services WHERE service_number=?""",
        (sn,),
    ).fetchone()
    if prev and (
        prev["lifecycle"] == lifecycle
        and prev["access_status"] == access
        and prev["partner_status"] == partner
        and prev["download_kbps"] == down
        and prev["upload_kbps"] == up
    ):
        return
    conn.execute(
        """INSERT INTO service_status_history
           (service_number, changed_at, lifecycle, access_status, partner_status,
            download_kbps, upload_kbps, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (sn, now(), lifecycle, access, partner, down, up, note),
    )


def upsert_service(conn, sn, circuit, status, validator, latest_order):
    circuit_data = (circuit or {}).get("data") or {}
    circ = circuit_data.get("circuit") or {}
    attrs = (circ.get("circuitAttributes") or [{}])[0]
    details = circ.get("circuitDetails") or {}
    endpoints = circ.get("circuitEndpoints") or [{}]
    address = (
        ((endpoints[0].get("aSide") or {}).get("computerSideAddress"))
        if endpoints
        else None
    )
    st_list = ((status or {}).get("data") or {}).get("serviceStatus") or [{}]
    st = st_list[0] if st_list else {}
    val = (validator or {}).get("data") or {}
    access = st.get("accessStatus")
    partner = st.get("partnerStatus")
    down = kbps(st.get("serviceSpeed"))
    up = kbps(st.get("uploadSpeed"))
    can_access = val.get("canBeAccessed")
    order_status = (latest_order or {}).get("orderStatus")
    customer = circ.get("customer") or attrs.get("ispName")
    isp_name = val.get("ispName") or attrs.get("ispName")
    validator_message = (validator or {}).get("message")
    circuit_admin = details.get("circuitAdmin")
    life = lifecycle_of(
        order_status,
        access,
        can_access,
        customer,
        isp_name,
        validator_message,
        circuit_admin,
    )
    existing = conn.execute("SELECT first_seen_at FROM services WHERE service_number=?", (sn,)).fetchone()
    record_service_history(conn, sn, life, access, partner, down, up)
    conn.execute(
        """INSERT INTO services (
            service_number, lifecycle, access_status, partner_status, download_kbps,
            upload_kbps, transport_type, circuit_type, customer, isp_name, address,
            can_be_accessed, validator_message, latest_order_id, latest_order_status,
            raw_circuit_json, raw_status_json, first_seen_at, updated_at, circuit_admin
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(service_number) DO UPDATE SET
            lifecycle=excluded.lifecycle, access_status=excluded.access_status,
            partner_status=excluded.partner_status, download_kbps=excluded.download_kbps,
            upload_kbps=excluded.upload_kbps, transport_type=excluded.transport_type,
            circuit_type=excluded.circuit_type, customer=excluded.customer,
            isp_name=excluded.isp_name, address=excluded.address,
            can_be_accessed=excluded.can_be_accessed,
            validator_message=excluded.validator_message,
            latest_order_id=excluded.latest_order_id,
            latest_order_status=excluded.latest_order_status,
            raw_circuit_json=excluded.raw_circuit_json,
            raw_status_json=excluded.raw_status_json, updated_at=excluded.updated_at,
            circuit_admin=excluded.circuit_admin
        """,
        (
            sn,
            life,
            access,
            partner,
            down,
            up,
            st.get("transportType"),
            details.get("circuitType"),
            circ.get("customer") or attrs.get("ispName"),
            val.get("ispName") or attrs.get("ispName"),
            address,
            1 if can_access else 0 if can_access is False else None,
            validator_message,
            (latest_order or {}).get("id"),
            order_status,
            json.dumps(circuit),
            json.dumps(status),
            existing["first_seen_at"] if existing else now(),
            now(),
            circuit_admin,
        ),
    )


def upsert_product(conn: sqlite3.Connection, product: dict):
    conn.execute(
        """INSERT INTO products (sku, name, status, gis_name, raw_json, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            product.get("sku") or product.get("gisProductCode"),
            product.get("name") or product.get("productName"),
            product.get("status"),
            product.get("gisName"),
            json.dumps(product),
            now(),
        ),
    )


def sync(s: requests.Session, conn: sqlite3.Connection) -> dict:
    org = api_get(s, f"/organisations/{ORG_ID}").get("data") or {}
    upsert_org(conn, org)
    users = api_get(s, f"/organisations/{ORG_ID}/users").get("data") or []
    for user in users:
        upsert_user(conn, user)
    orders = (
        api_post(s, "/order/search", {"pageNumber": 1, "pageSize": 200})
        .get("data", {})
        .get("resultSet")
        or []
    )
    latest_by_sn: dict[str, dict] = {}
    for order in orders:
        upsert_order(conn, order)
        sn = order.get("serviceNumber")
        if not sn:
            continue
        prev = latest_by_sn.get(sn)
        if not prev or str(order.get("createdOn") or "") >= str(prev.get("createdOn") or ""):
            latest_by_sn[sn] = order
    for sn, order in latest_by_sn.items():
        circuit = api_get(s, f"/services/{sn}")
        status = api_get(s, f"/services/service-status/{sn}")
        validator = api_get(s, f"/services/validator/service-number/{sn}")
        upsert_service(conn, sn, circuit, status, validator, order)
        time.sleep(0.15)
    products = api_get(s, "/products/name/asc/20/0?searchQuery=").get("resultSet") or []
    conn.execute("DELETE FROM products")
    for product in products:
        upsert_product(conn, product)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from audit_export import build, write
    from invoice_import import ingest_mail
    from status_events import apply_events

    apply_events(conn)
    invoices = ingest_mail(conn)
    write(build(conn))
    return {
        "orders": len(orders),
        "services": len(latest_by_sn),
        "users": len(users),
        "invoices": invoices.get("invoices"),
    }


def _lock_or_skip() -> object | None:
    path = DB_PATH.parent / "sync.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        print(json.dumps({"ok": True, "skipped": "already running"}))
        return None
    return handle


def main() -> int:
    lock = _lock_or_skip()
    if lock is None:
        return 0
    conn = connect()
    run_id = conn.execute(
        """INSERT INTO sync_runs (started_at, initiating_user, box_account, ok)
           VALUES (?, ?, ?, 0)""",
        (
            now(),
            os.environ.get("UPP_INITIATING_USER", "kevinweaving@icloud.com"),
            os.environ.get("UPP_BOX_ACCOUNT", "openserve@gowifi.co.za"),
        ),
    ).lastrowid
    conn.commit()
    try:
        counts = sync(session(), conn)
        conn.execute(
            """UPDATE sync_runs SET finished_at=?, ok=1, orders_upserted=?,
               services_upserted=? WHERE id=?""",
            (now(), counts["orders"], counts["services"], run_id),
        )
        conn.commit()
        summary = {
            "ok": True,
            "db": str(DB_PATH),
            **counts,
            "lifecycle": dict(
                conn.execute(
                    "SELECT lifecycle, COUNT(*) FROM services GROUP BY lifecycle"
                ).fetchall()
            ),
        }
        print(json.dumps(summary, indent=2))
        return 0
    except Exception as exc:
        conn.execute(
            "UPDATE sync_runs SET finished_at=?, ok=0, error=? WHERE id=?",
            (now(), str(exc)[:800], run_id),
        )
        conn.commit()
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    finally:
        conn.close()
        try:
            lock.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
