"""Event class interest API (Stage 2).

Registered sailors: cookie ``session`` → user_sessions → user_accounts.
Anonymous visitors: cookie-only ``ssa_vid`` (never IP-based public visitor resolver).

Routes are attached via ``register_event_interest_routes(...)``.
This module does **not** patch ``api.py`` — that requires separate approval.
"""

from __future__ import annotations

import re
import secrets
import threading
from typing import Any, Optional

import psycopg2.extras
from fastapi import Request
from fastapi.responses import JSONResponse

from sailingsa.backend.event_interest_schema import apply_schema

PUBLIC_VISITOR_COOKIE = "ssa_vid"
SESSION_COOKIE = "session"
_VISITOR_RE = re.compile(r"^[a-f0-9]{32}$")
_IDENT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False


class InterestError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def ensure_schema(conn) -> None:
    """Idempotent schema ensure for disposable/test envs. Safe CREATE IF NOT EXISTS."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        apply_schema(conn)
        _SCHEMA_READY = True


def reset_schema_ready_flag() -> None:
    """Test helper only."""
    global _SCHEMA_READY
    _SCHEMA_READY = False


def _token(request: Request) -> str:
    return (request.cookies.get(SESSION_COOKIE) or "").strip()


def session_account(conn, token: str) -> Optional[dict]:
    """Resolve authenticated sailor from session cookie. Never trust client account_id."""
    if not token:
        return None
    cur = _cur(conn)
    try:
        cur.execute(
            """
            SELECT s.account_id, s.sas_id, ua.role
            FROM public.user_sessions s
            JOIN public.user_accounts ua ON ua.account_id = s.account_id
            WHERE s.session_id = %s
              AND s.expires_at > NOW()
              AND COALESCE(s.is_active, true) IS TRUE
              AND COALESCE(ua.is_active, true) IS TRUE
            """,
            (token,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
    if not row:
        return None
    return {
        "account_id": int(row["account_id"]),
        "sas_id": row.get("sas_id"),
        "role": (row.get("role") or "").strip().lower() or "sailor",
    }


def cookie_only_ssa_vid(request: Request) -> tuple[str, bool]:
    """Return (visitor_id, is_new). Cookie value only — never IP fingerprinting."""
    raw = (request.cookies.get(PUBLIC_VISITOR_COOKIE) or "").strip().lower()
    if _VISITOR_RE.fullmatch(raw):
        return raw, False
    return secrets.token_hex(16), True


def _normalize_identifier(value: Any) -> str:
    if not isinstance(value, str):
        raise InterestError(400, "class_identifier is required")
    ident = value.strip().lower()
    if not _IDENT_RE.fullmatch(ident):
        raise InterestError(400, "Invalid class_identifier")
    return ident


def _parse_event_id(value: Any) -> int:
    try:
        eid = int(value)
    except (TypeError, ValueError):
        raise InterestError(400, "Invalid event_id") from None
    if eid <= 0:
        raise InterestError(400, "Invalid event_id")
    return eid


def _event_exists(cur, event_id: int) -> bool:
    cur.execute("SELECT 1 FROM public.events WHERE event_id = %s", (event_id,))
    return cur.fetchone() is not None


def resolve_edition_class(cur, event_id: int, class_identifier: str) -> dict:
    """Validate class belongs to event; resolve canonical class_id when possible.

    Unmapped labels (e.g. Junior) remain selectable with class_id NULL.
    """
    cur.execute(
        """
        SELECT eec.event_id,
               eec.class_identifier,
               eec.class_display_name,
               eec.sort_order,
               eec.extras,
               CASE
                 WHEN (eec.extras->>'class_id') ~ '^[0-9]+$'
                   THEN (eec.extras->>'class_id')::integer
                 ELSE NULL
               END AS extras_class_id
        FROM public.event_edition_classes eec
        WHERE eec.event_id = %s
          AND eec.class_identifier = %s
        """,
        (event_id, class_identifier),
    )
    row = cur.fetchone()
    if not row:
        raise InterestError(400, "Class is not configured for this event")

    class_id = row.get("extras_class_id")
    if class_id is not None:
        cur.execute(
            "SELECT class_id, class_name, logo_path, icon_path FROM public.classes WHERE class_id = %s",
            (class_id,),
        )
        klass = cur.fetchone()
        if not klass:
            class_id = None
    else:
        # Best-effort name match only — never invent a class row.
        display = (row.get("class_display_name") or "").strip()
        klass = None
        if display:
            cur.execute(
                """
                SELECT class_id, class_name, logo_path, icon_path
                FROM public.classes
                WHERE lower(class_name) = lower(%s)
                LIMIT 1
                """,
                (display,),
            )
            klass = cur.fetchone()
            if klass:
                class_id = int(klass["class_id"])

    logo = None
    if klass:
        logo = klass.get("logo_path") or klass.get("icon_path")

    return {
        "event_id": event_id,
        "class_identifier": row["class_identifier"],
        "class_display_name": row.get("class_display_name") or row["class_identifier"],
        "sort_order": int(row.get("sort_order") or 0),
        "class_id": int(class_id) if class_id is not None else None,
        "logo_path": logo,
    }


def list_edition_classes(cur, event_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT eec.class_identifier,
               eec.class_display_name,
               eec.sort_order,
               eec.extras,
               CASE
                 WHEN (eec.extras->>'class_id') ~ '^[0-9]+$'
                   THEN (eec.extras->>'class_id')::integer
                 ELSE NULL
               END AS extras_class_id
        FROM public.event_edition_classes eec
        WHERE eec.event_id = %s
        ORDER BY eec.sort_order, eec.class_identifier
        """,
        (event_id,),
    )
    rows = cur.fetchall() or []
    out = []
    for row in rows:
        resolved = resolve_edition_class(cur, event_id, row["class_identifier"])
        out.append(resolved)
    return out


