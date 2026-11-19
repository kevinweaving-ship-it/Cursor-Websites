#!/usr/bin/env python3
"""Live now: arrow on name expands full URL trail + dwell for that session."""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER = r'''
def _lean_fmt_dwell_seconds(dwell) -> str:
    if dwell is None:
        return "…"
    try:
        n = int(dwell)
    except Exception:
        return "—"
    if n < 0:
        n = 0
    if n < 60:
        return f"{n}s"
    m, s = divmod(n, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def _lean_session_page_trail(cur, *, visitor_id: str = "", ip: str = "", session_id: str = "") -> list:
    """Chronological URL stays for one live session (path + dwell)."""
    trail = []
    vid = (visitor_id or "").strip()
    ip_s = (ip or "").strip()
    sid = (session_id or "").strip()
    try:
        if not table_exists("public_page_hits"):
            return []
        rows = []
        if vid:
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (vid,),
            )
            rows = list(cur.fetchall() or [])
        if not rows and sid:
            sess_vid = f"sess:{sid[:32]}"
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (sess_vid,),
            )
            rows = list(cur.fetchall() or [])
        if not rows and ip_s and table_exists("session_page_hits") and sid:
            try:
                cur.execute(
                    """
                    SELECT path, occurred_at, NULL::timestamptz AS left_at, NULL::int AS dwell_seconds
                    FROM public.session_page_hits
                    WHERE session_id = %s
                      AND occurred_at > NOW() - INTERVAL '45 minutes'
                    ORDER BY occurred_at ASC
                    LIMIT 60
                    """,
                    (sid,),
                )
                rows = list(cur.fetchall() or [])
            except Exception:
                rows = []
        # Dedupe consecutive same path (legacy spam rows)
        for r in rows:
            if isinstance(r, dict):
                path = (r.get("path") or "/").strip() or "/"
                occ = r.get("occurred_at")
                left = r.get("left_at")
                dwell = r.get("dwell_seconds")
            else:
                path = (r[0] or "/").strip() or "/"
                occ, left, dwell = r[1], r[2], r[3]
            path = path.split("?", 1)[0] or "/"
            open_hit = left is None
            if dwell is None and open_hit and occ is not None:
                try:
                    cur.execute(
                        "SELECT GREATEST(0, EXTRACT(EPOCH FROM (NOW() - %s::timestamptz))::int)",
                        (occ,),
                    )
                    dr = cur.fetchone()
                    if dr:
                        dwell = dr[0] if not isinstance(dr, dict) else next(iter(dr.values()))
                except Exception:
                    dwell = None
            elif dwell is None and left is not None and occ is not None:
                try:
                    cur.execute(
                        "SELECT GREATEST(0, EXTRACT(EPOCH FROM (%s::timestamptz - %s::timestamptz))::int)",
                        (left, occ),
                    )
                    dr = cur.fetchone()
                    if dr:
                        dwell = dr[0] if not isinstance(dr, dict) else next(iter(dr.values()))
                except Exception:
                    dwell = None
            item = {
                "path": path,
                "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                "dwell_seconds": int(dwell) if dwell is not None else None,
                "dwell_label": _lean_fmt_dwell_seconds(dwell) + (" (open)" if open_hit else ""),
                "open": bool(open_hit),
            }
            if trail and trail[-1]["path"] == path and trail[-1].get("open") and open_hit:
                trail[-1] = item
                continue
            if trail and trail[-1]["path"] == path and not trail[-1].get("open") and not open_hit:
                # keep first stay of consecutive closed dupes
                continue
            trail.append(item)
    except Exception:
        return trail
    return trail

'''

# Insert helper before lean_traffic_api_live if missing
if "_lean_session_page_trail" not in text:
    mark = '@app.get("/traffic/api/live")\ndef lean_traffic_api_live(request: Request):'
    if mark not in text:
        raise SystemExit("lean_traffic_api_live marker missing")
    text = text.replace(mark, HELPER + "\n" + mark, 1)

