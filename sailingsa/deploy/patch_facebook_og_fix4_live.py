#!/usr/bin/env python3
"""Pass sailor avatar crop position into OG PNG renderer (circle, not raw photo)."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX4_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

HELPER = '''
def _fb_og_sailor_avatar_position(sas_id: str) -> tuple[float, float]:
    """Match DEV1_AVATAR_CROP object-position overrides on /sailor/ pages."""
    sid = str(sas_id or "").strip()
    if sid == "21172":
        return (0.36, 0.22)
    if sid == "13522":
        return (0.55, 0.22)
    if sid == "6903":
        return (0.50, 0.12)
    return (0.50, 0.28)

'''

PREPARE_OLD = """    if not path or not os.path.isfile(path):
        return None
    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path)
    fp = _fb.source_fingerprint(path)
    return _fb.build_og_image_url(_canonical_base_url(), page_type, entity_key, fp)"""

PREPARE_NEW = """    if not path or not os.path.isfile(path):
        return None
    _pos = None
    if (page_type or "").strip().lower() == "sailor":
        _pos = _fb_og_sailor_avatar_position(_get_sailor_sas_id_from_slug(entity_key) or "")
    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos)
    fp = _fb.og_cache_fingerprint(path, page_type, _pos)
    return _fb.build_og_image_url(_canonical_base_url(), page_type, entity_key, fp)"""

API_OLD = """    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="OG source not found")
    out = _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path)"""

API_NEW = """    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="OG source not found")
    _pos = None
    if (page_type or "").strip().lower() == "sailor":
        _pos = _fb_og_sailor_avatar_position(_get_sailor_sas_id_from_slug(entity_key) or "")
    out = _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos)"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix4")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix4_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    anchor = "def _fb_og_prepare("
    if anchor not in text:
        raise SystemExit("_fb_og_prepare anchor not found")
    text = text.replace(anchor, HELPER + MARKER + "\n" + anchor, 1)

    if PREPARE_OLD not in text:
        raise SystemExit("_fb_og_prepare body anchor not found")
    text = text.replace(PREPARE_OLD, PREPARE_NEW, 1)

    if API_OLD not in text:
        raise SystemExit("api_facebook_og_image anchor not found")
    text = text.replace(API_OLD, API_NEW, 1)

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix4", API_PATH)


if __name__ == "__main__":
    main()
