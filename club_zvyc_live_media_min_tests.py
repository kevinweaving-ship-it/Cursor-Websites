#!/usr/bin/env python3
"""ZVYC club page reuses Cape Classic weather + MM cam/reels (cam first)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


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
    assert 'id="club-zvyc-live-media"' in src
    idx_header = src.find("f'<div class=\"header\"><h1>{club_heading_html}</h1></div>'")
    idx_host = src.find("{club_live_host}")
    idx_about_or_cal = src.find("{sas_calendar_html}")
    assert idx_header > 0 and idx_host > idx_header
    assert idx_about_or_cal > idx_host
    assert "club-live-media.js?v=clubmm1" in src


def test_live_club_html_can_host_inject_between_identity_and_about():
    html = (
        '<div class="club-story-inner">'
        '<div class="club-story-panel club-story-identity"><h1>ZVYC</h1></div>'
        '<div class="club-story-panel club-story-block">'
        '<div class="club-story-about">About text</div></div></div>'
    )
    host = (
        '<div id="club-zvyc-live-media" class="club-live-media club-story-panel"></div>'
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
    test_live_club_html_can_host_inject_between_identity_and_about()
    print("club_zvyc_live_media_min_tests: ok")
