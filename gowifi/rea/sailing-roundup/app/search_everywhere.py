#!/usr/bin/env python3
"""Search the public web for one event: Google, Facebook, TikTok, YouTube, Instagram, X, news.

Every hit is later verified against the event URL and results. No login bypass.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Public indexes we can query without platform login.
EVERYWHERE = (
    ("web", None),
    ("news", None),
    ("facebook", "facebook.com"),
    ("instagram", "instagram.com"),
    ("tiktok", "tiktok.com"),
    ("youtube", "youtube.com"),
    ("x", "x.com"),
    ("reddit", "reddit.com"),
)


def _get(url: str, timeout: int = 18) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_day(value) -> dt.date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    iso = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if iso:
        try:
            return dt.date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass
    words = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2})", raw)
    if words:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return dt.datetime.strptime(words.group(1), fmt).date()
            except ValueError:
                continue
    return None


def coverage_window(event: dict, after_days: int = 14, before_days: int = 2) -> tuple[dt.date | None, dt.date | None]:
    """Keep coverage from two days before the start through two weeks after the finish."""
    start = parse_day(event.get("start") or event.get("start_date"))
    end = parse_day(event.get("end") or event.get("end_date")) or start
    if not start:
        return None, None
    return start - dt.timedelta(days=before_days), end + dt.timedelta(days=after_days)


def date_span_words(event: dict) -> str:
    start = parse_day(event.get("start") or event.get("start_date"))
    end = parse_day(event.get("end") or event.get("end_date")) or start
    if not start:
        return ""
    if start == end:
        return start.strftime("%-d %B %Y")
    if start.month == end.month:
        return f"{start.day}–{end.day} {end.strftime('%B %Y')}"
    return f"{start.strftime('%-d %B')}–{end.strftime('%-d %B %Y')}"


def published_on(item: dict) -> dt.date | None:
    for key in ("published", "published_at", "pubDate", "date", "created_at"):
        day = parse_day(item.get(key))
        if day:
            return day
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("url", "source_url", "title", "description", "snippet")
    )
    match = re.search(r"(20\d{2})[-/](\d{2})[-/](\d{2})", blob)
    if match:
        try:
            return dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def in_coverage_window(item: dict, event: dict) -> bool | None:
    """True = posted during/just after the event. False = too old/too late. None = date unknown."""
    if is_official_sailingsa(item, event):
        return True
    lo, hi = coverage_window(event)
    day = published_on(item)
    if not lo or not day:
        return None
    return lo <= day <= hi


def event_year_month(event: dict) -> tuple[str, str]:
    start = parse_day(
        event.get("start")
        or event.get("start_date")
        or event.get("id")
        or event.get("slug")
        or event.get("regatta_id")
        or ""
    )
    if not start:
        return "", ""
    return str(start.year), start.strftime("%B %Y")


def event_slug(event: dict) -> str:
    slug = (event.get("slug") or event.get("id") or event.get("regatta_id") or "").strip()
    if slug:
        return slug
    url = event.get("event_url") or event.get("url") or ""
    if "/regatta/" in url:
        return url.rstrip("/").split("/")[-1]
    return ""


def official_sailingsa_sources(event: dict) -> list[dict]:
    """The SAS-sanctioned card already on SailingSA by Monday. Direct access, not a scrape."""
    slug = event_slug(event)
    title = (event.get("title") or event.get("event_name") or slug).strip()
    club = (event.get("club") or "").strip()
    club_name = (event.get("club_name") or club).strip()
    club_slug = (event.get("host_club_slug") or club).strip().lower()
    klass = (event.get("class_name") or "").strip()
    class_slug = klass.lower().replace(" ", "-")
    end = event.get("end") or event.get("end_date") or ""
    out = []
    if slug:
        out.append(
            {
                "url": "https://sailingsa.co.za/regatta/" + slug,
                "title": f"{title} — SailingSA results",
                "description": f"Official SAS-sanctioned {title} results on SailingSA.",
                "engine": "sailingsa",
                "role": "official_results",
                "published": end,
            }
        )
    if club_slug:
        out.append(
            {
                "url": "https://sailingsa.co.za/club/" + club_slug,
                "title": f"{club_name} — SailingSA club",
                "description": f"Host club record for {title}.",
                "engine": "sailingsa",
                "role": "official_club",
            }
        )
    if class_slug:
        out.append(
            {
                "url": "https://sailingsa.co.za/class/" + class_slug,
                "title": f"{klass} — SailingSA class",
                "description": f"Class record for {title}.",
                "engine": "sailingsa",
                "role": "official_class",
            }
        )
    return out


def is_official_sailingsa(item: dict, event: dict) -> bool:
    url = (item.get("url") or item.get("source_url") or "").lower()
    slug = event_slug(event).lower()
    return bool(slug and "sailingsa.co.za" in url and slug in url)


def event_query(event: dict) -> str:
    club = event.get("club") or ""
    club_name = event.get("club_name") or club
    parts = [
        event.get("title") or event.get("event_name") or "",
        club_name,
        date_span_words(event),
        "sailing",
    ]
    return " ".join(p for p in parts if p).strip()


def google_after_before(event: dict) -> str:
    lo, hi = coverage_window(event)
    if not lo or not hi:
        return ""
    return f"after:{lo.isoformat()} before:{(hi + dt.timedelta(days=1)).isoformat()}"


def discovery_queries(event: dict) -> list[str]:
    """Search the event + year/month. Google should surface SailingSA, then everyone else."""
    title = (event.get("title") or event.get("event_name") or "").strip()
    klass = (event.get("class_name") or "").strip()
    club = (event.get("club_name") or event.get("club") or "").strip()
    dates = date_span_words(event)
    bounded = google_after_before(event)
    year, month = event_year_month(event)
    queries = [event_query(event)]
    klass_u = klass.upper()
    team_event = klass_u in {"TSL", "TEAM SAILING"} or "team sailing" in title.lower()
    if team_event:
        for name in (event.get("result_names") or event.get("names") or [])[:5]:
            if not name:
                continue
            queries.append(f'"{name}" team sailing {club} {year}'.strip())
            queries.append(f'site:facebook.com "{name}" TSL {year}'.strip())
            queries.append(f'site:instagram.com "{name}" team sailing {year}'.strip())
    if title and year:
        queries.append(f"{title} {year}")
        queries.append(f"{title} {year} SailingSA")
        queries.append(f"{title} {year} site:sailingsa.co.za")
    if title and month:
        queries.append(f"{title} {month}")
        queries.append(f"{title} {month} SailingSA")
    if title and dates:
        queries.append(f"{title} {dates}")
        if bounded:
            queries.append(f"{title} {bounded}")
    if klass:
        queries.append(f"{klass} RSA facebook group sailing")
        queries.append(f"{klass} South Africa facebook group")
        queries.append(f"site:facebook.com/groups {klass} SA sailing")
    if klass and dates:
        queries.append(f"{klass} {club} {dates} facebook")
        if bounded:
            queries.append(f"site:facebook.com {klass} {title} {bounded}")
    if title and club:
        queries.append(f"{title} {club} facebook {dates}")
    seen = []
    for q in queries:
        q = " ".join(q.split())
        if q and q not in seen:
            seen.append(q)
    return seen


def catalog_local_urls(event: dict) -> list[dict]:
    """Local class/club pages already in the directory — the first places to scrape."""
    out = []
    try:
        from event_social_verify import class_config_links
        from social_collect import club_config_links
    except Exception:
        return out
    slugs = event.get("class_slugs") or []
    klass = (event.get("class_name") or "").strip().lower().replace(" ", "-")
    if klass and klass not in slugs:
        slugs = list(slugs) + [klass]
    for item in class_config_links(slugs, local_only=True):
        if item.get("url"):
            out.append({**item, "engine": "class_catalog", "locality": "local"})
    club = event.get("club") or ""
    if club:
        try:
            for item in club_config_links(club):
                if item.get("url"):
                    out.append({**item, "engine": "club_catalog", "locality": "local"})
        except Exception:
            pass
    return out


def _decode_ddg(href: str) -> str:
    raw = urllib.parse.unquote(href.replace("&amp;", "&"))
    match = re.search(r"uddg=([^&]+)", raw)
    if match:
        return urllib.parse.unquote(match.group(1))
    if raw.startswith("http"):
        return raw
    return ""


def web_hits(query: str, limit: int = 8) -> list[dict]:
    """DuckDuckGo HTML is the public web index; Bing is a fallback."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    try:
        html = _get(url)
    except Exception as exc:
        return [{"engine": "ddg", "query": query, "error": str(exc)[:160]}]
    out = []
    for href, title in re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S
    ):
        link = _decode_ddg(href)
        text = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", title)).strip()
        if link.startswith("http") and text and not any(x.get("url") == link for x in out):
            out.append({"url": link, "title": text, "description": "", "engine": "ddg", "query": query})
        if len(out) >= limit:
            break
    if out:
        return out
    # fallback: Bing cites often show the real host even when hrefs are redirects
    try:
        html = _get("https://www.bing.com/search?q=" + urllib.parse.quote(query))
    except Exception as exc:
        return [{"engine": "bing", "query": query, "error": str(exc)[:160]}]
    for cite in re.findall(r"<cite[^>]*>(.*?)</cite>", html, re.I | re.S):
        host = re.sub("<[^>]+>", "", cite).replace(" › ", "/").strip()
        if host.startswith("http"):
            out.append({"url": host, "title": host, "description": "", "engine": "bing", "query": query})
        if len(out) >= limit:
            break
    return out


