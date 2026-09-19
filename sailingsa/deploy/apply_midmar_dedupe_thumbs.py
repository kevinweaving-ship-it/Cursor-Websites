#!/usr/bin/env python3
"""Dedupe Midmar media by file hash, retarget 14:59 thumb, retry 14:52."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

sys.path.insert(0, "/var/www/sailingsa")
from sailingsa.backend import mm_event_clips as mm

SAST = ZoneInfo("Africa/Johannesburg")
RID = "2026-09-19-hmyc-midmar-cup"
STATIC = Path("/var/www/sailingsa")
MM = Path("/var/www/sailingsa/sailingsa/backend/mm_event_clips.py")
FOLDER = mm.clips_dir(RID, STATIC)
THUMB_ID = "mmclip-f8345f37ff27"


def backup() -> None:
    ts = datetime.now(SAST).strftime("%Y%m%d_%H%M%S")
    bak = FOLDER / f"clips.json.bak.dedupe.{ts}"
    shutil.copy2(FOLDER / "clips.json", bak)
    mm_bak = MM.with_name(f"mm_event_clips.py.bak.dedupe.{ts}")
    shutil.copy2(MM, mm_bak)
    print("BACKUP", bak, mm_bak)


def patch_public_dedupe() -> None:
    t = MM.read_text()
    if "def dedupe_by_filehash" in t:
        print("DEDUPE_FN already")
        return
    needle = "def public_payload(rid: str, static_dir: Path) -> dict:"
    if needle not in t:
        raise SystemExit("REFUSE no public_payload")
    helper = '''
def dedupe_by_filehash(videos: list) -> list:
    seen = set()
    out = []
    for v in videos or []:
        hid = str((v or {}).get("file_sha256") or "")
        if hid:
            if hid in seen:
                continue
            seen.add(hid)
        out.append(v)
    return out


'''
    t = t.replace(needle, helper + needle, 1)
    old = """    videos = with_midmar_trophy(rid, videos)
    return {"ok": True, "videos": sort_videos(videos)}
"""
    new = """    videos = with_midmar_trophy(rid, videos)
    videos = dedupe_by_filehash(videos)
    return {"ok": True, "videos": sort_videos(videos)}
"""
    if old not in t:
        raise SystemExit("REFUSE public_payload return needle")
    MM.write_text(t.replace(old, new, 1))
    subprocess.check_call(["python3", "-m", "py_compile", str(MM)])
    print("MM hash-dedupe public_payload")


def retarget_thumb() -> None:
    src = FOLDER / f"{THUMB_ID}.mp4"
    dest = FOLDER / f"{THUMB_ID}.jpg"
    if not src.is_file():
        print("NO 14:59 video")
        return
    tmp = Path("/tmp/f834-thumb90.jpg")
    subprocess.check_call(
        ["ffmpeg", "-y", "-ss", "90", "-i", str(src), "-frames:v", "1", "-q:v", "3", str(tmp)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if tmp.is_file() and tmp.stat().st_size > 800:
        shutil.copy2(tmp, dest)
        print("THUMB 14:59 now 90s frame", dest.stat().st_size)
    else:
        print("THUMB fail")


def drop_orphan_dupes() -> None:
    data = json.loads((FOLDER / "clips.json").read_text())
    keep_ids = {str(v.get("id")) for v in (data.get("videos") or [])}
    removed = 0
    for p in FOLDER.glob("mmclip-*"):
        if p.suffix.lower() not in {".mp4", ".jpg"}:
            continue
        cid = p.stem
        if cid in keep_ids:
            continue
        # only delete orphans that match a kept file hash / known dupe leftovers
        if cid in {"mmclip-0bc6e4de6a13", "mmclip-225f9bb647a6", "mmclip-94caffa43cc4"}:
            p.unlink()
            print("DEL_ORPHAN", p.name)
            removed += 1
    print("ORPHAN_DEL", removed)


def fetch_1452() -> None:
    env = {}
    for line in Path("/etc/arial-whatsapp-poc.env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'").strip('"')
    token = env.get("WAPOC_TOKEN") or ""
    port = env.get("WAPOC_PORT") or "8009"
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/fetch-midmar-history",
        data=b"{}",
        method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print("FETCH", r.status, r.read()[:240])
    except Exception as e:
        print("FETCH_ERR", e)


def show_head() -> None:
    payload = mm.public_payload(RID, STATIC)
    videos = payload.get("videos") or []
    print("PUBLIC_N", len(videos))
    for i, v in enumerate(videos[:6]):
        print(i, v.get("started_at"), v.get("id"), (v.get("title") or "")[:48])


def main() -> None:
    backup()
    patch_public_dedupe()
    retarget_thumb()
    drop_orphan_dupes()
    fetch_1452()
    time.sleep(2)
    show_head()
    print("DONE")


if __name__ == "__main__":
    main()
