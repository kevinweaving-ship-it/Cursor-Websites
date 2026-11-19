#!/usr/bin/env python3
"""Nav → clicked (server) + tougher client scroll/click flush.

Impossible to move URL A→B without a click; leave/engage often loses the race.
Stamp clicked on the previous hit when a new path opens for the same IP/visitor.
Client: lower scroll threshold, pointerdown on links, sync Image beacon.
"""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SESSION_JS = Path("/var/www/sailingsa/js/session.js")

STAMP_HELPER = '''
def _lean_stamp_nav_click_on_prev_hit(
    cur, *, ip: str = "", visitor_id: str = "", new_path: str = ""
) -> None:
    """When visitor opens a new URL, previous page must have been clicked to leave.

    Client leave/engage often loses the race on full navigation; this is the
    reliable server-side signal. Also stamps scrolled if they stayed ≥3s
    (short pages may not hit client scroll %).
    """
    ip_s = (ip or "").strip()
    vid = (visitor_id or "").strip()
    new_p = _normalize_traffic_path(new_path)
    if not new_p or (not ip_s and not vid):
        return
    try:
        _lean_ensure_page_hit_engagement_column(cur)
        if ip_s:
            cur.execute(
                """
                SELECT hit_id, path, COALESCE(engagement, '') AS engagement,
                       occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE ip_address = %s
                ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (ip_s,),
            )
        else:
            cur.execute(
                """
                SELECT hit_id, path, COALESCE(engagement, '') AS engagement,
                       occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (vid,),
            )
        row = cur.fetchone()
        if not row:
            return
        if isinstance(row, dict):
            hit_id = row.get("hit_id")
            prev_path = row.get("path")
            prev_eng = row.get("engagement") or ""
            occurred = row.get("occurred_at")
            dwell = row.get("dwell_seconds")
        else:
            hit_id, prev_path, prev_eng = row[0], row[1], row[2]
            occurred, dwell = row[3], row[5]
        if hit_id is None:
            return
        prev_p = _normalize_traffic_path(str(prev_path or ""))
        if not prev_p or prev_p == new_p:
            return
        toks = _lean_parse_engage_tokens(prev_eng)
        if "clicked" not in toks:
            toks.append("clicked")
        # Likely scrolled if they spent a few seconds on the page
        need_scroll = "scrolled" not in toks
        if need_scroll:
            dwell_s = None
            try:
                if dwell is not None:
                    dwell_s = int(dwell)
                elif occurred is not None:
                    cur.execute(
                        "SELECT GREATEST(0, EXTRACT(EPOCH FROM (NOW() - %s::timestamptz))::int)",
                        (occurred,),
                    )
                    dr = cur.fetchone()
                    if dr:
                        dwell_s = int(dr[0] if not isinstance(dr, dict) else next(iter(dr.values())))
            except Exception:
                dwell_s = None
            if dwell_s is not None and dwell_s >= 3:
                toks.append("scrolled")
        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(toks), hit_id),
        )
    except Exception:
        pass


'''

MERGE_BY_PATH = '''
def _lean_merge_hit_engagement_for_path(
    cur, *, ip: str = "", visitor_id: str = "", path: str = "", engage_raw: str = ""
) -> None:
    """Merge engage onto the hit for this path (open preferred, else most recent).

    Leave beacons often arrive after the next page already opened; merging only
    onto left_at IS NULL would stamp the wrong URL.
    """
    toks = _lean_parse_engage_tokens(engage_raw)
    if not toks:
        return
    ip_s = (ip or "").strip()
    vid = (visitor_id or "").strip()
    p = _normalize_traffic_path(path)
    if not p or (not ip_s and not vid):
        return
    try:
        _lean_ensure_page_hit_engagement_column(cur)
        if ip_s:
            cur.execute(
                """
                SELECT hit_id, COALESCE(engagement, '') AS engagement
                FROM public.public_page_hits
                WHERE ip_address = %s
                  AND path = %s
                ORDER BY (left_at IS NULL) DESC, occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (ip_s, p),
            )
        else:
            cur.execute(
                """
                SELECT hit_id, COALESCE(engagement, '') AS engagement
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND path = %s
                ORDER BY (left_at IS NULL) DESC, occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (vid, p),
            )
        row = cur.fetchone()
        if not row:
            # Fallback: open hit (legacy)
            _lean_merge_open_hit_engagement(
                cur, ip=ip_s, visitor_id=vid, engage_raw=engage_raw
            )
            return
        if isinstance(row, dict):
            hit_id = row.get("hit_id")
            prev = row.get("engagement") or ""
        else:
            hit_id, prev = row[0], row[1]
        merged = _lean_parse_engage_tokens(prev) + [
            t for t in toks if t not in _lean_parse_engage_tokens(prev)
        ]
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


'''

