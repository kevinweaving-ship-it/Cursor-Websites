#!/usr/bin/env python3
"""This URL only: default .site-header on top of unchanged serve_regatta_standalone."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
NEEDLE = '@app.get("/regatta/{slug}")'
INSERT = '''@app.get("/regatta/2026-09-13-zvyc-cape-classic")
@app.head("/regatta/2026-09-13-zvyc-cape-classic")
def _zvyc_cape_classic_2026_pending(request: Request):
    """Default site-header only. Event header from serve_regatta_standalone — do not change."""
    from zvyc_cape_classic_2026 import SLUG, add_default_site_header
    resp = serve_regatta_standalone(SLUG, request)
    raw = resp.body
    html = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
    return HTMLResponse(add_default_site_header(html))


'''


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    start = text.find('@app.get("/regatta/2026-09-13-zvyc-cape-classic")')
    end = text.find(NEEDLE)
    if start >= 0 and end > start:
        text = text[:start] + INSERT + text[end:]
        LIVE_API.write_text(text, encoding="utf-8")
        print("replaced route")
        return
    if NEEDLE not in text:
        raise SystemExit("needle not found")
    LIVE_API.write_text(text.replace(NEEDLE, INSERT + NEEDLE, 1), encoding="utf-8")
    print("patched")


if __name__ == "__main__":
    main()
