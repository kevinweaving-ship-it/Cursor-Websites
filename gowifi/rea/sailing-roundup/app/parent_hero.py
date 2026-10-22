#!/usr/bin/env python3
"""Step 2: inspect the parent event URL for its own images, pick a hero, store it on the box.

REA uses two tools on the available set:
  1. Local photograph tester (_event_photo_score + _is_event_photograph)
  2. Optional Bing image search (media_research.search) as an external API

The confirmed weekend roster is the only list that may be inspected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from event_rewrite import (
    _bad_image_url,
    _event_photo_score,
    _is_event_photograph,
    _wiki_url,
    facts_from_rows,
    is_chrome_image,
    seed_media_images,
)
from evidence_pipeline import is_scoresheet

IMAGE_EXT = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)
EXTERNAL_JUNK = re.compile(
    r"win big|real deals|racknerd|giveaway|buy now|how-are-river-dams|"
    r"lowendtalk|prize.?pool|click here|sponsored",
    re.I,
)
GENERIC_PHOTO_TOKEN = {
    "sailing",
    "regatta",
    "event",
    "club",
    "yacht",
    "boat",
    "fleet",
    "race",
    "dam",
    "bottle",
}
EDITORIAL_REQUESTS = {
    "2026-09-24-ayc-505-nationals": [
        {"title": "505 Nationals prizegiving", "prefer": ("prizegiving", "prize"), "order": 0},
        {"title": "505 Nationals trophy presentation", "prefer": ("trophy",), "order": 1},
        {"title": "505 Nationals on-water racing", "prefer": ("water", "racing"), "order": 2},
    ],
    "2026-09-25-tsc-420-nationals": [
        {"title": "420 Nationals overall winners", "prefer": ("prize", "winner", "overall", "adult"), "order": 0},
        {"title": "420 Nationals U17 boys", "prefer": ("u17", "under-17", "under 17"), "order": 1},
        {
            "title": "420 Nationals boat",
            "source_page": "https://www.facebook.com/share/1DGs9FyLwT/",
            "order": 2,
            "user_selected": True,
        },
    ],
}
# Size + byte-length fingerprints for recovered event photographs. Not identity claims.
KNOWN_PHOTO_HINTS = {
    "2026-09-25-tsc-420-nationals": (
        {"bytes": 76193, "size": (900, 600), "title": "420 Nationals overall winners"},
        {"bytes": 54216, "size": (383, 400), "title": "420 Nationals U17 boys"},
        {
            "bytes": 206583,
            "size": (2048, 1366),
            "title": "420 Nationals boat",
            "source_page": "https://www.facebook.com/share/1DGs9FyLwT/",
            "user_selected": True,
        },
    ),
}


def _largest_srcset(srcset: str, base: str) -> str:
    best = ""
    best_w = -1
    for part in (srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        link = urllib.parse.urljoin(base, bits[0])
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        if width >= best_w:
            best_w = width
            best = link
    return best


def images_from_html(url: str, html: str) -> list[dict]:
    """Pull photograph candidates off the parent event page HTML."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    found = []
    seen = set()

    def add(src: str, alt: str = "", srcset: str = ""):
        link = _largest_srcset(srcset, url) if srcset else ""
        if not link:
            link = urllib.parse.urljoin(url, src) if src else ""
        if not link or not IMAGE_EXT.search(link) or _bad_image_url(link) or _wiki_url(link):
            return
        if link in seen:
            return
        seen.add(link)
        found.append(
            {
                "url": link,
                "source_url": url,
                "title": (alt or title or "").strip(),
                "credit": "SailingSA event page",
                "from_parent": True,
            }
        )

    for tag in soup.select(
        'meta[property="og:image"], meta[name="twitter:image"], article img, main img, '
        ".gallery img, figure img, picture source, img, source, a[href]"
    ):
        add(
            tag.get("content")
            or tag.get("src")
            or tag.get("data-src")
            or tag.get("data-lazy-src")
            or tag.get("data-original")
            or tag.get("data-full")
            or tag.get("data-large")
            or tag.get("href")
            or "",
            tag.get("alt") or title,
            tag.get("srcset") or tag.get("data-srcset") or "",
        )
    return found[:32]


