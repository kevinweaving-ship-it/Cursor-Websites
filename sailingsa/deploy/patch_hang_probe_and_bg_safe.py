#!/usr/bin/env python3
"""Stop public hangs: fast-reject probes; safe BG DB commits; pause heavy scans under load."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.bak-hang-fix-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # 1) Fast probe reject — any .php / wp- / weird scanners before other work
    old_probe = '''async def _block_probe_paths_middleware(request: Request, call_next):
    """Auto-block WordPress/CMS scanner probes (wp-login.php, .env, etc.)."""
    try:
        ip = _get_client_ip(request)
        if _ip_is_probe_banned(ip):
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
        req_path = request.url.path or ""
        if _is_probe_blocked_path(req_path):
            _ban_probe_ip(ip)
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
        qpath = (request.query_params.get("path") or "").strip()
        if _ip_in_known_scanner_net(ip) and (
            _is_junk_crawler_path(req_path) or _is_junk_crawler_path(qpath)
        ):
            _ban_probe_ip(ip)
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
'''
    new_probe = '''async def _block_probe_paths_middleware(request: Request, call_next):
    """Auto-block WordPress/CMS scanner probes (wp-login.php, .env, etc.)."""
    try:
        req_path = request.url.path or ""
        low = req_path.lower()
        # Ultra-cheap reject: never let PHP / wp probes occupy the single API worker
        if (
            low.endswith(".php")
            or low.endswith(".aspx")
            or low.endswith(".asp")
            or low.endswith(".jsp")
            or "/wp-" in low
            or low.startswith("/wordpress")
            or low.startswith("/phpmyadmin")
            or low.startswith("/.env")
            or low.startswith("/.git")
        ):
            try:
                _ban_probe_ip(_get_client_ip(request))
            except Exception:
                pass
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
        ip = _get_client_ip(request)
        if _ip_is_probe_banned(ip):
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
        if _is_probe_blocked_path(req_path):
            _ban_probe_ip(ip)
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
        qpath = (request.query_params.get("path") or "").strip()
        if _ip_in_known_scanner_net(ip) and (
            _is_junk_crawler_path(req_path) or _is_junk_crawler_path(qpath)
        ):
            _ban_probe_ip(ip)
            return PlainTextResponse("Forbidden", status_code=403, headers={"Cache-Control": "no-store"})
'''
    if old_probe not in text:
        raise SystemExit("probe middleware block not found")
    text = text.replace(old_probe, new_probe, 1)
    print("fast php/wp probe reject")

    # 2) Rewrite background tick to commit/rollback per step (never leave idle-in-transaction)
    old_tick = '''def _lean_traffic_background_tick() -> None:
    """Idle-finalize + bot-shape quarantine off the request path."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            try:
                cur.execute("SET LOCAL statement_timeout = '2000'")
            except Exception:
                pass
            try:
                _finalize_idle_open_page_hits(cur, idle_seconds=120)
            except Exception:
                pass
            try:
                global _LEAN_BOT_SHAPE_SCAN_TS
                _LEAN_BOT_SHAPE_SCAN_TS = 0.0
                _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
            except Exception:
                pass
            try:
                _lean_bg_quarantine_swarms(cur, window_minutes=30)
            except Exception:
                pass
            try:
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
    except Exception:
        pass
    finally:
        if conn is not None:
            try:
                return_db_connection(conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
'''
    new_tick = '''def _lean_traffic_background_tick() -> None:
    """Idle-finalize + light bot quarantine off the request path.

    Each step commits or rolls back so we never leave idle-in-transaction
    connections that starve the single API worker.
    """
    # Shed under load — public pages win
    try:
        if _server_load_1m() >= 2.5:
            return
    except Exception:
        pass
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        def _step(fn):
            try:
                try:
                    cur.execute("SET LOCAL statement_timeout = '1200'")
                except Exception:
                    pass
                fn()
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        _step(lambda: _finalize_idle_open_page_hits(cur, idle_seconds=120))
        # Skip heavy shaped/swarm scans when busy; light finalize only is enough
        try:
            if _server_load_1m() < 1.8:
                def _shaped():
                    global _LEAN_BOT_SHAPE_SCAN_TS
                    _LEAN_BOT_SHAPE_SCAN_TS = 0.0
                    _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
                _step(_shaped)
                _step(lambda: _lean_bg_quarantine_swarms(cur, window_minutes=30))
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.close()
        except Exception:
            pass
    except Exception:
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
    finally:
        if conn is not None:
            try:
                return_db_connection(conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
'''
    if old_tick not in text:
        raise SystemExit("bg tick not found")
    text = text.replace(old_tick, new_tick, 1)
    print("safe bg tick")

    # 3) Presence bg: always rollback on error (already does) + skip under load
    old_track = '''def _lean_track_public_presence_bg(request_snap: dict) -> None:
    """Presence/hit recording off the event loop."""
    conn = None
    try:
        if request_snap.get("has_session"):
            return
'''
    new_track = '''def _lean_track_public_presence_bg(request_snap: dict) -> None:
    """Presence/hit recording off the event loop."""
    conn = None
    try:
        try:
            if _server_load_1m() >= 3.0:
                return
        except Exception:
            pass
        if request_snap.get("has_session"):
            return
'''
    if old_track in text:
        text = text.replace(old_track, new_track, 1)
        print("track sheds under load")
    else:
        print("WARN track fn")

    # 4) Slow bg interval further
    text = text.replace(
        '''    _time.sleep(60)
    while True:
        try:
            _lean_traffic_background_tick()
        except Exception:
            pass
        _time.sleep(90)
''',
        '''    _time.sleep(120)
    while True:
        try:
            _lean_traffic_background_tick()
        except Exception:
            pass
        _time.sleep(180)
''',
        1,
    )

    # 5) Canonical middleware: also skip obvious static probes early if not already
    # Ensure getconn wait doesn't hang forever — check pool getconn timeout if any

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK hang fix (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
