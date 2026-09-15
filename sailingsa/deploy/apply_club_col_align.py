#!/usr/bin/env python3
"""Club col: logo left, code right, codes stacked. No extra row height."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
COMPACT = Path("/var/www/sailingsa/sailingsa/backend/regatta_print_compact_css.py")

API_OLD = (
    '    ".fleet-results-table .rs-club-with-logo{'
    "display:inline-flex!important;flex-direction:row!important;"
    "flex-wrap:nowrap!important;align-items:center!important;"
    'gap:4px;max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"'
)
API_NEW = (
    '    ".fleet-results-table .rs-club-with-logo{'
    "display:flex!important;flex-direction:row!important;"
    "flex-wrap:nowrap!important;align-items:center!important;"
    "justify-content:space-between!important;gap:6px;width:100%;"
    'max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"\n'
    '    ".fleet-results-table td.club-col .rs-club-row-logo-sm{'
    "flex:0 0 22px!important;width:22px!important;max-width:22px!important;"
    'object-fit:contain!important}"\n'
    '    ".fleet-results-table td.club-col .rs-club-with-logo>a{'
    'margin-left:auto!important;text-align:right!important}"'
)

API_A_OLD = (
    '    ".fleet-results-table .rs-club-with-logo>a,'
    ".fleet-results-table .rs-club-with-logo>span{"
    'display:inline-block!important;min-width:0;text-align:left;line-height:1.2}"'
)
API_A_NEW = (
    '    ".fleet-results-table .rs-club-with-logo>a{'
    "display:inline-block!important;min-width:0;"
    'margin-left:auto!important;text-align:right;line-height:1.2}"\n'
    '    ".fleet-results-table .rs-club-with-logo>span{'
    'display:inline-block!important;min-width:0;text-align:left;line-height:1.2}"'
)

COMPACT_ANCHOR = "/* Title-row fleet logos: same height as the word Fleet."
COMPACT_INSERT = """/* Club col: logo left, code right so codes stack. */
.fleet-results-table.rs-compact-row-logos td.club-col {
  text-align: left !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo {
  display: flex !important;
  width: 100% !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 6px !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-row-logo-sm {
  flex: 0 0 22px !important;
  width: 22px !important;
  max-width: 22px !important;
  object-fit: contain !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
  margin-left: auto !important;
  text-align: right !important;
}
"""

PRINT_OLD = """  .rs-class-with-logo, .fleet-results-table.rs-compact-row-logos .rs-club-with-logo {
    display: inline-flex !important;
    align-items: center !important;
    gap: 2px !important;
    flex-wrap: nowrap !important;
  }"""
PRINT_NEW = """  .rs-class-with-logo {
    display: inline-flex !important;
    align-items: center !important;
    gap: 2px !important;
    flex-wrap: nowrap !important;
  }
  .fleet-results-table.rs-compact-row-logos .rs-club-with-logo {
    display: flex !important;
    width: 100% !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 6px !important;
    flex-wrap: nowrap !important;
  }
  .fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
    margin-left: auto !important;
    text-align: right !important;
  }"""


def main() -> None:
    api = API.read_text()
    if "td.club-col .rs-club-with-logo>a{margin-left:auto" in api.replace(" ", ""):
        print("API_ALREADY")
    else:
        if API_OLD not in api:
            raise SystemExit("API_CLUB_FLEX_MISSING")
        api = api.replace(API_OLD, API_NEW, 1)
        if API_A_OLD in api:
            api = api.replace(API_A_OLD, API_A_NEW, 1)
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = API.with_name(f"api.py.bak.club_align.{ts}")
        shutil.copy2(API, bak)
        API.write_text(api)
        print("API_PATCHED", bak)

    c = COMPACT.read_text()
    if "Club col: logo left, code right so codes stack" in c:
        print("COMPACT_ALREADY")
        return
    if COMPACT_ANCHOR not in c:
        raise SystemExit("COMPACT_ANCHOR_MISSING")
    c = c.replace(COMPACT_ANCHOR, COMPACT_INSERT + COMPACT_ANCHOR, 1)
    if PRINT_OLD in c:
        c = c.replace(PRINT_OLD, PRINT_NEW)
        print("PRINT_PATCHED")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = COMPACT.with_name(f"regatta_print_compact_css.py.bak.{ts}")
    shutil.copy2(COMPACT, bak)
    COMPACT.write_text(c)
    print("COMPACT_PATCHED", bak)


if __name__ == "__main__":
    main()
