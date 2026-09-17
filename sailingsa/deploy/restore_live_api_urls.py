#!/usr/bin/env python3
"""Put the real live api.py back. Do not use the workspace stub."""
from pathlib import Path
import shutil

LIVE = Path("/var/www/sailingsa/api/api.py")
SRC = Path("/var/www/sailingsa/api/api.py.bak.club_sailor_mp.20260916_140347")
MARK = "RESTORE_LIVE_API_URLS_v1"

if not SRC.is_file():
    raise SystemExit("ERROR: 3.8MB live backup missing: " + str(SRC))
if SRC.stat().st_size < 3000000:
    raise SystemExit("ERROR: backup too small: %s" % SRC.stat().st_size)

src = SRC.read_text(encoding="utf-8", errors="replace")
if "def events_logos_page" not in src:
    raise SystemExit("ERROR: backup missing events_logos_page")
cur = LIVE.read_text(encoding="utf-8", errors="replace") if LIVE.is_file() else ""
if LIVE.is_file() and LIVE.stat().st_size > 3000000 and "def events_logos_page" in cur:
    print("ALREADY_LARGE_LIVE", LIVE.stat().st_size)
else:
    bak = LIVE.with_name("api.py.bak.pre_restore_urls")
    if LIVE.is_file():
        shutil.copy2(LIVE, bak)
    shutil.copy2(SRC, LIVE)
    print("RESTORED_FROM", SRC, "bytes", LIVE.stat().st_size, "pre", bak)