# --- Enrich signed-in SELECT to include session_id + ip ---
old_signed = '''                SELECT DISTINCT ON (COALESCE(NULLIF(us.sas_id::text,''), us.session_id::text))
                    'signed' AS kind,
                    COALESCE(
                        NULLIF(TRIM(ua.full_name), ''),
                        NULLIF(TRIM(CONCAT(COALESCE(ua.first_name,''), ' ', COALESCE(ua.last_name,''))), ''),
                        NULLIF(us.sas_id::text, ''),
                        'Signed-in'
                    ) AS who,
                    us.sas_id::text AS sas_id,
                    COALESCE(us.last_path, '—') AS path,
                    us.last_activity,
                    COALESCE(us.user_agent, '') AS device
                FROM public.user_sessions us
                LEFT JOIN public.user_accounts ua ON ua.account_id = us.account_id
                WHERE us.last_activity > NOW() - make_interval(mins => %s)
                  AND COALESCE(us.is_active, true) = true
                  AND (us.sas_id IS NULL OR us.sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """)
                ORDER BY COALESCE(NULLIF(us.sas_id::text,''), us.session_id::text), us.last_activity DESC
                LIMIT 40
                """,
                (_LEAN_TRAFFIC_LIVE_MINUTES,),
            )
            for r in cur.fetchall() or []:
                d = r if isinstance(r, dict) else {
                    "who": r[1], "sas_id": r[2], "path": r[3], "last_activity": r[4], "device": r[5]
                }
                la = d.get("last_activity")
                path = d.get("path") or "—"
                rows.append({
                    "kind": "signed",
                    "who": d.get("who") or "Signed-in",
                    "who_href": "",
                    "guessed": False,
                    "likely_hits": 0,
                    "sas_id": d.get("sas_id") or "",
                    "ip": "",
                    "path": path,
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "device": (d.get("device") or "")[:80],
                    "href": path if str(path).startswith("/") else "",
                })'''

new_signed = '''                SELECT DISTINCT ON (COALESCE(NULLIF(us.sas_id::text,''), us.session_id::text))
                    'signed' AS kind,
                    COALESCE(
                        NULLIF(TRIM(ua.full_name), ''),
                        NULLIF(TRIM(CONCAT(COALESCE(ua.first_name,''), ' ', COALESCE(ua.last_name,''))), ''),
                        NULLIF(us.sas_id::text, ''),
                        'Signed-in'
                    ) AS who,
                    us.sas_id::text AS sas_id,
                    COALESCE(us.last_path, '—') AS path,
                    us.last_activity,
                    COALESCE(us.user_agent, '') AS device,
                    us.session_id::text AS session_id,
                    COALESCE(us.ip_address, '') AS ip_address
                FROM public.user_sessions us
                LEFT JOIN public.user_accounts ua ON ua.account_id = us.account_id
                WHERE us.last_activity > NOW() - make_interval(mins => %s)
                  AND COALESCE(us.is_active, true) = true
                  AND (us.sas_id IS NULL OR us.sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """)
                ORDER BY COALESCE(NULLIF(us.sas_id::text,''), us.session_id::text), us.last_activity DESC
                LIMIT 40
                """,
                (_LEAN_TRAFFIC_LIVE_MINUTES,),
            )
            for r in cur.fetchall() or []:
                d = r if isinstance(r, dict) else {
                    "who": r[1], "sas_id": r[2], "path": r[3], "last_activity": r[4],
                    "device": r[5], "session_id": r[6], "ip_address": r[7],
                }
                la = d.get("last_activity")
                path = d.get("path") or "—"
                sid = (d.get("session_id") or "").strip()
                ip = (d.get("ip_address") or "").strip()
                sess_vid = f"sess:{sid[:32]}" if sid else ""
                trail = _lean_session_page_trail(cur, visitor_id=sess_vid, ip=ip, session_id=sid)
                rows.append({
                    "kind": "signed",
                    "who": d.get("who") or "Signed-in",
                    "who_href": "",
                    "guessed": False,
                    "likely_hits": 0,
                    "sas_id": d.get("sas_id") or "",
                    "ip": ip,
                    "visitor_id": sess_vid,
                    "session_id": sid,
                    "path": path,
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "device": (d.get("device") or "")[:80],
                    "device_type": "",
                    "browser": "",
                    "href": path if str(path).startswith("/") else "",
                    "page_trail": trail,
                    "pages_count": len(trail),
                })'''

if old_signed not in text:
    if '"page_trail": trail' in text and "lean_traffic_api_live" in text:
        print("signed enrich may already be present")
    else:
        raise SystemExit("signed live block not found")
else:
    text = text.replace(old_signed, new_signed, 1)

# --- Enrich public session SELECT + row dict ---
old_pub_sel = '''                SELECT visitor_id,
                       COALESCE(last_path, '—') AS path,
                       last_activity,
                       COALESCE(user_agent, '') AS device,
                       COALESCE(ip_address, '') AS ip_address
                FROM public.public_sessions'''

new_pub_sel = '''                SELECT visitor_id,
                       COALESCE(last_path, '—') AS path,
                       last_activity,
                       COALESCE(user_agent, '') AS device,
                       COALESCE(ip_address, '') AS ip_address,
                       COALESCE(device_type, '') AS device_type,
                       COALESCE(browser, '') AS browser
                FROM public.public_sessions'''

if old_pub_sel in text:
    text = text.replace(old_pub_sel, new_pub_sel, 1)
