#!/usr/bin/env python3
"""GOLD fleet title: class logo + word Fleet on all Event URLs (not class-name text)."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD_STRIP = """    if _is_cape_classic_2026_zvy_event(_rid_ft) and not standalone_class_page:
        _cc_names = {
            str(r.get("class_name") or "").strip()
            for r in (fleet.get("rows") or [])
            if str(r.get("class_name") or "").strip()
        }
        _cc_core = re.sub(r"(?i)\\s+fleet$", "", str(fleet_header_title or "")).strip()
        _cc_logo = ""
        try:
            # CC_FLEET_OPEN_TITLE_v5 — mixed Open still uses the Open mark, not a row class.
            for _cand in (_cc_core, class_canonical, fleet_label):
                _cand_s = re.sub(r"(?i)\\s+fleet$", "", str(_cand or "").strip()).strip()
                if not _cand_s:
                    continue
                _cc_logo = (_catalogue_logo_path_for_class_name(_cand_s) or "").strip()
                if _cc_logo:
                    break
        except Exception:
            _cc_logo = ""
"""

NEW_STRIP = """    _cc_logo = ""
    if (not _regatta_is_lipton_challenge(_rid_ft)) and not standalone_class_page:
        _cc_names = {
            str(r.get("class_name") or r.get("class_canonical") or "").strip()
            for r in (fleet.get("rows") or [])
            if str(r.get("class_name") or r.get("class_canonical") or "").strip()
        }
        _cc_core = re.sub(r"(?i)\\s+fleet$", "", str(fleet_header_title or "")).strip()
        try:
            # GOLD: logo is the name. Prefer fleet/title identity (Open mark, Hunter 19).
            # Mixed fleets must not pick a random row class.
            for _cand in (_cc_core, class_canonical, fleet_label, fleet.get("name")):
                _cand_s = re.sub(r"(?i)\\s+fleet$", "", str(_cand or "").strip()).strip()
                if not _cand_s:
                    continue
                _cc_logo = (_catalogue_logo_path_for_class_name(_cand_s) or "").strip()
                if _cc_logo:
                    break
            if not _cc_logo:
                _row_cores = []
                for _n in _cc_names:
                    _cs = re.sub(r"(?i)\\s+fleet$", "", str(_n or "").strip()).strip()
                    if _cs:
                        _row_cores.append(_cs)
                _row_uniq = {x.casefold(): x for x in _row_cores}
                if len(_row_uniq) == 1:
                    _cc_logo = (
                        _catalogue_logo_path_for_class_name(next(iter(_row_uniq.values()))) or ""
                    ).strip()
            if not _cc_logo:
                _cc_logo = (fleet.get("class_logo_path") or "").strip()
            if not _cc_logo and _is_generic_hobie_fleet(fleet):
                _cc_logo = (GENERIC_HOBIE_FLEET_LOGO or "").strip()
        except Exception:
            _cc_logo = ""
"""

OLD_WRAP = """    if _is_cape_classic_2026_zvy_event(_rid_ft):
        # CC_FLEET_CLASS_LOGOS_v4
        # Small copy of the left class logo, beside the Fleet title.
        _title_cn = (class_canonical or fleet_label or "").strip()
        _title_cn = re.sub(r"(?i)\\s+fleet$", "", _title_cn).strip() or _title_cn
        if _title_cn.casefold() not in ("staff", "event staff", "crew", ""):
            _title_logo_u = ""
            try:
                _title_logo_u = (_catalogue_logo_path_for_class_name(_title_cn) or "").strip()
            except Exception:
                _title_logo_u = ""
            if _title_logo_u:
                _timg = _fleet_sheet_artwork_img(
                    _title_logo_u, _title_cn, "rs-fleet-title-logo"
                )
                if _timg:
                    fleet_header_html = (
                        f'<span class="fleet-title-with-logo">{_timg}{fleet_header_html}</span>'
                    )
"""

NEW_WRAP = """    if (not _regatta_is_lipton_challenge(_rid_ft)) and _cc_logo:
        # GOLD: class logo + the word Fleet (not "Hunter 19 Fleet").
        _title_cn = (class_canonical or fleet_label or "").strip()
        _title_cn = re.sub(r"(?i)\\s+fleet$", "", _title_cn).strip() or _title_cn
        if _title_cn.casefold() not in ("staff", "event staff", "crew", ""):
            _timg = _fleet_sheet_artwork_img(
                _cc_logo, _title_cn, "rs-fleet-title-logo"
            )
            if _timg:
                fleet_header_html = (
                    f'<span class="fleet-title-with-logo">{_timg}{fleet_header_html}</span>'
                )
"""


def main() -> None:
    text = API.read_text()
    if 'GOLD: class logo + the word Fleet (not "Hunter 19 Fleet")' in text:
        print("ALREADY")
        return
    missing = []
    if OLD_STRIP not in text:
        missing.append("STRIP")
    if OLD_WRAP not in text:
        missing.append("WRAP")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    text = text.replace(OLD_STRIP, NEW_STRIP, 1)
    text = text.replace(OLD_WRAP, NEW_WRAP, 1)
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.fleet_title_logo.{ts}")
    shutil.copy2(API, bak)
    API.write_text(text)
    print("BACKUP", bak, "PATCHED")


if __name__ == "__main__":
    main()
