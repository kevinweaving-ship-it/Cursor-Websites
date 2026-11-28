#!/usr/bin/env python3
"""Sync Live graph + card with Live now list; recover engaged IPs missing from list."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, Path(f"/root/backups/api.live_graph_list_sync_{ts}.py"))
print("BACKUP", ts)

text = API.read_text(encoding="utf-8", errors="replace")

# --- Module snapshot for series ↔ live alignment ---
SNAP_ANCHOR = '_LEAN_RV_CACHE = {\n    "lock": _lean_rv_threading.Lock(),'
SNAP_INSERT = '''_LEAN_LIVE_HUMAN_SNAPSHOT = {"human_live": None, "at": 0.0}

''' + SNAP_ANCHOR

if "_LEAN_LIVE_HUMAN_SNAPSHOT" not in text:
    if SNAP_ANCHOR in text:
        text = text.replace(SNAP_ANCHOR, SNAP_INSERT, 1)
        print("ok snapshot var")
    else:
        print("WARN snapshot anchor missing")

# --- Live API: save human count + recover engaged IPs ---
LIVE_SNAP_BEFORE_RETURN = '''        human_rows = [r for r in rows if r.get("kind") != "bot"]
        human_pages = sum(int(r.get("pages_count") or 0) for r in human_rows)

        return JSONResponse('''

LIVE_SNAP_WITH_CACHE = '''        human_rows = [r for r in rows if r.get("kind") != "bot"]
        human_pages = sum(int(r.get("pages_count") or 0) for r in human_rows)
        try:
            import time as _lean_live_snap_time
            _LEAN_LIVE_HUMAN_SNAPSHOT["human_live"] = len(human_rows)
            _LEAN_LIVE_HUMAN_SNAPSHOT["at"] = _lean_live_snap_time.time()
        except Exception:
            pass

        return JSONResponse('''

if LIVE_SNAP_BEFORE_RETURN in text and "_LEAN_LIVE_HUMAN_SNAPSHOT[\"human_live\"]" not in text.split("def lean_traffic_api_live")[1].split("def lean_traffic_api_top")[0]:
    text = text.replace(LIVE_SNAP_BEFORE_RETURN, LIVE_SNAP_WITH_CACHE, 1)
    print("ok live snapshot write")

IP_RECOVERY_ANCHOR = """        except Exception:
            _lean_db_rollback(conn)
        try:
            conn.commit()
        except Exception:
            _lean_db_rollback(conn)
        # Drop agent/admin junk from Live list (never public visitors)"""

