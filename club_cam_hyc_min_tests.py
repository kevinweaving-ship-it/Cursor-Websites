#!/usr/bin/env python3
"""HYC live cam is Hikvision Cam 5 on the DS NVR; SA can show/hide."""
import os
from pathlib import Path

from sailingsa.backend.club_cam_hyc import (
    CAM_NO,
    INTERVAL_SEC,
    ISAPI_CHANNEL,
    KIND,
    LABEL,
    is_visible,
    picture_url,
    set_visible,
    status_payload,
)


def test_cam5_isapi_channel():
    assert CAM_NO == 5
    assert ISAPI_CHANNEL == 501
    assert KIND == "live"
    assert INTERVAL_SEC == 2
    assert LABEL == "HYC club cam"


def test_picture_url_uses_cam5(monkey_host=None):
    os.environ["HYC_NVR_HOST"] = "hyc-nvr.example"
    os.environ["HYC_NVR_PORT"] = "80"
    url = picture_url()
    assert "/ISAPI/Streaming/channels/501/picture" in url
    assert "hyc-nvr.example" in url
    os.environ.pop("HYC_NVR_HOST", None)


def test_show_hide_persists():
    path = Path("/tmp/sailingsa-club-cam-hyc-test.json")
    os.environ["HYC_CAM_VISIBLE_FILE"] = str(path)
    if path.exists():
        path.unlink()
    assert is_visible() is True
    assert set_visible(False) is False
    assert is_visible() is False
    assert set_visible(True) is True
    assert is_visible() is True
    payload = status_payload(allowed=True, can_toggle=True)
    assert payload["can_toggle"] is True
    assert payload["channel"] == 5
    assert payload["src"] == "/api/club-cam/hyc/snapshot"
    os.environ.pop("HYC_CAM_VISIBLE_FILE", None)
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    test_cam5_isapi_channel()
    test_picture_url_uses_cam5()
    test_show_hide_persists()
    print("club_cam_hyc_min_tests: ok")
