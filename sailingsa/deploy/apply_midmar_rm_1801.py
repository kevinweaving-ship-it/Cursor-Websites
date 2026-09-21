#!/usr/bin/env python3
"""Remove Midmar last media image: Sun 20 Sep 18:01 Day 2 (mmclip-8f28e2300042)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/var/www/sailingsa")
from sailingsa.backend import mm_event_clips as mm

SAST = ZoneInfo("Africa/Johannesburg")
RID = "2026-09-19-hmyc-midmar-cup"
STATIC = Path("/var/www/sailingsa")
REMOVE_ID = "mmclip-8f28e2300042"
MARK = "MIDMAR_DROP_1801_v1"
MM = Path("/var/www/sailingsa/sailingsa/backend/mm_event_clips.py")
INGEST = Path("/opt/arial-whatsapp-poc/event_whatsapp_ingest.py")

SET_OLD = '    if cid in {"mmclip-b300a5c1a735", "mmclip-f1e7c1b6d111"}:\n        return True\n'
SET_NEW = (
    '    if cid in {"mmclip-b300a5c1a735", "mmclip-f1e7c1b6d111", "mmclip-8f28e2300042"}:\n'
    "        return True  # " + MARK + "\n"
    "    try:\n"
    "        from datetime import datetime as _dt\n"
    "        from zoneinfo import ZoneInfo as _ZI\n"
    '        _raw = str((clip or {}).get("started_at") or "")\n'
    "        if _raw:\n"
    '            _dtm = _dt.fromisoformat(_raw.replace("Z", "+00:00"))\n'
    "            if _dtm.tzinfo is None:\n"
    '                _dtm = _dtm.replace(tzinfo=_ZI("Africa/Johannesburg"))\n'
    '            if _dtm > _dt(2026, 9, 20, 18, 0, tzinfo=_ZI("Africa/Johannesburg")):\n'
    "                return True\n"
    "    except Exception:\n"
    "        pass\n"
)


def patch_filter() -> None:
    text = MM.read_text()
    if MARK in text and REMOVE_ID in text:
        print("FILTER_ALREADY")
        return
    n = text.count(SET_OLD)
    if n != 1:
        raise SystemExit("ANCHOR_SET_" + str(n))
    MM.write_text(text.replace(SET_OLD, SET_NEW, 1))
    print("FILTER_OK")


def patch_ingest() -> None:
    if not INGEST.is_file():
        print("INGEST_MISSING")
        return
    text = INGEST.read_text()
    if MARK in text:
        print("INGEST_ALREADY")
        return
    old = "    if _dt.now(_ZI(\"Africa/Johannesburg\")) > _cutoff:\n        return\n"
    new = "    if _dt.now(_ZI(\"Africa/Johannesburg\")) >= _cutoff:  # " + MARK + "\n        return\n"
    n = text.count(old)
    if n != 1:
        print("INGEST_SKIP", n)
        return
    INGEST.write_text(text.replace(old, new, 1))
    print("INGEST_OK")


def remove_clip() -> None:
    path = mm.clips_json_path(RID, STATIC)
    if not path.is_file():
        raise SystemExit("MISSING_CLIPS_JSON")
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"clips.json.bak.rm1801.{ts}")
    shutil.copy2(path, bak)
    print("BACKUP", bak)

    data = mm.load_or_seed(RID, STATIC)
    videos = list(data.get("videos") or [])
    keep = []
    removed = []
    for v in videos:
        if str(v.get("id") or "") == REMOVE_ID:
            removed.append(v)
            continue
        keep.append(v)
    if len(removed) != 1:
        raise SystemExit("REFUSE expected 1 clip, got " + str(len(removed)))
    row = removed[0]
    if str(row.get("kind") or "") != "photo":
        raise SystemExit("REFUSE not a photo: " + str(row.get("kind")))
    stamp = str(row.get("stamp") or row.get("fb_sub") or "")
    started = str(row.get("started_at") or "")
    if "18:01" not in stamp and "18:01" not in started:
        raise SystemExit("REFUSE stamp mismatch " + stamp + " " + started)
    print("HIT", row.get("id"), row.get("title"), started, stamp, row.get("width"), row.get("height"))

    mm.save_clips(RID, STATIC, keep)
    folder = mm.clips_dir(RID, STATIC)
    for v in removed:
        for key in ("play_url", "thumb"):
            name = Path(str(v.get(key) or "")).name
            if not name or not name.startswith("mmclip-"):
                continue
            f = folder / name
            if f.is_file():
                f.unlink()
                print("DEL_FILE", f)

    import importlib
    importlib.reload(mm)
    payload = mm.public_payload(RID, STATIC)
    pub = payload.get("videos") or []
    ids = {str(v.get("id")) for v in pub}
    if REMOVE_ID in ids:
        raise SystemExit("STILL_PRESENT")
    for v in pub:
        at = str(v.get("started_at") or "")
        if at.startswith("2026-09-20T18:01") or "18:01 Day 2" in str(v.get("stamp") or ""):
            raise SystemExit("STILL_1801 " + str(v.get("id")))
    print("PUBLIC_N", len(pub), "JSON_N", len(keep))
    print("NEXT", [(v.get("id"), v.get("title"), v.get("started_at"), v.get("stamp")) for v in pub[:3]])


def main() -> None:
    patch_filter()
    subprocess.check_call(["python3", "-m", "py_compile", str(MM)])
    print("MM_COMPILE_OK")
    patch_ingest()
    if INGEST.is_file() and MARK in INGEST.read_text():
        subprocess.check_call(["python3", "-m", "py_compile", str(INGEST)])
        print("INGEST_COMPILE_OK")
        subprocess.check_call(["systemctl", "restart", "arial-whatsapp-poc"])
        time.sleep(2)
        print("WA", subprocess.check_output(["systemctl", "is-active", "arial-whatsapp-poc"], text=True).strip())
    remove_clip()
    subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
    time.sleep(5)
    print("API_SVC", subprocess.check_output(["systemctl", "is-active", "sailingsa-api"], text=True).strip())
    print("DONE", MARK)


if __name__ == "__main__":
    main()
