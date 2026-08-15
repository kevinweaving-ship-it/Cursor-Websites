#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import re, sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

RESET_ISO = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%dT%H:%M:%S+02:00")
Path("/var/tmp/sailingsa_traffic_real_since").write_text(RESET_ISO + "\n", encoding="utf-8")
print("RESET", RESET_ISO)

def must_replace(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f"FAIL {label}")
    text = text.replace(old, new, 1)
    print("OK", label)

# 1) reset helper
if "_lean_traffic_real_since" not in text:
    must_replace(
        "_LEAN_ENGAGE_GRACE_SECONDS = 12",
        "_LEAN_ENGAGE_GRACE_SECONDS = 12\n"
        f'_LEAN_TRAFFIC_REAL_SINCE_DEFAULT = "{RESET_ISO}"\n\n'
        "def _lean_traffic_real_since():\n"
        '    """ISO timestamptz — real visitor list starts here (reset)."""\n'
        "    try:\n"
        '        raw = open("/var/tmp/sailingsa_traffic_real_since", encoding="utf-8").read().strip()\n'
        "        if raw:\n"
        "            return raw\n"
        "    except Exception:\n"
        "        pass\n"
        "    return _LEAN_TRAFFIC_REAL_SINCE_DEFAULT\n",
        "reset helper",
    )
else:
    text, n = re.subn(r'_LEAN_TRAFFIC_REAL_SINCE_DEFAULT = "[^"]+"', f'_LEAN_TRAFFIC_REAL_SINCE_DEFAULT = "{RESET_ISO}"', text, count=1)
    print("OK reset update", n)

# 2) staff show
must_replace(
    "            # Staff (Tim/Kevin signed-in IPs) never appear as Done/offline visitors\n"
    "            if is_staff and not is_bot:\n"
    "                continue\n"
    "            if is_bot:\n"
    '                kind = "bot"\n'
    '                who = f"Bot {ip}"\n'
    "            else:\n"
    '                kind = "anon"\n'
    '                who = f"Guest {ip}"\n',
    "            # All real visitors (staff included when scrolled/clicked)\n"
    "            if is_bot:\n"
    '                kind = "bot"\n'
    '                who = f"Bot {ip}"\n'
    "            elif is_staff:\n"
    '                kind = "signed"\n'
    '                who = f"Staff {ip}"\n'
    "            else:\n"
    '                kind = "anon"\n'
    '                who = f"Guest {ip}"\n',
    "staff visible",
)

# 3) group sql
must_replace(
    "              AND h.occurred_at > NOW() - make_interval(hours => %s)\n"
    "              AND h.ip_address <> '102.218.215.253'\n"
    "            GROUP BY h.ip_address\n"
    "            ORDER BY MAX(h.occurred_at) DESC\n"
    "            LIMIT 100\n"
    '            """,\n'
    "            (look_h,),\n",
    "              AND h.occurred_at > NOW() - make_interval(hours => %s)\n"
    "              AND h.occurred_at >= %s::timestamptz\n"
    "              AND h.ip_address <> '102.218.215.253'\n"
    "            GROUP BY h.ip_address\n"
    "            ORDER BY MAX(h.occurred_at) DESC\n"
    "            LIMIT 250\n"
    '            """,\n'
    "            (look_h, _lean_traffic_real_since()),\n",
    "group sql",
)

# 4) trail sql
must_replace(
    "            WHERE ip_address = %s\n"
    "              AND occurred_at > NOW() - make_interval(hours => %s)\n"
    "            ORDER BY occurred_at ASC, hit_id ASC\n"
    "            LIMIT 200\n"
    '            """,\n'
    "            (ip, int(lookback_hours)),\n",
    "            WHERE ip_address = %s\n"
    "              AND occurred_at > NOW() - make_interval(hours => %s)\n"
    "              AND occurred_at >= %s::timestamptz\n"
    "            ORDER BY occurred_at ASC, hit_id ASC\n"
    "            LIMIT 500\n"
    '            """,\n'
    "            (ip, int(lookback_hours), _lean_traffic_real_since()),\n",
    "trail sql",
)

