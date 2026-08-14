#!/usr/bin/env python3
"""Lite on-page engagement: scroll / search / click → Live trail summary under URL."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SESSION_JS = Path("/var/www/sailingsa/js/session.js")

ENGAGE_HELPER = '''def _lean_parse_engage_tokens(raw: Optional[str]) -> list:
    """Lite engagement tokens from client: scrolled, searched, clicked."""
    out = []
    for part in str(raw or "").replace(";", ",").split(","):
        t = part.strip().lower()
        if t in ("scrolled", "scroll", "scroll50", "scroll_half"):
            t = "scrolled"
        elif t in ("searched", "search", "search_focus", "search_submit"):
            t = "searched"
        elif t in ("clicked", "click", "tap"):
            t = "clicked"
        else:
            continue
        if t not in out:
            out.append(t)
    return out


def _lean_engage_summary_label(tokens) -> str:
    order = ("scrolled", "searched", "clicked")
    labels = {"scrolled": "scrolled", "searched": "used search", "clicked": "clicked"}
    have = set(tokens or [])
    bits = [labels[k] for k in order if k in have]
    return " · ".join(bits)


def _lean_merge_open_hit_engagement(cur, *, ip: str = "", visitor_id: str = "", engage_raw: str = "") -> None:
    """Merge lite engagement tokens onto the visitor's current open page hit."""
    toks = _lean_parse_engage_tokens(engage_raw)
    if not toks:
        return
    ip_s = (ip or "").strip()
    vid = (visitor_id or "").strip()
    if not ip_s and not vid:
        return
    try:
        cur.execute(
            """
            SELECT hit_id, COALESCE(engagement, '') AS engagement
            FROM public.public_page_hits
            WHERE left_at IS NULL
              AND (
                    (%s <> '' AND ip_address = %s)
                 OR (%s <> '' AND visitor_id = %s)
              )
            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
            LIMIT 1
            """,
            (ip_s, ip_s, vid, vid),
        )
        row = cur.fetchone()
        if not row:
            return
        if isinstance(row, dict):
            hit_id = row.get("hit_id")
            prev = row.get("engagement") or ""
        else:
            hit_id, prev = row[0], row[1]
        merged = _lean_parse_engage_tokens(prev) + [t for t in toks if t not in _lean_parse_engage_tokens(prev)]
        # unique preserve order
        seen = set()
        uniq = []
        for t in merged:
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(uniq), hit_id),
        )
    except Exception:
        pass


def _lean_ensure_page_hit_engagement_column(cur) -> None:
    try:
        cur.execute(
            """
            ALTER TABLE public.public_page_hits
            ADD COLUMN IF NOT EXISTS engagement text
            """
        )
    except Exception:
        pass