def inspect_parent(url: str, html: str | None = None, fetch_html=None) -> dict:
    """Check whether the parent event URL has its own media."""
    text = html
    error = ""
    if text is None and fetch_html:
        try:
            text = fetch_html(url) or ""
        except Exception as exc:
            error = str(exc)[:180]
            text = ""
    if text is None:
        try:
            from event_rewrite import UA, _http_get

            raw, _ = _http_get(url, UA, timeout=20)
            text = raw.decode("utf-8", "replace")
        except Exception as exc:
            error = str(exc)[:180]
            text = ""
    images = images_from_html(url, text) if text else []
    return {
        "url": url,
        "has_media": bool(images),
        "images": images,
        "error": error,
    }


def external_image_candidates(facts: dict, search_fn=None) -> list[dict]:
    """External API: Bing image search keyed to the confirmed event equals card."""
    search_fn = search_fn or _bing_images
    name = facts.get("title") or facts.get("name") or ""
    host = facts.get("club") or facts.get("club_name") or ""
    fleets = " ".join(facts.get("fleets") or facts.get("classes") or [])
    query = " ".join(part for part in (name, host, fleets, "sailing") if part).strip()
    if not query:
        return []
    out = []
    try:
        for item in search_fn(query) or []:
            image = item.get("image_url") or item.get("url") or ""
            source = item.get("source_url") or ""
            title = item.get("title") or ""
            if not image or _bad_image_url(image) or _wiki_url(image):
                continue
            out.append(
                {
                    "url": image,
                    "source_url": source or image,
                    "title": title,
                    "credit": source,
                    "from_external": True,
                }
            )
    except Exception:
        return []
    return out[:12]


def _bing_images(query: str) -> list[dict]:
    from media_research import search

    return search(query, "images")


def available_images(facts: dict, parent_images: list[dict], extra=None, search_fn=None, root=None) -> list[dict]:
    """Parent page first, then seed files, then optional extra/external candidates."""
    out = []
    seen = set()

    def add(item):
        url = (item.get("url") or item.get("image_url") or item.get("local_file") or "").split("#")[0]
        if not url or url in seen:
            return
        seen.add(url)
        out.append(item)

    for item in parent_images or []:
        add(item)
    for item in extra or []:
        if item.get("verified_previous") or item.get("from_issue"):
            add(item)
    for item in seed_media_images(facts, root=root):
        add(item)
    for item in extra or []:
        add(item)
    if search_fn is not None:
        for item in external_image_candidates(facts, search_fn=search_fn):
            add(item)
    return out


def _external_belongs(item: dict, facts: dict) -> bool:
    """Bing/web hits must name this event, class, or winner — not a generic dam or an ad."""
    blob = " ".join(
        (
            item.get("url") or "",
            item.get("source_url") or "",
            item.get("title") or "",
        )
    ).lower()
    if EXTERNAL_JUNK.search(blob):
        return False
    title = (facts.get("title") or facts.get("name") or "").strip().lower()
    if title and title in blob:
        return True
    winner = (facts.get("winner") or facts.get("winner_helm") or "").strip().lower()
    if winner and winner not in {"the leader", "mac"} and winner in blob:
        return True
    tokens = []
    for part in (title, facts.get("slug") or "", facts.get("class_name") or ""):
        tokens.extend(re.findall(r"[a-z0-9]+", str(part).lower()))
    meaningful = [t for t in tokens if t not in GENERIC_PHOTO_TOKEN and len(t) > 3]
    return bool(meaningful) and sum(1 for t in set(meaningful) if t in blob) >= 2


def score_hero(item: dict, facts: dict, raw: bytes | None = None) -> int:
    """Identify the best suited hero from available images."""
    url = item.get("url") or item.get("local_file") or ""
    source = item.get("source_url") or ""
    title = item.get("title") or ""
    if is_chrome_image(url, title) or is_chrome_image(source, title):
        return -1000
    if is_scoresheet({"url": url, "title": title, "caption": title}):
        return -1000
    if item.get("from_external") and not _external_belongs(item, facts):
        return -1000
    score = _event_photo_score(item, facts)
    if item.get("from_parent"):
        score += 25
    if item.get("seed"):
        score += 80
    if raw is not None and not item.get("seed"):
        from event_rewrite import _image_size
        from evidence_pipeline import MEDIA_REGIONS

        size = _image_size(raw)
        if size and any(tuple(spec.get("dimensions") or []) == size for spec in MEDIA_REGIONS.values()):
            score += 80
        elif not _is_event_photograph(raw):
            return -500
        elif size:
            score += min(size) // 20
    return score


