#!/usr/bin/env python3
"""Collect public social/media evidence for one event.

Sources (read-only, no login bypass):
- SailingSA club/class directory pages
- Local source registry + club_sources.json
- Sailor Media-tab mentions (public-mentions API)
- Open Graph metadata on discovered URLs
- gallery-dl / yt-dlp extractors already installed for REA
- Optional Athena / SocialCrawl when credentials exist
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import urllib.parse

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; SailingRoundupResearch/1.0)"}
SOCIAL_HOSTS = {
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "tiktok.com": "tiktok",
    "x.com": "x",
    "twitter.com": "x",
}


def platform_for(url: str) -> str | None:
    host = urllib.parse.urlparse(url or "").netloc.lower().removeprefix("www.")
    for key, name in SOCIAL_HOSTS.items():
        if host == key or host.endswith("." + key):
            return name
    return None


def og_metadata(url: str) -> dict | None:
    try:
        r = requests.get(
            url,
            timeout=14,
            headers={"User-Agent": "facebookexternalhit/1.1"},
            allow_redirects=True,
        )
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

        def og(key):
            tag = soup.find("meta", attrs={"property": "og:" + key}) or soup.find(
                "meta", attrs={"name": "og:" + key}
            )
            return (tag.get("content") or "").strip() if tag else ""

        title = og("title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
        desc = og("description")
        image = og("image")
        if not (title or desc or image):
            return None
        return {
            "url": r.url,
            "title": title,
            "description": desc,
            "image": image,
            "platform": platform_for(r.url) or platform_for(url),
            "status": r.status_code,
        }
    except requests.RequestException:
        return None


def _add_link(bucket: list, url: str, platform: str | None, provenance: str):
    url = (url or "").strip()
    if not url.startswith("http"):
        return
    if any(x.get("url") == url for x in bucket):
        return
    bucket.append(
        {
            "url": url,
            "platform": platform or platform_for(url) or "website",
            "provenance": provenance,
        }
    )


def directory_links(kind: str, slug: str) -> list:
    from sailingsa_sources import extract

    if not kind or not slug:
        return []
    try:
        rec = extract(kind, slug.lower())
    except Exception as exc:
        return [{"error": str(exc)[:160], "record": f"{kind}/{slug}"}]
    out = []
    for link in rec.get("links") or []:
        _add_link(out, link.get("url"), link.get("platform"), rec.get("record") or "")
    return out


def club_config_links(club: str) -> list:
    path = ROOT / "app" / "club_sources.json"
    if not path.exists() or not club:
        return []
    clubs = json.loads(path.read_text()).get("clubs") or {}
    cfg = clubs.get(club.upper()) or clubs.get(club)
    if not cfg:
        return []
    out = []
    for key in ("website", "gallery", "facebook", "instagram", "youtube", "tiktok"):
        _add_link(out, cfg.get(key), key if key != "website" else "website", "club_sources.json")
    return out


def registry_links(club: str, klass: str) -> list:
    db = ROOT / "data" / "sources.sqlite3"
    if not db.exists():
        return []
    import sqlite3

    out = []
    keys = []
    if club:
        keys.append(("club", club.lower()))
    if klass:
        keys.append(("class", klass.lower().replace(" ", "-")))
    try:
        with sqlite3.connect(db) as conn:
            for kind, key in keys:
                rows = conn.execute(
                    "SELECT platform,url FROM sources WHERE entity_type=? AND entity_key=?",
                    (kind, key),
                ).fetchall()
                for platform, url in rows:
                    _add_link(out, url, platform, "source_registry")
    except sqlite3.Error:
        return out
    return out


def gallery_dl(url: str, timeout: int = 35) -> dict:
    exe = ROOT / ".venv" / "bin" / "gallery-dl"
    if not exe.exists():
        exe = pathlib.Path("gallery-dl")
    try:
        proc = subprocess.run(
            [str(exe), "--get-urls", "--no-download", url],
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        urls = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip().startswith("http")]
        return {
            "url": url,
            "status": "ok" if proc.returncode == 0 else "error",
            "media_urls": urls[:12],
            "error": (proc.stderr or "")[-180:] if proc.returncode else None,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"url": url, "status": "error", "media_urls": [], "error": str(exc)[:160]}


def yt_search(query: str, limit: int = 5) -> list:
    exe = ROOT / ".venv" / "bin" / "yt-dlp"
    if not exe.exists():
        exe = pathlib.Path("yt-dlp")
    try:
        proc = subprocess.run(
            [
                str(exe),
                f"ytsearch{limit}:{query}",
                "--skip-download",
                "--print",
                "%(title)s\t%(webpage_url)s\t%(thumbnail)s",
            ],
            timeout=40,
            capture_output=True,
            text=True,
        )
        out = []
        for line in (proc.stdout or "").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1].startswith("http"):
                out.append(
                    {
                        "title": parts[0],
                        "url": parts[1],
                        "image": parts[2] if len(parts) > 2 else "",
                        "platform": "youtube",
                    }
                )
        return out
    except (OSError, subprocess.TimeoutExpired):
        return []


def try_aggregators(issue: str, query: str, urls: list[str]) -> list:
    if not (os.getenv("APIFY_TOKEN") or os.getenv("SOCIALCRAWL_API_KEY")):
        return [{"status": "skipped", "reason": "no aggregator credentials"}]
    try:
        import social_aggregators

        results = []
        if os.getenv("APIFY_TOKEN") and urls:
            try:
                for r in social_aggregators.official_apify(urls[:8]):
                    if r.get("status") == "ok":
                        name = (r.get("actor") or "apify").replace("/", "-")
                        r["saved"] = social_aggregators.save(name, r.get("items"), issue)
                        r["count"] = len(r.get("items") or []) if isinstance(r.get("items"), list) else None
                        r.pop("items", None)
                    results.append(r)
            except Exception as exc:
                results.append({"provider": "apify", "status": "error", "error": str(exc)[:160]})
        if os.getenv("SOCIALCRAWL_API_KEY"):
            try:
                r = social_aggregators.socialcrawl(query)
                if r.get("status") == "ok":
                    r["saved"] = social_aggregators.save("socialcrawl", r.get("items"), issue)
                    r.pop("items", None)
                results.append(r)
            except Exception as exc:
                results.append({"provider": "socialcrawl", "status": "error", "error": str(exc)[:160]})
        return results
    except Exception as exc:
        return [{"status": "error", "error": str(exc)[:160]}]


def collect(issue: str, event: dict, sa_ids: list, terms: list[str], start, end, rows=None) -> dict:
    """Search everywhere, then keep posts that verify against this event URL and results."""
    from event_social_verify import class_slugs_from_event, result_names, verify_post
    from sailor_mentions import collect_for_sailors
    from search_everywhere import search_everywhere

    club = (event.get("club") or event.get("host_club_code") or "").strip()
    klass = (event.get("class_name") or event.get("class_canonical") or "").strip()
    club_slug = (event.get("host_club_slug") or club).strip().lower()
    class_slug = klass.lower().replace(" ", "-")
    links = []
    directory = []
    for kind, slug in (("club", club_slug), ("class", class_slug)):
        if not slug:
            continue
        found = directory_links(kind, slug)
        directory.append({"kind": kind, "slug": slug, "links": found})
        for item in found:
            if item.get("url"):
                _add_link(links, item["url"], item.get("platform"), item.get("provenance") or "")
    for item in club_config_links(club) + registry_links(club, klass):
        _add_link(links, item.get("url"), item.get("platform"), item.get("provenance") or "")

    mentions = collect_for_sailors(sa_ids, start, end, terms)
    for item in mentions.get("matched") or []:
        _add_link(links, item.get("url"), platform_for(item.get("url") or ""), "sailor_public_mentions")

    posts = []
    images = []
    gallery = []
    social_urls = [x["url"] for x in links if x.get("platform") in SOCIAL_HOSTS.values()]
    for url in social_urls[:4]:
        meta = og_metadata(url)
        if meta:
            posts.append(meta)
            if meta.get("image"):
                images.append(
                    {
                        "image_url": meta["image"],
                        "source_url": meta["url"],
                        "source_title": meta.get("title") or "",
                        "rights_status": "external_link_only",
                        "platform": meta.get("platform"),
                    }
                )
        g = gallery_dl(url, timeout=20)
        gallery.append({"url": url, "status": g.get("status"), "count": len(g.get("media_urls") or []), "error": g.get("error")})
        for media_url in g.get("media_urls") or []:
            images.append(
                {
                    "image_url": media_url,
                    "source_url": url,
                    "source_title": "",
                    "rights_status": "external_link_only",
                    "platform": platform_for(url),
                }
            )

    query = " ".join(x for x in (event.get("title") or event.get("event_name"), club, "sailing 2026") if x)
    videos = yt_search(query)
    for vid in videos:
        _add_link(links, vid["url"], "youtube", "yt-dlp")
        posts.append(
            {
                "url": vid["url"],
                "title": vid.get("title"),
                "description": "",
                "image": vid.get("image"),
                "platform": "youtube",
                "status": 200,
            }
        )

    event_url = event.get("event_url") or (
        "https://sailingsa.co.za/regatta/" + (event.get("id") or event.get("regatta_id") or "")
    )
    class_slugs = class_slugs_from_event(
        event.get("title") or "", event.get("id") or "", klass or event.get("class_canonical") or ""
    )
    names = event.get("result_names") or result_names(rows or [])
    event_ctx = {
        **event,
        "event_url": event_url,
        "class_slugs": class_slugs,
        "result_names": names,
        "club": club,
    }
    everywhere = search_everywhere(event_ctx)
    verified = []
    rejected = []
    for hit in everywhere.get("hits") or []:
        check = verify_post(hit, event_ctx)
        hit["verification"] = check
        if check["verified"]:
            verified.append(hit)
            _add_link(links, hit.get("url"), platform_for(hit.get("url") or ""), hit.get("lane") or "everywhere")
            if not any(p.get("url") == hit.get("url") for p in posts):
                posts.append(hit)
        else:
            rejected.append(check)

    aggregators = try_aggregators(issue, query, social_urls)
    return {
        "event_id": event.get("id") or event.get("regatta_id"),
        "event_url": event_url,
        "class_pages": ["https://sailingsa.co.za/class/" + c for c in class_slugs],
        "club_page": ("https://sailingsa.co.za/club/" + club_slug) if club_slug else None,
        "links": links,
        "directory": directory,
        "sailor_mentions": mentions,
        "posts": [p for p in posts if (p.get("verification") or {}).get("verified", p.get("lane") is None)],
        "images": images[:24],
        "gallery_dl": gallery,
        "videos": videos,
        "aggregators": aggregators,
        "everywhere": {"query": everywhere.get("query"), "counts": everywhere.get("counts"), "total": everywhere.get("total")},
        "verified_posts": verified,
        "rejected_count": len(rejected),
    }
