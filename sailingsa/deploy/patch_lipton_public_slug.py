#!/usr/bin/env python3
"""Serve Lipton playback on the public slug. Does not replace whole api.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
PUBLIC = "2026-08-29-lipton-challenge-cup"
DEV = PUBLIC + "-dev"

PLAYBACK_FN = '''LIPTON_DEV_SLUG = "2026-08-29-lipton-challenge-cup-dev"
LIPTON_PUBLIC_SLUG = "2026-08-29-lipton-challenge-cup"


def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    from pathlib import Path as _P
    names = (
        _P("/var/www/sailingsa/lipton-dev.html"),
        _P("/var/www/sailingsa/frontend/lipton-dev.html"),
    )
    headers = {"Cache-Control": "no-store"}
    if not public:
        headers["X-Robots-Tag"] = "noindex, nofollow"
    for p in names:
        try:
            if p.is_file():
                from fastapi.responses import HTMLResponse as _HR
                return _HR(p.read_text(encoding="utf-8"), headers=headers)
        except OSError:
            continue
    from fastapi.responses import HTMLResponse as _HR2
    return _HR2("Lipton playback page missing", status_code=500)


'''

EARLY = '''    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
'''

OLD_EARLY = [
    '''    if str(slug or "").strip() == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request)
''',
    '''    if str(slug or "").strip() == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
''',
]


def _replace_playback_block(text: str) -> str:
    pat = re.compile(
        r'LIPTON_DEV_SLUG = "2026-08-29-lipton-challenge-cup-dev"\n+'
        r'(?:LIPTON_PUBLIC_SLUG = "2026-08-29-lipton-challenge-cup"\n+)?'
        r'def serve_lipton_dev_playback_page\([\s\S]*?\n(?=\n(?:def |@app\.))',
        re.M,
    )
    if pat.search(text):
        return pat.sub(PLAYBACK_FN.rstrip() + "\n", text, count=1)
    needle = "def serve_regatta_standalone(slug: str, request: Request):"
    if needle not in text:
        raise SystemExit("ERROR: serve_regatta_standalone not found")
    if "def serve_lipton_dev_playback_page" not in text:
        text = text.replace(needle, PLAYBACK_FN + needle, 1)
    return text


def _ensure_early(text: str) -> str:
    needle = "def serve_regatta_standalone(slug: str, request: Request):"
    after = text.split(needle, 1)[-1][:1200] if needle in text else ""
    if f'slug_s == "{PUBLIC}"' in after and "public=True" in after:
        return text
    for old in OLD_EARLY:
        if old in text:
            return text.replace(old, EARLY, 1)
    # -dev hook exists but public slug was never added — insert both.
    if "return serve_lipton_dev_playback_page" in after:
        idx = text.find(needle)
        insert_at = text.find("\n", idx) + 1
        return text[:insert_at] + EARLY + text[insert_at:]
    if needle in text:
        return text.replace(needle + "\n", needle + "\n" + EARLY, 1)
    return text


def _playback_is_real(text: str) -> bool:
    """False if another process inverted playback into the old event page."""
    m = re.search(
        r"def serve_lipton_dev_playback_page\([\s\S]*?\n(?=\n(?:def |@app\.))",
        text,
    )
    body = m.group(0) if m else ""
    if "_serve_regatta_standalone_impl" in body:
        return False
    if "lipton-dev.html" not in body:
        return False
    after = text.split("def serve_regatta_standalone", 1)[-1][:1200]
    if f'slug_s == "{PUBLIC}"' not in after:
        return False
    if "public=True" not in after:
        return False
    return True


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if _playback_is_real(text):
        print("public slug already patched")
        return 0
    text = _replace_playback_block(text)
    text = _ensure_early(text)
    if not _playback_is_real(text):
        print("ERROR: playback hook still inverted or public slug missing", file=sys.stderr)
        return 1
    API.write_text(text, encoding="utf-8")
    print("patched public slug", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