IP_RECOVERY_BLOCK = """        except Exception:
            _lean_db_rollback(conn)
        # Recover by IP: scroll/click in live window but missing from sessions (graph had them, list did not)
        try:
            if table_exists("public_page_hits"):
                seen_ips_engaged = {(r.get("ip") or "").strip() for r in rows if (r.get("ip") or "").strip()}
                cur.execute(
                    \"\"\"
                    SELECT DISTINCT ON (h.ip_address)
                        h.ip_address,
                        COALESCE(h.visitor_id, '') AS visitor_id,
                        h.path,
                        h.occurred_at AS last_activity
                    FROM public.public_page_hits h
                    WHERE h.occurred_at > NOW() - make_interval(mins => %s)
                      AND h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
                      AND h.ip_address NOT IN \"\"\"
                    + _LEAN_TRAFFIC_STAFF_IP_SQL
                    + \"\"\"
                      AND h.ip_address NOT IN \"\"\"
                    + _LEAN_TRAFFIC_QUARANTINE_IP_SQL
                    + \"\"\"
                      AND COALESCE(h.path, '') NOT LIKE '/temp-landing%%'
                      AND COALESCE(h.path, '') NOT LIKE '/dev-1%%'
                      AND COALESCE(h.path, '') NOT LIKE '/traffic%%'
                      AND COALESCE(h.path, '') NOT LIKE '/admin%%'
                      AND (
                        h.engagement ~* 'scroll'
                        OR (h.engagement ~* 'click' AND h.engagement !~* 'search')
                      )
                    ORDER BY h.ip_address, h.occurred_at DESC
                    LIMIT 40
                    \"\"\",
                    (_LEAN_TRAFFIC_LIVE_MINUTES,),
                )
                for r in cur.fetchall() or []:
                    d = r if isinstance(r, dict) else {
                        "ip_address": r[0], "visitor_id": r[1], "path": r[2], "last_activity": r[3],
                    }
                    ip = (d.get("ip_address") or "").strip()
                    if not ip or ip in seen_ips_engaged:
                        continue
                    full_vid = (d.get("visitor_id") or "").strip()
                    path = d.get("path") or "—"
                    la = d.get("last_activity")
                    trail = []
                    try:
                        trail = _lean_session_page_trail(cur, visitor_id=full_vid or None, ip=ip)
                    except Exception:
                        _lean_db_rollback(conn)
                        trail = []
                    if _lean_is_agent_junk_path(path):
                        continue
                    if any(_lean_is_agent_junk_path((t or {}).get("path") if isinstance(t, dict) else "") for t in trail):
                        continue
                    rows.append({
                        "kind": "anon",
                        "who": f"Guest {ip}",
                        "who_href": "",
                        "guessed": False,
                        "likely_name": "",
                        "likely_slug": "",
                        "likely_hits": 0,
                        "sas_id": "",
                        "ip": ip,
                        "visitor_id": full_vid,
                        "path": path,
                        "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                        "device": "",
                        "device_type": "",
                        "browser": "",
                        "href": path if str(path).startswith("/") else "",
                        "page_trail": trail,
                        "pages_count": len(trail),
                        "session_seconds": _lean_session_total_seconds(trail, last_activity=la),
                        "session_dwell_label": _lean_fmt_dwell_seconds(
                            _lean_session_total_seconds(trail, last_activity=la)
                        ),
                    })
                    seen_ips_engaged.add(ip)
        except Exception:
            _lean_db_rollback(conn)
        try:
            conn.commit()
        except Exception:
            _lean_db_rollback(conn)
        # Drop agent/admin junk from Live list (never public visitors)"""

if IP_RECOVERY_ANCHOR in text and "seen_ips_engaged" not in text:
    text = text.replace(IP_RECOVERY_ANCHOR, IP_RECOVERY_BLOCK, 1)
    print("ok ip recovery")

# --- Series API: align live_now with live list snapshot ---
OLD_SERIES_LIVE = """        if range_key == "live" and points:
            # Rightmost point is "live now" for this wave — expose for UI cross-check
            live_now_series = int(points[-1].get("visitors") or 0)
        else:
            live_now_series = None"""

NEW_SERIES_LIVE = """        if range_key == "live" and points:
            live_now_series = int(points[-1].get("visitors") or 0)
            try:
                import time as _lean_series_snap_time
                snap = _LEAN_LIVE_HUMAN_SNAPSHOT
                if snap.get("human_live") is not None and (_lean_series_snap_time.time() - float(snap.get("at") or 0)) < 45:
                    hl = int(snap["human_live"])
                    points[-1]["visitors"] = hl
                    live_now_series = hl
            except Exception:
                pass
        else:
            live_now_series = None"""

if OLD_SERIES_LIVE in text:
    text = text.replace(OLD_SERIES_LIVE, NEW_SERIES_LIVE, 1)
    print("ok series live_now")

