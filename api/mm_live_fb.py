"""Marine Megastore Facebook Live helpers for Upcoming Events video cards."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")

MM_FB_PAGE_SLUG = (os.getenv("MM_FB_PAGE_SLUG") or "marin.megastoresa").strip() or "marin.megastoresa"
MM_FB_PAGE_NAME = "Marine Megastore"
MM_FB_PAGE_URL = f"https://www.facebook.com/{MM_FB_PAGE_SLUG}"
MM_FB_SITE_URL = "https://www.marinemegastore.co.za/"

_VIDEO_ID_RE = re.compile(
    r"(?:/videos/|/reel/|/reels/|/watch/?\?v=)(\d+)",
    re.I,
)
_ISO_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")


def parse_video_id(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    m = _VIDEO_ID_RE.search(raw)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d+", raw):
        return raw
    return ""


def facebook_permalink(video_id: str, page_slug: str = "") -> str:
    vid = str(video_id or "").strip()
    slug = (page_slug or MM_FB_PAGE_SLUG).strip() or MM_FB_PAGE_SLUG
    if not vid:
        return ""
    return f"https://www.facebook.com/{slug}/videos/{vid}/"


def facebook_embed_url(permalink: str, autoplay: bool = False) -> str:
    href = quote((permalink or "").strip(), safe="")
    if not href:
        return ""
    ap = "true" if autoplay else "false"
    return f"https://www.facebook.com/plugins/video.php?href={href}&show_text=false&autoplay={ap}"


def parse_ts(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    m = _ISO_PREFIX_RE.match(raw.replace(" ", "T"))
    if not m:
        return None
    try:
        dt = datetime.fromisoformat(m.group(1))
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def format_mm_timestamp(value: Any) -> str:
    """Event-card stamp, e.g. ``09 Sep · 14:20`` in SAST."""
    dt = parse_ts(value)
    if dt is None:
        return ""
    return dt.astimezone(SAST).strftime("%d %b · %H:%M")


def _as_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()[:10]
    if len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def video_in_event_window(
    started_at: Any,
    start_date: Any,
    end_date: Any,
    pad_days: int = 2,
) -> bool:
    dt = parse_ts(started_at)
    if dt is None:
        return False
    day = dt.astimezone(SAST).date()
    start = _as_date(start_date)
    end = _as_date(end_date) or start
    if start is None:
        return True
    if end is None:
        end = start
    pad = timedelta(days=max(0, int(pad_days)))
    return (start - pad) <= day <= (end + pad)


def title_matches_event(title: str, event_name: str) -> bool:
    title_l = (title or "").lower()
    name_l = (event_name or "").lower()
    if not title_l or not name_l:
        return False
    if name_l in title_l:
        return True
    tokens = [t for t in re.findall(r"[a-z0-9]+", name_l) if len(t) >= 4]
    skip = {"sailing", "regatta", "championship", "championships", "event", "open", "club"}
    tokens = [t for t in tokens if t not in skip]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in title_l)
    return hits >= 2 or (len(tokens) == 1 and hits == 1)


def normalize_mm_video(raw: Optional[dict], page_slug: str = "") -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    vid = str(raw.get("id") or parse_video_id(str(raw.get("url") or raw.get("permalink_url") or ""))).strip()
    if not vid:
        return None
    permalink = (raw.get("url") or raw.get("permalink_url") or "").strip()
    if not permalink:
        permalink = facebook_permalink(vid, page_slug)
    if permalink.startswith("/"):
        permalink = "https://www.facebook.com" + permalink
    live_status = str(raw.get("live_status") or raw.get("status") or "").strip().upper()
    is_live = bool(raw.get("is_live")) or live_status in ("LIVE", "LIVE_NOW")
    started = parse_ts(raw.get("started_at") or raw.get("creation_time") or raw.get("created_time"))
    first_seen = parse_ts(raw.get("first_seen_at")) or started
    title = (raw.get("title") or raw.get("description") or "").strip()
    thumb = (raw.get("thumb") or raw.get("picture") or "").strip()
    embed = (raw.get("embed_url") or "").strip() or facebook_embed_url(permalink, autoplay=is_live)
    out = {
        "id": vid,
        "url": permalink,
        "embed_url": embed,
        "title": title,
        "started_at": started.isoformat() if started else "",
        "first_seen_at": first_seen.isoformat() if first_seen else "",
        "is_live": is_live,
        "thumb": thumb,
        "stamp": format_mm_timestamp(started),
    }
    return out


def merge_mm_videos(
    existing: Any,
    incoming: Any,
    start_date: Any = None,
    end_date: Any = None,
    event_name: str = "",
) -> list:
    """Keep prior same-event clips; accept a new LIVE item even if it just started."""
    by_id = {}
    for item in existing or []:
        norm = normalize_mm_video(item)
        if norm:
            by_id[norm["id"]] = norm
    for item in incoming or []:
        norm = normalize_mm_video(item)
        if not norm:
            continue
        known = norm["id"] in by_id
        in_window = video_in_event_window(norm.get("started_at"), start_date, end_date)
        named = title_matches_event(norm.get("title") or "", event_name)
        if not known and not norm["is_live"] and not in_window and not named:
            continue
        prev = by_id.get(norm["id"])
        if prev:
            if prev.get("first_seen_at") and not norm.get("first_seen_at"):
                norm["first_seen_at"] = prev["first_seen_at"]
            elif prev.get("first_seen_at") and norm.get("first_seen_at"):
                try:
                    if parse_ts(prev["first_seen_at"]) <= parse_ts(norm["first_seen_at"]):
                        norm["first_seen_at"] = prev["first_seen_at"]
                except Exception:
                    norm["first_seen_at"] = prev["first_seen_at"]
            if prev.get("thumb") and not norm.get("thumb"):
                norm["thumb"] = prev["thumb"]
            if prev.get("title") and not norm.get("title"):
                norm["title"] = prev["title"]
            if prev.get("started_at") and not norm.get("started_at"):
                norm["started_at"] = prev["started_at"]
                norm["stamp"] = prev.get("stamp") or format_mm_timestamp(prev["started_at"])
        by_id[norm["id"]] = norm
    videos = list(by_id.values())

    def _sort_key(v):
        ts = parse_ts(v.get("started_at") or v.get("first_seen_at")) or datetime.min.replace(tzinfo=timezone.utc)
        return (0 if v.get("is_live") else 1, -ts.timestamp())

    videos.sort(key=_sort_key)
    return videos


def pick_mm_stage(videos: Any) -> tuple[Optional[dict], list]:
    """LIVE item is primary; every other same-event clip is a timestamped replay thumb."""
    items = [normalize_mm_video(v) for v in (videos or [])]
    items = [v for v in items if v]
    live = next((v for v in items if v.get("is_live")), None)
    if live:
        replays = [v for v in items if v["id"] != live["id"]]
        return live, replays
    return None, items


def graph_item_to_video(item: dict, is_live_hint: bool = False) -> Optional[dict]:
    if not isinstance(item, dict):
        return None
    raw = dict(item)
    if is_live_hint:
        raw["is_live"] = True
    return normalize_mm_video(raw)
