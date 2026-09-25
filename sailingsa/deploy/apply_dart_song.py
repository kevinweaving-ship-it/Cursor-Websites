#!/usr/bin/env python3
"""Deploy Dart theme song toggle + smaller/faster mp3."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/midmar-live-media.js")
FRONT = Path("/var/www/sailingsa/frontend/js/midmar-live-media.js")
SRC = Path("/tmp/hmyc-cam-js/midmar-live-media.js")
ORIG = Path("/var/www/sailingsa/assets/dart-nats-theme.mp3")
FAST = Path("/var/www/sailingsa/assets/dart-nats-theme-fast.mp3")
VER = "midmarwx59"


def copy_js() -> None:
    if not SRC.exists():
        raise SystemExit("MISSING_JS")
    shutil.copy2(SRC, JS)
    print("JS", JS, JS.stat().st_size)
    if FRONT.parent.is_dir():
        shutil.copy2(SRC, FRONT)
        print("JS", FRONT, FRONT.stat().st_size)


def compress() -> None:
    if FAST.exists() and FAST.stat().st_size > 10000:
        print("FAST_OK", FAST.stat().st_size)
        return
    if not ORIG.exists():
        raise SystemExit("MISSING_MP3")
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(ORIG),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "80k",
            "-ac",
            "2",
            str(FAST),
        ]
    )
    FAST.chmod(0o644)
    print("FAST", FAST.stat().st_size)


def bump_api() -> None:
    text = API.read_text()
    before = text
    text, n = re.subn(
        r"midmar-live-media\.js\?v=midmarwx[A-Za-z0-9_-]+",
        f"midmar-live-media.js?v={VER}",
        text,
    )
    print("API midmar-live-media", n)
    if text != before:
        API.write_text(text)
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("API_COMPILE_OK", text.count(VER))


def main() -> None:
    copy_js()
    compress()
    bump_api()
    print("DONE")


if __name__ == "__main__":
    main()
