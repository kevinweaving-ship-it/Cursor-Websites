#!/usr/bin/env python3
"""OG fix12: inject Facebook meta immediately after <head> (crawler-visible)."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER = "# FB_OG_FIX12_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
OG_MODULE_SRC = Path(__file__).resolve().parent / "facebook_og.py"
OG_MODULE_DST = Path("/var/www/sailingsa/api/facebook_og.py")


def main() -> None:
    if OG_MODULE_SRC.is_file() and OG_MODULE_SRC.resolve() != OG_MODULE_DST.resolve():
        shutil.copy2(OG_MODULE_SRC, OG_MODULE_DST)
        print(f"Updated {OG_MODULE_DST}")
    else:
        # Already copied to same path via scp
        print(f"OG module at {OG_MODULE_DST}")

    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix12 marker")
    else:
        insert_at = "# FB_OG_FIX11_v1\n"
        if insert_at not in text:
            raise SystemExit("FB_OG_FIX11 marker not found")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        bak = API_PATH.with_suffix(f".py.bak_fb_og_fix12_{ts}")
        shutil.copy2(API_PATH, bak)
        print(f"Backup: {bak}")
        text = text.replace(insert_at, insert_at + MARKER + "\n", 1)
        API_PATH.write_text(text, encoding="utf-8")
        print("OK patched fix12 marker", API_PATH)


if __name__ == "__main__":
    main()