'''


def patch_api() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-engage-lite-{stamp}"))
    text = API.read_text(encoding="utf-8")

    if "def _lean_merge_open_hit_engagement" not in text:
        anchor = text.find("def _close_open_public_page_hit")
        if anchor < 0:
            anchor = text.find("def _finalize_idle_open_page_hits")
        if anchor < 0:
            raise SystemExit("anchor missing")
        text = text[:anchor] + ENGAGE_HELPER + text[anchor:]

    # Ensure column on touch / live
    if "_lean_ensure_page_hit_engagement_column(cur)" not in text:
        # call from lean live finalize area
        needle = "_finalize_idle_open_page_hits(cur, idle_seconds=120)"
        if needle not in text:
            raise SystemExit("finalize call missing")
        text = text.replace(
            needle,
            "_lean_ensure_page_hit_engagement_column(cur)\n"
            "            _finalize_idle_open_page_hits(cur, idle_seconds=120)",
            1,
        )

    # In leave / touch presence: read engage query and merge
    old_leave = '''            vid_leave = _public_visitor_id_from_request(request) or ""
            _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid_leave)
            conn.commit()
            return vid_leave or None'''
    new_leave = '''            vid_leave = _public_visitor_id_from_request(request) or ""
            try:
                _lean_ensure_page_hit_engagement_column(cur)
                eng = str(request.query_params.get("engage") or "")
                if eng:
                    _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=vid_leave, engage_raw=eng)
            except Exception:
                pass
            _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid_leave)
            conn.commit()
            return vid_leave or None'''
    if old_leave not in text:
        raise SystemExit("leave block not found")
    text = text.replace(old_leave, new_leave, 1)

    # After normal presence touch (non-leave), merge engage on heartbeat
    # Find end of successful touch commit near _touch_public_presence return visitor_id
    marker = "return visitor_id\n    except Exception:\n        try:\n            if conn:\n                conn.rollback()"
    # too fragile — instead patch check_session anonymous branch
    old_sess = '''                leave = str(request.query_params.get("leave") or "").strip().lower() in ("1", "true", "yes")
                if leave or _public_tracking_allowed():
                    visitor_id = _touch_public_presence(request, leave=leave)'''
    # Better: inside _touch_public_presence after recording, before return — search for path recording return

    # Patch _touch_public_presence non-leave path: after upsert, merge engage
    touch_anchor = text.find("def _touch_public_presence")
    # find first "conn.commit()" after leave block ends inside this function that's for normal path
    # Simpler approach: wrap _touch_public_presence call sites to pass engage via request (already on request)

    # Inject near end of non-leave branch before commit — look for unique string in touch function
    uniq = "Presence/duration must come from real path changes only."
    # that's in JS

    inject_after = "_record_url_stay_hit(cur, visitor_id=visitor_id, ip_address=ip, path=p)"
    # there may be multiple — only in _upsert or touch
    count = text.count(inject_after)
    if count < 1:
        # alternate
        inject_after = "_record_url_stay_hit(cur, visitor_id=visitor_id, ip_address=ip, path="
    # Add merge right after _ensure in upsert? Cleaner: at start of _touch_public_presence after leave handling, for normal path after we have vid/ip:

    # Find: in _touch_public_presence after leave block, the line that starts normal path "p ="
    leave_end = text.find("if leave:")
    # after leave block returns, next is normal
    # Search for pattern after leave function section:
    old_norm = '''    p = _normalize_traffic_path(path) if path is not None else _normalize_traffic_path(_client_path_for_session_touch(request) if False else "")'''
    # read actual file section
    i = text.find("def _touch_public_presence")
    chunk = text[i : i + 4500]
    # print keys for patch targeting
    if "engage" not in chunk or "_lean_merge_open_hit_engagement" not in chunk:
        # insert before final commit of normal touch — find "conn.commit()" inside function after leave
        # Use: after _upsert_public_session call
        if "_upsert_public_session(" not in chunk:
            raise SystemExit("upsert not in touch")
        # replace first upsert follow-up area inside whole text carefully
        old_u = '''        _upsert_public_session(cur, visitor_id, p, ua, ip)
