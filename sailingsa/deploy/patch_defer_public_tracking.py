#!/usr/bin/env python3
"""Restore + defer public presence tracking off the request path (safe insert)."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
BAK = Path("/var/www/sailingsa/api/api.bak-defer-track-20260815_083442")

HELPERS = '''
# Lightweight executor for public presence (never block HTML/API responses)
from concurrent.futures import ThreadPoolExecutor
_LEAN_TRACK_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lean-track")


def _lean_track_public_presence_bg(request_snap: dict) -> None:
    """Presence/hit recording off the event loop."""
    conn = None
    try:
        if request_snap.get("has_session"):
            return
        path = request_snap.get("path") or "/"
        if not _is_document_page_path_for_hit(path):
            return
        ua = request_snap.get("ua") or ""
        if _is_bot_user_agent(ua):
            return
        ip = (request_snap.get("ip") or "").strip()
        if not ip or _is_noise_public_ip(ip):
            return
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SET LOCAL statement_timeout = '800'")
        except Exception:
            pass
        _ensure_public_sessions_table(cur)
        if _ip_has_active_logged_in_session(cur, ip):
            vid_cookie = (request_snap.get("visitor_id") or "").strip()
            _purge_public_sessions_known_user(cur, ip_address=ip, visitor_id=vid_cookie or None)
            conn.commit()
            return
        visitor_id = (request_snap.get("visitor_id") or "").strip() or None
        if not visitor_id:
            try:
                cur.execute(
                    """
                    SELECT visitor_id FROM public.public_sessions
                    WHERE ip_address = %s
                    ORDER BY last_activity DESC NULLS LAST
                    LIMIT 1
                    """,
                    (ip[:80],),
                )
                row = cur.fetchone()
                if row:
                    visitor_id = row[0] if not isinstance(row, dict) else row.get("visitor_id")
            except Exception:
                visitor_id = None
            if not visitor_id:
                import uuid as _uuid
                visitor_id = _uuid.uuid4().hex
        _upsert_public_session(cur, visitor_id, path, ua, ip)
        try:
            _lean_ensure_page_hit_engagement_column(cur)
        except Exception:
            pass
        try:
            _record_url_stay_hit(cur, visitor_id=str(visitor_id), ip_address=ip, path=path)
        except Exception:
            pass
        conn.commit()
    except Exception:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
    finally:
        if conn is not None:
            try:
                return_db_connection(conn)
            except Exception:
                pass


def _lean_schedule_public_presence(request_snap: dict) -> None:
    try:
        _LEAN_TRACK_EXECUTOR.submit(_lean_track_public_presence_bg, request_snap)
    except Exception:
        pass


'''

NEW_MW = '''async def _public_presence_middleware(request: Request, call_next):
    """Track anonymous live page views AFTER the response — never block public HTML."""
    req_path = ""
    try:
        req_path = request.url.path or ""
        if _is_probe_blocked_path(req_path):
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
    except Exception:
        pass
    response = await call_next(request)
    try:
        if not _public_tracking_allowed():
            return response
        if request.method not in ("GET", "HEAD"):
            return response
        if request.cookies.get("session"):
            return response
        if (
            req_path.startswith("/admin")
            or req_path.startswith("/api")
            or req_path.startswith("/auth")
            or req_path.startswith("/traffic")
        ):
            return response
        path = _client_path_for_session_touch(request)
        if not _is_document_page_path_for_hit(path):
            return response
        import uuid as _uuid
        visitor_id = (request.cookies.get(PUBLIC_VISITOR_COOKIE) or "").strip() or _uuid.uuid4().hex
        try:
            _set_public_visitor_cookie(response, visitor_id, request)
        except Exception:
            pass
        snap = {
            "has_session": False,
            "path": path,
            "ua": (request.headers.get("user-agent") or ""),
            "ip": _get_client_ip(request),
            "visitor_id": visitor_id,
        }
        _lean_schedule_public_presence(snap)
    except Exception:
        pass
    return response
'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Restore known-good pre-broken file (still has traffic bg)
    if not BAK.exists():
        raise SystemExit(f"missing bak {BAK}")
    shutil.copy2(API, API.with_name(f"api.bak-broken-defer-{stamp}"))
    shutil.copy2(BAK, API)
    text = API.read_text(encoding="utf-8")

    # Slow down bg loop if present
    text = text.replace(
        '''def _lean_traffic_background_loop() -> None:
    import time as _time
    # Stagger start so boot stays responsive
    _time.sleep(8)
    while True:
        try:
            _lean_traffic_background_tick()
        except Exception:
            pass
        _time.sleep(45)
''',
        '''def _lean_traffic_background_loop() -> None:
    import time as _time
    # Stagger start so boot + public pages stay responsive
    _time.sleep(60)
    while True:
        try:
            _lean_traffic_background_tick()
        except Exception:
            pass
        _time.sleep(90)
''',
        1,
    )
    text = text.replace("SET LOCAL statement_timeout = '4000'", "SET LOCAL statement_timeout = '2000'", 1)
    text = text.replace("LIMIT 40\n            \"\"\",\n            (hours,),\n        )\n        ips = []", "LIMIT 20\n            \"\"\",\n            (hours,),\n        )\n        ips = []", 1)

    marker = '@app.middleware("http")\nasync def _public_presence_middleware(request: Request, call_next):'
    if marker not in text:
        raise SystemExit("presence middleware marker missing after restore")

    # Extract old middleware body until next @app.middleware or def at same level
    start = text.find(marker)
    # find end: next \n@app.middleware or \n@app. after this mw
    rest = text[start + len(marker) :]
    # old function starts with docstring
    # find next decorator at column 0
    import re
    m = re.search(r'\n@app\.(middleware|get|post|put|delete|patch)', rest)
    if not m:
        raise SystemExit("could not find end of presence middleware")
    old_full = text[start : start + len(marker) + m.start()]
    # old_full includes from decorator through end of function before next @app

    new_full = HELPERS + '@app.middleware("http")\n' + NEW_MW + "\n\n"
    text = text.replace(old_full, new_full, 1)

    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK restored+deferred (+{len(text) - len(BAK.read_text())} vs bak)")


if __name__ == "__main__":
    main()
