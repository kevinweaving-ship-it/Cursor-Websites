#!/usr/bin/env python3
"""Auto-fetch Marine Megastore Facebook reels/lives into the Cape Classic MM card.

Live first, then most recent. Skips old Lipton clips. Safe to run under flock.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

FEED = Path("/var/www/sailingsa/api/data/event_fb_feeds.json")
ASSET = Path("/var/www/sailingsa/assets/adverts/mm-cape-classic")
YTDLP = Path("/usr/local/bin/yt-dlp")
RID = "2026-09-13-zvyc-cape-classic"
PAGE = "marin.megastoresa"
CHROME = "/usr/bin/google-chrome"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
LOGO = "/assets/adverts/mm-lipton/fb-page-marine-megastore.jpg"
LIPTON_IDS = {
    "2622643364847262",
    "2410502969472697",
    "1014880974840710",
    "26023759437321260",
    "1587763379559775",
    "4518629078350390",
    "1751846282795149",
    "2111285223132517",
}
KEEP_RE = re.compile(
    r"zvyc|zeekoe|cape.?classic|classic.?test|capeclassic",
    re.I,
)
VID_RE = re.compile(
    r"https://www\.facebook\.com/marin\.megastoresa/videos/(?:([^/\"']+)/)?(\d{8,})",
    re.I,
)
REEL_RE = re.compile(r"https://www\.facebook\.com/reel/(\d{8,})", re.I)


def dump(url: str, budget_ms: int = 9000) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--virtual-time-budget={budget_ms}",
        "--timeout=16000",
        f"--user-agent={UA}",
        "--dump-dom",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
    return proc.stdout or ""


def title_from_slug(slug: str) -> str:
    s = re.sub(r"[-_]+", " ", str(slug or "")).strip()
    if not s or s.isdigit() or s.lower() in ("watch", "reel", "reels", "videos"):
        return ""
    titled = s.title()
    return re.sub(r"\bZvyc\b", "ZVYC", titled)


def embed_src(url: str) -> str:
    href = (url or "").strip()
    if not href:
        return ""
    return "https://www.facebook.com/plugins/video.php?href=" + quote(href, safe="") + "&show_text=false"


def parse_videos(html: str) -> list[dict]:
    found = []
    seen = set()
    for slug, vid in VID_RE.findall(html or ""):
        if vid in seen or vid in LIPTON_IDS:
            continue
        seen.add(vid)
        slug = slug or ""
        url = f"https://www.facebook.com/marin.megastoresa/videos/{slug + '/' if slug else ''}{vid}/"
        found.append(
            {
                "id": vid,
                "slug": slug,
                "url": url,
                "permalink": f"https://www.facebook.com/reel/{vid}/",
                "title": title_from_slug(slug) or "Marine Megastore reel",
            }
        )
    for vid in REEL_RE.findall(html or ""):
        if vid in seen or vid in LIPTON_IDS:
            continue
        seen.add(vid)
        found.append(
            {
                "id": vid,
                "slug": "",
                "url": f"https://www.facebook.com/reel/{vid}/",
                "permalink": f"https://www.facebook.com/reel/{vid}/",
                "title": "Marine Megastore reel",
            }
        )
    return found


def video_is_live(html: str) -> bool:
    low = (html or "").lower()
    if "was live" in low or "was_live" in low:
        return False
    if re.search(r"is_live(?:_streaming)?\"?\s*:\s*true", html or "", re.I):
        return True
    if "is live now" in low or '"live_status":"live"' in low:
        return True
    return False


def keep_clip(item: dict, is_live: bool) -> bool:
    if is_live:
        return True
    blob = " ".join([item.get("slug") or "", item.get("title") or "", item.get("url") or ""])
    return bool(KEEP_RE.search(blob))


def load_feed() -> dict:
    if FEED.is_file():
        try:
            data = json.loads(FEED.read_text(encoding="utf-8") or "{}")
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_feed(data: dict) -> None:
    FEED.parent.mkdir(parents=True, exist_ok=True)
    tmp = FEED.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(FEED)
    try:
        os.chown(FEED, 33, 33)  # www-data
    except Exception:
        pass


def hose_media(item: dict) -> dict:
    """Save local jpg + mp4 like Lipton thumbs so the card can play on tap."""
    vid = str((item or {}).get("id") or "")
    if not vid.isdigit():
        return item
    ASSET.mkdir(parents=True, exist_ok=True)
    mp4 = ASSET / f"{vid}.mp4"
    jpg = ASSET / f"{vid}.jpg"
    url = str(item.get("url") or item.get("permalink") or "").strip()
    live = bool(item.get("is_live"))
    if url and not live and YTDLP.is_file() and (not mp4.is_file() or mp4.stat().st_size < 50_000):
        subprocess.run(
            [str(YTDLP), "--no-warnings", "-f", "b", "-o", str(mp4), url],
            capture_output=True,
            text=True,
            timeout=180,
        )
    if url and YTDLP.is_file() and (not jpg.is_file() or jpg.stat().st_size < 1000):
        proc = subprocess.run(
            [str(YTDLP), "--no-warnings", "-j", url],
            capture_output=True,
            text=True,
            timeout=60,
        )
        thumb = ""
        try:
            thumb = str((json.loads(proc.stdout or "{}") or {}).get("thumbnail") or "")
        except Exception:
            thumb = ""
        if thumb:
            subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    "-A",
                    "facebookexternalhit/1.1",
                    "-o",
                    str(jpg),
                    thumb,
                ],
                capture_output=True,
                timeout=30,
            )
        if (not jpg.is_file() or jpg.stat().st_size < 1000) and mp4.is_file() and mp4.stat().st_size > 50_000:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "1",
                    "-i",
                    str(mp4),
                    "-vframes",
                    "1",
                    "-q:v",
                    "3",
                    str(jpg),
                ],
                capture_output=True,
                timeout=30,
            )
    if jpg.is_file() and jpg.stat().st_size > 1000:
        item["thumb"] = f"/assets/adverts/mm-cape-classic/{vid}.jpg"
    if mp4.is_file() and mp4.stat().st_size > 50_000:
        item["play_url"] = f"/assets/adverts/mm-cape-classic/{vid}.mp4"
    for path in (mp4, jpg):
        try:
            if path.is_file():
                os.chown(path, 33, 33)
        except Exception:
            pass
    return item


def merge_videos(existing: list, fetched: list) -> list:
    by_id = {}
    for item in existing or []:
        vid = str((item or {}).get("id") or "")
        if vid:
            by_id[vid] = dict(item)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    order = []
    for item in fetched:
        vid = item["id"]
        prev = by_id.get(vid, {})
        live = bool(item.get("is_live"))
        row = dict(prev)
        row.update(
            {
                "id": vid,
                "url": item.get("url") or prev.get("url") or "",
                "permalink": item.get("permalink") or prev.get("permalink") or "",
                "title": item.get("title") or prev.get("title") or "Marine Megastore reel",
                "fb_title": item.get("title") or prev.get("fb_title") or item.get("title"),
                "fb_page": PAGE,
                "fb_owner_logo": LOGO,
                "embed_url": embed_src(item.get("permalink") or item.get("url") or ""),
                "is_live": live,
                "fb_sub": "LIVE" if live else "Marine Megastore was live",
            }
        )
        if not row.get("started_at"):
            row["started_at"] = now
        by_id[vid] = hose_media(row)
        order.append(vid)
    # keep previous Cape clips not in this scrape (so a missed live stays listed)
    extra = [
        hose_media(dict(v)) if isinstance(v, dict) else v
        for v in (existing or [])
        if str((v or {}).get("id") or "") not in set(order)
    ]
    out = [by_id[i] for i in order] + extra
    live = [v for v in out if v.get("is_live")]
    rest = [v for v in out if not v.get("is_live")]
    rest.sort(key=lambda v: str(v.get("started_at") or ""), reverse=True)
    return live + rest


def fetch() -> list:
    html = dump("https://www.facebook.com/marin.megastoresa/videos")
    found = parse_videos(html)
    kept = []
    checked = 0
    for item in found:
        is_live = False
        want = KEEP_RE.search(item.get("slug") or "") or KEEP_RE.search(item.get("title") or "")
        if want and checked < 3:
            checked += 1
            try:
                vhtml = dump(item["permalink"], budget_ms=7000)
                is_live = video_is_live(vhtml)
            except Exception:
                is_live = False
        elif not want and checked == 0:
            # Top of the list: might be a live that is not named yet.
            checked += 1
            try:
                vhtml = dump(item["permalink"], budget_ms=7000)
                is_live = video_is_live(vhtml)
            except Exception:
                is_live = False
        if not keep_clip(item, is_live):
            continue
        item["is_live"] = is_live
        kept.append(item)
    return kept


def main() -> int:
    fetched = fetch()
    data = load_feed()
    row = dict(data.get(RID) or {})
    row["enabled"] = True
    row["feed_source"] = "marine-megastore"
    row["fb_page"] = PAGE
    existing = row.get("videos") if isinstance(row.get("videos"), list) else []
    row["videos"] = merge_videos(existing, fetched)
    data[RID] = row
    save_feed(data)
    print(
        json.dumps(
            {
                "ok": True,
                "n": len(row["videos"]),
                "ids": [v.get("id") for v in row["videos"]],
                "live": [v.get("id") for v in row["videos"] if v.get("is_live")],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
