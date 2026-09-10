#!/usr/bin/env python3
"""Restore last-good ZVYC cam: token + ffmpeg thumb, no 4040.jpg first. Bump mmr118."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_snap = '''    def _keep(jpg: bytes) -> bytes:
        with _ZVYC_GRAB_LOCK:
            _ZVYC_GRAB_MEM["t"] = time.time()
            _ZVYC_GRAB_MEM["jpg"] = jpg
        return jpg

    try:
        with httpx.Client(
            timeout=8.0, follow_redirects=True, headers=_ZVYC_CAM_FETCH_HEADERS
        ) as client:
            snap = client.get(_ZVYC_LIVE_CAM_SNAP)
        jpg = snap.content or b""
        if snap.status_code < 400 and jpg[:2] == b"\\xff\\xd8":
            return _keep(jpg)
    except Exception as e:
        print(f"[zvyc_live_cam] snap failed: {e}", flush=True)

    url = _zvyc_live_cam_stream_url(explicit_token)
    if not url:
        return b""
'''
new_stream = '''    url = _zvyc_live_cam_stream_url(explicit_token)
    if not url:
        return b""
'''
if "[zvyc_live_cam] snap failed" in src:
    if old_snap not in src:
        raise SystemExit("ANCHOR_SNAP_MISSING")
    src = src.replace(old_snap, new_stream, 1)
    print("SNAP_FIRST_REMOVED")
else:
    print("SNAP_FIRST_ALREADY")

old_ok = '''        if proc.returncode == 0 and jpg[:2] == b"\\xff\\xd8":
            return _keep(jpg)
'''
new_ok = '''        if proc.returncode == 0 and jpg[:2] == b"\\xff\\xd8":
            with _ZVYC_GRAB_LOCK:
                _ZVYC_GRAB_MEM["t"] = time.time()
                _ZVYC_GRAB_MEM["jpg"] = jpg
            return jpg
'''
if old_ok in src:
    src = src.replace(old_ok, new_ok, 1)
    print("GRAB_KEEP_RESTORED")
else:
    print("GRAB_KEEP_SKIP")

for old_js, new_js in (
    ("mm-lipton-reels-card.js?v=mmr117", "mm-lipton-reels-card.js?v=mmr118"),
    ("mm-lipton-reels-card.js?v=mmr116", "mm-lipton-reels-card.js?v=mmr118"),
    ("mm-lipton-reels-card.js?v=mmr115", "mm-lipton-reels-card.js?v=mmr118"),
):
    if "mm-lipton-reels-card.js?v=mmr118" in src:
        print("JS_MM_ALREADY")
        break
    if old_js in src:
        src = src.replace(old_js, new_js, 1)
        print("JS_MM_BUMPED", old_js)
        break
else:
    if "mm-lipton-reels-card.js?v=mmr118" not in src:
        raise SystemExit("ANCHOR_MM_JS_MISSING")

if "[zvyc_live_cam] snap failed" in src:
    raise SystemExit("SNAP_STILL_PRESENT")

API.write_text(src, encoding="utf-8")
print("mmr118", "mm-lipton-reels-card.js?v=mmr118" in src)
print("no_snap_first", "[zvyc_live_cam] snap failed" not in src)
