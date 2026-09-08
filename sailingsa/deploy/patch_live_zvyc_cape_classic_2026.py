#!/usr/bin/env python3
"""All /regatta/{slug} results: default header.html site-header. Event header unchanged."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
EXACT_START = '@app.get("/regatta/2026-09-13-zvyc-cape-classic")'
GENERIC = '@app.get("/regatta/{slug}")'
OLD_RETURN = "    return serve_regatta_standalone(slug, request)\n"
NEW_RETURN = """    resp = serve_regatta_standalone(slug, request)
    if isinstance(resp, HTMLResponse):
        from zvyc_cape_classic_2026 import add_default_site_header
        raw = resp.body
        html = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
        return HTMLResponse(add_default_site_header(html), status_code=getattr(resp, "status_code", 200))
    return resp
"""


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    start = text.find(EXACT_START)
    end = text.find(GENERIC)
    if start >= 0 and end > start:
        text = text[:start] + text[end:]
        print("removed exact-slug route")
    if "add_default_site_header" in text and "def _regatta_standalone" in text:
        # already wrapping generic route
        if OLD_RETURN not in text.split("def _regatta_standalone", 1)[-1][:800]:
            LIVE_API.write_text(text, encoding="utf-8")
            print("generic wrap already present")
            return
    if OLD_RETURN not in text:
        raise SystemExit("standalone return not found")
    text = text.replace(OLD_RETURN, NEW_RETURN, 1)
    LIVE_API.write_text(text, encoding="utf-8")
    print("patched generic /regatta/{slug} with default site-header")


if __name__ == "__main__":
    main()
