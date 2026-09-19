#!/usr/bin/env python3
"""Install Midmar R2 leaderboard JS (all ranks + nett pt) and cache-bust."""
from pathlib import Path

SRC = Path("/tmp/midmar-leaderboard.js")
DEST = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
MM = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    src = SRC.read_text()
    if "midmar-lb-nett" not in src or "n <= 3" not in src:
        raise SystemExit("SRC_BAD")
    DEST.write_text(src)
    DEST.chmod(0o644)
    print("JS_OK", DEST.stat().st_size)

    mm = MM.read_text()
    mm2 = mm.replace("midmar-leaderboard.js?v=mmlb6", "midmar-leaderboard.js?v=mmlb9")
    mm2 = mm2.replace("midmar-leaderboard.js?v=mmlb7", "midmar-leaderboard.js?v=mmlb9")
    mm2 = mm2.replace("midmar-leaderboard.js?v=mmlb8", "midmar-leaderboard.js?v=mmlb9")
    if mm2 != mm:
        MM.write_text(mm2)
        print("MM_VER mmlb9")
    else:
        print("MM_VER_ALREADY", "mmlb9" in mm)

    api = API.read_text()
    api2 = api.replace("midmar-leaderboard.js?v=mmlb6", "midmar-leaderboard.js?v=mmlb9")
    api2 = api2.replace("midmar-leaderboard.js?v=mmlb7", "midmar-leaderboard.js?v=mmlb9")
    api2 = api2.replace("midmar-leaderboard.js?v=mmlb8", "midmar-leaderboard.js?v=mmlb9")
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY", "mmlb7" in api)


if __name__ == "__main__":
    main()
