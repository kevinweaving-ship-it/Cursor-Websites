#!/usr/bin/env python3
"""Club weather + live-cam cards: ZVYC example reused for HYC and HMYC."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_injector_covers_zvyc_hyc_hmyc_with_club_logo():
    js = read("js/club-live-media.js")
    assert "CLUBS = {" in js
    assert "zvyc:" in js and "hyc:" in js and "hmyc:" in js
    assert "pws-iovers2" in js
    assert "agromet-midmar" in js
    assert "wunderground.com/dashboard/pws/IOVERS2" in js
    assert "agromet.ukzn.ac.za/midmar" in js
    assert "hmyccam1.nwsza.net/latest.jpg" in js
    assert "snapshot: true" in js
    assert "livePass: true" in js
    assert "liveCam: HYC_LIVE_CAM" in js or "liveCam: 'hyc-club'" in js or 'liveCam: HYC_LIVE_CAM' in js
    assert "/api/club-cam/hyc" in js
    assert "https://sailingsa.co.za:8443/api/ws?src=hyc" in js
    assert "club-hyc-cam" in js
    assert "hyc-club-cam" in js
    assert "startHycGo2rtc" in js
    assert "SSALiveCam" in js
    assert "live-cam-sources.js" in js
    assert 'data-cam="hyc"' in js
    assert "cam-cell" in js
    assert "video-stream.js" in js
    assert "webrtc,mse" in js
    assert "Hide live cam from public" in js
    assert "Show live cam to public" in js
    assert "data-live-cam" in js
    assert "fb_owner_logo" not in js
    assert "mmLiptonReels" in js
    assert "makeClubCam" not in js
    assert "clubLiveCam" not in js
    assert "HMYC live cam" not in js
    assert "Live cam coming soon" not in js
    assert "/artwork/Club Logo/ZVYC.png" in js
    assert "/artwork/Club Logo/HYC.png" in js
    assert "/artwork/Club Logo/HMYC.png" in js
    assert "mm-powered-by-live.png" not in js
    assert "marinemegastore.co.za" not in js
    assert "data-weather-club" in js
    assert "orderCards" in js
    frontend = ROOT / "sailingsa/frontend/js/club-live-media.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


def test_live_cam_sources_catalog_is_shared_for_club_and_mm():
    js = read("js/live-cam-sources.js")
    assert "hyc-club" in js
    assert "hmyc-club" in js
    assert "clubSurface: 'permanent'" in js
    assert "mmSurface: true" in js
    assert "how: 'go2rtc'" in js
    assert "how: 'snapshot'" in js
    assert "video-stream" in js
    assert "webrtc,mse" in js
    assert "api/ws?src=" in js
    assert "never rewrite" in js
    assert "SSALiveCam" in js
    assert "function mmVideo" in js
    assert "eventVideo: mmVideo" in js
    assert "function attach" in js
    assert "function start" in js
    assert "querySelector('video-stream')" in js
    assert "cam-cell" in js
    assert 'api/ws?src=' in js
    frontend = ROOT / "sailingsa/frontend/js/live-cam-sources.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


def test_club_page_mm_brand_stays_club_logo():
    js = read("js/mm-lipton-reels-card.js")
    assert "data-mm-club-logo" in js
    assert "isClubPage() && clubLogo" in js
    assert "MM_STORE_HOME" in js
    assert "isSnapshotCam" in js
    assert "SNAPSHOT" in js
    assert "pollSnapshotCam" in js
    assert "liveStillCamRoot" in js
    assert "https://sailingsa.co.za:8443/" in js
    assert "video-stream.js" in js
    assert "api/ws?src=" in js
    assert "webrtc,mse" in js
    assert "singleCamRoot" in js
    assert "data-mm-live-still" in js
    assert "data-mm-live-pass" in js
    assert "data-live-cam" in js
    assert "SSALiveCam" in js
    assert "live-cam-sources.js" in js
    frontend = ROOT / "sailingsa/frontend/js/mm-lipton-reels-card.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


def test_weather_card_uses_agromet_history_path():
    js = read("js/regatta-slot-card.js")
    assert "/api/weather/agromet-midmar/history" in js
    assert "/api/weather/hyc/history" in js
    assert 'if (marine.getAttribute("data-mm-club-page") === "1") return;' in js
    assert "data-hours" in js
    assert "sizeSparkPlot" in js
    assert "Last Hour" in js
    assert "older · swipe" not in js
    assert "wx-x-mid" in js
    frontend = ROOT / "sailingsa/frontend/js/regatta-slot-card.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


def test_api_club_page_loads_live_media_script():
    src = read("api.py")
    assert "club-live-media.js?v=clubwx15" in src
    assert "live-cam-sources.js?v=clubwx15" in src
    assert "mm-lipton-reels.css?v=clubwx15" in src
    assert "/api/weather/agromet-midmar/history" in src
    assert "/api/weather/hyc/history" in src
    assert "/api/club-cam/hyc/live" in src
    assert "/api/super-admin/club-cam/hyc" in src
    impl_start = src.find("def _serve_club_page_impl")
    impl_end = src.find("def _format_regatta_host_display")
    impl = src[impl_start:impl_end]
    assert "club-live-media.js?v=clubwx15" in impl


def test_live_club_html_can_host_inject_between_identity_and_about():
    html = (
        '<div class="club-story-inner">'
        '<div class="club-story-panel club-story-identity"><h1>HYC</h1></div>'
        '<div class="club-story-panel club-story-block">'
        '<div class="club-story-about">About text</div></div></div>'
    )
    host = '<div id="club-live-media" class="club-live-media"></div>'
    ident = re.search(r'<div class="club-story-panel club-story-identity">.*?</div>', html)
    assert ident
    out = html[: ident.end()] + host + html[ident.end() :]
    assert out.index("club-story-identity") < out.index("club-live-media")
    assert out.index("club-live-media") < out.index("club-story-about")


if __name__ == "__main__":
    test_injector_covers_zvyc_hyc_hmyc_with_club_logo()
    test_live_cam_sources_catalog_is_shared_for_club_and_mm()
    test_club_page_mm_brand_stays_club_logo()
    test_weather_card_uses_agromet_history_path()
    test_api_club_page_loads_live_media_script()
    test_live_club_html_can_host_inject_between_identity_and_about()
    print("club_zvyc_live_media_min_tests: ok")