# --- JS: sync graph + card to human_live from /live ---
JS_ANCHOR = "  var SERIES_HIT=[], SERIES_LAYOUT=null, SELECTED_BUCKET=\"\", LAST_SERIES=null;\n  function drawSeries(payload){"
JS_INSERT = """  var SERIES_HIT=[], SERIES_LAYOUT=null, SELECTED_BUCKET="", LAST_SERIES=null;
  window.__liveHumanCount = null;
  function syncLiveGraphToList(payload){
    if(!payload) return payload;
    if((payload.range||RANGE)!=="live") return payload;
    if(window.__liveHumanCount==null) return payload;
    var pts=payload.points||[];
    if(!pts.length) return payload;
    pts[pts.length-1].visitors = window.__liveHumanCount;
    payload.live_now = window.__liveHumanCount;
    var ym=1;
    pts.forEach(function(z){ ym=Math.max(ym, Number(z.visitors||0)); });
    payload.y_max = ym;
    return payload;
  }
  function drawSeries(payload){
    payload = syncLiveGraphToList(payload||{});"""

if JS_ANCHOR in text and "syncLiveGraphToList" not in text:
    text = text.replace(JS_ANCHOR, JS_INSERT, 1)
    print("ok js sync fn")

OLD_LIVE_FETCH = """    fetchJson("/traffic/api/live").then(function(live){
      if(live.ok){
        renderLive(live);
        try{ renderOfflineFb(live); }catch(eF){}
        try{ renderOfflineBots(live); }catch(eB){}
        try{ loadRealVisitors({full: !window.__rvFetchedAt}); }catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class='note'>No offline data.</p>"; }
        // Card must match Live list (not a separate unified count that can show 1 with empty list)
        if(RANGE==="live" && live.human_live!=null){
          $("kLive").textContent=String(live.human_live);
        }
      } else { $("liveBox").innerHTML="<p class='err'>"+esc(live.error||"live failed")+"</p>"; var ob2=$("offlineBox"); if(ob2) ob2.innerHTML="<p class='note'>—</p>"; }
    }).catch(function(e){ $("liveBox").innerHTML="<p class='err'>"+esc(e.message||e)+"</p>"; });"""

NEW_LIVE_FETCH = """    fetchJson("/traffic/api/live").then(function(live){
      if(live.ok){
        window.__liveHumanCount = (live.human_live!=null) ? Number(live.human_live) : 0;
        renderLive(live);
        try{ renderOfflineFb(live); }catch(eF){}
        try{ renderOfflineBots(live); }catch(eB){}
        try{ loadRealVisitors({full: !window.__rvFetchedAt}); }catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class='note'>No offline data.</p>"; }
        if(RANGE==="live"){
          $("kLive").textContent=String(window.__liveHumanCount);
          if(LAST_SERIES) drawSeries(syncLiveGraphToList(Object.assign({}, LAST_SERIES)));
        }
      } else { $("liveBox").innerHTML="<p class='err'>"+esc(live.error||"live failed")+"</p>"; var ob2=$("offlineBox"); if(ob2) ob2.innerHTML="<p class='note'>—</p>"; }
    }).catch(function(e){ $("liveBox").innerHTML="<p class='err'>"+esc(e.message||e)+"</p>"; });"""

if OLD_LIVE_FETCH in text:
    text = text.replace(OLD_LIVE_FETCH, NEW_LIVE_FETCH, 1)
    print("ok js live fetch")

OLD_SERIES_FETCH = """    fetchJson("/traffic/api/series"+q).then(function(s){
      if(s.ok){
        drawSeries(s);
        // Do not overwrite LIVE NOW from series — /live human_live is source of truth for the card
      } else drawSeries({points:[],y_max:1,range:RANGE});
    }).catch(function(){ drawSeries({points:[],y_max:1,range:RANGE}); });"""

NEW_SERIES_FETCH = """    fetchJson("/traffic/api/series"+q).then(function(s){
      if(s.ok){
        drawSeries(syncLiveGraphToList(s));
      } else drawSeries({points:[],y_max:1,range:RANGE});
    }).catch(function(){ drawSeries({points:[],y_max:1,range:RANGE}); });"""

if OLD_SERIES_FETCH in text:
    text = text.replace(OLD_SERIES_FETCH, NEW_SERIES_FETCH, 1)
    print("ok js series fetch")

