#!/usr/bin/env python3
"""MP only: event + fleet headers stack (logo / text / host). Other viewports unchanged."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")

OLD_GRID = (
    '    ".header{width:100%!important;max-width:100%!important;margin-bottom:12px;padding:8px 6px;margin-left:0;margin-right:0;"\n'
    '    "grid-template-columns:minmax(0,auto) minmax(0,1fr) minmax(0,auto);grid-template-rows:auto;"\n'
    '    "align-items:center;justify-items:stretch;column-gap:4px;row-gap:0;min-height:0}"\n'
    '    ".regatta-header-logo-col{grid-column:1;grid-row:1;justify-content:flex-start;width:auto;min-width:0;padding:2px}"\n'
    '    ".regatta-header-main-col{grid-column:2;grid-row:1;justify-self:center;align-self:center;padding:2px 4px;min-width:0;max-width:100%;width:100%}"\n'
    '    ".regatta-header-club-logo-col{grid-column:3;grid-row:1;justify-content:flex-end;width:auto;min-width:0;padding:2px}"\n'
)

NEW_GRID = (
    '    ".header{width:100%!important;max-width:100%!important;margin-bottom:12px;padding:8px 6px;margin-left:0;margin-right:0;"\n'
    '    "grid-template-columns:minmax(0,1fr);grid-template-rows:auto auto auto;"\n'
    '    "align-items:center;justify-items:center;column-gap:0;row-gap:6px;min-height:0}"\n'
    '    ".regatta-header-logo-col{grid-column:1;grid-row:1;justify-content:center;width:100%;min-width:0;padding:2px}"\n'
    '    ".regatta-header-main-col{grid-column:1;grid-row:2;justify-self:center;align-self:center;padding:2px 4px;min-width:0;max-width:100%;width:100%}"\n'
    '    ".regatta-header-club-logo-col{grid-column:1;grid-row:3;justify-content:center;width:100%;min-width:0;padding:2px}"\n'
)

# First occurrence is the MP (max-aspect-ratio) block; landscape copy stays 3-col.
OLD_LOGOS = (
    '    ".regatta-header-logo-img,"\n'
    '    ".regatta-header-left-logo-img,"\n'
    '    ".regatta-header-club-logo-img{height:auto;max-height:min(22vw,96px);width:auto;max-width:min(28vw,120px);object-fit:contain}"\n'
)
NEW_LOGOS = (
    '    ".regatta-header-logo-img,"\n'
    '    ".regatta-header-left-logo-img,"\n'
    '    ".regatta-header-club-logo-img{height:auto;max-height:min(34vw,180px);width:auto;max-width:min(62vw,440px);object-fit:contain}"\n'
)

OLD_CLASS = (
    '    ".class-header{padding:8px 6px;font-size:14px}"\n'
    '    ".class-header--with-logos{padding:6px 4px;column-gap:4px}"\n'
    '    ".class-header-logo-img,"\n'
    '    ".class-header-club-logo-col .regatta-header-logo-img{max-height:min(16vw,64px);max-width:min(36vw,140px)}"\n'
)
NEW_CLASS = (
    '    ".class-header{padding:8px 6px;font-size:14px;flex-direction:column;gap:8px}"\n'
    '    ".class-header--with-logos{padding:6px 4px;column-gap:0;row-gap:6px;'
    "grid-template-columns:minmax(0,1fr);grid-template-rows:auto auto auto;justify-items:center}\"\n"
    '    ".class-header-logo-col{grid-column:1;grid-row:1;justify-content:center}"\n'
    '    ".class-header-main-col,.class-header-text-col{grid-column:1;grid-row:2}"\n'
    '    ".class-header-club-logo-col{grid-column:1;grid-row:3;justify-content:center}"\n'
    '    ".class-header-logo-img,"\n'
    '    ".class-header-club-logo-col .regatta-header-logo-img{max-height:min(18vw,80px);max-width:min(42vw,220px)}"\n'
)


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    if "grid-template-rows:auto auto auto;" in text and "class-header-club-logo-col{grid-column:1;grid-row:3" in text:
        print("already stacked")
        return
    if OLD_GRID not in text:
        raise SystemExit("MP header grid not found")
    text = text.replace(OLD_GRID, NEW_GRID, 1)
    if OLD_LOGOS not in text:
        raise SystemExit("MP logo sizes not found")
    text = text.replace(OLD_LOGOS, NEW_LOGOS, 1)
    if OLD_CLASS not in text:
        raise SystemExit("MP class-header not found")
    text = text.replace(OLD_CLASS, NEW_CLASS, 1)
    LIVE_API.write_text(text, encoding="utf-8")
    print("MP stacked event + fleet headers")


if __name__ == "__main__":
    main()
