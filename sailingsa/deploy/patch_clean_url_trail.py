#!/usr/bin/env python3
"""Clean traffic trail: one row per URL stay + dwell; session IP/user + device/browser.

Rules:
- Session start stores IP (+ login if signed-in), UA, device_type, browser.
- New public_page_hits / session_page_hits only when shown URL changes (or first page).
- Same-URL auth/session heartbeats and refreshes only bump last_activity — no new rows.
- Leave / next URL / idle session close open hit (left_at + dwell_seconds).
- Landing `/` is a real page stay.
"""
from __future__ import annotations

import pathlib
import sys

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER = '''
def _normalize_traffic_path(path: Optional[str]) -> str:
    """Canonical path for trail rows (landing aliases → /)."""
    p = _sanitize_session_path(path or "/")
    path_only = (p.split("?", 1)[0] or "/").rstrip("/") or "/"
    if path_only in ("/index.html", "/blank.html", "/blank69.html", "/landing.html"):
        return "/"
    return path_only


def _traffic_ua_meta(user_agent: str) -> tuple:
    """Return (device_type, browser) for session start — phone/tablet/pc + browser name."""
    u = (user_agent or "").lower()
    if "ipad" in u or "tablet" in u or "kindle" in u or "silk" in u:
        device = "tablet"
    elif "mobi" in u or "iphone" in u or "ipod" in u or ("android" in u and "mobile" in u):
        device = "phone"
    elif "android" in u:
        device = "tablet"
    else:
        device = "pc"
    if "edg/" in u or "edge/" in u:
        browser = "Edge"
    elif "crios/" in u or ("chrome/" in u and "chromium" not in u and "edg/" not in u):
        browser = "Chrome"
    elif "fxios/" in u or "firefox/" in u:
        browser = "Firefox"
    elif "safari/" in u and "chrome/" not in u and "crios/" not in u:
        browser = "Safari"
    else:
        browser = "Other"
    return device, browser


def _open_public_page_hit_path(cur, ip_address: str) -> Optional[str]:
    """Path of the currently open (left_at IS NULL) hit for this IP, if any."""
    ip = (ip_address or "").strip()
    if not ip:
        return None
    try:
        cur.execute(
            """
            SELECT path FROM public.public_page_hits
            WHERE ip_address = %s AND left_at IS NULL
            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
            LIMIT 1
            """,
            (ip,),
        )
        row = cur.fetchone()
        if not row:
            return None
        raw = row[0] if not isinstance(row, dict) else row.get("path")
        return _normalize_traffic_path(str(raw)) if raw is not None else None
    except Exception:
        return None


def _record_url_stay_hit(
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
    return True

'''

# Insert helpers after _is_document_page_path_for_hit
MARK = "def _is_document_page_path_for_hit(path: Optional[str]) -> bool:"
if MARK not in text:
    raise SystemExit("missing _is_document_page_path_for_hit")
if "_normalize_traffic_path" not in text:
    # insert after the short function body
    old_doc = '''def _is_document_page_path_for_hit(path: Optional[str]) -> bool:
    """True for real browser document URLs we should record (incl. landing + refresh)."""
    p = _sanitize_session_path(path or "/")
    path_only = (p.split("?", 1)[0] or "/").rstrip("/") or "/"
    if path_only in ("/", "/index.html", "/blank.html", "/blank69.html", "/landing.html"):
        return True
    return bool(_is_trackable_page_path(p))
'''
    if old_doc not in text:
        raise SystemExit("document path fn body mismatch")
    text = text.replace(old_doc, old_doc + "\n" + HELPER, 1)