def _rate_limit_write(cur, *, account_id: Optional[int], visitor_id: Optional[str]) -> None:
    if account_id is not None:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM public.event_class_interest_history
            WHERE account_id = %s
              AND created_at > NOW() - INTERVAL '1 minute'
            """,
            (account_id,),
        )
    else:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM public.event_class_interest_history
            WHERE visitor_id = %s
              AND created_at > NOW() - INTERVAL '1 minute'
            """,
            (visitor_id,),
        )
    n = int((cur.fetchone() or {}).get("n") or 0)
    if n >= 30:
        raise InterestError(429, "Too many interest updates; try again shortly")


def interest_snapshot(cur, event_id: int, *, account_id=None, visitor_id=None) -> dict:
    cur.execute(
        """
        SELECT COALESCE(SUM(interested_count), 0)::bigint AS total
        FROM public.event_class_interest_counts
        WHERE event_id = %s
        """,
        (event_id,),
    )
    total = int((cur.fetchone() or {}).get("total") or 0)

    cur.execute(
        """
        SELECT c.class_identifier,
               c.class_id,
               c.interested_count,
               eec.class_display_name,
               cl.logo_path,
               cl.icon_path
        FROM public.event_class_interest_counts c
        LEFT JOIN public.event_edition_classes eec
          ON eec.event_id = c.event_id AND eec.class_identifier = c.class_identifier
        LEFT JOIN public.classes cl ON cl.class_id = c.class_id
        WHERE c.event_id = %s
        ORDER BY c.interested_count DESC, c.class_identifier ASC
        """,
        (event_id,),
    )
    classes = []
    for row in cur.fetchall() or []:
        classes.append(
            {
                "class_identifier": row["class_identifier"],
                "class_display_name": row.get("class_display_name") or row["class_identifier"],
                "class_id": int(row["class_id"]) if row.get("class_id") is not None else None,
                "interested_count": int(row["interested_count"]),
                "logo_path": row.get("logo_path") or row.get("icon_path"),
            }
        )

    sum_classes = sum(c["interested_count"] for c in classes)
    if sum_classes != total:
        # Prefer identity of active rows if views diverge (should not happen).
        cur.execute(
            """
            SELECT COUNT(*)::bigint AS total
            FROM public.event_class_interest
            WHERE event_id = %s AND status = 'active'
            """,
            (event_id,),
        )
        total = int((cur.fetchone() or {}).get("total") or 0)

    mine = None
    if account_id is not None:
        cur.execute(
            """
            SELECT status, class_identifier, class_id
            FROM public.event_class_interest
            WHERE event_id = %s AND account_id = %s
            """,
            (event_id, account_id),
        )
    elif visitor_id:
        cur.execute(
            """
            SELECT status, class_identifier, class_id
            FROM public.event_class_interest
            WHERE event_id = %s AND visitor_id = %s
            """,
            (event_id, visitor_id),
        )
    else:
        cur.execute("SELECT NULL WHERE FALSE")

    row = cur.fetchone()
    if row:
        mine = {
            "status": row["status"],
            "class_identifier": row.get("class_identifier"),
            "class_id": int(row["class_id"]) if row.get("class_id") is not None else None,
            "interested": row["status"] == "active",
        }

    return {
        "event_id": event_id,
        "total_interested": total,
        "classes": classes,
        "mine": mine,
    }


