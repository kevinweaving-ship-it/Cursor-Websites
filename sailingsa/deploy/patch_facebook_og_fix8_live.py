#!/usr/bin/env python3
"""OG fix8: visible brand on white, HEAD on PNG route, secure_url + twitter tags."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX8_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
OG_MODULE_SRC = Path(__file__).resolve().parent / "facebook_og.py"
OG_MODULE_DST = Path("/var/www/sailingsa/api/facebook_og.py")

BRAND_OLD = '_FB_OG_BRAND_URL = "/assets/logos/sailingsa-logo-on-white.png"'
BRAND_NEW = '_FB_OG_BRAND_URL = "/assets/logos/sailingsa-logo.png"'

ROUTE_OLD = """@app.get("/api/og/{page_type}/{entity_key}.png")
def api_facebook_og_image(page_type: str, entity_key: str, v: Optional[str] = None):"""

ROUTE_NEW = """@app.api_route("/api/og/{page_type}/{entity_key}.png", methods=["GET", "HEAD"])
def api_facebook_og_image(page_type: str, entity_key: str, v: Optional[str] = None):"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    if OG_MODULE_SRC.is_file() and OG_MODULE_SRC.resolve() != OG_MODULE_DST.resolve():
        shutil.copy2(OG_MODULE_SRC, OG_MODULE_DST)
        print(f"Updated {OG_MODULE_DST}")
    elif OG_MODULE_DST.is_file():
        print(f"OG module already at {OG_MODULE_DST}")

    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix8")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix8_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    insert_at = "# FB_OG_FIX7_v1\n"
    if insert_at not in text:
        raise SystemExit("FB_OG_FIX7 marker not found")
    text = text.replace(insert_at, insert_at + MARKER + "\n", 1)

    if BRAND_OLD not in text:
        if BRAND_NEW in text:
            print("Brand URL already updated")
        else:
            raise SystemExit("brand URL anchor not found")
    else:
        text = text.replace(BRAND_OLD, BRAND_NEW, 1)

    if ROUTE_OLD not in text:
        if ROUTE_NEW.split("\n")[0] in text:
            print("OG route already supports HEAD")
        else:
            raise SystemExit("OG route anchor not found")
    else:
        text = text.replace(ROUTE_OLD, ROUTE_NEW, 1)

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix8", API_PATH)


if __name__ == "__main__":
    main()