# --- replace _session_touch_user_activity ---
OLD_TOUCH_START = "def _session_touch_user_activity("
OLD_TOUCH_END = "def _ensure_session_page_hits_table("
i0 = text.index(OLD_TOUCH_START)
i1 = text.index(OLD_TOUCH_END)
NEW_TOUCH = '''def _session_touch_user_activity(
    cur,
    session_token: str,
    path: str,
    *,
    ip_address: str = "",
    user_agent: str = "",
    force_hit: bool = False,
) -> None:
    """Touch signed-in session; record URL stay only when path changes.

    force_hit is ignored for inserts (refresh/heartbeat must not spam trail rows).
    """
    if not session_token or not table_exists("user_sessions"):
        return
    p = _normalize_traffic_path(path)
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
    # Trail: only on real URL change (ignore force_hit / same-URL refresh)
    try:
        if not track:
            return
        prev_s = _normalize_traffic_path(str(prev_path)) if prev_path is not None else None
        path_changed = prev_s != p
        if not path_changed:
            # Still ensure open hit exists once for this URL (first touch after deploy)
            ip = (ip_address or "")[:80]
            if ip and _open_public_page_hit_path(cur, ip) is None:
                path_changed = True
            else:
                return
        _record_session_page_hit(
            cur,
            session_id=session_token,
            sas_id=sas_id,
            path=p,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
        )
        try:
            _ensure_public_sessions_table(cur)
            vid = f"sess:{(session_token or '')[:32]}"
            ip = (ip_address or "")[:80]
            if ip:
                _record_url_stay_hit(cur, visitor_id=vid, ip_address=ip, path=p)
        except Exception:
            pass
    except Exception:
        pass


'''
text = text[:i0] + NEW_TOUCH + text[i1:]

# --- ensure table: add device_type / browser ---
ENSURE_ADD = '''
        try:
            cur.execute("ALTER TABLE public.public_sessions ADD COLUMN IF NOT EXISTS device_type text")
            cur.execute("ALTER TABLE public.public_sessions ADD COLUMN IF NOT EXISTS browser text")
            cur.execute("ALTER TABLE public.public_visit_sessions ADD COLUMN IF NOT EXISTS device_type text")
            cur.execute("ALTER TABLE public.public_visit_sessions ADD COLUMN IF NOT EXISTS browser text")
            cur.execute("ALTER TABLE public.public_visit_sessions ADD COLUMN IF NOT EXISTS start_path text")
        except Exception:
            pass
'''
anchor = '''        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_public_visit_sessions_open ON public.public_visit_sessions (ip_address) WHERE ended_at IS NULL"
        )
        _PUBLIC_SESSIONS_READY = True'''
if "device_type text" not in text.split("def _ensure_public_sessions_table")[1].split("def _is_noise_public_ip")[0]:
    if anchor not in text:
        raise SystemExit("ensure table anchor missing")
    text = text.replace(
        anchor,
        '''        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_public_visit_sessions_open ON public.public_visit_sessions (ip_address) WHERE ended_at IS NULL"
        )
'''
        + ENSURE_ADD
        + '''
        _PUBLIC_SESSIONS_READY = True''',
        1,
    )

