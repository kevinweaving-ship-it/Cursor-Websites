#!/usr/bin/env python3
"""Seed Cape Classic MM card with the missed ZVYC Classic Test reel."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

FEED = Path("/var/www/sailingsa/api/data/event_fb_feeds.json")
RID = "2026-09-13-zvyc-cape-classic"
VID = "1723275305570869"
URL = f"https://www.facebook.com/marin.megastoresa/videos/zvyc-classic-test/{VID}/"
PERMA = f"https://www.facebook.com/reel/{VID}/"
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
clip = {
    "id": VID,
    "url": URL,
    "permalink": PERMA,
    "embed_url": "https://www.facebook.com/plugins/video.php?href="
    + quote(PERMA, safe="")
    + "&show_text=false",
    "title": "ZVYC Classic Test",
    "fb_title": "ZVYC Classic Test",
    "fb_sub": "Marine Megastore was live",
    "fb_page": "marin.megastoresa",
    "fb_owner_logo": "/assets/adverts/mm-lipton/fb-page-marine-megastore.jpg",
    "thumb": f"/assets/adverts/mm-cape-classic/{VID}.jpg",
    "play_url": f"/assets/adverts/mm-cape-classic/{VID}.mp4",
    "is_live": False,
    "started_at": now,
}
data = json.loads(FEED.read_text(encoding="utf-8"))
row = dict(data.get(RID) or {})
row["enabled"] = True
row["feed_source"] = "marine-megastore"
row["fb_page"] = "marin.megastoresa"
existing = [v for v in (row.get("videos") or []) if str((v or {}).get("id")) != VID]
row["videos"] = [clip] + existing
data[RID] = row
tmp = FEED.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
tmp.replace(FEED)
try:
    os.chown(FEED, 33, 33)
except Exception:
    pass
print("seeded", VID, "n", len(row["videos"]))
