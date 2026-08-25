"""
Site traffic: real human visits (source + journey events).
Table: public.site_traffic_events. Used only by /api/traffic/* and /admin/api/analytics-traffic.
Does not touch user_sessions or analytics_events.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlparse

SITE_TRAFFIC_DDL = """
CREATE TABLE IF NOT EXISTS public.site_traffic_events (
  id              bigserial PRIMARY KEY,
  visitor_id      text NOT NULL,
  visit_id        text NOT NULL,
  event_type      text NOT NULL,
  path            text,
  referrer        text,
  source_channel  text,
  utm_source      text,
  utm_medium      text,
  utm_campaign    text,
  scroll_pct      integer,
  click_text      text,
  click_href      text,
  click_selector  text,
  duration_ms     integer,
  page_visible_ms integer,
  is_bot          boolean NOT NULL DEFAULT false,
  ip_address      text,
  user_agent      text,
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_site_traffic_created
  ON public.site_traffic_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_site_traffic_visit
  ON public.site_traffic_events (visit_id, created_at);
CREATE INDEX IF NOT EXISTS idx_site_traffic_human_type_created
  ON public.site_traffic_events (created_at DESC)
  WHERE is_bot = false;
CREATE INDEX IF NOT EXISTS idx_site_traffic_source_created
  ON public.site_traffic_events (source_channel, created_at DESC)
  WHERE is_bot = false AND event_type = 'visit_start';
"""

ALLOWED_EVENT_TYPES = frozenset({
    "visit_start",
    "page_view",
    "heartbeat",
    "scroll",
    "click",
    "page_leave",
    "inactive",
    "exit",
})

# Known self-declaring bots (GA4/IAB-style). Avoid broad tokens that hit real browsers
# (e.g. bare "whatsapp", "preview", "java/" false-positive humans).
_BOT_UA_RE = re.compile(
    r"("
    r"googlebot|bingbot|yandexbot|baiduspider|duckduckbot|slurp|"
    r"facebookexternalhit|linkedinbot|twitterbot|discordbot|telegrambot|"
    r"applebot|amazonbot|petalbot|bytespider|semrushbot|ahrefsbot|dotbot|mj12bot|"
    r"gptbot|chatgpt-user|claudebot|anthropic-ai|perplexitybot|ccbot|"
    r"dataforseobot|serpstatbot|screaming frog|"
    r"uptimerobot|pingdom|statuscake|"
    r"headlesschrome|phantomjs|selenium|puppeteer|playwright|"
    r"python-requests|curl/|wget/|scrapy|go-http-client|libwww-perl|"
    r"okhttp|node-fetch|undici|"
    r"\bbot\b|\bcrawl\b|\bspider\b"
    r")",
    re.I,
)

_SOCIAL_HOST_RE = re.compile(
    r"(^|\.)(facebook\.com|fb\.com|instagram\.com|t\.co|twitter\.com|x\.com|"
    r"linkedin\.com|lnkd\.in|tiktok\.com|youtube\.com|youtu\.be|"
    r"whatsapp\.com|wa\.me|telegram\.org|t\.me|reddit\.com|pinterest\.com)$",
    re.I,
)

_GOOGLE_HOST_RE = re.compile(
    r"(^|\.)(google\.[a-z.]+|googleusercontent\.com|googlesyndication\.com)$",
    re.I,
)


def is_bot_user_agent(ua: Optional[str]) -> bool:
    if not ua or not str(ua).strip():
        return True
    return bool(_BOT_UA_RE.search(str(ua)))


def event_marks_bot(raw: dict, ua: str) -> bool:
    """Known-bot UA (GA4/IAB-style) plus client automation signals."""
    if is_bot_user_agent(ua):
        return True
    if not isinstance(raw, dict):
        return False
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    if meta.get("webdriver") is True or raw.get("webdriver") is True:
        return True
    if meta.get("automation") is True or meta.get("headless") is True:
        return True
    return False


def _host(url_or_host: Optional[str]) -> str:
    if not url_or_host:
        return ""
    s = str(url_or_host).strip()
    if not s:
        return ""
    try:
        if "://" in s:
            return (urlparse(s).hostname or "").lower()
        return s.split("/")[0].split(":")[0].lower()
    except Exception:
        return ""


def classify_source_channel(
    referrer: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    landing_host: Optional[str] = None,
) -> str:
    """Return direct | google | social | referral | other."""
    medium = (utm_medium or "").strip().lower()
    source = (utm_source or "").strip().lower()
    if medium in ("cpc", "ppc", "paidsearch") or source in ("google", "googleads", "adwords"):
        return "google"
    if medium in ("social", "social-media") or source in (
        "facebook", "fb", "instagram", "ig", "twitter", "x", "linkedin", "tiktok", "youtube",
    ):
        return "social"
    if medium in ("email", "sms"):
        return "other"
    ref_host = _host(referrer)
    site_host = (landing_host or "").lower().split(":")[0]
    if ref_host and site_host and (ref_host == site_host or ref_host.endswith("." + site_host)):
        return "direct"
    if ref_host and _GOOGLE_HOST_RE.search(ref_host):
        return "google"
    if ref_host and _SOCIAL_HOST_RE.search(ref_host):
        return "social"
    if not ref_host:
        return "direct"
    return "referral"


def ensure_site_traffic_table(cur) -> None:
    cur.execute(SITE_TRAFFIC_DDL)


def _clip(val: Any, n: int) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    return s[:n]


def normalize_event(raw: dict, *, ip: str, ua: str, is_bot: bool, site_host: str) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    et = (raw.get("event_type") or "").strip()
    if et not in ALLOWED_EVENT_TYPES:
        return None
    visitor_id = _clip(raw.get("visitor_id"), 80)
    visit_id = _clip(raw.get("visit_id"), 80)
    if not visitor_id or not visit_id:
        return None
    path = _clip(raw.get("path"), 500) or "/"
    if not path.startswith("/"):
        path = "/" + path
    referrer = _clip(raw.get("referrer"), 800)
    utm_source = _clip(raw.get("utm_source"), 120)
    utm_medium = _clip(raw.get("utm_medium"), 120)
    utm_campaign = _clip(raw.get("utm_campaign"), 180)
    source = _clip(raw.get("source_channel"), 40)
    if not source or source not in ("direct", "google", "social", "referral", "other"):
        source = classify_source_channel(referrer, utm_source, utm_medium, site_host)
    scroll_pct = raw.get("scroll_pct")
    try:
        scroll_pct = int(scroll_pct) if scroll_pct is not None else None
        if scroll_pct is not None:
            scroll_pct = max(0, min(100, scroll_pct))
    except (TypeError, ValueError):
        scroll_pct = None
    duration_ms = raw.get("duration_ms")
    page_visible_ms = raw.get("page_visible_ms")
    try:
        duration_ms = int(duration_ms) if duration_ms is not None else None
        if duration_ms is not None:
            duration_ms = max(0, min(duration_ms, 86_400_000))
    except (TypeError, ValueError):
        duration_ms = None
    try:
        page_visible_ms = int(page_visible_ms) if page_visible_ms is not None else None
        if page_visible_ms is not None:
            page_visible_ms = max(0, min(page_visible_ms, 86_400_000))
    except (TypeError, ValueError):
        page_visible_ms = None
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    bot = bool(is_bot) or event_marks_bot(raw, ua)
    return {
        "visitor_id": visitor_id,
        "visit_id": visit_id,
        "event_type": et,
        "path": path,
        "referrer": referrer,
        "source_channel": source,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "scroll_pct": scroll_pct,
        "click_text": _clip(raw.get("click_text"), 200),
        "click_href": _clip(raw.get("click_href"), 800),
        "click_selector": _clip(raw.get("click_selector"), 200),
        "duration_ms": duration_ms,
        "page_visible_ms": page_visible_ms,
        "is_bot": bot,
        "ip_address": _clip(ip, 80),
        "user_agent": _clip(ua, 500),
        "metadata": meta,
    }


def insert_traffic_events(cur, events: list) -> int:
    if not events:
        return 0
    try:
        from psycopg2.extras import Json
    except ImportError:
        Json = None  # type: ignore
    sql = """
        INSERT INTO public.site_traffic_events (
          visitor_id, visit_id, event_type, path, referrer, source_channel,
          utm_source, utm_medium, utm_campaign, scroll_pct, click_text, click_href,
          click_selector, duration_ms, page_visible_ms, is_bot, ip_address, user_agent, metadata
        ) VALUES (
          %(visitor_id)s, %(visit_id)s, %(event_type)s, %(path)s, %(referrer)s, %(source_channel)s,
          %(utm_source)s, %(utm_medium)s, %(utm_campaign)s, %(scroll_pct)s, %(click_text)s, %(click_href)s,
          %(click_selector)s, %(duration_ms)s, %(page_visible_ms)s, %(is_bot)s, %(ip_address)s, %(user_agent)s, %(metadata)s
        )
    """
    n = 0
    for ev in events:
        row = dict(ev)
        meta = row.get("metadata") or {}
        row["metadata"] = Json(meta) if Json is not None else json.dumps(meta)
        cur.execute(sql, row)
        n += 1
    return n


def _window_stats(cur, interval_literal: str, limit: int) -> dict:
    cur.execute(
        """
        SELECT COUNT(DISTINCT visit_id)::int AS visits
        FROM public.site_traffic_events
        WHERE is_bot = false AND event_type = 'visit_start'
          AND created_at >= NOW() - INTERVAL %s
        """,
        (interval_literal,),
    )
    visits = int((cur.fetchone() or {}).get("visits") or 0)

    # Engaged humans (GA4-like): scroll, click, or visible ≥10s on any event in visit
    cur.execute(
        """
        SELECT COUNT(DISTINCT visit_id)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false
          AND created_at >= NOW() - INTERVAL %s
          AND (
            event_type IN ('scroll', 'click')
            OR COALESCE(page_visible_ms, 0) >= 10000
            OR COALESCE(scroll_pct, 0) >= 25
          )
        """,
        (interval_literal,),
    )
    engaged = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COUNT(DISTINCT visit_id)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = true AND event_type = 'visit_start'
          AND created_at >= NOW() - INTERVAL %s
        """,
        (interval_literal,),
    )
    quarantined = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COALESCE(source_channel, 'other') AS source_channel, COUNT(DISTINCT visit_id)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false AND event_type = 'visit_start'
          AND created_at >= NOW() - INTERVAL %s
        GROUP BY 1
        ORDER BY n DESC
        """,
        (interval_literal,),
    )
    by_source = [{"source": r["source_channel"], "count": int(r["n"])} for r in (cur.fetchall() or [])]

    cur.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(path), ''), '/') AS path, COUNT(*)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false AND event_type = 'page_view'
          AND created_at >= NOW() - INTERVAL %s
        GROUP BY 1
        ORDER BY n DESC
        LIMIT %s
        """,
        (interval_literal, limit),
    )
    top_pages = [{"path": r["path"], "count": int(r["n"])} for r in (cur.fetchall() or [])]

    cur.execute(
        """
        SELECT COUNT(*)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false AND event_type = 'page_view'
          AND created_at >= NOW() - INTERVAL %s
        """,
        (interval_literal,),
    )
    page_views = int((cur.fetchone() or {}).get("n") or 0)

    return {
        "human_visits": visits,
        "engaged_visits": engaged,
        "quarantined_bot_visits": quarantined,
        "page_view_count": page_views,
        "by_source": by_source,
        "top_pages": top_pages,
    }


