#!/usr/bin/env python3
"""Encode spaces in fleet header class logo URLs (left + right)."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
OLD = '''left_col = ""
    right_col = ""
    if display_url:
        img = (
            f'<img src="{html_module.escape(display_url)}" alt="" class="class-header-logo-img" '
            f'loading="lazy" decoding="async" />'
        )
        left_col = f'<div class="class-header-logo-col">{img}</div>'
    right_logo_url = _wc_regatta_fleet_block_logo_url_right(rid, bid)
    right_display = right_logo_url or display_url
    if right_display:
        img_r = (
            f'<img src="{html_module.escape(right_display)}" alt="" class="class-header-logo-img" '
            f'loading="lazy" decoding="async" />'
        )
        right_col = f'<div class="class-header-club-logo-col">{img_r}</div>'
    return left_col, right_col'''
NEW = '''def _enc_artwork_src(url: str) -> str:
        raw = (url or "").strip()
        if not raw:
            return ""
        try:
            from urllib.parse import quote, urlsplit, urlunsplit
            if "://" in raw:
                parts = urlsplit(raw)
                return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%"), parts.query, parts.fragment))
            path = raw if raw.startswith("/") else "/" + raw
            return quote(path, safe="/%")
        except Exception:
            return raw.replace(" ", "%20")

    left_col = ""
    right_col = ""
    if display_url:
        src = html_module.escape(_enc_artwork_src(display_url))
        alt = "J22" if "j22" in str(display_url).lower() else ""
        img = (
            f'<img src="{src}" alt="{html_module.escape(alt)}" class="class-header-logo-img" '
            f'loading="lazy" decoding="async" />'
        )
        left_col = f'<div class="class-header-logo-col">{img}</div>'
    right_logo_url = _wc_regatta_fleet_block_logo_url_right(rid, bid)
    right_display = right_logo_url or display_url
    if right_display:
        src_r = html_module.escape(_enc_artwork_src(right_display))
        alt_r = "J22" if "j22" in str(right_display).lower() else ""
        img_r = (
            f'<img src="{src_r}" alt="{html_module.escape(alt_r)}" class="class-header-logo-img" '
            f'loading="lazy" decoding="async" />'
        )
        right_col = f'<div class="class-header-club-logo-col">{img_r}</div>'
    return left_col, right_col'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if "_enc_artwork_src" in text and "class-header-logo-img" in text:
        # already has helper in fleet fn
        if 'alt = "J22" if "j22"' in text or "alt = \"J22\" if \"j22\"" in text:
            print("already patched")
            return 0
    if OLD not in text:
        raise SystemExit("anchor not found")
    bak = API.with_suffix(f".py.bak_fleet_logo_enc_{int(time.time())}")
    shutil.copy2(API, bak)
    API.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
