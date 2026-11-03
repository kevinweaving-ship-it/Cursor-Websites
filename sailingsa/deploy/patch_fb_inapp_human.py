#!/usr/bin/env python3
"""Meta IP can be FB in-app humans — count them; only link-preview crawlers are bots."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

def rep(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f"FAIL {label}\n---\n{old[:200]}")
    text = text.replace(old, new, 1)
    print("OK", label)

# 1) crawler_cloud_ip: do NOT ban Meta IP alone (FB in-app uses Meta egress)
rep(
    '''def _lean_is_crawler_cloud_ip(ip: str) -> bool:
    """Hard hide from Guest/Done: Meta, Google crawler, AWS/Alibaba datacenter ranges.

    These ranges are overwhelmingly scrapers/link-preview bots on this site — not SA home/mobile.
    """
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        if _lean_is_facebook_crawler_ip(ip):
            return True
    except Exception:
        pass
    try:
        if _lean_is_google_crawler_ip(ip):
            return True
    except Exception:
        pass
    try:
        if _lean_ip_is_cloud_datacenter(ip):
            return True
    except Exception:
        pass
    return False
''',
    '''def _lean_is_crawler_cloud_ip(ip: str) -> bool:
    """Hard hide: Google crawler + AWS/Alibaba/Azure datacenter ranges.

    Meta/Facebook IPs are NOT included — real people browse inside Facebook's in-app
    browser on Meta egress. Link-preview crawlers are detected via UA instead.
    """
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        if _lean_is_google_crawler_ip(ip):
            return True
    except Exception:
        pass
    try:
        if _lean_ip_is_cloud_datacenter(ip):
            return True
    except Exception:
        pass
    return False


def _lean_is_facebook_inapp_human_ua(user_agent: str) -> bool:
    """Person using Facebook/Instagram in-app browser (not link-preview crawler)."""
    ua = (user_agent or "").lower()
    if not ua:
        return False
    if _lean_is_facebook_crawler_ua(user_agent):
        return False
    return any(
        x in ua
        for x in (
            "fban/",
            "fbav/",
            "fb_iab",
            "fb4a",
            "fbios",
            "instagram",
            "; fb",  # common mobile FB marker
        )
    )
''',
    "crawler_cloud no meta-ip-ban",
)

# 2) Real engage: reject searched-without-scroll (Meta preview fake); scroll/click OK
rep(
    '''def _lean_tokens_are_real_human_engage(tokens) -> bool:
    """Real people scroll or click. searched-alone is a bot/crawler fake (Meta/AWS samples)."""
    if not tokens:
        return False
    if isinstance(tokens, str):
        tokens = _lean_parse_engage_tokens(tokens)
    try:
        toks = {str(t).strip().lower() for t in (tokens or []) if t}
    except Exception:
        toks = set()
    return bool(toks & {"scrolled", "clicked"})
''',
    '''def _lean_tokens_are_real_human_engage(tokens) -> bool:
    """Real people scroll or click (incl. Facebook in-app browser).

    Link-preview crawlers often fake searched+clicked without scroll — that is NOT real.
    scrolled => always real. clicked without search-only fake => real.
    """
    if not tokens:
        return False
    if isinstance(tokens, str):
        tokens = _lean_parse_engage_tokens(tokens)
    try:
        toks = {str(t).strip().lower() for t in (tokens or []) if t}
    except Exception:
        toks = set()
    if "scrolled" in toks:
        return True
    if "clicked" in toks and "searched" not in toks:
        return True
    # searched+clicked without scroll = preview-bot pattern
    return False
''',
    "engage tokens fb-safe",
)

# 3) Touch: quarantine on crawler UA or cloud IP — not Meta IP alone
rep(
    '''    # Meta/AWS/Alibaba/Google: never Guest — quarantine and skip (no live monitoring cost)
    try:
        if _lean_is_crawler_cloud_ip(ip):
            conn_q = None
            try:
                conn_q = get_db_connection()
                cur_q = conn_q.cursor()
                _lean_quarantine_ip(cur_q, ip, "crawler_cloud_ip")
                conn_q.commit()
            except Exception:
                try:
                    if conn_q:
                        conn_q.rollback()
                except Exception:
                    pass
            finally:
                if conn_q:
                    try:
                        return_db_connection(conn_q)
                    except Exception:
                        pass
            return None
    except Exception:
        pass
''',
    '''    # AWS/Alibaba/Google cloud scrapers: quarantine and skip.
    # Meta IP alone is NOT skipped — humans open links inside Facebook browser.
    try:
        ua_touch = ""
        try:
            ua_touch = request.headers.get("user-agent", "") or ""
        except Exception:
            ua_touch = ""
        if _lean_is_facebook_crawler_ua(ua_touch):
            conn_q = None
            try:
                conn_q = get_db_connection()
                cur_q = conn_q.cursor()
                _lean_quarantine_ip(cur_q, ip, "facebook_crawler_ua")
                conn_q.commit()
            except Exception:
                try:
                    if conn_q:
                        conn_q.rollback()
                except Exception:
                    pass
            finally:
                if conn_q:
                    try:
                        return_db_connection(conn_q)
                    except Exception:
                        pass
            return None
        if _lean_is_crawler_cloud_ip(ip):
            conn_q = None
            try:
                conn_q = get_db_connection()
                cur_q = conn_q.cursor()
                _lean_quarantine_ip(cur_q, ip, "crawler_cloud_ip")
                conn_q.commit()
            except Exception:
                try:
                    if conn_q:
                        conn_q.rollback()
                except Exception:
                    pass
            finally:
                if conn_q:
                    try:
                        return_db_connection(conn_q)
                    except Exception:
                        pass
            return None
    except Exception:
        pass
''',
    "touch fb-ua vs human",
)

# 4) Remove Meta prefixes from unified bot_prefix_sql (keep AWS/Azure/Alibaba/Google nets)
old_prefix = '''    bot_prefix_sql = """
        AND ip_address NOT LIKE '173.252.%'
        AND ip_address NOT LIKE '69.63.%'
        AND ip_address NOT LIKE '69.171.%'
        AND ip_address NOT LIKE '31.13.%'
        AND ip_address NOT LIKE '66.220.%'
        AND ip_address NOT LIKE '157.240.%'
        AND ip_address NOT LIKE '185.60.%'
        AND ip_address NOT LIKE '3.%'
        AND ip_address NOT LIKE '13.%'
        AND ip_address NOT LIKE '16.%'
        AND ip_address NOT LIKE '18.%'
        AND ip_address NOT LIKE '20.%'
        AND ip_address NOT LIKE '34.%'
        AND ip_address NOT LIKE '35.%'
        AND ip_address NOT LIKE '44.%'
        AND ip_address NOT LIKE '47.7%'
        AND ip_address NOT LIKE '47.8%'
        AND ip_address NOT LIKE '47.9%'
        AND ip_address NOT LIKE '52.%'
        AND ip_address NOT LIKE '54.%'
    """
'''

new_prefix = '''    # Do NOT exclude Meta IPs here — FB in-app humans share those ranges.
    bot_prefix_sql = """
        AND ip_address NOT LIKE '3.%'
        AND ip_address NOT LIKE '13.%'
        AND ip_address NOT LIKE '16.%'
        AND ip_address NOT LIKE '18.%'
        AND ip_address NOT LIKE '20.%'
        AND ip_address NOT LIKE '34.%'
        AND ip_address NOT LIKE '35.%'
        AND ip_address NOT LIKE '44.%'
        AND ip_address NOT LIKE '47.7%'
        AND ip_address NOT LIKE '47.8%'
        AND ip_address NOT LIKE '47.9%'
        AND ip_address NOT LIKE '52.%'
        AND ip_address NOT LIKE '54.%'
        AND ip_address NOT LIKE '66.249.%'
        AND ip_address NOT LIKE '64.233.%'
    """
'''

rep(old_prefix, new_prefix, "unified allow meta humans")

# 5) real_ip SQL: scroll|click but exclude search-without-scroll fakes
old_real = '''    real_ip_sql = f"""
        AND ip_address IN (
          SELECT DISTINCT he.ip_address
          FROM public.public_page_hits he
          WHERE he.engagement ~* 'scroll|click'
            AND he.ip_address IS NOT NULL AND TRIM(he.ip_address) <> ''
            {since_clause_eng}
        )
    """
'''

new_real = '''    # Real = scrolled, or clicked without search-fake (Meta preview bots fake searched+clicked).
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

rep(old_real, new_real, "real_ip scroll-or-clean-click")

# 6) offline_fb: only link-preview crawls (Meta IP without real scroll), not FB in-app humans
old_fb = '''                try:
                    if not _lean_is_facebook_crawler_ip(ip):
                        continue
                except Exception:
                    continue
                offline_fb.append(
'''

new_fb = '''                try:
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
                    pass
                offline_fb.append(
'''

rep(old_fb, new_fb, "fb confirm skip in-app humans")

# 7) UI note
old_note = "Confirmation when you post a link — Meta fetched that URL. Not real visitors."
new_note = "Link-preview crawls when you post (not people browsing inside Facebook). FB in-app humans count as real."
if old_note in text:
    text = text.replace(old_note, new_note, 1)
    print("OK ui note")

if text == orig:
    sys.exit("NO CHANGE")

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
