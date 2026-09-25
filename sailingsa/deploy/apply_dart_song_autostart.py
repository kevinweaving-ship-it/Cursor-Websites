#!/usr/bin/env python3
import re
import shutil
import subprocess
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
SRC = Path("/tmp/hmyc-cam-js/midmar-live-media.js")
JS = Path("/var/www/sailingsa/js/midmar-live-media.js")
FRONT = Path("/var/www/sailingsa/frontend/js/midmar-live-media.js")
VER = "midmarwx60"


def main() -> None:
    if not SRC.exists():
        raise SystemExit("MISSING_JS")
    shutil.copy2(SRC, JS)
    if FRONT.parent.is_dir():
        shutil.copy2(SRC, FRONT)
    print("JS", JS.stat().st_size)
    t = JS.read_text()
    print("AUTO", "dart-nats-theme-audio" in t, "nudge" in t, VER in t)
    text = API.read_text()
    text2, n = re.subn(
        r"midmar-live-media\.js\?v=midmarwx[A-Za-z0-9_-]+",
        f"midmar-live-media.js?v={VER}",
        text,
    )
    print("API", n)
    if text2 != text:
        API.write_text(text2)
        subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("DONE")


if __name__ == "__main__":
    main()
