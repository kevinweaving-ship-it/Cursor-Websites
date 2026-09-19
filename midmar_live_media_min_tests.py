#!/usr/bin/env python3
"""Midmar Cup cam expands in-page; never links out to Agromet weather."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_midmar_cam_expands_not_redirects():
    js = (ROOT / "js/midmar-live-media.js").read_text(encoding="utf-8")
    assert "midmarwx5" in js
    assert "hmyccam1.nwsza.net/latest.jpg" in js
    assert "button type=\"button\" class=\"cam-frame\"" in js
    assert "is-open" in js
    assert "position:fixed" in js
    assert "mm-lipton-reels-hide" in js
    assert "data-mm-hide" in js
    assert ">Hide<" in js
    assert "site-header{display:none!important;}" in js
    assert "backToEvent" in js
    assert "agromet.ukzn.ac.za" not in js
    assert "target=\"_blank\"" not in js
    assert "<a class=\"cam-frame\"" not in js
    assert "midmar-cam-wx" in js
    assert "data-mm-cam-wx-temp" in js
    assert "data-mm-cam-wx-kn" in js
    assert "data-mm-cam-wx-gauge" in js
    assert "/api/weather/agromet-midmar/history" in js
    assert " kn" in js
    frontend = ROOT / "sailingsa/frontend/js/midmar-live-media.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


if __name__ == "__main__":
    test_midmar_cam_expands_not_redirects()
    print("midmar_live_media_min_tests: ok")
