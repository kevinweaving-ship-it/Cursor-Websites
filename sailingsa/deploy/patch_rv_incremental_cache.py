#!/usr/bin/env python3
"""Real visitors: server cache + incremental after= API; live no longer blocks on full rebuild; harden ▶."""
from __future__ import annotations

import py_compile
import re
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

CACHE_HELPERS = r'''
# --- Real visitors cache (avoid 8s live timeout emptying the list) ---
import threading as _lean_rv_threading
_LEAN_RV_CACHE = {
    "lock": _lean_rv_threading.Lock(),
    "real_since": None,
    "humans_by_ip": {},  # ip -> item dict
    "bots_by_ip": {},
    "built_at": None,  # iso str of last full/diff build finish
    "building": False,
}

def _lean_rv_cache_lists():
    with _LEAN_RV_CACHE["lock"]:
        humans = list(_LEAN_RV_CACHE["humans_by_ip"].values())
        bots = list(_LEAN_RV_CACHE["bots_by_ip"].values())
        built = _LEAN_RV_CACHE["built_at"]
        rs = _LEAN_RV_CACHE["real_since"]
    humans.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    bots.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    return humans, bots, built, rs

def _lean_rv_cache_apply(humans, bots, real_since, replace=False):
    from datetime import datetime, timezone
    with _LEAN_RV_CACHE["lock"]:
        if replace or _LEAN_RV_CACHE["real_since"] != real_since:
            _LEAN_RV_CACHE["humans_by_ip"] = {}
            _LEAN_RV_CACHE["bots_by_ip"] = {}
            _LEAN_RV_CACHE["real_since"] = real_since
        for it in humans or []:
            ip = (it.get("ip") or "").strip()
            if ip:
                _LEAN_RV_CACHE["humans_by_ip"][ip] = it
                _LEAN_RV_CACHE["bots_by_ip"].pop(ip, None)
        for it in bots or []:
            ip = (it.get("ip") or "").strip()
            if ip:
                _LEAN_RV_CACHE["bots_by_ip"][ip] = it
                _LEAN_RV_CACHE["humans_by_ip"].pop(ip, None)
        _LEAN_RV_CACHE["built_at"] = datetime.now(timezone.utc).isoformat()
        _LEAN_RV_CACHE["building"] = False

def _lean_rv_rebuild(conn, *, after_iso=None):
    """Full or incremental rebuild into cache. after_iso => only IPs active after that time."""
    rs = _lean_traffic_real_since()
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL statement_timeout = '60000'")
    except Exception:
        pass
    # Reuse existing builder for full; for incremental filter IPs first then build subset
    if after_iso:
        try:
            cur.execute(
                """
                SELECT h.ip_address
                FROM public.public_page_hits h
                WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
                  AND h.occurred_at >= %s::timestamptz
                  AND h.occurred_at > %s::timestamptz
                  AND h.ip_address <> '102.218.215.253'
                GROUP BY h.ip_address
                ORDER BY MAX(h.occurred_at) DESC
                LIMIT 80
                """,
                (rs, after_iso),
            )
            ips = []
            for row in cur.fetchall() or []:
                ip = (row.get("ip_address") if isinstance(row, dict) else row[0]) or ""
                ip = str(ip).strip()
                if ip:
                    ips.append(ip)
            humans, bots = [], []
            if ips:
                # Fall back to full builder then filter — still cheaper when few new IPs? 
                # Full builder scans 250 IPs; for diff we call offline_sessions then filter.
                h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
                ipset = set(ips)
                humans = [x for x in (h or []) if (x.get("ip") or "") in ipset]
                bots = [x for x in (b or []) if (x.get("ip") or "") in ipset]
                # Also include any of those IPs classified only as still-live (not in humans) — skip
            _lean_rv_cache_apply(humans, bots, rs, replace=False)
            return humans, bots
        except Exception:
            _lean_db_rollback(conn)
            # fall through to full
    h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
    _lean_rv_cache_apply(h or [], b or [], rs, replace=True)
    return h or [], b or []

'''