def get_interest(conn, event_id: int, *, account=None, visitor_id=None) -> dict:
    eid = _parse_event_id(event_id)
    cur = _cur(conn)
    try:
        if not _event_exists(cur, eid):
            raise InterestError(404, "Event not found")
        return interest_snapshot(
            cur,
            eid,
            account_id=account["account_id"] if account else None,
            visitor_id=None if account else visitor_id,
        )
    finally:
        cur.close()


def get_interest_batch(conn, event_ids: list[int], *, account=None, visitor_id=None) -> dict:
    cur = _cur(conn)
    try:
        out = {}
        for raw in event_ids:
            eid = _parse_event_id(raw)
            if not _event_exists(cur, eid):
                continue
            out[str(eid)] = interest_snapshot(
                cur,
                eid,
                account_id=account["account_id"] if account else None,
                visitor_id=None if account else visitor_id,
            )
        return {"events": out}
    finally:
        cur.close()


def get_interest_classes(conn, event_id: int) -> dict:
    eid = _parse_event_id(event_id)
    cur = _cur(conn)
    try:
        if not _event_exists(cur, eid):
            raise InterestError(404, "Event not found")
        classes = list_edition_classes(cur, eid)
        snap = interest_snapshot(cur, eid)
        counts = {c["class_identifier"]: c["interested_count"] for c in snap["classes"]}
        for c in classes:
            c["interested_count"] = int(counts.get(c["class_identifier"], 0))
        return {
            "event_id": eid,
            "total_interested": snap["total_interested"],
            "classes": classes,
        }
    finally:
        cur.close()


def set_interest(conn, event_id: int, class_identifier: str, *, account=None, visitor_id=None) -> dict:
    eid = _parse_event_id(event_id)
    ident = _normalize_identifier(class_identifier)
    if not account and not (visitor_id and _VISITOR_RE.fullmatch(visitor_id)):
        raise InterestError(401, "Visitor identity required")

    cur = _cur(conn)
    try:
        if not _event_exists(cur, eid):
            raise InterestError(404, "Event not found")
        resolved = resolve_edition_class(cur, eid, ident)
        _rate_limit_write(
            cur,
            account_id=account["account_id"] if account else None,
            visitor_id=None if account else visitor_id,
        )
        cur.execute(
            """
            SELECT interest_id, status, class_identifier, class_id
            FROM public.eci_upsert_interest(
                %s, %s, %s, %s, %s, %s::jsonb
            )
            """,
            (
                eid,
                resolved["class_identifier"],
                account["account_id"] if account else None,
                None if account else visitor_id,
                resolved["class_id"],
                "{}",
            ),
        )
        row = cur.fetchone()
        snap = interest_snapshot(
            cur,
            eid,
            account_id=account["account_id"] if account else None,
            visitor_id=None if account else visitor_id,
        )
        snap["updated"] = {
            "interest_id": int(row["interest_id"]),
            "status": row["status"],
            "class_identifier": row["class_identifier"],
            "class_id": int(row["class_id"]) if row.get("class_id") is not None else None,
        }
        return snap
    finally:
        cur.close()


def withdraw_interest(conn, event_id: int, *, account=None, visitor_id=None) -> dict:
    eid = _parse_event_id(event_id)
    if not account and not (visitor_id and _VISITOR_RE.fullmatch(visitor_id)):
        raise InterestError(401, "Visitor identity required")
    cur = _cur(conn)
    try:
        if not _event_exists(cur, eid):
            raise InterestError(404, "Event not found")
        _rate_limit_write(
            cur,
            account_id=account["account_id"] if account else None,
            visitor_id=None if account else visitor_id,
        )
        if account:
            cur.execute(
                """
                SELECT interest_id FROM public.event_class_interest
                WHERE event_id = %s AND account_id = %s
                """,
                (eid, account["account_id"]),
            )
        else:
            cur.execute(
                """
                SELECT interest_id FROM public.event_class_interest
                WHERE event_id = %s AND visitor_id = %s
                """,
                (eid, visitor_id),
            )
        if not cur.fetchone():
            raise InterestError(404, "No interest to withdraw")

        cur.execute(
            """
            SELECT interest_id, status, class_identifier, class_id
            FROM public.eci_withdraw_interest(%s, %s, %s, %s::jsonb)
            """,
            (
                eid,
                account["account_id"] if account else None,
                None if account else visitor_id,
                "{}",
            ),
        )
        row = cur.fetchone()

        snap = interest_snapshot(
            cur,
            eid,
            account_id=account["account_id"] if account else None,
            visitor_id=None if account else visitor_id,
        )
        snap["updated"] = {
            "interest_id": int(row["interest_id"]),
            "status": row["status"],
            "class_identifier": row.get("class_identifier"),
            "class_id": int(row["class_id"]) if row.get("class_id") is not None else None,
        }
        return snap
    finally:
        cur.close()


