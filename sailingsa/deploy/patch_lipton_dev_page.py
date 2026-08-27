#!/usr/bin/env python3
"""Patch live api.py with Lipton -dev slug hook. Does not replace the whole file."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
NEEDLE = "def serve_regatta_standalone(slug: str, request: Request):"
HOOK = '''LIPTON_DEV_SLUG = "2026-08-29-lipton-challenge-cup-dev"


def serve_lipton_dev_playback_page(_request):
    """Isolated Lipton playback mirror. Does not touch the public Lipton URL."""
    from pathlib import Path as _P
    names = (
        _P("/var/www/sailingsa/lipton-dev.html"),
        _P("/var/www/sailingsa/frontend/lipton-dev.html"),
    )
    for p in names:
        try:
            if p.is_file():
                from fastapi.responses import HTMLResponse as _HR
                return _HR(
                    p.read_text(encoding="utf-8"),
                    headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"},
                )
        except OSError:
            continue
    from fastapi.responses import HTMLResponse as _HR2
    return _HR2("Lipton dev page missing", status_code=500)


'''
EARLY = '''    if str(slug or "").strip() == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request)
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if "serve_lipton_dev_playback_page" in text and "lipton-challenge-cup-dev" in text:
        print("already patched")
        return 0
    if NEEDLE not in text:
        print("ERROR: serve_regatta_standalone not found", file=sys.stderr)
        return 1
    if "def serve_lipton_dev_playback_page" not in text:
        text = text.replace(NEEDLE, HOOK + NEEDLE, 1)
    # insert early return after docstring / first line of function
    old = NEEDLE + '\n    """Serve one full standalone HTML result sheet for /regatta/{slug}. Unknown regatta → 301 /events (not 404)."""\n'
    new = NEEDLE + '\n    """Serve one full standalone HTML result sheet for /regatta/{slug}. Unknown regatta → 301 /events (not 404)."""\n' + EARLY
    if old in text and "lipton-challenge-cup-dev" not in text.split("def serve_regatta_standalone", 1)[-1][:800]:
        text = text.replace(old, new, 1)
    elif "return serve_lipton_dev_playback_page" not in text:
        text = text.replace(
            NEEDLE + "\n",
            NEEDLE + "\n" + EARLY,
            1,
        )
    API.write_text(text, encoding="utf-8")
    print("patched", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
