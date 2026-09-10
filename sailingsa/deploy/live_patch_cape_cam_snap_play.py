#!/usr/bin/env python3
"""Cape Classic cam: bump reels JS mmr117. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")
old = "mm-lipton-reels-card.js?v=mmr116"
new = "mm-lipton-reels-card.js?v=mmr117"
if new in src:
    print("JS_ALREADY_MMR117")
elif old not in src:
    raise SystemExit("ANCHOR_MM_MISSING")
else:
    src = src.replace(old, new, 1)
    print("JS_BUMPED_MMR117")
API.write_text(src, encoding="utf-8")
print("mmr117", new in src)
