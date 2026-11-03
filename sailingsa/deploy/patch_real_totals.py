#!/usr/bin/env python3
"""Overview/series/top maths = real visitors (scroll/click IPs) and their pages only."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old = '''def _lean_traffic_unified_sql(since_sql: Optional[str], *, pct_escape: bool = False):
    """Union page hits (post-cutover) with traffic_events (pre-cutover).
    Excludes dev URLs + super-admin (Kevin/Tim/agent) sessions. Visitors keyed by IP."""
    since_clause_hits = ""
    since_clause_te = ""
    if since_sql:
        since_clause_hits = f" AND occurred_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_te = f" AND occurred_at > NOW() - INTERVAL '{since_sql}'"
    path_hits = _lean_traffic_path_ok_sql("path", pct_escape=pct_escape)
    path_te = _lean_traffic_path_ok_sql("COALESCE(url_path, request_url)", pct_escape=pct_escape)
    return f"""
    SELECT path, occurred_at, visitor_key FROM (
      SELECT path, occurred_at,
             COALESCE(NULLIF(TRIM(ip_address::text), ''), visitor_id::text) AS visitor_key
      FROM public.public_page_hits
      WHERE path IS NOT NULL AND TRIM(path) <> ''
        AND occurred_at >= TIMESTAMPTZ '{_LEAN_TRAFFIC_CUTOVER}'
        {since_clause_hits}
        {path_hits}
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_STAFF_IP_SQL})
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
      UNION ALL
      SELECT COALESCE(url_path, request_url) AS path, occurred_at,
             COALESCE(NULLIF(TRIM(ip_hash::text), ''), visitor_id::text) AS visitor_key
      FROM public.traffic_events
      WHERE occurred_at < TIMESTAMPTZ '{_LEAN_TRAFFIC_CUTOVER}'
        {since_clause_te}
        AND COALESCE(url_path, request_url) IS NOT NULL
        {path_te}
        AND (sas_id IS NULL OR sas_id::text NOT IN {_LEAN_TRAFFIC_STAFF_SAS_SQL})
    ) u
    """
'''

new = '''def _lean_traffic_unified_sql(since_sql: Optional[str], *, pct_escape: bool = False):
    """Union page hits (post-cutover) with traffic_events (pre-cutover).

    Totals = REAL only: IPs that scrolled/clicked in-range (plus their page trail).
    Excludes staff, quarantine, Meta/cloud crawler prefixes. Visitors keyed by IP.
    """
    since_clause_hits = ""
    since_clause_te = ""
    since_clause_eng = ""
    if since_sql:
        since_clause_hits = f" AND occurred_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_te = f" AND occurred_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_eng = f" AND he.occurred_at > NOW() - INTERVAL '{since_sql}'"
    path_hits = _lean_traffic_path_ok_sql("path", pct_escape=pct_escape)
    path_te = _lean_traffic_path_ok_sql("COALESCE(url_path, request_url)", pct_escape=pct_escape)
    # Meta + common cloud scrapers — never count as real visitors/hits
    bot_prefix_sql = """
        AND ip_address NOT LIKE '173.252.%%'
        AND ip_address NOT LIKE '69.63.%%'
        AND ip_address NOT LIKE '69.171.%%'
        AND ip_address NOT LIKE '31.13.%%'
        AND ip_address NOT LIKE '66.220.%%'
        AND ip_address NOT LIKE '157.240.%%'
        AND ip_address NOT LIKE '185.60.%%'
        AND ip_address NOT LIKE '3.%%'
        AND ip_address NOT LIKE '13.%%'
        AND ip_address NOT LIKE '16.%%'
        AND ip_address NOT LIKE '18.%%'
        AND ip_address NOT LIKE '20.%%'
        AND ip_address NOT LIKE '34.%%'
        AND ip_address NOT LIKE '35.%%'
        AND ip_address NOT LIKE '44.%%'
        AND ip_address NOT LIKE '47.7%%'
        AND ip_address NOT LIKE '47.8%%'
        AND ip_address NOT LIKE '47.9%%'
        AND ip_address NOT LIKE '52.%%'
        AND ip_address NOT LIKE '54.%%'
    """.replace("%%", "%%%%" if pct_escape else "%%")
    # Note: in f-string below we need %% for LIKE when passed through — use single % in final SQL
    bot_prefix_sql = """
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
    if pct_escape:
        bot_prefix_sql = bot_prefix_sql.replace("%", "%%")
    real_ip_sql = f"""
        AND ip_address IN (
          SELECT DISTINCT he.ip_address
          FROM public.public_page_hits he
          WHERE he.engagement ~* 'scroll|click'
            AND he.ip_address IS NOT NULL AND TRIM(he.ip_address) <> ''
            {since_clause_eng}
        )
    """
    return f"""
    SELECT path, occurred_at, visitor_key FROM (
      SELECT path, occurred_at,
             COALESCE(NULLIF(TRIM(ip_address::text), ''), visitor_id::text) AS visitor_key
      FROM public.public_page_hits
      WHERE path IS NOT NULL AND TRIM(path) <> ''
        AND occurred_at >= TIMESTAMPTZ '{_LEAN_TRAFFIC_CUTOVER}'
        {since_clause_hits}
        {path_hits}
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_STAFF_IP_SQL})
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
        {real_ip_sql}
        {bot_prefix_sql}
      UNION ALL
      SELECT COALESCE(url_path, request_url) AS path, occurred_at,
             COALESCE(NULLIF(TRIM(ip_hash::text), ''), visitor_id::text) AS visitor_key
      FROM public.traffic_events
      WHERE occurred_at < TIMESTAMPTZ '{_LEAN_TRAFFIC_CUTOVER}'
        {since_clause_te}
        AND COALESCE(url_path, request_url) IS NOT NULL
        {path_te}
        AND (sas_id IS NULL OR sas_id::text NOT IN {_LEAN_TRAFFIC_STAFF_SAS_SQL})
        AND false
    ) u
    """