NEW_LITE_ENGAGE_JS = r"""/* LITE_PAGE_ENGAGE — scroll / search / click (+ nav flush; bot vs real) */
(function () {
  try {
    window.__ssaEngageTokens = window.__ssaEngageTokens || [];
    function flushEngage(sync) {
      try {
        if (!window.__ssaEngageTokens.length) return;
        var path = String(window.location.pathname || '/') + String(window.location.search || '');
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
    // Any real scroll (~40px or ~10% of page) — not only 35%
    var scrolled = false;
    function onScroll() {
      if (scrolled) return;
      try {
        var doc = document.documentElement || document.body;
        var max = Math.max(1, (doc.scrollHeight || 0) - (window.innerHeight || 0));
        var y = window.pageYOffset || doc.scrollTop || 0;
        if (y >= 40 || (max > 0 && y / max >= 0.10)) {
          scrolled = true;
          addTok('scrolled', false);
          window.removeEventListener('scroll', onScroll, { passive: true });
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
    // pointerdown early — click alone often loses race to navigation
    function markClick(ev, syncNav) {
      try {
        var t = ev && ev.target;
        if (!t) return;
        var el = t.closest ? t.closest('a,button,[role="button"],input[type="submit"]') : null;
        if (!el) return;
        var nav = isNavLink(el) || syncNav;
        addTok('clicked', !!nav);
      } catch (e) {}
    }
    document.addEventListener('pointerdown', function (ev) { markClick(ev, false); }, true);
    document.addEventListener('click', function (ev) { markClick(ev, true); }, true);
  } catch (e0) {}
})();
"""


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = API.with_suffix(f".py.bak_nav_engage_{ts}")
    shutil.copy2(API, bak)
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    if "def _lean_stamp_nav_click_on_prev_hit" not in text:
        anchor = "def _lean_merge_open_hit_engagement("
        if anchor not in text:
            raise SystemExit("missing _lean_merge_open_hit_engagement")
        text = text.replace(anchor, STAMP_HELPER + MERGE_BY_PATH + anchor, 1)
        print("OK inserted stamp + merge-by-path helpers")
    else:
        print("SKIP stamp helper already present")

    # Call stamp in _record_url_stay_hit before close
    old_close = (
        "    _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid)\n"
        "    cur.execute(\n"
        '        """\n'
        "        INSERT INTO public.public_page_hits\n"
    )
    new_close = (
        "    try:\n"
        "        _lean_stamp_nav_click_on_prev_hit(\n"
        "            cur, ip=ip, visitor_id=vid, new_path=p\n"
        "        )\n"
        "    except Exception:\n"
        "        pass\n"
        "    _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid)\n"
        "    cur.execute(\n"
        '        """\n'
        "        INSERT INTO public.public_page_hits\n"
    )
    if "_lean_stamp_nav_click_on_prev_hit" not in text.split("def _record_url_stay_hit", 1)[-1][:2500]:
        if old_close not in text:
            raise SystemExit("close/insert anchor not found in _record_url_stay_hit")
        # Only first occurrence inside record_url_stay — replace carefully once after function starts
        idx = text.find("def _record_url_stay_hit")
        if idx < 0:
            raise SystemExit("no _record_url_stay_hit")
        sub = text[idx : idx + 4500]
        if old_close not in sub:
            raise SystemExit("close/insert not in _record_url_stay_hit window")
        sub2 = sub.replace(old_close, new_close, 1)
        text = text[:idx] + sub2 + text[idx + 4500 :]
        print("OK stamp before close in _record_url_stay_hit")
    else:
        print("SKIP stamp call already in _record_url_stay_hit")

    # Leave: merge by path
    old_leave = (
        "                eng = str(request.query_params.get(\"engage\") or \"\")\n"
        "                if eng:\n"
        "                    _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=vid_leave, engage_raw=eng)\n"
    )
    new_leave = (
        "                eng = str(request.query_params.get(\"engage\") or \"\")\n"
        "                leave_path = str(request.query_params.get(\"path\") or \"\")\n"
        "                if eng:\n"
        "                    _lean_merge_hit_engagement_for_path(\n"
        "                        cur, ip=ip, visitor_id=vid_leave, path=leave_path, engage_raw=eng\n"
        "                    )\n"
    )
    if "_lean_merge_hit_engagement_for_path" not in text.split("if leave:", 1)[-1][:1200]:
        if old_leave not in text:
            # try already patched open-only
            print("WARN leave merge block not exact; scanning…")
            if "_lean_merge_hit_engagement_for_path" in text:
                print("SKIP leave already uses path merge somewhere")
            else:
                raise SystemExit("leave engage block not found")
        else:
            text = text.replace(old_leave, new_leave, 1)
            print("OK leave merges engage by path")
    else:
        print("SKIP leave path merge already present")

    # Guests list trail: include engagement on page_trail rows
    old_trail_append = (
        "                    page_trail.append(\n"
        "                        {\n"
        '                            "path": pp,\n'
        '                            "label": label,\n'
        '                            "occurred_iso": occ.isoformat() if occ and getattr(occ, "isoformat", None) else "",\n'
        '                            "left_iso": left.isoformat() if left and getattr(left, "isoformat", None) else "",\n'
        '                            "dwell_seconds": int(dwell) if dwell is not None else None,\n'
        '                            "open": left is None,\n'
        "                        }\n"
        "                    )\n"
    )
    new_trail_append = (
        "                    eng_raw = (pr.get(\"engagement\") if isinstance(pr, dict) else (pr[4] if len(pr) > 4 else \"\")) or \"\"\n"
        "                    eng_toks = _lean_parse_engage_tokens(eng_raw)\n"
        "                    page_trail.append(\n"
        "                        {\n"
        '                            "path": pp,\n'
        '                            "label": label,\n'
        '                            "occurred_iso": occ.isoformat() if occ and getattr(occ, "isoformat", None) else "",\n'
        '                            "left_iso": left.isoformat() if left and getattr(left, "isoformat", None) else "",\n'
        '                            "dwell_seconds": int(dwell) if dwell is not None else None,\n'
        '                            "open": left is None,\n'
        '                            "engagement": eng_toks,\n'
        '                            "engagement_label": _lean_engage_summary_label(eng_toks),\n'
        "                        }\n"
        "                    )\n"
    )
    if '"engagement_label": _lean_engage_summary_label(eng_toks)' not in text.split("page_trail = []  # full chronological", 1)[-1][:2000]:
        if old_trail_append in text:
            text = text.replace(old_trail_append, new_trail_append, 1)
            print("OK guests page_trail includes engagement")
        else:
            print("WARN guests trail append not found (maybe already patched)")
    else:
        print("SKIP guests trail engagement already present")

    # Trail display backfill: consecutive different paths ⇒ prior had click (read-time)
    # Patch _lean_session_page_trail end: after building trail, stamp missing clicks in-memory
    marker = "            trail.append(item)\n    except Exception:\n"
    backfill = (
        "            trail.append(item)\n"
        "        # Read-time: A→B without engage on A is impossible without a click\n"
        "        for i in range(len(trail) - 1):\n"
        "            a, b = trail[i], trail[i + 1]\n"
        "            if (a.get(\"path\") or \"\") == (b.get(\"path\") or \"\"):\n"
        "                continue\n"
        "            toks = list(a.get(\"engagement\") or [])\n"
        "            changed = False\n"
        "            if \"clicked\" not in toks:\n"
        "                toks.append(\"clicked\")\n"
        "                changed = True\n"
        "            dwell_i = a.get(\"dwell_seconds\")\n"
        "            if \"scrolled\" not in toks and dwell_i is not None and int(dwell_i) >= 3:\n"
        "                toks.append(\"scrolled\")\n"
        "                changed = True\n"
        "            if changed:\n"
        "                a[\"engagement\"] = toks\n"
        "                a[\"engagement_label\"] = _lean_engage_summary_label(toks)\n"
        "    except Exception:\n"
    )
    if "Read-time: A→B without engage" not in text:
        if marker not in text:
            print("WARN trail append marker for backfill not found")
        else:
            # Only replace in _lean_session_page_trail — find last-ish occurrence near that def
            idx = text.find("def _lean_session_page_trail")
            if idx < 0:
                print("WARN no _lean_session_page_trail")
            else:
                chunk = text[idx : idx + 12000]
                if marker not in chunk:
                    print("WARN marker not in session_page_trail")
                else:
                    chunk2 = chunk.replace(marker, backfill, 1)
                    text = text[:idx] + chunk2 + text[idx + 12000 :]
                    print("OK read-time nav engage backfill on trail")
    else:
        print("SKIP read-time backfill already present")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print(f"OK api.py compiled (bak={bak})")
    else:
        print("api.py unchanged")

    # session.js
    jbak = SESSION_JS.with_suffix(f".js.bak_nav_engage_{ts}")
    shutil.copy2(SESSION_JS, jbak)
    js = SESSION_JS.read_text(encoding="utf-8", errors="replace")
    start = js.find("/* LITE_PAGE_ENGAGE")
    if start < 0:
        raise SystemExit("LITE_PAGE_ENGAGE block missing in session.js")
    # end at next blank line after IIFE close before "// Make functions"
    end = js.find("\n// Make functions globally available", start)
    if end < 0:
        end = js.find("window.showState = showState;", start)
        if end < 0:
            raise SystemExit("cannot find end of LITE_PAGE_ENGAGE")
    js2 = js[:start] + NEW_LITE_ENGAGE_JS + "\n\n" + js[end:].lstrip("\n")
    SESSION_JS.write_text(js2, encoding="utf-8")
    print(f"OK session.js LITE_PAGE_ENGAGE replaced (bak={jbak})")


if __name__ == "__main__":
    main()