# --- replace _upsert_public_session entirely ---
u0 = text.index("def _upsert_public_session(")
u1 = text.index("def _public_heading_stats(")
NEW_UPSERT = '''def _upsert_public_session(cur, visitor_id: str, path: str, user_agent: str, ip_address: str) -> None:
    """Upsert anonymous visitor session; one trail row per URL stay + dwell."""
    if not visitor_id or not _is_document_page_path_for_hit(path):
        return
    if _is_bot_user_agent(user_agent):
        return
    if _is_noise_public_ip(ip_address):
        return
    try:
        if _is_sailor_sas_id_path(path) and ip_address:
            _lean_quarantine_ip(cur, ip_address, "sailor_sas_id_url")
    except Exception:
        pass
    try:
        if _lean_ip_is_cloud_datacenter(ip_address) and not _lean_human_traffic_pass(user_agent, path):
            _lean_quarantine_ip(cur, ip_address, "cloud_datacenter")
    except Exception:
        pass
    p = _normalize_traffic_path(path)
    ip = (ip_address or "")[:80]
    ua = (user_agent or "")[:500]
    device_type, browser = _traffic_ua_meta(ua)
    prev_path = None
    prev_last_activity = None
    idle_new_session = True
    try:
        cur.execute(
            """
            SELECT visitor_id, last_path, last_activity
            FROM public.public_sessions
            WHERE ip_address = %s
            ORDER BY last_activity DESC NULLS LAST
            LIMIT 1
            """,
            (ip,),
        )
        row = cur.fetchone()
        if row:
            existing_vid = row[0] if not isinstance(row, dict) else row.get("visitor_id")
            prev_path = (row[1] if not isinstance(row, dict) else row.get("last_path")) or None
            prev_last_activity = row[2] if not isinstance(row, dict) else row.get("last_activity")
            if existing_vid:
                visitor_id = str(existing_vid)
            if prev_last_activity is not None:
                try:
                    cur.execute(
                        "SELECT (%s >= NOW() - INTERVAL '30 minutes') AS live",
                        (prev_last_activity,),
                    )
                    live_row = cur.fetchone()
                    live = False
                    if live_row:
                        live = bool(live_row[0] if not isinstance(live_row, dict) else live_row.get("live"))
                    idle_new_session = not live
                except Exception:
                    idle_new_session = True
    except Exception:
        pass

    prev_s = _normalize_traffic_path(str(prev_path)) if prev_path is not None else None
    same_url = (prev_s == p) and (not idle_new_session)

    # Same URL heartbeat: bump activity only — never spam new hit rows
    if same_url:
        try:
            cur.execute(
                """
                UPDATE public.public_sessions
                SET last_activity = NOW(),
                    last_path = %s,
                    user_agent = COALESCE(NULLIF(%s, ''), user_agent),
                    device_type = COALESCE(device_type, %s),
                    browser = COALESCE(browser, %s)
                WHERE visitor_id = %s OR ip_address = %s
                """,
                (p, ua, device_type, browser, visitor_id, ip),
            )
        except Exception:
            try:
                cur.execute(
                    """
                    UPDATE public.public_sessions
                    SET last_activity = NOW(), last_path = %s,
                        user_agent = COALESCE(NULLIF(%s, ''), user_agent)
                    WHERE visitor_id = %s OR ip_address = %s
                    """,
                    (p, ua, visitor_id, ip),
                )
            except Exception:
                pass
        # If somehow no open hit (legacy), open one once
        try:
            if _open_public_page_hit_path(cur, ip) is None:
                _record_url_stay_hit(cur, visitor_id=visitor_id, ip_address=ip, path=p)
        except Exception:
            pass
        return

    cur.execute(
        """
        INSERT INTO public.public_sessions
            (visitor_id, created_at, last_activity, last_path, user_agent, ip_address, first_seen_at)
        VALUES (%s, NOW(), NOW(), %s, %s, %s, NOW())
        ON CONFLICT (visitor_id) DO UPDATE SET
            last_activity = NOW(),
            last_path = EXCLUDED.last_path,
            user_agent = COALESCE(NULLIF(EXCLUDED.user_agent, ''), public.public_sessions.user_agent),
            ip_address = EXCLUDED.ip_address,
            first_seen_at = COALESCE(public.public_sessions.first_seen_at, EXCLUDED.first_seen_at, NOW()),
            created_at = CASE
                WHEN public.public_sessions.last_activity < NOW() - INTERVAL '30 minutes'
                THEN NOW()
                ELSE public.public_sessions.created_at
            END
        """,
        (visitor_id, p, ua, ip),
    )
    try:
        cur.execute(
            """
            UPDATE public.public_sessions
            SET device_type = COALESCE(%s, device_type),
                browser = COALESCE(%s, browser)
            WHERE visitor_id = %s
            """,
            (device_type, browser, visitor_id),
        )
    except Exception:
        pass
    try:
        cur.execute(
            "DELETE FROM public.public_sessions WHERE ip_address = %s AND visitor_id <> %s",
            (ip, visitor_id),
        )
    except Exception:
        pass

    # Visit sessions: new on idle Return; else touch open
    try:
        if idle_new_session:
            try:
                _close_open_public_page_hit(cur, ip, prev_last_activity)
            except Exception:
                pass
            if prev_last_activity is not None:
                cur.execute(
                    """
                    UPDATE public.public_visit_sessions
                    SET ended_at = COALESCE(ended_at, %s), last_path = COALESCE(last_path, %s)
                    WHERE ip_address = %s AND ended_at IS NULL
                    """,
                    (prev_last_activity, prev_path, ip),
                )
            else:
                cur.execute(
                    """
                    UPDATE public.public_visit_sessions
                    SET ended_at = COALESCE(ended_at, NOW())
                    WHERE ip_address = %s AND ended_at IS NULL
                    """,
                    (ip,),
                )
            try:
                cur.execute(
                    """
                    INSERT INTO public.public_visit_sessions
                        (visitor_id, ip_address, started_at, ended_at, last_path, user_agent,
                         device_type, browser, start_path)
                    VALUES (%s, %s, NOW(), NULL, %s, %s, %s, %s, %s)
                    """,
                    (visitor_id, ip, p, ua, device_type, browser, p),
                )
            except Exception:
                cur.execute(
                    """
                    INSERT INTO public.public_visit_sessions
                        (visitor_id, ip_address, started_at, ended_at, last_path, user_agent)
                    VALUES (%s, %s, NOW(), NULL, %s, %s)
                    """,
                    (visitor_id, ip, p, ua),
                )
        else:
            cur.execute(
                """
                UPDATE public.public_visit_sessions
                SET last_path = %s, user_agent = COALESCE(NULLIF(%s, ''), user_agent)
                WHERE ip_address = %s AND ended_at IS NULL
                """,
                (p, ua, ip),
            )
            cur.execute(
                "SELECT 1 FROM public.public_visit_sessions WHERE ip_address = %s AND ended_at IS NULL LIMIT 1",
                (ip,),
            )
            if cur.fetchone() is None:
                try:
                    cur.execute(
                        """
                        INSERT INTO public.public_visit_sessions
                            (visitor_id, ip_address, started_at, ended_at, last_path, user_agent,
                             device_type, browser, start_path)
                        VALUES (%s, %s, NOW(), NULL, %s, %s, %s, %s, %s)
                        """,
                        (visitor_id, ip, p, ua, device_type, browser, p),
                    )
                except Exception:
                    cur.execute(
                        """
                        INSERT INTO public.public_visit_sessions
                            (visitor_id, ip_address, started_at, ended_at, last_path, user_agent)
                        VALUES (%s, %s, NOW(), NULL, %s, %s)
                        """,
                        (visitor_id, ip, p, ua),
                    )
    except Exception:
        pass

    # One trail row when URL actually changes (or first page of session)
    try:
        _record_url_stay_hit(cur, visitor_id=visitor_id, ip_address=ip, path=p)
    except Exception:
        pass


'''
text = text[:u0] + NEW_UPSERT + text[u1:]

