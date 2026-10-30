#!/usr/bin/env python3
"""Done/offline humans + separate hide/show quarantined bots list."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-offline-bots-panel-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # --- 1) Replace offline helper to return (humans, bots) via dual lists built in one pass ---
    # Change signature to return tuple, or add sibling function. Easiest: change to return dict
    # and update caller.

    start = text.find("def _lean_traffic_offline_sessions")
    end = text.find("\ndef lean_traffic_api_live", start)
    if start < 0 or end < 0:
        raise SystemExit("offline helper bounds missing")

    new_helper = '''def _lean_traffic_offline_sessions(cur, *, live_minutes: int = 15, lookback_hours: int = 24):
    """Completed sessions for Done/offline.

    Returns (humans, bots):
      humans — real guests only (URL trails)
      bots — quarantined / confirmed scrapers (separate hide/show panel)
    """
    humans = []
    bots = []
    try:
        if not table_exists("public_sessions"):
            return humans, bots
        cur.execute(
            """
            SELECT visitor_id, ip_address, last_path, last_activity, user_agent,
                   COALESCE(device_type, '') AS device_type, COALESCE(browser, '') AS browser,
                   COALESCE(first_seen_at, created_at) AS first_seen
            FROM public.public_sessions
            WHERE last_activity IS NOT NULL
              AND last_activity > NOW() - make_interval(hours => %s)
              AND (
                    last_activity <= NOW() - make_interval(mins => %s)
                 OR (
                      ip_address IN (
                        SELECT ip_address FROM public.traffic_quarantine_ips
                        WHERE COALESCE(active, true) = true
                          AND COALESCE(first_seen_at, last_seen_at) <= NOW() - INTERVAL '60 seconds'
                      )
                    )
                  )
              AND (ip_address IS NULL OR ip_address NOT IN """
            + _LEAN_TRAFFIC_STAFF_IP_SQL
            + """)
              AND COALESCE(last_path, '') NOT LIKE '/temp-landing%%'
              AND COALESCE(last_path, '') NOT LIKE '/admin%%'
              AND COALESCE(last_path, '') NOT LIKE '/traffic%%'
              AND COALESCE(last_path, '') NOT LIKE '/lean-traffic%%'
            ORDER BY last_activity DESC NULLS LAST
            LIMIT 80
            """,
            (int(lookback_hours), int(live_minutes)),
        )
        for row in cur.fetchall() or []:
            if isinstance(row, dict):
                ip = (row.get("ip_address") or "").strip()
                vid = (row.get("visitor_id") or "").strip()
                path = row.get("last_path") or "—"
                la = row.get("last_activity")
                ua = row.get("user_agent") or ""
                device_type = row.get("device_type") or ""
                browser = row.get("browser") or ""
                first_seen = row.get("first_seen")
            else:
                vid = (row[0] or "").strip()
                ip = (row[1] or "").strip()
                path = row[2] or "—"
                la = row[3]
                ua = row[4] or ""
                device_type = row[5] or ""
                browser = row[6] or ""
                first_seen = row[7]
            if _lean_is_agent_junk_path(path):
                continue
            trail = []
            try:
                trail = _lean_session_page_trail(cur, visitor_id=vid, ip=ip)
            except Exception:
                trail = []
            if any(_lean_is_agent_junk_path((t or {}).get("path") if isinstance(t, dict) else "") for t in trail):
                continue
            is_bot = False
            try:
                if ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
            except Exception:
                pass
            # Humans must be outside live window (not only quarantine-grace)
            in_live_window = False
            try:
                if la is not None:
                    cur.execute(
                        "SELECT (%s::timestamptz > NOW() - make_interval(mins => %s))",
                        (la, int(live_minutes)),
                    )
                    rr = cur.fetchone()
                    if rr:
                        in_live_window = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
            except Exception:
                in_live_window = False
            item = {
                "kind": "bot" if is_bot else "anon",
                "who": (f"Bot {ip}" if is_bot else f"Guest {ip}") if ip else ("Bot" if is_bot else "Guest"),
                "ip": ip,
                "visitor_id": vid,
                "path": path,
                "href": path if str(path).startswith("/") else "",
                "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else str(first_seen or ""),
                "device_type": device_type or (_traffic_ua_meta(ua)[0] if ua else ""),
                "browser": browser or (_traffic_ua_meta(ua)[1] if ua else ""),
                "page_trail": trail,
                "pages_count": len(trail),
                "session_seconds": _lean_session_total_seconds(
                    trail, first_seen=first_seen, last_activity=la
                ),
                "session_dwell_label": _lean_fmt_dwell_seconds(
                    _lean_session_total_seconds(trail, first_seen=first_seen, last_activity=la)
                ),
                "done": True,
                "quarantined": bool(is_bot),
            }
            if is_bot:
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
    except Exception:
        return humans, bots
    return humans, bots


'''
    text = text[:start] + new_helper + text[end:]

    # --- 2) Live API caller ---
    old_call = '''        offline = []
        try:
            offline = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
        except Exception:
            offline = []
'''
    new_call = '''        offline = []
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
'''
    if old_call not in text:
        raise SystemExit("offline call site not found")
    text = text.replace(old_call, new_call, 1)

    old_ret = '''                "offline": offline[:40],
                "human_live": len(human_rows),
                "human_pages": human_pages,
'''
    new_ret = '''                "offline": offline[:40],
                "offline_bots": offline_bots[:40],
                "human_live": len(human_rows),
                "human_pages": human_pages,
'''
    if old_ret not in text:
        raise SystemExit("offline return not found")
    text = text.replace(old_ret, new_ret, 1)

    # --- 3) HTML: bots panel (collapsed by default) ---
    old_html = (
        '<section class="card" style="margin-top:12px"><h2>Done / offline — last 24h</h2>'
        '<p class="note">Completed real visits only (no bots). ▶ show/hide URL trail. Session total = first page → last action.</p>'
        '<div id="offlineBox"><p class="note">Loading…</p></div></section>'
    )
    new_html = (
        '<section class="card" style="margin-top:12px"><h2>Done / offline — last 24h</h2>'
        '<p class="note">Real visits only. ▶ show/hide URL trail. Session total = first page → last action.</p>'
        '<div id="offlineBox"><p class="note">Loading…</p></div></section>'
        '<section class="card" style="margin-top:12px">'
        '<h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
        '<button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" '
        'style="font:inherit;font-weight:800">▶</button> '
        'Bots done / quarantined <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2>'
        '<p class="note">Hidden by default. Show to audit scrapers (URL trails). Not counted as real visits.</p>'
        '<div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>'
    )
    if old_html not in text:
        # try find offlineBox section loosely
        if 'id="offlineBotsBox"' not in text:
            marker = '<div id="offlineBox"><p class="note">Loading…</p></div></section>'
            if marker not in text:
                raise SystemExit("offline HTML not found")
            text = text.replace(
                marker,
                '<div id="offlineBox"><p class="note">Loading…</p></div></section>'
                + new_html.split("</section>", 1)[1]
                if False
                else marker.replace(
                    "</section>",
                    "</section>"
                    '<section class="card" style="margin-top:12px">'
                    '<h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                    '<button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" '
                    'style="font:inherit;font-weight:800">▶</button> '
                    'Bots done / quarantined <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2>'
                    '<p class="note">Hidden by default. Show to audit scrapers (URL trails).</p>'
                    '<div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>',
                    1,
                ),
                1,
            )
    else:
        text = text.replace(old_html, new_html, 1)

    if 'id="offlineBotsBox"' not in text:
        raise SystemExit("bots box HTML missing after patch")

    # --- 4) JS: shared row renderer + renderOfflineBots + toggle ---
    old_ro = "function renderOffline(d){"
    if "function renderOfflineBots" not in text:
        inject = r'''
  var OFFLINE_BOTS_OPEN=false;
  function renderOfflineRows(rows, keyPrefix){
    var html="<table><thead><tr><th>Who</th><th>Last page / total</th><th>When done</th></tr></thead><tbody>";
    rows.forEach(function(r){
      var badge=r.kind==="bot"?"bot":"anon";
      var badgeLabel=r.kind==="bot"?"bot":"guest";
      var who=esc(r.who||(r.ip?(badgeLabel==="bot"?("Bot "+r.ip):("Guest "+r.ip)):badgeLabel));
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      var n=r.pages_count!=null?r.pages_count:((r.page_trail||[]).length);
      var key=keyPrefix+":"+(r.ip||r.visitor_id||who);
      var isOpen=!!LIVE_TRAIL_OPEN[key];
      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      var arrow=trail.length
        ? ("<button type='button' class='live-exp' data-trail='"+esc(key)+"' aria-expanded='"+(isOpen?"true":"false")+"'>"+(isOpen?"▼":"▶")+"</button> ")
        : "";
      var lastP=r.path||"—";
      var lastLab=(lastP==="/"||lastP==="/index.html")?"home":lastP;
      var lastHref=lastP.indexOf("/")===0?lastP:"";
      var lastLink=lastHref?("<a href='"+esc(lastHref)+"'>"+esc(lastLab)+"</a>"):esc(lastLab);
      var sess=r.session_dwell_label?(" · session "+esc(r.session_dwell_label)):"";
      html+="<tr class='live-main' data-trail='"+esc(key)+"'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+" · done</td><td>"+lastLink+sess+" · "+n+"p</td><td>"+esc(when)+"</td></tr>";
      if(trail.length){
        var metaBits=[];
        if(r.ip) metaBits.push("IP "+esc(r.ip));
        if(r.device_type) metaBits.push(esc(r.device_type));
        if(r.browser) metaBits.push(esc(r.browser));
        if(r.quarantined) metaBits.push("quarantined");
        var thtml="<div class='trail-meta'>"+(metaBits.join(" · ")||"Session pages")+"</div>";
        thtml+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
        trail.forEach(function(pt){
          var p=pt.path||"/";
          var pLab=(p==="/"||p==="/index.html")?"home":p;
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);
          var eg=(pt.engagement_label||"");
          if(eg) pl+="<div class='trail-engage'>"+esc(eg)+"</div>";
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";
        });
        thtml+="</tbody></table>";
        html+="<tr class='live-trail' data-trail='"+esc(key)+"'"+(isOpen?"":" hidden")+"><td colspan='3'>"+thtml+"</td></tr>";
      }
    });
    html+="</tbody></table>";
    return html;
  }
  function renderOfflineBots(d){
    var box=$("offlineBotsBox");
    var cnt=$("offlineBotsCount");
    var rows=(d.offline_bots||[]).filter(function(r){ return r && r.kind==="bot"; });
    if(cnt) cnt.textContent=rows.length?("· "+rows.length):"";
    if(!box) return;
    if(!rows.length){ box.innerHTML="<p class='note'>No quarantined bots in the last 24h.</p>"; return; }
    box.innerHTML=renderOfflineRows(rows, "offbot");
  }
  function renderOffline(d){
'''
        if old_ro not in text:
            raise SystemExit("renderOffline not found")
        text = text.replace(old_ro, inject, 1)

    # Simplify renderOffline body to use renderOfflineRows for humans
    # Replace the big forEach table build - find from var rows= to box.innerHTML=html
    ro = text.find("function renderOffline(d){")
    # After our inject there may be two "function renderOffline" - find the real body after inject
    ro = text.find("function renderOffline(d){\n    var box=$(\"offlineBox\")")
    if ro < 0:
        ro = text.find("function renderOffline(d){")
        # skip to last occurrence if inject created nested
        ro2 = text.find("var box=$(\"offlineBox\")", ro)
        ro = text.rfind("function renderOffline", 0, ro2 + 1) if ro2 > 0 else ro

    # Replace human render body
    old_body_start = 'var box=$("offlineBox");\n    if(!box) return;\n    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; });'
    if old_body_start in text:
        # Find end of function - next function renderLive or function 
        body_i = text.find(old_body_start)
        # Find closing of renderOffline: look for "box.innerHTML=html;\n  }\n  function"
        end_m = text.find("box.innerHTML=html;\n  }", body_i)
        if end_m < 0:
            end_m = text.find("box.innerHTML=html;", body_i)
            end_m = text.find("\n  }", end_m)
        if end_m > 0:
            new_body = '''var box=$("offlineBox");
    if(!box) return;
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; });
    if(!rows.length){ box.innerHTML="<p class='note'>No completed real visits in the last 24h outside the live window.</p>"; }
    else box.innerHTML=renderOfflineRows(rows, "off");
    try{renderOfflineBots(d);}catch(eB){}
  }'''
            # include through old closing brace
            old_seg = text[body_i : end_m + len("\n  }")]
            # careful - replace only human part
            text = text[:body_i] + new_body + text[end_m + len("\n  }") :]

    # Wire toggle once
    if "offlineBotsToggle" in text and "OFFLINE_BOTS_TOGGLE_WIRED" not in text:
        wire = r'''
  (function wireOfflineBotsToggle(){
    var btn=$("offlineBotsToggle"), box=$("offlineBotsBox");
    if(!btn||!box||btn._wired) return;
    btn._wired=true;
    btn.addEventListener("click", function(){
      OFFLINE_BOTS_OPEN=!OFFLINE_BOTS_OPEN;
      box.hidden=!OFFLINE_BOTS_OPEN;
      btn.textContent=OFFLINE_BOTS_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false");
    });
  })();
  /* OFFLINE_BOTS_TOGGLE_WIRED */
'''
        # insert before loadAll or after renderOffline
        anchor = "function loadAll(){"
        if anchor in text:
            text = text.replace(anchor, wire + "\n  " + anchor, 1)

    # Ensure renderOfflineBots called even if body replace failed
    if "renderOfflineBots(d)" not in text:
        text = text.replace(
            "try{renderOffline(live);}catch(eOff)",
            "try{renderOffline(live); renderOfflineBots(live);}catch(eOff)",
        )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK offline humans + bots panel (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
