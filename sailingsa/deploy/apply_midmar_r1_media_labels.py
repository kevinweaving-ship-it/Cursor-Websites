#!/usr/bin/env python3
"""Mark Midmar media through 12:29 SAST as Race 1 in race labels.

Trophy + Friday training stay as-is. 12:32 and later stay unlabeled.
"""
from __future__ import annotations

import json
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
CUTOFF = datetime(2026, 9, 19, 12, 29, 59, tzinfo=SAST)
DAY = CUTOFF.date()
SKIP_IDS = {"midmar-cup-1", "midmar-train-1"}


def main() -> None:
    path = mm.clips_json_path(RID, STATIC)
    if not path.is_file():
        raise SystemExit("MISSING_CLIPS_JSON")
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"clips.json.bak.r1labels.{ts}")
    shutil.copy2(path, bak)
    print("BACKUP", bak)

    data = mm.load_or_seed(RID, STATIC)
    videos = list(data.get("videos") or [])
    marked = 0
    skipped = 0
    later = 0
    for v in videos:
        cid = str(v.get("id") or "")
        dt = mm.parse_started_at(str(v.get("started_at") or ""))
        if cid in SKIP_IDS or v.get("pinned"):
            skipped += 1
            print("SKIP", cid, v.get("title"), v.get("started_at"))
            continue
        if dt.date() != DAY or dt > CUTOFF:
            later += 1
            print("LATER", cid, dt.isoformat(), v.get("title"))
            continue
        v["race"] = 1
        v["race_label"] = "Race 1"
        marked += 1
        print("R1", cid, dt.strftime("%H:%M"), v.get("title") or v.get("kind"))

    mm.save_clips(RID, STATIC, videos)
    payload = mm.public_payload(RID, STATIC)
    r1 = 0
    other = 0
    for v in payload.get("videos") or []:
        if int(v.get("race") or 0) == 1 or str(v.get("race_label") or "") == "Race 1":
            r1 += 1
        else:
            other += 1
            print("PUBLIC_OTHER", v.get("id"), v.get("started_at"), v.get("title"))
    print("MARKED", marked, "SKIPPED", skipped, "LATER", later, "PUBLIC_R1", r1, "PUBLIC_OTHER", other)
    print("JSON", path, path.stat().st_size)


if __name__ == "__main__":
    main()
