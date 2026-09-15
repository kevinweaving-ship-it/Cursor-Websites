#!/usr/bin/env python3
"""Club: logo, small space, codes start in one column. Shrink club col. No stretch gap."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
COMPACT = Path("/var/www/sailingsa/sailingsa/backend/regatta_print_compact_css.py")

COMPACT_OLD = """/* Club col: logo left, space, code starts — codes align. Column shrinks to content. */
.fleet-results-table.rs-compact-row-logos td.club-col,
.fleet-results-table.rs-compact-row-logos th.club-col {
  text-align: left !important;
  width: auto !important;
  max-width: none !important;
  white-space: nowrap !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo {
  display: inline-flex !important;
  width: auto !important;
  justify-content: flex-start !important;
  align-items: center !important;
  gap: 4px !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-row-logo-sm {
  flex: 0 0 22px !important;
  width: 22px !important;
  max-width: 22px !important;
  object-fit: contain !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
  margin-left: 0 !important;
  text-align: left !important;
}
"""

COMPACT_NEW = """/* Club col: logo | light rule | code. Codes start in one column. Col shrinks. */
.fleet-results-table.rs-compact-row-logos td.club-col,
.fleet-results-table.rs-compact-row-logos th.club-col {
  text-align: left !important;
  width: auto !important;
  max-width: none !important;
  white-space: nowrap !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo {
  display: inline-flex !important;
  width: auto !important;
  justify-content: flex-start !important;
  align-items: center !important;
  gap: 0 !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-row-logo-sm {
  flex: 0 0 22px !important;
  width: 22px !important;
  max-width: 22px !important;
  object-fit: contain !important;
  box-sizing: content-box !important;
  padding-right: 4px !important;
  margin-right: 4px !important;
  border-right: 1px solid rgba(26, 39, 80, 0.22) !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
  margin-left: 0 !important;
  text-align: left !important;
}
"""

PRINT_CLUB_WIDE = """  .fleet-results-table.rs-compact-row-logos .club-col {
    width: 7.2% !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-align: left !important;
  }"""
PRINT_CLUB_TIGHT = """  .fleet-results-table.rs-compact-row-logos .club-col {
    width: auto !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-align: left !important;
  }"""

PRINT_CLUB_PCT = "  .club-col { width: 4.2% !important; }"
PRINT_CLUB_AUTO = "  .club-col { width: auto !important; white-space: nowrap !important; }"

PRINT_FLEX_OLD = """  .fleet-results-table.rs-compact-row-logos .rs-club-with-logo {
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
PRINT_FLEX_NEW = """  .fleet-results-table.rs-compact-row-logos .rs-club-with-logo {
    display: inline-flex !important;
    width: auto !important;
    justify-content: flex-start !important;
    align-items: center !important;
    gap: 4px !important;
    flex-wrap: nowrap !important;
  }
  .fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
    margin-left: 0 !important;
    text-align: left !important;
  }"""

API_OLD = (
    '    ".fleet-results-table .rs-club-with-logo{'
    "display:inline-flex!important;flex-direction:row!important;"
    "flex-wrap:nowrap!important;align-items:center!important;"
    "justify-content:flex-start!important;gap:4px;width:auto;"
    'max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"\n'
    '    ".fleet-results-table td.club-col .rs-club-row-logo-sm{'
    "flex:0 0 22px!important;width:22px!important;max-width:22px!important;"
    'object-fit:contain!important}"\n'
    '    ".fleet-results-table td.club-col .rs-club-with-logo>a{'
    'margin-left:0!important;text-align:left!important}"'
)
API_NEW = (
    '    ".fleet-results-table .rs-club-with-logo{'
    "display:inline-flex!important;flex-direction:row!important;"
    "flex-wrap:nowrap!important;align-items:center!important;"
    "justify-content:flex-start!important;gap:0;width:auto;"
    'max-width:100%;white-space:nowrap!important;line-height:1.2;overflow:visible}"\n'
    '    ".fleet-results-table td.club-col .rs-club-row-logo-sm{'
    "flex:0 0 22px!important;width:22px!important;max-width:22px!important;"
    "object-fit:contain!important;box-sizing:content-box!important;"
    "padding-right:4px!important;margin-right:4px!important;"
    'border-right:1px solid rgba(26,39,80,0.22)!important}"\n'
    '    ".fleet-results-table td.club-col .rs-club-with-logo>a{'
    'margin-left:0!important;text-align:left!important}"'
)

API_A_OLD = (
    '    ".fleet-results-table .rs-club-with-logo>a{'
    "display:inline-block!important;min-width:0;"
    'margin-left:auto!important;text-align:right;line-height:1.2}"'
)
API_A_NEW = (
    '    ".fleet-results-table .rs-club-with-logo>a{'
    "display:inline-block!important;min-width:0;"
    'margin-left:0!important;text-align:left;line-height:1.2}"'
)


def main() -> None:
    c = COMPACT.read_text()
    if "light rule | code" in c:
        print("COMPACT_ALREADY")
    else:
        if COMPACT_OLD not in c:
            raise SystemExit("COMPACT_BLOCK_MISSING")
        c = c.replace(COMPACT_OLD, COMPACT_NEW, 1)
        if PRINT_CLUB_WIDE in c:
            c = c.replace(PRINT_CLUB_WIDE, PRINT_CLUB_TIGHT)
        if PRINT_CLUB_PCT in c:
            c = c.replace(PRINT_CLUB_PCT, PRINT_CLUB_AUTO)
        if PRINT_FLEX_OLD in c:
            c = c.replace(PRINT_FLEX_OLD, PRINT_FLEX_NEW)
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = COMPACT.with_name(f"regatta_print_compact_css.py.bak.{ts}")
        shutil.copy2(COMPACT, bak)
        COMPACT.write_text(c)
        print("COMPACT_PATCHED", bak)

    api = API.read_text()
    n = 0
    if API_OLD in api:
        api = api.replace(API_OLD, API_NEW, 1)
        n += 1
    if API_A_OLD in api:
        api = api.replace(API_A_OLD, API_A_NEW, 1)
        n += 1
    if n:
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = API.with_name(f"api.py.bak.club_tight.{ts}")
        shutil.copy2(API, bak)
        API.write_text(api)
        print("API_PATCHED", bak, n)
    else:
        print("API_SKIP")


if __name__ == "__main__":
    main()