def _realtime_block(cur) -> dict:
    """Realtime human view + quarantine (Google excludes bots from main reports; we show both)."""
    out = {
        "active_now": 0,
        "humans_1m": 0,
        "humans_5m": 0,
        "humans_15m": 0,
        "engaged_15m": 0,
        "quarantined_bots_15m": 0,
        "by_source_15m": [],
        "top_pages_15m": [],
    }
    for key, iv in (("humans_1m", "1 minute"), ("humans_5m", "5 minutes"), ("humans_15m", "15 minutes")):
        cur.execute(
            """
            SELECT COUNT(DISTINCT visit_id)::int AS n
            FROM public.site_traffic_events
            WHERE is_bot = false AND event_type IN ('visit_start', 'page_view', 'heartbeat', 'scroll', 'click')
              AND created_at >= NOW() - INTERVAL %s
            """,
            (iv,),
        )
        out[key] = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COUNT(DISTINCT visit_id)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false
          AND created_at >= NOW() - INTERVAL '15 minutes'
          AND (
            event_type IN ('scroll', 'click')
            OR COALESCE(page_visible_ms, 0) >= 10000
            OR COALESCE(scroll_pct, 0) >= 25
          )
        """
    )
    out["engaged_15m"] = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COUNT(DISTINCT visit_id)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = true
          AND created_at >= NOW() - INTERVAL '15 minutes'
        """
    )
    out["quarantined_bots_15m"] = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COALESCE(source_channel, 'other') AS source_channel, COUNT(DISTINCT visit_id)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false AND event_type = 'visit_start'
          AND created_at >= NOW() - INTERVAL '15 minutes'
        GROUP BY 1
        ORDER BY n DESC
        """
    )
    out["by_source_15m"] = [{"source": r["source_channel"], "count": int(r["n"])} for r in (cur.fetchall() or [])]

    cur.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(path), ''), '/') AS path, COUNT(*)::int AS n
        FROM public.site_traffic_events
        WHERE is_bot = false AND event_type = 'page_view'
          AND created_at >= NOW() - INTERVAL '15 minutes'
        GROUP BY 1
        ORDER BY n DESC
        LIMIT 8
        """
    )
    out["top_pages_15m"] = [{"path": r["path"], "count": int(r["n"])} for r in (cur.fetchall() or [])]

    cur.execute(
        """
        WITH recent AS (
          SELECT DISTINCT ON (visit_id)
            visit_id, event_type, created_at
          FROM public.site_traffic_events
          WHERE is_bot = false
            AND created_at >= NOW() - INTERVAL '5 minutes'
          ORDER BY visit_id, created_at DESC
        )
        SELECT COUNT(*)::int AS n FROM recent
        WHERE event_type NOT IN ('exit', 'inactive')
        """
    )
    out["active_now"] = int((cur.fetchone() or {}).get("n") or 0)
    return out