def pick_best_hero(candidates: list[dict], facts: dict, fetch_bytes=None) -> tuple[dict | None, list[dict]]:
    ranked = []
    for item in candidates or []:
        raw = None
        if fetch_bytes:
            try:
                raw = fetch_bytes(item)
            except Exception:
                raw = None
        scored = dict(item)
        scored["hero_score"] = score_hero(item, facts, raw)
        ranked.append(scored)
    ranked.sort(key=lambda x: x.get("hero_score") or 0, reverse=True)
    best = next((item for item in ranked if (item.get("hero_score") or 0) >= 40 or item.get("seed")), None)
    return best, ranked


def existing_issue_images(issue: str, slug: str, root: pathlib.Path | None = None) -> list[dict]:
    """Keep previously verified files when a later discovery pass fails."""
    root = root or ROOT
    folder = root / "issues" / issue / "media"
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        if slug not in path.name:
            continue
        out.append(
            {
                "url": str(path),
                "local_file": str(path),
                "source_url": "",
                "title": slug,
                "credit": "Event photography",
                "verified_previous": True,
                "from_issue": True,
                "seed": True,
            }
        )
    return out


def content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw or b"").hexdigest()


def visual_hash(raw: bytes) -> str:
    """Tiny average hash for near-duplicate rejection. Empty when pixels cannot be read."""
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:
        return ""
    try:
        im = Image.open(BytesIO(raw)).convert("L").resize((8, 8))
    except Exception:
        return ""
    pixels = list(im.getdata())
    avg = sum(pixels) / len(pixels) if pixels else 0
    return "".join("1" if p > avg else "0" for p in pixels)


def visual_similar(left: str, right: str, max_dist: int = 6) -> bool:
    if not left or not right or len(left) != len(right):
        return False
    return sum(a != b for a, b in zip(left, right)) <= max_dist


def image_dates(raw: bytes, item: dict | None = None) -> dict:
    """Publication/upload date is not a capture date."""
    published = (item or {}).get("published") or (item or {}).get("publication_date") or ""
    captured = ""
    try:
        from io import BytesIO

        from PIL import Image
        from PIL.ExifTags import TAGS

        im = Image.open(BytesIO(raw))
        exif = im.getexif() if hasattr(im, "getexif") else {}
        tags = {TAGS.get(k, k): v for k, v in (exif or {}).items()}
        captured = str(tags.get("DateTimeOriginal") or "")
    except Exception:
        captured = ""
    return {
        "publication_date": published,
        "capture_date": captured,
        "date_kind": "capture" if captured else ("publication" if published else "unknown"),
    }


def event_search_queries(facts: dict) -> list[str]:
    name = (facts.get("title") or facts.get("name") or "").strip()
    year = str(facts.get("start") or facts.get("end") or "")[:4]
    venue = (facts.get("club_name") or facts.get("club") or "").strip()
    queries = []
    if name and year:
        queries.extend(
            [
                f"{name} {year} {venue}".strip(),
                f"{name} {year} results",
                f"{name} {year} report",
                f"{name} {year} photos",
            ]
        )
    seen = []
    for query in queries:
        query = " ".join(query.split())
        if query and query not in seen:
            seen.append(query)
    return seen


def harvest_requested_page(url: str, facts: dict) -> dict:
    """Follow one requested source page. Never substitute a parent-post cover."""
    from event_rewrite import harvest_source_images

    try:
        images = harvest_source_images(url) or []
    except Exception as exc:
        name = type(exc).__name__
        if any(token in str(exc).lower() for token in ("403", "401", "blocked", "login")):
            return {"status": "access_blocked", "reason": name, "images": [], "source_page": url}
        return {"status": "download_failed", "reason": name, "images": [], "source_page": url}
    kept = []
    for item in images:
        item = dict(item)
        item["source_url"] = url
        item["user_selected"] = True
        item["from_requested"] = True
        if _facebook_page_cover(item, url):
            continue
        kept.append(item)
    if not kept:
        return {"status": "access_blocked" if "facebook.com" in url else "empty", "reason": "requested photo unavailable", "images": [], "source_page": url}
    return {"status": "ok", "images": kept, "source_page": url}


