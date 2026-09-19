#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "sailingsa" / "backend"))
from midmar_landing_cup import (  # noqa: E402
    MIDMAR_CUP_IMG_SRC,
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
    assert img.is_file() and img.stat().st_size > 1000


if __name__ == "__main__":
    test_midmar_cup_left_history_right()
    print("midmar_landing_cup_min_tests: ok")
