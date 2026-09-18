#!/usr/bin/env python3
"""Midmar Event URL: HMYC weather + expanded club cam between header and fleet."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
JS_DEST = Path("/var/www/sailingsa/js/midmar-live-media.js")
JS_SRC = Path("/tmp/midmar-live-media.js")
MARK = "MIDMAR_HMYC_WX_CAM_v1"

OLD = """        elif str(regatta_id) == "2026-09-13-zvyc-cape-classic":
            mm_card = _cape_classic_mm_reels_card_html(str(regatta_id))
            mm_card_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr142" defer></script><script src="/js/club-score-edit.js?v=ccr21" defer></script><script src="/js/regatta-slot-card.js?v=20260912wa10" defer></script>'
        banner_top = _wc_regatta_source_banner_html(str(regatta_id), position="top")
"""

NEW = """        elif str(regatta_id) == "2026-09-13-zvyc-cape-classic":
            mm_card = _cape_classic_mm_reels_card_html(str(regatta_id))
            mm_card_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr142" defer></script><script src="/js/club-score-edit.js?v=ccr21" defer></script><script src="/js/regatta-slot-card.js?v=20260912wa10" defer></script>'
        elif str(regatta_id) == "2026-09-19-hmyc-midmar-cup":
            # MIDMAR_HMYC_WX_CAM_v1: same HMYC weather + full-width cam between header and fleet.
            mm_card = ""
            mm_card_script = '<script src="/js/midmar-live-media.js?v=midmarwx1" defer></script>'
        banner_top = _wc_regatta_source_banner_html(str(regatta_id), position="top")
"""


def main() -> None:
    if not JS_SRC.is_file():
        raise SystemExit("MISSING_JS " + str(JS_SRC))
    js_text = JS_SRC.read_text()
    if "agromet-midmar" not in js_text or "hmyccam1.nwsza.net" not in js_text:
        raise SystemExit("JS_BAD")
    JS_DEST.write_text(js_text)
    JS_DEST.chmod(0o644)
    print("JS_OK", JS_DEST, JS_DEST.stat().st_size)

    api = API.read_text()
    if MARK in api and NEW in api:
        print("API_ALREADY", MARK)
        return
    if OLD not in api:
        raise SystemExit("API_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.midmar_wx_cam.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    API.write_text(api.replace(OLD, NEW, 1))
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
