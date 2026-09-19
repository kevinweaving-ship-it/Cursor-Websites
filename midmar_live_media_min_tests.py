#!/usr/bin/env python3
"""Midmar Cup cam expands in-page; never links out to Agromet weather."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_midmar_cam_expands_not_redirects():
    js = (ROOT / "js/midmar-live-media.js").read_text(encoding="utf-8")
    assert "midmarwx19" in js
    assert "placeCup" not in js
    assert "makeMmCard" in js
    assert "mmLiptonReels" in js
    assert "Midmar-Cup-Event.jpg" in js
    assert "mm-lipton-reels-card.js" in js
    assert ".mm-lipton-reels{order:1" in js
    assert "mmLiptonReelsInit" in js
    assert "aspect-ratio:3 / 4" in js
    assert "mm-lipton-reels-brand{display:none!important;}" in js
    assert 'data-mm-vid="midmar-cup-1"' in js
    assert "Midmar-Cup-Event.jpg" in js
    assert js.index('data-mm-vid="midmar-cup-1"') < js.index('data-mm-vid="midmar-train-1"')
    assert "Last minute Training and Setup" in js
    assert "Fri 18 Sep 2026 - 14:59" in js
    assert "Midmar-Last-Minute-Training.mp4" in js
    assert ".mm-lipton-reels-play{display:none!important;}" in js
    assert "19 Sep 2026" in js
    assert ".midmar-hmyc-cam{order:2" in js
    assert "injectFleetResultsStatus" in js
    assert "Results are Provisional" in js
    assert "19 Sep 2026" in js
    assert "fleet-results-status" in js
    assert "fleet-results-as-at" in js
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
    assert "<a class=\"cam-frame\"" not in js
    assert js.count('target="_blank"') == 1
    assert "mm-lipton-reels-brand" in js
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
    card = (ROOT / "js/mm-lipton-reels-card.js").read_text(encoding="utf-8")
    assert "function isMidmar()" in card
    assert "window.mmLiptonReelsInit = init" in card
    assert "var hideBrand = singleCamRoot(root) || isMidmar();" in card
    assert "var vid = isMidmar() ? 3 / 4 : VID_W / VID_H;" in card
    assert "if (isMidmar()) return list;" in card
    assert "function midmarThumbStamp" in card
    assert (ROOT / "sailingsa/frontend/js/mm-lipton-reels-card.js").read_text(
        encoding="utf-8"
    ) == card


def test_midmar_fleet_header_results_status_helper():
    import re

    api = (ROOT / "api.py").read_text(encoding="utf-8")
    m = re.search(
        r"_MIDMAR_CUP_REGATTA_ID = .*?\ndef _midmar_fleet_header_results_status_html.*?(?=\ndef )",
        api,
        re.S,
    )
    assert m, "helper missing from api.py"
    ns = {}
    exec(m.group(0), ns)
    fn = ns["_midmar_fleet_header_results_status_html"]
    html = fn("2026-09-19-hmyc-midmar-cup")
    assert "Results are Provisional" in html
    assert "19 Sep 2026" in html
    assert " at " not in html
    assert fn("other-regatta") == ""
    assert "_midmar_fleet_header_results_status_html(regatta_id)" in api


if __name__ == "__main__":
    test_midmar_cam_expands_not_redirects()
    test_midmar_fleet_header_results_status_helper()
    print("midmar_live_media_min_tests: ok")
