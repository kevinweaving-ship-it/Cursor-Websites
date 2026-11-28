#!/usr/bin/env python3
"""Surgical Facebook OG patch for LIVE api.py — never replace whole file."""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "# FB_OG_PATCH_v1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
OG_MODULE_SRC = Path(__file__).resolve().parent / "facebook_og.py"
OG_MODULE_DST = API_PATH.parent / "facebook_og.py"

INSERT_BLOCK = '''
# FB_OG_PATCH_v1 — Facebook Open Graph 1200x630 cards (do not remove marker)
def _fb_og_cache_dir() -> str:
    d = os.path.join(WEB_ROOT, "media", "og")
    os.makedirs(d, exist_ok=True)
    return d


def _fb_url_to_local(url: Optional[str]) -> Optional[str]:
    import facebook_og as _fb
    return _fb.url_to_local_path(
        url or "",
        static_dir=STATIC_DIR,
        base_dir=BASE_DIR,
        club_logo_resolver=_club_logo_disk_path,
    )


def _fb_og_regatta_left_url(regatta_id: str, regatta_name: Optional[str] = None) -> Optional[str]:
    lu, _ru = _wc_regatta_header_icon_urls(str(regatta_id), regatta_name)
    if not lu:
        try:
            lu = _regatta_main_header_left_class_logo_url(str(regatta_id))
        except Exception:
            lu = None
    if not lu and regatta_id:
        cat_lu, _cat_href = _catalogue_regatta_left_logo(str(regatta_id), regatta_name)
        lu = cat_lu or None
    if lu:
        lu = _public_artwork_url(lu) or lu
    return (lu or None)


def _fb_og_sailor_avatar_local(sas_id: str, full_name: str) -> Optional[str]:
    parts = (full_name or "").strip().split(None, 1)
    fn = parts[0] if parts else ""
    ln = parts[1] if len(parts) > 1 else ""
    av = _users_avatar_url(str(sas_id or "").strip(), fn, ln, full_name or "")
    return _fb_url_to_local(av)


def _fb_og_events_logo_url(slug: str) -> Optional[str]:
    try:
        d = _events_logos_gallery_deps()
        elg = d.pop("elg")
        row = elg.row_by_slug(slug, **d)
        if row and row.get("path"):
            return str(row["path"]).strip() or None
    except Exception as e:
        print(f"[_fb_og_events_logo_url] {e}", flush=True)
    return None


def _fb_og_sponsor_logo_url(slug: str) -> Optional[str]:
    if (slug or "").strip().lower() in ("index", ""):
        try:
            d = _sponsor_profiles_deps()
            sp = d.pop("sp")
            items = sp._sponsor_index_items() or []
            for item in items or []:
                lp = (item.get("logo_path") or "").strip()
                if lp:
                    return lp
        except Exception as e:
            print(f"[_fb_og_sponsor_logo_url index] {e}", flush=True)
        return None
    try:
        d = _sponsor_profiles_deps()
        sp = d.pop("sp")
        prof = sp._profile_for_page(
            slug,
            get_db_connection=d["get_db_connection"],
            return_db_connection=d["return_db_connection"],
            table_exists=d["table_exists"],
        )
        if prof:
            lp = (prof.get("logo_path") or "").strip()
            if lp:
                return lp
    except Exception as e:
        print(f"[_fb_og_sponsor_logo_url] {e}", flush=True)
    return None


def _fb_og_prepare(
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
    _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path)
    fp = _fb.source_fingerprint(path)
    return _fb.build_og_image_url(_canonical_base_url(), page_type, entity_key, fp)


def _fb_og_head_for(
    page_type: str,
    entity_key: str,
    title: str,
    description: str,
    canonical_url: str,
    *,
    og_type: str = "website",
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
) -> str:
    import facebook_og as _fb
    img = _fb_og_prepare(
        page_type,
        entity_key,
        source_url=source_url,
        source_path=source_path,
    )
    return _fb.render_facebook_head(
        title=title,
        description=description,
        canonical_url=canonical_url,
        og_image_url=img or "",
        og_type=og_type,
    )


def _fb_og_resolve_source(page_type: str, entity_key: str) -> Optional[str]:
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
    return None


@app.get("/api/og/{page_type}/{entity_key}.png")
def api_facebook_og_image(page_type: str, entity_key: str, v: Optional[str] = None):
    import facebook_og as _fb
    path = _fb_og_resolve_source(page_type, entity_key)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="OG source not found")
    out = _fb.cache_og_png(_fb_og_cache_dir(), page_type, entity_key, path)
    headers = {"Cache-Control": "public, max-age=86400"}
    return FileResponse(out, media_type="image/png", headers=headers)

'''


