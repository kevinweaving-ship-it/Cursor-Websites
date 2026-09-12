#!/usr/bin/env python3
"""Fix ZVYC live cam and put it last once MM reels/live exist.

Skyline blocks the SA server IP (empty HTML + copyright_violation HLS).
Play hd-auth live.m3u8 in the phone browser (user IP). Thumb falls back
to Skyline 4040.jpg. Webcam stays in the list, last when MM clips exist.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")

API_REPLACEMENTS = [
    (
        '''    "thumb": "/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-thumb",
    "live_snap": "/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-thumb",''',
        '''    "thumb": "https://www.skylinewebcams.com/temp/4040.jpg",
    "live_snap": "https://www.skylinewebcams.com/temp/4040.jpg",''',
    ),
    (
        '''        print(f"[zvyc_live_cam] grab failed: {e}", flush=True)
    return b""


def _cape_classic_has_real_reels(videos: list) -> bool:''',
        '''        print(f"[zvyc_live_cam] grab failed: {e}", flush=True)
    try:
        with httpx.Client(
            timeout=8.0, follow_redirects=True, headers=_ZVYC_CAM_FETCH_HEADERS
        ) as client:
            resp = client.get(_ZVYC_LIVE_CAM_SNAP)
        jpg = resp.content or b""
        if resp.status_code < 400 and jpg[:2] == b"\\xff\\xd8":
            with _ZVYC_GRAB_LOCK:
                _ZVYC_GRAB_MEM["t"] = time.time()
                _ZVYC_GRAB_MEM["jpg"] = jpg
            return jpg
    except Exception as e:
        print(f"[zvyc_live_cam] snap failed: {e}", flush=True)
    return b""


def _cape_classic_has_real_reels(videos: list) -> bool:''',
    ),
    (
        '''        videos.append(n)
    if not videos:
        videos = [dict(_ZVYC_LIVE_CAM)]
    return {
        "enabled": True,
        "feed_source": "marine-megastore",
        "fb_page": "marin.megastoresa",
        "videos": _mm_apply_page_chrome(_mm_sorted_newest(videos)),
    }''',
        '''        videos.append(n)
    videos = _mm_apply_page_chrome(_mm_sorted_newest(videos))
    cam = dict(_ZVYC_LIVE_CAM)
    videos = [v for v in videos if str((v or {}).get("id") or "") != "zvyc-live-cam"]
    # Until MM live/reels exist, cam is the only tile. Once they do, cam is last.
    if videos:
        videos.append(cam)
    else:
        videos = [cam]
    return {
        "enabled": True,
        "feed_source": "marine-megastore",
        "fb_page": "marin.megastoresa",
        "videos": videos,
    }''',
    ),
    (
        "mm-lipton-reels-card.js?v=mmr119",
        "mm-lipton-reels-card.js?v=mmr120",
    ),
]

JS_REPLACEMENTS = [
    (
        '''    if (isWebcam(v)) {
      var root = cardEl();
      return withCamQuery(u, camTokenOf(root), true);
    }''',
        '''    if (isWebcam(v)) {
      var root = cardEl();
      var tok = camTokenOf(root);
      if (tok) return 'https://hd-auth.skylinewebcams.com/live.m3u8?a=' + encodeURIComponent(tok);
      return withCamQuery(u, tok, true);
    }''',
    ),
]


def apply(path: Path, reps: list) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(reps, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    api = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    js = Path(sys.argv[2]) if len(sys.argv) > 2 else JS
    apply(api, API_REPLACEMENTS)
    apply(js, JS_REPLACEMENTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
