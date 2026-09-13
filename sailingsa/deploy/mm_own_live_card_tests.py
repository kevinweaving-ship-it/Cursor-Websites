#!/usr/bin/env python3
"""Guard: MM LIVE has its own card; old reels stay in the reel rail."""
from pathlib import Path

JS = Path(__file__).resolve().parents[1] / "frontend" / "js" / "mm-lipton-reels-card.js"


def test_own_live_card():
    js = JS.read_text(encoding="utf-8")
    assert "data-mm-live-slot" in js
    assert "function liveCardHtml" in js
    assert "function reelVideos" in js
    chunk = js[js.index("function liveCardHtml") : js.index("function liveCardHtml") + 900]
    assert "advertPoster" not in chunk
    assert "liveEmbedIframeHtml" in chunk
    assert "if (!mmFbLive(videos[i])) out.push(videos[i])" in js.replace("\n", " ") or "if (!mmFbLive(videos[i]))" in js


if __name__ == "__main__":
    test_own_live_card()
    print("ok")
