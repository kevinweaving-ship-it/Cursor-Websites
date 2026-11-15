#!/usr/bin/env python3
"""Attach Grok Bot photos to weekly roundup issues.

The live job is /opt/rea/work/sailing-roundup (sailing-roundup.timer).
Call this on every run, before or after the edition build. It reads
external-photos/MANIFEST.md, fills events that still need a photo, and
does not change result tables, story paragraphs, or winner lines.

Sync the manifest from the Grok Bot box first when ROUNDUP_PHOTOS_RSYNC
is set, for example:

    user@grok-bot:/workspace/roundup-photos/

into {roundup-root}/external-photos/. The bot adds rows on Mondays;
this script still checks the manifest on every run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAX_IMAGE_BYTES = 8_000_000
SITE = "https://sailingsa.co.za/sailing-roundup/"
HEADER_ALIASES = {
    "edition": "edition",
    "issue": "edition",
    "event id": "event_id",
    "event_id": "event_id",
    "event": "event_id",
    "local file": "file",
    "file": "file",
    "path": "file",
    "image url": "image_url",
    "image_url": "image_url",
    "url": "image_url",
    "source_url": "source_url",
    "source": "source_url",
    "caption": "caption",
    "credit": "credit",
}
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})-.+")
BANNED = re.compile(
    r"burgee|pennant|ensign|club[-_ ]?logo|event[-_ ]?logo|class[-_ ]?logo|"
    r"artwork/(?:event|club|class)|/t39\.30808-1/|/picture\?|profile[_-]?pic",
    re.I,
)


def parse_manifest(text: str) -> list[dict]:
    """Read a markdown table. A row with a cell EXCLUDED is skipped."""
    rows = []
    header = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [_cell(part) for part in line.strip("|").split("|")]
        if not any(cells):
            continue
        if header is None:
            mapped = [_header_name(cell) for cell in cells]
            if "edition" in mapped and "event_id" in mapped:
                header = mapped
            continue
        if all(set(cell) <= set("-: ") and cell for cell in cells):
            continue
        if any(cell.upper() == "EXCLUDED" for cell in cells):
            continue
        item = {}
        for key, value in zip(header, cells):
            if key and key not in item:
                item[key] = value
        edition = item.get("edition", "")
        event_id = item.get("event_id", "")
        if not edition or not event_id:
            continue
        if not item.get("file") and not item.get("image_url"):
            continue
        rows.append(item)
    return rows


def _cell(value: str) -> str:
    return value.strip().strip("`")


def _header_name(value: str) -> str:
    return HEADER_ALIASES.get(re.sub(r"\s+", " ", value).strip().lower(), "")


def hero_filename(event_id: str, edition: str, ext: str) -> str:
    stem = event_id if DATE_PREFIX.match(event_id) else f"{edition}-{event_id}"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-")
    return f"{stem}-hero{ext}"


def _ext_for(data: bytes, hint: str) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    lower = hint.lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        if lower.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ""


def _public_http(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        return False
    if host == "169.254.169.254" or host.startswith("127.") or host == "::1":
        return False
    return True


def download_image(url: str, opener=None) -> bytes | None:
    if not url or not _public_http(url) or BANNED.search(url):
        return None
    request = urllib.request.Request(url, headers={"User-Agent": "SailingSA-Roundup/1.0"})
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request, timeout=20) as response:
            data = response.read(MAX_IMAGE_BYTES + 1)
    except (OSError, urllib.error.URLError, ValueError):
        return None
    if not data or len(data) > MAX_IMAGE_BYTES or not _ext_for(data, url):
        return None
    return data


def local_image(photos_dir: Path, rel: str) -> bytes | None:
    if not rel or BANNED.search(rel):
        return None
    root = photos_dir.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    data = candidate.read_bytes()
    if len(data) > MAX_IMAGE_BYTES or not _ext_for(data, candidate.name):
        return None
    return data


def load_photo(row: dict, photos_dir: Path, opener=None) -> tuple[bytes, str] | None:
    url = row.get("image_url") or ""
    data = download_image(url, opener=opener)
    hint = url
    if data is None:
        data = local_image(photos_dir, row.get("file") or "")
        hint = row.get("file") or ""
    if data is None:
        return None
    ext = _ext_for(data, hint)
    if not ext:
        return None
    return data, ext


def _image_block(media_name: str, row: dict, event_id: str, digest: str) -> dict:
    return {
        "type": "image",
        "url": f"media/{media_name}",
        "alt": row.get("caption") or "",
        "caption": row.get("caption") or "",
        "credit": row.get("credit") or "",
        "source_url": row.get("source_url") or row.get("image_url") or "",
        "rights_status": "source_attributed",
        "content_hash": digest,
        "event_verified": True,
        "verified_event_id": event_id,
        "role": "hero",
        "category": "on-water",
        "verification": "reviewed_source_and_pixels",
    }


def _hero_object(media_name: str, row: dict, event_id: str) -> dict:
    return {
        "url": f"media/{media_name}",
        "source_url": row.get("source_url") or row.get("image_url") or "",
        "caption": row.get("caption") or "",
        "credit": row.get("credit") or "",
        "verification": "reviewed_source_and_pixels",
        "focus": None,
        "event_id": event_id,
    }


def _needs_photo(article: dict) -> bool:
    if article.get("needs_external") is True:
        return True
    return not article.get("hero_image")


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def insert_hero_html(html: str, event_id: str, media_name: str, caption: str, credit: str) -> str:
    """Insert the hero figure without changing the story copy."""
    match = re.search(
        r"<article\b[^>]*\bid=(['\"])" + re.escape(event_id) + r"\1[^>]*>.*?</article>",
        html,
        re.I | re.S,
    )
    if not match:
        return html
    block = match.group(0)
    if re.search(r"data-role=(['\"])hero\1", block, re.I):
        return html
    caption_html = _html_escape(caption)
    credit_html = _html_escape(credit)
    figure = (
        "<div class='photo-set hero-support'><figure data-role='hero'>"
        f'<img src="media/{_html_escape(media_name)}" alt="{caption_html}">'
        f"<figcaption>{caption_html} Photo: {credit_html}</figcaption>"
        "</figure></div>"
    )
    copy = re.search(r"<div class=(['\"])copy\1>", block, re.I)
    if copy:
        updated = block[: copy.start()] + figure + block[copy.start() :]
    else:
        updated = block[: -len("</article>")] + figure + "</article>"
    return html[: match.start()] + updated + html[match.end() :]


def _story_snapshot(article: dict) -> tuple:
    texts = []
    for block in article.get("blocks") or []:
        if block.get("type") in {"paragraph", "heading", "results"}:
            texts.append(json.dumps(block, sort_keys=True, ensure_ascii=False))
    return (
        article.get("headline"),
        article.get("editorial_headline"),
        json.dumps(article.get("week_fact"), sort_keys=True, ensure_ascii=False),
        tuple(texts),
    )


def apply_row(issue: dict, row: dict, photos_dir: Path, issue_dir: Path, opener=None) -> str | None:
    event_id = row["event_id"]
    articles = issue.get("articles") or []
    targets = [article for article in articles if article.get("event_id") == event_id or article.get("id") == event_id]
    targets = [article for article in targets if article.get("type") != "feature" and _needs_photo(article)]
    if not targets:
        return None
    loaded = load_photo(row, photos_dir, opener=opener)
    if loaded is None:
        return None
    data, ext = loaded
    media_name = hero_filename(event_id, row["edition"], ext)
    media_dir = issue_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / media_name).write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    block = _image_block(media_name, row, event_id, digest)
    hero = _hero_object(media_name, row, event_id)
    for article in targets:
        before = _story_snapshot(article)
        article["hero_image"] = hero
        article["needs_external"] = False
        article["media_layout"] = article.get("media_layout") or "hero-support"
        blocks = list(article.get("blocks") or [])
        if not any(item.get("type") == "image" and item.get("role") == "hero" for item in blocks):
            blocks.insert(0, block)
        article["blocks"] = blocks
        if _story_snapshot(article) != before:
            raise RuntimeError(f"story changed for {event_id}")
    pending = issue.get("needs_external")
    if isinstance(pending, list):
        issue["needs_external"] = [item for item in pending if item != event_id]
    html_path = issue_dir / "index.html"
    if html_path.is_file():
        html_path.write_text(
            insert_hero_html(
                html_path.read_text(encoding="utf-8"),
                event_id,
                media_name,
                row.get("caption") or "",
                row.get("credit") or "",
            ),
            encoding="utf-8",
        )
    return media_name


def _feed_row(feed: list, edition: str) -> dict | None:
    needle = f"/issues/{edition}/"
    for item in feed:
        url = str(item.get("url") or "")
        if item.get("published_at") == edition or needle in url:
            return item
    return None


def apply_manifest(roundup_root: Path, manifest: Path, opener=None) -> list[str]:
    photos_dir = manifest.parent
    rows = parse_manifest(manifest.read_text(encoding="utf-8"))
    by_edition: dict[str, list[dict]] = {}
    for row in rows:
        by_edition.setdefault(row["edition"], []).append(row)
    applied = []
    feed_path = roundup_root / "feed.json"
    feed = json.loads(feed_path.read_text(encoding="utf-8")) if feed_path.is_file() else []
    issues_root = roundup_root / "issues"
    for edition, edition_rows in by_edition.items():
        issue_dir = issues_root / edition
        issue_path = issue_dir / "issue.json"
        if not issue_path.is_file():
            continue
        issue = json.loads(issue_path.read_text(encoding="utf-8"))
        first_media = None
        first_caption = ""
        for row in edition_rows:
            media_name = apply_row(issue, row, photos_dir, issue_dir, opener=opener)
            if media_name and first_media is None:
                first_media = media_name
                first_caption = row.get("caption") or ""
                applied.append(f"{edition}/{row['event_id']}")
        issue_path.write_text(json.dumps(issue, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        feed_item = _feed_row(feed, edition)
        if feed_item is not None and first_media and not feed_item.get("image"):
            feed_item["image"] = urllib.parse.urljoin(SITE, f"issues/{edition}/media/{first_media}")
            feed_item["image_caption"] = first_caption
            feed_item["image_focus"] = ""
    if feed_path.is_file():
        feed_path.write_text(json.dumps(feed, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return applied


def sync_photos(dest: Path, rsync_spec: str) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if not shutil.which("rsync"):
        raise RuntimeError("rsync is not installed")
    subprocess.run(["rsync", "-a", rsync_spec, str(dest) + "/"], check=True, timeout=180)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull Grok Bot roundup photos into existing issues")
    parser.add_argument("--roundup-root", default="/opt/rea/work/sailing-roundup")
    parser.add_argument("--manifest", default="")
    args = parser.parse_args(argv)
    root = Path(args.roundup_root)
    manifest = Path(args.manifest) if args.manifest else root / "external-photos" / "MANIFEST.md"
    spec = os.environ.get("ROUNDUP_PHOTOS_RSYNC", "").strip()
    if spec:
        sync_photos(manifest.parent, spec)
    if not manifest.is_file():
        print(f"no manifest at {manifest}")
        return 0
    applied = apply_manifest(root, manifest)
    print(f"applied {len(applied)}")
    for item in applied:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
