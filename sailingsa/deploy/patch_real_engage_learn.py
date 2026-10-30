#!/usr/bin/env python3
"""Learn from engaged humans: real = scrolled|clicked; searched-alone is fake; phones strong real."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# --- Replace _lean_trail_has_engagement to require scrolled/clicked ---
old_eng = '''def _lean_trail_has_engagement(page_trail: list) -> bool:
    """True if any stay recorded scrolled / searched / clicked."""
    for pt in page_trail or []:
        if not isinstance(pt, dict):
            continue
        eng = pt.get("engagement") or []
        if isinstance(eng, str):
            eng = _lean_parse_engage_tokens(eng)
        if eng:
            return True
        lab = (pt.get("engagement_label") or "").strip()
        if lab:
            return True
    return False'''

new_eng = '''def _lean_tokens_are_real_human_engage(tokens) -> bool:
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


def _lean_ua_looks_phone(user_agent: str) -> bool:
    """Phone/tablet browsers — strong real-visitor tell vs desktop broadcast scrapers."""
    ua = (user_agent or "").lower()
    if not ua:
        return False
    if any(x in ua for x in ("iphone", "ipad", "ipod", "android", "mobile")):
        # Exclude obvious bot UAs that mention mobile
        if any(x in ua for x in ("bot", "crawl", "spider", "facebookexternal", "meta-external")):
            return False
        return True
    return False


def _lean_trail_has_engagement(page_trail: list) -> bool:
    """True if scrolled or clicked (learned from real/admin samples). searched-alone ≠ real."""
    for pt in page_trail or []:
        if not isinstance(pt, dict):
            continue
        eng = pt.get("engagement") or []
        if isinstance(eng, str):
            eng = _lean_parse_engage_tokens(eng)
        if _lean_tokens_are_real_human_engage(eng):
            return True
        lab = (pt.get("engagement_label") or "").strip().lower()
        if lab and ("scroll" in lab or "click" in lab or "tap" in lab):
            return True
    return False'''

if "_lean_tokens_are_real_human_engage" in text:
    print("SKIP engage helpers")
elif old_eng not in text:
    print("FAIL eng fn", file=sys.stderr)
    sys.exit(1)
else:
    text = text.replace(old_eng, new_eng, 1)
    print("OK real-engage definition")

# --- Expand cloud nets: Azure 20.x, AWS 16.x (seen sterile scrapers) ---
old_nets = '''                "3.0.0.0/8",
                "13.0.0.0/8",
                "15.0.0.0/10",
                "18.0.0.0/8",
                "34.0.0.0/8",
                "35.0.0.0/8",
                "44.0.0.0/8",  # Amazon AWS (EC2 etc.) — link scrapers on this site
                "50.16.0.0/14",  # AWS legacy
                "52.0.0.0/8",
                "54.0.0.0/8",'''

new_nets = '''                "3.0.0.0/8",
                "13.0.0.0/8",
                "15.0.0.0/10",
                "16.0.0.0/8",  # AWS
                "18.0.0.0/8",
                "20.0.0.0/8",  # Azure probes
                "34.0.0.0/8",
                "35.0.0.0/8",
                "44.0.0.0/8",  # Amazon AWS (EC2 etc.) — link scrapers on this site
                "50.16.0.0/14",  # AWS legacy
                "52.0.0.0/8",
                "54.0.0.0/8",'''

if '"16.0.0.0/8"' in text and '"20.0.0.0/8"' in text:
    print("SKIP nets expand")
elif old_nets not in text:
    # try without 44 comment variance
    print("WARN nets block mismatch — trying alt")
    alt = '''                "3.0.0.0/8",
                "13.0.0.0/8",
                "15.0.0.0/10",
                "18.0.0.0/8",'''
    if alt in text and '"16.0.0.0/8"' not in text:
        text = text.replace(
            alt,
            '''                "3.0.0.0/8",
                "13.0.0.0/8",
                "15.0.0.0/10",
                "16.0.0.0/8",  # AWS
                "18.0.0.0/8",
                "20.0.0.0/8",  # Azure probes
''',
            1,
        )
        print("OK nets via alt")
    else:
        print("FAIL nets", file=sys.stderr)
        sys.exit(2)
else:
    text = text.replace(old_nets, new_nets, 1)
    print("OK nets expand")

# Reset cloud nets cache on load - the cache is module-level; restart clears it.

# --- Strengthen classify: fake searched-only → quarantine; phone+real engage never sterile ---
old_class = '''def _lean_classify_sterile_no_engage(cur, *, ip: str, visitor_id: str = "") -> bool:
    """Mark bot when short trail (<=5 pages) and still no scroll/click after grace.

    Returns True when quarantined / classified bot.
    """
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        if _lean_is_crawler_cloud_ip(ip):
            _lean_quarantine_ip(cur, ip, "crawler_cloud_ip")
            return True
    except Exception:
        pass
    try:
        if _lean_ip_is_quarantined(cur, ip):
            return True
    except Exception:
        pass
    # Any engagement on this IP recently → real enough, leave alone
    try:
        _lean_ensure_page_hit_engagement_column(cur)
        cur.execute(
            """
            SELECT engagement, path, occurred_at
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - interval '30 minutes'
            ORDER BY occurred_at ASC
            LIMIT 20
            """,
            (ip[:80],),
        )
        rows = cur.fetchall() or []
    except Exception:
        return False
    if not rows:
        return False
    trail = []
    first_at = None
    for row in rows:
        if isinstance(row, dict):
            eng = row.get("engagement")
            path = row.get("path") or "/"
            occurred = row.get("occurred_at")
        else:
            eng, path, occurred = row[0], row[1] or "/", row[2]
        if first_at is None:
            first_at = occurred
        trail.append({"path": path, "engagement": eng, "occurred_at": occurred})
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass'''

new_class = '''def _lean_classify_sterile_no_engage(cur, *, ip: str, visitor_id: str = "") -> bool:
    """Mark bot when short trail (<=5 pages) and still no scroll/click after grace.

    Learned: real/admin samples scroll|click (often phone). Bots ≤5 pages, no scroll/click,
    or fake searched-only tokens on cloud. Quarantine once → ignore forever (no more cost).

    Returns True when quarantined / classified bot.
    """
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        if _lean_is_crawler_cloud_ip(ip):
            _lean_quarantine_ip(cur, ip, "crawler_cloud_ip")
            return True
    except Exception:
        pass
    try:
        if _lean_ip_is_quarantined(cur, ip):
            return True
    except Exception:
        pass
    # Load recent trail + session UA (phone tell)
    ua = ""
    try:
        cur.execute(
            "SELECT COALESCE(user_agent,'') FROM public.public_sessions WHERE ip_address = %s LIMIT 1",
            (ip[:80],),
        )
        ur = cur.fetchone()
        if ur:
            ua = str(ur[0] if not isinstance(ur, dict) else next(iter(ur.values())) or "")
    except Exception:
        ua = ""
    try:
        _lean_ensure_page_hit_engagement_column(cur)
        cur.execute(
            """
            SELECT engagement, path, occurred_at
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - interval '30 minutes'
            ORDER BY occurred_at ASC
            LIMIT 20
            """,
            (ip[:80],),
        )
        rows = cur.fetchall() or []
    except Exception:
        return False
    if not rows:
        return False
    trail = []
    first_at = None
    all_tokens = []
    for row in rows:
        if isinstance(row, dict):
            eng = row.get("engagement")
            path = row.get("path") or "/"
            occurred = row.get("occurred_at")
        else:
            eng, path, occurred = row[0], row[1] or "/", row[2]
        if first_at is None:
            first_at = occurred
        trail.append({"path": path, "engagement": eng, "occurred_at": occurred})
        if eng:
            all_tokens.extend(_lean_parse_engage_tokens(eng) if not isinstance(eng, list) else eng)
    # Fake engage: searched without scroll/click → bot (seen on Meta/AWS)
    try:
        toks = {str(t).strip().lower() for t in all_tokens if t}
        if toks and not (toks & {"scrolled", "clicked"}) and ("searched" in toks):
            _lean_quarantine_ip(cur, ip, "fake_search_engage")
            return True
    except Exception:
        pass
    # Real scroll/click — phone especially: never sterile-quarantine
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    try:
        if _lean_ua_looks_phone(ua) and _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass'''

if "fake_search_engage" in text and "Learned: real/admin samples" in text:
    print("SKIP classify body")
elif old_class not in text:
    print("FAIL classify", file=sys.stderr)
    k = text.find("def _lean_classify_sterile_no_engage")
    print(repr(text[k:k+800]))
    sys.exit(3)
else:
    text = text.replace(old_class, new_class, 1)
    print("OK classify learned rules")

# --- On merge engagement: if only searched, don't treat as human (optional quarantine cloud) ---
# Find _lean_merge_open_hit_engagement end - add note via wrap at call sites is enough via trail_has_engagement

if text == orig:
    print("NO CHANGE", file=sys.stderr)
    sys.exit(4)

# Force cloud nets cache rebuild: null out if present after edit
# (_LEAN_CLOUD_NETS_CACHE = None at import; restart clears)

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
