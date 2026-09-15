#!/usr/bin/env python3
"""Replace squashed MP sticky v1 with content-fit v2 on live api.py."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
SNIP = Path("/tmp/mp_sticky_v2_insert.txt")


def main() -> None:
    live = API.read_text()
    v2 = SNIP.read_text()
    if not v2.startswith('    "/* MP_STICKY_SCORE_SHEET_v2 */"'):
        raise SystemExit("V2_SNIP_BAD")
    if "MP_STICKY_SCORE_SHEET_v2" in live and "text-overflow:ellipsis" not in live.split("MP_STICKY_SCORE_SHEET_v2", 1)[1][:2500]:
        print("ALREADY_V2")
        return
    start = live.find('    "/* MP_STICKY_SCORE_SHEET_v1 */"')
    if start < 0:
        start = live.find('    "/* MP_STICKY_SCORE_SHEET_v2 */"')
    if start < 0:
        raise SystemExit("LIVE_MARKER_MISSING")
    end = live.find('    "@media (max-width:768px) and (max-aspect-ratio:1/1){"', start)
    if end < 0:
        raise SystemExit("LIVE_END_MISSING")
    live = live[:start] + v2 + live[end:]
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.mp_sticky_v2.{ts}")
    shutil.copy2(API, bak)
    print("BAK", bak)
    API.write_text(live)
    print("MP_STICKY_V2_OK")


if __name__ == "__main__":
    main()
