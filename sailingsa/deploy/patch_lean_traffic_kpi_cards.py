#!/usr/bin/env python3
"""Surgical /traffic KPI fix: Signed-in + FB cards accurate vs tables.

Live-only lean traffic HTML/API in api.py. No other URL handlers.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"PATCH FAIL {label}: count={n}")
    return text.replace(old, new, 1)


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if 'id="kFb"' in text and "facebook_landings" in text and "signed_in_range" in text:
        print("ALREADY_PATCHED")
        return

    bak = Path(f"/root/backups/api.py.kpi_cards.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    # --- 1) KPI HTML: Signed-in subtext id + FB card ---
    old_kpis = '''    <div class="kpi"><div class="l">Signed-in live</div><div class="v" id="kSigned">—</div><div class="s">vs guests</div></div>
    <div class="kpi"><div class="l">Google landings</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">referrer / gclid</div></div>
'''
    new_kpis = '''    <div class="kpi"><div class="l" id="kSignedLabel">Signed-in</div><div class="v" id="kSigned">—</div><div class="s" id="kSignedSub">vs guests</div></div>
    <div class="kpi"><div class="l">Google landings</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">referrer / gclid</div></div>
    <div class="kpi"><div class="l">Facebook landings</div><div class="v" id="kFb">—</div><div class="s" id="kFbSub">referrer / fbclid</div></div>
'''
    text = must_replace(text, old_kpis, new_kpis, "kpi html")

    # --- 2) Overview: FB counts + range-aware signed/guests ---
    old_g = '''        google_landings = 0
        google_visitors = 0
        try:
            cur.execute("SAVEPOINT gref")
            _lean_ensure_page_hit_referrer_column(cur)
            g_where = "TRUE" if not since_sql else "occurred_at >= NOW() - INTERVAL %s"
            g_params = () if not since_sql else (since_sql,)
            g_sql = """
                SELECT
                  COUNT(*) FILTER (WHERE is_g)::int AS landings,
                  COUNT(DISTINCT visitor_id) FILTER (WHERE is_g)::int AS gvis
                FROM (
                  SELECT visitor_id,
                    (
                      lower(coalesce(referrer, '')) LIKE '%%google%%'
                      OR lower(path) LIKE '%%gclid=%%'
                      OR lower(path) LIKE '%%utm_source=google%%'
                    ) AS is_g
                  FROM public.public_page_hits
                  WHERE """ + g_where + """
                ) z
                """
            cur.execute(g_sql, g_params)
            grow = cur.fetchone() or {}
            if isinstance(grow, dict):
                google_landings = int(grow.get("landings") or 0)
                google_visitors = int(grow.get("gvis") or 0)
            else:
                google_landings = int(grow[0] or 0)
                google_visitors = int(grow[1] or 0)
            cur.execute("RELEASE SAVEPOINT gref")
        except Exception:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT gref")
            except Exception:
                pass
            google_landings = 0
            google_visitors = 0
        return JSONResponse(
            {
                "ok": True,
                "range": range_key,
                "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES,
                "live_anon": live_anon,
                "live_signed": live_signed,
                "live_admin": live_admin,
                "live_total": live_total,
                "hits": hits,
                "visitors": visitors,
                "google_landings": google_landings,
                "google_visitors": google_visitors,
                "quarantine_ips": quarantine_ips,
                "sections": donut,
                "sections_all": sections,
            },
            headers={"Cache-Control": "no-store"},
        )
'''
    new_g = '''        google_landings = 0
        google_visitors = 0
        facebook_landings = 0
        facebook_visitors = 0
        try:
            cur.execute("SAVEPOINT gref")
            _lean_ensure_page_hit_referrer_column(cur)
            g_where = "TRUE" if not since_sql else "occurred_at >= NOW() - INTERVAL %s"
            g_params = () if not since_sql else (since_sql,)
            g_sql = """
                SELECT
                  COUNT(*) FILTER (WHERE is_g)::int AS landings,
                  COUNT(DISTINCT visitor_id) FILTER (WHERE is_g)::int AS gvis,
                  COUNT(*) FILTER (WHERE is_f)::int AS fb_landings,
                  COUNT(DISTINCT visitor_id) FILTER (WHERE is_f)::int AS fb_vis
                FROM (
                  SELECT visitor_id,
                    (
                      lower(coalesce(referrer, '')) LIKE '%%google%%'
                      OR lower(path) LIKE '%%gclid=%%'
                      OR lower(path) LIKE '%%utm_source=google%%'
                    ) AS is_g,
                    (
                      lower(coalesce(referrer, '')) LIKE '%%facebook.%%'
                      OR lower(coalesce(referrer, '')) LIKE '%%fb.com%%'
                      OR lower(coalesce(referrer, '')) LIKE '%%fb.me%%'
                      OR lower(path) LIKE '%%fbclid=%%'
                      OR lower(path) LIKE '%%utm_source=facebook%%'
                      OR lower(path) LIKE '%%utm_source=fb%%'
                    ) AS is_f
                  FROM public.public_page_hits
                  WHERE """ + g_where + """
                ) z
                """
            cur.execute(g_sql, g_params)
            grow = cur.fetchone() or {}
            if isinstance(grow, dict):
                google_landings = int(grow.get("landings") or 0)
                google_visitors = int(grow.get("gvis") or 0)
                facebook_landings = int(grow.get("fb_landings") or 0)
                facebook_visitors = int(grow.get("fb_vis") or 0)
            else:
                google_landings = int(grow[0] or 0)
                google_visitors = int(grow[1] or 0)
                facebook_landings = int(grow[2] or 0)
                facebook_visitors = int(grow[3] or 0)
            cur.execute("RELEASE SAVEPOINT gref")
        except Exception:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT gref")
            except Exception:
                pass
            google_landings = 0
            google_visitors = 0
            facebook_landings = 0
            facebook_visitors = 0

        # Signed-in humans in selected range (exclude super_admin staff)
        signed_in_range = 0
        try:
            cur.execute("SAVEPOINT signedref")
            if since_sql:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT sas_id::text) AS n
                    FROM public.user_sessions
                    WHERE last_activity >= NOW() - INTERVAL %s
                      AND sas_id IS NOT NULL AND TRIM(sas_id::text) <> ''
                      AND COALESCE(is_active, true) = true
                      AND sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """
                    """,
                    (since_sql,),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT sas_id::text) AS n
                    FROM public.user_sessions
                    WHERE sas_id IS NOT NULL AND TRIM(sas_id::text) <> ''
                      AND COALESCE(is_active, true) = true
                      AND sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """
                    """
                )
            srow = cur.fetchone() or {}
            signed_in_range = int((srow.get("n") if isinstance(srow, dict) else srow[0]) or 0)
            cur.execute("RELEASE SAVEPOINT signedref")
        except Exception:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT signedref")
            except Exception:
                pass
            signed_in_range = 0

        # Card value: live window when range=live, else signed humans in range
        signed_card = live_signed if range_key == "live" else signed_in_range
        guests_card = max(0, int(live_anon or 0)) if range_key == "live" else max(0, int(visitors or 0) - int(signed_in_range or 0))

        return JSONResponse(
            {
                "ok": True,
                "range": range_key,
                "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES,
                "live_anon": live_anon,
                "live_signed": live_signed,
                "live_admin": live_admin,
                "live_total": live_total,
                "hits": hits,
                "visitors": visitors,
                "google_landings": google_landings,
                "google_visitors": google_visitors,
                "facebook_landings": facebook_landings,
                "facebook_visitors": facebook_visitors,
                "signed_in_range": signed_in_range,
                "signed_card": signed_card,
                "guests_card": guests_card,
                "quarantine_ips": quarantine_ips,
                "sections": donut,
                "sections_all": sections,
            },
            headers={"Cache-Control": "no-store"},
        )
'''
    text = must_replace(text, old_g, new_g, "overview fb+signed")

    # --- 3) JS: wire Signed-in + FB cards ---
    old_js = '''      $("kVis").textContent=String(o.visitors||0);
      $("kHits").textContent=String(o.hits||0);
      $("kSigned").textContent=String(o.live_signed||0);
      if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
      if($("kGoogleSub")) $("kGoogleSub").textContent=(o.google_visitors? (o.google_visitors+" visitors · "):"")+"referrer / gclid (not GSC)";
'''
    new_js = '''      $("kVis").textContent=String(o.visitors||0);
      $("kHits").textContent=String(o.hits||0);
      $("kSigned").textContent=String((o.signed_card!=null?o.signed_card:o.live_signed)||0);
      if($("kSignedLabel")) $("kSignedLabel").textContent=(RANGE==="live")?"Signed-in live":"Signed-in";
      if($("kSignedSub")) $("kSignedSub").textContent=String(o.guests_card!=null?o.guests_card:o.live_anon||0)+" guests"+(RANGE==="live"?" live":" in range");
      if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
      if($("kGoogleSub")) $("kGoogleSub").textContent=(o.google_visitors? (o.google_visitors+" visitors · "):"")+"referrer / gclid (not GSC)";
      if($("kFb")) $("kFb").textContent=String(o.facebook_landings||0);
      if($("kFbSub")) $("kFbSub").textContent=(o.facebook_visitors? (o.facebook_visitors+" visitors · "):"")+"referrer / fbclid";
'''
    # two occurrences (loadAll + poll) — replace_all carefully
    if text.count(old_js) < 1:
        raise SystemExit("PATCH FAIL js card setter missing")
    text = text.replace(old_js, new_js)

    # poll path may use slightly different block - check remaining live_signed-only setters
    old_poll = '''          $("kVis").textContent=String(o.visitors||0);
          $("kHits").textContent=String(o.hits||0);
          $("kSigned").textContent=String(o.live_signed||0);
          if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
'''
    if old_poll in text:
        new_poll = '''          $("kVis").textContent=String(o.visitors||0);
          $("kHits").textContent=String(o.hits||0);
          $("kSigned").textContent=String((o.signed_card!=null?o.signed_card:o.live_signed)||0);
          if($("kSignedLabel")) $("kSignedLabel").textContent=(RANGE==="live")?"Signed-in live":"Signed-in";
          if($("kSignedSub")) $("kSignedSub").textContent=String(o.guests_card!=null?o.guests_card:o.live_anon||0)+" guests"+(RANGE==="live"?" live":" in range");
          if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
          if($("kFb")) $("kFb").textContent=String(o.facebook_landings||0);
          if($("kFbSub")) $("kFbSub").textContent=(o.facebook_visitors? (o.facebook_visitors+" visitors · "):"")+"referrer / fbclid";
'''
        text = must_replace(text, old_poll, new_poll, "poll card setter")

    # --- 4) Fix blank Facebook share-crawls: query Meta IPs directly, not last-80 global hits ---
    old_fb = '''        offline_fb = []
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
                # Skip Meta IPs that scrolled — those are humans in FB browser, not share crawls
                try:
                    cur.execute(
                        """
                        SELECT 1 FROM public.public_page_hits
                        WHERE ip_address = %s
                          AND engagement ~* 'scroll'
                          AND occurred_at > NOW() - interval '24 hours'
                        LIMIT 1
                        """,
                        (ip[:80],),
                    )
                    if cur.fetchone():
                        continue
                except Exception:
                    _lean_db_rollback(conn)
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
    new_fb = '''        offline_fb = []
        try:
            since = _lean_traffic_real_since()
            # Direct Meta egress prefixes (link-preview crawlers) — do NOT scan last-N global hits
            # (those miss older FB crawls and leave the FB panel blank).
            cur.execute(
                """
                SELECT DISTINCT ON (h.ip_address)
                       h.ip_address, h.path, h.occurred_at
                FROM public.public_page_hits h
                WHERE h.occurred_at >= %s::timestamptz
                  AND h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
                  AND (
                       h.ip_address LIKE '173.252.%%'
                    OR h.ip_address LIKE '69.63.%%'
                    OR h.ip_address LIKE '69.171.%%'
                    OR h.ip_address LIKE '31.13.%%'
                    OR h.ip_address LIKE '66.220.%%'
                    OR h.ip_address LIKE '157.240.%%'
                    OR h.ip_address LIKE '185.60.%%'
                  )
                ORDER BY h.ip_address, h.occurred_at DESC
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
                # Skip Meta IPs that scrolled — those are humans in FB browser, not share crawls
                try:
                    cur.execute(
                        """
                        SELECT 1 FROM public.public_page_hits
                        WHERE ip_address = %s
                          AND engagement ~* 'scroll'
                          AND occurred_at >= %s::timestamptz
                        LIMIT 1
                        """,
                        (ip[:80], since),
                    )
                    if cur.fetchone():
                        continue
                except Exception:
                    _lean_db_rollback(conn)
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
            # Newest first for the panel
            try:
                offline_fb.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
            except Exception:
                pass
        except Exception:
            offline_fb = []
'''
    text = must_replace(text, old_fb, new_fb, "offline_fb query")

    API.write_text(text, encoding="utf-8")
    print(f"WROTE lines={text.count(chr(10))+1}")
    print("OK")


if __name__ == "__main__":
    main()
