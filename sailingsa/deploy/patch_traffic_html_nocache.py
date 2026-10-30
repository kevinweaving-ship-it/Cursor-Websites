#!/usr/bin/env python3
"""Ensure lean traffic HTML is never cached so junk-filter JS ships."""
from pathlib import Path
import py_compile
import shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-traffic-nocache-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # Find lean_traffic_dashboard_page return HTMLResponse
    i = text.find("def lean_traffic_dashboard_page")
    if i < 0:
        raise SystemExit("dashboard page missing")
    chunk = text[i : i + 2500]
    if "no-store" in chunk and "isJunkTrafficPath" in text:
        # still ensure HTMLResponse headers
        pass

    old = None
    for cand in (
        "return HTMLResponse(_LEAN_TRAFFIC_PAGE_HTML)",
        "return HTMLResponse(content=_LEAN_TRAFFIC_PAGE_HTML)",
        'return HTMLResponse(_LEAN_TRAFFIC_PAGE_HTML, headers={"Cache-Control": "no-store"})',
    ):
        if cand in text:
            old = cand
            break
    if old is None:
        # search pattern
        j = text.find("return HTMLResponse", i)
        print("nearby", repr(text[j : j + 120]))
        raise SystemExit("HTMLResponse return not found")

    new = 'return HTMLResponse(_LEAN_TRAFFIC_PAGE_HTML, headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"})'
    if "no-store, no-cache" not in text[i : i + 3000]:
        text = text.replace(old, new, 1)

    if text == orig:
        print("OK already nocache or no change needed; isJunk=", "isJunkTrafficPath" in text)
        return
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK traffic html no-cache")


if __name__ == "__main__":
    main()