elif "AS device_type" in text[text.find("def lean_traffic_api_live"): text.find("def lean_traffic_api_live") + 8000]:
    print("public select already has device_type")
else:
    # columns may not exist yet — use safe select without device cols and fill empty
    print("WARN: using fallback without device_type columns in SELECT")

old_pub_row = '''                d = r if isinstance(r, dict) else {
                    "visitor_id": r[0], "path": r[1], "last_activity": r[2],
                    "device": r[3], "ip_address": r[4],
                }
                la = d.get("last_activity")
                path = d.get("path") or "—"
                ip = (d.get("ip_address") or "").strip()
                vid = (d.get("visitor_id") or "")[:10]
                is_bot = False'''

new_pub_row = '''                d = r if isinstance(r, dict) else {
                    "visitor_id": r[0], "path": r[1], "last_activity": r[2],
                    "device": r[3], "ip_address": r[4],
                    "device_type": (r[5] if len(r) > 5 else ""),
                    "browser": (r[6] if len(r) > 6 else ""),
                }
                la = d.get("last_activity")
                path = d.get("path") or "—"
                ip = (d.get("ip_address") or "").strip()
                full_vid = (d.get("visitor_id") or "").strip()
                vid = full_vid[:10]
                is_bot = False'''

if old_pub_row not in text:
    raise SystemExit("public row parse block not found")
text = text.replace(old_pub_row, new_pub_row, 1)

old_append = '''                rows.append({
                    "kind": "bot" if is_bot else "anon",
                    "who": who,
                    "who_href": who_href,
                    "guessed": bool(likely_name) and not is_bot,
                    "likely_hits": int(likely.get("hits") or 0) if not is_bot else 0,
                    "sas_id": (likely.get("sas_id") or "") if not is_bot else "",
                    "ip": ip,
                    "path": path,
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "device": (d.get("device") or "")[:80],
                    "href": path if str(path).startswith("/") else "",
                })
        try:
            conn.commit()
        except Exception:
            pass
        rows.sort(key=lambda x: x.get("last_activity") or "", reverse=True)
        return JSONResponse(
            {"ok": True, "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES, "rows": rows[:50]},'''

new_append = '''                trail = []
                try:
                    trail = _lean_session_page_trail(cur, visitor_id=full_vid, ip=ip)
                except Exception:
                    trail = []
                rows.append({
                    "kind": "bot" if is_bot else "anon",
                    "who": who,
                    "who_href": who_href,
                    "guessed": bool(likely_name) and not is_bot,
                    "likely_hits": int(likely.get("hits") or 0) if not is_bot else 0,
                    "sas_id": (likely.get("sas_id") or "") if not is_bot else "",
                    "ip": ip,
                    "visitor_id": full_vid,
                    "path": path,
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "device": (d.get("device") or "")[:80],
                    "device_type": (d.get("device_type") or "")[:20],
                    "browser": (d.get("browser") or "")[:40],
                    "href": path if str(path).startswith("/") else "",
                    "page_trail": trail,
                    "pages_count": len(trail),
                })
        try:
            conn.commit()
        except Exception:
            pass
        rows.sort(key=lambda x: x.get("last_activity") or "", reverse=True)
        return JSONResponse(
            {"ok": True, "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES, "rows": rows[:50]},'''

if old_append not in text:
    raise SystemExit("anon append block not found")
text = text.replace(old_append, new_append, 1)

# --- CSS for expand button ---
old_css = ".badge.bot{background:#fee2e2;color:#991b1b}"
new_css = """.badge.bot{background:#fee2e2;color:#991b1b}
.live-exp{border:0;background:transparent;color:var(--navy);font-size:12px;font-weight:900;cursor:pointer;min-width:28px;min-height:28px;padding:0 4px;line-height:1;vertical-align:middle}
.live-exp[aria-expanded="true"]{color:var(--teal)}
.live-trail td{background:#f8fafc;padding:8px 6px}
.live-trail .trail-meta{font-size:11px;color:var(--muted);margin:0 0 6px;font-weight:600}
.live-trail table.trail{min-width:0;font-size:11px;margin:0}
.live-trail table.trail th{background:#eef2f7}
.live-trail table.trail td.dwell{white-space:nowrap;font-variant-numeric:tabular-nums}"""
if old_css not in text:
    raise SystemExit("badge.bot css missing")
if ".live-exp{" not in text:
    text = text.replace(old_css, new_css, 1)

