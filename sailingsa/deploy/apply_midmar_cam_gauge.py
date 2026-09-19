#!/usr/bin/env python3
"""Pin Midmar Hide + wind gauge on the snapshot; gauge 1.5x."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
JS_DEST = Path("/var/www/sailingsa/js/midmar-live-media.js")
JS_SRC = Path("/tmp/midmar-live-media.js")
MARK = "midmarwx10"


def main() -> None:
    if not JS_SRC.is_file():
        raise SystemExit("MISSING_JS")
    js = JS_SRC.read_text()
    if 'var JS_VER = "midmarwx10"' not in js or "cam-photo" not in js:
        raise SystemExit("JS_BAD")
    if JS_DEST.is_file():
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = JS_DEST.with_name("midmar-live-media.js.bak.gauge." + ts)
        shutil.copy2(JS_DEST, bak)
        print("BACKUP_JS", bak)
    JS_DEST.write_text(js)
    JS_DEST.chmod(0o644)
    print("JS_OK", JS_DEST.stat().st_size)

    api = API.read_text()
    if MARK in api:
        print("API_ALREADY", MARK)
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.midmar_cam_gauge." + ts)
    shutil.copy2(API, bak)
    print("BACKUP_API", bak)
    updated = api
    for old in (
        "midmar-live-media.js?v=midmarwx9",
        "midmar-live-media.js?v=midmarwx8",
        "midmar-live-media.js?v=midmarwx7",
        "midmar-live-media.js?v=midmarwx6",
        "midmar-live-media.js?v=midmarwx5",
        "midmar-live-media.js?v=midmarwx4",
        "midmar-live-media.js?v=midmarwx3",
        "midmar-live-media.js?v=midmarwx2",
        "midmar-live-media.js?v=midmarwx1",
    ):
        if old in updated:
            updated = updated.replace(old, "midmar-live-media.js?v=midmarwx10")
            print("API_VER", old, "->", MARK)
            break
    if updated == api:
        raise SystemExit("API_VER_MISSING")
    API.write_text(updated)
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