'''

# Pre-cutover disabled with AND false for real-only era (post Aug 13) — cleaner maths.
# Actually for "Ever" and old data, disabling traffic_events might zero historical. Better keep TE without engagement filter for pre-cutover only when range includes pre-cutover.

# Fix: only apply real_ip to public_page_hits; keep traffic_events for pre-cutover history without real filter (or exclude TE entirely for consistency).

# Rewrite new without AND false - restore TE union for ever/old ranges
new = '''def _lean_traffic_unified_sql(since_sql: Optional[str], *, pct_escape: bool = False):
    """Stats continuum for traffic dash.

    Post-cutover hits: REAL only — IP must have scroll/click in-range; exclude staff,
    quarantine, Meta/cloud prefixes. Page hits = full trail for those IPs.
    Pre-cutover traffic_events kept for long-range history only.
    """
    since_clause_hits = ""
    since_clause_te = ""
    since_clause_eng = ""
    if since_sql:
        since_clause_hits = f" AND occurred_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_te = f" AND occurred_at > NOW() - INTERVAL '{since_sql}'"
        since_clause_eng = f" AND he.occurred_at > NOW() - INTERVAL '{since_sql}'"
    path_hits = _lean_traffic_path_ok_sql("path", pct_escape=pct_escape)
    path_te = _lean_traffic_path_ok_sql("COALESCE(url_path, request_url)", pct_escape=pct_escape)
    bot_prefix_sql = """
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
    if pct_escape:
        bot_prefix_sql = bot_prefix_sql.replace("%", "%%")
    real_ip_sql = f"""
        AND ip_address IN (
          SELECT DISTINCT he.ip_address
          FROM public.public_page_hits he
          WHERE he.engagement ~* 'scroll|click'
            AND he.ip_address IS NOT NULL AND TRIM(he.ip_address) <> ''
            {since_clause_eng}
        )
    """
    return f"""
    SELECT path, occurred_at, visitor_key FROM (
      SELECT path, occurred_at,
             COALESCE(NULLIF(TRIM(ip_address::text), ''), visitor_id::text) AS visitor_key
      FROM public.public_page_hits
      WHERE path IS NOT NULL AND TRIM(path) <> ''
        AND occurred_at >= TIMESTAMPTZ '{_LEAN_TRAFFIC_CUTOVER}'
        {since_clause_hits}
        {path_hits}
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_STAFF_IP_SQL})
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
        {real_ip_sql}
        {bot_prefix_sql}
      UNION ALL
      SELECT COALESCE(url_path, request_url) AS path, occurred_at,
             COALESCE(NULLIF(TRIM(ip_hash::text), ''), visitor_id::text) AS visitor_key
      FROM public.traffic_events
      WHERE occurred_at < TIMESTAMPTZ '{_LEAN_TRAFFIC_CUTOVER}'
        {since_clause_te}
        AND COALESCE(url_path, request_url) IS NOT NULL
        {path_te}
        AND (sas_id IS NULL OR sas_id::text NOT IN {_LEAN_TRAFFIC_STAFF_SAS_SQL})
    ) u
    """
'''

if old not in text:
    print("FAIL old unified", file=sys.stderr)
    i = text.find("def _lean_traffic_unified_sql")
    print(repr(text[i:i+400]))
    sys.exit(1)

text = text.replace(old, new, 1)
print("OK unified real-only")

# Update blurb on page
old_blurb = "Visitors = unique IPs."
new_blurb = "Visitors = unique real IPs (scroll/click). Page hits = their pages only."
if old_blurb in text:
    text = text.replace(old_blurb, new_blurb, 1)
    print("OK blurb")
else:
    # try longer blurb
    for s in ["Visitors = unique IPs", "unique IPs."]:
        if s in text:
            print("found", s)

# Also fix note about cloud quarantined
old2 = "Cloud/bot IPs quarantined (excluded from Hits/Vis)."
new2 = "Totals = real only (scroll/click). Bots quarantined / excluded."
if old2 in text:
    text = text.replace(old2, new2, 1)
    print("OK blurb2")

if text == orig:
    sys.exit("NO CHANGE")

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
