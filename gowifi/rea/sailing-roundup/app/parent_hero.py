#!/usr/bin/env python3
"""Step 2: inspect the parent event URL for its own images, pick a hero, store it on the box.

REA uses two tools on the available set:
  1. Local photograph tester (_event_photo_score + _is_event_photograph)
  2. Optional Bing image search (media_research.search) as an external API

The confirmed weekend roster is the only list that may be inspected.
"""
from __future__ import annotations

import argparse
import json
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


def images_from_html(url: str, html: str) -> list[dict]:
    """Pull photograph candidates off the parent event page HTML."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    found = []
    seen = set()
    for tag in soup.select(
        'meta[property="og:image"], meta[name="twitter:image"], article img, main img, .gallery img, img'
    ):
        src = tag.get("content") or tag.get("src") or tag.get("data-src") or ""
        if not src:
            continue
        link = urllib.parse.urljoin(url, src)
        if not IMAGE_EXT.search(link) or _bad_image_url(link) or _wiki_url(link):
            continue
        if link in seen:
            continue
        seen.add(link)
        alt = (tag.get("alt") or title or "").strip()
        found.append(
            {
                "url": link,
                "source_url": url,
                "title": alt,
                "credit": "SailingSA event page",
                "from_parent": True,
            }
        )
    return found[:16]


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


def available_images(facts: dict, parent_images: list[dict], extra=None, search_fn=None) -> list[dict]:
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
    for item in seed_media_images(facts):
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
        if not _is_event_photograph(raw):
            return -500
        from event_rewrite import _image_size

        size = _image_size(raw)
        if size:
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
    return {
        "slug": slug,
        "filename": filename,
        "local_path": f"media/{filename}",
        "bytes": len(raw),
        "source_url": image.get("source_url") or "",
        "remote_url": image.get("url") or "",
        "title": image.get("title") or "",
        "hero_score": image.get("hero_score") or 0,
        "picker": "event_photograph+parent_score",
        "status": "pass",
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
) -> dict:
    root = root or ROOT
    slug = rec.get("slug") or facts.get("slug") or ""
    url = rec.get("url") or facts.get("url") or ""
    if fetch_bytes is None:
        fetch_bytes = download_hero_bytes
    parent = inspect_parent(url, html=html, fetch_html=fetch_html)
    if use_external and search_fn is None:
        search_fn = _bing_images
    available = available_images(facts, parent["images"], extra=extra, search_fn=search_fn)
    best, ranked = pick_best_hero(available, facts, fetch_bytes=fetch_bytes)
    source_dir = root / "issues" / issue / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / f"{slug}-parent-media.json").write_text(
        json.dumps({**parent, "slug": slug, "available": len(available)}, indent=2, ensure_ascii=False) + "\n"
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
            for i in ranked[:8]
        ],
    }
    if not best:
        pack["status"] = "empty"
        pack["inspected"] = True
        pack["empty"] = True
        pack["error"] = "no usable hero in available images"
        (source_dir / f"{slug}-hero.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
        return pack
    raw = None
    local = best.get("local_file")
    if local and pathlib.Path(local).is_file():
        raw = pathlib.Path(local).read_bytes()
    elif fetch_bytes:
        try:
            raw = fetch_bytes(best)
        except Exception as exc:
            pack["error"] = str(exc)[:180]
    if not raw:
        pack["error"] = pack.get("error") or "hero chosen but bytes were not stored on the box"
        (source_dir / f"{slug}-hero.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
        return pack
    stored = store_on_box(issue, slug, best, raw, root=root)
    pack.update(stored)
    (source_dir / f"{slug}-hero.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
    return pack


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
    (root / "issues" / issue / "sources" / "weekend-heroes.json").write_text(
        json.dumps({"issue": issue, "heroes": heroes}, indent=2, ensure_ascii=False) + "\n"
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