def _collage_panels(slug: str, raw: bytes, item: dict) -> list[dict]:
    """Split a known 505 collage into the approved photograph panels only."""
    from event_rewrite import _image_size
    from evidence_pipeline import MEDIA_REGIONS, crop_media_region

    if "505-nationals" not in (slug or ""):
        return []
    size = _image_size(raw)
    if not size:
        return []
    for spec in MEDIA_REGIONS.values():
        if tuple(spec.get("dimensions") or []) != size:
            continue
        out = []
        inset = int(spec.get("inset") or 16)
        for panel in spec.get("regions") or []:
            if is_scoresheet({"title": panel.get("label") or "", "panel_label": panel.get("label") or ""}):
                continue
            cropped = crop_media_region(raw, panel.get("rect"), inset=inset, expected=spec.get("dimensions"))
            if not cropped:
                continue
            piece = dict(item)
            piece.pop("_raw", None)
            piece["title"] = panel.get("label") or item.get("title")
            piece["source_region"] = panel.get("rect")
            piece["source_dimensions"] = spec.get("dimensions")
            piece["cropped"] = True
            piece["hero_score"] = max(int(item.get("hero_score") or 0), 80)
            piece["verified_previous"] = True
            piece["content_hash"] = content_hash(cropped)
            piece["visual_hash"] = visual_hash(cropped)
            piece["_raw"] = cropped
            piece["credit"] = item.get("credit") or "RSA 505"
            out.append(piece)
        return out
    return []


def classify_known_photo(raw: bytes, item: dict, slug: str) -> dict:
    """Attach recovered roles from file fingerprints. Never infer winners from pixels."""
    from event_rewrite import _image_size

    scored = dict(item)
    size = _image_size(raw) if raw else None
    for hint in KNOWN_PHOTO_HINTS.get(slug) or ():
        if hint.get("bytes") and len(raw or b"") != hint["bytes"]:
            continue
        if hint.get("size") and size != tuple(hint["size"]):
            continue
        scored["title"] = hint.get("title") or scored.get("title")
        if hint.get("source_page"):
            scored["source_url"] = scored.get("source_url") or hint["source_page"]
            scored["user_selected"] = bool(hint.get("user_selected"))
        return scored
    blob = " ".join(
        (
            scored.get("title") or "",
            scored.get("url") or "",
            scored.get("local_file") or "",
            scored.get("source_url") or "",
        )
    ).lower()
    if "1dgs9fylwt" in blob:
        scored["title"] = "420 Nationals boat"
        scored["user_selected"] = True
        scored["source_url"] = scored.get("source_url") or "https://www.facebook.com/share/1DGs9FyLwT/"
    return scored


def recover_known_photos(issue: str, slug: str, root: pathlib.Path) -> list[dict]:
    """Discovery gap: a photo not in this issue folder may still exist on the box."""
    out = []
    seen = set()
    folders = [
        root / "data" / "seed-media",
        root / ".builds",
        root / "issues" / issue / "media",
        root / "public" / "issues" / issue / "media",
    ]
    for folder in folders:
        if not folder.is_dir():
            continue
        paths = folder.rglob("*") if folder.name == ".builds" else folder.iterdir()
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            if slug not in path.name and not any(
                token in path.name.lower() for token in ("420", "505", "u17", "overall", "boat")
            ):
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            key = (len(raw), content_hash(raw))
            if key in seen:
                continue
            seen.add(key)
            item = classify_known_photo(
                raw,
                {
                    "url": str(path),
                    "local_file": str(path),
                    "source_url": "",
                    "title": slug,
                    "credit": "Event photography",
                    "verified_previous": True,
                    "seed": True,
                },
                slug,
            )
            if item.get("title") in {slug, ""} and slug not in path.name:
                continue
            out.append(item)
    return out


def _facebook_page_cover(item: dict, requested: str) -> bool:
    from event_rewrite import _facebook_page_chrome

    source = item.get("source_url") or ""
    image = item.get("url") or ""
    if "/share/" in (requested or "") and _facebook_page_chrome(source, image):
        return True
    return False


def editorial_requests(slug: str) -> list[dict]:
    return list(EDITORIAL_REQUESTS.get(slug) or [])


def apply_editorial_order(chosen: list[dict], slug: str) -> list[dict]:
    requests = editorial_requests(slug)
    if not requests or not chosen:
        return chosen[:4]
    used = set()
    ordered = []
    for spec in sorted(requests, key=lambda item: item.get("order") or 0):
        prefer = tuple(p.lower() for p in (spec.get("prefer") or ()))
        source_page = (spec.get("source_page") or "").lower()
        match = None
        for idx, item in enumerate(chosen):
            if idx in used:
                continue
            blob = " ".join(
                (
                    item.get("title") or "",
                    item.get("url") or "",
                    item.get("source_url") or "",
                    item.get("local_file") or "",
                )
            ).lower()
            if source_page and source_page in blob:
                match = idx
                break
            if prefer and any(token in blob for token in prefer):
                match = idx
                break
        if match is None:
            continue
        used.add(match)
        item = dict(chosen[match])
        item["title"] = spec.get("title") or item.get("title")
        item["user_selected"] = bool(spec.get("user_selected") or item.get("user_selected"))
        ordered.append(item)
    for idx, item in enumerate(chosen):
        if idx in used:
            continue
        ordered.append(item)
    return ordered[:4]


