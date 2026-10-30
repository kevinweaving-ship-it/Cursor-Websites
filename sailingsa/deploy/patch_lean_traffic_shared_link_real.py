#!/usr/bin/env python3
"""Fix /traffic undercounting shared-link humans (WhatsApp/email URL clicks).

- Dual-write site_traffic scroll/click → public_page_hits.engagement
- Broaden lean real IP set: engage OR site_traffic engage OR human content deep-link
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"FAIL {label}: count={text.count(old)}")
    return text.replace(old, new, 1)


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if "site_traffic_"+ "scroll" in text.replace("site_traffic_", "site_traffic_") and "shared-link phones" in text:
        print("ALREADY_PATCHED")
        return
    if "Dual-write scroll/click into lean public_page_hits" in text:
        print("ALREADY_PATCHED")
        return

    bak = Path(f"/root/backups/api.py.shared_link_real.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    old_collect = '''    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        _site_traffic.ensure_site_traffic_table(cur)
        n = _site_traffic.insert_traffic_events(cur, normalized)
        conn.commit()
        cur.close()
        return {"ok": True, "saved": n}
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"[traffic] collect failed: {e}", flush=True)
        return JSONResponse(content={"ok": False, "error": "save failed"}, status_code=500)
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/admin/api/traffic/release-human")
'''

    new_collect = '''    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        _site_traffic.ensure_site_traffic_table(cur)
        n = _site_traffic.insert_traffic_events(cur, normalized)
        # Dual-write scroll/click into lean public_page_hits so /traffic counts shared-link humans.
        if not is_bot:
            try:
                for ev in normalized:
                    et = str((ev or {}).get("event_type") or "").strip().lower()
                    if et not in ("scroll", "click"):
                        continue
                    path = str((ev or {}).get("path") or "").strip() or "/"
                    engage_raw = "scrolled" if et == "scroll" else "clicked"
                    try:
                        _lean_merge_hit_engagement_for_path(
                            cur, ip=ip or "", visitor_id="", path=path, engage_raw=engage_raw
                        )
                    except Exception:
                        pass
                    try:
                        _lean_release_quarantine_for_engage(cur, ip, note="site_traffic_"+et)
                    except Exception:
                        pass
            except Exception as e_dw:
                print(f"[traffic] dual-write engage skipped: {e_dw}", flush=True)
        conn.commit()
        cur.close()
        return {"ok": True, "saved": n}
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"[traffic] collect failed: {e}", flush=True)
        return JSONResponse(content={"ok": False, "error": "save failed"}, status_code=500)
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/admin/api/traffic/release-human")
'''
    text = must_replace(text, old_collect, new_collect, "collect dual-write")

    old_real = '''    # Real = scrolled, or clicked without search-fake (Meta preview bots fake searched+clicked).
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
        )
    """
'''

    new_real = '''    # Real =
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
    text = must_replace(text, old_real, new_real, "real_ip broaden")
    API.write_text(text, encoding="utf-8")
    print("OK")


if __name__ == "__main__":
    main()
