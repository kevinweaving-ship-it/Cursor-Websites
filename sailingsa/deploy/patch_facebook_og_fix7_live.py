#!/usr/bin/env python3
"""Unified OG entity logo resolver (same URL as page) + always emit og:image."""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_FIX7_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

HELPER = '''
_FB_OG_BRAND_URL = "/assets/logos/sailingsa-logo-on-white.png"


def _fb_og_class_logo_public_url(entity_key: str) -> Optional[str]:
    """Same logo URL as /class/ and /classes/ tiles (DB logo_path + artwork SSOT)."""
    key = (entity_key or "").strip()
    if not key:
        return None
    cid, cname = _resolve_class_slug_to_class_id(key)
    logo_path = None
    if cid:
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT NULLIF(btrim(logo_path), '') FROM classes WHERE class_id = %s LIMIT 1",
                    (int(cid),),
                )
                row = cur.fetchone()
                if row and row[0]:
                    logo_path = str(row[0]).strip()
            finally:
                cur.close()
        except Exception:
            pass
        finally:
            if conn:
                return_db_connection(conn)
    name = (cname or key).strip()
    return _directory_class_item_logo_url(name, logo_path)


def _fb_og_entity_public_url(page_type: str, entity_key: str) -> Optional[str]:
    """Public logo/avatar URL shown on the live page for this entity."""
    pt = (page_type or "").strip().lower()
    key = (entity_key or "").strip()
    if pt in ("home", "directory"):
        return _FB_OG_BRAND_URL
    if pt == "class":
        return _fb_og_class_logo_public_url(key)
    if pt == "sailor":
        name, canon = _get_sailor_name_by_slug(key)
        if not name:
            return None
        sas = _get_sailor_sas_id_from_slug(canon or key)
        if sas:
            parts = name.split(None, 1)
            fn = parts[0] if parts else name
            ln = parts[1] if len(parts) > 1 else ""
            return _users_avatar_url(str(sas), fn, ln, name)
        return "/assets/avatars/default-youth.png"
    if pt == "club":
        club = _get_club_by_slug(key)
        if not club:
            return None
        _cid, _cn, ca = club
        code = (ca or "").strip()
        return f"/api/club-logo/{code}" if code else None
    if pt == "regatta":
        reg = _get_regatta_by_regatta_id(key) or _get_regatta_by_slug(key)
        if not reg:
            return None
        rid, ev_name = reg[0], reg[1]
        return _fb_og_regatta_left_url(str(rid), ev_name)
    if pt == "events_logos":
        if key in ("index", ""):
            return _FB_OG_BRAND_URL
        return _fb_og_events_logo_url(key)
    if pt == "sponsor":
        return _fb_og_sponsor_logo_url(key)
    return None


def _fb_og_resolve_local_path(
    page_type: str,
    entity_key: str,
    *,
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
) -> Optional[str]:
    path = (source_path or "").strip() or None
    if not path and source_url:
        path = _fb_url_to_local(source_url)
    if path and os.path.isfile(path):
        return path
    pub = _fb_og_entity_public_url(page_type, entity_key)
    if pub:
        path = _fb_url_to_local(pub)
        if path and os.path.isfile(path):
            return path
    return _fb_url_to_local(_FB_OG_BRAND_URL)

'''

PREPARE_OLD = """def _fb_og_prepare(
    page_type: str,
    entity_key: str,
    *,
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
) -> Optional[str]:
    import facebook_og as _fb
    path = source_path
    if not path and source_url:
        path = _fb_url_to_local(source_url)
    if not path or not os.path.isfile(path):
        return None
    _pos = None
    if (page_type or "").strip().lower() == "sailor":
        _pos = _fb_og_sailor_avatar_position(_get_sailor_sas_id_from_slug(entity_key) or "")
    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos, static_dir=STATIC_DIR)
    fp = _fb.og_cache_fingerprint(path, page_type, _pos)
    return _fb.build_og_image_url(_canonical_base_url(), page_type, entity_key, fp)"""

