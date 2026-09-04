#!/usr/bin/env python3
"""OG fix10: fingerprint in URL path (FB ignores ?v=) + artwork prefers STATIC_DIR."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER = "# FB_OG_FIX10_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
OG_MODULE_SRC = Path(__file__).resolve().parent / "facebook_og.py"
OG_MODULE_DST = Path("/var/www/sailingsa/api/facebook_og.py")

ROUTE_OLD = """@app.api_route("/api/og/{page_type}/{entity_key}.png", methods=["GET", "HEAD"])
def api_facebook_og_image(page_type: str, entity_key: str, v: Optional[str] = None):
    import facebook_og as _fb
    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        path = _fb_url_to_local(_FB_OG_BRAND_URL)
    _pos = None
    if (page_type or "").strip().lower() == "sailor":
        _pos = _fb_og_sailor_avatar_position(_get_sailor_sas_id_from_slug(entity_key) or "")
    out = _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos)
    headers = {"Cache-Control": "public, max-age=86400"}
    return FileResponse(out, media_type="image/png", headers=headers)"""

ROUTE_NEW = """@app.api_route("/api/og/{page_type}/{entity_key}.png", methods=["GET", "HEAD"])
def api_facebook_og_image(page_type: str, entity_key: str, v: Optional[str] = None):
    return api_facebook_og_image_versioned(page_type, entity_key, v or "0")


@app.api_route("/api/og/{page_type}/{entity_key}/{v}.png", methods=["GET", "HEAD"])
def api_facebook_og_image_versioned(page_type: str, entity_key: str, v: str):
    import facebook_og as _fb
    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        path = _fb_url_to_local(_FB_OG_BRAND_URL)
    _pos = None
    if (page_type or "").strip().lower() == "sailor":
        _pos = _fb_og_sailor_avatar_position(_get_sailor_sas_id_from_slug(entity_key) or "")
    out = _fb.cache_og_png(
        _fb_og_cache_dir(), page_type, entity_key, path,
        object_position=_pos, static_dir=STATIC_DIR,
    )
    headers = {"Cache-Control": "public, max-age=86400"}
    return FileResponse(out, media_type="image/png", headers=headers)"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    if OG_MODULE_SRC.is_file() and OG_MODULE_SRC.resolve() != OG_MODULE_DST.resolve():
        shutil.copy2(OG_MODULE_SRC, OG_MODULE_DST)
        print(f"Updated {OG_MODULE_DST}")
    else:
        print(f"OG module at {OG_MODULE_DST}")

    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix10")
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix10_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    insert_at = "# FB_OG_FIX9_v1\n"
    if insert_at not in text:
        raise SystemExit("FB_OG_FIX9 marker not found")
    text = text.replace(insert_at, insert_at + MARKER + "\n", 1)

    if ROUTE_OLD in text:
        text = text.replace(ROUTE_OLD, ROUTE_NEW, 1)
    elif "api_facebook_og_image_versioned" in text:
        print("versioned OG route already present")
    else:
        raise SystemExit("OG route anchor not found")

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix10", API_PATH)


if __name__ == "__main__":
    main()
