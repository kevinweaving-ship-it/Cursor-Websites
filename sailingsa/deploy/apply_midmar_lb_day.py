#!/usr/bin/env python3
"""Install Midmar Leader Board 'after N Races on Day N' title and cache-bust mmlb13."""
from pathlib import Path

SRC = Path("/tmp/midmar-leaderboard.js")
DEST = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
MM = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")
VER = "mmlb13"


def main() -> None:
    src = SRC.read_text()
    if "on Day " not in src or "function eventDay" not in src:
        raise SystemExit("SRC_BAD")
    DEST.write_text(src)
    DEST.chmod(0o644)
    print("JS_OK", DEST.stat().st_size)

    olds = ("mmlb6", "mmlb7", "mmlb8", "mmlb9", "mmlb10", "mmlb11", "mmlb12")
    mm = MM.read_text()
    mm2 = mm
    for old in olds:
        mm2 = mm2.replace("midmar-leaderboard.js?v=" + old, "midmar-leaderboard.js?v=" + VER)
    if mm2 != mm:
        MM.write_text(mm2)
        print("MM_VER", VER)
    else:
        print("MM_VER_ALREADY", VER in mm)

    api = API.read_text()
    api2 = api
    for old in olds:
        api2 = api2.replace("midmar-leaderboard.js?v=" + old, "midmar-leaderboard.js?v=" + VER)
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY", VER in api)


if __name__ == "__main__":
    main()
