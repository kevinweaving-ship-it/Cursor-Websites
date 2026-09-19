#!/usr/bin/env python3
"""Restore Midmar media thumbs to normal 16:9. Rotate must not squash the card."""
from pathlib import Path
import shutil
import time

MARK = "MIDMAR_MEDIA_UNSQUASH_v1"
SRC = Path("/tmp/midmar-media-rotate.js")
DEST = Path("/var/www/sailingsa/js/midmar-media-rotate.js")
MEDIA = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")

ROW_OLD = (
    '      ".regatta-page > .midmar-live-media .midmar-mm-row{order:1;display:flex;flex-wrap:wrap;align-items:flex-start;gap:10px;margin-top:10px;width:100%;}",'
)
ROW_NEW = (
    '      ".regatta-page > .midmar-live-media .midmar-mm-row{order:1;display:flex;flex-direction:column;flex-wrap:nowrap;align-items:stretch;gap:10px;margin-top:10px;width:100%;}",\n'
    '      ".regatta-page > .midmar-live-media .midmar-mm-row > .mm-lipton-reels{flex:1 1 auto;width:100%!important;max-width:100%!important;}",\n'
    '      ".regatta-page > .midmar-live-media .midmar-mm-row > .midmar-mm-sa{flex:0 0 auto;width:100%;max-width:100%;}",\n'
    '      ".midmar-live-media .mm-lipton-reels-grid .mm-lipton-reels-thumb,.midmar-live-media .mm-lipton-reels-days .mm-lipton-reels-thumb{aspect-ratio:16/9!important;height:auto!important;}",'
)


def main() -> None:
    src = SRC.read_text()
    if "aspect-ratio:16/9!important" not in src or "revertBox" not in src:
        raise SystemExit("MISSING_OR_BAD_SRC")
    DEST.write_text(src)
    DEST.chmod(0o644)
    print("ROT_JS_OK", DEST.stat().st_size)

    media = MEDIA.read_text()
    if MARK in media and "midmarwx46" in media:
        print("MEDIA_ALREADY")
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = MEDIA.with_name(f"midmar-live-media.js.bak.unsquash.{ts}")
        shutil.copy2(MEDIA, bak)
        print("BACKUP", bak)
        if ROW_OLD in media:
            media = media.replace(ROW_OLD, ROW_NEW, 1)
            print("ROW_CSS_OK")
        elif "aspect-ratio:16/9!important;height:auto!important" in media:
            print("ROW_CSS_ALREADY")
        else:
            raise SystemExit("ROW_CSS_MISSING")
        media = media.replace('JS_VER = "midmarwx45"', 'JS_VER = "midmarwx46"', 1)
        media = media.replace(
            'loadScript("/js/midmar-media-rotate.js?v=mmrot3");',
            'loadScript("/js/midmar-media-rotate.js?v=mmrot4");',
            1,
        )
        if MARK not in media:
            media = media.replace("  var JS_VER = ", "  // " + MARK + "\n  var JS_VER = ", 1)
        MEDIA.write_text(media)
        print("MEDIA_OK")

    api = API.read_text()
    api2 = api.replace("midmar-live-media.js?v=midmarwx45", "midmar-live-media.js?v=midmarwx46")
    api2 = api2.replace("midmar-media-rotate.js?v=mmrot3", "midmar-media-rotate.js?v=mmrot4")
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY")


if __name__ == "__main__":
    main()
