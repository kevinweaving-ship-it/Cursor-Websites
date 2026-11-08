#!/usr/bin/env python3
"""Build the independent club/class URL directory the same way club pages list links.

Clubs on SailingSA already publish website + Facebook + Instagram on /club/{slug}.
This crawler:

  1. Scrapes every public club page and stores those URLs (local).
  2. Does the same for South African classes only.
  3. Keeps international class association URLs, labelled locality=not_local.
  4. Resolves Facebook share links (e.g. 420 Class RSA group) and matches
     cross-shared pages back to /club/, /class/, /sailor/, or sponsor records.

Never writes to SailingSA.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

from entity_match import (
    DEFAULT_SPONSORS,
    build_index,
    match_text,
    normalize_facebook,
    slugify,
)
from facebook_cross_share import match_cross_shares, resolve_facebook_url
from source_registry import ingest as ingest_registry
from source_registry import normalize

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
SA = "https://sailingsa.co.za"
SAS_CLASSES = "https://www.sailing.org.za/what-we-do/sasclasses"
UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PLATFORMS = {
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "tiktok.com": "tiktok",
    "x.com": "x",
    "twitter.com": "x",
}

SKIP_HOST = (
    "sailingsa.co.za",
    "google.com",
    "g.page",
    "schema.org",
    "cloudflare",
    "openstreetmap",
    "facebook.net",
    "fbcdn.net",
    "revolutionise.com.au/site",
    "cdn.revolutionise",
    "cdn-static.revolutionise",
)

LOCAL_HINTS = (
    ".co.za",
    "sailing.org.za",
    "southafrica",
    "south-africa",
    "classrsa",
    "class rsa",
    "nationalsouthafrica",
    "nationals south africa",
    "laserclasssa",
    "saflying",
    "hobiesa",
    "dabchickca",
    "optimistca",
    "j22ca",
    "mirrorca",
    "l26ca",
    "stadt23class",
    "29erclass",
    "sarsa.weebly",
    "420nationalssouthafrica",
    "groups/120115671476306",
    "share/g/1jh51cdmew",
    "rsa505",
    "groups/230542873685522",
    "share/g/" + "1MHJNWcFSM".lower(),
    "groups/310727125653436",
    "share/g/" + "19VLSkGHBk".lower(),
    "dart18 sa",
    "rsa 505 group",
)
NOT_LOCAL_HINTS = (
    "int420",
    "int505",
    "international 420",
    "international 505",
    "linktr.ee/int",
    "dart18class.com",
    "sailing.org/",
    "worldsailing",
)

SA_CLASS_SITES = {
    "29er": "https://www.revolutionise.com.au/29erclass/",
    "ilca": "https://www.revolutionise.com.au/laserclasssa/",
    "ilca-6": "https://www.revolutionise.com.au/laserclasssa/",
    "ilca-7": "https://www.revolutionise.com.au/laserclasssa/",
    "ilca-4": "https://www.revolutionise.com.au/laserclasssa/",
    "optimist": "https://www.revolutionise.com.au/optimistca/",
    "dabchick": "https://www.revolutionise.com.au/dabchickca/",
    "mirror": "https://www.revolutionise.com.au/mirrorca",
    "j22": "https://www.revolutionise.com.au/j22ca/",
    "flying-fifteen": "https://www.revolutionise.com.au/saflyingfifteen/",
    "hobie": "https://www.hobiesa.co.za/",
    "l26": "https://www.revolutionise.com.au/l26ca",
    "stadt-23": "https://www.revolutionise.com.au/stadt23class/",
    "df95": "https://sarsa.weebly.com/",
    "radio": "https://sarsa.weebly.com/",
}

# Always-on seeds. 420 Class RSA is the local class Facebook group (user share link).
CLASS_SEEDS = {
    "420": [
        {
            "platform": "facebook",
            "url": "https://www.facebook.com/groups/120115671476306/",
            "locality": "local",
            "label": "420 Class RSA",
            "kind": "facebook_group",
            "provenance": "user:https://www.facebook.com/share/g/1Jh51CDMew/",
            "share_url": "https://www.facebook.com/share/g/1Jh51CDMew/",
        },
        {
            "platform": "facebook",
            "url": "https://www.facebook.com/420nationalssouthafrica/",
            "locality": "local",
            "label": "420 Nationals South Africa",
            "kind": "facebook_page",
            "provenance": "seed",
        },
        {
            "platform": "facebook",
            "url": "https://www.facebook.com/Int420Class/",
            "locality": "not_local",
            "label": "International 420 Class",
            "kind": "facebook_page",
            "provenance": "international",
        },
        {
            "platform": "website",
            "url": "https://linktr.ee/int420class",
            "locality": "not_local",
            "label": "International 420 Class",
            "provenance": "international",
        },
    ],
    "505": [
        {
            "platform": "facebook",
            "url": "https://www.facebook.com/groups/230542873685522/",
            "locality": "local",
            "label": "RSA 505 group",
            "kind": "facebook_group",
            "provenance": "user:https://www.facebook.com/share/g/1MHJNWcFSM/",
            "share_url": "https://www.facebook.com/share/g/1MHJNWcFSM/",
        },
        {
            "platform": "website",
            "url": "https://rsa505.org.za/",
            "locality": "local",
            "label": "RSA 505",
            "provenance": "https://rsa505.org.za/",
        },
        {
            "platform": "facebook",
            "url": "https://www.facebook.com/int505",
            "locality": "not_local",
            "label": "International 505 Class",
            "provenance": "international",
        },
        {
            "platform": "website",
            "url": "https://int505.org/",
            "locality": "not_local",
            "label": "International 505 Class",
            "provenance": "international",
        },
    ],
    "dart-18": [
        {
            "platform": "facebook",
            "url": "https://www.facebook.com/groups/310727125653436/",
            "locality": "local",
            "label": "DART18 SA",
            "kind": "facebook_group",
            "provenance": "user:https://www.facebook.com/share/g/19VLSkGHBk/",
            "share_url": "https://www.facebook.com/share/g/19VLSkGHBk/",
        },
        {
            "platform": "website",
            "url": "https://dart18class.com/",
            "locality": "not_local",
            "label": "International Dart 18 Class",
            "provenance": "international",
        },
    ],
}


def fetch(url: str, timeout: int = 22) -> tuple[str, str]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.geturl(), resp.read().decode("utf-8", "replace")


def fetch_json(url: str, timeout: int = 22):
    _final, raw = fetch(url, timeout)
    return json.loads(raw)


def platform_for(url: str) -> str:
    host = urllib.parse.urlparse(url or "").netloc.lower().removeprefix("www.")
    for key, name in PLATFORMS.items():
        if host == key or host.endswith("." + key):
            return name
    return "website"


def classify_locality(url: str, label: str = "", force: str = "") -> str:
    if force in ("local", "not_local"):
        return force
    blob = " ".join((url or "", label or "")).lower()
    if any(h in blob for h in NOT_LOCAL_HINTS):
        return "not_local"
    if any(h in blob for h in LOCAL_HINTS):
        return "local"
    return "local" if force == "club_page" else "not_local"


def skip_url(url: str) -> bool:
    host = urllib.parse.urlparse(url or "").netloc.lower()
    path = urllib.parse.urlparse(url or "").path.lower()
    if any(s in host or s in url for s in SKIP_HOST):
        return True
    if "sailing.org.za/events" in url or "/events/" in path and "sailing.org.za" in host:
        return True
    return False


def add_url(bucket: list[dict], item: dict) -> None:
    url = (item.get("url") or "").strip()
    if not url.startswith("http"):
        return
    if "facebook.com" in url:
        url = normalize_facebook(url)
    canonical = normalize(url)
    item = {**item, "url": url, "canonical_url": canonical}
    item["platform"] = item.get("platform") or platform_for(url)
    item["locality"] = item.get("locality") or classify_locality(url, item.get("label") or "")
    for existing in bucket:
        if existing.get("canonical_url") == canonical or existing.get("url") == url:
            if item["locality"] == "local":
                existing["locality"] = "local"
            if item.get("label") and not existing.get("label"):
                existing["label"] = item["label"]
            if item.get("share_url") and not existing.get("share_url"):
                existing["share_url"] = item["share_url"]
            return
    bucket.append(item)


def extract_page_links(html: str, page_url: str, default_locality: str):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    selectors = ["a.club-story-social", "a.club-story-website", "a[href]"]
    seen = set()
    for sel in selectors:
        for tag in soup.select(sel):
            href = urllib.parse.urljoin(page_url, tag.get("href") or "")
            if not href.startswith("http") or href in seen:
                continue
            seen.add(href)
            if skip_url(href) and platform_for(href) == "website":
                continue
            platform = platform_for(href)
            if platform == "website" and sel == "a[href]" and "club-story" not in " ".join(tag.get("class") or []):
                host = urllib.parse.urlparse(href).netloc.lower()
                if host.endswith("sailing.org.za") or "/events/" in href:
                    continue
            label = (tag.get("title") or tag.get("aria-label") or tag.get_text(" ", strip=True) or "")[:80]
            force = "local" if default_locality == "local" and platform != "website" else default_locality
            if platform == "website" and default_locality == "local":
                force = "local"
            add_url(
                out,
                {
                    "url": href,
                    "platform": platform,
                    "label": label,
                    "provenance": page_url,
                    "locality": classify_locality(href, label, force=force),
                },
            )
    return out, title


def preferred_keys(urls: list[dict]) -> dict:
    pref = {}
    for item in urls:
        if item.get("locality") != "local":
            continue
        key = item.get("platform") or "website"
        if key == "facebook" and item.get("kind") == "facebook_group":
            pref.setdefault("facebook", item["url"])
            pref.setdefault("facebook_group", item["url"])
        elif key not in pref:
            pref[key] = item["url"]
    not_local = [u for u in urls if u.get("locality") == "not_local"]
    if not_local:
        pref["not_local_urls"] = [
            {"platform": u.get("platform"), "url": u.get("url"), "label": u.get("label") or ""}
            for u in not_local
        ]
    return pref


def catalog_clubs(limit: int | None = None) -> dict:
    rows = fetch_json(SA + "/api/clubs")
    if not isinstance(rows, list):
        rows = []
    clubs = {}
    extract_records = []
    for i, row in enumerate(rows):
        if limit is not None and i >= limit:
            break
        code = (row.get("code") or "").strip()
        name = (row.get("name") or code).strip()
        slug = (row.get("slug") or slugify(name)).strip()
        page = f"{SA}/club/{slug}"
        rec = {
            "name": name,
            "code": code,
            "slug": slug,
            "sailingsa_url": page,
            "province": row.get("province") or "",
            "urls": [],
        }
        try:
            _final, html = fetch(page)
            links, title = extract_page_links(html, page, default_locality="local")
            rec["page_title"] = title
            for link in links:
                add_url(rec["urls"], {**link, "locality": "local"})
        except Exception as exc:
            rec["error"] = str(exc)[:160]
        rec.update(preferred_keys(rec["urls"]))
        key = (code or slug).upper()
        clubs[key] = rec
        extract_records.append(
            {
                "record": page,
                "title": rec.get("page_title") or name,
                "links": rec["urls"],
            }
        )
        time.sleep(0.12)
    return {"clubs": clubs, "extract": extract_records}


def _class_api(slug: str) -> dict:
    try:
        data = fetch_json(f"{SA}/api/class/{slug}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def catalog_classes() -> dict:
    classes: dict[str, dict] = {}

    def ensure(slug: str, name: str) -> dict:
        slug = slugify(slug)
        rec = classes.setdefault(
            slug,
            {
                "name": name or slug,
                "slug": slug,
                "sailingsa_url": f"{SA}/class/{slug}",
                "urls": [],
            },
        )
        if name and rec["name"] == slug:
            rec["name"] = name
        return rec

    for slug, url in SA_CLASS_SITES.items():
        rec = ensure(slug, slug.replace("-", " ").title())
        add_url(
            rec["urls"],
            {
                "url": url,
                "platform": "website",
                "locality": "local",
                "label": rec["name"] + " SA class website",
                "provenance": SAS_CLASSES,
            },
        )

    try:
        _final, sas_html = fetch(SAS_CLASSES)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(sas_html, "html.parser")
        for tag in soup.select("a[href]"):
            label = tag.get_text(" ", strip=True)
            href = urllib.parse.urljoin(SAS_CLASSES, tag.get("href") or "")
            if "Class Website" not in label and "Radio Sailing" not in label:
                continue
            name = re.sub(r"\s*(Class Website|Website)\s*$", "", label, flags=re.I).strip()
            slug = slugify(name.replace("ILCA", "ilca"))
            rec = ensure(slug, name)
            add_url(
                rec["urls"],
                {
                    "url": href,
                    "platform": platform_for(href),
                    "locality": "local",
                    "label": label,
                    "provenance": SAS_CLASSES,
                },
            )
    except Exception:
        pass

    wanted = set(CLASS_SEEDS) | set(SA_CLASS_SITES) | {"420", "505", "dart-18", "dabchick", "optimist", "j22", "df95", "mirror"}
    for slug in sorted(wanted):
        rec = ensure(slug, slug.replace("-", " ").title() if slug != "420" else "420")
        api = _class_api(slug)
        if api.get("class_name"):
            rec["name"] = api["class_name"]
        rec["email"] = api.get("email")
        rec["association_name"] = api.get("association_name")
        for key in ("website_url", "facebook_url", "instagram_url", "twitter_url", "youtube_url"):
            url = (api.get(key) or "").strip()
            if not url:
                continue
            platform = "website" if key.startswith("website") else key.replace("_url", "").replace("twitter", "x")
            add_url(
                rec["urls"],
                {
                    "url": url,
                    "platform": platform,
                    "locality": classify_locality(url, rec["name"]),
                    "provenance": f"{SA}/api/class/{slug}",
                    "label": rec["name"],
                },
            )
        time.sleep(0.08)

    for slug, seeds in CLASS_SEEDS.items():
        rec = ensure(slug, classes.get(slug, {}).get("name") or slug)
        for seed in seeds:
            if seed.get("share_url") or "/share/" in (seed.get("url") or ""):
                resolved = resolve_facebook_url(seed.get("share_url") or seed["url"])
                if resolved.get("canonical_url"):
                    seed = {
                        **seed,
                        "url": resolved["canonical_url"],
                        "share_url": resolved.get("share_url") or seed.get("share_url"),
                        "label": seed.get("label") or resolved.get("title") or "",
                        "kind": resolved.get("kind") or seed.get("kind"),
                    }
            add_url(rec["urls"], seed)

    extract_records = []
    for slug, rec in classes.items():
        rec.update(preferred_keys(rec["urls"]))
        extract_records.append({"record": rec["sailingsa_url"], "title": rec["name"], "links": rec["urls"]})
    return {"classes": classes, "extract": extract_records}


def attach_cross_shares(clubs: dict, classes: dict, sailors: list[dict] | None = None) -> list[dict]:
    index = build_index(
        clubs=[
            {"code": c.get("code"), "name": c.get("name"), "slug": c.get("slug")}
            for c in clubs.values()
        ],
        classes=[{"name": c.get("name"), "slug": c.get("slug")} for c in classes.values()],
        sailors=sailors or [],
        sponsors=DEFAULT_SPONSORS,
    )
    posts = []
    for rec in list(clubs.values()) + list(classes.values()):
        for item in rec.get("urls") or []:
            posts.append(
                {
                    "url": item.get("url"),
                    "title": item.get("label") or rec.get("name"),
                    "description": item.get("provenance") or "",
                }
            )
    matches = match_cross_shares(posts, index)
    for hit in matches:
        entity = hit.get("shared_from_entity") or hit.get("host_entity") or hit.get("shared_by_entity")
        if not entity:
            continue
        kind, key = entity["entity_type"], entity["entity_key"]
        bucket = clubs if kind == "club" else classes if kind == "class" else None
        if bucket is None:
            continue
        rec = None
        for cand in bucket.values():
            if slugify(cand.get("slug") or "") == key or slugify(cand.get("code") or "") == key:
                rec = cand
                break
        if rec is None and kind == "class":
            rec = classes.setdefault(
                key,
                {"name": entity["display_name"], "slug": key, "sailingsa_url": entity["sailingsa_url"], "urls": []},
            )
        if rec is None:
            continue
        add_url(
            rec["urls"],
            {
                "url": hit.get("facebook_url") or hit.get("post_url"),
                "platform": "facebook",
                "locality": classify_locality(hit.get("facebook_url") or "", entity["display_name"]),
                "label": hit.get("page_title") or entity["display_name"],
                "provenance": "facebook_cross_share",
                "share_url": hit.get("share_url") or "",
                "matched_sailingsa_url": entity["sailingsa_url"],
            },
        )
        rec.update(preferred_keys(rec["urls"]))
    return matches


def write_sources(clubs: dict, classes: dict) -> None:
    club_out = {}
    for key, rec in clubs.items():
        club_out[key] = {
            "name": rec.get("name"),
            "code": rec.get("code"),
            "slug": rec.get("slug"),
            "sailingsa_url": rec.get("sailingsa_url"),
            "website": rec.get("website"),
            "facebook": rec.get("facebook"),
            "instagram": rec.get("instagram"),
            "youtube": rec.get("youtube"),
            "gallery": rec.get("gallery"),
            "urls": rec.get("urls") or [],
        }
        if rec.get("error"):
            club_out[key]["error"] = rec["error"]
    class_out = {}
    for key, rec in classes.items():
        class_out[key] = {
            "name": rec.get("name"),
            "slug": rec.get("slug"),
            "sailingsa_url": rec.get("sailingsa_url"),
            "website": rec.get("website"),
            "facebook": rec.get("facebook"),
            "facebook_group": rec.get("facebook_group"),
            "instagram": rec.get("instagram"),
            "youtube": rec.get("youtube"),
            "email": rec.get("email"),
            "urls": rec.get("urls") or [],
            "not_local_urls": rec.get("not_local_urls") or [],
        }
    (APP / "club_sources.json").write_text(json.dumps({"clubs": club_out}, indent=2, ensure_ascii=False) + "\n")
    (APP / "class_sources.json").write_text(json.dumps({"classes": class_out}, indent=2, ensure_ascii=False) + "\n")


def source_links_from_config(cfg: dict, provenance: str, local_only: bool = False) -> list[dict]:
    out = []
    seen = set()
    for item in cfg.get("urls") or []:
        if local_only and item.get("locality") == "not_local":
            continue
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append({**item, "provenance": item.get("provenance") or provenance})
    if cfg.get("urls"):
        return out
    for key in ("website", "gallery", "facebook", "facebook_group", "instagram", "youtube", "tiktok"):
        url = (cfg.get(key) or "").strip()
        if url and url not in seen:
            seen.add(url)
            loc = "not_local" if key.endswith("international") else "local"
            out.append({"url": url, "platform": "facebook" if key.startswith("facebook") else ("website" if key in ("website", "gallery") else key), "locality": loc, "provenance": provenance})
    for item in cfg.get("not_local_urls") or []:
        url = item.get("url") if isinstance(item, dict) else item
        if url and url not in seen and not local_only:
            seen.add(url)
            out.append({"url": url, "platform": (item.get("platform") if isinstance(item, dict) else platform_for(url)), "locality": "not_local", "provenance": provenance})
    intl = (cfg.get("facebook_international") or "").strip()
    if intl and intl not in seen and not local_only:
        out.append({"url": intl, "platform": "facebook", "locality": "not_local", "provenance": provenance})
    return out


def run(limit_clubs: int | None = None, sailors: list[dict] | None = None) -> dict:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    club_pack = catalog_clubs(limit=limit_clubs)
    class_pack = catalog_classes()
    crosses = attach_cross_shares(club_pack["clubs"], class_pack["classes"], sailors=sailors)
    write_sources(club_pack["clubs"], class_pack["classes"])
    extract = club_pack["extract"] + class_pack["extract"]
    dest = ROOT / "data" / "sailingsa-social-directory.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(extract, indent=2, ensure_ascii=False))
    registry = ingest_registry(dest)
    summary = {
        "scraped_at": now,
        "clubs": len(club_pack["clubs"]),
        "club_urls": sum(len(c.get("urls") or []) for c in club_pack["clubs"].values()),
        "classes": len(class_pack["classes"]),
        "class_urls_local": sum(
            1 for c in class_pack["classes"].values() for u in c.get("urls") or [] if u.get("locality") == "local"
        ),
        "class_urls_not_local": sum(
            1 for c in class_pack["classes"].values() for u in c.get("urls") or [] if u.get("locality") == "not_local"
        ),
        "cross_shares": len(crosses),
        "registry": registry,
        "club_sources": str(APP / "club_sources.json"),
        "class_sources": str(APP / "class_sources.json"),
        "directory": str(dest),
        "420_local": [
            u
            for u in (class_pack["classes"].get("420") or {}).get("urls") or []
            if u.get("locality") == "local"
        ],
    }
    (ROOT / "data" / "directory-summary.json").write_text(json.dumps({"summary": summary, "cross_shares": crosses}, indent=2, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-clubs", type=int, default=None)
    parser.add_argument("--skip-write", action="store_true")
    args = parser.parse_args()
    if args.skip_write:
        print(json.dumps({"ok": True, "dry": True}))
        return
    print(json.dumps(run(limit_clubs=args.limit_clubs), indent=2, default=str))


if __name__ == "__main__":
    main()
