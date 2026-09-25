#!/usr/bin/env python3
import re
import shutil
from pathlib import Path

SRC = Path("/tmp/hmyc-cam-js/club-score-edit.js")
JS = Path("/var/www/sailingsa/js/club-score-edit.js")
FRONT = Path("/var/www/sailingsa/frontend/js/club-score-edit.js")
API = Path("/var/www/sailingsa/api/api.py")
VER = "ccr37"


def main() -> None:
    if not SRC.exists():
        raise SystemExit("MISSING_JS")
    shutil.copy2(SRC, JS)
    print("JS", JS, JS.stat().st_size)
    if FRONT.parent.is_dir():
        shutil.copy2(SRC, FRONT)
        print("JS", FRONT, FRONT.stat().st_size)
    t = JS.read_text()
    print("OCF_JS", '"OCF"' in t and "OCS|OCF" in t)
    api = API.read_text()
    api2, n1 = re.subn(
        r"club-score-edit\.js\?v=ccr[A-Za-z0-9_-]+",
        f"club-score-edit.js?v={VER}",
        api,
    )
    api2, n2 = re.subn(
        r"\(DNC\|DNS\|DNF\|RET\|DSQ\|UFD\|BFD\|DPI\|OCS\)",
        r"(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS|OCF)",
        api2,
    )
    if '"OCF"' not in api2 and '"On Course Side"' in api2:
        api2 = api2.replace(
            '{"code": "OCS", "description": "On Course Side"},',
            '{"code": "OCS", "description": "On Course Side"},\n'
            '        {"code": "OCF", "description": "On Course Finish"},',
            1,
        )
    print("API ccr", n1, "penalty", n2, "ocf_list", '"OCF"' in api2)
    if api2 != api:
        API.write_text(api2)
    print("DONE")


if __name__ == "__main__":
    main()