def rank_with_vision(item: dict, analysis: dict | None) -> int:
    score = int(item.get("hero_score") or 0)
    if item.get("user_selected") or item.get("verified_previous"):
        score += 400
    if not analysis:
        return score
    category = (analysis.get("category") or "").lower()
    role = (analysis.get("role") or "").lower()
    if category in {"logo", "results-sheet", "poster"} or role == "reject":
        return -1000
    if category == "on-water":
        score += 80
    if category == "prizegiving":
        score += 50
    if role == "lead":
        score += 40
    try:
        score += int(float(analysis.get("relevance") or 0) * 20)
    except (TypeError, ValueError):
        pass
    return score


def select_images(ranked: list[dict], slug: str, analyses: dict | None = None) -> list[dict]:
    """Keep at most four suitable images. User order wins. Do not fill empty slots."""
    analyses = analyses or {}
    usable = []
    seen_hash = set()
    seen_visual = []
    for item in ranked or []:
        if (item.get("hero_score") or 0) < 40 and not item.get("seed") and not item.get("user_selected") and not item.get("verified_previous"):
            continue
        analysis = analyses.get(item.get("content_hash") or item.get("url") or "")
        if analysis and (analysis.get("role") == "reject" or (analysis.get("category") or "") in {"logo", "results-sheet"}):
            continue
        digest = item.get("content_hash") or ""
        if digest and digest in seen_hash:
            continue
        vhash = item.get("visual_hash") or ""
        if vhash and any(visual_similar(vhash, old) for old in seen_visual):
            continue
        if digest:
            seen_hash.add(digest)
        if vhash:
            seen_visual.append(vhash)
        usable.append(item)
    usable.sort(key=lambda item: rank_with_vision(item, analyses.get(item.get("content_hash") or item.get("url") or "")), reverse=True)
    return apply_editorial_order(usable, slug)