PREPARE_NEW = """def _fb_og_prepare(
    page_type: str,
    entity_key: str,
    *,
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
) -> Optional[str]:
    import facebook_og as _fb
    path = _fb_og_resolve_local_path(
        page_type, entity_key, source_url=source_url, source_path=source_path
    )
    if not path or not os.path.isfile(path):
        return None
    _pos = None
    if (page_type or "").strip().lower() == "sailor":
        _pos = _fb_og_sailor_avatar_position(_get_sailor_sas_id_from_slug(entity_key) or "")
    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path, object_position=_pos, static_dir=STATIC_DIR)
    fp = _fb.og_cache_fingerprint(path, page_type, _pos)
    return _fb.build_og_image_url(_canonical_base_url(), page_type, entity_key, fp)"""

RESOLVE_OLD = """def _fb_og_resolve_source(page_type: str, entity_key: str) -> Optional[str]:
    pt = (page_type or "").strip().lower()
    key = (entity_key or "").strip()
    if pt == "home":
        return _fb_url_to_local("/assets/logos/sailingsa-logo.png")
    if pt == "directory":
        return _fb_url_to_local("/assets/logos/sailingsa-logo.png")
    if pt == "sailor":
        name, canon = _get_sailor_name_by_slug(key)
        if not name:
            return None
        sas = _get_sailor_sas_id_from_slug(canon or key)
        return _fb_og_sailor_avatar_local(sas, name) if sas else _fb_url_to_local("/assets/avatars/default-youth.png")
    if pt == "class":
        cid, cname = _resolve_class_slug_to_class_id(key)
        if not cname:
            return _fb_url_to_local(_artwork_class_logo_path_for_class_name(key) or "")
        lp = _artwork_class_logo_path_for_class_name(cname)
        return _fb_url_to_local(lp) if lp else None
    if pt == "club":
        club = _get_club_by_slug(key)
        if not club:
            return None
        _cid, _cn, ca = club
        return _club_logo_disk_path((ca or "").strip())
    if pt == "regatta":
        reg = _get_regatta_by_regatta_id(key) or _get_regatta_by_slug(key)
        if not reg:
            return None
        rid, ev_name = reg[0], reg[1]
        lu = _fb_og_regatta_left_url(str(rid), ev_name)
        return _fb_url_to_local(lu) if lu else None
    if pt == "events_logos":
        if key in ("index", ""):
            return _fb_url_to_local("/assets/logos/sailingsa-logo.png")
        return _fb_url_to_local(_fb_og_events_logo_url(key) or "")
    if pt == "sponsor":
        return _fb_url_to_local(_fb_og_sponsor_logo_url(key) or "")
    return None"""

RESOLVE_NEW = """def _fb_og_resolve_source(page_type: str, entity_key: str) -> Optional[str]:
    return _fb_og_resolve_local_path(page_type, entity_key)"""

API_OLD = """    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="OG source not found")"""

API_NEW = """    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        path = _fb_url_to_local(_FB_OG_BRAND_URL)"""

CLASS_SPA_OLD = """        _cls_url = _artwork_class_logo_path_for_class_name(class_name)
        _fb_head = _fb_og_head_for("class", canon_tail, seo_title, seo_desc, canonical_url, source_url=_cls_url)"""

CLASS_SPA_NEW = """        _cls_url = _fb_og_class_logo_public_url(canon_tail)
        _fb_head = _fb_og_head_for("class", canon_tail, seo_title, seo_desc, canonical_url, source_url=_cls_url)"""


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched fix7")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_fix7_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    insert_at = "# FB_OG_FIX6_v1\n"
    if insert_at not in text:
        raise SystemExit("FB_OG_FIX6 marker not found")
    text = text.replace(insert_at, insert_at + MARKER + HELPER, 1)

    for name, old, new in (
        ("prepare", PREPARE_OLD, PREPARE_NEW),
        ("resolve", RESOLVE_OLD, RESOLVE_NEW),
        ("api png", API_OLD, API_NEW),
        ("class spa", CLASS_SPA_OLD, CLASS_SPA_NEW),
    ):
        if old not in text:
            raise SystemExit(f"{name} anchor not found")
        text = text.replace(old, new, 1)

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched fix7", API_PATH)


if __name__ == "__main__":
    main()
