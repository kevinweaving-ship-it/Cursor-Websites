#!/usr/bin/env python3
"""Public Lipton slug = playback. Old weather page only at -old. Does not replace whole api.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
PUBLIC = "2026-08-29-lipton-challenge-cup"
DEV = PUBLIC + "-dev"
OLD = PUBLIC + "-old"

PLAYBACK_FN = '''LIPTON_DEV_SLUG = "2026-08-29-lipton-challenge-cup-dev"
LIPTON_PUBLIC_SLUG = "2026-08-29-lipton-challenge-cup"
LIPTON_OLD_SLUG = "2026-08-29-lipton-challenge-cup-old"


def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Playback HTML. Public Lipton URL only. Old weather page is -old."""
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
    if slug_s == "2026-08-29-lipton-challenge-cup-old":
        slug_s = "2026-08-29-lipton-challenge-cup"
        slug = "2026-08-29-lipton-challenge-cup"
        allow_lipton_event = True
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup" and not allow_lipton_event:
        return serve_lipton_dev_playback_page(request, public=True)
'''


def _replace_playback_block(text: str) -> str:
    pat = re.compile(
        r'LIPTON_DEV_SLUG = "2026-08-29-lipton-challenge-cup-dev"\n+'
        r'(?:LIPTON_PUBLIC_SLUG = "2026-08-29-lipton-challenge-cup"\n+)?'
        r'(?:LIPTON_OLD_SLUG = "2026-08-29-lipton-challenge-cup-old"\n+)?'
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
    after = text.split("def serve_regatta_standalone", 1)[-1][:2000]
    if f'slug_s == "{OLD}"' in after and "not allow_lipton_event" in after:
        return text
    without_old = '''    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup" and not allow_lipton_event:
        return serve_lipton_dev_playback_page(request, public=True)
'''
    if without_old in text:
        return text.replace(without_old, EARLY, 1)
    idx = text.find(SIG_NEW)
    if idx < 0:
        raise SystemExit("ERROR: cannot insert -old mapping")
    insert_at = text.find("\n", idx) + 1
    return text[:insert_at] + EARLY + text[insert_at:]


def _ok(text: str) -> bool:
    m = re.search(
        r"def serve_lipton_dev_playback_page\([\s\S]*?\n(?=\n(?:def |@app\.))",
        text,
    )
    body = m.group(0) if m else ""
    if "_serve_regatta_standalone_impl" in body or "lipton-dev.html" not in body:
        return False
    after = text.split("def serve_regatta_standalone", 1)[-1][:2000]
    return f'slug_s == "{OLD}"' in after and "not allow_lipton_event" in after


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if _ok(text):
        print("old page already on -old slug")
        return 0
    text = _replace_playback_block(text)
    text = _ensure_signature(text)
    text = _ensure_early(text)
    if not _ok(text):
        print("ERROR: -old mapping missing", file=sys.stderr)
        return 1
    API.write_text(text, encoding="utf-8")
    print("old page mapped to -old slug", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
