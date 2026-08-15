#!/usr/bin/env python3
"""Fix idle finalize to NOW(); add landing visibility heartbeat."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SESSION_JS = Path("/var/www/sailingsa/js/session.js")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # --- API: finalize at NOW when idle ---
    text = API.read_text(encoding="utf-8")
    old = '''            UPDATE public.public_page_hits h
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
'''
    new = '''            UPDATE public.public_page_hits h
            SET left_at = NOW(),
                dwell_seconds = GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (NOW() - h.occurred_at))::int
                )
            FROM public.public_sessions s
            WHERE h.left_at IS NULL
              AND h.ip_address IS NOT NULL
              AND TRIM(h.ip_address) <> ''
              AND s.ip_address = h.ip_address
              AND s.last_activity IS NOT NULL
              AND s.last_activity < NOW() - make_interval(secs => %s)
              AND h.occurred_at <= s.last_activity
'''
    if "SET left_at = NOW()," in text[text.find("def _finalize_idle_open_page_hits") : text.find("def _finalize_idle_open_page_hits") + 1200]:
        print("api finalize already NOW()")
    elif old not in text:
        raise SystemExit("finalize SQL not found")
    else:
        shutil.copy2(API, API.with_suffix(f".bak-idle-now-{stamp}"))
        text = text.replace(old, new, 1)
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK finalize closes at NOW() (dwell until idle detected)")

    # --- session.js: visibility heartbeat every 45s ---
    js = SESSION_JS.read_text(encoding="utf-8")
    if "LANDING_DWELL_HEARTBEAT" in js:
        print("heartbeat already present")
        return
    needle = """        window.addEventListener('pagehide', sendLeave);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'hidden') sendLeave();
        });
    } catch (e6) {}
})();"""
    insert = """        window.addEventListener('pagehide', sendLeave);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'hidden') sendLeave();
        });
        // While tab visible: soft heartbeat so landing-only dwell can stop at real leave
        // (same-URL touch bumps last_activity; does not add trail rows).
        try {
            /* LANDING_DWELL_HEARTBEAT */
            setInterval(function () {
                try {
                    if (document.visibilityState !== 'visible') return;
                    var path = String(window.location.pathname || '/') + String(window.location.search || '');
                    fetch('/auth/session?path=' + encodeURIComponent(path), {
                        method: 'GET',
                        credentials: 'include',
                        cache: 'no-store',
                        keepalive: true
                    }).catch(function () {});
                } catch (eH) {}
            }, 45000);
        } catch (eH2) {}
    } catch (e6) {}
})();"""
    if needle not in js:
        raise SystemExit("session.js leave listeners block not found")
    shutil.copy2(SESSION_JS, SESSION_JS.with_suffix(f".bak-heartbeat-{stamp}"))
    SESSION_JS.write_text(js.replace(needle, insert, 1), encoding="utf-8")
    print("OK session.js 45s visibility heartbeat")


if __name__ == "__main__":
    main()
