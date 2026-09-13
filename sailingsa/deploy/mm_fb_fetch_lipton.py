#!/usr/bin/env python3
"""Pull Marine Megastore Lipton reels via Graph, same path as Cape Classic.

Cape Classic fetch skips Lipton IDs. This writes the Lipton event feed
(`2026-08-29-lipton-challenge-cup`) from Graph /videos, keeps local thumbs,
and uses /videos/{id}/ (never /reel/). Current Cape Classic LIVE stays off
this card unless the title is Lipton.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/var/www/sailingsa/deploy")))
from mm_fb_fetch_cape import (  # noqa: E402
    FEED,
    PAGE,
    graph_get,
    graph_item,
    load_feed,
    page_token,
    save_feed,
    video_watch_url,
)

RID = "2026-08-29-lipton-challenge-cup"
KEEP_RE = re.compile(r"\blipton\b", re.I)
SKIP_RE = re.compile(r"zvyc|zeekoe|cape.?classic|classic.?test", re.I)
CAPE_IDS = {
    "1599076671855710",
    "28462423990049093",
    "1723275305570869",
}
LOGO = "/assets/adverts/mm-lipton/fb-page-marine-megastore.jpg"
THUMB = "/assets/adverts/mm-lipton/{vid}.jpg"


def _blob(item: dict) -> str:
    return " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("fb_title") or ""),
            str(item.get("url") or ""),
            str(item.get("permalink") or ""),
        ]
    )


def keep_lipton(item: dict, live: bool = False) -> bool:
    blob = _blob(item)
    if SKIP_RE.search(blob):
        return False
    if str(item.get("id") or "") in CAPE_IDS:
        return False
    if not KEEP_RE.search(blob):
        return False
    if live:
        return True
    return True


def graph_fetch_lipton(token: str) -> list:
    if not token:
        return []
    out = []
    seen = set()
    try:
        vids = graph_get(
            f"{PAGE}/videos",
            token,
            "id,title,description,live_status,permalink_url,created_time",
            limit="40",
        )
        for node in vids.get("data") or []:
            vid = str((node or {}).get("id") or "")
            if not vid or vid in CAPE_IDS or vid in seen:
                continue
            status = str((node or {}).get("live_status") or "").upper()
            live = status == "LIVE"
            item = graph_item(node, live)
            item["url"] = video_watch_url(vid)
            item["permalink"] = item["url"]
            if live and not keep_lipton(item, True):
                continue
            if not live and not keep_lipton(item, False):
                continue
            if live:
                item["play_url"] = ""
            seen.add(vid)
            out.append(item)
    except Exception as e:
        print(f"[mm_fb] lipton graph videos failed: {e}", flush=True)
    return out


def merge_lipton(existing: list, fetched: list) -> list:
    by_id = {}
    for item in existing or []:
        vid = str((item or {}).get("id") or "")
        if vid:
            by_id[vid] = dict(item)
    order = []
    for item in fetched:
        vid = str(item.get("id") or "")
        if not vid:
            continue
        prev = by_id.get(vid, {})
        live = bool(item.get("is_live"))
        href = video_watch_url(vid)
        row = dict(prev)
        row.update(
            {
                "id": vid,
                "url": href,
                "permalink": href,
                "title": item.get("title") or prev.get("title") or "Lipton Challenge Cup",
                "fb_title": item.get("title") or prev.get("fb_title") or item.get("title"),
                "fb_page": PAGE,
                "fb_owner_logo": LOGO,
                "thumb": prev.get("thumb") or THUMB.format(vid=vid),
                "is_live": live,
                "fb_sub": "LIVE" if live else (prev.get("fb_sub") or "Marine Megastore was live"),
            }
        )
        if item.get("started_at"):
            row["started_at"] = item["started_at"]
        if live:
            row["play_url"] = ""
        by_id[vid] = row
        order.append(vid)
    extra = [
        dict(v)
        for v in (existing or [])
        if isinstance(v, dict) and str(v.get("id") or "") not in set(order)
    ]
    out = [by_id[i] for i in order] + extra
    live = [v for v in out if v.get("is_live")]
    rest = [v for v in out if not v.get("is_live")]
    rest.sort(key=lambda v: str(v.get("started_at") or ""), reverse=True)
    return live + rest


def commit_lipton(fetched: list) -> dict:
    data = load_feed()
    row = dict(data.get(RID) or {})
    row["enabled"] = True
    row["feed_source"] = "marine-megastore"
    row["fb_page"] = PAGE
    existing = row.get("videos") if isinstance(row.get("videos"), list) else []
    if fetched:
        row["videos"] = merge_lipton(existing, fetched)
    elif existing:
        row["videos"] = existing
    else:
        row["videos"] = []
    data[RID] = row
    save_feed(data)
    return row


def main() -> int:
    token = page_token()
    fetched = graph_fetch_lipton(token) if token else []
    row = commit_lipton(fetched)
    print(
        json.dumps(
            {
                "ok": True,
                "source": "graph" if token else "none",
                "n": len(row.get("videos") or []),
                "ids": [v.get("id") for v in (row.get("videos") or [])],
                "titles": [v.get("title") for v in (row.get("videos") or [])],
                "live": [v.get("id") for v in (row.get("videos") or []) if v.get("is_live")],
            }
        )
    )
    return 0 if token else 1


if __name__ == "__main__":
    raise SystemExit(main())
