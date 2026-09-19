#!/usr/bin/env python3
"""Remove the Midmar results-sheet media thumb that the filter missed."""
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
REMOVE_IDS = {"mmclip-820c9a7cfdfb"}


def main() -> None:
    path = mm.clips_json_path(RID, STATIC)
    if not path.is_file():
        raise SystemExit("MISSING_CLIPS_JSON")
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"clips.json.bak.rmr3res.{ts}")
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
        raise SystemExit("REFUSE expected 1 results thumb, got " + str(len(removed)))
    row = removed[0]
    if str(row.get("kind") or "") != "photo":
        raise SystemExit("REFUSE not a photo: " + str(row.get("kind")))
    print("HIT", row.get("id"), row.get("title"), row.get("started_at"), row.get("width"), row.get("height"))

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
