#!/usr/bin/env python3
"""Pass STATIC_DIR into OG cache renderer for brand favicon lookup."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX5_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = """    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos)"""
NEW = """    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos, static_dir=STATIC_DIR)"""

OLD2 = """    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos)
    fp = _fb.og_cache_fingerprint(path, page_type, _pos)"""
NEW2 = """    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos, static_dir=STATIC_DIR)
    fp = _fb.og_cache_fingerprint(path, page_type, _pos)"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix5")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix5_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")
    if OLD2 not in text:
        raise SystemExit("_fb_og_prepare cache call not found")
    if OLD not in text:
        raise SystemExit("api_facebook_og_image cache call not found")
    text = text.replace(OLD2, NEW2, 1)
    text = text.replace(OLD, NEW, 1)
    text = text.replace("# FB_OG_FIX4_v1", "# FB_OG_FIX4_v1\n" + MARKER, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix5", API_PATH)


if __name__ == "__main__":
    main()