OLD_POLL = """        if(o && o.ok){
          var liveCard=(s && s.ok && s.live_now!=null)?s.live_now:(o.live_total||0);
          $("kLive").textContent=String(liveCard);
          $("kLiveSub").textContent="total online · last "+(o.live_minutes||15)+" min window"+(o.live_signed?(" · "+o.live_signed+" signed"):"")+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots quarantined"):"");
          $("kVis").textContent=String(o.visitors||0);
          $("kHits").textContent=String(o.hits||0);
          $("kSigned").textContent=String((o.signed_card!=null?o.signed_card:o.live_signed)||0);
          if($("kSignedLabel")) $("kSignedLabel").textContent=(RANGE==="live")?"Signed-in live":"Signed-in";
          if($("kSignedSub")) $("kSignedSub").textContent=String(o.guests_card!=null?o.guests_card:o.live_anon||0)+" guests"+(RANGE==="live"?" live":" in range");
          if($("kDirect")) $("kDirect").textContent=String(o.direct_landings||0);
          if($("kDirectSub")) $("kDirectSub").textContent=(o.direct_visitors? (o.direct_visitors+" visitors · "):"")+"typed / bookmark / chat link";
          if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
          if($("kGoogleSub")) $("kGoogleSub").textContent=(o.google_visitors? (o.google_visitors+" visitors · "):"")+"via Google";
          if($("kFb")) $("kFb").textContent=String(o.facebook_landings||0);
          if($("kFbSub")) $("kFbSub").textContent=(o.facebook_visitors? (o.facebook_visitors+" visitors · "):"")+"via Facebook";
          // Claim KPI refreshed from claim-attempts in loadAll — do not overwrite with overview estimate
        }
        if(s && s.ok) drawSeries(s);
        if(live && live.ok){
          // POLL: numbers only — never rebuild Live/Real visitors tables (was flashing every 3s)
          if(live.human_live!=null) $("kLive").textContent=String(live.human_live);
          else if(live.rows) $("kLive").textContent=String((live.rows||[]).length);
        }"""

NEW_POLL = """        if(o && o.ok){
          $("kLiveSub").textContent="total online · last "+(o.live_minutes||15)+" min window"+(o.live_signed?(" · "+o.live_signed+" signed"):"")+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots quarantined"):"");
          $("kVis").textContent=String(o.visitors||0);
          $("kHits").textContent=String(o.hits||0);
          $("kSigned").textContent=String((o.signed_card!=null?o.signed_card:o.live_signed)||0);
          if($("kSignedLabel")) $("kSignedLabel").textContent=(RANGE==="live")?"Signed-in live":"Signed-in";
          if($("kSignedSub")) $("kSignedSub").textContent=String(o.guests_card!=null?o.guests_card:o.live_anon||0)+" guests"+(RANGE==="live"?" live":" in range");
          if($("kDirect")) $("kDirect").textContent=String(o.direct_landings||0);
          if($("kDirectSub")) $("kDirectSub").textContent=(o.direct_visitors? (o.direct_visitors+" visitors · "):"")+"typed / bookmark / chat link";
          if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
          if($("kGoogleSub")) $("kGoogleSub").textContent=(o.google_visitors? (o.google_visitors+" visitors · "):"")+"via Google";
          if($("kFb")) $("kFb").textContent=String(o.facebook_landings||0);
          if($("kFbSub")) $("kFbSub").textContent=(o.facebook_visitors? (o.facebook_visitors+" visitors · "):"")+"via Facebook";
        }
        if(live && live.ok){
          window.__liveHumanCount = (live.human_live!=null) ? Number(live.human_live) : 0;
          $("kLive").textContent=String(window.__liveHumanCount);
        }
        if(s && s.ok) drawSeries(syncLiveGraphToList(s));"""

if OLD_POLL in text:
    text = text.replace(OLD_POLL, NEW_POLL, 1)
    print("ok js poll")

API.write_text(text, encoding="utf-8")
print("WROTE", API)
