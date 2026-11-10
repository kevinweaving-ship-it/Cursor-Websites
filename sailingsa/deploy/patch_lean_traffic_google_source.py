#!/usr/bin/env python3
"""Fix /traffic Google (and FB) source cards: stop zeroing on failure; use any Google signal.

- Source split failed → fallback set Google=0 of N (bullshit). Harden SQL (pct_escape) + rollback.
- Attribute by ANY google/facebook signal in range (page_hits referrer OR site_traffic source_channel),
  not only first-touch hit (often empty referrer).
- UI subtext: "X via Google · of Y visitors" (clearer than "0 of 920 real · via Google").
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


OLD_SRC = r'''            # First-touch for real visitor_keys only (same set as Visitors card).
            unified_src = _lean_traffic_unified_sql(since_sql)
            # Embed interval — do NOT pass pyformat params (unified SQL contains LIKE % wildcards).
            g_where = "TRUE" if not since_sql else f"h.occurred_at >= NOW() - INTERVAL '{since_sql}'"
            g_sql = """
                WITH real_keys AS (
                  SELECT DISTINCT visitor_key
                  FROM (""" + unified_src + """) u
                  WHERE visitor_key IS NOT NULL AND TRIM(visitor_key) <> ''
                ),
                first_touch AS (
                  SELECT DISTINCT ON (COALESCE(NULLIF(TRIM(h.ip_address::text), ''), h.visitor_id::text))
                    COALESCE(NULLIF(TRIM(h.ip_address::text), ''), h.visitor_id::text) AS visitor_key,
                    h.referrer,
                    h.path
                  FROM public.public_page_hits h
                  WHERE """ + g_where + """
                    AND (
                      (h.ip_address IS NOT NULL AND TRIM(h.ip_address::text) <> '')
                      OR h.visitor_id IS NOT NULL
                    )
                  ORDER BY
                    COALESCE(NULLIF(TRIM(h.ip_address::text), ''), h.visitor_id::text),
                    h.occurred_at ASC
                )
                SELECT
                  COUNT(*) FILTER (WHERE src = 'direct')::int AS d_land,
                  COUNT(*) FILTER (WHERE src = 'google')::int AS g_land,
                  COUNT(*) FILTER (WHERE src = 'facebook')::int AS f_land,
                  COUNT(*) FILTER (WHERE src = 'other')::int AS o_land
                FROM (
                  SELECT
                    CASE
                      WHEN lower(coalesce(ft.referrer, '')) LIKE '%%google%%'
                        OR lower(ft.path) LIKE '%%gclid=%%'
                        OR lower(ft.path) LIKE '%%utm_source=google%%'
                        THEN 'google'
                      WHEN lower(coalesce(ft.referrer, '')) LIKE '%%facebook.%%'
                        OR lower(coalesce(ft.referrer, '')) LIKE '%%fb.com%%'
                        OR lower(coalesce(ft.referrer, '')) LIKE '%%fb.me%%'
                        OR lower(ft.path) LIKE '%%fbclid=%%'
                        OR lower(ft.path) LIKE '%%utm_source=facebook%%'
                        OR lower(ft.path) LIKE '%%utm_source=fb%%'
                        THEN 'facebook'
                      WHEN coalesce(trim(ft.referrer), '') = ''
                        OR lower(ft.referrer) LIKE '%%sailingsa.co.za%%'
                        THEN 'direct'
                      ELSE 'other'
                    END AS src
                  FROM first_touch ft
                  INNER JOIN real_keys rk ON rk.visitor_key = ft.visitor_key
                ) z
                """
            cur.execute(g_sql)
            grow = cur.fetchone() or {}
            if isinstance(grow, dict):
                direct_landings = int(grow.get("d_land") or 0)
                google_landings = int(grow.get("g_land") or 0)
                facebook_landings = int(grow.get("f_land") or 0)
                other_landings = int(grow.get("o_land") or 0)
            elif grow is not None and len(grow) >= 4:
                direct_landings = int(grow[0] or 0)
                google_landings = int(grow[1] or 0)
                facebook_landings = int(grow[2] or 0)
                other_landings = int(grow[3] or 0)
            else:
                direct_landings = int(visitors or 0)
                google_landings = 0
                facebook_landings = 0
                other_landings = 0
'''

NEW_SRC = r'''            # Any-signal source for real visitor_keys (hits referrer/utm OR beacon source_channel).
            # pct_escape so embedded LIKE % never trips psycopg if vars are passed.
            unified_src = _lean_traffic_unified_sql(since_sql, pct_escape=True)
            g_where = "TRUE" if not since_sql else f"h.occurred_at >= NOW() - INTERVAL '{since_sql}'"
            ste_where = "TRUE" if not since_sql else f"ste.created_at >= NOW() - INTERVAL '{since_sql}'"
            g_sql = """
                WITH real_keys AS (
                  SELECT DISTINCT visitor_key
                  FROM (""" + unified_src + """) u
                  WHERE visitor_key IS NOT NULL AND TRIM(visitor_key) <> ''
                ),
                hit_flags AS (
                  SELECT
                    COALESCE(NULLIF(TRIM(h.ip_address::text), ''), h.visitor_id::text) AS visitor_key,
                    bool_or(
                      lower(coalesce(h.referrer, '')) LIKE '%%google%%'
                      OR lower(h.path) LIKE '%%gclid=%%'
                      OR lower(h.path) LIKE '%%utm_source=google%%'
                    ) AS is_google,
                    bool_or(
                      lower(coalesce(h.referrer, '')) LIKE '%%facebook.%%'
                      OR lower(coalesce(h.referrer, '')) LIKE '%%fb.com%%'
                      OR lower(coalesce(h.referrer, '')) LIKE '%%fb.me%%'
                      OR lower(h.path) LIKE '%%fbclid=%%'
                      OR lower(h.path) LIKE '%%utm_source=facebook%%'
                      OR lower(h.path) LIKE '%%utm_source=fb%%'
                    ) AS is_facebook,
                    bool_or(
                      coalesce(trim(h.referrer), '') <> ''
                      AND lower(h.referrer) NOT LIKE '%%sailingsa.co.za%%'
                      AND lower(coalesce(h.referrer, '')) NOT LIKE '%%google%%'
                      AND lower(coalesce(h.referrer, '')) NOT LIKE '%%facebook.%%'
                      AND lower(coalesce(h.referrer, '')) NOT LIKE '%%fb.com%%'
                      AND lower(coalesce(h.referrer, '')) NOT LIKE '%%fb.me%%'
                    ) AS is_other
                  FROM public.public_page_hits h
                  WHERE """ + g_where + """
                    AND (
                      (h.ip_address IS NOT NULL AND TRIM(h.ip_address::text) <> '')
                      OR h.visitor_id IS NOT NULL
                    )
                  GROUP BY 1
                ),
                ste_flags AS (
                  SELECT
                    NULLIF(TRIM(ste.ip_address::text), '') AS visitor_key,
                    bool_or(
                      lower(coalesce(ste.source_channel, '')) = 'google'
                      OR lower(coalesce(ste.referrer, '')) LIKE '%%google%%'
                      OR lower(coalesce(ste.utm_source, '')) = 'google'
                    ) AS is_google,
                    bool_or(
                      lower(coalesce(ste.source_channel, '')) IN ('facebook', 'social')
                      OR lower(coalesce(ste.referrer, '')) LIKE '%%facebook.%%'
                      OR lower(coalesce(ste.referrer, '')) LIKE '%%fb.com%%'
                      OR lower(coalesce(ste.utm_source, '')) IN ('facebook', 'fb')
                    ) AS is_facebook,
                    bool_or(
                      lower(coalesce(ste.source_channel, '')) IN ('referral', 'other')
                      OR (
                        coalesce(trim(ste.referrer), '') <> ''
                        AND lower(ste.referrer) NOT LIKE '%%sailingsa.co.za%%'
                        AND lower(coalesce(ste.referrer, '')) NOT LIKE '%%google%%'
                        AND lower(coalesce(ste.referrer, '')) NOT LIKE '%%facebook.%%'
                      )
                    ) AS is_other
                  FROM public.site_traffic_events ste
                  WHERE """ + ste_where + """
                    AND COALESCE(ste.is_bot, false) = false
                    AND ste.ip_address IS NOT NULL AND TRIM(ste.ip_address::text) <> ''
                  GROUP BY 1
                )
                SELECT
                  COUNT(*) FILTER (WHERE src = 'direct')::int AS d_land,
                  COUNT(*) FILTER (WHERE src = 'google')::int AS g_land,
                  COUNT(*) FILTER (WHERE src = 'facebook')::int AS f_land,
                  COUNT(*) FILTER (WHERE src = 'other')::int AS o_land
                FROM (
                  SELECT
                    CASE
                      WHEN COALESCE(hf.is_google, false) OR COALESCE(sf.is_google, false) THEN 'google'
                      WHEN COALESCE(hf.is_facebook, false) OR COALESCE(sf.is_facebook, false) THEN 'facebook'
                      WHEN COALESCE(hf.is_other, false) OR COALESCE(sf.is_other, false) THEN 'other'
                      ELSE 'direct'
                    END AS src
                  FROM real_keys rk
                  LEFT JOIN hit_flags hf ON hf.visitor_key = rk.visitor_key
                  LEFT JOIN ste_flags sf ON sf.visitor_key = rk.visitor_key
                ) z
                """
            try:
                cur.execute("ROLLBACK TO SAVEPOINT gref")
            except Exception:
                pass
            try:
                cur.execute("SAVEPOINT gref")
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                cur.execute("SAVEPOINT gref")
            cur.execute(g_sql)  # no vars — percents already doubled via pct_escape + %% literals
            grow = cur.fetchone() or {}
            if isinstance(grow, dict):
                direct_landings = int(grow.get("d_land") or 0)
                google_landings = int(grow.get("g_land") or 0)
                facebook_landings = int(grow.get("f_land") or 0)
                other_landings = int(grow.get("o_land") or 0)
            elif grow is not None and len(grow) >= 4:
                direct_landings = int(grow[0] or 0)
                google_landings = int(grow[1] or 0)
                facebook_landings = int(grow[2] or 0)
                other_landings = int(grow[3] or 0)
            else:
                direct_landings = int(visitors or 0)
                google_landings = 0
                facebook_landings = 0
                other_landings = 0
'''


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if "ste_flags AS (" in text and "Any-signal source for real visitor_keys" in text:
        print("ALREADY_PATCHED")
        return

    bak = Path(f"/root/backups/api.py.google_source.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    # Remove duplicate SAVEPOINT gref just before our block if present — keep the one inside NEW_SRC
    # Existing code has: cur.execute("SAVEPOINT gref") then ensure column then OLD_SRC
    # We'll leave the outer SAVEPOINT; NEW_SRC resets it safely.

    text = must_replace(text, OLD_SRC, NEW_SRC, "source split sql")

    # UI subtext — primary loadAll path
    text = must_replace(
        text,
        '''      if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
      if($("kGoogleSub")) $("kGoogleSub").textContent="of "+String(o.visitors||0)+" real · via Google";
      if($("kFb")) $("kFb").textContent=String(o.facebook_landings||0);
      if($("kFbSub")) $("kFbSub").textContent="of "+String(o.visitors||0)+" real · via Facebook";''',
        '''      if($("kGoogle")) $("kGoogle").textContent=String(o.google_landings||0);
      if($("kGoogleSub")) $("kGoogleSub").textContent=String(o.google_landings||0)+" via Google · of "+String(o.visitors||0)+" visitors";
      if($("kFb")) $("kFb").textContent=String(o.facebook_landings||0);
      if($("kFbSub")) $("kFbSub").textContent=String(o.facebook_landings||0)+" via Facebook · of "+String(o.visitors||0)+" visitors";''',
        "kpi google/fb subtext",
    )

    # Direct subtext for consistency if present
    if 'textContent="of "+String(o.visitors||0)+" real · typed / bookmark / chat"' in text:
        text = must_replace(
            text,
            'textContent="of "+String(o.visitors||0)+" real · typed / bookmark / chat";',
            'textContent=String(o.direct_landings||0)+" direct · of "+String(o.visitors||0)+" visitors";',
            "kpi direct subtext",
        )

    API.write_text(text, encoding="utf-8")
    print("PATCHED")


if __name__ == "__main__":
    main()
