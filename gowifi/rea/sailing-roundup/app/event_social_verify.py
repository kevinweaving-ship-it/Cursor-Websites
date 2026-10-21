#!/usr/bin/env python3
"""Fetch club + class social/news posts for one event and verify them.

For each weekend event:
  1. Resolve the host-club page (/club/tsc) and class page (/class/420)
  2. Collect every public Facebook / Instagram / YouTube / website link
  3. Search those pages (and the open web) for posts about this event
  4. Keep a post only when it verifies against the event URL and/or results

Read-only. Does not write to SailingSA.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; SailingRoundupResearch/1.0)"}
CLASS_KEYS = ("420", "505", "dart-18", "dart", "dabchick", "ilca", "optimist", "j22", "df95", "mirror")


def _get(url: str, timeout: int = 22) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def class_slugs_from_event(title: str = "", slug: str = "", class_name: str = "") -> list[str]:
    blob = " ".join((title or "", slug or "", class_name or "")).lower().replace("_", "-")
    found = []
    for key in CLASS_KEYS:
        if re.search(r"(^|[^a-z0-9])" + re.escape(key) + r"([^a-z0-9]|$)", blob):
            found.append("dart-18" if key == "dart" else key)
    # preserve order, unique
    out = []
    for item in found:
        if item not in out:
            out.append(item)
    return out


def result_names(rows: list[dict], limit: int = 12) -> list[str]:
    """Official identity for search: team names on TSL, sailors otherwise."""
    teamish = any(
        (row.get("class_name") or row.get("class_canonical") or "").upper() in {"TSL", "TEAM SAILING"}
        or "team sailing" in str(row.get("event_name") or "").lower()
        or (";" in str(row.get("helm_name") or "") and (row.get("boat_name") or row.get("team_name")))
        for row in rows or []
    )
    if teamish:
        names = []
        for row in rows or []:
            team = (row.get("boat_name") or row.get("team_name") or "").strip()
            if team and team.lower() not in {n.lower() for n in names}:
                names.append(team)
        return names[:limit]
    names = []
    for row in rows or []:
        for key in ("helm_name", "crew_name", "crew2_name", "crew3_name"):
            raw = row.get(key)
            if not raw:
                continue
            for part in re.split(r"[;/]| and ", str(raw)):
                name = re.sub(r"\s+", " ", part).strip()
                if len(name) > 3 and name.lower() not in {n.lower() for n in names}:
                    names.append(name)
        if len(names) >= limit:
            break
    return names[:limit]


def post_text(post: dict) -> str:
    return " ".join(
        str(post.get(k) or "")
        for k in ("title", "headline", "description", "snippet", "url", "source_url")
    ).lower()


def verify_post(post: dict, event: dict) -> dict:
    """Score a post against this event's URL, title, class, club, and results names."""
    text = post_text(post)
    event_url = (event.get("event_url") or event.get("url") or "").rstrip("/").lower()
    slug = (event.get("id") or event.get("regatta_id") or "").lower()
    title = (event.get("title") or event.get("event_name") or "").lower()
    club = (event.get("club") or "").lower()
    club_name = (event.get("club_name") or "").lower()
    host_fb = (event.get("host_club_facebook") or "").lower()
    classes = [c.lower() for c in event.get("class_slugs") or class_slugs_from_event(title, slug, event.get("class_name") or "")]
    names = [n.lower() for n in event.get("result_names") or []]
    post_url = (post.get("url") or post.get("source_url") or "").lower()
    reasons = []
    score = 0

    if slug and "sailingsa.co.za" in post_url and slug in post_url:
        score += 8
        reasons.append("sailingsa_official")
    if event_url and event_url in text:
        score += 6
        reasons.append("event_url")
    if slug and slug in text:
        score += 5
        reasons.append("event_slug")

    title_bits = [w for w in re.findall(r"[a-z0-9]+", title) if w not in {"the", "and", "2026", "2025", "sailing"} and len(w) > 2]
    title_hits = [w for w in title_bits if w in text]
    if title_hits:
        score += min(4, len(title_hits))
        reasons.append("event_title:" + ",".join(title_hits[:4]))

    class_hits = [c for c in classes if c.replace("-", " ") in text or c.replace("-", "") in text.replace("-", "")]
    if class_hits:
        score += 3
        reasons.append("class:" + ",".join(class_hits))

    if club and re.search(r"(^|[^a-z])" + re.escape(club) + r"([^a-z]|$)", text):
        score += 2
        reasons.append("host_club")
    if club_name and len(club_name) > 4 and club_name in text:
        score += 2
        reasons.append("host_club_name")
    host_path = urllib.parse.urlparse(host_fb).path.strip("/").lower() if host_fb else ""
    if host_path and host_path in post_url:
        score += 4
        reasons.append("host_club_page")

    name_hits = [n for n in names if n in text]
    if name_hits:
        score += 3
        reasons.append("results_name:" + ",".join(name_hits[:3]))

    if "sailingsa.co.za/regatta/" in text and slug and slug not in text:
        score -= 4
        reasons.append("other_event_url")

    # Same-weekend collision: a Dart post must not attach to the 420 article.
    rivals = [c for c in CLASS_KEYS if c not in classes and c not in ("dart",)]
    rival_hits = [c for c in rivals if re.search(r"(^|[^a-z0-9])" + re.escape(c) + r"([^a-z0-9]|$)", text)]
    if rival_hits and not class_hits and "event_url" not in reasons:
        score -= 3
        reasons.append("other_class:" + ",".join(rival_hits[:2]))

    junk = ("everythingfor420", "the420crew", "greenbeelife", "420.com/collections")
    if any(j in text for j in junk):
        score -= 8
        reasons.append("offtopic_420")

    try:
        from search_everywhere import in_coverage_window

        window = in_coverage_window(post, event)
    except Exception:
        window = None
    if window is True:
        score += 2
        reasons.append("in_event_window")
    elif window is False:
        score -= 8
        reasons.append("outside_event_window")

    verified = score >= 5 and window is not False and (
        "sailingsa_official" in reasons
        or
        "event_url" in reasons
        or "event_slug" in reasons
        or "results_name" in "".join(reasons)
        or "host_club_page" in reasons
        or ("class:" in "".join(reasons) and ("host_club" in reasons or "host_club_name" in reasons or "event_title:" in "".join(reasons)))
    )
    return {
        "url": post.get("url") or post.get("source_url"),
        "score": score,
        "verified": verified,
        "reasons": reasons,
        "title": post.get("title") or post.get("headline") or "",
    }


