#!/usr/bin/env python3
"""Record same-page refreshes as page-hit events (public + signed-in)."""
from __future__ import annotations
import pathlib, sys, re

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# --- 1) Helpers for session_page_hits ---
HELPER_MARKER = "def _ensure_session_page_hits_table(cur) -> None:"
HELPER = '''
def _ensure_session_page_hits_table(cur) -> None:
    """Signed-in click trail (incl. refresh on same URL)."""
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.session_page_hits (
                hit_id bigserial PRIMARY KEY,
                session_id text,
                sas_id text,
                ip_address text,
                path text NOT NULL,
                occurred_at timestamptz NOT NULL DEFAULT NOW(),
                user_agent text
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_page_hits_sas_time "
            "ON public.session_page_hits (sas_id, occurred_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_page_hits_ip_time "
            "ON public.session_page_hits (ip_address, occurred_at DESC)"
        )
    except Exception:
        pass


def _is_document_page_path_for_hit(path: Optional[str]) -> bool:
    """True for real browser document URLs we should record (incl. landing + refresh)."""
    p = _sanitize_session_path(path or "/")
    path_only = (p.split("?", 1)[0] or "/").rstrip("/") or "/"
    if path_only in ("/", "/index.html", "/blank.html", "/blank69.html", "/landing.html"):
        return True
    return bool(_is_trackable_page_path(p))


def _record_session_page_hit(
    cur,
    *,
    session_id: str,
    sas_id: Optional[str],
    path: str,
    ip_address: str,
    user_agent: str = "",
) -> None:
    """Insert one click/refresh row for a signed-in user document navigation."""
    if not session_id:
        return
    p = _sanitize_session_path(path)
    if not _is_document_page_path_for_hit(p):
        return
    try:
        _ensure_session_page_hits_table(cur)
        cur.execute(
            """
            INSERT INTO public.session_page_hits
                (session_id, sas_id, ip_address, path, occurred_at, user_agent)
            VALUES (%s, %s, %s, %s, NOW(), %s)
            """,
            (
                (session_id or "")[:120],
                (str(sas_id) if sas_id is not None else None),
                (ip_address or "")[:80],
                p[:500],
                (user_agent or "")[:500],
            ),
        )
    except Exception:
        pass

'''

if HELPER_MARKER in text:
    print("session_page_hits helpers already present")
else:
    # insert after _session_touch_user_activity
    anchor = "def _touch_request_session_path(request: Request, path: str) -> None:"
    if anchor not in text:
        print("ERROR: anchor _touch_request_session_path not found", file=sys.stderr)
        sys.exit(1)
    text = text.replace(anchor, HELPER + "\n" + anchor, 1)
    print("inserted session_page_hits helpers")

# --- 2) Same-URL early return: still record refresh hit ---
OLD_EARLY = '''    # Same URL while still in-session → no last_activity bump (beacons must not fake engagement)
    try:
        if (
            prev_path is not None
            and _sanitize_session_path(str(prev_path)) == p
            and not idle_new_session
        ):
            return
    except Exception:
        pass
'''

NEW_EARLY = '''    # Same URL while still in-session (refresh / revisit): record a new page hit, bump activity.
    try:
        if (
            prev_path is not None
            and _sanitize_session_path(str(prev_path)) == p
            and not idle_new_session
        ):
            try:
                _close_open_public_page_hit(cur, ip)
                cur.execute(
                    """
                    INSERT INTO public.public_page_hits
                        (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
                    VALUES (%s, %s, %s, NOW(), NULL, NULL)
                    """,
                    (visitor_id, ip, p),
                )
                cur.execute(
                    """
                    UPDATE public.public_sessions
                    SET last_activity = NOW(), last_path = %s
                    WHERE visitor_id = %s OR ip_address = %s
                    """,
                    (p, visitor_id, ip),
                )
            except Exception:
                pass
            return
    except Exception:
        pass
'''

if "record a new page hit, bump activity" in text:
    print("same-URL refresh hit already patched")
elif OLD_EARLY in text:
    text = text.replace(OLD_EARLY, NEW_EARLY, 1)
    print("patched same-URL refresh to insert page hit")
else:
    print("WARN: same-URL early return block not found", file=sys.stderr)

# --- 3) Also allow should_hit on refresh if somehow reached ---
OLD_SHOULD = '''        should_hit = last_hit_path is None or _sanitize_session_path(last_hit_path) != p
        if not should_hit and prev_path is None:
            should_hit = True
        if should_hit:
'''

NEW_SHOULD = '''        # Always record a hit for a real upsert (path change OR first hit). Same-URL refresh handled above.
        should_hit = True
        if last_hit_path is not None and _sanitize_session_path(last_hit_path) == p and prev_path is not None:
            # Duplicate path in same upsert pass — still OK (refresh already returned earlier).
            should_hit = True
        if should_hit:
'''

if "Always record a hit for a real upsert" in text:
    print("should_hit already patched")
elif OLD_SHOULD in text:
    text = text.replace(OLD_SHOULD, NEW_SHOULD, 1)
    print("patched should_hit to always record")
else:
    print("WARN: should_hit block not found", file=sys.stderr)

# --- 4) Signed-in middleware: record document GET including refresh ---
OLD_MW = '''    # Update session last_activity and last_path for logged-in users (every API request)
    session_token = request.cookies.get("session")
    if session_token and table_exists("user_sessions"):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            req_path = _client_path_for_session_touch(request)
            _session_touch_user_activity(cur, session_token, req_path)
            # Signed-in ⇒ never appear in Public
            try:
                _ensure_public_sessions_table(cur)
                vid = (request.cookies.get(PUBLIC_VISITOR_COOKIE) or "").strip()
                _purge_public_sessions_known_user(cur, ip_address=_get_client_ip(request), visitor_id=vid)
            except Exception:
                pass
            conn.commit()
        except Exception:
            pass
        finally:
            if conn:
                return_db_connection(conn)
'''

NEW_MW = '''    # Update session last_activity and last_path for logged-in users (every API request)
    session_token = request.cookies.get("session")
    if session_token and table_exists("user_sessions"):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            req_path = _client_path_for_session_touch(request)
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
            # Signed-in ⇒ never appear in Public
            try:
                _ensure_public_sessions_table(cur)
                vid = (request.cookies.get(PUBLIC_VISITOR_COOKIE) or "").strip()
                _purge_public_sessions_known_user(cur, ip_address=_get_client_ip(request), visitor_id=vid)
            except Exception:
                pass
            conn.commit()
        except Exception:
            pass
        finally:
            if conn:
                return_db_connection(conn)
'''

if "_record_session_page_hit(" in text and "Document GET (incl. refresh" in text:
    print("signed-in document hit recording already present")
elif OLD_MW in text:
    text = text.replace(OLD_MW, NEW_MW, 1)
    print("patched signed-in middleware to record document GETs/refreshes")
else:
    print("WARN: signed-in middleware block not found", file=sys.stderr)

if text == orig:
    print("no changes")
    sys.exit(0)
API.write_text(text, encoding="utf-8")
print("wrote", API, "bytes", len(text))