def admin_traffic_payload(cur, limit: int = 25) -> dict:
    by_window = {}
    for key, iv in (("24h", "1 day"), ("7d", "7 days"), ("30d", "30 days")):
        by_window[key] = _window_stats(cur, iv, limit)

    realtime = _realtime_block(cur)

    # Active human visits: last event in 5 minutes, not exited/inactive
    cur.execute(
        """
        WITH recent AS (
          SELECT DISTINCT ON (visit_id)
            visit_id, visitor_id, path, source_channel, event_type, created_at, ip_address
          FROM public.site_traffic_events
          WHERE is_bot = false
            AND created_at >= NOW() - INTERVAL '5 minutes'
          ORDER BY visit_id, created_at DESC
        )
        SELECT * FROM recent
        WHERE event_type NOT IN ('exit', 'inactive')
        ORDER BY created_at DESC
        LIMIT 25
        """
    )
    active = []
    for r in cur.fetchall() or []:
        active.append({
            "visit_id": r.get("visit_id"),
            "visitor_id": r.get("visitor_id"),
            "path": r.get("path") or "/",
            "source_channel": r.get("source_channel") or "other",
            "last_event": r.get("event_type"),
            "last_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "ip_address": r.get("ip_address") or "",
        })

    total = sum(w["human_visits"] for w in by_window.values())

    # Quarantine review queue (possible false bots): recent is_bot rows for admin release
    cur.execute(
        """
        SELECT DISTINCT ON (visit_id)
          visit_id, visitor_id, path, source_channel, event_type, created_at, ip_address,
          left(user_agent, 120) AS user_agent
        FROM public.site_traffic_events
        WHERE is_bot = true
          AND created_at >= NOW() - INTERVAL '7 days'
        ORDER BY visit_id, created_at DESC
        LIMIT 50
        """
    )
    quarantine = []
    for r in cur.fetchall() or []:
        quarantine.append({
            "visit_id": r.get("visit_id"),
            "visitor_id": r.get("visitor_id"),
            "path": r.get("path") or "/",
            "source_channel": r.get("source_channel") or "other",
            "last_event": r.get("event_type"),
            "last_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "ip_address": r.get("ip_address") or "",
            "user_agent": r.get("user_agent") or "",
        })

    return {
        "ok": True,
        "traffic_table": "site_traffic_events",
        "analytics_table_exists": True,
        "method": {
            "like_ga4": "Known-bot UA quarantine (IAB-style list + automation signals); bots excluded from human counts.",
            "like_gsc": "GSC is search clicks/impressions not site sessions; low GSC often = bots/scrapers removed from Search reports.",
            "engaged": "Engaged = scroll, click, or ≥10s visible time (GA4-style engagement proxy).",
            "realtime": "Active = human events in last 5m without exit/inactive.",
            "old_data": "user_sessions / analytics_events are NOT this table — nothing to bulk-release there. Only site_traffic_events uses is_bot.",
            "release": "POST /admin/api/traffic/release-human with visit_ids to set is_bot=false if a human was quarantined.",
        },
        "partial_data": total == 0 and realtime.get("active_now", 0) == 0,
        "partial_data_message": (
            "No human beacons yet — deploy site-traffic.js + nginx inject, then refresh."
            if total == 0 and realtime.get("active_now", 0) == 0
            else "Human traffic (quarantined bots shown separately). Not login sessions."
        ),
        "limit_applied": limit,
        "realtime": realtime,
        "by_window": by_window,
        "active_visits": active,
        "quarantine_review": quarantine,
    }


def release_visits_as_human(cur, visit_ids: list) -> int:
    """Mark visit_ids as human (is_bot=false). Returns rows updated."""
    ids = [str(v).strip() for v in (visit_ids or []) if str(v).strip()]
    if not ids:
        return 0
    cur.execute(
        """
        UPDATE public.site_traffic_events
        SET is_bot = false,
            metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('released_human', true, 'released_at', NOW()::text)
        WHERE visit_id = ANY(%s) AND is_bot = true
        """,
        (ids,),
    )
    return int(cur.rowcount or 0)