# 5) FB builder + json
marker = "        # Human-only live stats for the card strip"
if "Facebook share crawls — confirmation only" not in text:
    fb = '''        # Facebook share crawls — confirmation only (URL we posted got scraped). Not real visitors.
        offline_fb = []
        try:
            since = _lean_traffic_real_since()
            cur.execute(
                """
                SELECT h.ip_address, h.path, h.occurred_at
                FROM public.public_page_hits h
                WHERE h.occurred_at >= %s::timestamptz
                  AND h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
                ORDER BY h.occurred_at DESC
                LIMIT 80
                """,
                (since,),
            )
            for hr in cur.fetchall() or []:
                if isinstance(hr, dict):
                    ip = (hr.get("ip_address") or "").strip()
                    path = hr.get("path") or "/"
                    occ = hr.get("occurred_at")
                else:
                    ip = (hr[0] or "").strip()
                    path = hr[1] or "/"
                    occ = hr[2]
                try:
                    if not _lean_is_facebook_crawler_ip(ip):
                        continue
                except Exception:
                    continue
                offline_fb.append(
                    {
                        "kind": "fb_preview",
                        "who": f"Facebook {ip}",
                        "ip": ip,
                        "path": path,
                        "href": path if str(path).startswith("/") else "",
                        "last_activity": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                        "pages_count": 1,
                        "page_trail": [{"path": path, "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or "")}],
                    }
                )
                if len(offline_fb) >= 40:
                    break
        except Exception:
            offline_fb = []

'''
    must_replace(marker, fb + marker, "fb builder")

must_replace(
    '"offline": offline[:40],\n                "offline_bots": offline_bots[:40],',
    '"offline": offline[:200],\n                "real_since": _lean_traffic_real_since(),\n'
    '                "offline_fb": offline_fb[:40],\n                "offline_bots": offline_bots[:40],',
    "json",
)

# 6) HTML sections
must_replace(
    '<section class="card" style="margin-top:12px"><h2>Done / offline — last 24h</h2>'
    '<p class="note">Real visits only. ▶ show/hide URL trail. Session total = first page → last action.</p>'
    '<div id="offlineBox"><p class="note">Loading…</p></div></section>'
    '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
    '<button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> '
    'Bots done / quarantined <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2>'
    '<p class="note">Hidden by default. Show to audit scrapers (URL trails). Not counted as real visits.</p>'
    '<div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>',
    '<section class="card" style="margin-top:12px"><h2>Real visitors — since reset</h2>'
    '<p class="note" id="realSinceNote">Every real visitor (scroll/click). All pages in the trail. Nothing hidden if real.</p>'
    '<div id="offlineBox"><p class="note">Loading…</p></div></section>'
    '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
    '<button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> '
    'Facebook share crawls <span id="offlineFbCount" class="note" style="font-weight:600"></span></h2>'
    '<p class="note">Confirmation when you post a link — Meta fetched that URL. Not real visitors.</p>'
    '<div id="offlineFbBox" hidden><p class="note">Loading…</p></div></section>'
    '<section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
    '<button type="button" id="offlineBotsToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> '
    'Other bots <span id="offlineBotsCount" class="note" style="font-weight:600"></span></h2>'
    '<p class="note">Hidden by default. Scrapers / probes — ignore.</p>'
    '<div id="offlineBotsBox" hidden><p class="note">Loading…</p></div></section>',
    "html",
)

# 7) renderOfflineBots — exclude FB from other bots; add renderOfflineFb
old_bots_fn = '''function renderOfflineBots(d){
    var box=$("offlineBotsBox");
    var cnt=$("offlineBotsCount");
    var rows=(d.offline_bots||[]).filter(function(r){ return r && r.kind==="bot"; });
    if(cnt) cnt.textContent=rows.length?("· "+rows.length):"";
    if(!box) return;
    if(!rows.length){ box.innerHTML="<p class='note'>No quarantined bots in the last 24h.</p>"; return; }
    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
  }'''

