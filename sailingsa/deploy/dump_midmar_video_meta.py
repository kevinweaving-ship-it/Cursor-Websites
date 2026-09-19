#!/usr/bin/env python3
"""Compare Midmar clip started_at vs file mtime vs ffprobe metadata."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, "/var/www/sailingsa")
from sailingsa.backend import mm_event_clips as mm

RID = "2026-09-19-hmyc-midmar-cup"
STATIC = Path("/var/www/sailingsa")
folder = mm.clips_dir(RID, STATIC)

print("===== LIMITS =====")
arch = Path("/opt/arial-whatsapp-poc/event_group_archive.js")
print("ARCHIVE", [ln.strip() for ln in arch.read_text().splitlines() if "MAX_BYTES" in ln][:3])
print("MM", [ln.strip() for ln in Path("/var/www/sailingsa/sailingsa/backend/mm_event_clips.py").read_text().splitlines() if "MAX_BYTES" in ln][:3])
print("14:52 KEY", "AC4466BD0CBCAF767B27527269A40B99" in Path("/opt/arial-whatsapp-poc/poc.js").read_text())

payload = mm.public_payload(RID, STATIC)
videos = payload.get("videos") or []
print("\n===== PUBLIC HEAD =====")
print("N", len(videos))
for i, v in enumerate(videos[:15]):
    print(
        f"{i:02d} {v.get('kind')} {v.get('started_at')} {v.get('id')} "
        f"{(v.get('title') or '')[:60]!r} {v.get('play_url')}"
    )

print("\n===== TOO LARGE =====")
try:
    out = subprocess.check_output(
        [
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-d",
            "sailors_master",
            "-At",
            "-c",
            "SELECT wa_message_id, sender_name, media_error, media_bytes, media_filename, occurred_at FROM public.event_whatsapp_messages WHERE media_error='too_large' OR occurred_at >= '2026-09-19 14:50:00+02' ORDER BY occurred_at DESC;",
        ],
        text=True,
        timeout=20,
    )
    print(out)
except Exception as e:
    print(e)

print("\n===== FFPROBE NEWEST VIDEOS =====")


def probe(path: Path) -> dict:
    try:
        raw = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            text=True,
            timeout=30,
        )
        data = json.loads(raw)
    except Exception as e:
        return {"err": str(e)}
    fmt = data.get("format") or {}
    tags = fmt.get("tags") or {}
    streams = data.get("streams") or []
    stags = {}
    for s in streams:
        if s.get("codec_type") == "video":
            stags = s.get("tags") or {}
            break
    return {
        "duration": fmt.get("duration"),
        "size": fmt.get("size"),
        "creation_time": tags.get("creation_time") or stags.get("creation_time"),
        "com.apple.quicktime.creationdate": tags.get("com.apple.quicktime.creationdate"),
        "encoder": tags.get("encoder"),
        "major_brand": tags.get("major_brand"),
    }


# public videos first 12 that are video
checked = 0
for v in videos:
    if v.get("kind") != "video":
        continue
    play = str(v.get("play_url") or "")
    name = Path(play).name
    f = folder / name if name.startswith("mmclip-") else Path("/var/www/sailingsa") / play.lstrip("/")
    if not f.is_file():
        # try img
        f = Path("/var/www/sailingsa") / play.lstrip("/")
    if not f.is_file():
        print("MISSING", v.get("id"), play)
        continue
    meta = probe(f)
    mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
    print(
        v.get("id"),
        "started",
        v.get("started_at"),
        "mtime",
        mtime,
        "meta",
        meta.get("creation_time"),
        "dur",
        meta.get("duration"),
        "title",
        (v.get("title") or "")[:50],
    )
    checked += 1
    if checked >= 14:
        break

print("\n===== FOLDER NEWEST MP4 =====")
files = sorted(folder.glob("mmclip-*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
ids_in_json = {str(v.get("id")) for v in videos}
for p in files[:12]:
    meta = probe(p)
    cid = p.stem
    in_json = cid in ids_in_json
    print(
        datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        p.stat().st_size,
        p.name,
        "IN_JSON" if in_json else "ORPHAN",
        "meta",
        meta.get("creation_time"),
        "dur",
        meta.get("duration"),
    )
