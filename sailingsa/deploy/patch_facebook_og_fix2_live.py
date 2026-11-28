#!/usr/bin/env python3
"""Fix FB OG on live api.py: wire sailor route (serve_dev1_rank_page) + bust events-logos cache."""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX2_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

SAILOR_ANCHOR = """        else:
            combined = combined.replace("</head>", f'<link rel="canonical" href="{_ec}"></head>', 1)
    return HTMLResponse(combined, media_type="text/html")"""

SAILOR_REPLACEMENT = """        else:
            combined = combined.replace("</head>", f'<link rel="canonical" href="{_ec}"></head>', 1)
        import facebook_og as _fb
        _sas_fb = (final_sas or "").strip() or _get_sailor_sas_id_from_slug(_sailor_canon_slug)
        _sn = (sailor_name or "Sailor").strip()
        _fb_head = _fb_og_head_for(
            "sailor",
            _sailor_canon_slug,
            f"{_sn} | SailingSA",
            f"Official SailingSA profile for {_sn}. Results, rankings and regattas.",
            _canon,
            og_type="profile",
            source_path=_fb_og_sailor_avatar_local(_sas_fb, _sn) if _sas_fb else None,
        )
        combined = _fb.inject_facebook_head(combined, _fb_head)
    return HTMLResponse(combined, media_type="text/html")"""

CACHE_MARKER = "_EVENTS_LOGOS_HTML_TTL_SEC = 7 * 24 * 3600.0  # disk is SSOT; rare new events"
CACHE_INSERT = """_EVENTS_LOGOS_HTML_TTL_SEC = 7 * 24 * 3600.0  # disk is SSOT; rare new events
_EVENTS_LOGOS_OG_CACHE_MARKER = "og:image"  # FB_OG_FIX2_v1 — reject stale HTML without OG"""


def _patch_cache_get(text: str) -> str:
    old = """    if ent and (now - float(ent[0])) < _EVENTS_LOGOS_HTML_TTL_SEC:
        return ent[1]"""
    new = """    if ent and (now - float(ent[0])) < _EVENTS_LOGOS_HTML_TTL_SEC:
        if _EVENTS_LOGOS_OG_CACHE_MARKER in (ent[1] or ""):
            return ent[1]"""
    if old not in text:
        raise SystemExit("events-logos memory cache anchor not found")
    return text.replace(old, new, 1)


def _patch_cache_disk(text: str) -> str:
    old = """            html = open(disk, encoding="utf-8", errors="replace").read()
            if html:
                details[key] = (now, html)
                return html"""
    new = """            html = open(disk, encoding="utf-8", errors="replace").read()
            if html and _EVENTS_LOGOS_OG_CACHE_MARKER in html:
                details[key] = (now, html)
                return html"""
    if old not in text:
        raise SystemExit("events-logos disk cache anchor not found")
    return text.replace(old, new, 1)


def _patch_gallery_cache(text: str) -> str:
    old = """    if ent.get("gallery") and (now - float(ent.get("gallery_ts") or 0)) < _EVENTS_LOGOS_HTML_TTL_SEC:
        return ent["gallery"]"""
    new = """    if ent.get("gallery") and (now - float(ent.get("gallery_ts") or 0)) < _EVENTS_LOGOS_HTML_TTL_SEC:
        if _EVENTS_LOGOS_OG_CACHE_MARKER in (ent.get("gallery") or ""):
            return ent["gallery"]"""
    if old not in text:
        raise SystemExit("events-logos gallery memory cache anchor not found")
    return text.replace(old, new, 1)


def _patch_gallery_disk(text: str) -> str:
    old = """            html = open(disk, encoding="utf-8", errors="replace").read()
            if html:
                ent["gallery"] = html
                ent["gallery_ts"] = now
                return html"""
    new = """            html = open(disk, encoding="utf-8", errors="replace").read()
            if html and _EVENTS_LOGOS_OG_CACHE_MARKER in html:
                ent["gallery"] = html
                ent["gallery_ts"] = now
                return html"""
    if old not in text:
        raise SystemExit("events-logos gallery disk cache anchor not found")
    return text.replace(old, new, 1)


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix2")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix2_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    if SAILOR_ANCHOR not in text:
        raise SystemExit("serve_dev1_rank_page sailor return anchor not found")
    text = text.replace(SAILOR_ANCHOR, SAILOR_REPLACEMENT, 1)

    if CACHE_MARKER not in text:
        raise SystemExit("events-logos TTL anchor not found")
    text = text.replace(CACHE_MARKER, CACHE_INSERT, 1)
    text = _patch_gallery_cache(text)
    text = _patch_gallery_disk(text)
    text = _patch_cache_get(text)
    text = _patch_cache_disk(text)

    text = text.replace(
        CACHE_INSERT,
        CACHE_INSERT + "\n" + MARKER,
        1,
    )

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix2", API_PATH)


if __name__ == "__main__":
    main()
