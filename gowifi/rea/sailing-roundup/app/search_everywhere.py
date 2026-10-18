#!/usr/bin/env python3
"""Search the public web for one event: Google, Facebook, TikTok, YouTube, Instagram, X, news.

Every hit is later verified against the event URL and results. No login bypass.
"""
from __future__ import annotations

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


def event_query(event: dict) -> str:
    club = event.get("club") or ""
    club_name = event.get("club_name") or club
    parts = [
        event.get("title") or event.get("event_name") or "",
        club_name,
        "sailing",
        "2026",
    ]
    return " ".join(p for p in parts if p).strip()


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
            seen.add(url)
            item["lane"] = lane
            hits.append(item)
            lanes[lane]["count"] += 1

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
        add(web_hits(f'"{name}" {event.get("club") or ""} sailing South Africa 2026', limit=5), "results_names")

    return {
        "query": q,
        "lanes": lanes,
        "hits": hits,
        "counts": {k: v["count"] for k, v in lanes.items()},
        "total": len(hits),
    }
