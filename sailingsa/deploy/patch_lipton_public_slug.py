#!/usr/bin/env python3
"""Detach the old Lipton weather/event page from the public slug.

Does not replace whole api.py. Public /regatta/2026-08-29-lipton-challenge-cup
serves playback HTML. Old event HTML only at /event.
"""
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
    """Playback HTML. The public Lipton URL is this page, not the old weather/event HTML."""
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

SIG_OLD = "def serve_regatta_standalone(slug: str, request: Request):"
SIG_NEW = "def serve_regatta_standalone(slug: str, request: Request, *, allow_lipton_event: bool = False):"

EARLY = '''    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup" and not allow_lipton_event:
        return serve_lipton_dev_playback_page(request, public=True)
'''

EVENT_ROUTE = '''@app.get("/regatta/2026-08-29-lipton-challenge-cup/event")
@app.head("/regatta/2026-08-29-lipton-challenge-cup/event")
def _lipton_old_event_page_not_public(request: Request):
    """Old weather/event HTML only. Not the public Lipton URL."""
    return serve_regatta_standalone(
        "2026-08-29-lipton-challenge-cup", request, allow_lipton_event=True
    )


'''

OLD_EARLY = [
    '''    if str(slug or "").strip() == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request)
''',
    '''    if str(slug or "").strip() == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
''',
    '''    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
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
    if SIG_NEW in text or SIG_OLD in text:
        if "def serve_lipton_dev_playback_page" not in text:
            needle = SIG_NEW if SIG_NEW in text else SIG_OLD
            text = text.replace(needle, PLAYBACK_FN + needle, 1)
        return text
    raise SystemExit("ERROR: serve_regatta_standalone not found")


def _ensure_signature(text: str) -> str:
    if SIG_NEW in text:
        return text
    if SIG_OLD not in text:
        raise SystemExit("ERROR: serve_regatta_standalone signature not found")
    return text.replace(SIG_OLD, SIG_NEW, 1)


def _ensure_early(text: str) -> str:
    after = text.split("def serve_regatta_standalone", 1)[-1][:1600]
    if f'slug_s == "{PUBLIC}"' in after and "not allow_lipton_event" in after and "public=True" in after:
        return text
    for old in OLD_EARLY:
        if old in text:
            return text.replace(old, EARLY, 1)
    idx = text.find(SIG_NEW)
    if idx < 0:
        raise SystemExit("ERROR: cannot insert public-slug early return")
    insert_at = text.find("\n", idx) + 1
    return text[:insert_at] + EARLY + text[insert_at:]


def _ensure_event_route(text: str) -> str:
    if "/regatta/2026-08-29-lipton-challenge-cup/event" in text:
        return text
    needle = '@app.get("/regatta/{slug}")\n@app.head("/regatta/{slug}")\ndef _regatta_standalone'
    if needle not in text:
        print("WARN: could not insert /event route", file=sys.stderr)
        return text
    return text.replace(needle, EVENT_ROUTE + needle, 1)


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
    after = text.split("def serve_regatta_standalone", 1)[-1][:1600]
    if f'slug_s == "{PUBLIC}"' not in after:
        return False
    if "public=True" not in after:
        return False
    if "not allow_lipton_event" not in after:
        return False
    if "/regatta/2026-08-29-lipton-challenge-cup/event" not in text:
        return False
    return True


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if _playback_is_real(text):
        print("old page already detached from public slug")
        return 0
    text = _replace_playback_block(text)
    text = _ensure_signature(text)
    text = _ensure_early(text)
    text = _ensure_event_route(text)
    if not _playback_is_real(text):
        print("ERROR: old page still owns public slug or playback inverted", file=sys.stderr)
        return 1
    API.write_text(text, encoding="utf-8")
    print("detached old page from public slug", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
