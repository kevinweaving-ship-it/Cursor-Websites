#!/usr/bin/env python3
"""Guard: 4040 placeholder is not live; last-live stamp copy stays honest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zvyc_cam_live import playlist_is_actual_live, playlist_offline_reason  # noqa: E402

JS = Path(__file__).resolve().parents[1] / "frontend" / "js" / "mm-lipton-reels-card.js"

LIVE_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:12
#EXT-X-TARGETDURATION:6
#EXTINF:3.000,
https://hddn51.skylinewebcams.com/zeekoevlei-1789296871370.ts
#EXTINF:3.000,
https://hddn51.skylinewebcams.com/zeekoevlei-1789296874439.ts
"""

OFF_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:34936
#EXT-X-TARGETDURATION:6
#EXTINF:3.000,
https://hddn51.skylinewebcams.com/4040livic-1789296871370.ts
#EXTINF:3.000,
https://hddn51.skylinewebcams.com/4040livic-1789296874439.ts
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
    assert playlist_offline_reason(OFF_PLAYLIST, 200) == "placeholder_4040"
    assert playlist_is_actual_live(ENDED) is False
    assert playlist_offline_reason(ENDED, 200) == "ended"
    assert playlist_is_actual_live("") is False
    assert playlist_offline_reason("", 404) == "http_404"


def test_js_stamp_copy():
    js = JS.read_text(encoding="utf-8")
    assert "No live feed" in js
    assert "Last live " in js
    assert "Last image " not in js
    assert "data.last_live_at" in js
    assert "X-Zvyc-Cam-Last-Live" in js
    assert "root._mmCamUpstream" in js
    assert "root._mmCamReady || root._mmCamUpstream" not in js


if __name__ == "__main__":
    test_playlist_rules()
    test_js_stamp_copy()
    print("ok")
