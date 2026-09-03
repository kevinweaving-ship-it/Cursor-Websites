#!/usr/bin/env python3
"""Public Lipton slug always serves the live board, even if playback hijack is re-inserted."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "LIPTON_PUBLIC_NOT_DEV_V3"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_PLAY = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    from pathlib import Path as _P
'''

NEW_PLAY = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    if public:
        # LIPTON_PUBLIC_NOT_DEV_V3 hijack public=True must still render the live board.
        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)
    from pathlib import Path as _P
'''

OLD_STAND = '''def serve_regatta_standalone(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
    """Serve one full standalone HTML result sheet for /regatta/{slug}. Unknown/missing → 404 (never /events)."""
    slug_s = str(slug or "").strip()
    # LIPTON_PUBLIC_NOT_DEV_V1 playback sandbox is -dev only; public Lipton URL stays the live board.
    # LIPTON_PUBLIC_NOT_DEV_V2 strip any re-inserted public-slug hijack above this.
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    start_time = time.time()
'''

NEW_STAND = '''def serve_regatta_standalone(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    # LIPTON_PUBLIC_NOT_DEV_V3
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    return _serve_regatta_standalone_impl(slug, request)


def _serve_regatta_standalone_impl(slug: str, request: Request):
    """Serve one full standalone HTML result sheet for /regatta/{slug}. Unknown/missing → 404 (never /events)."""
    start_time = time.time()
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n1 = text.count(OLD_PLAY)
    n2 = text.count(OLD_STAND)
    if n1 != 1:
        print(f"FAIL play: found {n1}", file=sys.stderr)
        return 1
    if n2 != 1:
        print(f"FAIL stand: found {n2}", file=sys.stderr)
        return 1
    text = text.replace(OLD_PLAY, NEW_PLAY, 1).replace(OLD_STAND, NEW_STAND, 1)
    tmp = Path("/tmp") / (API_PATH.name + ".v3patch")
    tmp.write_text(text, encoding="utf-8")
    rc = os.system(f"cp {tmp} {API_PATH}")
    if rc != 0:
        print("FAIL cp", rc, file=sys.stderr)
        return 1
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