# --- _touch_public_presence: allow landing ---
text = text.replace(
    """    p = path if path is not None else _client_path_for_session_touch(request)
    if not _is_trackable_page_path(p):
        return None""",
    """    p = path if path is not None else _client_path_for_session_touch(request)
    if not _is_document_page_path_for_hit(p):
        return None""",
    1,
)

# --- public presence middleware: allow landing ---
text = text.replace(
    """            path = _client_path_for_session_touch(request)
            if _is_trackable_page_path(path):
                visitor_id = _touch_public_presence(request, path)""",
    """            path = _client_path_for_session_touch(request)
            if _is_document_page_path_for_hit(path):
                visitor_id = _touch_public_presence(request, path)""",
    1,
)

# --- signed-in middleware: never force_hit (no refresh spam) ---
old_force = """            _session_touch_user_activity(
                cur,
                session_token,
                touch_path,
                ip_address=ip,
                user_agent=ua,
                force_hit=bool(is_document_get),
            )"""
new_force = """            _session_touch_user_activity(
                cur,
                session_token,
                touch_path,
                ip_address=ip,
                user_agent=ua,
                force_hit=False,
            )"""
if old_force not in text:
    raise SystemExit("force_hit middleware block missing")
text = text.replace(old_force, new_force, 1)

if text == orig:
    raise SystemExit("no changes applied")

API.write_text(text, encoding="utf-8")
print(f"OK patched {API} (+{len(text) - len(orig)} bytes)")