def reconcile_on_login(conn, *, account: dict, visitor_id: Optional[str]) -> dict:
    """Move/withdraw visitor interests for this ssa_vid onto the sailor account."""
    if not account:
        raise InterestError(401, "Sign in required")
    if not visitor_id or not _VISITOR_RE.fullmatch(visitor_id):
        return {"reconciled": 0, "visitor_id": None}
    cur = _cur(conn)
    try:
        cur.execute(
            "SELECT public.eci_reconcile_visitor_to_account(%s, %s, %s::jsonb)",
            (visitor_id, account["account_id"], "{}"),
        )
        moved = int(cur.fetchone()["eci_reconcile_visitor_to_account"])
        return {"reconciled": moved, "visitor_id": visitor_id, "account_id": account["account_id"]}
    finally:
        cur.close()


def register_event_interest_routes(app, get_db_connection, return_db_connection):
    """Attach /api/events/.../interest routes. Does not modify api.py by itself."""

    def _emit(payload, status, visitor, is_new):
        response = JSONResponse(payload, status_code=status)
        if is_new:
            response.set_cookie(
                PUBLIC_VISITOR_COOKIE,
                visitor,
                max_age=31536000,
                httponly=True,
                samesite="lax",
                secure=True,
                path="/",
            )
        return response

    def _run(request: Request, handler, *, write: bool = False):
        visitor, is_new = cookie_only_ssa_vid(request)
        request.state.ssa_vid = visitor
        conn = get_db_connection()
        try:
            ensure_schema(conn)
            account = session_account(conn, _token(request))
            # Login reconciliation: when a sailor is signed in and a visitor cookie
            # still owns interests, merge without double-counting.
            if account and visitor:
                try:
                    reconcile_on_login(conn, account=account, visitor_id=visitor)
                except InterestError:
                    pass
            result = handler(conn, account, visitor)
            conn.commit()
            return _emit(result, 200, visitor, is_new)
        except InterestError as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            return _emit({"detail": exc.detail}, exc.status, visitor, is_new)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            print("[event_interest] request failed", flush=True)
            raise
        finally:
            return_db_connection(conn)

    @app.get("/api/events/interest")
    def events_interest_batch(request: Request):
        raw = (request.query_params.get("ids") or "").strip()

        def handler(conn, account, visitor):
            if not raw:
                raise InterestError(400, "ids query parameter is required")
            ids = []
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                ids.append(_parse_event_id(part))
            if not ids:
                raise InterestError(400, "ids query parameter is required")
            if len(ids) > 50:
                raise InterestError(400, "Too many event ids")
            return get_interest_batch(conn, ids, account=account, visitor_id=visitor)

        return _run(request, handler)

    @app.get("/api/events/{event_id}/interest")
    def event_interest_get(event_id: int, request: Request):
        def handler(conn, account, visitor):
            return get_interest(conn, event_id, account=account, visitor_id=visitor)

        return _run(request, handler)

    @app.get("/api/events/{event_id}/interest/classes")
    def event_interest_classes(event_id: int, request: Request):
        def handler(conn, account, visitor):
            del account, visitor
            return get_interest_classes(conn, event_id)

        return _run(request, handler)

    @app.post("/api/events/{event_id}/interest")
    async def event_interest_set(event_id: int, request: Request):
        body = {}
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}

        def handler(conn, account, visitor):
            return set_interest(
                conn,
                event_id,
                body.get("class_identifier"),
                account=account,
                visitor_id=visitor,
            )

        return _run(request, handler, write=True)

    @app.post("/api/events/{event_id}/interest/withdraw")
    def event_interest_withdraw(event_id: int, request: Request):
        def handler(conn, account, visitor):
            return withdraw_interest(conn, event_id, account=account, visitor_id=visitor)

        return _run(request, handler, write=True)

    @app.post("/api/events/interest/reconcile")
    def event_interest_reconcile(request: Request):
        def handler(conn, account, visitor):
            if not account:
                raise InterestError(401, "Sign in required")
            return reconcile_on_login(conn, account=account, visitor_id=visitor)

        return _run(request, handler, write=True)

    return {
        "routes": [
            "GET /api/events/interest",
            "GET /api/events/{event_id}/interest",
            "GET /api/events/{event_id}/interest/classes",
            "POST /api/events/{event_id}/interest",
            "POST /api/events/{event_id}/interest/withdraw",
            "POST /api/events/interest/reconcile",
        ],
        "note": "Call register_event_interest_routes from api.py only after separate approval.",
    }
