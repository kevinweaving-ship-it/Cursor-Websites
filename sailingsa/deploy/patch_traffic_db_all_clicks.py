#!/usr/bin/env python3
"""Persist every signed-in navigation (SPA path change + refresh) into traffic DB tables.

- session_page_hits: signed-in click trail
- public_page_hits: unified traffic hit store (staff still excluded from public aggregates by IP)
"""
from __future__ import annotations
import pathlib, sys

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

OLD_TOUCH = '''def _session_touch_user_activity(cur, session_token: str, path: str) -> None:
    """Set last_activity = now; update last_path only for real page paths."""
    if not session_token or not table_exists("user_sessions"):
        return
    p = _sanitize_session_path(path)
    track = _is_trackable_page_path(p)
    try:
        if column_exists("user_sessions", "last_path") and track:
            cur.execute(
                """
                UPDATE public.user_sessions
                SET last_activity = NOW(), last_path = %s
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (p, session_token),
            )
        else:
            cur.execute(
                """
                UPDATE public.user_sessions
                SET last_activity = NOW()
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (session_token,),
            )
    except Exception:
        pass
'''

NEW_TOUCH = '''def _session_touch_user_activity(
    cur,
    session_token: str,
    path: str,
    *,
    ip_address: str = "",
    user_agent: str = "",
    force_hit: bool = False,
) -> None:
    """Set last_activity = now; update last_path; persist navigations into traffic DB.

    Records session_page_hits + public_page_hits when:
    - path changed (SPA click / new page), or
    - force_hit=True (document GET / refresh on same URL).
    Heartbeat polls with the same path do not create duplicate rows.
    """
    if not session_token or not table_exists("user_sessions"):
        return
    p = _sanitize_session_path(path)
    track = _is_document_page_path_for_hit(p)
    prev_path = None
    sas_id = None
    try:
        cols = "sas_id::text AS sas_id"
        if column_exists("user_sessions", "last_path"):
            cols = "last_path, sas_id::text AS sas_id"
        cur.execute(
            f"""
            SELECT {cols}
            FROM public.user_sessions
            WHERE session_id = %s AND expires_at > NOW()
            LIMIT 1
            """,
            (session_token,),
        )
        row = cur.fetchone()
        if row:
            if isinstance(row, dict):
                prev_path = row.get("last_path")
                sas_id = row.get("sas_id")
            else:
                if column_exists("user_sessions", "last_path"):
                    prev_path, sas_id = row[0], row[1]
                else:
                    sas_id = row[0]
    except Exception:
        prev_path = None
        sas_id = None
    try:
        if column_exists("user_sessions", "last_path") and track:
            cur.execute(
                """
                UPDATE public.user_sessions
                SET last_activity = NOW(), last_path = %s
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (p, session_token),
            )
        else:
            cur.execute(
                """
                UPDATE public.user_sessions
                SET last_activity = NOW()
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (session_token,),
            )
    except Exception:
        pass
    # Persist into traffic DB (signed-in click trail + unified page hits)
    try:
        if not track:
            return
        prev_s = _sanitize_session_path(str(prev_path)) if prev_path is not None else None
        path_changed = prev_s != p
        if not (force_hit or path_changed):
            return
        _record_session_page_hit(
            cur,
            session_id=session_token,
            sas_id=sas_id,
            path=p,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
        )
        # Unified traffic store (aggregates still exclude staff IPs in lean SQL)
        try:
            _ensure_public_sessions_table(cur)
            vid = f"sess:{(session_token or '')[:32]}"
            ip = (ip_address or "")[:80]
            if ip:
                try:
                    _close_open_public_page_hit(cur, ip)
                except Exception:
                    pass
                cur.execute(
                    """
                    INSERT INTO public.public_page_hits
                        (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
                    VALUES (%s, %s, %s, NOW(), NULL, NULL)
                    """,
                    (vid, ip, p),
                )
        except Exception:
            pass
    except Exception:
        pass
'''

if "force_hit: bool = False" in text and "Persist into traffic DB" in text:
    print("session touch already records traffic DB hits")
else:
    if OLD_TOUCH not in text:
        print("ERROR: _session_touch_user_activity block not found", file=sys.stderr)
        sys.exit(1)
    text = text.replace(OLD_TOUCH, NEW_TOUCH, 1)
    print("patched _session_touch_user_activity to write traffic DB")

# Rewrite middleware block to use path-change + document force_hit
OLD_MW = '''            req_path = _client_path_for_session_touch(request)
            _session_touch_user_activity(cur, session_token, req_path)
            # Document GET (incl. refresh on same URL) → permanent click row
            try:
                doc_path = request.url.path or "/"
                if (
                    request.method == "GET"
                    and _is_document_page_path_for_hit(doc_path)
                    and not doc_path.startswith("/api/")
                    and not doc_path.startswith("/auth/")
                    and not doc_path.startswith("/admin/api")
                ):
                    sas_row = None
                    try:
                        cur.execute(
                            """
                            SELECT sas_id::text AS sas_id FROM public.user_sessions
                            WHERE session_id = %s AND expires_at > NOW()
                            LIMIT 1
                            """,
                            (session_token,),
                        )
                        sas_row = cur.fetchone()
                    except Exception:
                        sas_row = None
                    sas_id = None
                    if sas_row:
                        sas_id = sas_row[0] if not isinstance(sas_row, dict) else sas_row.get("sas_id")
                    ua = ""
                    try:
                        ua = request.headers.get("user-agent", "") or ""
                    except Exception:
                        ua = ""
                    _record_session_page_hit(
                        cur,
                        session_id=session_token,
                        sas_id=sas_id,
                        path=doc_path,
                        ip_address=_get_client_ip(request),
                        user_agent=ua,
                    )
            except Exception:
                pass
'''

NEW_MW = '''            req_path = _client_path_for_session_touch(request)
            doc_path = request.url.path or "/"
            ua = ""
            try:
                ua = request.headers.get("user-agent", "") or ""
            except Exception:
                ua = ""
            ip = _get_client_ip(request)
            is_document_get = (
                request.method == "GET"
                and _is_document_page_path_for_hit(doc_path)
                and not doc_path.startswith("/api/")
                and not doc_path.startswith("/auth/")
                and not doc_path.startswith("/admin/api")
            )
            # SPA navigations send ?path= on /auth/session; document GET/refresh uses url.path
            touch_path = doc_path if is_document_get else req_path
            _session_touch_user_activity(
                cur,
                session_token,
                touch_path,
                ip_address=ip,
                user_agent=ua,
                force_hit=bool(is_document_get),
            )
'''

if "is_document_get = (" in text and "touch_path = doc_path if is_document_get" in text:
    print("middleware already uses SPA path-change recording")
elif OLD_MW in text:
    text = text.replace(OLD_MW, NEW_MW, 1)
    print("patched middleware for SPA + refresh traffic DB writes")
else:
    print("WARN: middleware record block not found", file=sys.stderr)

if text == orig:
    print("no changes")
    sys.exit(0)
API.write_text(text, encoding="utf-8")
print("wrote", API)
