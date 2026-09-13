#!/usr/bin/env python3
"""Guard: MM LIVE has its own card; old reels stay in the reel rail."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mm_fb_fetch_cape import parse_video_ids, prefer_new  # noqa: E402

JS = Path(__file__).resolve().parents[1] / "frontend" / "js" / "mm-lipton-reels-card.js"


def test_own_live_card():
    js = JS.read_text(encoding="utf-8")
    assert "data-mm-live-slot" in js
    assert "function liveCardHtml" in js
    assert "function reelVideos" in js
    chunk = js[js.index("function liveCardHtml") : js.index("function liveCardHtml") + 900]
    assert "advertPoster" not in chunk
    assert "liveEmbedIframeHtml" in chunk
    assert "liveBadgeHtml" not in chunk
    assert "mm-lipton-reels-live-badge" not in js
    assert "autoplay=1" in js
    assert "playsinline=1" in js
    assert "mute=1" in js


def test_bare_video_id_before_old_page_urls():
    html = (
        "/videos/1459464616072090/ "
        "https://www.facebook.com/marin.megastoresa/videos/1691951328561859/"
    )
    ids = [row["id"] for row in parse_video_ids(html)]
    assert ids[0] == "1459464616072090"
    assert "1691951328561859" in ids


def test_prefer_new_skips_stored_reels():
    found = parse_video_ids(
        "/videos/1459464616072090/ "
        "https://www.facebook.com/marin.megastoresa/videos/1691951328561859/"
    )
    ordered = prefer_new(found, {"1691951328561859"})
    assert ordered[0]["id"] == "1459464616072090"


if __name__ == "__main__":
    test_own_live_card()
    test_bare_video_id_before_old_page_urls()
    test_prefer_new_skips_stored_reels()
    print("ok")