def google_news(query: str, limit: int = 8) -> list[dict]:
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-ZA&gl=ZA&ceid=ZA:en"
    try:
        raw = _get(url)
        root = ET.fromstring(raw)
    except Exception as exc:
        return [{"engine": "google_news", "query": query, "error": str(exc)[:160]}]
    out = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        if link:
            out.append(
                {
                    "url": link,
                    "title": title,
                    "description": item.findtext("description") or "",
                    "engine": "google_news",
                    "query": query,
                    "published": item.findtext("pubDate"),
                }
            )
        if len(out) >= limit:
            break
    return out


def socialcrawl_everywhere(query: str) -> list[dict]:
    key = os.getenv("SOCIALCRAWL_API_KEY")
    if not key:
        return [{"engine": "socialcrawl", "status": "needs_credentials"}]
    base = os.getenv("SOCIALCRAWL_BASE_URL", "https://www.socialcrawl.dev").rstrip("/")
    url = (
        base
        + "/v1/search/everywhere?"
        + urllib.parse.urlencode({"query": query, "lookback_days": 21})
    )
    req = urllib.request.Request(url, headers={**UA, "x-api-key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=70) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as exc:
        return [{"engine": "socialcrawl", "status": "error", "error": str(exc)[:160]}]
    items = data.get("data", {}).get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        items = data.get("items") if isinstance(data, dict) else []
    out = []
    for item in items or []:
        src = (item.get("source_items") or [{}])[0] if isinstance(item.get("source_items"), list) else item
        url = src.get("url") or item.get("url")
        if url:
            out.append(
                {
                    "url": url,
                    "title": src.get("title") or item.get("title") or "",
                    "description": src.get("text") or item.get("snippet") or "",
                    "engine": "socialcrawl",
                    "platform": src.get("platform") or item.get("platform"),
                }
            )
    return out


def search_everywhere(event: dict) -> dict:
    """Fan a single event query across web, news, and every major social host."""
    q = event_query(event)
    lanes = {}
    hits = []
    seen = set()

    def add(batch, lane):
        lanes.setdefault(lane, {"count": 0, "errors": []})
        for item in batch:
            if item.get("error") or item.get("status") == "needs_credentials":
                lanes[lane]["errors"].append(item)
                continue
            url = (item.get("url") or "").split("#")[0]
            if not url or url in seen:
                continue
            item["published"] = item.get("published") or (published_on(item).isoformat() if published_on(item) else "")
            item["in_window"] = in_coverage_window(item, event)
            if item["in_window"] is False and lane not in ("class_catalog", "club_catalog", "sailingsa"):
                continue
            seen.add(url)
            item["lane"] = lane
            hits.append(item)
            lanes[lane]["count"] += 1

    add(official_sailingsa_sources(event), "sailingsa")
    add(catalog_local_urls(event), "class_catalog")
    year, month = event_year_month(event)
    title = (event.get("title") or event.get("event_name") or "").strip()
    if title and year:
        add(web_hits(f"{title} {year} site:sailingsa.co.za", limit=8), "sailingsa")
        add(web_hits(f"{title} {year} SailingSA", limit=6), "sailingsa")
        add(google_news(f"{title} {year} SailingSA", limit=4), "sailingsa")
    if title and month:
        add(web_hits(f"{title} {month} site:sailingsa.co.za", limit=6), "sailingsa")
    for q2 in discovery_queries(event)[:10]:
        add(web_hits(q2, limit=6), "discover")
        add(google_news(q2, limit=4), "google_news")
    add(web_hits(q), "web")
    add(google_news(q + " SailingSA"), "google_news")
    for lane, host in EVERYWHERE:
        if not host:
            continue
        add(web_hits(f"site:{host} {q}", limit=6), lane)
    add(socialcrawl_everywhere(q), "socialcrawl_everywhere")

    # Host-club Facebook / website is the primary media source (Dart Nationals → HMYC, etc.).
    for source in event.get("host_source_urls") or []:
        parsed = urllib.parse.urlparse(source)
        host = (parsed.netloc + parsed.path).rstrip("/")
        if host:
            add(web_hits(f"site:{host} {q}", limit=8), "host_club_page")

    # Sailor-name queries catch club posts that omit the event title.
    for name in (event.get("result_names") or [])[:4]:
        add(web_hits(f'"{name}" {event.get("club") or ""} sailing {date_span_words(event)}', limit=5), "results_names")

    lo, hi = coverage_window(event)
    return {
        "query": q,
        "window": {"from": lo.isoformat() if lo else None, "to": hi.isoformat() if hi else None},
        "lanes": lanes,
        "hits": hits,
        "counts": {k: v["count"] for k, v in lanes.items()},
        "total": len(hits),
    }