def store_on_box(issue: str, slug: str, image: dict, raw: bytes, root: pathlib.Path | None = None) -> dict:
    """Write the chosen hero onto the box (issues + public media)."""
    root = root or ROOT
    ext = ".jpg"
    path = ((image.get("local_file") or image.get("url") or "")).lower()
    for cand in (".png", ".webp", ".jpeg", ".jpg"):
        if path.endswith(cand):
            ext = ".jpg" if cand == ".jpeg" else cand
            break
    filename = f"{slug}-hero{ext}"
    for folder in (root / "issues" / issue / "media", root / "public" / "issues" / issue / "media"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_bytes(raw)
    from event_rewrite import _image_size

    size = _image_size(raw) or (0, 0)
    dates = image_dates(raw, image)
    digest = content_hash(raw)
    return {
        "slug": slug,
        "filename": filename,
        "local_path": f"media/{filename}",
        "bytes": len(raw),
        "content_hash": digest,
        "visual_hash": visual_hash(raw),
        "width": size[0],
        "height": size[1],
        "publication_date": dates["publication_date"],
        "capture_date": dates["capture_date"],
        "date_kind": dates["date_kind"],
        "source_url": image.get("source_url") or "",
        "remote_url": image.get("url") or "",
        "title": image.get("title") or "",
        "credit": image.get("credit") or "Event photography",
        "caption": image.get("title") or "",
        "hero_score": image.get("hero_score") or 0,
        "picker": "event_photograph+parent_score",
        "status": "pass",
        "source_region": image.get("source_region") if not image.get("cropped") else None,
        "source_dimensions": image.get("source_dimensions") if not image.get("cropped") else None,
        "cropped": bool(image.get("cropped")),
        "user_selected": bool(image.get("user_selected")),
        "verified_previous": bool(image.get("verified_previous")),
    }


def download_hero_bytes(item: dict) -> bytes:
    """Fetch the chosen hero onto the box. Used by dry-run and Monday publish."""
    local = item.get("local_file") or ""
    if local and pathlib.Path(local).is_file():
        return pathlib.Path(local).read_bytes()
    url = item.get("url") or ""
    if url.startswith("file://"):
        path = pathlib.Path(urllib.parse.urlparse(url).path)
        return path.read_bytes() if path.is_file() else b""
    if url.startswith("http://") or url.startswith("https://"):
        from event_rewrite import UA, _http_get

        raw, _ = _http_get(url, UA, timeout=20)
        return raw
    return b""


def _load_bytes(item: dict, fetch_bytes=None) -> tuple[bytes, str]:
    local = item.get("local_file") or ""
    if local and pathlib.Path(local).is_file():
        return pathlib.Path(local).read_bytes(), ""
    if not fetch_bytes:
        return b"", "download_failed"
    try:
        raw = fetch_bytes(item) or b""
    except Exception as exc:
        name = type(exc).__name__
        if any(token in str(exc).lower() for token in ("403", "401", "blocked", "login")):
            return b"", "access_blocked"
        return b"", name
    return raw, "" if raw else "download_failed"


def collect_event_hero(
    issue: str,
    rec: dict,
    facts: dict,
    root: pathlib.Path | None = None,
    html: str | None = None,
    extra=None,
    fetch_html=None,
    fetch_bytes=None,
    search_fn=None,
    use_external=False,
    analyze=None,
    harvest_sources=None,
) -> dict:
    root = root or ROOT
    slug = rec.get("slug") or facts.get("slug") or ""
    url = rec.get("url") or facts.get("url") or ""
    if fetch_bytes is None:
        fetch_bytes = download_hero_bytes
    parent = inspect_parent(url, html=html, fetch_html=fetch_html)
    parent_status = "ok"
    if parent.get("error"):
        err = (parent.get("error") or "").lower()
        parent_status = "access_blocked" if any(x in err for x in ("403", "401", "blocked")) else "download_failed"
    previous = existing_issue_images(issue, slug, root=root)
    recovered = recover_known_photos(issue, slug, root=root)
    requested = []
    requested_status = []
    event_pages = []
    if harvest_sources is None:
        harvest_sources = use_external
    if use_external and harvest_sources:
        from event_rewrite import SEED_URLS

        for spec in editorial_requests(slug):
            page = spec.get("source_page") or ""
            if not page:
                continue
            harvested = harvest_requested_page(page, facts)
            requested_status.append({"source_page": page, "status": harvested.get("status"), "reason": harvested.get("reason")})
            for item in harvested.get("images") or []:
                item["title"] = spec.get("title") or item.get("title")
                item["user_selected"] = True
                requested.append(item)
        for page in SEED_URLS.get(slug) or []:
            if page in {spec.get("source_page") for spec in editorial_requests(slug)}:
                continue
            harvested = harvest_requested_page(page, facts)
            event_pages.append({"source_page": page, "status": harvested.get("status"), "reason": harvested.get("reason")})
            for item in harvested.get("images") or []:
                item["from_event_source"] = True
                item["user_selected"] = False
                requested.append(item)
    extra_items = list(previous) + list(recovered) + list(requested) + list(extra or [])
    search_status = {"status": "skipped", "queries": [], "provider": ""}
    if use_external and search_fn is None:
        from ai_tools import search_images as _search_images

        def search_fn(query):
            result = _search_images(query)
            search_status["status"] = result.get("status") or "ok"
            search_status["provider"] = result.get("provider") or search_status.get("provider") or ""
            search_status["queries"].append(
                {
                    "query": query,
                    "status": result.get("status"),
                    "count": len(result.get("items") or []),
                    "provider": result.get("provider") or "",
                }
            )
            if result.get("status") == "ok":
                return result.get("items") or []
            return []

        queries = event_search_queries(facts)
        extra_items.extend(
            item
            for query in queries
            for item in (search_fn(query) or [])
        )
        search_fn = None
    elif use_external and search_fn is not None:
        search_status["status"] = "ok"
    available = available_images(
        facts,
        parent["images"],
        extra=extra_items,
        search_fn=search_fn,
        root=root,
    )
    best, ranked = pick_best_hero(available, facts, fetch_bytes=fetch_bytes)
    analyses = {}
    gaps = []
    enriched = []
    for item in ranked:
        raw, err = _load_bytes(item, fetch_bytes=fetch_bytes)
        scored = dict(item)
        if err:
            scored["gap"] = "access_blocked" if err == "access_blocked" else "download_failed"
            gaps.append({"url": item.get("url") or item.get("local_file"), "status": scored["gap"]})
            enriched.append(scored)
            continue
        if not raw:
            scored["gap"] = "download_failed"
            gaps.append({"url": item.get("url") or item.get("local_file"), "status": "download_failed"})
            enriched.append(scored)
            continue
        scored = classify_known_photo(raw, scored, slug)
        scored["content_hash"] = content_hash(raw)
        scored["visual_hash"] = visual_hash(raw)
        scored["_raw"] = raw
        panels = _collage_panels(slug, raw, scored)
        if panels:
            enriched.extend(panels)
            continue
        if _facebook_page_cover(scored, scored.get("source_url") or "") and not scored.get("user_selected"):
            scored["gap"] = "unrelated"
            enriched.append(scored)
            continue
        run_vision = analyze
        if run_vision is None:
            run_vision = (os.getenv("ROUNDUP_USE_VISION") or "1").strip() != "0"
        if run_vision:
            try:
                from ai_tools import analyze_image

                vision = analyze(raw, {"event": facts, "source_url": scored.get("source_url")}) if callable(analyze) else analyze_image(raw, {"event": facts})
            except Exception as exc:
                vision = {"status": "analysis_failed", "reason": type(exc).__name__}
            status = (vision or {}).get("status") or "analysis_failed"
            if status != "ok":
                gaps.append({"url": scored.get("url"), "status": status, "reason": (vision or {}).get("reason")})
                if status == "vision_unavailable":
                    scored["vision_status"] = status
                elif not scored.get("verified_previous") and not scored.get("user_selected"):
                    scored["hero_score"] = min(scored.get("hero_score") or 0, 0)
                    scored["gap"] = status
                    enriched.append(scored)
                    continue
            else:
                scored["vision"] = {k: vision.get(k) for k in ("category", "role", "relevance", "description", "reasons") if k in vision}
                scored["hero_score"] = rank_with_vision(scored, vision)
                analyses[scored["content_hash"]] = vision
        enriched.append(scored)
    chosen = select_images(enriched, slug, analyses)
    source_dir = root / "issues" / issue / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / f"{slug}-parent-media.json").write_text(
        json.dumps({**parent, "slug": slug, "available": len(available), "parent_status": parent_status}, indent=2, ensure_ascii=False) + "\n"
    )
    pack = {
        "slug": slug,
        "parent_url": url,
        "parent_has_media": parent["has_media"],
        "available": len(available),
        "status": "fail",
        "local_path": "",
        "picker": "event_photograph+parent_score",
        "candidates": [
            {"url": i.get("url") or i.get("local_file"), "hero_score": i.get("hero_score"), "title": i.get("title")}
            for i in enriched[:8]
        ],
        "gaps": gaps,
        "search_status": search_status,
        "requested": requested_status,
        "event_pages": event_pages,
    }
    required_failed = []
    if use_external and search_status.get("status") not in ("ok", "empty", "skipped"):
        required_failed.append("search:" + str(search_status.get("status") or "provider_failure"))
    vision_gaps = [g for g in gaps if (g.get("status") or "") in {"vision_unavailable", "analysis_failed"}]
    if use_external and (os.getenv("ROUNDUP_USE_VISION") or "1").strip() != "0" and vision_gaps and not analyses:
        required_failed.append("vision:" + vision_gaps[0].get("status"))
    pack["enrichment"] = "degraded" if required_failed else "ok"
    pack["enrichment_failures"] = required_failed
    if not chosen:
        if previous:
            chosen = [dict(item, hero_score=item.get("hero_score") or 80) for item in previous[:4]]
            pack["preserved_previous"] = True
        else:
            pack["status"] = "empty"
            pack["gap"] = "no_suitable_images" if not parent.get("error") else parent_status
            pack["inspected"] = True
            pack["empty"] = True
            pack["error"] = "no usable hero in available images"
            (source_dir / f"{slug}-hero.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
            _write_media_log(source_dir, slug, parent, pack, [])
            return pack
    stored_images = []
    for idx, item in enumerate(chosen[:4]):
        raw = item.pop("_raw", None)
        if raw is None:
            raw, err = _load_bytes(item, fetch_bytes=fetch_bytes)
            if err or not raw:
                continue
        name = slug if idx == 0 else f"{slug}-{idx + 1}"
        stored_images.append(store_on_box(issue, name, item, raw, root=root))
    if not stored_images and previous:
        for idx, item in enumerate(previous[:4]):
            raw, _err = _load_bytes(item, fetch_bytes=fetch_bytes)
            if not raw:
                continue
            name = slug if idx == 0 else f"{slug}-{idx + 1}"
            stored_images.append(store_on_box(issue, name, item, raw, root=root))
        pack["preserved_previous"] = True
    if not stored_images:
        pack["status"] = "download_failed"
        pack["error"] = pack.get("error") or "hero chosen but bytes were not stored on the box"
        (source_dir / f"{slug}-hero.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
        _write_media_log(source_dir, slug, parent, pack, [])
        return pack
    first = stored_images[0]
    pack.update(first)
    pack["images"] = stored_images
    pack["image_count"] = len(stored_images)
    pack["status"] = "pass"
    (source_dir / f"{slug}-hero.json").write_text(json.dumps({k: v for k, v in pack.items() if k != "candidates"} | {"candidates": pack["candidates"]}, indent=2, ensure_ascii=False) + "\n")
    _write_media_log(source_dir, slug, parent, pack, stored_images)
    return pack


def _write_media_log(source_dir: pathlib.Path, slug: str, parent: dict, pack: dict, selected: list[dict]) -> None:
    (source_dir / f"{slug}-media-log.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "parent": parent.get("url"),
                "parent_error": parent.get("error") or "",
                "available": pack.get("available"),
                "selected": [x.get("local_path") for x in selected],
                "status": pack.get("status"),
                "gaps": pack.get("gaps") or [],
                "search_status": pack.get("search_status") or {},
                "requested": pack.get("requested") or [],
                "event_pages": pack.get("event_pages") or [],
                "enrichment": pack.get("enrichment") or "ok",
                "enrichment_failures": pack.get("enrichment_failures") or [],
                "preserved_previous": bool(pack.get("preserved_previous")),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def store_roster_heroes(issue: str, events: list[dict], facts_by_slug: dict, root=None, **hooks) -> dict:
    """Run Step 2 for every confirmed roster event. Later steps must not invent other slugs."""
    root = root or ROOT
    heroes = {}
    for rec in events or []:
        if rec.get("status") != "pass":
            continue
        slug = rec.get("slug") or ""
        facts = dict(facts_by_slug.get(slug) or {})
        facts.setdefault("slug", slug)
        facts.setdefault("url", rec.get("url") or "")
        facts.setdefault("title", rec.get("name") or rec.get("title") or "")
        facts.setdefault("fleets", (rec.get("equals") or {}).get("fleets") or [])
        heroes[slug] = collect_event_hero(issue, rec, facts, root=root, **hooks)
    (root / "issues" / issue / "sources").mkdir(parents=True, exist_ok=True)
    degraded = {
        slug: {"status": pack.get("search_status"), "failures": pack.get("enrichment_failures"), "gaps": pack.get("gaps")}
        for slug, pack in heroes.items()
        if pack.get("enrichment") == "degraded"
    }
    enrichment = {
        "issue": issue,
        "degraded": bool(degraded),
        "events": {slug: pack.get("enrichment") for slug, pack in heroes.items()},
        "failures": degraded,
    }
    (root / "issues" / issue / "sources" / "weekend-heroes.json").write_text(
        json.dumps({"issue": issue, "heroes": heroes, "enrichment": enrichment}, indent=2, ensure_ascii=False) + "\n"
    )
    (root / "issues" / issue / "sources" / "enrichment.json").write_text(
        json.dumps(enrichment, indent=2, ensure_ascii=False) + "\n"
    )
    return heroes


def load_heroes(issue: str, slugs: list[str], root: pathlib.Path | None = None) -> dict:
    root = root or ROOT
    out = {}
    for slug in slugs:
        path = root / "issues" / issue / "sources" / f"{slug}-hero.json"
        if path.is_file():
            out[slug] = json.loads(path.read_text())
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Inspect parent event URLs and store the best hero on the box.")
    p.add_argument("--monday", required=True)
    p.add_argument("--root")
    p.add_argument("--no-external", action="store_true")
    args = p.parse_args(argv)
    root = pathlib.Path(args.root) if args.root else ROOT
    from gates import load_roster

    roster = load_roster(args.monday, root=root) or {}
    if not roster.get("confirmed"):
        print(json.dumps({"monday": args.monday, "error": "weekend roster is not confirmed"}))
        return 1
    facts_by_slug = {}
    for rec in roster.get("events") or []:
        slug = rec.get("slug") or ""
        rows_path = root / "issues" / args.monday / "sources" / f"{slug}-results.json"
        if rows_path.is_file():
            facts_by_slug[slug] = facts_from_rows(slug, json.loads(rows_path.read_text()))
    hooks = {}
    if args.no_external:
        hooks["search_fn"] = None
    heroes = store_roster_heroes(args.monday, roster.get("events") or [], facts_by_slug, root=root, **hooks)
    print(json.dumps({"monday": args.monday, "heroes": {k: v.get("status") for k, v in heroes.items()}}, indent=2))
    return 0 if heroes and all(v.get("status") == "pass" for v in heroes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
