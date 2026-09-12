#!/usr/bin/env python3
"""Surgical live api.py patch: saved advert mp4s are never Live.

Marker: MM_LIVE_NOT_ADVERT_v1
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "MM_LIVE_NOT_ADVERT_v1"

OLD = '''    started = str(item.get("started_at") or "").strip()
    title = str(item.get("title") or "").strip()
    return {
        "id": vid,
        "url": url,
        "permalink": permalink,
        "embed_url": embed,
        "title": title,
        "fb_title": str(item.get("fb_title") or title).strip(),
        "fb_sub": str(item.get("fb_sub") or "").strip(),
        "fb_owner_logo": str(item.get("fb_owner_logo") or "").strip(),
        "fb_page": str(item.get("fb_page") or "").strip(),
        "play_url": str(item.get("play_url") or "").strip(),
        "started_at": started,
        "track_offset_ms": int(item.get("track_offset_ms") or 0),
        "is_live": bool(item.get("is_live")),
'''

NEW = '''    started = str(item.get("started_at") or "").strip()
    title = str(item.get("title") or "").strip()
    play_url = str(item.get("play_url") or "").strip()
    is_live = bool(item.get("is_live"))
    # ''' + MARKER + '''
    # Saved advert files are reels. Live is Facebook embed only.
    if play_url.startswith("/assets/adverts/"):
        is_live = False
    return {
        "id": vid,
        "url": url,
        "permalink": permalink,
        "embed_url": embed,
        "title": title,
        "fb_title": str(item.get("fb_title") or title).strip(),
        "fb_sub": str(item.get("fb_sub") or "").strip(),
        "fb_owner_logo": str(item.get("fb_owner_logo") or "").strip(),
        "fb_page": str(item.get("fb_page") or "").strip(),
        "play_url": play_url,
        "started_at": started,
        "track_offset_ms": int(item.get("track_offset_ms") or 0),
        "is_live": is_live,
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched")
    else:
        if OLD not in text:
            raise SystemExit("normalize block missing")
        text = text.replace(OLD, NEW, 1)
        if MARKER not in text:
            raise SystemExit("marker failed")
    if "mm-lipton-reels-card.js?v=mmr128" in text:
        text = text.replace(
            "mm-lipton-reels-card.js?v=mmr128",
            "mm-lipton-reels-card.js?v=mmr129",
            1,
        )
        print("BUMPED mmr129")
    elif "mm-lipton-reels-card.js?v=mmr129" in text:
        print("already mmr129")
    elif "mm-lipton-reels-card.js?v=mmr127" in text:
        text = text.replace(
            "mm-lipton-reels-card.js?v=mmr127",
            "mm-lipton-reels-card.js?v=mmr129",
            1,
        )
        print("BUMPED mmr129")
    else:
        raise SystemExit("mmr127/128 script tag missing")
    API.write_text(text, encoding="utf-8")
    print("PATCHED", API, "bytes", API.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
