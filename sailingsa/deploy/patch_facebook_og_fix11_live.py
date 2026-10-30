#!/usr/bin/env python3
"""OG fix11: case-insensitive Class Logo artwork match (ILCA 6/7, Topper 5.3, etc.)."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER = "# FB_OG_FIX11_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

# Replace the file-exists loop inside _artwork_class_logo_path_for_class_name
# with a case-insensitive directory lookup.

OLD = """        try:
            for art_root in art_roots:
                for fn in candidates:
                    if os.path.isfile(os.path.join(art_root, fn)):
                        return f"/artwork/Class Logo/{fn}"
        except OSError:
            pass
    return None


def _norm_artwork_path(path: Optional[str]) -> str:"""

NEW = """        try:
            for art_root in art_roots:
                if not os.path.isdir(art_root):
                    continue
                # Exact match first
                for fn in candidates:
                    p = os.path.join(art_root, fn)
                    if os.path.isfile(p):
                        return f"/artwork/Class Logo/{fn}"
                # Case-insensitive match (ILCA-6 vs Ilca-6, Topper-5.3, etc.)
                try:
                    listing = os.listdir(art_root)
                except OSError:
                    listing = []
                lower_map = {f.casefold(): f for f in listing}
                for fn in candidates:
                    real = lower_map.get(fn.casefold())
                    if real and os.path.isfile(os.path.join(art_root, real)):
                        return f"/artwork/Class Logo/{real}"
        except OSError:
            pass
    return None


def _norm_artwork_path(path: Optional[str]) -> str:"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix11")
        return
    if OLD not in text:
        raise SystemExit("artwork case-sensitive loop anchor not found")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix11_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    insert_at = "# FB_OG_FIX10_v1\n"
    if insert_at not in text:
        raise SystemExit("FB_OG_FIX10 marker not found")
    text = text.replace(insert_at, insert_at + MARKER + "\n", 1)
    text = text.replace(OLD, NEW, 1)

    # Also harden _fb_og_class_logo_public_url: if directory helper returns None,
    # retry artwork with key and common case variants.
    CLASS_LOGO_OLD = '''    name = (cname or key).strip()
    return _directory_class_item_logo_url(name, logo_path)


def _fb_og_entity_public_url(page_type: str, entity_key: str) -> Optional[str]:'''

    CLASS_LOGO_NEW = '''    name = (cname or key).strip()
    url = _directory_class_item_logo_url(name, logo_path)
    if url:
        return url
    # Case / punctuation variants (Ilca 6 → ILCA-6-Class-Logo.png, 4.7 dots)
    for try_name in (
        name,
        name.upper(),
        key,
        key.replace("-", " "),
        key.replace("-", "."),
        (cname or "").upper(),
    ):
        if not try_name:
            continue
        art = _artwork_class_logo_path_for_class_name(try_name)
        if art:
            return art
    return None


def _fb_og_entity_public_url(page_type: str, entity_key: str) -> Optional[str]:'''

    if CLASS_LOGO_OLD not in text:
        raise SystemExit("class logo public url anchor not found")
    text = text.replace(CLASS_LOGO_OLD, CLASS_LOGO_NEW, 1)

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix11", API_PATH)


if __name__ == "__main__":
    main()