def class_config_links(slugs: list[str], local_only: bool = False) -> list[dict]:
    path = ROOT / "app" / "class_sources.json"
    if not path.exists():
        return []
    from catalog_sources import source_links_from_config

    classes = json.loads(path.read_text()).get("classes") or {}
    out = []
    seen = set()
    for slug in slugs:
        cfg = classes.get(slug) or (classes.get("dart-18") if slug == "dart" else {}) or {}
        for item in source_links_from_config(cfg, "class_sources.json:" + slug, local_only=local_only):
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(item)
    return out


def bing_search(query: str, limit: int = 8) -> list[dict]:
    q = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
    try:
        html = _get(q, timeout=18)
    except Exception:
        return []
    out = []
    for href, title in re.findall(r'<h2[^>]*>\s*<a href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        text = re.sub("<[^>]+>", "", title)
        text = re.sub(r"\s+", " ", text).strip()
        if href.startswith("http") and text and not any(x.get("url") == href for x in out):
            out.append({"url": href, "title": text, "description": "", "provenance": "bing:" + query})
        if len(out) >= limit:
            break
    return out


def search_source_posts(source_url: str, event: dict) -> list[dict]:
    host = urllib.parse.urlparse(source_url).netloc
    title = event.get("title") or event.get("event_name") or ""
    club = event.get("club") or ""
    queries = [
        f'site:{host} {title} {club} 2026',
        f'{title} {club} sailing',
    ]
    found = []
    seen = set()
    for q in queries:
        for item in bing_search(q):
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            item["source_page"] = source_url
            found.append(item)
    return found


def collect_and_verify(event: dict, rows: list[dict] | None = None) -> dict:
    """High-level helper used by the publisher and CLI."""
    from social_collect import (
        club_config,
        club_config_links,
        known_club_posts,
        directory_links,
        og_metadata,
        platform_for,
        _add_link,
    )

    slug = event.get("id") or event.get("regatta_id") or ""
    title = event.get("title") or event.get("event_name") or slug
    club = (event.get("club") or event.get("host_club_code") or "").strip()
    club_slug = (event.get("host_club_slug") or club).strip().lower()
    class_slugs = event.get("class_slugs") or class_slugs_from_event(title, slug, event.get("class_name") or "")
    names = event.get("result_names") or result_names(rows or [])
    event_url = event.get("event_url") or ("https://sailingsa.co.za/regatta/" + slug if slug else "")
    cfg = club_config(club)
    host_posts = known_club_posts(club, event)
    event_ctx = {
        "id": slug,
        "regatta_id": slug,
        "title": title,
        "event_name": title,
        "club": club,
        "club_name": event.get("club_name") or cfg.get("name") or club,
        "class_name": event.get("class_name") or "",
        "class_slugs": class_slugs,
        "result_names": names,
        "event_url": event_url,
        "host_club_facebook": cfg.get("facebook") or "",
        "host_source_urls": [x["url"] for x in club_config_links(club) if x.get("url")],
        "start": event.get("start") or event.get("start_date") or "",
        "end": event.get("end") or event.get("end_date") or "",
    }

    pages = []
    links = []
    if club_slug:
        rec = directory_links("club", club_slug)
        pages.append({"kind": "club", "slug": club_slug, "record": "https://sailingsa.co.za/club/" + club_slug, "links": rec})
        for item in rec:
            if item.get("url"):
                _add_link(links, item["url"], item.get("platform"), item.get("provenance") or "")
    for cslug in class_slugs:
        rec = directory_links("class", cslug)
        pages.append({"kind": "class", "slug": cslug, "record": "https://sailingsa.co.za/class/" + cslug, "links": rec})
        for item in rec:
            if item.get("url"):
                _add_link(links, item["url"], item.get("platform"), item.get("provenance") or "")
    for item in club_config_links(club) + class_config_links(class_slugs):
        _add_link(links, item.get("url"), item.get("platform"), item.get("provenance") or "")
        if links:
            links[-1]["locality"] = item.get("locality") or "local"
    for item in host_posts:
        _add_link(links, item.get("url"), item.get("platform"), item.get("provenance") or "host_club_post")

    from search_everywhere import official_sailingsa_sources

    candidates = list(official_sailingsa_sources(event_ctx)) + list(host_posts)
    for link in links:
        url = link.get("url") or ""
        if not url:
            continue
        meta = og_metadata(url) or {"url": url, "title": "", "description": "", "platform": link.get("platform")}
        meta["provenance"] = link.get("provenance")
        candidates.append(meta)
        if link.get("platform") in ("facebook", "instagram", "youtube", "website"):
            candidates.extend(search_source_posts(url, event_ctx))

    from search_everywhere import search_everywhere

    everywhere = search_everywhere(event_ctx)
    candidates.extend(everywhere.get("hits") or [])
    candidates.extend(bing_search(f"{title} {club} {event_url}"))

    verified = []
    rejected = []
    seen = set()
    for post in candidates:
        url = (post.get("url") or "").split("?")[0]
        if not url or url in seen:
            continue
        seen.add(url)
        if not post.get("title") and not post.get("description"):
            meta = og_metadata(url)
            if meta:
                post = {**post, **meta}
        check = verify_post(post, event_ctx)
        post["verification"] = check
        (verified if check["verified"] else rejected).append(post)

    return {
        "event_url": event_url,
        "club": club,
        "club_page": ("https://sailingsa.co.za/club/" + club_slug) if club_slug else None,
        "class_pages": ["https://sailingsa.co.za/class/" + c for c in class_slugs],
        "class_slugs": class_slugs,
        "result_names": names,
        "directory_pages": pages,
        "source_links": links,
        "verified_posts": verified,
        "rejected_posts": rejected[:40],
        "counts": {"sources": len(links), "verified": len(verified), "rejected": len(rejected)},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--event-url", required=True)
    p.add_argument("--issue", default="2026-09-28")
    args = p.parse_args()
    slug = args.event_url.rstrip("/").split("/")[-1]
    rows = []
    try:
        req = urllib.request.Request(
            "https://sailingsa.co.za/api/regatta/" + slug, headers=UA
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
            rows = data if isinstance(data, list) else []
    except Exception as exc:
        rows = []
        err = str(exc)
    else:
        err = None
    first = rows[0] if rows else {}
    pack = collect_and_verify(
        {
            "id": slug,
            "title": first.get("event_name") or slug,
            "club": first.get("host_club_code") or "",
            "host_club_slug": first.get("host_club_slug") or "",
            "class_name": first.get("class_name") or first.get("class_canonical") or "",
            "event_url": args.event_url,
            "start": first.get("start_date") or "",
            "end": first.get("end_date") or "",
        },
        rows,
    )
    if err:
        pack["regatta_api_error"] = err
    dest = ROOT / "issues" / args.issue / "sources"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / (slug + "-social-verified.json")
    path.write_text(json.dumps(pack, indent=2, ensure_ascii=False))
    print(json.dumps({"path": str(path), **pack["counts"], "event_url": pack["event_url"], "class_pages": pack["class_pages"]}, indent=2))


if __name__ == "__main__":
    main()
