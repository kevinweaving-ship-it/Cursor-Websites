#!/usr/bin/env python3
"""Fix Add clip pointer-events so Super Admin can drag-drop videos."""
from pathlib import Path
import time
import shutil

MARK = "MIDMAR_DROP_PE_v1"
MEDIA = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")
SRC = Path("/tmp/midmar-media-rotate.js")
DEST = Path("/var/www/sailingsa/js/midmar-media-rotate.js")

HIDE_OLD = (
    '      ".midmar-mm-sa,.midmar-mm-sa[hidden],.regatta-page:not(.regatta-page--super-admin-edit) .midmar-mm-sa{display:none!important;pointer-events:none!important;}",\n'
    '      ".regatta-page--super-admin-edit .midmar-live-media--sa .midmar-mm-sa:not([hidden]){display:block!important;pointer-events:auto;}",'
)
HIDE_NEW = (
    '      ".midmar-mm-sa[hidden],.regatta-page:not(.regatta-page--super-admin-edit) .midmar-mm-sa{display:none!important;pointer-events:none!important;}",\n'
    '      ".regatta-page--super-admin-edit .midmar-live-media--sa .midmar-mm-sa:not([hidden]){display:block!important;pointer-events:auto!important;}",'
)
CONTAIN_OLD = (
    '      ".midmar-mm-sa-drop{position:relative;isolation:isolate;contain:layout;border:2px dashed #001f3f;border-radius:8px;min-height:72px;background:#f8fafc;overflow:hidden;}",'
)
CONTAIN_NEW = (
    '      ".midmar-mm-sa-drop{position:relative;border:2px dashed #001f3f;border-radius:8px;min-height:72px;background:#f8fafc;overflow:hidden;cursor:pointer;}",'
)


def main() -> None:
    if SRC.is_file() and "revertBox" in SRC.read_text():
        DEST.write_text(SRC.read_text())
        DEST.chmod(0o644)
        print("ROT_JS_OK")
    media = MEDIA.read_text()
    if MARK in media and "pointer-events:auto!important" in media and "contain:layout" not in media:
        print("MEDIA_ALREADY")
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = MEDIA.with_name(f"midmar-live-media.js.bak.droppe.{ts}")
        shutil.copy2(MEDIA, bak)
        print("BACKUP", bak)
        if HIDE_OLD not in media:
            raise SystemExit("HIDE_MISSING")
        media = media.replace(HIDE_OLD, HIDE_NEW, 1)
        if CONTAIN_OLD in media:
            media = media.replace(CONTAIN_OLD, CONTAIN_NEW, 1)
            print("CONTAIN_GONE")
        media = media.replace('JS_VER = "midmarwx44"', 'JS_VER = "midmarwx45"', 1)
        media = media.replace(
            'loadScript("/js/midmar-media-rotate.js?v=mmrot3");',
            'loadScript("/js/midmar-media-rotate.js?v=mmrot3");',
            1,
        )
        if MARK not in media:
            media = media.replace("  var JS_VER = ", "  // " + MARK + "\n  var JS_VER = ", 1)
        MEDIA.write_text(media)
        print("MEDIA_OK")
    api = API.read_text()
    api2 = api.replace("midmar-live-media.js?v=midmarwx44", "midmar-live-media.js?v=midmarwx45")
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY")


if __name__ == "__main__":
    main()