new_bots_fn = '''function isFbCrawlIp(ip){
    ip=String(ip||"");
    return ip.indexOf("173.252.")===0||ip.indexOf("69.63.")===0||ip.indexOf("69.171.")===0||ip.indexOf("31.13.")===0||ip.indexOf("66.220.")===0||ip.indexOf("157.240.")===0||ip.indexOf("185.60.")===0;
  }
  function renderOfflineFb(d){
    var box=$("offlineFbBox");
    var cnt=$("offlineFbCount");
    var rows=d.offline_fb||[];
    if(cnt) cnt.textContent=rows.length?("· "+rows.length):"";
    if(!box) return;
    if(!rows.length){ box.innerHTML="<p class='note'>No Facebook share crawls since reset.</p>"; return; }
    box.innerHTML=renderOfflineRows(rows, "offfb");
    bindTrailToggleButtons(box);
  }
  function renderOfflineBots(d){
    var box=$("offlineBotsBox");
    var cnt=$("offlineBotsCount");
    var rows=(d.offline_bots||[]).filter(function(r){ return r && r.kind==="bot" && !isFbCrawlIp(r.ip); });
    if(cnt) cnt.textContent=rows.length?("· "+rows.length):"";
    if(!box) return;
    if(!rows.length){ box.innerHTML="<p class='note'>No other bots in lookback.</p>"; return; }
    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
  }'''

must_replace(old_bots_fn, new_bots_fn, "bots+fb render")

# 8) renderOffline messages + call renderOfflineFb
old_off = '''function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */
    if(!rows.length){
      box.innerHTML="<p class='note'>No completed real visits in the last 24h outside the live window.</p>";
    } else {
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+" — tap ▶ to show/hide URLs</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
    try{renderOfflineBots(d);}catch(eB){}
  }'''

new_off = '''function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var note=$("realSinceNote");
    if(note && d.real_since){
      note.textContent="Since reset "+String(d.real_since).replace("T"," ").slice(0,19)+" — every real visitor (scroll/click). All pages in trail (sailors, clubs, events, boats…). Nothing hidden if real.";
    }
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */
    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
    } else {
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pages+" page"+(pages===1?"":"s")+" — tap ▶ for full trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
    try{renderOfflineFb(d);}catch(eF){}
    try{renderOfflineBots(d);}catch(eB){}
  }'''

must_replace(old_off, new_off, "renderOffline")

# 9) FB toggle wire
old_wire = '''(function wireOfflineBotsToggle(){
    var btn=$("offlineBotsToggle"), box=$("offlineBotsBox");
    if(!btn||!box||btn._wired) return;
    btn._wired=true;
    btn.addEventListener("click", function(){
      OFFLINE_BOTS_OPEN=!OFFLINE_BOTS_OPEN;
      box.hidden=!OFFLINE_BOTS_OPEN;
      btn.textContent=OFFLINE_BOTS_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false");
    });
  })();'''

new_wire = '''var OFFLINE_FB_OPEN=false;
  (function wireOfflineFbToggle(){
    var btn=$("offlineFbToggle"), box=$("offlineFbBox");
    if(!btn||!box||btn._wired) return;
    btn._wired=true;
    btn.addEventListener("click", function(){
      OFFLINE_FB_OPEN=!OFFLINE_FB_OPEN;
      box.hidden=!OFFLINE_FB_OPEN;
      btn.textContent=OFFLINE_FB_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_FB_OPEN?"true":"false");
    });
  })();
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
  })();'''

must_replace(old_wire, new_wire, "fb toggle")

if text == orig:
    sys.exit("NO CHANGE")

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
