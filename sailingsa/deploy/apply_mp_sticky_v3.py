#!/usr/bin/env python3
"""Replace MP sticky v2 (helm wrap / 100% squash) with v3 on live api.py."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
SNIP = Path("/tmp/mp_sticky_v3_insert.txt")


def main() -> None:
    live = API.read_text()
    v3 = SNIP.read_text()
    if not v3.startswith('    "/* MP_STICKY_SCORE_SHEET_v3 */"'):
        raise SystemExit("V3_SNIP_BAD")
    if "MP_STICKY_SCORE_SHEET_v3" in live and "mp-race-under" in live:
        print("ALREADY_V3")
        return
    start = live.find('    "/* MP_STICKY_SCORE_SHEET_v2 */"')
    if start < 0:
        start = live.find('    "/* MP_STICKY_SCORE_SHEET_v1 */"')
    if start < 0:
        start = live.find("/* MP_STICKY_SCORE_SHEET_v2 */")
    if start < 0:
        start = live.find("/* MP_STICKY_SCORE_SHEET_v1 */")
    if start < 0:
        raise SystemExit("LIVE_MARKER_MISSING")
    end = live.find('    "@media (max-width:768px) and (max-aspect-ratio:1/1){"', start)
    if end < 0:
        raise SystemExit("LIVE_END_MISSING")
    live = live[:start] + v3 + live[end:]
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.mp_sticky_v3.{ts}")
    shutil.copy2(API, bak)
    print("BAK", bak)
    API.write_text(live)
    print("MP_STICKY_V3_OK")


if __name__ == "__main__":
    main()
