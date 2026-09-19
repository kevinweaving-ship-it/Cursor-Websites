#!/usr/bin/env python3
"""Remove WhatsApp scores / Leader Board screenshots from Midmar media."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

sys.path.insert(0, "/var/www/sailingsa")
from sailingsa.backend import mm_event_clips as mm

SAST = ZoneInfo("Africa/Johannesburg")
RID = "2026-09-19-hmyc-midmar-cup"
STATIC = Path("/var/www/sailingsa")
REMOVE_IDS = {"mmclip-8aebb864b588", "mmclip-323818dd6a1e"}


def main() -> None:
    path = mm.clips_json_path(RID, STATIC)
    if not path.is_file():
        raise SystemExit("MISSING_CLIPS_JSON")
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"clips.json.bak.rmscore.{ts}")
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
    if len(removed) != 2:
        raise SystemExit("REFUSE expected 2 score images, got " + str(len(removed)))
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
    ids = {str(v.get("id")) for v in payload.get("videos") or []}
    if REMOVE_IDS & ids:
        raise SystemExit("STILL_PRESENT " + str(REMOVE_IDS & ids))
    print("PUBLIC_N", len(payload.get("videos") or []), "JSON_N", len(keep))


if __name__ == "__main__":
    main()
