#!/usr/bin/env python3
"""Paid/optional social ingest. Independent of SailingSA production.

Official tools REA mapped from the public web (see docs/TOOL_RESEARCH.md):

- SocialCrawl `/v1/search/everywhere` — one query across Instagram, YouTube,
  TikTok, Facebook, X, Reddit, and more.
- Apify actors (preferred over unofficial scrapers):
  - apify/facebook-posts-scraper
  - apify/instagram-scraper
  - streamers/youtube-scraper
  - apify/facebook-events-scraper

These run only when APIFY_TOKEN or SOCIALCRAWL_API_KEY is set. Without
credentials the Monday publisher still uses the sailor Media-tab API,
club/class directories, Open Graph, gallery-dl and yt-dlp.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sqlite3
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sources.sqlite3"
APIFY_ACTORS = {
    "facebook": "apify/facebook-posts-scraper",
    "instagram": "apify/instagram-scraper",
    "youtube": "streamers/youtube-scraper",
    "facebook_events": "apify/facebook-events-scraper",
    "athena": "ranil~athena-social-scraper",
}


def request(url, payload=None, headers=None, timeout=75):
    h = {"User-Agent": "SailingSA-REA-Roundup/1.0", "Accept": "application/json"}
    h.update(headers or {})
    body = None if payload is None else json.dumps(payload).encode()
    if body:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def apify_actor(actor, payload, timeout=240):
    key = os.getenv("APIFY_TOKEN")
    if not key:
        return {"status": "needs_credentials", "provider": "apify", "actor": actor, "env": "APIFY_TOKEN"}
    url = (
        "https://api.apify.com/v2/acts/"
        + urllib.parse.quote(actor, safe="")
        + "/run-sync-get-dataset-items?token="
        + urllib.parse.quote(key)
    )
    data = request(url, payload, timeout=timeout)
    return {"status": "ok", "provider": "apify", "actor": actor, "items": data}


def athena(urls):
    return apify_actor(APIFY_ACTORS["athena"], {"startUrls": [{"url": u} for u in urls], "useBrowserFallback": True})


def official_apify(urls):
    """Run the documented official actors against discovered social URLs."""
    by_platform = {"facebook": [], "instagram": [], "youtube": []}
    for url in urls or []:
        low = url.lower()
        if "facebook.com" in low or "fb.watch" in low:
            by_platform["facebook"].append(url)
        elif "instagram.com" in low:
            by_platform["instagram"].append(url)
        elif "youtube.com" in low or "youtu.be" in low:
            by_platform["youtube"].append(url)
    results = []
    if by_platform["facebook"]:
        results.append(
            apify_actor(
                APIFY_ACTORS["facebook"],
                {"startUrls": [{"url": u} for u in by_platform["facebook"][:8]], "resultsLimit": 20},
            )
        )
    if by_platform["instagram"]:
        results.append(
            apify_actor(
                APIFY_ACTORS["instagram"],
                {"directUrls": by_platform["instagram"][:8], "resultsType": "posts", "resultsLimit": 20},
            )
        )
    if by_platform["youtube"]:
        results.append(apify_actor(APIFY_ACTORS["youtube"], {"startUrls": [{"url": u} for u in by_platform["youtube"][:8]]}))
    if not results:
        results.append(athena(urls))
    return results


def socialcrawl(query, platform="search", resource="everywhere"):
    key = os.getenv("SOCIALCRAWL_API_KEY")
    if not key:
        return {"status": "needs_credentials", "provider": "socialcrawl", "env": "SOCIALCRAWL_API_KEY"}
    base = os.getenv("SOCIALCRAWL_BASE_URL", "https://www.socialcrawl.dev").rstrip("/")
    params = {"query": query, "lookback_days": 14}
    url = base + "/v1/" + urllib.parse.quote(platform) + "/" + resource + "?" + urllib.parse.urlencode(params)
    data = request(url, headers={"x-api-key": key})
    return {"status": "ok", "provider": "socialcrawl", "items": data}


def known_sources():
    if not DB.exists():
        return []
    with sqlite3.connect(DB) as c:
        return [
            {"entity_type": r[0], "entity_key": r[1], "platform": r[2], "url": r[3]}
            for r in c.execute(
                "SELECT entity_type,entity_key,platform,url FROM sources "
                "WHERE platform IN ('facebook','instagram','tiktok','youtube') "
                "AND confidence IN ('confirmed_directory','confirmed_official')"
            )
        ]


def save(provider, items, issue):
    out = ROOT / "issues" / issue / "sources" / (provider + "-aggregator.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"provider": provider, "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "items": items},
            indent=2,
            ensure_ascii=False,
        )
    )
    return str(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider", choices=["athena", "apify", "socialcrawl", "both"], default="both")
    p.add_argument("--issue", default="2026-09-28")
    p.add_argument("--query", default="2026 420 Nationals Theewater Sports Club September 2026 sailing")
    p.add_argument("--urls", nargs="*")
    a = p.parse_args()
    results = []
    urls = a.urls or [s["url"] for s in known_sources()]
    if a.provider in ("athena", "apify", "both") and urls:
        for r in official_apify(urls):
            if r.get("status") == "ok":
                name = (r.get("actor") or "apify").replace("/", "-")
                r["saved"] = save(name, r.get("items"), a.issue)
                r["count"] = len(r.get("items") or []) if isinstance(r.get("items"), list) else None
                r.pop("items", None)
            results.append(r)
    if a.provider in ("socialcrawl", "both"):
        try:
            r = socialcrawl(a.query)
        except Exception as e:
            r = {"provider": "socialcrawl", "status": "error", "error": str(e)}
        if r.get("status") == "ok":
            r["saved"] = save("socialcrawl", r.get("items"), a.issue)
            r.pop("items", None)
        results.append(r)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
