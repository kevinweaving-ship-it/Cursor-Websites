#!/usr/bin/env python3
"""Stop fake one-day visitor spikes: tighten deep-link 'real' rule + exclude headless bots.

Aug 18 had ~884 IPs but 864 were single-hit (no scroll); Lightpanda + spoofed Chrome.
Deep-link-without-engage was counting scrapes as visitors (~684 on chart).
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


OLD = r'''    # Real =
    #  (A) scrolled / clicked (non search-fake) on public_page_hits
    #  (B) site_traffic_events scroll/click (beacon dual-path; shared-link phones often only hit this)
    #  (C) human-browser content deep-link (/sailor|/club|/regatta|/class|/boat) — WhatsApp/email clicks
    #      often never fire in-page scroll before leave; still unique human IPs.
    since_clause_ste = ""
    since_clause_sess = ""
    if since_sql:
        since_clause_ste = f" AND ste.created_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_sess = f" AND ps.last_activity > NOW() - INTERVAL '{since_sql}'"
    real_ip_sql = f"""
        AND ip_address IN (
          SELECT DISTINCT he.ip_address
          FROM public.public_page_hits he
          WHERE he.ip_address IS NOT NULL AND TRIM(he.ip_address) <> ''
            {since_clause_eng}
            AND (
              he.engagement ~* 'scroll'
              OR (he.engagement ~* 'click' AND he.engagement !~* 'search')
            )
          UNION
          SELECT DISTINCT ste.ip_address
          FROM public.site_traffic_events ste
          WHERE ste.ip_address IS NOT NULL AND TRIM(ste.ip_address) <> ''
            AND COALESCE(ste.is_bot, false) = false
            AND ste.event_type IN ('scroll', 'click')
            {since_clause_ste}
          UNION
          SELECT DISTINCT h2.ip_address
          FROM public.public_page_hits h2
          INNER JOIN public.public_sessions ps
            ON ps.ip_address = h2.ip_address
          WHERE h2.ip_address IS NOT NULL AND TRIM(h2.ip_address) <> ''
            {since_clause_eng.replace('he.', 'h2.')}
            {since_clause_sess}
            AND (
                 h2.path LIKE '/sailor/%%'
              OR h2.path LIKE '/club/%%'
              OR h2.path LIKE '/regatta/%%'
              OR h2.path LIKE '/class/%%'
              OR h2.path LIKE '/boat/%%'
              OR h2.path LIKE '/boat-name/%%'
              OR h2.path LIKE '/events-logos/%%'
            )
            AND COALESCE(ps.user_agent, '') <> ''
            AND lower(ps.user_agent) NOT LIKE '%%bot%%'
            AND lower(ps.user_agent) NOT LIKE '%%crawl%%'
            AND lower(ps.user_agent) NOT LIKE '%%spider%%'
            AND lower(ps.user_agent) NOT LIKE '%%facebookexternal%%'
            AND lower(ps.user_agent) NOT LIKE '%%meta-external%%'
            AND (
                 lower(ps.user_agent) LIKE '%%iphone%%'
              OR lower(ps.user_agent) LIKE '%%ipad%%'
              OR lower(ps.user_agent) LIKE '%%android%%'
              OR lower(ps.user_agent) LIKE '%%mobile%%'
              OR lower(ps.user_agent) LIKE '%%chrome/%%'
              OR lower(ps.user_agent) LIKE '%%safari/%%'
              OR lower(ps.user_agent) LIKE '%%firefox/%%'
              OR lower(ps.user_agent) LIKE '%%edg/%%'
            )
        )
    """
'''

NEW = r'''    # Real =
    #  (A) scrolled / clicked (non search-fake) on public_page_hits
    #  (B) site_traffic_events scroll/click (beacon)
    #  (C) content deep-link ONLY if looks like a real open (dwell>=5s OR 2+ pages) —
    #      not one-hit scrapes (Aug 18 spike: 864/883 IPs single-hit, Lightpanda, etc.)
    since_clause_ste = ""
    since_clause_sess = ""
    since_clause_h2b = ""
    if since_sql:
        since_clause_ste = f" AND ste.created_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_sess = f" AND ps.last_activity > NOW() - INTERVAL '{since_sql}'"
        since_clause_h2b = f" AND h2b.occurred_at > NOW() - INTERVAL '{since_sql}'"
    real_ip_sql = f"""
        AND ip_address IN (
          SELECT DISTINCT he.ip_address
          FROM public.public_page_hits he
          WHERE he.ip_address IS NOT NULL AND TRIM(he.ip_address) <> ''
            {since_clause_eng}
            AND (
              he.engagement ~* 'scroll'
              OR (he.engagement ~* 'click' AND he.engagement !~* 'search')
            )
          UNION
          SELECT DISTINCT ste.ip_address
          FROM public.site_traffic_events ste
          WHERE ste.ip_address IS NOT NULL AND TRIM(ste.ip_address) <> ''
            AND COALESCE(ste.is_bot, false) = false
            AND ste.event_type IN ('scroll', 'click')
            {since_clause_ste}
          UNION
          SELECT DISTINCT h2.ip_address
          FROM public.public_page_hits h2
          INNER JOIN public.public_sessions ps
            ON ps.ip_address = h2.ip_address
          WHERE h2.ip_address IS NOT NULL AND TRIM(h2.ip_address) <> ''
            {since_clause_eng.replace('he.', 'h2.')}
            {since_clause_sess}
            AND (
                 h2.path LIKE '/sailor/%%'
              OR h2.path LIKE '/club/%%'
              OR h2.path LIKE '/regatta/%%'
              OR h2.path LIKE '/class/%%'
              OR h2.path LIKE '/boat/%%'
              OR h2.path LIKE '/boat-name/%%'
              OR h2.path LIKE '/events-logos/%%'
            )
            AND COALESCE(ps.user_agent, '') <> ''
            AND lower(ps.user_agent) NOT LIKE '%%bot%%'
            AND lower(ps.user_agent) NOT LIKE '%%crawl%%'
            AND lower(ps.user_agent) NOT LIKE '%%spider%%'
            AND lower(ps.user_agent) NOT LIKE '%%facebookexternal%%'
            AND lower(ps.user_agent) NOT LIKE '%%meta-external%%'
            AND lower(ps.user_agent) NOT LIKE '%%lightpanda%%'
            AND lower(ps.user_agent) NOT LIKE '%%headless%%'
            AND lower(ps.user_agent) NOT LIKE '%%phantom%%'
            AND lower(ps.user_agent) NOT LIKE '%%puppeteer%%'
            AND lower(ps.user_agent) NOT LIKE '%%playwright%%'
            AND lower(ps.user_agent) NOT LIKE '%%selenium%%'
            AND (
                 lower(ps.user_agent) LIKE '%%iphone%%'
              OR lower(ps.user_agent) LIKE '%%ipad%%'
              OR lower(ps.user_agent) LIKE '%%android%%'
              OR lower(ps.user_agent) LIKE '%%mobile%%'
              OR lower(ps.user_agent) LIKE '%%chrome/%%'
              OR lower(ps.user_agent) LIKE '%%safari/%%'
              OR lower(ps.user_agent) LIKE '%%firefox/%%'
              OR lower(ps.user_agent) LIKE '%%edg/%%'
            )
            AND (
              COALESCE(h2.dwell_seconds, 0) >= 5
              OR (
                SELECT COUNT(*) FROM public.public_page_hits h2b
                WHERE h2b.ip_address = h2.ip_address
                  {since_clause_h2b}
              ) >= 2
            )
        )
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
    """
'''


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if "lightpanda" in text and "dwell_seconds, 0) >= 5" in text:
        print("ALREADY_PATCHED")
        return
    if "_LEAN_TRAFFIC_QUARANTINE_IP_SQL" not in text:
        raise SystemExit("missing quarantine SQL const")

    bak = Path(f"/root/backups/api.py.spike_real.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    text = must_replace(text, OLD, NEW, "unified real deep-link")
    API.write_text(text, encoding="utf-8")
    print("PATCHED")


if __name__ == "__main__":
    main()