'''
        # may not match exact
        import re
        m = re.search(r"_upsert_public_session\(cur,[^\n]+\)\n", text[i : i + 5000])
        if not m:
            raise SystemExit("upsert call not found in touch")
        abs_start = i + m.start()
        abs_end = i + m.end()
        call = text[abs_start:abs_end]
        addition = (
            call
            + "        try:\n"
            + "            _lean_ensure_page_hit_engagement_column(cur)\n"
            + "            eng = str(request.query_params.get('engage') or '')\n"
            + "            if eng:\n"
            + "                _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=visitor_id, engage_raw=eng)\n"
            + "        except Exception:\n"
            + "            pass\n"
        )
        text = text[:abs_start] + addition + text[abs_end:]

    # Trail SELECT include engagement
    old_sel = "SELECT path, occurred_at, left_at, dwell_seconds\n                    FROM public.public_page_hits"
    if old_sel not in text:
        old_sel = "SELECT path, occurred_at, left_at, dwell_seconds\n                FROM public.public_page_hits"
    # replace all trail selects in _lean_session_page_trail
    text2 = text.replace(
        "SELECT path, occurred_at, left_at, dwell_seconds\n                    FROM public.public_page_hits",
        "SELECT path, occurred_at, left_at, dwell_seconds, COALESCE(engagement, '') AS engagement\n                    FROM public.public_page_hits",
    )
    text2 = text2.replace(
        "SELECT path, occurred_at, left_at, dwell_seconds\n                FROM public.public_page_hits",
        "SELECT path, occurred_at, left_at, dwell_seconds, COALESCE(engagement, '') AS engagement\n                FROM public.public_page_hits",
    )
    text = text2

    # Parse engagement in trail loop — find item = { path...
    old_item = '''            item = {
                "path": path,
                "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                "dwell_seconds": int(dwell) if dwell is not None else None,
                "dwell_label": _lean_fmt_dwell_seconds(dwell) + (" (open)" if open_hit else ""),
                "open": bool(open_hit),
            }'''
    new_item = '''            if isinstance(r, dict):
                eng_raw = r.get("engagement") or ""
            else:
                eng_raw = r[4] if len(r) > 4 else ""
            eng_toks = _lean_parse_engage_tokens(eng_raw)
            eng_label = _lean_engage_summary_label(eng_toks)
            item = {
                "path": path,
                "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                "dwell_seconds": int(dwell) if dwell is not None else None,
                "dwell_label": _lean_fmt_dwell_seconds(dwell) + (" (open)" if open_hit else ""),
                "open": bool(open_hit),
                "engagement": eng_toks,
                "engagement_label": eng_label,
            }'''
    if old_item not in text:
        raise SystemExit("trail item block not found")
    text = text.replace(old_item, new_item, 1)

    # Live UI: under URL show engagement_label
    old_trail_row = '''          var pLab=(p==="/"||p==="/index.html")?"home":p;
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";'''
    new_trail_row = '''          var pLab=(p==="/"||p==="/index.html")?"home":p;
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);
          var eg=(pt.engagement_label||"");
          if(eg) pl+="<div class='trail-engage'>"+esc(eg)+"</div>";
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";'''
    if old_trail_row not in text:
        raise SystemExit("trail row js not found")
    text = text.replace(old_trail_row, new_trail_row, 1)

    # tiny CSS for trail-engage if style block exists in lean page
    if ".trail-engage" not in text:
        css_anchor = ".trail .dwell{color:#64748b;font-variant-numeric:tabular-nums}"
        if css_anchor in text:
            text = text.replace(
                css_anchor,
                css_anchor
                + "\n  .trail-engage{display:block;margin-top:2px;font-size:11px;color:#64748b;font-weight:500}",
                1,
            )

    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK api engagement")


