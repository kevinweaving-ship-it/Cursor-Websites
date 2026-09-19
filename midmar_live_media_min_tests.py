#!/usr/bin/env python3
"""Midmar Cup cam expands in-page; never links out to Agromet weather."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_midmar_cam_expands_not_redirects():
    js = (ROOT / "js/midmar-live-media.js").read_text(encoding="utf-8")
    assert "midmarwx13" in js
    assert "hmyccam1.nwsza.net/latest.jpg" in js
    assert "button type=\"button\" class=\"cam-frame\"" in js
    assert 'class="cam-shot"' in js
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
    assert "/api/weather/agromet-midmar/history?hours=12" in js
    assert "darc.prev" in js
    assert "viewFromReadings" in js
    assert "uniq" in js
    assert "placeWxOnImage" not in js
    assert "width:72px" in js
    assert "top:8px;right:8px" in js
    assert ".cam-shot .midmar-cam-wx" in js
    assert "color:#000" in js
    assert "fill:#000" in js
    assert ".dhead{fill:#000!important;}" in js
    assert " kn" in js
    assert ".midmar-hmyc-cam .midmar-cam-wx{display:none;}" in js
    assert "NNE" in js
    frontend = ROOT / "sailingsa/frontend/js/midmar-live-media.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


if __name__ == "__main__":
    test_midmar_cam_expands_not_redirects()
    print("midmar_live_media_min_tests: ok")