# --- replace renderLive ---
old_rl = '''  function renderLive(d){
    var rows=d.rows||[];
    if(!rows.length){$("liveBox").innerHTML="<p class='note'>Nobody active in the last "+(d.live_minutes||15)+" minutes.</p>"; return;}
    var html="<table><thead><tr><th>Who</th><th>Page</th><th>When</th></tr></thead><tbody>";
    rows.slice(0,30).forEach(function(r){
      var badge=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"anon"));
      var badgeLabel=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"guest"));
      var path=r.path||"—";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(path)+"</a>"):esc(path);
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      var who=esc(r.who||"");
      if(r.who_href){ who="<a href='"+esc(r.who_href)+"' title='Guessed from IP sailor page visits'>"+who+"</a>"; }
      var meta="";
      if(r.sas_id) meta+=" · "+esc(r.sas_id);
      if(r.guessed && r.likely_hits) meta+=" · "+r.likely_hits+" sailor hits";
      html+="<tr><td><span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+meta+"</td><td>"+link+"</td><td>"+esc(when)+"</td></tr>";
    });
    html+="</tbody></table>";
    $("liveBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
  }'''

# In the file the backslash escaping for \"table-scroll\" may differ - read exact
idx = text.find("  function renderLive(d){")
if idx < 0:
    raise SystemExit("renderLive not found")
idx2 = text.find("  function mediaSrc(u){", idx)
if idx2 < 0:
    raise SystemExit("mediaSrc after renderLive not found")
old_block = text[idx:idx2]
new_block = r'''  function renderLive(d){
    var rows=d.rows||[];
    if(!rows.length){$("liveBox").innerHTML="<p class='note'>Nobody active in the last "+(d.live_minutes||15)+" minutes.</p>"; return;}
    var html="<table><thead><tr><th>Who</th><th>Page</th><th>When</th></tr></thead><tbody>";
    rows.slice(0,30).forEach(function(r, idx){
      var badge=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"anon"));
      var badgeLabel=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"guest"));
      var path=r.path||"—";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(path)+"</a>"):esc(path);
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      var who=esc(r.who||"");
      if(r.who_href){ who="<a href='"+esc(r.who_href)+"' title='Guessed from IP sailor page visits'>"+who+"</a>"; }
      var meta="";
      if(r.sas_id) meta+=" · "+esc(r.sas_id);
      if(r.guessed && r.likely_hits) meta+=" · "+r.likely_hits+" sailor hits";
      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      var nPages=r.pages_count!=null?r.pages_count:trail.length;
      if(nPages>1) meta+=" · "+nPages+" pages";
      var key="live"+idx;
      var arrow=trail.length
        ? ("<button type='button' class='live-exp' data-trail='"+key+"' aria-expanded='false' aria-label='Show session pages'>▶</button> ")
        : "";
      html+="<tr class='live-main'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+meta+"</td><td>"+link+"</td><td>"+esc(when)+"</td></tr>";
      if(trail.length){
        var metaBits=[];
        if(r.ip) metaBits.push("IP "+esc(r.ip));
        if(r.device_type) metaBits.push(esc(r.device_type));
        if(r.browser) metaBits.push(esc(r.browser));
        if(r.kind==="signed" && r.sas_id) metaBits.push("sas "+esc(r.sas_id));
        var thtml="<div class='trail-meta'>"+(metaBits.join(" · ")||"Session pages")+"</div>";
        thtml+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
        trail.forEach(function(pt){
          var p=pt.path||"/";
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(p)+"</a>"):esc(p);
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";
        });
        thtml+="</tbody></table>";
        html+="<tr class='live-trail' data-trail='"+key+"' hidden><td colspan='3'>"+thtml+"</td></tr>";
      }
    });
    html+="</tbody></table>";
    $("liveBox").innerHTML="<div class=\"table-scroll\">"+html+"</div>";
    $("liveBox").querySelectorAll(".live-exp").forEach(function(btn){
      btn.addEventListener("click", function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        var k=btn.getAttribute("data-trail");
        var row=$("liveBox").querySelector("tr.live-trail[data-trail='"+k+"']");
        if(!row) return;
        var open=row.hasAttribute("hidden");
        if(open){ row.removeAttribute("hidden"); btn.setAttribute("aria-expanded","true"); btn.textContent="▼"; }
        else { row.setAttribute("hidden",""); btn.setAttribute("aria-expanded","false"); btn.textContent="▶"; }
      });
    });
  }
'''
text = text[:idx] + new_block + text[idx2:]

# Note under live table
old_note = 'Last 15 min. Guests guessed from IP + sailor pages they opened (same as Admin Public).'
new_note = 'Last 15 min. ▶ next to a name shows/hides every URL in that session with dwell time. Guests guessed from IP + sailor pages.'
if old_note in text:
    text = text.replace(old_note, new_note, 1)

if text == orig:
    raise SystemExit("no changes applied")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK patched {API} (+{len(text)-len(orig)} bytes)")
