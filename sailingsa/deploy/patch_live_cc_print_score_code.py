#!/usr/bin/env python3
"""Cape Classic print/URL: Open title = Fleet; split 20 DNC; small code.

Markers:
  CC_FLEET_OPEN_TITLE_v5
  CC_FLEET_RACE_CODE_SPLIT_v1
  CC_FLEET_RACE_CODE_CSS_v1
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD_TITLE = '''        _cc_logo = ""
        if len(_cc_names) <= 1:
            try:
                _cc_logo = (
                    _catalogue_logo_path_for_class_name(
                        _cc_core or class_canonical or fleet_label
                    )
                    or ""
                ).strip()
                if not _cc_logo and _cc_names:
                    _cc_logo = (
                        _catalogue_logo_path_for_class_name(next(iter(_cc_names))) or ""
                    ).strip()
            except Exception:
                _cc_logo = ""
            try:
                from sailingsa.backend.cape_classic_fleet_sheet import (
                    fleet_header_title_without_class_dup,
                )
                fleet_header_title = fleet_header_title_without_class_dup(
                    fleet_header_title,
                    unique_classes=_cc_names,
                    has_class_logo=bool(_cc_logo),
                )
            except Exception:
                if _cc_logo and _cc_core.casefold() not in ("staff", "event staff", "crew"):
                    fleet_header_title = "Fleet"
'''

NEW_TITLE = '''        _cc_logo = ""
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
        try:
            from sailingsa.backend.cape_classic_fleet_sheet import (
                fleet_header_title_without_class_dup,
            )
            fleet_header_title = fleet_header_title_without_class_dup(
                fleet_header_title,
                unique_classes=_cc_names,
                has_class_logo=bool(_cc_logo),
            )
        except Exception:
            if _cc_logo and _cc_core.casefold() not in ("staff", "event staff", "crew"):
                fleet_header_title = "Fleet"
'''

OLD_CELL = '''                    _inner = (
                        f'<span class="{cell_class}"{_style}>{html_module.escape(score_display)}</span>'
                        if cell_class
                        else html_module.escape(score_display)
                    )
                    # Prefer plain display when no special class (keep previous behaviour)
                    if not cell_class and not _assigned:
                        _inner = html_module.escape(score_display)
'''

NEW_CELL = '''                    _inner = (
                        f'<span class="{cell_class}"{_style}>{html_module.escape(score_display)}</span>'
                        if cell_class
                        else html_module.escape(score_display)
                    )
                    if _is_cape_classic_2026_zvy_event(_rid_ft) and has_penalty:
                        # CC_FLEET_RACE_CODE_SPLIT_v1
                        try:
                            from sailingsa.backend.cape_classic_fleet_sheet import (
                                race_points_and_code_html,
                            )
                            _split = race_points_and_code_html(score_display, cell_class, _style)
                            if _split:
                                _inner = _split
                        except Exception:
                            pass
                    # Prefer plain display when no special class (keep previous behaviour)
                    if not cell_class and not _assigned:
                        _inner = html_module.escape(score_display)
'''

OLD_CSS = '''    ".fleet-title-with-logo{display:inline-flex;align-items:center;gap:6px;flex-wrap:nowrap;max-width:100%}"
    ".fleet-title-with-logo .rs-fleet-title-logo{height:auto;width:auto;max-height:22px;max-width:40px;object-fit:contain;flex:0 0 auto}"
'''

# Compact CSS owns 1.1em Fleet-height. Do not re-inject the 22x40 cap.
NEW_CSS = '''    ".fleet-title-with-logo{display:inline-flex;align-items:center;gap:6px;flex-wrap:nowrap;max-width:100%}"
    ".fleet-title-with-logo .rs-fleet-title-logo{height:1.1em!important;width:auto!important;max-height:1.1em!important;max-width:none!important;object-fit:contain;flex:0 0 auto}"
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if "CC_FLEET_RACE_CODE_SPLIT_v1" in text and "CC_FLEET_OPEN_TITLE_v5" in text:
        print("already patched api.py v5/split")
        return 0
    for name, old, new in (
        ("title", OLD_TITLE, NEW_TITLE),
        ("cell", OLD_CELL, NEW_CELL),
        ("css", OLD_CSS, NEW_CSS),
    ):
        if old not in text:
            raise SystemExit(f"missing block: {name}")
        text = text.replace(old, new, 1)
    if "CC_FLEET_RACE_CODE_SPLIT_v1" not in text or "CC_FLEET_OPEN_TITLE_v5" not in text:
        raise SystemExit("markers failed")
    API.write_text(text, encoding="utf-8")
    print("PATCHED", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
