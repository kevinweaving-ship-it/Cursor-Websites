#!/usr/bin/env python3
"""HYC live cam is a pass-through of Cam 5 on the club NVR; SA can show/hide."""
import os
from pathlib import Path

from sailingsa.backend.club_cam_hyc import (
    CAM_NO,
    ISAPI_LIVE_CHANNEL,
    KIND,
    LABEL,
    LIVE_SRC,
    allowed_upstream,
    is_visible,
    live_url,
    rewrite_hls_playlist,
    set_visible,
    status_payload,
    stream_kind,
)


def test_cam5_live_pass_through():
    assert CAM_NO == 5
    assert ISAPI_LIVE_CHANNEL == 502
    assert KIND == "live"
    assert LABEL == "HYC club cam"
    assert LIVE_SRC == "/api/club-cam/hyc/live"


def test_live_url_is_http_preview_not_snapshot():
    os.environ["HYC_NVR_HOST"] = "hyc-nvr.example"
    os.environ["HYC_NVR_PORT"] = "80"
    os.environ["HYC_GO2RTC_SRC"] = "off"
    os.environ.pop("HYC_NVR_LIVE_URL", None)
    url = live_url()
    assert "/ISAPI/Streaming/channels/502/httpPreview" in url
    assert "/picture" not in url
    os.environ["HYC_NVR_LIVE_URL"] = "https://nvr.example/hls/cam5/index.m3u8"
    assert live_url().endswith("/hls/cam5/index.m3u8")
    assert stream_kind() == "hls"
    os.environ.pop("HYC_NVR_LIVE_URL", None)
    os.environ.pop("HYC_NVR_HOST", None)
    os.environ.pop("HYC_GO2RTC_SRC", None)
    assert "stream.m3u8?src=hyc" in live_url()
    assert stream_kind() == "hls"


def test_hls_playlist_rewrites_through_pass_through():
    os.environ["HYC_NVR_LIVE_URL"] = "https://nvr.example/hls/cam5/index.m3u8"
    text = "#EXTM3U\n#EXTINF:1,\nseg0.ts\n"
    out = rewrite_hls_playlist(text, "https://nvr.example/hls/cam5/index.m3u8")
    assert LIVE_SRC in out
    assert "seg0.ts" in out
    assert allowed_upstream("https://nvr.example/hls/cam5/seg0.ts") is True
    assert allowed_upstream("https://evil.example/x") is False
    os.environ.pop("HYC_NVR_LIVE_URL", None)


def test_show_hide_persists():
    path = Path("/tmp/sailingsa-club-cam-hyc-test.json")
    os.environ["HYC_CAM_VISIBLE_FILE"] = str(path)
    if path.exists():
        path.unlink()
    assert is_visible() is True
    assert set_visible(False) is False
    assert is_visible() is False
    assert set_visible(True) is True
    payload = status_payload(allowed=True, can_toggle=True)
    assert payload["can_toggle"] is True
    assert payload["channel"] == 5
    assert payload["src"] == "/api/club-cam/hyc/live"
    assert payload["reason"] == "pass-through"
    os.environ.pop("HYC_CAM_VISIBLE_FILE", None)
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    test_cam5_live_pass_through()
    test_live_url_is_http_preview_not_snapshot()
    test_hls_playlist_rewrites_through_pass_through()
    test_show_hide_persists()
    print("club_cam_hyc_min_tests: ok")
