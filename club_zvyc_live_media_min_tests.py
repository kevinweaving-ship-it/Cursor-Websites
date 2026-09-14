#!/usr/bin/env python3
"""ZVYC club page reuses Cape Classic weather + MM cam/reels (cam first).
All /club/{slug} pages share the site header and have no Back to Search / outer card."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def club_impl(src: str) -> str:
    start = src.find("def _serve_club_page_impl")
    end = src.find("def _format_regatta_host_display")
    assert start > 0 and end > start
    return src[start:end]


def test_injector_is_zvyc_only_and_sits_after_header():
    js = read("js/club-live-media.js")
    assert "CLUB_SLUG = 'zvyc'" in js
    assert "club-story-identity" in js
    assert "club-story-about" in js
    assert "data-weather-club" in js
    assert "data-mm-club-page" in js
    assert "2026-09-13-zvyc-cape-classic" in js
    assert "mm-powered-by-live.png" in js
    # WhatsApp overlay stays Cape Classic-only
    assert "data-weather-wa" not in js
    assert "host.className = 'club-live-media';" in js
    assert "club-live-media club-story-panel" not in js


def test_mm_sort_cam_first_on_club_page_only():
    js = read("js/mm-lipton-reels-card.js")
    assert "function isClubPage()" in js
    assert "if (isClubPage()) return cam.concat(mm);" in js
    assert "return mm.concat(cam);" in js


def test_weather_skips_cape_classic_auto_mount_on_club_page():
    js = read("js/regatta-slot-card.js")
    assert 'if (marine.getAttribute("data-mm-club-page") === "1") return;' in js


def test_api_club_page_inserts_host_below_header():
    src = read("api.py")
    impl = club_impl(src)
    assert 'id="club-zvyc-live-media"' in impl
    idx_header = impl.find("f'<div class=\"header\"><h1>{club_heading_html}</h1></div>'")
    idx_host = impl.find("{club_live_host}")
    idx_about_or_cal = impl.find("{sas_calendar_html}")
    assert idx_header > 0 and idx_host > idx_header
    assert idx_about_or_cal > idx_host
    assert "club-live-media.js?v=clubmm1" in impl
    assert 'class="club-live-media club-story-panel"' not in impl


def test_all_club_urls_share_header_and_drop_back_to_search():
    src = read("api.py")
    impl = club_impl(src)
    assert "Back to Search" not in impl
    assert "_CLUB_SITE_HEADER_HTML" in impl
    assert "admin-dashboard-v10" in impl
    assert "club-page-std.js?v=clubstd2" in impl
    assert "admin-v10-second-header" in src
    css = src[src.find("_CLUB_PAGE_CSS"): src.find("def serve_club_page")]
    assert "club-page-header" in css
    assert "border: none !important" in css or "border:none !important" in css
    js = read("js/club-page-std.js")
    assert "function isClubUrl()" in js
    assert "back to search" in js.lower()
    assert "admin-v10-second-header" in js
    assert ".club-page-header" in js
    assert "border:none!important" in js
    frontend = ROOT / "sailingsa/frontend/js/club-page-std.js"
    assert frontend.is_file()
    assert frontend.read_text(encoding="utf-8") == js


def test_live_club_html_can_host_inject_between_identity_and_about():
    html = (
        '<div class="club-story-inner">'
        '<div class="club-story-panel club-story-identity"><h1>ZVYC</h1></div>'
        '<div class="club-story-panel club-story-block">'
        '<div class="club-story-about">About text</div></div></div>'
    )
    host = (
        '<div id="club-zvyc-live-media" class="club-live-media"></div>'
    )
    ident = re.search(r'<div class="club-story-panel club-story-identity">.*?</div>', html)
    assert ident
    out = html[: ident.end()] + host + html[ident.end() :]
    assert out.index("club-story-identity") < out.index("club-zvyc-live-media")
    assert out.index("club-zvyc-live-media") < out.index("club-story-about")


if __name__ == "__main__":
    test_injector_is_zvyc_only_and_sits_after_header()
    test_mm_sort_cam_first_on_club_page_only()
    test_weather_skips_cape_classic_auto_mount_on_club_page()
    test_api_club_page_inserts_host_below_header()
    test_all_club_urls_share_header_and_drop_back_to_search()
    test_live_club_html_can_host_inject_between_identity_and_about()
    print("club_zvyc_live_media_min_tests: ok")
