#!/usr/bin/env python3
"""Public slug = playback HTML. -old = weather page. Undo LIPTON_PUBLIC_NOT_DEV hijack."""
from __future__ import annotations

import re
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

PLAYBACK_FN = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
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

EARLY = '''def serve_regatta_standalone(slug: str, request: Request, *, allow_lipton_event: bool = False):
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup":
        return serve_lipton_dev_playback_page(request, public=True)
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    if slug_s == "2026-08-29-lipton-challenge-cup-old":
        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", request)
    return _serve_regatta_standalone_impl(slug, request)


'''


def _replace_fn(text: str, name: str, new: str) -> str:
    pat = re.compile(
        rf"def {name}\([\s\S]*?\n(?=\n(?:def |@app\.))",
        re.M,
    )
    if not pat.search(text):
        raise SystemExit(f"ERROR: {name} not found")
    return pat.sub(new.rstrip() + "\n\n", text, count=1)


def _ok(text: str) -> bool:
    pb = text.split("def serve_lipton_dev_playback_page", 1)[-1][:900]
    if "_serve_regatta_standalone_impl" in pb or "LIPTON_PUBLIC_NOT_DEV" in pb:
        return False
    if "lipton-dev.html" not in pb:
        return False
    after = text.split("def serve_regatta_standalone", 1)[-1][:900]
    if "LIPTON_PUBLIC_NOT_DEV" in after:
        return False
    if 'slug_s == "2026-08-29-lipton-challenge-cup-old"' not in after:
        return False
    if 'slug_s == "2026-08-29-lipton-challenge-cup":' not in after:
        return False
    if "public=True" not in after:
        return False
    # First public-slug branch must be playback, not impl.
    pub = after.split('slug_s == "2026-08-29-lipton-challenge-cup":', 1)[-1][:180]
    if "public=True" not in pub:
        return False
    if "_serve_regatta_standalone_impl" in pub:
        return False
    return True


def main() -> int:
    text = API.read_text(encoding="utf-8")
    text = _replace_fn(text, "serve_lipton_dev_playback_page", PLAYBACK_FN)
    if "def _serve_regatta_standalone_impl" in text:
        text = re.sub(
            r"def serve_regatta_standalone\([\s\S]*?\n\n(?=def _serve_regatta_standalone_impl)",
            EARLY,
            text,
            count=1,
        )
    else:
        text = re.sub(
            r"def serve_regatta_standalone\([\s\S]*?\n(?=    start_time = )",
            EARLY.replace(
                "    return _serve_regatta_standalone_impl(slug, request)\n\n",
                "",
            ),
            text,
            count=1,
        )
    if not _ok(text):
        print("ERROR: API still hijacked", flush=True)
        after = text.split("def serve_regatta_standalone", 1)[-1][:800]
        print(after)
        return 1
    API.write_text(text, encoding="utf-8")
    print("API public=playback old=-old")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
