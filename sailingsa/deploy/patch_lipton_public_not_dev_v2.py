#!/usr/bin/env python3
"""Remove re-inserted public-slug hijack that sits above LIPTON_PUBLIC_NOT_DEV_V1."""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_PUBLIC_NOT_DEV_V2"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''def serve_regatta_standalone(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
    """Serve one full standalone HTML result sheet for /regatta/{slug}. Unknown/missing → 404 (never /events)."""
    slug_s = str(slug or "").strip()
    # LIPTON_PUBLIC_NOT_DEV_V1 playback sandbox is -dev only; public Lipton URL stays the live board.
'''

NEW = '''def serve_regatta_standalone(slug: str, request: Request):
    """Serve one full standalone HTML result sheet for /regatta/{slug}. Unknown/missing → 404 (never /events)."""
    slug_s = str(slug or "").strip()
    # LIPTON_PUBLIC_NOT_DEV_V1 playback sandbox is -dev only; public Lipton URL stays the live board.
    # LIPTON_PUBLIC_NOT_DEV_V2 strip any re-inserted public-slug hijack above this.
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL public-not-dev-v2: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
