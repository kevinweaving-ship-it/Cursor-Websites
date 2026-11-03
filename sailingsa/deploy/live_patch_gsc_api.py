#!/usr/bin/env python3
"""Surgical Search Console fixes on a live api.py (do not replace the whole file).

- Empty /regatta/class/podium/podium.html?regatta_id= → 301 /events
- /sailors <title> uses “South African Sailors” so GSC no longer sees a thin “Sailors” title
"""
from __future__ import annotations

import pathlib
import re
import sys

PODIUM_FN = re.compile(
    r"@app\.get\(\"/regatta/class/podium/podium\.html\"\)\n"
    r"def _regatta_podium_html\(([^)]*)\):\n"
    r"(?:    [^\n]*\n)*?"
    r"    path = os\.path\.join\(_static_dir\(\), \"regatta\", \"class\", \"podium\", \"podium\.html\"\)\n"
)

PODIUM_GUARD = '''@app.get("/regatta/class/podium/podium.html")
def _regatta_podium_html(request: Request):
    if not (request.query_params.get("regatta_id") or "").strip():
        return RedirectResponse(url="/events", status_code=301)
'''


def patch_podium(text: str) -> str:
    if 'query_params.get("regatta_id")' in text and "/regatta/class/podium/podium.html" in text:
        return text
    match = PODIUM_FN.search(text)
    if not match:
        raise SystemExit("podium route not found")
    start = match.start()
    # Keep the existing body from `path = ...`
    body_at = text.find("    path = os.path.join(_static_dir(), \"regatta\", \"class\", \"podium\", \"podium.html\")", start)
    if body_at < 0:
        raise SystemExit("podium body not found")
    return text[:start] + PODIUM_GUARD + text[body_at:]


def patch_sailors_title(text: str) -> str:
    text = text.replace(
        '_directory_page_html("/sailors", items, "sailor", "Sailors")',
        '_directory_page_html("/sailors", items, "sailor", "South African Sailors")',
    )
    text = text.replace("<title>Sailors</title>", "<title>South African Sailors | SailingSA</title>")
    if 'name="robots"' not in text and "<title>" in text and "_directory_page_html" in text:
        text = text.replace(
            "</title>\n<link rel=\"canonical\"",
            "</title>\n<meta name=\"robots\" content=\"index, follow\">\n<link rel=\"canonical\"",
            1,
        )
    return text


def patch(text: str) -> str:
    return patch_sailors_title(patch_podium(text))


def main() -> None:
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
    before = path.read_text(encoding="utf-8")
    after = patch(before)
    if after == before:
        print("NOCHANGE")
        return
    path.write_text(after, encoding="utf-8")
    print("PATCHED", path)


if __name__ == "__main__":
    main()
