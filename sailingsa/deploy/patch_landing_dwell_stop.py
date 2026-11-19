#!/usr/bin/env python3
"""Fix landing dwell stop: GET leave beacon + idle finalize open hits."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SESSION_JS = Path("/var/www/sailingsa/js/session.js")


def patch_session_js() -> None:
    text = SESSION_JS.read_text(encoding="utf-8")
    old = """        function sendLeave() {
            try {
                var path = String(window.location.pathname || '/') + String(window.location.search || '');
                var url = '/auth/session?path=' + encodeURIComponent(path) + '&leave=1';
                if (navigator.sendBeacon) {
                    navigator.sendBeacon(url);
                } else {
                    fetch(url, { credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
                }
            } catch (eL) {}
        }"""
    new = """        function sendLeave() {
            try {
                // MUST be GET — /auth/session leave is GET-only. sendBeacon() POSTs and never closes dwell.
                var path = String(window.location.pathname || '/') + String(window.location.search || '');
                var url = '/auth/session?path=' + encodeURIComponent(path) + '&leave=1';
                if (typeof fetch === 'function') {
                    fetch(url, { method: 'GET', credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
                }
                try {
                    var img = new Image();
                    img.src = url + '&_=' + Date.now();
                } catch (eImg) {}
            } catch (eL) {}
        }"""
    if "MUST be GET" in text:
        print("session.js leave already GET")
        return
    if old not in text:
        raise SystemExit("session.js sendLeave block not found")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(SESSION_JS, SESSION_JS.with_suffix(f".bak-leave-get-{stamp}"))
    SESSION_JS.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("OK session.js leave uses GET keepalive + Image ping")


def patch_api() -> None:
    text = API.read_text(encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-idle-dwell-{stamp}"))

    if "def _finalize_idle_open_page_hits" not in text:
        anchor = text.find("def _close_open_public_page_hit")
        if anchor < 0:
            raise SystemExit("close helper missing")
        helper = '''def _finalize_idle_open_page_hits(cur, *, idle_seconds: int = 120) -> int:
    """Stop open dwell when the visitor left without a beacon (common on landing-only).

    If public_sessions.last_activity for that IP is older than idle_seconds, close any
    open public_page_hits at last_activity so dwell stops growing as "(open)".
    """
    try:
        idle = max(30, int(idle_seconds or 120))
    except Exception:
        idle = 120
    try:
        cur.execute(
            """
            UPDATE public.public_page_hits h
            SET left_at = s.last_activity,
                dwell_seconds = GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (s.last_activity - h.occurred_at))::int
                )
            FROM public.public_sessions s
            WHERE h.left_at IS NULL
              AND h.ip_address IS NOT NULL
              AND TRIM(h.ip_address) <> ''
              AND s.ip_address = h.ip_address
              AND s.last_activity IS NOT NULL
              AND s.last_activity < NOW() - make_interval(secs => %s)
              AND h.occurred_at <= s.last_activity
            """,
            (idle,),
        )
        return int(cur.rowcount or 0)
    except Exception:
        return 0


'''
        text = text[:anchor] + helper + text[anchor:]

    # Call from lean live API near start (after cursor)
    live = text.find("def lean_traffic_api_live")
    if live < 0:
        raise SystemExit("live api missing")
    marker = "cur = conn.cursor()"
    # find first cursor in live fn
    sub = text[live : live + 2500]
    if "_finalize_idle_open_page_hits" not in sub:
        if marker not in sub:
            raise SystemExit("live cursor marker missing")
        insert = (
            "cur = conn.cursor()\n"
            "        try:\n"
            "            _finalize_idle_open_page_hits(cur, idle_seconds=120)\n"
            "            conn.commit()\n"
            "        except Exception:\n"
            "            try:\n"
            "                conn.rollback()\n"
            "            except Exception:\n"
            "                pass\n"
            "        # refresh cursor after possible rollback\n"
            "        try:\n"
            "            cur = conn.cursor()\n"
            "        except Exception:\n"
            "            pass"
        )
        # only replace first occurrence inside live function region carefully
        idx = text.find(marker, live)
        # ensure we don't hit a later function - live end
        end = text.find("\ndef lean_traffic_api_top", live)
        if idx < 0 or idx > end:
            raise SystemExit("cursor not in live fn")
        text = text[:idx] + insert + text[idx + len(marker) :]

    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK api idle finalize + live call")


def main() -> None:
    patch_session_js()
    patch_api()


if __name__ == "__main__":
    main()
