#!/usr/bin/env python3
"""Follow-up: stop double-write on /auth/session; close all opens; harden stay insert."""
from __future__ import annotations
import pathlib, sys, py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old = '''        if request.method in ("GET", "HEAD") and not request.cookies.get("session"):
            # Skip heavy admin/static paths
            if req_path.startswith("/admin") or req_path.startswith("/api"):
                return await call_next(request)
            path = _client_path_for_session_touch(request)
            if _is_document_page_path_for_hit(path):
                visitor_id = _touch_public_presence(request, path)'''
new = '''        if request.method in ("GET", "HEAD") and not request.cookies.get("session"):
            # Skip heavy admin/static/auth paths (/auth/session records presence itself)
            if (
                req_path.startswith("/admin")
                or req_path.startswith("/api")
                or req_path.startswith("/auth")
            ):
                return await call_next(request)
            path = _client_path_for_session_touch(request)
            if _is_document_page_path_for_hit(path):
                visitor_id = _touch_public_presence(request, path)'''
if old not in text:
    # maybe already partially patched
    if "req_path.startswith(\"/auth\")" in text:
        print("middleware auth skip already present")
    else:
        raise SystemExit("middleware block not found")
else:
    text = text.replace(old, new, 1)

old_close = '''def _close_open_public_page_hit(cur, ip_address: str, at=None) -> None:
    """Close the open page hit for this IP (sets left_at + dwell_seconds)."""
    ip = (ip_address or "").strip()
    if not ip:
        return
    try:
        if at is None:
            cur.execute(
                """
                UPDATE public.public_page_hits
                SET left_at = NOW(),
                    dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - occurred_at))::int)
                WHERE hit_id = (
                    SELECT hit_id FROM public.public_page_hits
                    WHERE ip_address = %s AND left_at IS NULL
                    ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                    LIMIT 1
                )
                """,
                (ip,),
            )
        else:
            cur.execute(
                """
                UPDATE public.public_page_hits
                SET left_at = %s,
                    dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (%s - occurred_at))::int)
                WHERE hit_id = (
                    SELECT hit_id FROM public.public_page_hits
                    WHERE ip_address = %s AND left_at IS NULL
                    ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                    LIMIT 1
                )
                """,
                (at, at, ip),
            )
    except Exception:
        pass'''

new_close = '''def _close_open_public_page_hit(cur, ip_address: str, at=None) -> None:
    """Close all open page hits for this IP (sets left_at + dwell_seconds)."""
    ip = (ip_address or "").strip()
    if not ip:
        return
    try:
        if at is None:
            cur.execute(
                """
                UPDATE public.public_page_hits
                SET left_at = NOW(),
                    dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - occurred_at))::int)
                WHERE ip_address = %s AND left_at IS NULL
                """,
                (ip,),
            )
        else:
            cur.execute(
                """
                UPDATE public.public_page_hits
                SET left_at = %s,
                    dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (%s - occurred_at))::int)
                WHERE ip_address = %s AND left_at IS NULL
                """,
                (at, at, ip),
            )
    except Exception:
        pass'''

if old_close in text:
    text = text.replace(old_close, new_close, 1)
elif "Close all open page hits for this IP" in text:
    print("close-all already present")
else:
    raise SystemExit("close fn not found")

old_rec = '''def _record_url_stay_hit(
    cur,
    *,
    visitor_id: str,
    ip_address: str,
    path: str,
) -> bool:
    """Open one trail row for this URL stay. Skip if already open on same URL.
    Returns True when a new row was inserted.
    """
    ip = (ip_address or "")[:80]
    p = _normalize_traffic_path(path)
    if not ip or not visitor_id or not _is_document_page_path_for_hit(p):
        return False
    open_path = _open_public_page_hit_path(cur, ip)
    if open_path is not None and open_path == p:
        return False
    _close_open_public_page_hit(cur, ip)
    cur.execute(
        """
        INSERT INTO public.public_page_hits
            (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
        VALUES (%s, %s, %s, NOW(), NULL, NULL)
        """,
        (visitor_id, ip, p),
    )
    return True'''

new_rec = '''def _record_url_stay_hit(
    cur,
    *,
    visitor_id: str,
    ip_address: str,
    path: str,
) -> bool:
    """Open one trail row for this URL stay. Skip if already on same URL.
    Returns True when a new row was inserted.
    """
    ip = (ip_address or "")[:80]
    p = _normalize_traffic_path(path)
    if not ip or not visitor_id or not _is_document_page_path_for_hit(p):
        return False
    try:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"traffic:{ip}",))
    except Exception:
        pass
    try:
        cur.execute(
            """
            SELECT path, left_at FROM public.public_page_hits
            WHERE ip_address = %s
            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
            LIMIT 1
            """,
            (ip,),
        )
        row = cur.fetchone()
        if row:
            last_path = row[0] if not isinstance(row, dict) else row.get("path")
            left_at = row[1] if not isinstance(row, dict) else row.get("left_at")
            if last_path is not None and _normalize_traffic_path(str(last_path)) == p:
                if left_at is None:
                    return False
                # Same URL just closed (race / double beacon): keep one stay, reopen
                try:
                    cur.execute(
                        """
                        UPDATE public.public_page_hits
                        SET left_at = NULL, dwell_seconds = NULL
                        WHERE hit_id = (
                            SELECT hit_id FROM public.public_page_hits
                            WHERE ip_address = %s
                            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                            LIMIT 1
                        )
                        """,
                        (ip,),
                    )
                    return False
                except Exception:
                    return False
    except Exception:
        pass
    _close_open_public_page_hit(cur, ip)
    cur.execute(
        """
        INSERT INTO public.public_page_hits
            (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
        VALUES (%s, %s, %s, NOW(), NULL, NULL)
        """,
        (visitor_id, ip, p),
    )
    return True'''

if old_rec in text:
    text = text.replace(old_rec, new_rec, 1)
elif "pg_advisory_xact_lock" in text and "_record_url_stay_hit" in text:
    print("record harden already present")
else:
    raise SystemExit("record fn not found")

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK {API} (+{len(text)-len(orig)} bytes)")
