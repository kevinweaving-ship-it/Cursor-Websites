#!/usr/bin/env python3
"""Hide camera OSD datetime; keep HMYC SNAPSHOT as at HH:MM on Midmar + club."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
JS_DEST = Path("/var/www/sailingsa/js/midmar-live-media.js")
JS_SRC = Path("/tmp/midmar-live-media.js")
CLUB_JS = Path("/var/www/sailingsa/js/club-live-media.js")
MARK = "HMYC_CAM_OSD_HIDE_v1"

CLUB_OLD = (
    ".club-hyc-cam .cam-cap,.club-live-cam .cam-cap{position:absolute;left:8px;top:8px;"
    "z-index:2;color:#fff;font:700 12px Arial,Helvetica,sans-serif;text-shadow:0 1px 2px #000}';"
)
CLUB_NEW = (
    ".club-hyc-cam .cam-cap,.club-live-cam .cam-cap{position:absolute;left:8px;top:8px;"
    "z-index:2;color:#fff;font:700 12px Arial,Helvetica,sans-serif;text-shadow:0 1px 2px #000}"
    "/* HMYC_CAM_OSD_HIDE_v1: crop camera burned-in date/time; keep SNAPSHOT as at. */"
    ".mm-lipton-reels[data-mm-snapshot] .mm-lipton-reels-thumb{overflow:hidden}"
    ".mm-lipton-reels[data-mm-snapshot] img[data-mm-webcam-live]{"
    "width:100%;height:118%;margin-top:-10%;object-fit:cover;object-position:center bottom}';"
)


def main() -> None:
    if not JS_SRC.is_file():
        raise SystemExit("MISSING_JS")
    js = JS_SRC.read_text()
    if "data-mm-cam-stamp-label" not in js or "margin-top:-10%" not in js:
        raise SystemExit("JS_BAD")
    JS_DEST.write_text(js)
    JS_DEST.chmod(0o644)
    print("JS_OK", JS_DEST.stat().st_size)

    api = API.read_text()
    if "midmar-live-media.js?v=midmarwx1" in api:
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = API.with_name(f"api.py.bak.midmar_cam_stamp.{ts}")
        shutil.copy2(API, bak)
        print("BACKUP_API", bak)
        api = api.replace("midmar-live-media.js?v=midmarwx1", "midmar-live-media.js?v=midmarwx2")
        API.write_text(api)
        print("API_VER midmarwx2")
    else:
        print("API_VER", "midmarwx2" if "midmarwx2" in api else "unchanged")

    club = CLUB_JS.read_text()
    if MARK in club:
        print("CLUB_ALREADY", MARK)
        return
    if CLUB_OLD not in club:
        raise SystemExit("CLUB_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = CLUB_JS.with_name(f"club-live-media.js.bak.osd_hide.{ts}")
    shutil.copy2(CLUB_JS, bak)
    print("BACKUP_CLUB", bak)
    club = club.replace(CLUB_OLD, CLUB_NEW, 1)
    club = club.replace("var JS_VER = 'clubwx18';", "var JS_VER = 'clubwx19';")
    CLUB_JS.write_text(club)
    print("CLUB_OK", MARK)

    if "club-live-media.js?v=clubwx18" in api:
        API.write_text(API.read_text().replace("club-live-media.js?v=clubwx18", "club-live-media.js?v=clubwx19"))
        print("API_CLUB_VER clubwx19")


if __name__ == "__main__":
    main()
