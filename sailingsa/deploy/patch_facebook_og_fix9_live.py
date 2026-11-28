#!/usr/bin/env python3
"""OG fix9: left brand = logo-wordmark-on-white (never favicon/mark-on-color)."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX9_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
OG_MODULE_SRC = Path(__file__).resolve().parent / "facebook_og.py"
OG_MODULE_DST = Path("/var/www/sailingsa/api/facebook_og.py")

BRAND_URL = "/assets/logos/Live/logo-wordmark-on-white.png"
REPLACEMENTS = (
    ('_FB_OG_BRAND_URL = "/assets/logos/sailingsa-logo-on-white.png"', f'_FB_OG_BRAND_URL = "{BRAND_URL}"'),
    ('_FB_OG_BRAND_URL = "/assets/logos/sailingsa-logo.png"', f'_FB_OG_BRAND_URL = "{BRAND_URL}"'),
)


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
        print("OK already patched fix9")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix9_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    insert_at = "# FB_OG_FIX8_v1\n"
    if insert_at not in text:
        raise SystemExit("FB_OG_FIX8 marker not found")
    text = text.replace(insert_at, insert_at + MARKER + "\n", 1)

    replaced = False
    for old, new in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new, 1)
            replaced = True
            break
    if not replaced and BRAND_URL not in text:
        raise SystemExit("_FB_OG_BRAND_URL anchor not found")

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix9", API_PATH)


if __name__ == "__main__":
    main()
