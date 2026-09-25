#!/usr/bin/env python3
"""Deploy HMYC snapshot hide-unless-valid + unwire ZVYC fallback."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js")
FRONT_JS = Path("/var/www/sailingsa/frontend/js")
SRC = Path("/tmp/hmyc-cam-js")
CLUB_VER = "clubwx22"
MM_VER = "midmarwx58"


def copy_js() -> None:
    for name in ("club-live-media.js", "midmar-live-media.js", "mm-lipton-reels-card.js"):
        src = SRC / name
        if not src.exists():
            raise SystemExit(f"MISSING_{name}")
        dest = JS / name
        shutil.copy2(src, dest)
        print("JS", dest, dest.stat().st_size)
        alt = FRONT_JS / name
        if alt.parent.is_dir():
            shutil.copy2(src, alt)
            print("JS", alt, alt.stat().st_size)


def bump_api() -> None:
    text = API.read_text()
    before = text
    text, n1 = re.subn(
        r"club-live-media\.js\?v=[A-Za-z0-9_-]+",
        f"club-live-media.js?v={CLUB_VER}",
        text,
    )
    text, n2 = re.subn(
        r"mm-lipton-reels\.css\?v=clubwx[A-Za-z0-9_-]+",
        f"mm-lipton-reels.css?v={CLUB_VER}",
        text,
    )
    text, n3 = re.subn(
        r"midmar-live-media\.js\?v=midmarwx[A-Za-z0-9_-]+",
        f"midmar-live-media.js?v={MM_VER}",
        text,
    )
    print("API club-live-media", n1, "reels-css", n2, "midmar-live-media", n3)
    if text == before:
        print("API_NO_CHANGE")
    else:
        API.write_text(text)
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("API_COMPILE_OK")
    print("API_clubwx22", text.count(CLUB_VER), "API_midmarwx58", text.count(MM_VER))
    print("API_clubwx19", text.count("clubwx19"), "API_clubwx21", text.count("clubwx21"))


def main() -> None:
    copy_js()
    bump_api()
    print("DONE")


if __name__ == "__main__":
    main()
