#!/usr/bin/env python3
"""Guard: 4040 placeholder is not live; last-live stamp copy stays honest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zvyc_cam_live import playlist_is_actual_live, playlist_offline_reason  # noqa: E402

JS = Path(__file__).resolve().parents[1] / "frontend" / "js" / "mm-lipton-reels-card.js"

LIVE_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:35531
#EXT-X-TARGETDURATION:6
#EXTINF:3.000,
https://hddn54.skylinewebcams.com/4040livic-1789299007564.ts
#EXTINF:3.000,
https://hddn54.skylinewebcams.com/4040livic-1789299010460.ts
"""

OFF_PLAYLIST = """#EXTM3U
#EXTINF:3.000,
https://www.skylinewebcams.com/temp/4040.jpg
#EXT-X-ENDLIST
"""

ENDED = """#EXTM3U
#EXTINF:3.000,
https://hddn51.skylinewebcams.com/zeekoevlei-1.ts
#EXT-X-ENDLIST
"""


def test_playlist_rules():
    assert playlist_is_actual_live(LIVE_PLAYLIST) is True
    assert playlist_offline_reason(LIVE_PLAYLIST, 200) == "hls"
    assert playlist_is_actual_live(OFF_PLAYLIST) is False
    assert playlist_offline_reason(OFF_PLAYLIST, 200) in ("placeholder_4040", "ended")
    assert playlist_is_actual_live(ENDED) is False
    assert playlist_offline_reason(ENDED, 200) == "ended"
    assert playlist_is_actual_live("") is False
    assert playlist_offline_reason("", 404) == "http_404"


def test_js_stamp_copy():
    js = JS.read_text(encoding="utf-8")
    assert "Offline" in js
    assert "label.textContent = live ? 'LIVE' : 'Offline'" in js
    assert "No live feed" not in js
    assert "No Live available" not in js
    assert "Last image " not in js
    assert "data.last_live_at" in js
    assert "left:118px" in js
    assert "function fmtClock" in js
    chunk = js[js.index("function paintCamStamps") : js.index("function paintCamStamps") + 900]
    assert "function showingZvycCam" in js
    assert "hideAllCamStamps" in js
    assert "clip-chrome--zvyc" in js
    assert "var live = !!root._mmCamUpstream;" in chunk
    assert "hud && isCapeClassic()" not in chunk


if __name__ == "__main__":
    test_playlist_rules()
    test_js_stamp_copy()
    print("ok")
