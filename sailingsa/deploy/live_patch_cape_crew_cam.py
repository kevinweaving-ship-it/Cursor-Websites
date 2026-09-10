#!/usr/bin/env python3
"""Cape Classic: always emit Staff HTML; cam thumb falls back to Skyline still. Bump JS."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_gate = """    show = _cape_classic_crew_show()
    if not show and not is_editor:
        return \"\"
"""
new_gate = """    show = _cape_classic_crew_show()
"""
if old_gate in src:
    src = src.replace(old_gate, new_gate, 1)
    print("CREW_GATE_REMOVED")
elif "if not show and not is_editor:" not in src:
    print("CREW_GATE_ALREADY")
else:
    raise SystemExit("ANCHOR_CREW_GATE_MISSING")

old_css = '".cape-crew--hidden .table-wrapper{opacity:0.55}"'
new_css = (
    '".cape-crew--hidden{display:none}"'
    '\n    ".regatta-page--club-score-edit .cape-crew--hidden,"'
    '\n    ".regatta-page--super-admin-edit .cape-crew--hidden,"'
    '\n    ".cape-crew--admin.cape-crew--hidden{display:block}"'
    '\n    ".regatta-page--club-score-edit .cape-crew--hidden .table-wrapper,"'
    '\n    ".regatta-page--super-admin-edit .cape-crew--hidden .table-wrapper,"'
    '\n    ".cape-crew--admin.cape-crew--hidden .table-wrapper{opacity:0.55}"'
)
if ".regatta-page--club-score-edit .cape-crew--hidden" in src:
    print("CREW_CSS_ALREADY")
elif old_css in src:
    src = src.replace(old_css, new_css, 1)
    print("CREW_CSS_UPDATED")
else:
    raise SystemExit("ANCHOR_CREW_CSS_MISSING")

old_empty = '''    url = _zvyc_live_cam_stream_url(explicit_token)
    if not url:
        return b""
'''
new_empty = '''    def _keep(jpg: bytes) -> bytes:
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
if "[zvyc_live_cam] snap failed" in src:
    print("SNAP_ALREADY")
elif old_empty in src:
    src = src.replace(old_empty, new_empty, 1)
    print("SNAP_FALLBACK")
else:
    raise SystemExit("ANCHOR_SNAP_MISSING")

old_ok = '''        if proc.returncode == 0 and jpg[:2] == b"\\xff\\xd8":
            with _ZVYC_GRAB_LOCK:
                _ZVYC_GRAB_MEM["t"] = time.time()
                _ZVYC_GRAB_MEM["jpg"] = jpg
            return jpg
'''
new_ok = '''        if proc.returncode == 0 and jpg[:2] == b"\\xff\\xd8":
            return _keep(jpg)
'''
if old_ok in src:
    src = src.replace(old_ok, new_ok, 1)
    print("GRAB_KEEP")
else:
    print("GRAB_KEEP_SKIP")

for old_js, new_js in (
    ("mm-lipton-reels-card.js?v=mmr113", "mm-lipton-reels-card.js?v=mmr116"),
    ("mm-lipton-reels-card.js?v=mmr114", "mm-lipton-reels-card.js?v=mmr116"),
    ("mm-lipton-reels-card.js?v=mmr115", "mm-lipton-reels-card.js?v=mmr116"),
):
    if "mm-lipton-reels-card.js?v=mmr116" in src:
        print("JS_MM_ALREADY")
        break
    if old_js in src:
        src = src.replace(old_js, new_js, 1)
        print("JS_MM_BUMPED", old_js)
        break
else:
    if "mm-lipton-reels-card.js?v=mmr116" not in src:
        raise SystemExit("ANCHOR_MM_JS_MISSING")

for old_js, new_js in (
    ("club-score-edit.js?v=ccr15", "club-score-edit.js?v=ccr16"),
    ("club-score-edit.js?v=ccr14", "club-score-edit.js?v=ccr16"),
):
    if "club-score-edit.js?v=ccr16" in src:
        print("JS_CC_ALREADY")
        break
    if old_js in src:
        src = src.replace(old_js, new_js, 1)
        print("JS_CC_BUMPED", old_js)
        break
else:
    if "club-score-edit.js?v=ccr16" not in src:
        print("JS_CC_SKIP")

API.write_text(src, encoding="utf-8")
print("crew_hidden_css", ".regatta-page--club-score-edit .cape-crew--hidden" in src)
print("snap", "[zvyc_live_cam] snap failed" in src)
print("mmr116", "mm-lipton-reels-card.js?v=mmr116" in src)
print("ccr16", "club-score-edit.js?v=ccr16" in src)
