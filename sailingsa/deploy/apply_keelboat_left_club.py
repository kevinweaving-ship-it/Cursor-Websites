#!/usr/bin/env python3
"""When a fleet has no class logo (mixed Keelboat), left slot = host club logo."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = """    if not display_url:
        for _fallback in (
            _fleet_cls_lp,
            (fleet.get("class_logo_path") or "").strip() or None,
            _catalogue_logo_path_for_class_name(_fleet_cn) if _fleet_cn else None,
            HUNTER_19_CLASS_LOGO_SSOT if _regatta_is_hbyc_h19_club_series(rid) else None,
        ):
            if _fallback and not _artwork_path_is_club_logo(_fallback):
                display_url = _fallback
                break
    left_col = ""
    right_col = ""
    if display_url:
        src = html_module.escape(_enc_artwork_src(display_url))
        alt = html_module.escape(_fleet_cn or "")
        img = (
            f'<img src="{src}" alt="{alt}" class="class-header-logo-img" '
            f'loading="lazy" decoding="async" />'
        )
        # Class logo left of fleet title → class catalogue (/class/{slug}), not event logos.
        _left_class_slug = (
            _class_slug_without_fleet(_fleet_cn) or _class_canonical_slug(_fleet_cn) if _fleet_cn else ""
        )
        if _left_class_slug and "/artwork/class logo/" in str(display_url).lower():
            cat_href = f"/class/{_left_class_slug}"
            cat_title = html_module.escape(f"Open {_fleet_cn} class page")
        else:
            cat_href = _event_logo_catalogue_href(display_url, rid, _fleet_cn)
            cat_title = html_module.escape(_left_logo_catalogue_link_title(display_url, _fleet_cn))
        img_linked = (
            f'<a href="{html_module.escape(cat_href)}" class="regatta-header-logo-link" title="{cat_title}">{img}</a>'
        )
        left_col = f'<div class="class-header-logo-col">{img_linked}</div>'
    right_logo_url = _wc_regatta_fleet_block_logo_url_right(rid, bid)
    # Right slot = host club flag (same as main regatta header). Never duplicate class logo.
    if right_logo_url and display_url:
        if _norm_artwork_path(right_logo_url) == _norm_artwork_path(display_url):
            right_logo_url = None
"""

NEW = """    if not display_url:
        for _fallback in (
            _fleet_cls_lp,
            (fleet.get("class_logo_path") or "").strip() or None,
            _catalogue_logo_path_for_class_name(_fleet_cn) if _fleet_cn else None,
            HUNTER_19_CLASS_LOGO_SSOT if _regatta_is_hbyc_h19_club_series(rid) else None,
        ):
            if _fallback and not _artwork_path_is_club_logo(_fallback):
                display_url = _fallback
                break
    _left_is_host_club = False
    if not display_url and rid and not _regatta_is_lipton_challenge(rid):
        # Mixed / no-class fleets (Keelboat): left slot = host club logo.
        _host_abbr_left = _wc_regatta_host_club_abbrev_for_regatta(rid)
        if _host_abbr_left:
            _host_src_left = _regatta_host_club_logo_src_for_code(_host_abbr_left)
            if _host_src_left:
                display_url = _host_src_left
                _left_is_host_club = True
    left_col = ""
    right_col = ""
    if display_url:
        src = html_module.escape(_enc_artwork_src(display_url))
        alt = html_module.escape(_fleet_cn or "")
        img = (
            f'<img src="{src}" alt="{alt}" class="class-header-logo-img" '
            f'loading="lazy" decoding="async" />'
        )
        # Class logo left of fleet title → class catalogue (/class/{slug}), not event logos.
        _left_class_slug = (
            _class_slug_without_fleet(_fleet_cn) or _class_canonical_slug(_fleet_cn) if _fleet_cn else ""
        )
        if _left_is_host_club:
            _ab = (_wc_regatta_host_club_abbrev_for_regatta(rid) or "").strip()
            cat_href = f"/club/{_ab.lower()}" if _ab else "/"
            cat_title = html_module.escape(f"Open {_ab} club page") if _ab else ""
        elif _left_class_slug and "/artwork/class logo/" in str(display_url).lower():
            cat_href = f"/class/{_left_class_slug}"
            cat_title = html_module.escape(f"Open {_fleet_cn} class page")
        else:
            cat_href = _event_logo_catalogue_href(display_url, rid, _fleet_cn)
            cat_title = html_module.escape(_left_logo_catalogue_link_title(display_url, _fleet_cn))
        img_linked = (
            f'<a href="{html_module.escape(cat_href)}" class="regatta-header-logo-link" title="{cat_title}">{img}</a>'
        )
        left_col = f'<div class="class-header-logo-col">{img_linked}</div>'
    right_logo_url = _wc_regatta_fleet_block_logo_url_right(rid, bid)
    # Right slot = host club flag (same as main regatta header). Never duplicate class logo.
    if right_logo_url and display_url and not _left_is_host_club:
        if _norm_artwork_path(right_logo_url) == _norm_artwork_path(display_url):
            right_logo_url = None
"""


def main() -> None:
    text = API.read_text()
    if "Mixed / no-class fleets (Keelboat): left slot = host club logo." in text:
        print("ALREADY")
        return
    if OLD not in text:
        raise SystemExit("BLOCK_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.keel_left_club.{ts}")
    shutil.copy2(API, bak)
    API.write_text(text.replace(OLD, NEW, 1))
    print("BACKUP", bak, "PATCHED")


if __name__ == "__main__":
    main()
