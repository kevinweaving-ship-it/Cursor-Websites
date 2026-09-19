#!/usr/bin/env python3
"""Remove latest Midmar results + Leader Board media thumbs and keep them filtered."""
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
REMOVE_IDS = {"mmclip-b300a5c1a735", "mmclip-f1e7c1b6d111"}
MARK = "MIDMAR_DROP_SCORE_MEDIA_v3"

FILTER_FN = '''
def _midmar_is_score_or_leader_shot(clip: dict) -> bool:
    """Drop results-sheet / Leader Board screenshots from Midmar media. MIDMAR_DROP_SCORE_MEDIA_v3"""
    cid = str((clip or {}).get("id") or "")
    if cid in {"mmclip-b300a5c1a735", "mmclip-f1e7c1b6d111"}:
        return True
    title = " ".join(
        str((clip or {}).get(k) or "") for k in ("title", "caption", "alt", "text")
    ).casefold()
    if any(
        k in title
        for k in (
            "leader board",
            "leaderboard",
            "results are provisional",
            "results are final",
            "youth helm races",
            "full results sheet",
        )
    ):
        return True
    try:
        w = int((clip or {}).get("width") or 0)
        h = int((clip or {}).get("height") or 0)
    except Exception:
        w = h = 0
    if w >= 500 and h and h <= 200:
        return True
    if w and h and (w / float(h)) >= 4.0:
        return True
    return False


'''

PAYLOAD_OLD = '''    videos = with_midmar_trophy(rid, videos)
    videos = dedupe_by_filehash(videos)
    return {"ok": True, "videos": sort_videos(videos)}
'''
PAYLOAD_NEW = '''    videos = with_midmar_trophy(rid, videos)
    videos = dedupe_by_filehash(videos)
    if rid == "2026-09-19-hmyc-midmar-cup":
        videos = [v for v in videos if not _midmar_is_score_or_leader_shot(v)]
    return {"ok": True, "videos": sort_videos(videos)}
'''


def _patch_filter() -> None:
    path = Path("/var/www/sailingsa/sailingsa/backend/mm_event_clips.py")
    text = path.read_text()
    if MARK in text:
        print("FILTER_ALREADY")
        return
    if PAYLOAD_OLD not in text:
        raise SystemExit("ANCHOR_PAYLOAD")
    if "def _midmar_is_score_or_leader_shot" not in text:
        text = text.replace("def public_payload(", FILTER_FN + "def public_payload(", 1)
    text = text.replace(PAYLOAD_OLD, PAYLOAD_NEW, 1)
    path.write_text(text)
    print("FILTER_OK")


def main() -> None:
    _patch_filter()
    path = mm.clips_json_path(RID, STATIC)
    if not path.is_file():
        raise SystemExit("MISSING_CLIPS_JSON")
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"clips.json.bak.rmscore3.{ts}")
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
    print("REMOVED_N", len(removed))
    mm.save_clips(RID, STATIC, keep)
    folder = mm.clips_dir(RID, STATIC)
    for v in removed:
        print("REMOVED", v.get("id"), v.get("title"), v.get("started_at"), v.get("width"), v.get("height"))
        for key in ("play_url", "thumb"):
            name = Path(str(v.get(key) or "")).name
            if not name or not name.startswith("mmclip-"):
                continue
            f = folder / name
            if f.is_file():
                f.unlink()
                print("DEL_FILE", f)

    # reload module filter
    import importlib
    importlib.reload(mm)
    payload = mm.public_payload(RID, STATIC)
    pub = payload.get("videos") or []
    ids = {str(v.get("id")) for v in pub}
    if REMOVE_IDS & ids:
        raise SystemExit("STILL_PRESENT " + str(REMOVE_IDS & ids))
    print("PUBLIC_N", len(pub), "JSON_N", len(keep))
    print("NEXT", [(v.get("id"), v.get("title"), v.get("started_at"), v.get("width"), v.get("height")) for v in pub[:4]])


if __name__ == "__main__":
    main()
