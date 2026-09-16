#!/usr/bin/env python3
"""Keep Event header date+time on one line (no wrap on mobile)."""
from pathlib import Path
import shutil
import time

SHEET = Path("/var/www/sailingsa/sailingsa/backend/cape_classic_fleet_sheet.py")
API = Path("/var/www/sailingsa/api/api.py")

OLD_RET = """    rest = re.sub(r"\\s+at\\s+", " ", rest, flags=re.I).strip()
    return (
        f'<div class="status-line">{head}</div>'
        f'<div class="status-line">{rest}</div>'
    )
"""

NEW_RET = """    rest = re.sub(r"\\s+at\\s+", " ", rest, flags=re.I).strip()
    # Date + time stay on one line (nbsp between tokens; no wrap on a narrow phone).
    rest = re.sub(r"\\s+", "\\u00a0", rest)
    return (
        f'<div class="status-line">{head}</div>'
        f'<div class="status-line status-line--asat">'
        f'<span class="regatta-status-as-at-date">{rest}</span></div>'
    )
"""

OLD_CSS = '    ".regatta-header-status-stack .entry-total-line{margin-top:14px}"'
NEW_CSS = (
    '    ".regatta-header-status-stack .entry-total-line{margin-top:14px}"\n'
    '    ".header:not(.header--lipton) .status-line--asat,'
    '.header:not(.header--lipton) .regatta-status-as-at-date{'
    'white-space:nowrap!important;display:inline!important}"'
)


def main() -> None:
    sheet = SHEET.read_text()
    api = API.read_text()
    if "status-line--asat" in sheet and "status-line--asat" in api:
        print("ALREADY")
        return
    if OLD_RET not in sheet:
        raise SystemExit("SHEET_MISSING")
    if OLD_CSS not in api:
        raise SystemExit("CSS_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(SHEET, SHEET.with_name(f"cape_classic_fleet_sheet.py.bak.asat_nowrap.{ts}"))
    shutil.copy2(API, API.with_name(f"api.py.bak.asat_nowrap.{ts}"))
    SHEET.write_text(sheet.replace(OLD_RET, NEW_RET, 1))
    API.write_text(api.replace(OLD_CSS, NEW_CSS, 1))
    print("PATCHED")


if __name__ == "__main__":
    main()
