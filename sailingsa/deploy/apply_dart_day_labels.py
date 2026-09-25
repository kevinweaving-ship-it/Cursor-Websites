#!/usr/bin/env python3
import shutil
from pathlib import Path

SRC = Path("/tmp/hmyc-cam-js")
JS = Path("/var/www/sailingsa/js")
FRONT = Path("/var/www/sailingsa/frontend/js")


def copy(name: str) -> None:
    src = SRC / name
    if not src.exists():
        raise SystemExit("MISSING_" + name)
    dest = JS / name
    shutil.copy2(src, dest)
    print("JS", dest, dest.stat().st_size)
    alt = FRONT / name
    if alt.parent.is_dir():
        shutil.copy2(src, alt)
        print("JS", alt, alt.stat().st_size)


def main() -> None:
    copy("mm-lipton-reels-card.js")
    copy("midmar-live-media.js")
    t = (JS / "mm-lipton-reels-card.js").read_text()
    print("DAY_LABEL", " - Day " in t and "dartDayNumberFromKey" in t)
    print("DART25", "hmycdart25" in (JS / "midmar-live-media.js").read_text())
    print("DONE")


if __name__ == "__main__":
    main()
