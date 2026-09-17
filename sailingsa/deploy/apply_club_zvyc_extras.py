#!/usr/bin/env python3
"""Keep ZVYC weather card + MM cards header in the gold club story."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARK = "ZVYC_LIVE_MEDIA_v1"
text = API.read_text()
if MARK in text:
    print("ALREADY")
    raise SystemExit(0)

old = '''    if meta_line:
        blocks.append(f'<p class="club-story-meta">{html_module.escape(meta_line)}</p>')
    blocks.append("</div>")
    if p.get("about_text"):
'''
new = '''    if meta_line:
        blocks.append(f'<p class="club-story-meta">{html_module.escape(meta_line)}</p>')
    blocks.append("</div>")
    if (abbrev or "").strip().upper() == "ZVYC":
        # ZVYC_LIVE_MEDIA_v1 — weather card + MM cards header under identity
        blocks.append(
            '<div id="club-zvyc-live-media" class="club-live-media" aria-label="Live weather and club camera">'
            '<section id="ssa-regatta-slot-card" class="card ssa-wx-card ssa-regatta-slot-card" '
            'data-weather-club="ZVYC" data-weather-role="venue" aria-label="Venue wind"></section>'
            '<section id="mmLiptonReels" class="card mm-lipton-reels mm-lipton-reels--compact" '
            'data-regatta-id="2026-09-13-zvyc-cape-classic" data-mm-poll="1" data-mm-club-page="1">'
            '<div class="mm-lipton-reels-compact">'
            '<a class="mm-lipton-reels-brand" href="https://www.marinemegastore.co.za/" target="_blank" rel="noopener noreferrer">'
            '<img src="/assets/adverts/mm-powered-by-live.png?v=mmcc2" alt="Powered by Marine Megastore Live Streaming" width="320" height="213" loading="lazy" decoding="async">'
            "</a>"
            '<div class="mm-lipton-reels-rail-wrap">'
            '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>'
            '<div class="mm-lipton-reels-rail" data-mm-compact></div>'
            '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>'
            "</div></div></section></div>"
        )
    if p.get("about_text"):
'''
if old not in text:
    raise SystemExit("STORY_INSERT_NOT_FOUND")

css_old = ".club-page .club-story-identity { text-align: center; }\n"
css_new = (
    ".club-page .club-story-identity { text-align: center; }\n"
    ".club-page .club-live-media{display:flex!important;flex-direction:column;width:100%;"
    "box-sizing:border-box;margin:0;padding:0;border:0;background:transparent;box-shadow:none;}\n"
    ".club-page .club-live-media .ssa-regatta-slot-card,"
    ".club-page .club-live-media .mm-lipton-reels{display:block!important;visibility:visible!important;width:100%;}\n"
)
if css_old not in text:
    raise SystemExit("CSS_NOT_FOUND")

text = text.replace(old, new, 1).replace(css_old, css_new, 1)
API.write_text(text)
print("ZVYC_EXTRAS")
