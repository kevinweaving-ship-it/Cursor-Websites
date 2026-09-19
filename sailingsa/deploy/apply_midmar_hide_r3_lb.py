#!/usr/bin/env python3
"""Remove the Midmar Leader Board / After 3 Races media thumb."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/var/www/sailingsa")
from sailingsa.backend import mm_event_clips as mm

SAST = ZoneInfo("Africa/Johannesburg")
RID = "2026-09-19-hmyc-midmar-cup"
STATIC = Path("/var/www/sailingsa")
REMOVE_IDS = {"mmclip-f9f28a72cb75"}


def main() -> None:
    path = mm.clips_json_path(RID, STATIC)
    if not path.is_file():
        raise SystemExit("MISSING_CLIPS_JSON")
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"clips.json.bak.rmr3lb.{ts}")
    shutil.copy2(path, bak)
    print("BACKUP", bak)

    data = mm.load_or_seed(RID, STATIC)
    videos = list(data.get("videos") or [])
    keep = []
    removed = []
    for v in videos:
        cid = str(v.get("id") or "")
        if cid in REMOVE_IDS:
            removed.append(v)
            continue
        keep.append(v)
    if len(removed) != 1:
        raise SystemExit("REFUSE expected 1 leader thumb, got " + str(len(removed)))
    title = str(removed[0].get("title") or "")
    if "after 3 races" not in title.casefold() and "leader" not in title.casefold():
        raise SystemExit("REFUSE unexpected title: " + title)

    mm.save_clips(RID, STATIC, keep)
    folder = mm.clips_dir(RID, STATIC)
    for v in removed:
        print("REMOVED", v.get("id"), v.get("title"), v.get("started_at"), v.get("play_url"))
        for key in ("play_url", "thumb"):
            name = Path(str(v.get(key) or "")).name
            if not name or not name.startswith("mmclip-"):
                continue
            f = folder / name
            if f.is_file():
                f.unlink()
                print("DEL_FILE", f)

    payload = mm.public_payload(RID, STATIC)
    pub = payload.get("videos") or []
    ids = {str(v.get("id")) for v in pub}
    if REMOVE_IDS & ids:
        raise SystemExit("STILL_PRESENT " + str(REMOVE_IDS & ids))
    print("PUBLIC_N", len(pub), "JSON_N", len(keep))
    print("NEXT", [(v.get("id"), v.get("title"), v.get("started_at")) for v in pub[:4]])


if __name__ == "__main__":
    main()
