#!/usr/bin/env python3
import shutil
from pathlib import Path

SRC = Path("/tmp/hmyc-cam-js/club-score-edit.js")
JS = Path("/var/www/sailingsa/js/club-score-edit.js")
FRONT = Path("/var/www/sailingsa/frontend/js/club-score-edit.js")
API = Path("/var/www/sailingsa/api/api.py")
VER = "ccr38"


def main() -> None:
    if not SRC.exists():
        raise SystemExit("MISSING_JS")
    shutil.copy2(SRC, JS)
    print("JS", JS.stat().st_size)
    if FRONT.parent.is_dir():
        shutil.copy2(SRC, FRONT)
        print("FRONT", FRONT.stat().st_size)
    js = JS.read_text()
    print("TLE_JS", '"TLE"' in js and '"DNE", "TLE"' in js)

    api = API.read_text()
    before = api
    k = api.find("_RACE_PENALTY_CODES =")
    print("ASSIGN", k)
    if k < 0:
        raise SystemExit("NO_CODES")
    block = api[k : k + 800]
    print("BEFORE_BLOCK", block.split("\n", 1)[0])
    if '"TLE"' not in block:
        if '"DNE"' in block:
            block = block.replace('"DNE"', '"DNE", "TLE"', 1)
        elif '"OCF"' in block:
            block = block.replace('"OCF"', '"OCF", "TLE"', 1)
        else:
            raise SystemExit("NO_INSERT")
        api = api[:k] + block + api[k + 800 :]
    if f"club-score-edit.js?v={VER}" not in api:
        api = api.replace("club-score-edit.js?v=ccr37", f"club-score-edit.js?v={VER}")
        api = api.replace("club-score-edit.js?v=ccr36", f"club-score-edit.js?v={VER}")
    if '{"code": "TLE"' not in api and '{"code": "OCF"' in api:
        api = api.replace(
            '{"code": "OCF", "description": "On Course Finish"},',
            '{"code": "OCF", "description": "On Course Finish"},\n'
            '        {"code": "TLE", "description": "Time Limit Expired"},',
            1,
        )
    if api != before:
        API.write_text(api)
    t2 = API.read_text()
    k2 = t2.find("_RACE_PENALTY_CODES =")
    print("CHANGED", t2 != before)
    print("AFTER_BLOCK", t2[k2 : k2 + 180].split("\n", 1)[0] if k2 >= 0 else "MISSING")
    print("VER", VER, t2.count(f"club-score-edit.js?v={VER}"))
    print("DONE")


if __name__ == "__main__":
    main()
