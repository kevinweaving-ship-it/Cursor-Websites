#!/usr/bin/env python3
"""Guard: MM LIVE has its own card; old reels stay in the reel rail."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mm_fb_fetch_cape import (  # noqa: E402
    broadcast_state,
    dedupe_reels,
    listing_meta,
    parse_video_ids,
    prefer_new,
    same_reel,
    video_is_live,
)

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


def test_paused_broadcast_is_still_live():
    html = (
        '"is_live_streaming":false,"is_premiere":false,"is_huddle":false,'
        '"is_video_broadcast":true,"id":"999000111222333",'
        '"broadcast_status":"LIVE","live_status":"PAUSED",'
        "The live video is paused"
    )
    assert broadcast_state(html, "999000111222333") == "paused"
    assert video_is_live(html, "999000111222333") is True


def test_live_stopped_stays_on_live_card():
    html = (
        '"id":"999000111222333","broadcast_status":"LIVE_STOPPED",'
        '"live_status":"LIVE"'
    )
    assert broadcast_state(html, "999000111222333") == "live"
    assert video_is_live(html, "999000111222333") is True


def test_vod_ready_is_finished_reel_not_live():
    html = (
        '"is_live_streaming":false,"is_premiere":false,"is_huddle":false,'
        '"is_video_broadcast":true,"id":"2830349890679040",'
        '"broadcast_status":"VOD_READY","live_status":"WAS_LIVE"'
    )
    assert broadcast_state(html, "2830349890679040") == "vod"
    assert video_is_live(html, "2830349890679040") is False


def test_js_bundle_paused_stream_is_not_live():
    html = 'oz_www_paused_stream_segments_count":2,"is_live_for_comet_live_ring":false'
    assert broadcast_state(html) == "unknown"
    assert video_is_live(html) is False


def test_listing_meta_uses_facebook_reel_thumb():
    html = (
        '"id":"2830349890679040","playable_duration_in_ms":927894,'
        '"image":{"uri":"https:\\/\\/scontent.example\\/t15.5256-10\\/thumb.jpg"}'
    )
    meta = listing_meta(html)
    assert meta["2830349890679040"]["duration_ms"] == 927894
    assert meta["2830349890679040"]["fb_thumb"] == "https://scontent.example/t15.5256-10/thumb.jpg"


def test_dedupe_same_title_keeps_one():
    videos = [
        {"id": "2830349890679040", "title": "ZVYC Day 2 ILCA and open start", "is_live": False},
        {"id": "1087203537604361", "title": "ZVYC Day 2 ILCA and open start", "is_live": False},
    ]
    out = dedupe_reels(videos)
    assert [v["id"] for v in out] == ["2830349890679040"]


def test_dedupe_keeps_different_clips_titled_live():
    videos = [
        {"id": "1599076671855710", "title": "LIVE", "is_live": False, "duration_ms": 1104000},
        {"id": "1723275305570869", "title": "LIVE", "is_live": False, "duration_ms": 160000},
    ]
    assert same_reel(videos[0], videos[1]) is False
    out = dedupe_reels(videos)
    assert [v["id"] for v in out] == ["1599076671855710", "1723275305570869"]


if __name__ == "__main__":
    test_own_live_card()
    test_bare_video_id_before_old_page_urls()
    test_prefer_new_skips_stored_reels()
    test_paused_broadcast_is_still_live()
    test_live_stopped_stays_on_live_card()
    test_vod_ready_is_finished_reel_not_live()
    test_js_bundle_paused_stream_is_not_live()
    test_listing_meta_uses_facebook_reel_thumb()
    test_dedupe_same_title_keeps_one()
    test_dedupe_keeps_different_clips_titled_live()
    print("ok")
