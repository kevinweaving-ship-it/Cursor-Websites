#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "sailingsa" / "backend"))
from midmar_landing_cup import (  # noqa: E402
    MIDMAR_CUP_EVENT_IMG_SRC,
    MIDMAR_CUP_IMG_SRC,
    midmar_event_mm_videos,
    wrap_story_html,
)


def test_midmar_cup_left_history_right():
    html = wrap_story_html("<span>Recent Hunter 19 form</span>", "/regatta/2026-09-19-hmyc-midmar-cup")
    assert "landing-event-card-story-wrap--with-cup" in html
    assert 'class="landing-event-cup-img"' in html
    assert MIDMAR_CUP_IMG_SRC in html
    assert html.index("landing-event-cup-img") < html.index('class="landing-event-card-story"')
    assert "Recent Hunter 19 form" in html
    other = wrap_story_html("<span>Other</span>", "/regatta/2026-09-13-zvyc-cape-classic")
    assert "landing-event-cup-img" not in other
    assert wrap_story_html("", "/regatta/2026-09-19-hmyc-midmar-cup") == ""
    img = ROOT / "sailingsa/frontend/img/midmar-cup.jpg"
    ev = ROOT / "sailingsa/frontend/img/midmar-cup-event.jpg"
    assert img.is_file() and img.stat().st_size > 1000
    assert ev.is_file() and ev.stat().st_size > 1000
    assert MIDMAR_CUP_EVENT_IMG_SRC.endswith("Midmar-Cup-Event.jpg")
    vids = midmar_event_mm_videos()
    assert vids and vids[0]["thumb"] == MIDMAR_CUP_EVENT_IMG_SRC
    assert vids[1]["title"] == "Last minute Training and Setup"
    assert vids[1]["fb_sub"] == "Fri 18 Sep 2026 - 14:59"
    assert vids[1]["play_url"].endswith("Midmar-Last-Minute-Training.mp4")
    assert MIDMAR_CUP_IMG_SRC != MIDMAR_CUP_EVENT_IMG_SRC
    css = (ROOT / "sailingsa/backend/midmar_landing_cup.py").read_text(encoding="utf-8")
    assert "midmar-live-invert" in css


if __name__ == "__main__":
    test_midmar_cup_left_history_right()
    print("midmar_landing_cup_min_tests: ok")
