#!/usr/bin/env python3
"""v3: 4040livic is live; status accepts token; do not seed last-live from jpg."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

REPLACES = [
    (
        '_ZVYC_CAM_OFFLINE_RE = re.compile(r"4040livic|4040[.]jpg|/4040", re.I)',
        '_ZVYC_CAM_OFFLINE_RE = re.compile(r"4040[.]jpg|copyright_violation|/temp/4040", re.I)',
    ),
    (
        '        html_headers["Accept-Encoding"] = "identity"\n',
        '        html_headers["Accept-Encoding"] = "gzip, deflate"\n',
    ),
    (
        '    if not ts:\n        ts = _zvyc_cam_still_mtime()\n    if ts:\n',
        '    if ts:\n',
    ),
    (
        'def api_zvyc_live_cam_status(regatta_id: str):\n    """Probe the actual HLS feed. 4040 placeholder is not live."""\n    if str(regatta_id or "").strip() != _CAPE_CLASSIC_MM_REGATTA_ID:\n        raise HTTPException(status_code=404, detail="not found")\n    live = _zvyc_cam_probe_live()\n',
        'def api_zvyc_live_cam_status(regatta_id: str, a: str = Query("")):\n    """Probe the actual HLS feed. 4040livic is the live cam; 4040.jpg is offline."""\n    if str(regatta_id or "").strip() != _CAPE_CLASSIC_MM_REGATTA_ID:\n        raise HTTPException(status_code=404, detail="not found")\n    live = _zvyc_cam_probe_live(a)\n',
    ),
    (
        'mm-lipton-reels-card.js?v=mmr139',
        'mm-lipton-reels-card.js?v=mmr140',
    ),
]


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in REPLACES:
        if old not in text:
            print("missing", repr(old[:80]))
            continue
        text = text.replace(old, new, 1)
        print("replaced", old[:60].replace("\n", " "))
        changed = True
    if "ZVYC_CAM_STAMP_v2" in text:
        text = text.replace("ZVYC_CAM_STAMP_v2", "ZVYC_CAM_STAMP_v3", 1)
        print("marker v3")
        changed = True
    if not changed:
        raise SystemExit("nothing replaced")
    path.write_text(text, encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    apply(API)
