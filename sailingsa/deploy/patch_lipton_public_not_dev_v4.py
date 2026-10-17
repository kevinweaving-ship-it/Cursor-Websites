#!/usr/bin/env python3
"""Strip public-slug playback hijack sitting above LIPTON_PUBLIC_NOT_DEV_V3; restore public=True → impl."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "LIPTON_PUBLIC_NOT_DEV_V4"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_HIJACK = '''def serve_regatta_standalone(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
    slug_s = str(slug or "").strip()
    # LIPTON_PUBLIC_NOT_DEV_V3
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    return _serve_regatta_standalone_impl(slug, request)
'''

NEW_HIJACK = '''def serve_regatta_standalone(slug: str, request: Request):
    slug_s = str(slug or "").strip()
    # LIPTON_PUBLIC_NOT_DEV_V4
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    return _serve_regatta_standalone_impl(slug, request)
'''

OLD_PLAY = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    from pathlib import Path as _P
'''

NEW_PLAY = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    if public:
        # LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True must still render the live board.
        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)
    from pathlib import Path as _P
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text and "if public:" in text[text.find("def serve_lipton_dev_playback_page"):text.find("def serve_lipton_dev_playback_page")+400]:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n1 = text.count(OLD_HIJACK)
    n2 = text.count(OLD_PLAY)
    if n1 != 1:
        print(f"FAIL hijack: found {n1}", file=sys.stderr)
        return 1
    if n2 != 1:
        print(f"FAIL play: found {n2}", file=sys.stderr)
        return 1
    text = text.replace(OLD_HIJACK, NEW_HIJACK, 1).replace(OLD_PLAY, NEW_PLAY, 1)
    tmp = Path("/tmp") / (API_PATH.name + ".v4patch")
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
