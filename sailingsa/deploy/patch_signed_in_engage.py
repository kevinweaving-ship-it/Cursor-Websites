#!/usr/bin/env python3
"""Signed-in engage was dropped: session cookie path never merged engage=.

Also harden client: any click/scroll, SPA flush+reset, faster heartbeat.
"""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SESSION_JS = Path("/var/www/sailingsa/js/session.js")

NEW_LITE = r"""/* LITE_PAGE_ENGAGE — scroll / search / click (+ nav flush; bot vs real) */
(function () {
  try {
    window.__ssaEngageTokens = window.__ssaEngageTokens || [];
    function curPath() {
      return String(window.location.pathname || '/') + String(window.location.search || '');
    }
    function flushEngage(sync, pathOverride) {
      try {
        if (!window.__ssaEngageTokens.length) return;
        var path = pathOverride || curPath();
        var url = '/auth/session?path=' + encodeURIComponent(path) + '&engage=' + encodeURIComponent(window.__ssaEngageTokens.join(','));
        if (typeof fetch === 'function') {
          fetch(url, { method: 'GET', credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
        }
        if (sync) {
          try {
            var img = new Image();
            img.src = url + '&_=' + Date.now();
          } catch (eImg) {}
        }
      } catch (eF) {}
    }
    function addTok(t, sync) {
      try {
        if (!t) return;
        if (window.__ssaEngageTokens.indexOf(t) >= 0) {
          if (sync) flushEngage(true);
          return;
        }
        window.__ssaEngageTokens.push(t);
        flushEngage(!!sync);
      } catch (e) {}
    }
    function resetEngageForNewPage() {
      try {
        var prev = curPath();
        if (window.__ssaEngageTokens && window.__ssaEngageTokens.length) {
          flushEngage(true, prev);
        }
        window.__ssaEngageTokens = [];
        scrolled = false;
        try { window.addEventListener('scroll', onScroll, { passive: true }); } catch (eA) {}
      } catch (eR) {}
    }
    function isSearchEl(el) {
      if (!el || !el.tagName) return false;
      var tag = String(el.tagName).toLowerCase();
      if (tag === 'input' || tag === 'textarea') {
        var ty = String(el.type || '').toLowerCase();
        var nm = String(el.name || el.id || '').toLowerCase();
        var ph = String(el.placeholder || '').toLowerCase();
        var role = String(el.getAttribute && el.getAttribute('role') || '').toLowerCase();
        if (ty === 'search') return true;
        if (role === 'searchbox') return true;
        if (nm.indexOf('search') >= 0 || nm === 'q' || nm.indexOf('query') >= 0) return true;
        if (ph.indexOf('search') >= 0) return true;
      }
      return false;
    }
    function isNavLink(el) {
      if (!el || !el.tagName) return false;
      var a = el.closest ? el.closest('a[href]') : null;
      if (!a) return false;
      var href = String(a.getAttribute('href') || '').trim();
      if (!href || href.charAt(0) === '#' || href.indexOf('javascript:') === 0) return false;
      try {
        if (a.target && String(a.target).toLowerCase() === '_blank') return false;
      } catch (eT) {}
      return true;
    }
    var scrolled = false;
    function onScroll() {
      if (scrolled) return;
      try {
        var doc = document.documentElement || document.body;
        var max = Math.max(1, (doc.scrollHeight || 0) - (window.innerHeight || 0));
        var y = window.pageYOffset || doc.scrollTop || 0;
        if (y >= 10 || (max > 0 && y / max >= 0.05)) {
          scrolled = true;
          addTok('scrolled', false);
          try { window.removeEventListener('scroll', onScroll, { passive: true }); } catch (eR) {}
        }
      } catch (e) {}
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    try { onScroll(); } catch (e0s) {}
    document.addEventListener('focusin', function (ev) {
      if (isSearchEl(ev.target)) addTok('searched', false);
    }, true);
    document.addEventListener('input', function (ev) {
      if (isSearchEl(ev.target)) addTok('searched', false);
    }, true);
    // Any real pointer/click on the page counts (tabs, cards, rows — not only <a>/<button>)
    function markClick(ev, syncNav) {
      try {
        var t = ev && ev.target;
        if (!t || !t.tagName) return;
        var tag = String(t.tagName).toLowerCase();
        if (tag === 'html' || tag === 'body') return;
        if (isSearchEl(t)) return;
        var el = t.closest ? t.closest('a,button,[role="button"],input[type="submit"],input[type="button"],.tab,[data-action],[onclick]') : null;
        var nav = !!(el && isNavLink(el)) || !!syncNav;
        // Count any click that isn't a pure empty background
        if (!el) {
          // still a human action on content
          addTok('clicked', false);
          return;
        }
        addTok('clicked', !!nav);
      } catch (e) {}
    }
    document.addEventListener('pointerdown', function (ev) { markClick(ev, false); }, true);
    document.addEventListener('click', function (ev) {
      try {
        var t = ev && ev.target;
        var nav = t && t.closest && !!isNavLink(t);
        markClick(ev, nav);
      } catch (e) { markClick(ev, true); }
    }, true);
    // SPA: flush previous page engage before path report
    try {
      var _ps = history.pushState;
      var _rs = history.replaceState;
      if (typeof _ps === 'function') {
        history.pushState = function () {
          try { resetEngageForNewPage(); } catch (e1) {}
          return _ps.apply(this, arguments);
        };
      }
      if (typeof _rs === 'function') {
        history.replaceState = function () {
          try { resetEngageForNewPage(); } catch (e2) {}
          return _rs.apply(this, arguments);
        };
      }
      window.addEventListener('popstate', function () {
        try { resetEngageForNewPage(); } catch (e3) {}
      });
    } catch (eSpa) {}
    window.__ssaFlushEngage = flushEngage;
    window.__ssaAddEngageTok = addTok;
  } catch (e0) {}
})();
"""


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = API.with_suffix(f".py.bak_signed_engage_{ts}")
    shutil.copy2(API, bak)
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # Patch: when session valid, merge engage + handle leave on public_page_hits
    old = '''        if session:
            _session_touch_user_activity(cur, session_token, _client_path_for_session_touch(request))
            conn.commit()
            # Fetch user name information from sas_id_personal or sailing_id
'''
    new = '''        if session:
            _session_touch_user_activity(cur, session_token, _client_path_for_session_touch(request))
            # Signed-in users still send engage=/leave= from session.js — do not drop them.
            try:
                _lean_ensure_page_hit_engagement_column(cur)
                eng = str(request.query_params.get("engage") or "")
                leave = str(request.query_params.get("leave") or "").strip().lower() in ("1", "true", "yes")
                path_q = str(request.query_params.get("path") or "") or _client_path_for_session_touch(request)
                ip_s = _get_client_ip(request)
                vid_s = f"sess:{(session_token or '')[:32]}"
                if eng:
                    _lean_merge_hit_engagement_for_path(
                        cur, ip=ip_s, visitor_id=vid_s, path=path_q, engage_raw=eng
                    )
                if leave:
                    _close_open_public_page_hit(cur, ip_address=ip_s, visitor_id=vid_s)
            except Exception:
                pass
            conn.commit()
            # Fetch user name information from sas_id_personal or sailing_id
'''
    if "Signed-in users still send engage=" not in text:
        if old not in text:
            raise SystemExit("session-valid touch block not found")
        text = text.replace(old, new, 1)
        print("OK signed-in engage/leave merge")
    else:
        print("SKIP signed-in engage already present")

    # Also merge engage when same-URL heartbeat on signed-in (_session_touch returns early)
    # Covered by check_session patch above which runs after touch regardless of path change.

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print(f"OK api bak={bak}")
    else:
        print("api unchanged")

    jbak = SESSION_JS.with_suffix(f".js.bak_signed_engage_{ts}")
    shutil.copy2(SESSION_JS, jbak)
    js = SESSION_JS.read_text(encoding="utf-8", errors="replace")
    start = js.find("/* LITE_PAGE_ENGAGE")
    if start < 0:
        raise SystemExit("no LITE_PAGE_ENGAGE")
    end = js.find("\n// Make functions globally available", start)
    if end < 0:
        raise SystemExit("no end marker")
    js2 = js[:start] + NEW_LITE + "\n\n" + js[end:].lstrip("\n")
    # Faster heartbeat for engage (45s → 15s)
    js2 = js2.replace("}, 45000);", "}, 15000);", 1)
    SESSION_JS.write_text(js2, encoding="utf-8")
    print(f"OK session.js bak={jbak}")


if __name__ == "__main__":
    main()
