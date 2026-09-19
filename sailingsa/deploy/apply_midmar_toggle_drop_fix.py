#!/usr/bin/env python3
"""Fix Midmar Public toggle + drop overlay caused by rotate/drop patch."""
from pathlib import Path
import shutil
import time

MARK = "MIDMAR_TOGGLE_DROP_FIX_v1"
SRC = Path("/tmp/midmar-media-rotate.js")
DEST = Path("/var/www/sailingsa/js/midmar-media-rotate.js")
MEDIA = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")

CSS_OLD = (
    '      ".midmar-mm-sa{display:none!important;flex:1 1 100%;width:100%;max-width:100%;padding:8px;box-sizing:border-box;border:2px solid #001f3f;border-radius:8px;background:#dce6ef;}",\n'
    '      ".regatta-page--super-admin-edit .midmar-live-media--sa .midmar-mm-sa{display:block!important;}",'
)
CSS_NEW = (
    '      ".midmar-mm-sa,.midmar-mm-sa[hidden],.regatta-page:not(.regatta-page--super-admin-edit) .midmar-mm-sa{display:none!important;pointer-events:none!important;}",\n'
    '      ".regatta-page--super-admin-edit .midmar-live-media--sa .midmar-mm-sa:not([hidden]){display:block!important;pointer-events:auto;}",\n'
    '      ".regatta-page .regatta-sa-mode-wrap{position:relative;z-index:80;pointer-events:auto;}",'
)

DROP_OLD = (
    '      ".midmar-mm-sa-drop{position:relative;border:2px dashed #001f3f;border-radius:8px;min-height:72px;background:#f8fafc;overflow:hidden;}",\n'
    '      ".midmar-mm-sa-drop.is-on{background:#e8eef5;}",\n'
    '      ".midmar-mm-sa-file{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;z-index:2;}",'
)
DROP_NEW = (
    '      ".midmar-mm-sa-drop{position:relative;isolation:isolate;contain:layout;border:2px dashed #001f3f;border-radius:8px;min-height:72px;background:#f8fafc;overflow:hidden;}",\n'
    '      ".midmar-mm-sa-drop.is-on{background:#e8eef5;}",\n'
    '      ".midmar-mm-sa-file{position:absolute;left:0;top:0;width:100%;height:100%;max-width:100%;max-height:100%;opacity:0;cursor:pointer;z-index:2;}",\n'
    '      ".midmar-mm-sa-drop.has-file .midmar-mm-sa-file{pointer-events:none;}",'
)


def main() -> None:
    if not SRC.is_file() or "rotBox" not in SRC.read_text():
        raise SystemExit("MISSING_OR_BAD_SRC")
    DEST.write_text(SRC.read_text())
    DEST.chmod(0o644)
    print("JS_OK", DEST.stat().st_size)

    ts = time.strftime("%Y%m%d_%H%M%S")
    media = MEDIA.read_text()
    if MARK in media and "midmarwx43" in media and "has-file" in media:
        print("MEDIA_ALREADY")
    else:
        bak = MEDIA.with_name(f"midmar-live-media.js.bak.togdrop.{ts}")
        shutil.copy2(MEDIA, bak)
        print("BACKUP_MEDIA", bak)
        if CSS_OLD not in media:
            raise SystemExit("CSS_ANCHOR_MISSING")
        if DROP_OLD not in media:
            raise SystemExit("DROP_ANCHOR_MISSING")
        media = media.replace(CSS_OLD, CSS_NEW, 1)
        media = media.replace(DROP_OLD, DROP_NEW, 1)
        media = media.replace('JS_VER = "midmarwx42"', 'JS_VER = "midmarwx43"', 1)
        media = media.replace(
            'loadScript("/js/midmar-media-rotate.js?v=mmrot1");',
            'loadScript("/js/midmar-media-rotate.js?v=mmrot2");',
            1,
        )
        if 'drop.classList.add("has-file")' not in media:
            old_show = "      pending = { file: f, width: 0, height: 0, rotation: 0 };\n      if (!preview) return;"
            new_show = (
                "      pending = { file: f, width: 0, height: 0, rotation: 0 };\n"
                '      if (drop) drop.classList.add("has-file");\n'
                "      if (!preview) return;"
            )
            if old_show not in media:
                raise SystemExit("SHOWFILE_ANCHOR_MISSING")
            media = media.replace(old_show, new_show, 1)
        if 'drop.classList.remove("has-file")' not in media:
            old_clr = (
                "          pending = { file: null, width: 0, height: 0 };\n"
                '          if (drop) drop.removeAttribute("data-mm-sa-orient");'
            )
            new_clr = (
                "          pending = { file: null, width: 0, height: 0, rotation: 0 };\n"
                '          if (drop) drop.classList.remove("has-file");\n'
                '          if (drop) drop.removeAttribute("data-mm-sa-orient");'
            )
            if old_clr not in media:
                raise SystemExit("CLEAR_ANCHOR_MISSING")
            media = media.replace(old_clr, new_clr, 1)
        if MARK not in media:
            media = media.replace("  var JS_VER = ", "  // " + MARK + "\n  var JS_VER = ", 1)
        MEDIA.write_text(media)
        print("MEDIA_OK", MEDIA.stat().st_size)

    api = API.read_text()
    api2 = api.replace("midmar-live-media.js?v=midmarwx42", "midmar-live-media.js?v=midmarwx43")
    api2 = api2.replace("midmar-media-rotate.js?v=mmrot1", "midmar-media-rotate.js?v=mmrot2")
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY", "wx43" in api, "mmrot2" in api)


if __name__ == "__main__":
    main()