def patch_session_js() -> None:
    js = SESSION_JS.read_text(encoding="utf-8")
    if "LITE_PAGE_ENGAGE" in js:
        print("session.js engage already present")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(SESSION_JS, SESSION_JS.with_suffix(f".bak-engage-{stamp}"))

    # Replace heartbeat + leave to append engage=
    old_leave = """        function sendLeave() {
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
    new_leave = """        function sendLeave() {
            try {
                // MUST be GET — /auth/session leave is GET-only. sendBeacon() POSTs and never closes dwell.
                var path = String(window.location.pathname || '/') + String(window.location.search || '');
                var url = '/auth/session?path=' + encodeURIComponent(path) + '&leave=1';
                try {
                    var eg = (window.__ssaEngageTokens || []);
                    if (eg && eg.length) url += '&engage=' + encodeURIComponent(eg.join(','));
                } catch (eE) {}
                if (typeof fetch === 'function') {
                    fetch(url, { method: 'GET', credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
                }
                try {
                    var img = new Image();
                    img.src = url + '&_=' + Date.now();
                } catch (eImg) {}
            } catch (eL) {}
        }"""
    if old_leave not in js:
        raise SystemExit("sendLeave block not found for engage patch")
    js = js.replace(old_leave, new_leave, 1)

    old_hb = """                    fetch('/auth/session?path=' + encodeURIComponent(path), {
                        method: 'GET',
                        credentials: 'include',
                        cache: 'no-store',
                        keepalive: true
                    }).catch(function () {});"""
    new_hb = """                    var hb = '/auth/session?path=' + encodeURIComponent(path);
                    try {
                        var eg2 = (window.__ssaEngageTokens || []);
                        if (eg2 && eg2.length) hb += '&engage=' + encodeURIComponent(eg2.join(','));
                    } catch (eE2) {}
                    fetch(hb, {
                        method: 'GET',
                        credentials: 'include',
                        cache: 'no-store',
                        keepalive: true
                    }).catch(function () {});"""
    if old_hb not in js:
        raise SystemExit("heartbeat fetch not found")
    js = js.replace(old_hb, new_hb, 1)

    engage_block = """
/* LITE_PAGE_ENGAGE — scroll / search / first click (bot vs real on long home dwell) */
(function () {
  try {
    window.__ssaEngageTokens = window.__ssaEngageTokens || [];
    function addTok(t) {
      try {
        if (!t) return;
        if (window.__ssaEngageTokens.indexOf(t) >= 0) return;
        window.__ssaEngageTokens.push(t);
        // push soon so Live can see it without waiting for leave
        var path = String(window.location.pathname || '/') + String(window.location.search || '');
        var url = '/auth/session?path=' + encodeURIComponent(path) + '&engage=' + encodeURIComponent(window.__ssaEngageTokens.join(','));
        if (typeof fetch === 'function') {
          fetch(url, { method: 'GET', credentials: 'include', cache: 'no-store', keepalive: true }).catch(function () {});
        }
      } catch (e) {}
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
    // scroll ~halfway
    var scrolled = false;
    function onScroll() {
      if (scrolled) return;
      try {
        var doc = document.documentElement || document.body;
        var max = Math.max(1, (doc.scrollHeight || 0) - (window.innerHeight || 0));
        var y = window.pageYOffset || doc.scrollTop || 0;
        if (y / max >= 0.35) {
          scrolled = true;
          addTok('scrolled');
          window.removeEventListener('scroll', onScroll, { passive: true });
        }
      } catch (e) {}
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    // search focus / type
    document.addEventListener('focusin', function (ev) {
      if (isSearchEl(ev.target)) addTok('searched');
    }, true);
    document.addEventListener('input', function (ev) {
      if (isSearchEl(ev.target)) addTok('searched');
    }, true);
    // first meaningful click/tap
    var clicked = false;
    document.addEventListener('click', function (ev) {
      if (clicked) return;
      try {
        var t = ev.target;
        if (!t) return;
        var el = t.closest ? t.closest('a,button,[role="button"],input[type="submit"]') : null;
        if (!el) return;
        clicked = true;
        addTok('clicked');
      } catch (e) {}
    }, true);
  } catch (e0) {}
})();
"""
    # append before final export or at end of leave IIFE file section — after LANDING heartbeat IIFE
    marker = "/* LANDING_DWELL_HEARTBEAT */"
    if marker not in js:
        js = js + "\n" + engage_block
    else:
        # insert after the heartbeat IIFE closing
        idx = js.find(marker)
        end = js.find("})();", idx)
        if end < 0:
            js = js + "\n" + engage_block
        else:
            end = end + len("})();")
            js = js[:end] + "\n" + engage_block + js[end:]

    SESSION_JS.write_text(js, encoding="utf-8")
    print("OK session.js lite engage")


def ensure_column() -> None:
    import psycopg2

    conn = psycopg2.connect("postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master")
    cur = conn.cursor()
    cur.execute("ALTER TABLE public.public_page_hits ADD COLUMN IF NOT EXISTS engagement text")
    conn.commit()
    cur.close()
    conn.close()
    print("OK column engagement")


def main() -> None:
    ensure_column()
    patch_api()
    patch_session_js()


if __name__ == "__main__":
    main()
