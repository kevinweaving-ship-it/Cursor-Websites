#!/usr/bin/env python3
"""Install Midmar Leader Board card (header → board → weather) and cache-bust JS."""
from pathlib import Path
import shutil
import time

SRC = Path("/tmp/midmar-leaderboard.js")
DEST = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
MM = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_LEADERBOARD_v1"

BOOT_OLD = """    loadScript("/js/regatta-slot-card.js?v=" + JS_VER).then(function () {
"""

BOOT_NEW = """    // MIDMAR_LEADERBOARD_v1: compact 1st/2nd/3rd between header and weather.
    loadScript("/js/midmar-leaderboard.js?v=mmlb3");
    loadScript("/js/regatta-slot-card.js?v=" + JS_VER).then(function () {
"""

TAG_OLD = (
    "mm_card_script = '<script src=\"/js/midmar-live-media.js?v=midmarwx40\" defer></script>'"
)
TAG_NEW = (
    "mm_card_script = '<script src=\"/js/midmar-live-media.js?v=midmarwx41\" defer></script>"
    "<script src=\"/js/midmar-leaderboard.js?v=mmlb3\" defer></script>'"
)


def main() -> None:
    if not SRC.is_file():
        raise SystemExit("MISSING_SRC")
    src = SRC.read_text()
    if "midmar-leaderboard" not in src or "Leader Board" not in src:
        raise SystemExit("SRC_BAD")
    DEST.write_text(src)
    DEST.chmod(0o644)
    print("JS_OK", DEST, DEST.stat().st_size)

    mm = MM.read_text()
    for old_ver in ("mmlb1", "mmlb2"):
        needle = "midmar-leaderboard.js?v=" + old_ver
        if needle in mm:
            mm = mm.replace(needle, "midmar-leaderboard.js?v=mmlb3")
            MM.write_text(mm)
            print("MM_VER mmlb3")
            break
    mm = MM.read_text()
    if MARK in mm:
        print("MM_ALREADY", MARK)
    else:
        if BOOT_OLD not in mm:
            raise SystemExit("BOOT_ANCHOR_MISSING")
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = MM.with_name(f"midmar-live-media.js.bak.lb.{ts}")
        shutil.copy2(MM, bak)
        print("BACKUP_MM", bak)
        mm = mm.replace(BOOT_OLD, BOOT_NEW, 1)
        if "midmarwx40" in mm:
            mm = mm.replace("midmarwx40", "midmarwx41")
        MM.write_text(mm)
        print("MM_OK", MARK)

    if not API.is_file():
        return
    import re

    api = API.read_text()
    api2 = api.replace("midmar-leaderboard.js?v=mmlb1", "midmar-leaderboard.js?v=mmlb3")
    api2 = api2.replace("midmar-leaderboard.js?v=mmlb2", "midmar-leaderboard.js?v=mmlb3")

    def _pin(m: re.Match) -> str:
        tag = m.group(0)
        rest = api2[m.end() : m.end() + 90]
        if "midmar-leaderboard.js" in rest:
            return tag
        return tag + '<script src="/js/midmar-leaderboard.js?v=mmlb3" defer></script>'

    api2 = re.sub(
        r'<script src="/js/midmar-live-media\.js\?v=midmarwx\d+" defer></script>',
        _pin,
        api2,
    )
    if api2 != api:
        try:
            API.write_text(api2)
            print("API_OK scripts", api2.count("midmar-leaderboard.js"))
        except OSError as e:
            print("API_SKIP", e)
    else:
        print("API_UNCHANGED", "lb" if "midmar-leaderboard.js" in api else "NO_LB")


if __name__ == "__main__":
    main()
