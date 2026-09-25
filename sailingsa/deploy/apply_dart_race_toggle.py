#!/usr/bin/env python3
import re
import shutil
from pathlib import Path

SRC = Path("/tmp/hmyc-cam-js/club-score-edit.js")
JS = Path("/var/www/sailingsa/js/club-score-edit.js")
FRONT = Path("/var/www/sailingsa/frontend/js/club-score-edit.js")
API = Path("/var/www/sailingsa/api/api.py")
VER = "ccr36"


def main() -> None:
    if not SRC.exists():
        raise SystemExit("MISSING_JS")
    shutil.copy2(SRC, JS)
    print("JS", JS, JS.stat().st_size)
    if FRONT.parent.is_dir():
        shutil.copy2(SRC, FRONT)
        print("JS", FRONT, FRONT.stat().st_size)
    t = JS.read_text()
    print(
        "TOGGLE",
        "syncRaceHide" in t,
        "ensureOpenRaces" in t,
        "adminEditOn" in t,
    )
    if API.exists():
        api = API.read_text()
        api2, n = re.subn(
            r"club-score-edit\.js\?v=ccr[A-Za-z0-9_-]+",
            f"club-score-edit.js?v={VER}",
            api,
        )
        print("API club-score-edit", n)
        if api2 != api:
            API.write_text(api2)
    print("DONE")


if __name__ == "__main__":
    main()
