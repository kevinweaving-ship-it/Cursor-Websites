#!/usr/bin/env python3
"""Auto-fetch Marine Megastore Facebook reels/lives into the Cape Classic MM card.

Live = Facebook broadcast only (never a saved /assets/adverts/ mp4).
When a live ends it becomes today's newest reel. Event-day reels stay in
started_at order (newest first). Skips old Lipton clips. Safe under flock.
"""
from __future__ import annotations

import html as html_lib
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
# Cape Classic racing days — keep MM clips posted on these dates.
EVENT_DATES = {"2026-09-12", "2026-09-13"}
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
VIDEO_ID_RE = re.compile(r'"video_id"\s*:\s*"(\d{8,})"')
CREATION_RE = re.compile(r"(?:creation_time|publish_time)[\"\s:]+(\d{10})")
OG_TITLE_RE = re.compile(r'og:title" content="([^"]+)"', re.I)
TEXT_RE = re.compile(r'"text":"([^"]{5,180})"')
LIVE_PROBE_URLS = (
    "https://www.facebook.com/marin.megastoresa/live",
    "https://www.facebook.com/marin.megastoresa",
    "https://m.facebook.com/marin.megastoresa",
)
SCRAPE_PAGES = (
    "https://www.facebook.com/marin.megastoresa/videos",
    "https://www.facebook.com/marin.megastoresa/live",
)


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


def video_watch_url(vid: str) -> str:
    return f"https://www.facebook.com/{PAGE}/videos/{vid}/"


def embed_src(url: str, autoplay: bool = False) -> str:
    href = (url or "").strip()
    if not href:
        return ""
    src = "https://www.facebook.com/plugins/video.php?href=" + quote(href, safe="") + "&show_text=false"
    if autoplay:
        src += "&autoplay=1"
    return src


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
                "permalink": url,
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
    """True only for a broadcast happening now. Ended lives and reels are False.

    Do not match Facebook's JS bundle (`is_live` appears in crawler HTML even
    when the Page is not live). That false positive skipped Chrome and never
    found a video id.
    """
    raw = html or ""
    if re.search(r"is live now", raw, re.I):
        return True
    if re.search(r'"broadcast_status"\s*:\s*"LIVE"', raw):
        return True
    if re.search(r'"live_status"\s*:\s*"LIVE"', raw):
        return True
    if re.search(r'"is_live_streaming"\s*:\s*true', raw):
        return True
    return False


def http_get(url: str, timeout: int = 10) -> str:
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_video_ids(html: str) -> list[dict]:
    found = parse_videos(html)
    seen = {str(item.get("id") or "") for item in found}
    for vid in VIDEO_ID_RE.findall(html or ""):
        if vid in seen or vid in LIPTON_IDS:
            continue
        seen.add(vid)
        found.append(
            {
                "id": vid,
                "slug": "",
                "url": f"https://www.facebook.com/marin.megastoresa/videos/{vid}/",
                "permalink": f"https://www.facebook.com/marin.megastoresa/videos/{vid}/",
                "title": "Marine Megastore LIVE",
            }
        )
    return found


def probe_live() -> list | None:
    """Public Page scrape only — no Page token.

    Facebook Login / Business picker cannot see Marine Megastore. GitHub +
    Reddit agree Graph live_videos webhooks need the Page to install the app.
    Access we actually have: public marin.megastoresa. Chrome-dump /live,
    take the current /videos/{id}/, embed with autoplay.
    """
    html = ""
    try:
        html = dump("https://www.facebook.com/marin.megastoresa/live", budget_ms=5000)
    except Exception:
        html = ""
    if not html:
        return None
    found = parse_video_ids(html)
    if not found:
        return []
    for item in found[:4]:
        current = inspect_video(dict(item))
        if not current.get("is_live"):
            continue
        vid = str(current.get("id") or "")
        current["is_live"] = True
        current["play_url"] = ""
        current["url"] = video_watch_url(vid)
        current["permalink"] = current["url"]
        current["title"] = current.get("title") or "Marine Megastore LIVE"
        current["fb_sub"] = "LIVE"
        return [current]
    return []


def keep_clip(item: dict, is_live: bool | None = None) -> bool:
    if is_live is None:
        is_live = bool(item.get("is_live"))
    if is_live:
        return True
    blob = " ".join(
        [
            str(item.get("slug") or ""),
            str(item.get("title") or ""),
            str(item.get("fb_title") or ""),
            str(item.get("url") or ""),
        ]
    )
    if KEEP_RE.search(blob):
        return True
    day = str(item.get("started_at") or "")[:10]
    return day in EVENT_DATES


