#!/usr/bin/env python3
"""Fleet Club column: logo left, code right, codes share one start edge. No table box growth."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

OLD_HTML = (
    '    """Club code/link + club logo immediately to the right."""\n'
    "    code = _fleet_sheet_club_logo_code(club_raw)\n"
    '    logo_u = _club_logo_public_url(code) if code else ""\n'
    "    if not club_link_html:\n"
    '        return ""\n'
    "    if not logo_u:\n"
    "        return club_link_html\n"
    '    img = _fleet_sheet_artwork_img(logo_u, code, "rs-club-row-logo")\n'
    "    if not img:\n"
    "        return club_link_html\n"
    '    return f\'<span class="rs-club-with-logo">{club_link_html}{img}</span>\'\n'
)
NEW_HTML = (
    '    """Club logo left, club code right. Codes share one start edge."""\n'
    "    code = _fleet_sheet_club_logo_code(club_raw)\n"
    '    logo_u = _club_logo_public_url(code) if code else ""\n'
    "    if not club_link_html:\n"
    '        return ""\n'
    "    if not logo_u:\n"
    "        return club_link_html\n"
    '    img = _fleet_sheet_artwork_img(logo_u, code, "rs-club-row-logo")\n'
    "    if not img:\n"
    "        return club_link_html\n"
    '    return f\'<span class="rs-club-with-logo">{img}{club_link_html}</span>\'\n'
)

OLD_CSS1 = (
    '".fleet-results-table .rs-club-with-logo{display:inline-flex!important;flex-direction:row!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px;max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"\n'
    '    ".fleet-results-table .rs-club-row-logo{display:inline-block!important;height:auto!important;width:auto!important;max-height:20px!important;max-width:36px!important;object-fit:contain!important;vertical-align:middle;flex:0 0 auto!important}"'
)
NEW_CSS1 = (
    '".fleet-results-table .rs-club-with-logo{display:inline-flex!important;flex-direction:row!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px;max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"\n'
    '    ".fleet-results-table .rs-club-row-logo{display:block!important;height:20px!important;width:36px!important;max-height:20px!important;max-width:36px!important;object-fit:contain!important;object-position:center!important;vertical-align:middle;flex:0 0 36px!important}"\n'
    '    ".fleet-results-table .rs-club-with-logo>a,.fleet-results-table .rs-club-with-logo>span{display:inline-block!important;min-width:0;text-align:left;line-height:1.2}"'
)

OLD_CSS2 = (
    '".fleet-results-table .rs-club-with-logo{display:inline-flex!important;flex-wrap:nowrap!important;align-items:center!important;white-space:nowrap!important}"\n'
    '    ".fleet-results-table .rs-club-row-logo{height:auto!important;max-height:22.8px!important;max-width:40px!important;display:inline-block!important}"'
)
NEW_CSS2 = (
    '".fleet-results-table .rs-club-with-logo{display:inline-flex!important;flex-direction:row!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px;white-space:nowrap!important}"\n'
    '    ".fleet-results-table .rs-club-row-logo{height:22.8px!important;width:40px!important;max-height:22.8px!important;max-width:40px!important;object-fit:contain!important;object-position:center!important;display:block!important;flex:0 0 40px!important}"\n'
    '    ".fleet-results-table .rs-club-with-logo>a,.fleet-results-table .rs-club-with-logo>span{display:inline-block!important;min-width:0;text-align:left}"'
)

OLD_IMG = (
    '            \'style="height:auto;width:auto;max-height:20px;max-width:36px;\'\n'
    '            \'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto" \'\n'
)
NEW_IMG = (
    '            \'style="height:20px;width:36px;max-height:20px;max-width:36px;\'\n'
    '            \'object-fit:contain;object-position:center;display:block;vertical-align:middle;flex:0 0 36px" \'\n'
)


def apply(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    for label, old in [
        ("html", OLD_HTML),
        ("css1", OLD_CSS1),
        ("css2", OLD_CSS2),
        ("img", OLD_IMG),
    ]:
        c = t.count(old)
        if c != 1:
            raise SystemExit(f"{path}: {label} count {c}")
    t = (
        t.replace(OLD_HTML, NEW_HTML, 1)
        .replace(OLD_CSS1, NEW_CSS1, 1)
        .replace(OLD_CSS2, NEW_CSS2, 1)
        .replace(OLD_IMG, NEW_IMG, 1)
    )
    path.write_text(t, encoding="utf-8")
    print("patched", path)


if __name__ == "__main__":
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
