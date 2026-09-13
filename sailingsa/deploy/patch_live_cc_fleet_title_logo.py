#!/usr/bin/env python3
"""Cape Classic URL: small class logo beside the Fleet title.

Marker: CC_FLEET_CLASS_LOGOS_v4
Large left header logo stays. Title row gets a small copy of the same logo.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "CC_FLEET_CLASS_LOGOS_v4"

OLD_ART = """    elif css in ("rs-club-row-logo-sm", "rs-class-row-logo"):
        # Compact cap — never a fixed height that expands the rank row.
        _img_style = (
            'style="height:auto;width:auto;max-height:16px;max-width:28px;'
            'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto" '
        )
"""

NEW_ART = """    elif css in ("rs-club-row-logo-sm", "rs-class-row-logo"):
        # Compact cap — never a fixed height that expands the rank row.
        _img_style = (
            'style="height:auto;width:auto;max-height:16px;max-width:28px;'
            'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto" '
        )
    elif css == "rs-fleet-title-logo":
        # Size comes from CSS (1.1em = Fleet word). Do not cap width here.
        _img_style = (
            'style="object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto" '
        )
"""

OLD_HDR = """    else:
        fleet_header_html = fleet_header_title
    rows = list(fleet.get("rows") or [])
"""

NEW_HDR = """    else:
        fleet_header_html = fleet_header_title
    if _is_cape_classic_2026_zvy_event(_rid_ft):
        # """ + MARKER + """
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
    rows = list(fleet.get("rows") or [])
"""

OLD_CSS = """    ".fleet-results-table td.class-col{white-space:nowrap;overflow:visible}"
"""

NEW_CSS = """    ".fleet-results-table td.class-col{white-space:nowrap;overflow:visible}"
    ".fleet-title-with-logo{display:inline-flex;align-items:center;gap:6px;flex-wrap:nowrap;max-width:100%}"
    ".fleet-title-with-logo .rs-fleet-title-logo{height:1.1em!important;width:auto!important;max-height:1.1em!important;max-width:none!important;object-fit:contain;flex:0 0 auto}"
"""


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched v4")
        return 0
    for name, old, new in (
        ("art", OLD_ART, NEW_ART),
        ("hdr", OLD_HDR, NEW_HDR),
        ("css", OLD_CSS, NEW_CSS),
    ):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name} count={n}")
        text = text.replace(old, new, 1)
        print("replaced", name)
    if MARKER not in text:
        raise SystemExit("v4 marker failed")
    API.write_text(text, encoding="utf-8")
    print("PATCHED", API, "bytes", API.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