def page_token() -> str:
    for key in (
        "MM_FB_PAGE_TOKEN",
        "FACEBOOK_PAGE_TOKEN",
        "MARINE_MEGASTORE_PAGE_TOKEN",
    ):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    token_path = Path("/var/www/sailingsa/api/data/mm_fb_page.token")
    if token_path.is_file():
        return token_path.read_text(encoding="utf-8").strip()
    return ""


def graph_get(path: str, token: str, fields: str, extra: str = "") -> dict:
    import json as _json
    import urllib.parse
    import urllib.request

    q = {"access_token": token, "fields": fields, "limit": "12"}
    url = f"https://graph.facebook.com/v21.0/{path}?" + urllib.parse.urlencode(q)
    if extra:
        url += "&" + extra
    req = urllib.request.Request(url, headers={"User-Agent": "SailingSA-MM/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return _json.loads(r.read().decode("utf-8", "replace") or "{}")


def graph_item(node: dict, live: bool) -> dict:
    vid = str((node or {}).get("id") or "")
    permalink = str((node or {}).get("permalink_url") or "").strip()
    if permalink and permalink.startswith("/"):
        permalink = "https://www.facebook.com" + permalink
    title = str((node or {}).get("title") or (node or {}).get("description") or "").strip()
    if live:
        url = video_watch_url(vid)
        permalink = url
        title = title or "Marine Megastore LIVE"
    else:
        url = permalink or video_watch_url(vid)
    return {
        "id": vid,
        "slug": "",
        "url": url,
        "permalink": permalink or url,
        "title": title or "Marine Megastore reel",
        "is_live": live,
        "play_url": "" if live else None,
        "started_at": str((node or {}).get("created_time") or ""),
    }


def graph_fetch(token: str) -> list:
    """Page-token Graph is better than public scrape: Live status + reels without Page Public Content Access."""
    if not token:
        return []
    out = []
    seen = set()
    try:
        live_js = graph_get(
            f"{PAGE}/live_videos",
            token,
            "id,title,status,permalink_url,from",
            extra="broadcast_status=LIVE",
        )
        for node in live_js.get("data") or []:
            vid = str((node or {}).get("id") or "")
            if not vid or vid in LIPTON_IDS or vid in seen:
                continue
            seen.add(vid)
            out.append(graph_item(node, True))
    except Exception as e:
        print(f"[mm_fb] graph live_videos failed: {e}", flush=True)
    try:
        vids = graph_get(
            f"{PAGE}/videos",
            token,
            "id,title,description,live_status,permalink_url,created_time",
        )
        for node in vids.get("data") or []:
            vid = str((node or {}).get("id") or "")
            if not vid or vid in LIPTON_IDS or vid in seen:
                continue
            status = str((node or {}).get("live_status") or "").upper()
            live = status == "LIVE"
            item = graph_item(node, live)
            if live:
                item["play_url"] = ""
            if live or keep_clip(item, False):
                seen.add(vid)
                out.append(item)
    except Exception as e:
        print(f"[mm_fb] graph videos failed: {e}", flush=True)
    return out


def title_from_html(html: str, fallback: str) -> str:
    for m in TEXT_RE.finditer(html or ""):
        text = html_lib.unescape(m.group(1)).strip()
        if KEEP_RE.search(text) and "comment" not in text.lower():
            return text[:160]
    m = OG_TITLE_RE.search(html or "")
    if not m:
        return fallback
    title = html_lib.unescape(m.group(1)).strip()
    title = re.sub(r"^\d[\d.,KkMm\s]*\s*(views|reactions|shares)?\s*\|\s*", "", title, flags=re.I)
    title = re.split(r"\s*\|\s*Marine Megastore\s*$", title, maxsplit=1, flags=re.I)[0].strip()
    title = title.split("\n")[0].strip()
    if not title or title.lower() in ("marine megastore on reels", "marine megastore"):
        return fallback
    return title[:160]


def inspect_video(item: dict) -> dict:
    url = str(item.get("url") or item.get("permalink") or "").strip()
    if not url:
        return item
    try:
        page = dump(url, budget_ms=7000)
    except Exception:
        return item
    item["is_live"] = video_is_live(page)
    if item["is_live"]:
        item["play_url"] = ""
        item["title"] = title_from_html(page, item.get("title") or "Marine Megastore LIVE")
    else:
        item["title"] = title_from_html(page, item.get("title") or "Marine Megastore reel")
    ts = CREATION_RE.findall(page or "")
    if ts:
        dt = datetime.fromtimestamp(int(ts[0]), tz=timezone.utc)
        item["started_at"] = dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return item


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


def advert_play_url(url: str) -> bool:
    return str(url or "").startswith("/assets/adverts/")


def commit_videos(fetched: list) -> dict:
    data = load_feed()
    row = dict(data.get(RID) or {})
    row["enabled"] = True
    row["feed_source"] = "marine-megastore"
    row["fb_page"] = PAGE
    existing = row.get("videos") if isinstance(row.get("videos"), list) else []
    live_ids = {str(v.get("id") or "") for v in fetched if v.get("is_live")}
    if fetched:
        merged = merge_videos(existing, fetched)
    else:
        merged = [dict(v) for v in existing if isinstance(v, dict)]
    cleaned = []
    for item in merged:
        row_item = dict(item)
        vid = str(row_item.get("id") or "")
        if advert_play_url(row_item.get("play_url")):
            row_item["is_live"] = False
        if row_item.get("is_live") and live_ids and vid not in live_ids:
            row_item["is_live"] = False
            row_item["fb_sub"] = "Marine Megastore was live"
        if not live_ids and row_item.get("is_live"):
            row_item["is_live"] = False
            row_item["fb_sub"] = "Marine Megastore was live"
        if row_item.get("is_live"):
            row_item["play_url"] = ""
            row_item["fb_sub"] = "LIVE"
        elif not row_item.get("fb_sub"):
            row_item["fb_sub"] = "Marine Megastore was live"
        cleaned.append(row_item)
    live = [v for v in cleaned if v.get("is_live")]
    rest = [v for v in cleaned if not v.get("is_live")]
    rest.sort(key=lambda v: str(v.get("started_at") or ""), reverse=True)
    row["videos"] = live + rest
    data[RID] = row
    save_feed(data)
    return row


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
    if live:
        # Never attach a saved file as Live. The card plays the FB embed.
        item["play_url"] = ""
        return item
    if url and YTDLP.is_file() and (not mp4.is_file() or mp4.stat().st_size < 50_000):
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
        vid = str(item.get("id") or "")
        if not vid:
            continue
        prev = by_id.get(vid, {})
        live = bool(item.get("is_live"))
        watch = video_watch_url(vid)
        href = watch if live else (item.get("url") or prev.get("url") or watch)
        if "/reel/" in str(href):
            href = watch
        row = dict(prev)
        row.update(
            {
                "id": vid,
                "url": href,
                "permalink": href,
                "title": item.get("title") or prev.get("title") or "Marine Megastore reel",
                "fb_title": item.get("title") or prev.get("fb_title") or item.get("title"),
                "fb_page": PAGE,
                "fb_owner_logo": LOGO,
                "embed_url": embed_src(href, autoplay=live),
                "is_live": live,
                "fb_sub": "LIVE" if live else "Marine Megastore was live",
            }
        )
        if item.get("started_at"):
            row["started_at"] = item["started_at"]
        elif not row.get("started_at"):
            row["started_at"] = now
        if live:
            row["play_url"] = ""
            by_id[vid] = row
        else:
            by_id[vid] = hose_media(row)
        order.append(vid)
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


def scrape_found() -> list:
    found = []
    seen = set()
    for url in SCRAPE_PAGES:
        try:
            page = dump(url)
        except Exception:
            continue
        for item in parse_video_ids(page):
            vid = str(item.get("id") or "")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            found.append(item)
    return found


def fetch() -> list:
    token = page_token()
    if token:
        graphed = graph_fetch(token)
        if graphed:
            return graphed
    live_now = probe_live() or []
    if live_now:
        return list(live_now)
    found = scrape_found()
    kept = []
    seen = set()
    existing_ids = set()
    row = load_feed().get(RID) or {}
    for prev in row.get("videos") or []:
        if isinstance(prev, dict) and prev.get("id"):
            existing_ids.add(str(prev.get("id")))
    inspected = 0
    for item in found:
        vid = str(item.get("id") or "")
        if not vid or vid in seen or vid in existing_ids:
            continue
        if inspected >= 2:
            break
        inspected += 1
        item = inspect_video(item)
        if not keep_clip(item, bool(item.get("is_live"))):
            continue
        if item.get("is_live"):
            item["play_url"] = ""
            item["url"] = video_watch_url(vid)
            item["permalink"] = item["url"]
        kept.append(item)
        seen.add(vid)
    return kept


def main() -> int:
    fetched = fetch()
    row = commit_videos(fetched)
    print(
        json.dumps(
            {
                "ok": True,
                "n": len(row["videos"]),
                "ids": [v.get("id") for v in row["videos"]],
                "live": [v.get("id") for v in row["videos"] if v.get("is_live")],
                "titles": [v.get("title") for v in row["videos"]],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
