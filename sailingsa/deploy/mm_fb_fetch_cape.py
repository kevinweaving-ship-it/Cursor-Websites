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
VIDEO_ID_RE = re.compile(r'"video_id"\s*:\s*"(\d{8,})"')
LIVE_PROBE_URLS = (
    "https://www.facebook.com/marin.megastoresa/live",
    "https://www.facebook.com/marin.megastoresa",
    "https://m.facebook.com/marin.megastoresa",
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
    if "is live" in low and "was live" not in low:
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
                "permalink": f"https://www.facebook.com/reel/{vid}/",
                "title": "Marine Megastore LIVE",
            }
        )
    return found


def probe_live() -> list:
    """Cheap LIVE check. Do not download media. Live clips are kept even without Cape Classic in the title."""
    htmls = []
    for url in LIVE_PROBE_URLS:
        try:
            htmls.append(http_get(url))
        except Exception:
            pass
    if not htmls:
        return None
    blob = "\n".join(htmls)
    if not video_is_live(blob):
        try:
            htmls.append(dump("https://www.facebook.com/marin.megastoresa/live", budget_ms=3500))
        except Exception:
            pass
        blob = "\n".join(htmls)
    if not htmls:
        return None
    if not video_is_live(blob):
        return []
    found = []
    seen = set()
    for html in htmls:
        for item in parse_video_ids(html):
            vid = str(item.get("id") or "")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            item["is_live"] = True
            item["title"] = item.get("title") or "Marine Megastore LIVE"
            found.append(item)
    return found[:4]


def keep_clip(item: dict, is_live: bool) -> bool:
    if is_live:
        return True
    blob = " ".join([item.get("slug") or "", item.get("title") or "", item.get("url") or ""])
    return bool(KEEP_RE.search(blob))


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
    url = permalink or f"https://www.facebook.com/marin.megastoresa/videos/{vid}/"
    title = str((node or {}).get("title") or (node or {}).get("description") or "").strip()
    if live:
        title = title or "Marine Megastore LIVE"
    return {
        "id": vid,
        "slug": "",
        "url": url,
        "permalink": permalink or url,
        "title": title or "Marine Megastore reel",
        "is_live": live,
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
            if live or keep_clip(item, False):
                seen.add(vid)
                out.append(item)
    except Exception as e:
        print(f"[mm_fb] graph videos failed: {e}", flush=True)
    return out


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
        if row_item.get("is_live") and live_ids and vid not in live_ids:
            row_item["is_live"] = False
            row_item["fb_sub"] = "Marine Megastore was live"
        if not live_ids and row_item.get("is_live"):
            row_item["is_live"] = False
            row_item["fb_sub"] = "Marine Megastore was live"
        cleaned.append(row_item)
    live = [v for v in cleaned if v.get("is_live")]
    rest = [v for v in cleaned if not v.get("is_live")]
    rest.sort(key=lambda v: str(v.get("started_at") or ""), reverse=True)
    row["videos"] = live + rest
    data[RID] = row
    save_feed(data)
    return row
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
    if live:
        # Never block a live on yt-dlp; the card plays the FB embed instantly.
        return item
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
    token = page_token()
    if token:
        graphed = graph_fetch(token)
        if graphed:
            return graphed
    live_now = probe_live() or []
    if live_now:
        commit_videos(live_now)
    html = dump("https://www.facebook.com/marin.megastoresa/videos")
    found = parse_videos(html)
    kept = list(live_now)
    seen_live = {str(item.get("id") or "") for item in kept}
    checked = 0
    for item in found:
        vid = str(item.get("id") or "")
        if vid in seen_live:
            continue
        is_live = False
        if live_now:
            if not keep_clip(item, False):
                continue
            item["is_live"] = False
            kept.append(item)
            continue
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
    row = commit_videos(fetched)
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
