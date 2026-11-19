#!/usr/bin/env python3
"""Traffic audit UX: confident bots, hide agent/admin, offline done trails, human-only totals."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-traffic-audit-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # --- 1) Expand confident bot: deep-link only (boat/sailor, no home), esp. cloud ---
    old_beh = '''def _lean_behavior_confident_bot(page_trail: list, current_path: str = "") -> bool:
    """High-confidence scraper pattern (not a maybe).

    Confirmed shape we have seen (e.g. Alibaba deep-link swarm):
      - never touches home/landing
      - enters on /boat/ or /sailor/
      - short hop trail (3–8 URLs)
      - almost all dwells <= 2s (then often stops)
    """
'''
    # Replace whole function - find end at next def
    start = text.find("def _lean_behavior_confident_bot")
    if start < 0:
        raise SystemExit("behavior fn missing")
    end = text.find("\ndef _lean_human_traffic_pass", start)
    if end < 0:
        end = text.find("\ndef ", start + 1)
    new_beh = '''def _lean_is_agent_junk_path(path: Optional[str]) -> bool:
    """Cursor/agent/dev paths that must never count as public traffic."""
    p = (path or "").split("?", 1)[0].strip() or "/"
    low = p.lower()
    if low in ("/workspace", "/cursor", "/agent"):
        return True
    if low.startswith("/workspace/") or low.startswith("/.cursor"):
        return True
    if "clean-trail" in low or "local-trail" in low:
        return True
    return False


def _lean_behavior_confident_bot(page_trail: list, current_path: str = "", ip: str = "") -> bool:
    """High-confidence scraper pattern (not a maybe).

    Confirmed shapes:
      A) deep-link only on /boat/ or /sailor/ (no home) — classic Alibaba/cloud entry
      B) short hop trail (3–8) no home, mostly <=2s dwell
      C) agent junk paths (/workspace, etc.)
    """
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    dwells = []
    for pt in trail:
        if not isinstance(pt, dict):
            continue
        p = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
        paths.append(p)
        if _lean_is_agent_junk_path(p):
            return True
        if pt.get("open"):
            continue
        try:
            dwells.append(int(pt.get("dwell_seconds") if pt.get("dwell_seconds") is not None else 0))
        except Exception:
            dwells.append(0)
    if not paths:
        p0 = (current_path or "").split("?", 1)[0].strip() or "/"
        paths = [p0]
    if any(_lean_is_agent_junk_path(p) for p in paths) or _lean_is_agent_junk_path(current_path):
        return True
    if any(p in ("/", "/index.html") for p in paths):
        # has home — only bot if short-hop swarm (rare with home)
        pass
    else:
        first = paths[0]
        deep = first.startswith("/boat/") or first.startswith("/sailor/")
        if deep:
            # 1-page (or few) deep-link with no home = confident bot, esp. cloud/datacenter
            if len(paths) <= 2:
                try:
                    if ip and _lean_ip_is_cloud_datacenter(ip):
                        return True
                except Exception:
                    pass
                # even non-cloud: bare boat/sailor entry with no home/click trail = bot smell we accept as bot
                return True
            if 3 <= len(paths) <= 8:
                if len(dwells) >= max(2, len(paths) - 1):
                    short = sum(1 for d in dwells if d <= 2)
                    if short >= len(dwells) * 0.75:
                        return True
                return True
    n = len(paths)
    if n < 3 or n > 8:
        return False
    if any(p in ("/", "/index.html") for p in paths):
        return False
    first = paths[0]
    if not (first.startswith("/boat/") or first.startswith("/sailor/")):
        return False
    if len(dwells) < max(2, n - 1):
        return False
    short = sum(1 for d in dwells if d <= 2)
    return short >= len(dwells) * 0.75


'''
    text = text[:start] + new_beh + text[end:]

    # Update call sites to pass ip=
    text = text.replace(
        "_lean_behavior_confident_bot(_trail_pre, path)",
        "_lean_behavior_confident_bot(_trail_pre, path, ip)",
    )
    text = text.replace(
        "_lean_behavior_confident_bot(_tr, path)",
        "_lean_behavior_confident_bot(_tr, path, ip)",
    )

    # --- 2) Live: hide agent junk + staff IPs from live rows entirely; quarantine bots ---
    # After is_bot decided and before appending row, skip agent junk / staff
    # Find rows.append in live for anon - easier to filter at end before return

    live_ret = '''        rows.sort(key=lambda x: x.get("last_activity") or "", reverse=True)
        return JSONResponse(
            {"ok": True, "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES, "rows": rows[:50]},
            headers={"Cache-Control": "no-store"},
        )'''
    if live_ret not in text:
        raise SystemExit("live return not found")
    live_ret_new = '''        # Drop agent/admin junk from Live list (never public visitors)
        filtered = []
        for r in rows:
            try:
                ip_r = (r.get("ip") or "").strip()
                path_r = (r.get("path") or "")
                if _lean_is_agent_junk_path(path_r):
                    if ip_r:
                        try:
                            _lean_quarantine_ip(cur, ip_r, "agent_junk_path")
                        except Exception:
                            pass
                    continue
                trail_r = r.get("page_trail") or []
                if any(_lean_is_agent_junk_path((t or {}).get("path") if isinstance(t, dict) else "") for t in trail_r):
                    if ip_r:
                        try:
                            _lean_quarantine_ip(cur, ip_r, "agent_junk_path")
                        except Exception:
                            pass
                    continue
                # staff IPs (signed-in Tim/Kevin wifi) stay out of public Live
                if ip_r:
                    try:
                        cur.execute(
                            "SELECT 1 WHERE %s IN " + _LEAN_TRAFFIC_STAFF_IP_SQL + " LIMIT 1",
                            (ip_r,),
                        )
                        if cur.fetchone():
                            continue
                    except Exception:
                        pass
                if r.get("kind") == "bot" and ip_r:
                    try:
                        _lean_quarantine_ip(cur, ip_r, "live_bot")
                    except Exception:
                        pass
                filtered.append(r)
            except Exception:
                filtered.append(r)
        rows = filtered
        rows.sort(key=lambda x: x.get("last_activity") or "", reverse=True)

        # Offline / done sessions (outside live window, still in lookback) for audit
        offline = []
        try:
            offline = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
        except Exception:
            offline = []

        # Human-only live stats for the card strip
        human_rows = [r for r in rows if r.get("kind") != "bot"]
        human_pages = sum(int(r.get("pages_count") or 0) for r in human_rows)

        return JSONResponse(
            {
                "ok": True,
                "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES,
                "rows": rows[:50],
                "offline": offline[:40],
                "human_live": len(human_rows),
                "human_pages": human_pages,
            },
            headers={"Cache-Control": "no-store"},
        )'''
    text = text.replace(live_ret, live_ret_new, 1)

    # --- 3) Offline sessions helper ---
    if "def _lean_traffic_offline_sessions" not in text:
        helper = '''def _lean_traffic_offline_sessions(cur, *, live_minutes: int = 15, lookback_hours: int = 24) -> list:
    """Completed IP sessions (last_activity older than live window) with URL trails for audit."""
    out = []
    try:
        if not table_exists("public_sessions"):
            return out
        cur.execute(
            """
            SELECT visitor_id, ip_address, last_path, last_activity, user_agent,
                   COALESCE(device_type, '') AS device_type, COALESCE(browser, '') AS browser,
                   COALESCE(first_seen_at, created_at) AS first_seen
            FROM public.public_sessions
            WHERE last_activity IS NOT NULL
              AND last_activity <= NOW() - make_interval(mins => %s)
              AND last_activity > NOW() - make_interval(hours => %s)
              AND (ip_address IS NULL OR ip_address NOT IN """
            + _LEAN_TRAFFIC_STAFF_IP_SQL
            + """)
              AND COALESCE(last_path, '') NOT LIKE '/temp-landing%%'
              AND COALESCE(last_path, '') NOT LIKE '/admin%%'
              AND COALESCE(last_path, '') NOT LIKE '/traffic%%'
            ORDER BY last_activity DESC NULLS LAST
            LIMIT 40
            """,
            (int(live_minutes), int(lookback_hours)),
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
            if ip and _lean_ip_is_quarantined(cur, ip):
                # still show quarantined offline for audit, marked bot
                pass
            trail = []
            try:
                trail = _lean_session_page_trail(cur, visitor_id=vid, ip=ip)
            except Exception:
                trail = []
            if any(_lean_is_agent_junk_path((t or {}).get("path") if isinstance(t, dict) else "") for t in trail):
                continue
            is_bot = False
            try:
                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
            except Exception:
                pass
            out.append(
                {
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
                    "done": True,
                }
            )
    except Exception:
        return out
    return out


'''
        anchor = text.find("def lean_traffic_api_live")
        text = text[:anchor] + helper + text[anchor:]

    # --- 4) Overview: human-only hits/visitors for live range (exclude quarantine already; also exclude bot-like via quarantine after classify)
    # Also exclude agent paths from unified via path_ok - add workspace to path_ok
    old_path_ok = "      AND {col} NOT LIKE '{pct}local-trail{pct}'"
    if old_path_ok in text and "workspace" not in text[text.find("def _lean_traffic_path_ok_sql") : text.find("def _lean_traffic_path_ok_sql") + 900]:
        text = text.replace(
            old_path_ok,
            "      AND {col} NOT LIKE '{pct}local-trail{pct}'\n"
            "      AND {col} NOT LIKE '/workspace{pct}'\n"
            "      AND {col} <> '/workspace'",
            1,
        )

    # --- 5) Live page HTML: offline section + human totals note + use offline from API ---
    old_js_live = "function renderLive(d){"
    if "renderOffline" not in text:
        # inject after renderLive function start - add offline renderer before renderLive
        inject_js = r'''
  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var rows=d.offline||[];
    if(!rows.length){ box.innerHTML="<p class='note'>No completed sessions in the last 24h outside the live window.</p>"; return; }
    var html="<table><thead><tr><th>Who</th><th>Pages</th><th>When done</th></tr></thead><tbody>";
    rows.forEach(function(r){
      var badge=r.kind==="bot"?"bot":"anon";
      var badgeLabel=r.kind==="bot"?"bot":"guest";
      var who=esc(r.who||(r.ip?("Guest "+r.ip):"Guest"));
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      var n=r.pages_count!=null?r.pages_count:((r.page_trail||[]).length);
      var key="off:"+(r.ip||r.visitor_id||who);
      var isOpen=!!LIVE_TRAIL_OPEN[key];
      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      var arrow=trail.length
        ? ("<button type='button' class='live-exp' data-trail='"+esc(key)+"' aria-expanded='"+(isOpen?"true":"false")+"'>"+(isOpen?"▼":"▶")+"</button> ")
        : "";
      html+="<tr class='live-main' data-trail='"+esc(key)+"'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+" · done</td><td>"+n+"</td><td>"+esc(when)+"</td></tr>";
      if(trail.length){
        var metaBits=[];
        if(r.ip) metaBits.push("IP "+esc(r.ip));
        if(r.device_type) metaBits.push(esc(r.device_type));
        if(r.browser) metaBits.push(esc(r.browser));
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
    box.innerHTML=html;
  }
  function renderLive(d){
'''
        if old_js_live not in text:
            raise SystemExit("renderLive not found")
        text = text.replace(old_js_live, inject_js, 1)

    # After renderLive(d) call, also renderOffline
    if "renderOffline(d)" not in text:
        text = text.replace(
            "renderLive(j);",
            "renderLive(j); try{renderOffline(j);}catch(eOff){}",
            1,
        )

    # Add offline box HTML near liveBox
    if 'id="offlineBox"' not in text:
        live_box_markers = [
            '<div id="liveBox"></div>',
            "<div id='liveBox'></div>",
        ]
        replaced = False
        for m in live_box_markers:
            if m in text:
                text = text.replace(
                    m,
                    m
                    + '\n<section class="card" style="margin-top:12px"><h2>Done / offline — last 24h</h2>'
                    + '<p class="note">Outside the live window. ▶ show/hide URL trail to audit. Bots included for review; staff/agent hidden.</p>'
                    + '<div id="offlineBox"><p class="note">Loading…</p></div></section>',
                    1,
                )
                replaced = True
                break
        if not replaced:
            print("WARN: liveBox not found for offline section")

    # Overview note: prefer human_live from live poll for display - also fix overview count to exclude cloud bots by quarantining on classify
    # Patch overview to compute visitors/hits excluding quarantined (already) — after soft bot we quarantine on live poll

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK traffic audit (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