def main() -> None:
    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")
    if OG_MODULE_SRC.resolve() != OG_MODULE_DST.resolve():
        shutil.copy2(OG_MODULE_SRC, OG_MODULE_DST)
    text = API_PATH.read_text(encoding="utf-8", errors="replace")
    if MARKER in text:
        print("OK already patched")
        return
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = API_PATH.with_suffix(f".py.bak_fb_og_{ts}")
    shutil.copy2(API_PATH, bak)
    print(f"Backup: {bak}")

    anchor = "    return b\n\n\n@app.middleware(\"http\")\nasync def _canonical_redirect_middleware"
    if anchor not in text:
        raise SystemExit("anchor for insert block not found")
    text = text.replace(anchor, "    return b\n\n" + INSERT_BLOCK + "\n@app.middleware(\"http\")\nasync def _canonical_redirect_middleware", 1)

    # Club page — compute FB head before doc tuple; replace raw club-logo og:image
    club_pre_doc = (
        '    doc = (\n'
        '        "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"\n'
        '        f"{club_heading_html} | SailingSA</title>"\n'
        '        "<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"'
    )
    club_pre_doc_new = (
        '    _fb_club_title = ((ca + " - " + cn) if (ca and cn and ca.lower() != cn.lower()) else (cn or ca or "Club")) + " | SailingSA"\n'
        '    _fb_club_desc = "Sailing club: " + (cn or ca or "Club") + ". Sailors and regattas on SailingSA."\n'
        '    _fb_club_head = _fb_og_head_for("club", slug, _fb_club_title, _fb_club_desc, canonical_url, source_path=_club_logo_disk_path((ca or "").strip()))\n'
        '    doc = (\n'
        '        "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"\n'
        '        f"{club_heading_html} | SailingSA</title>"\n'
        '        "<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"'
    )
    if club_pre_doc not in text:
        raise SystemExit("club pre-doc anchor not found")
    text = text.replace(club_pre_doc, club_pre_doc_new, 1)

    old_club = (
        'f"<meta name=\\"description\\" content=\\"Sailing club: {html_module.escape(cn or ca or \'Club\')}. Sailors and regattas.\\">"\n'
        '        f"<link rel=\\"canonical\\" href=\\"{html_module.escape(canonical_url)}\\">"\n'
        '        f"<meta property=\\"og:type\\" content=\\"website\\">"\n'
        '        f"<meta property=\\"og:url\\" content=\\"{html_module.escape(canonical_url)}\\">"\n'
        '        f"<meta property=\\"og:title\\" content=\\"{html_module.escape((ca + \' - \' + cn) if (ca and cn and ca.lower() != cn.lower()) else (cn or ca or \'Club\'))} | SailingSA\\">"\n'
        '        f"<meta property=\\"og:description\\" content=\\"Sailing club: {html_module.escape(cn or ca or \'Club\')}. Sailors and regattas on SailingSA.\\">"\n'
        '        f"<meta property=\\"og:image\\" content=\\"https://sailingsa.co.za/api/club-logo/{html_module.escape((ca or slug or \'\').strip())}\\">"\n'
        '        f"<meta name=\\"twitter:card\\" content=\\"summary\\">"\n'
        '        "<link rel=\\"icon\\"'
    )
    new_club = (
        '+ _fb_club_head +\n'
        '        "<link rel=\\"icon\\"'
    )
    if old_club not in text:
        raise SystemExit("club og block not found")
    text = text.replace(old_club, new_club, 1)

    # Regatta class standalone (before regatta standalone in file)
    regatta_class_old = (
        '        doc = (\n'
        '            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"\n'
        '            f"{html_module.escape(class_name)} – {escaped_title} | SailingSA</title>"\n'
        '            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"\n'
        '            f"<link rel=\\"canonical\\" href=\\"{html_module.escape(canonical_url)}\\">"\n'
        '            "<link rel=\\"icon\\"'
    )
    regatta_class_new = (
        '        doc = (\n'
        '            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"\n'
        '            f"{html_module.escape(class_name)} – {escaped_title} | SailingSA</title>"\n'
        '            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"\n'
        '            + _fb_og_head_for("regatta", str(regatta_id), f"{html_module.escape(class_name)} – {escaped_title} | SailingSA", f"Regatta results: {escaped_title} — {html_module.escape(class_name)}.", canonical_url, source_url=_fb_og_regatta_left_url(str(regatta_id), event_name))\n'
        '            + "<link rel=\\"icon\\"'
    )
    if regatta_class_old not in text:
        raise SystemExit("regatta class head anchor not found")
    text = text.replace(regatta_class_old, regatta_class_new, 1)

    # Regatta standalone doc head
    regatta_doc_old = (
        '        doc = (\n'
        '            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"\n'
        '            f"{escaped_title} | SailingSA</title>"\n'
        '            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"\n'
        '            f"<link rel=\\"canonical\\" href=\\"{html_module.escape(canonical_url)}\\">"\n'
        '            "<link rel=\\"icon\\"'
    )
    regatta_doc_new = (
        '        doc = (\n'
        '            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"\n'
        '            f"{escaped_title} | SailingSA</title>"\n'
        '            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"\n'
        '            + _fb_og_head_for("regatta", str(canonical_slug), f"{escaped_title} | SailingSA", f"Regatta results: {escaped_title}.", canonical_url, source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name))\n'
        '            + "<link rel=\\"icon\\"'
    )
    if regatta_doc_old not in text:
        raise SystemExit("regatta head anchor not found")
    text = text.replace(regatta_doc_old, regatta_doc_new, 1)

    # Directory pages
    text = text.replace(
        '<title>""" + html_module.escape(page_title) + """</title>\n<link rel="canonical" href="https://sailingsa.co.za""" + html_module.escape(title) + """">',
        '<title>""" + html_module.escape(page_title) + """</title>\n""" + _fb_og_head_for("directory", href_key, html_module.escape(page_title) + " | SailingSA", html_module.escape(about_text or page_title + " on SailingSA."), _canonical_base_url() + html_module.escape(title), source_url="/assets/logos/sailingsa-logo.png") + """',
        1,
    )

    # Sailor SPA
    sailor_inj = (
        '        html = re.sub(\n'
        '            r\'<link\\s+rel="canonical"\\s+href="[^"]*"\\s*/?>\',\n'
        '            f\'<link rel="canonical" href="{html_module.escape(f"{base_url}/sailor/{canonical_slug}")}">\',\n'
        '            html,\n'
        '            count=1,\n'
        '        )\n'
        '        return HTMLResponse(html)'
    )
    sailor_new = (
        '        html = re.sub(\n'
        '            r\'<link\\s+rel="canonical"\\s+href="[^"]*"\\s*/?>\',\n'
        '            f\'<link rel="canonical" href="{html_module.escape(f"{base_url}/sailor/{canonical_slug}")}">\',\n'
        '            html,\n'
        '            count=1,\n'
        '        )\n'
        '        import facebook_og as _fb\n'
        '        _sas_fb = _get_sailor_sas_id_from_slug(canonical_slug)\n'
        '        _fb_head = _fb_og_head_for("sailor", canonical_slug, f"{escaped_name} | SailingSA", f"Official SailingSA profile for {escaped_name}. Results, rankings and regattas.", f"{base_url}/sailor/{canonical_slug}", og_type="profile", source_path=_fb_og_sailor_avatar_local(_sas_fb, name) if _sas_fb else None)\n'
        '        html = _fb.inject_facebook_head(html, _fb_head)\n'
        '        return HTMLResponse(html)'
    )
    if sailor_inj not in text:
        raise SystemExit("sailor inject anchor not found")
    text = text.replace(sailor_inj, sailor_new, 1)

    # Class SPA
    class_inj = (
        '        html = _dedupe_html_canonical_links(html)\n'
        '        return HTMLResponse(html)\n'
        '    except HTTPException:\n'
        '        raise\n'
        '    except Exception as e:\n'
        '        print(f"[serve_class_spa] {e}", flush=True)'
    )
    class_new = (
        '        html = _dedupe_html_canonical_links(html)\n'
        '        import facebook_og as _fb\n'
        '        _cls_url = _artwork_class_logo_path_for_class_name(class_name)\n'
        '        _fb_head = _fb_og_head_for("class", canon_tail, seo_title, seo_desc, canonical_url, source_url=_cls_url)\n'
        '        html = _fb.inject_facebook_head(html, _fb_head)\n'
        '        return HTMLResponse(html)\n'
        '    except HTTPException:\n'
        '        raise\n'
        '    except Exception as e:\n'
        '        print(f"[serve_class_spa] {e}", flush=True)'
    )
    if class_inj not in text:
        raise SystemExit("class inject anchor not found")
    text = text.replace(class_inj, class_new, 1)

    # Home / temp landing
    home_inj = (
        '    html = re.sub(\n'
        '        r"function showSailorProfilePlaceholder\\(\\)",\n'
        '        "function showSailorProfilePlaceholder()",\n'
        '        html,\n'
        '        count=1,\n'
        '        flags=re.I,\n'
        '    )\n'
    )
    # Find return after _temp_landing_duplicate modifications
    home_anchor = '    return HTMLResponse(content=html, headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"})\n\n\n@app.get("/api/stats")'
    if home_anchor not in text:
        raise SystemExit("home landing anchor not found")
    text = text.replace(
        home_anchor,
        '    import facebook_og as _fb\n'
        '    _fb_head = _fb_og_head_for("home", "site", "South African Sailing Results & Regatta Database | SailingSA", "Search South African sailing results, regatta results, sailor profiles, and class standings.", _canonical_base_url() + "/", source_url="/assets/logos/sailingsa-logo.png")\n'
        '    html = _fb.inject_facebook_head(html, _fb_head)\n'
        '    return HTMLResponse(content=html, headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"})\n\n\n@app.get("/api/stats")',
        1,
    )

    text = text.replace(
        "extra_head = (\n        '<link rel=\"canonical\" href=\"https://sailingsa.co.za/clubs\">'\n        \"<style>\" + _directory_logo_grid_extra_css() + \"</style>\"\n    )",
        "extra_head = (\n        '<link rel=\"canonical\" href=\"https://sailingsa.co.za/clubs\">'\n        + _fb_og_head_for('directory', 'clubs', 'Clubs | SailingSA', about, _canonical_base_url() + '/clubs', source_url='/assets/logos/sailingsa-logo.png')\n        + \"<style>\" + _directory_logo_grid_extra_css() + \"</style>\"\n    )",
        1,
    )

    text = text.replace(
        "extra_head = (\n                '<link rel=\"canonical\" href=\"https://sailingsa.co.za/classes\">'\n                \"<style>\" + _directory_logo_grid_extra_css() + ccd.classes_directory_extra_css() + \"</style>\"\n            )",
        "extra_head = (\n                '<link rel=\"canonical\" href=\"https://sailingsa.co.za/classes\">'\n                + _fb_og_head_for('directory', 'classes', 'Classes | SailingSA', about, _canonical_base_url() + '/classes', source_url='/assets/logos/sailingsa-logo.png')\n                + \"<style>\" + _directory_logo_grid_extra_css() + ccd.classes_directory_extra_css() + \"</style>\"\n            )",
        1,
    )

    # Events-logos gallery
    text = text.replace(
        "extra_head = (\n            '<link rel=\"canonical\" href=\"https://sailingsa.co.za/events-logos\">'\n            \"<style>\" + _directory_logo_grid_extra_css() + elg.gallery_extra_css() + \"</style>\"\n        )",
        "extra_head = (\n            '<link rel=\"canonical\" href=\"https://sailingsa.co.za/events-logos\">'\n            + _fb_og_head_for('events_logos', 'index', 'Named Events | SailingSA', 'Named event logos and regatta series on SailingSA.', _canonical_base_url() + '/events-logos', source_url='/assets/logos/sailingsa-logo.png')\n            + \"<style>\" + _directory_logo_grid_extra_css() + elg.gallery_extra_css() + \"</style>\"\n        )",
        1,
    )

    # Events-logo detail
    text = text.replace(
        "extra_head = (\n            f'<link rel=\"canonical\" href=\"https://sailingsa.co.za{html_module.escape(canonical_path)}\">'\n            f\"<style>{elg.detail_extra_css()}</style>\"\n        )",
        "extra_head = (\n            _fb_og_head_for('events_logos', slug, title, f'Named event: {title.split(\" | \")[0]}. Regattas and hosts on SailingSA.', _canonical_base_url() + canonical_path, source_url=_fb_og_events_logo_url(slug))\n            + f\"<style>{elg.detail_extra_css()}</style>\"\n        )",
        1,
    )

    # Sponsors index — inject after body returned (first sponsors_index_page only)
    sp_idx_old = (
        '        status_code, body = sp.sponsors_index_html(\n'
        '            canonical_base_url=d.pop("canonical_base_url")(),\n'
        '            **d,\n'
        '        )\n'
        '        return HTMLResponse(body, status_code=status_code)'
    )
    sp_idx_new = (
        '        status_code, body = sp.sponsors_index_html(\n'
        '            canonical_base_url=d.pop("canonical_base_url")(),\n'
        '            **d,\n'
        '        )\n'
        '        import facebook_og as _fb\n'
        '        _cb = _canonical_base_url()\n'
        '        _fb_head = _fb_og_head_for("sponsor", "index", "Sponsors | SailingSA", "Headline and tier sponsors on SailingSA.", _cb + "/sponsors", source_url=_fb_og_sponsor_logo_url("index"))\n'
        '        body = _fb.inject_facebook_head(body, _fb_head)\n'
        '        return HTMLResponse(body, status_code=status_code)'
    )
    if text.count(sp_idx_old) < 1:
        raise SystemExit("sponsors index anchor not found")
    text = text.replace(sp_idx_old, sp_idx_new, 1)

    # Sponsor detail — first occurrence
    sp_det_old = (
        '        status_code, body = sp.page_html(\n'
        '            slug=slug,\n'
        '            is_super_admin=_session_role_is_super_admin(request),\n'
        '            canonical_base_url=d.pop("canonical_base_url")(),\n'
        '            **d,\n'
        '        )\n'
        '        return HTMLResponse(body, status_code=status_code)'
    )
    sp_det_new = (
        '        status_code, body = sp.page_html(\n'
        '            slug=slug,\n'
        '            is_super_admin=_session_role_is_super_admin(request),\n'
        '            canonical_base_url=d.pop("canonical_base_url")(),\n'
        '            **d,\n'
        '        )\n'
        '        import facebook_og as _fb\n'
        '        _cb = _canonical_base_url()\n'
        '        _fb_head = _fb_og_head_for("sponsor", slug, f"Sponsor | SailingSA", f"Sponsor profile on SailingSA.", _cb + "/sponsors/" + slug.strip("/"), source_url=_fb_og_sponsor_logo_url(slug))\n'
        '        body = _fb.inject_facebook_head(body, _fb_head)\n'
        '        return HTMLResponse(body, status_code=status_code)'
    )
    if text.count(sp_det_old) < 1:
        raise SystemExit("sponsor detail anchor not found")
    text = text.replace(sp_det_old, sp_det_new, 1)

    API_PATH.write_text(text, encoding="utf-8")
    print("OK patched", API_PATH)


if __name__ == "__main__":
    main()
