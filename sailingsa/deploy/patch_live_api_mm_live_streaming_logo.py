#!/usr/bin/env python3
"""Cape Classic MM reels card: use red Live Streaming brand logo.

Live file already exists: /assets/adverts/mm-powered-by-live.png
(Lipton Event Reels brand unchanged.)
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")

API_REPLACEMENTS = [
    (
        '''_MM_COMING_SOON_BRAND_SRC = "/assets/adverts/mm-powered-by-coming-soon.jpg?v=mmcc1"
_MM_EVENT_REELS_BRAND_SRC = "/assets/adverts/mm-powered-by-event-reels.png?v=mmr3"''',
        '''_MM_COMING_SOON_BRAND_SRC = "/assets/adverts/mm-powered-by-coming-soon.jpg?v=mmcc1"
_MM_EVENT_REELS_BRAND_SRC = "/assets/adverts/mm-powered-by-event-reels.png?v=mmr3"
_MM_LIVE_STREAMING_BRAND_SRC = "/assets/adverts/mm-powered-by-live.png?v=mmcc2"''',
    ),
    (
        '''    brand_src = _MM_EVENT_REELS_BRAND_SRC if has_clips else _MM_COMING_SOON_BRAND_SRC
    brand_alt = (
        "Powered by Marine Megastore Event Reels"
        if has_clips
        else "Powered by Marine Megastore Coming Soon"
    )''',
        '''    brand_src = _MM_LIVE_STREAMING_BRAND_SRC
    brand_alt = "Powered by Marine Megastore Live Streaming"''',
    ),
    (
        '''        f'data-mm-brand-soon="{html_module.escape(_MM_COMING_SOON_BRAND_SRC)}" '
        f'data-mm-brand-live="{html_module.escape(_MM_EVENT_REELS_BRAND_SRC)}" \'''',
        '''        f'data-mm-brand-soon="{html_module.escape(_MM_LIVE_STREAMING_BRAND_SRC)}" '
        f'data-mm-brand-live="{html_module.escape(_MM_LIVE_STREAMING_BRAND_SRC)}" \'''',
    ),
    (
        """mm_card_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr118" defer></script>""",
        """mm_card_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr119" defer></script>""",
    ),
]

JS_REPLACEMENTS = [
    (
        """    var next = has ? live || '/assets/adverts/mm-powered-by-event-reels.png?v=mmr2' : soon;
    if (img.getAttribute('src') !== next) img.setAttribute('src', next);
    img.setAttribute('alt', has ? 'Powered by Marine Megastore Event Reels' : 'Powered by Marine Megastore Coming Soon');""",
        """    var next = has ? live || '/assets/adverts/mm-powered-by-event-reels.png?v=mmr2' : soon;
    if (img.getAttribute('src') !== next) img.setAttribute('src', next);
    var alt = 'Powered by Marine Megastore Coming Soon';
    if (String(next).indexOf('powered-by-live') !== -1) alt = 'Powered by Marine Megastore Live Streaming';
    else if (has) alt = 'Powered by Marine Megastore Event Reels';
    img.setAttribute('alt', alt);""",
    ),
]


def apply(path: Path, reps: list) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(reps, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    api = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    js = Path(sys.argv[2]) if len(sys.argv) > 2 else JS
    apply(api, API_REPLACEMENTS)
    apply(js, JS_REPLACEMENTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
