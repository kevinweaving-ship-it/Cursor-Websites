#!/usr/bin/env python3
"""Surgical live api.py edits for Google crawl allow + traffic card.

Never overwrite the whole file. Each old string must match exactly once.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

REPLACEMENTS: list[tuple[str, str]] = []

REPLACEMENTS.append(
    (
        '''def _lean_is_google_crawler_ip(ip: str) -> bool:
    """Googlebot / Google crawler egress prefixes (common published ranges)."""
    ip = (ip or "").strip()
    if not ip:
        return False
    return any(
        ip.startswith(p)
        for p in (
            "66.249.",
            "64.233.",
            "72.14.",
            "74.125.",
            "209.85.",
            "216.239.",
            "142.250.",
            "172.217.",
            "172.253.",
            "108.177.",
            "35.247.",  # sometimes Google cloud crawlers
        )
    )''',
        '''_LEAN_GOOGLE_CRAWLER_NETS = None
_LEAN_GOOGLE_CIDR_PATHS = (
    "/etc/nginx/conf.d/googlebot-cidrs.inc",
    "/var/www/sailingsa/deploy/nginx-googlebot-cidrs.inc",
)


def _lean_google_crawler_nets():
    """Official Googlebot + special-crawlers CIDRs (same file nginx geo uses)."""
    global _LEAN_GOOGLE_CRAWLER_NETS
    if _LEAN_GOOGLE_CRAWLER_NETS is not None:
        return _LEAN_GOOGLE_CRAWLER_NETS
    import ipaddress
    from pathlib import Path as _P
    nets = []
    for path in _LEAN_GOOGLE_CIDR_PATHS:
        p = _P(path)
        if not p.is_file():
            continue
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].strip().rstrip(";")
            if not line:
                continue
            cidr = line.split()[0]
            try:
                nets.append(ipaddress.ip_network(cidr, strict=False))
            except Exception:
                continue
        if nets:
            break
    _LEAN_GOOGLE_CRAWLER_NETS = tuple(nets)
    return _LEAN_GOOGLE_CRAWLER_NETS


def _lean_is_google_crawler_ip(ip: str) -> bool:
    """Official Googlebot / special-crawler CIDRs; prefix fallback if file missing."""
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        import ipaddress
        addr = ipaddress.ip_address(ip.split("%", 1)[0])
        nets = _lean_google_crawler_nets()
        if nets:
            return any(addr in net for net in nets)
    except Exception:
        pass
    return any(
        ip.startswith(p)
        for p in (
            "66.249.",
            "64.233.",
            "72.14.",
            "74.125.",
            "209.85.",
            "216.239.",
            "142.250.",
            "172.217.",
            "172.253.",
            "108.177.",
        )
    )''',
    )
)

REPLACEMENTS.append(
    (
        '''        for x in (
            "googlebot",
            "google-inspectiontool",
            "storebot-google",
            "adsbot-google",
            "apis-google",
            "mediapartners-google",
            "feedfetcher-google",
        )''',
        '''        for x in (
            "googlebot",
            "google-inspectiontool",
            "storebot-google",
            "adsbot-google",
            "apis-google",
            "mediapartners-google",
            "feedfetcher-google",
            "googleother",
        )''',
    )
)

REPLACEMENTS.append(
    (
        '''def _lean_human_traffic_pass(user_agent: str, path: Optional[str] = None) -> bool:
    """Valid clickable page + real browser UA => treat as real traffic (not bot).

    Landing `/` counts — visitors must get a chance to click through from home.
    """
    if not _is_human_browser_ua(user_agent):
        return False''',
        '''def _lean_human_traffic_pass(user_agent: str, path: Optional[str] = None) -> bool:
    """Valid clickable page + real browser UA => treat as real traffic (not bot).

    Landing `/` counts — visitors must get a chance to click through from home.
    """
    if _lean_is_google_crawler_ua(user_agent):
        return False
    if not _is_human_browser_ua(user_agent):
        return False''',
    )
)

REPLACEMENTS.append(
    (
        '''    ua = (request.headers.get("user-agent") or "")[:500]
    ip = _get_client_ip(request)
    is_bot = _site_traffic.is_bot_user_agent(ua)''',
        '''    ua = (request.headers.get("user-agent") or "")[:500]
    ip = _get_client_ip(request)
    is_bot = _site_traffic.is_bot_user_agent(ua)
    try:
        if (not is_bot) and (
            _lean_is_google_crawler_ua(ua) or _lean_is_google_crawler_ip(ip or "")
        ):
            is_bot = True
    except Exception:
        pass''',
    )
)

REPLACEMENTS.append(
    (
        '''        "User-agent: *\\n"
        "Allow: /\\n"
        "Disallow: /api/\\n"
        "Disallow: /auth/\\n"
        "Disallow: /admin/\\n"
        "Disallow: /login\\n"
        "Disallow: /test/\\n"
        f"Sitemap: {base}/sitemap.xml\\n"''',
        '''        "User-agent: *\\n"
        "Allow: /\\n"
        "Allow: /api/og/\\n"
        "Allow: /api/club-logo/\\n"
        "Disallow: /api/\\n"
        "Disallow: /auth/\\n"
        "Disallow: /admin/\\n"
        "Disallow: /login\\n"
        "Disallow: /test/\\n"
        "Disallow: /dev-1\\n"
        "Disallow: /dev-1/\\n"
        "Disallow: /signup.html\\n"
        "Disallow: /profiles\\n"
        f"Sitemap: {base}/sitemap.xml\\n"
        "Disallow: /sailing-roundup/archive.json\\n"
        "Disallow: /sailing-roundup/feed.json\\n"
        "Disallow: /sailing-roundup/cards.json\\n"
        "Disallow: /sailing-roundup/latest.json\\n"
        f"Sitemap: {base}/sitemap-roundups.xml\\n"
        f"Sitemap: {base}/sitemap-news.xml\\n"''',
    )
)

REPLACEMENTS.append(
    (
        '''    return 24


def _lean_quarantine_age_seconds(cur, ip_address: Optional[str]) -> Optional[float]:''',
        '''    return 24


_LEAN_GOOGLE_CRAWL_CACHE = {"at": 0.0, "hits": None}


def _lean_parse_nginx_combined(line: str):
    try:
        ip = line.split(" ", 1)[0]
        lb = line.find("[")
        rb = line.find("]", lb)
        ts = line[lb + 1 : rb]
        rest = line[rb + 2 :]
        q1 = rest.find('"')
        q2 = rest.find('"', q1 + 1)
        req = rest[q1 + 1 : q2]
        after = rest[q2 + 2 :].lstrip()
        status = after.split(" ", 1)[0]
        uq = rest.rfind('"')
        uq0 = rest.rfind('"', 0, uq)
        ua = rest[uq0 + 1 : uq]
        parts = req.split(" ", 2)
        meth = parts[0] if parts else ""
        path = parts[1].split("?", 1)[0] if len(parts) > 1 else "/"
        return ip, ts, meth, path, status, ua
    except Exception:
        return None


def _lean_scan_google_crawls():
    """Verified Google crawler hits from current + previous nginx access logs."""
    import datetime as _dt
    import re as _re
    import time as _time

    now = _time.time()
    ent = _LEAN_GOOGLE_CRAWL_CACHE
    if ent.get("hits") is not None and (now - float(ent.get("at") or 0)) < 60:
        return ent["hits"]
    ua_re = _re.compile(
        r"Googlebot|Google-InspectionTool|AdsBot-Google|Storebot-Google|GoogleOther",
        _re.I,
    )
    hits = []
    for fn in ("/var/log/nginx/access.log", "/var/log/nginx/access.log.1"):
        try:
            fh = open(fn, "r", errors="replace")
        except Exception:
            continue
        with fh:
            for line in fh:
                if not ua_re.search(line):
                    continue
                parsed = _lean_parse_nginx_combined(line)
                if not parsed:
                    continue
                ip, ts, meth, path, status, ua = parsed
                try:
                    if not _lean_is_google_crawler_ip(ip):
                        continue
                except Exception:
                    continue
                try:
                    dt = _dt.datetime.strptime(ts, "%d/%b/%Y:%H:%M:%S %z")
                except Exception:
                    continue
                hits.append(
                    {
                        "ip": ip,
                        "path": path or "/",
                        "status": status,
                        "ua": ua,
                        "dt": dt,
                        "iso": dt.isoformat(),
                    }
                )
    ent["at"] = now
    ent["hits"] = hits
    return hits


def _lean_google_crawl_stats(range_key: str) -> dict:
    import datetime as _dt

    hours = _lean_lookback_hours_for_range(range_key)
    hits = _lean_scan_google_crawls()
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=hours)
    rows = []
    ips = set()
    paths = {}
    for h in hits:
        dt = h.get("dt")
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        if dt < cutoff:
            continue
        ip = h.get("ip") or ""
        path = h.get("path") or "/"
        ips.add(ip)
        paths[path] = paths.get(path, 0) + 1
        rows.append(h)
    rows.sort(key=lambda x: x.get("dt") or cutoff, reverse=True)
    return {
        "hits": len(rows),
        "ips": len(ips),
        "pages": len(paths),
        "rows": [
            {
                "kind": "google_crawl",
                "who": "Googlebot " + str(r.get("ip") or ""),
                "ip": r.get("ip") or "",
                "path": r.get("path") or "/",
                "href": r.get("path") if str(r.get("path") or "").startswith("/") else "",
                "last_activity": r.get("iso") or "",
                "pages_count": 1,
                "status": r.get("status") or "",
                "page_trail": [
                    {
                        "path": r.get("path") or "/",
                        "occurred_at": r.get("iso") or "",
                    }
                ],
            }
            for r in rows[:40]
        ],
    }


def _lean_quarantine_age_seconds(cur, ip_address: Optional[str]) -> Optional[float]:''',
    )
)

REPLACEMENTS.append(
    (
        '''        signed_card = live_signed if range_key == "live" else signed_in_range
        # Always identity: signed + guests == visitors
        guests_card = max(0, int(visitors or 0) - int(signed_card or 0))

        return JSONResponse(
            {
                "ok": True,
                "range": range_key,''',
        '''        signed_card = live_signed if range_key == "live" else signed_in_range
        # Always identity: signed + guests == visitors
        guests_card = max(0, int(visitors or 0) - int(signed_card or 0))
        google_crawl = {"hits": 0, "ips": 0, "pages": 0, "rows": []}
        try:
            google_crawl = _lean_google_crawl_stats(range_key)
        except Exception:
            google_crawl = {"hits": 0, "ips": 0, "pages": 0, "rows": []}

        return JSONResponse(
            {
                "ok": True,
                "range": range_key,''',
    )
)

REPLACEMENTS.append(
    (
        '''                "sections": donut,
                "sections_all": sections,
            },''',
        '''                "sections": donut,
                "sections_all": sections,
                "google_crawls": int(google_crawl.get("hits") or 0),
                "google_crawl_ips": int(google_crawl.get("ips") or 0),
                "google_crawl_pages": int(google_crawl.get("pages") or 0),
                "google_crawl_rows": google_crawl.get("rows") or [],
            },''',
    )
)

REPLACEMENTS.append(
    (
        '''                "offline_fb": offline_fb[:40],
                "offline_bots": offline_bots[:40],''',
        '''                "offline_fb": offline_fb[:40],
                "offline_google": (_lean_google_crawl_stats("24h").get("rows") or [])[:40],
                "offline_bots": offline_bots[:40],''',
    )
)

REPLACEMENTS.append(
    (
        '''  <p class="note" id="scaleNote">Every box below is for the range you picked only. Staff browsing ignored. Fake bots removed. Direct + Google + Facebook + Other = Visitors. Claim card = popup (members + blocked + left).</p>''',
        '''  <p class="note" id="scaleNote">Every box below is for the range you picked only. Staff browsing ignored. Fake bots removed. Google crawls excluded from Visitors. Direct + Google + Facebook + Other = Visitors. Claim card = popup (members + blocked + left).</p>''',
    )
)

REPLACEMENTS.append(
    (
        '''    <div class="kpi"><div class="l">Google</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">via Google</div></div>''',
        '''    <div class="kpi"><div class="l">Google</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">via Google</div></div>
    <div class="kpi"><div class="l">Google crawls</div><div class="v" id="kGooglebot">—</div><div class="s" id="kGooglebotSub">verified Googlebot · not visitors</div></div>''',
    )
)

REPLACEMENTS.append(
    (
        '''</div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Facebook share crawls''',
        '''</div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineGoogleToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Google crawls <span id="offlineGoogleCount" class="note" style="font-weight:600"></span></h2><p class="note">Verified Googlebot from official IPs. Excluded from Visitors.</p><div id="offlineGoogleBox" hidden><p class="note">Loading…</p></div></section><section class="card" style="margin-top:12px"><h2 style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button type="button" id="offlineFbToggle" class="live-exp" aria-expanded="false" style="font:inherit;font-weight:800">▶</button> Facebook share crawls''',
    )
)

REPLACEMENTS.append(
    (
        '''      if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
      if($("kGoogleSub")) $("kGoogleSub").textContent=String(o.google_landings||0)+" via Google · of "+String(o.visitors||0)+" visitors";''',
        '''      if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
      if($("kGoogleSub")) $("kGoogleSub").textContent=String(o.google_landings||0)+" via Google · of "+String(o.visitors||0)+" visitors";
      if($("kGooglebot")) $("kGooglebot").textContent=String(o.google_crawls||0);
      if($("kGooglebotSub")) $("kGooglebotSub").textContent=String(o.google_crawl_ips||0)+" IPs · "+String(o.google_crawl_pages||0)+" pages · not visitors";
      try{ renderOfflineGoogle({offline_google: o.google_crawl_rows||[]}); }catch(eG){}''',
    )
)

REPLACEMENTS.append(
    (
        '''          if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
          if($("kGoogleSub")) $("kGoogleSub").textContent=(o.google_visitors? (o.google_visitors+" visitors · "):"")+"via Google";''',
        '''          if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
          if($("kGoogleSub")) $("kGoogleSub").textContent=(o.google_visitors? (o.google_visitors+" visitors · "):"")+"via Google";
          if($("kGooglebot")) $("kGooglebot").textContent=String(o.google_crawls||0);
          if($("kGooglebotSub")) $("kGooglebotSub").textContent=String(o.google_crawl_ips||0)+" IPs · "+String(o.google_crawl_pages||0)+" pages · not visitors";''',
    )
)

REPLACEMENTS.append(
    (
        '''        try{ renderOfflineFb(live); }catch(eF){}
        try{ renderOfflineBots(live); }catch(eB){}''',
        '''        try{ renderOfflineGoogle(live); }catch(eG2){}
        try{ renderOfflineFb(live); }catch(eF){}
        try{ renderOfflineBots(live); }catch(eB){}''',
    )
)

REPLACEMENTS.append(
    (
        '''  function renderOfflineFb(d){''',
        '''  function renderOfflineGoogle(d){
    var box=$("offlineGoogleBox");
    var cnt=$("offlineGoogleCount");
    var rows=d.offline_google||d.google_crawl_rows||[];
    if(cnt) cnt.textContent=rows.length?("· "+rows.length):"";
    if(!box) return;
    if(!rows.length){
      box.innerHTML="<p class='note'>No verified Google crawls in this log window.</p>";
      OFFLINE_GOOGLE_OPEN=!!window.__offlineGoogleOpen;
      box.hidden=!OFFLINE_GOOGLE_OPEN;
      var tbtnG=$("offlineGoogleToggle");
      if(tbtnG){ tbtnG.textContent=OFFLINE_GOOGLE_OPEN?"▼":"▶"; tbtnG.setAttribute("aria-expanded", OFFLINE_GOOGLE_OPEN?"true":"false"); }
      return;
    }
    box.innerHTML=renderOfflineRows(rows, "offg");
    bindTrailToggleButtons(box);
    OFFLINE_GOOGLE_OPEN=!!window.__offlineGoogleOpen;
    box.hidden=!OFFLINE_GOOGLE_OPEN;
    var tbtnG2=$("offlineGoogleToggle");
    if(tbtnG2){ tbtnG2.textContent=OFFLINE_GOOGLE_OPEN?"▼":"▶"; tbtnG2.setAttribute("aria-expanded", OFFLINE_GOOGLE_OPEN?"true":"false"); }
  }
  function renderOfflineFb(d){''',
    )
)

REPLACEMENTS.append(
    (
        '''  var OFFLINE_FB_OPEN=!!window.__offlineFbOpen;
  var OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen;''',
        '''  var OFFLINE_GOOGLE_OPEN=!!window.__offlineGoogleOpen;
  var OFFLINE_FB_OPEN=!!window.__offlineFbOpen;
  var OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen;''',
    )
)

REPLACEMENTS.append(
    (
        '''  (function wireOfflineFbToggle(){''',
        '''  (function wireOfflineGoogleToggle(){
    var btn=$("offlineGoogleToggle"), box=$("offlineGoogleBox");
    if(!btn||!box||btn._wired) return;
    btn._wired=true;
    btn.addEventListener("click", function(){
      OFFLINE_GOOGLE_OPEN=!OFFLINE_GOOGLE_OPEN;
      window.__offlineGoogleOpen=OFFLINE_GOOGLE_OPEN;
      box.hidden=!OFFLINE_GOOGLE_OPEN;
      btn.textContent=OFFLINE_GOOGLE_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_GOOGLE_OPEN?"true":"false");
    });
  })();
  (function wireOfflineFbToggle(){''',
    )
)

def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, 1):
        n = text.count(old)
        if n != 1:
            raise SystemExit("patch %d: expected 1 match, found %d" % (i, n))
        text = text.replace(old, new, 1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(path.name + ".bak_googlebot_" + stamp)
    shutil.copy2(path, bak)
    path.write_text(text, encoding="utf-8")
    print("PATCHED", path, "backup", bak)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    apply(target)
