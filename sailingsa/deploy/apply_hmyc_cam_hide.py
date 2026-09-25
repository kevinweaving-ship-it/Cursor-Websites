#!/usr/bin/env python3
"""Deploy HMYC snapshot hide-unless-valid + unwire ZVYC fallback."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js")
SRC = Path("/tmp/hmyc-cam-js")


def copy_js() -> None:
    for name in ("club-live-media.js", "midmar-live-media.js", "mm-lipton-reels-card.js"):
        src = SRC / name
        if not src.exists():
            raise SystemExit(f"MISSING_{name}")
        dest = JS / name
        shutil.copy2(src, dest)
        print("JS", dest, dest.stat().st_size)


def bump_api() -> None:
    text = API.read_text()
    reps = (
        ("club-live-media.js?v=clubwx19", "club-live-media.js?v=clubwx21"),
        ("club-live-media.js?v=clubwx20", "club-live-media.js?v=clubwx21"),
        ("mm-lipton-reels.css?v=clubwx18", "mm-lipton-reels.css?v=clubwx21"),
        ("midmar-live-media.js?v=midmarwx55dart2", "midmar-live-media.js?v=midmarwx57"),
        ("midmar-live-media.js?v=midmarwx55dart28", "midmar-live-media.js?v=midmarwx57"),
        ("midmar-live-media.js?v=midmarwx56", "midmar-live-media.js?v=midmarwx57"),
    )
    for old, new in reps:
        c = text.count(old)
        if c:
            text = text.replace(old, new)
            print("API", old, "->", new, "n", c)
    API.write_text(text)
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("API_COMPILE_OK")


def main() -> None:
    copy_js()
    bump_api()
    print("DONE")


if __name__ == "__main__":
    main()