# Route registration via middleware path check - add real-visitors API


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    if "_LEAN_RV_CACHE" not in text:
        # insert before _lean_traffic_offline_sessions
        anchor = "def _lean_traffic_offline_sessions("
        if anchor not in text:
            raise SystemExit("offline_sessions missing")
        text = text.replace(anchor, CACHE_HELPERS + "\n" + anchor, 1)
        print("OK cache helpers")
    else:
        print("SKIP cache helpers")

    # live API: use cache instead of inline offline_sessions
    old_off = """        offline = []
        offline_bots = []
        try:
            _off = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
            if isinstance(_off, tuple) and len(_off) == 2:
                offline, offline_bots = _off
            else:
                offline = _off or []
                offline_bots = []
        except Exception:
            offline = []
            offline_bots = []
"""
    new_off = """        # Real visitors: cache only on /live (full rebuild is too slow for 8s timeout → was returning [])
        offline = []
        offline_bots = []
        try:
            offline, offline_bots, _built, _rs = _lean_rv_cache_lists()
        except Exception:
            offline, offline_bots = [], []
"""
    if "serve from cache (full rebuild is too slow" in text:
        print("SKIP live cache wire")
    elif old_off in text:
        text = text.replace(old_off, new_off, 1)
        print("OK live uses RV cache")
    else:
        raise SystemExit("live offline block missing")

    # Add JSON fields fetched_at on live response
    old_resp = """                "offline": offline[:200],
                "real_since": _lean_traffic_real_since(),
                "offline_fb": offline_fb[:40],
                "offline_bots": offline_bots[:40],
"""
    new_resp = """                "offline": offline[:200],
                "real_since": _lean_traffic_real_since(),
                "offline_fetched_at": (_LEAN_RV_CACHE.get("built_at") or ""),
                "offline_fb": offline_fb[:40],
                "offline_bots": offline_bots[:40],
"""
    if "offline_fetched_at" not in text:
        if old_resp not in text:
            raise SystemExit("live response offline keys missing")
        text = text.replace(old_resp, new_resp, 1)
        print("OK offline_fetched_at field")
    else:
        print("SKIP fetched_at")

    # Middleware route for /traffic/api/real-visitors
    mw = '        if path == "/traffic/api/live":\n            return lean_traffic_api_live(request)'
    mw_new = '''        if path == "/traffic/api/live":
            return lean_traffic_api_live(request)
        if path == "/traffic/api/real-visitors":
            return lean_traffic_api_real_visitors(request)'''
    if "/traffic/api/real-visitors" not in text:
        if mw not in text:
            raise SystemExit("middleware live route missing")
        text = text.replace(mw, mw_new, 1)
        print("OK middleware real-visitors")
    else:
        print("SKIP middleware")

    # Define lean_traffic_api_real_visitors near lean_traffic_api_live
    if "def lean_traffic_api_real_visitors" not in text:
        endpoint = r'''
def lean_traffic_api_real_visitors(request: Request):
    """Real visitors list — cached; ?after=ISO for incremental diff since last fetch."""
    denied = _lean_traffic_gate(request)
    if denied is not None:
        if isinstance(denied, RedirectResponse):
            return denied
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    after = (request.query_params.get("after") or "").strip() or None
    full = (request.query_params.get("full") or "").strip() in ("1", "true", "yes")
    conn = None
    try:
        conn = get_db_connection()
        if full or not _LEAN_RV_CACHE.get("built_at") or after:
            try:
                _LEAN_RV_CACHE["building"] = True
                _lean_rv_rebuild(conn, after_iso=None if full or not after else after)
            except Exception as e:
                _lean_db_rollback(conn)
                _LEAN_RV_CACHE["building"] = False
                # still return cache if any
        humans, bots, built, rs = _lean_rv_cache_lists()
        # If after set, only return rows newer than after (diff payload)
        if after and not full:
            def _newer(r):
                la = str(r.get("last_activity") or "")
                return la > after
            humans = [r for r in humans if _newer(r)]
            bots = [r for r in bots if _newer(r)]
        return JSONResponse(
            {
                "ok": True,
                "real_since": rs or _lean_traffic_real_since(),
                "offline": humans[:200],
                "offline_bots": bots[:40],
                "offline_fetched_at": built or "",
                "diff": bool(after) and not full,
            },
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)[:200]}, status_code=500)
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

'''
        anchor = "def lean_traffic_api_live(request: Request):"
        if anchor not in text:
            raise SystemExit("lean_traffic_api_live missing")
        text = text.replace(anchor, endpoint + "\n" + anchor, 1)
        print("OK real-visitors endpoint")
    else:
        print("SKIP endpoint")

    # --- Frontend: load Real visitors from dedicated endpoint; incremental Refresh; onclick ▶ ---
    # Replace renderOffline function's data source wiring in loadAll and Refresh

    old_rv_click = """  if(!window.__rvClickWired){
    window.__rvClickWired=true;
    document.addEventListener("click", function(ev){
      var box=$("offlineBox");
      if(!box || !box.contains(ev.target)) return;
      var btn=ev.target.closest && ev.target.closest("button.rv-exp[data-rvid]");
      var row=(!btn && ev.target.closest) ? ev.target.closest("tr.rv-main[data-rvid]") : null;
      if(!btn && !row) return;
      if(ev.target.closest && ev.target.closest("a[href]") && !btn) return;
      var id=(btn||row).getAttribute("data-rvid");
      if(!id) return;
      ev.preventDefault();
      ev.stopPropagation();
      rvToggle(id);
    });
  }
"""
    new_rv_click = """  window.__rvToggle = rvToggle;
  /* clicks: inline onclick on buttons + row handler below */
"""
    if "window.__rvToggle = rvToggle" not in text:
        if old_rv_click in text:
            text = text.replace(old_rv_click, new_rv_click, 1)
            print("OK rvToggle on window")
        else:
            print("WARN rv click block missing")

    # arrow with onclick
    old_arrow = """      var arrow=trail.length
        ? ("<button type='button' class='rv-exp' data-rvid='"+rvEsc(id)+"' aria-expanded='"+(open?"true":"false")+"' style='min-width:44px;min-height:44px;border:0;background:"+(open?"#ccfbf1":"transparent")+";font-weight:900;cursor:pointer'>"+(open?"▼":"▶")+"</button> ")
        : "";
"""
    new_arrow = """      var arrow=trail.length
        ? ("<button type='button' class='rv-exp' data-rvid='"+rvEsc(id)+"' aria-expanded='"+(open?"true":"false")+"' "
          +"onclick=\\"return window.__rvToggle(this.getAttribute('data-rvid'))\\" "
          +"style='min-width:44px;min-height:44px;border:0;background:"+(open?"#ccfbf1":"transparent")+";font-weight:900;cursor:pointer'>"+(open?"▼":"▶")+"</button> ")
        : "";
"""
    if "window.__rvToggle(this.getAttribute" not in text:
        if old_arrow in text:
            text = text.replace(old_arrow, new_arrow, 1)
            print("OK inline onclick arrow")
        else:
            print("WARN arrow pattern missing")

    # Replace Refresh + add loadRealVisitors incremental
    # Insert before renderOffline function a loader
    loader = r'''
  window.__rvFetchedAt = window.__rvFetchedAt || "";
  function loadRealVisitors(opts){
    opts = opts || {};
    var box=$("offlineBox");
    var q = opts.full ? "?full=1" : (window.__rvFetchedAt ? ("?after="+encodeURIComponent(window.__rvFetchedAt)) : "?full=1");
    if(box && !box.querySelector("table") && !opts.silent) box.innerHTML="<p class='note'>Loading real visitors…</p>";
    return fetchJson("/traffic/api/real-visitors"+q).then(function(d){
      if(!d || !d.ok) throw new Error((d && d.error) || "real-visitors failed");
      if(d.diff && window.__rvRowsMerge){
        window.__rvRowsMerge(d);
      } else {
        renderOffline(d);
      }
      if(d.offline_fetched_at) window.__rvFetchedAt = d.offline_fetched_at;
      else if(d.real_since) window.__rvFetchedAt = d.real_since;
      return d;
    }).catch(function(e){
      if(box && !box.querySelector("table")) box.innerHTML="<p class='note'>Could not load real visitors ("+esc(String(e.message||e))+"). Tap Refresh.</p>";
    });
  }
  window.__rvRowsMerge = function(d){
    // Merge diff rows into cached list then re-render from merged snapshot stored on window
    var prev = window.__rvLastOffline || [];
    var byIp = {};
    prev.forEach(function(r){ if(r && r.ip) byIp[r.ip]=r; });
    (d.offline||[]).forEach(function(r){ if(r && r.ip) byIp[r.ip]=r; });
    var merged = Object.keys(byIp).map(function(k){ return byIp[k]; });
    merged.sort(function(a,b){ return String(b.last_activity||"").localeCompare(String(a.last_activity||"")); });
    window.__rvLastOffline = merged;
    renderOffline({ok:true, offline:merged, real_since:d.real_since, offline_bots:d.offline_bots, offline_fb:d.offline_fb});
  };
'''

    if "function loadRealVisitors" not in text:
        text = text.replace(
            "  /* ==== Real visitors (rebuilt)",
            loader + "\n  /* ==== Real visitors (rebuilt)",
            1,
        )
        print("OK loadRealVisitors")
    else:
        print("SKIP loader")

    # In renderOffline after successful rows paint, stash __rvLastOffline
    if "window.__rvLastOffline = rows" not in text:
        text = text.replace(
            "    window.__rvData={};\n    var pages=0;",
            "    window.__rvLastOffline = rows;\n    window.__rvData={};\n    var pages=0;",
            1,
        )
        print("OK stash last offline")

    # Refresh button uses loadRealVisitors
    old_ref = """    var rb=$("rvRefreshBtn");
    if(rb){
      rb.addEventListener("click", function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        rb.disabled=true; rb.textContent="…";
        fetchJson("/traffic/api/live").then(function(d){
          if(d && d.ok) renderOffline(d);
        }).catch(function(){}).then(function(){ try{ rb.disabled=false; rb.textContent="Refresh"; }catch(eR){} });
      });
    }
"""
    new_ref = """    var rb=$("rvRefreshBtn");
    if(rb){
      rb.addEventListener("click", function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        rb.disabled=true; rb.textContent="…";
        loadRealVisitors({full:false}).then(function(){
          try{ rb.disabled=false; rb.textContent="Refresh"; }catch(eR){}
        });
      });
    }
"""
    if old_ref in text:
        text = text.replace(old_ref, new_ref, 1)
        print("OK refresh incremental")
    else:
        print("WARN refresh block missing")

    # loadAll: after live fetch, also loadRealVisitors (don't rely on live.offline)
    # Find try{renderOffline(live)} in loadAll
    if "loadRealVisitors({full:true})" not in text:
        # replace first renderOffline(live) in loadAll success path
        old_l = "        try{renderOffline(live);}catch(eOff){ var ob=$(\"offlineBox\"); if(ob) ob.innerHTML=\"<p class='note'>No offline data.</p>\"; }"
        new_l = "        try{ loadRealVisitors({full: !window.__rvFetchedAt}); }catch(eOff){ var ob=$(\"offlineBox\"); if(ob) ob.innerHTML=\"<p class='note'>No offline data.</p>\"; }"
        if old_l in text:
            text = text.replace(old_l, new_l, 1)
            print("OK loadAll -> loadRealVisitors")
        else:
            # softer
            c = text.count("renderOffline(live)")
            print("WARN loadAll pattern missing; renderOffline(live) count", c)
            text = text.replace(
                "try{renderOffline(live);}catch(eOff)",
                "try{loadRealVisitors({full:!window.__rvFetchedAt});}catch(eOff)",
                1,
            )
            print("OK loadAll replace v2")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
