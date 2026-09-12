#!/usr/bin/env python3
"""MP header layout: match landing 48h ZVYC card.

Landing keeps logos left/right of title text. Event/fleet portrait CSS was
stacking logos above/below, which also left the long Results/Sailed lines
squeezed. Keep 3-col logos; put status + entries (and fleet sailed) on a
full-width row under the logo row. Smaller text like landing.
Lipton stacked header unchanged.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

REPLACEMENTS = [
    (
        '''    ".header{width:100%!important;max-width:100%!important;margin-bottom:12px;padding:8px 6px;margin-left:0;margin-right:0;"
    "grid-template-columns:minmax(0,1fr);grid-template-rows:auto auto auto;"
    "align-items:center;justify-items:center;column-gap:0;row-gap:6px;min-height:0}"
    ".regatta-header-logo-col{grid-column:1;grid-row:1;justify-content:center;width:100%;min-width:0;padding:2px}"
    ".regatta-header-main-col{grid-column:1;grid-row:2;justify-self:center;align-self:center;padding:2px 4px;min-width:0;max-width:100%;width:100%}"
    ".regatta-header-club-logo-col{grid-column:1;grid-row:3;justify-content:center;width:100%;min-width:0;padding:2px}"''',
        '''    ".header{width:100%!important;max-width:100%!important;margin-bottom:12px;padding:8px 6px;margin-left:0;margin-right:0;"
    "grid-template-columns:minmax(0,min(22vw,72px)) minmax(0,1fr) minmax(0,min(22vw,72px));grid-template-rows:auto auto auto auto auto;"
    "align-items:center;justify-items:stretch;column-gap:4px;row-gap:2px;min-height:0}"
    ".header:not(.header--lipton) .regatta-header-logo-col{grid-column:1;grid-row:1/span 3;justify-content:flex-start;width:auto;min-width:0;padding:2px;align-self:center}"
    ".header:not(.header--lipton) .regatta-header-main-col{display:contents}"
    ".header:not(.header--lipton) .regatta-name,.header:not(.header--lipton) .host-club,.header:not(.header--lipton) .regatta-venue{grid-column:2;justify-self:center;text-align:center;min-width:0;max-width:100%}"
    ".header:not(.header--lipton) .regatta-name{grid-row:1}"
    ".header:not(.header--lipton) .host-club{grid-row:2}"
    ".header:not(.header--lipton) .regatta-venue{grid-row:3}"
    ".header:not(.header--lipton) .status-line{grid-column:1/-1;grid-row:4;text-align:center;padding:0 2px}"
    ".header:not(.header--lipton) .entry-total-line{grid-column:1/-1;grid-row:5;text-align:center}"
    ".header:not(.header--lipton) .regatta-header-club-logo-col{grid-column:3;grid-row:1/span 3;justify-content:flex-end;width:auto;min-width:0;padding:2px;align-self:center}"
    ".header--lipton .regatta-header-logo-col{grid-column:1;grid-row:1;justify-content:center;width:100%;min-width:0;padding:2px}"
    ".header--lipton .regatta-header-main-col{grid-column:1;grid-row:2;justify-self:center;align-self:center;padding:2px 4px;min-width:0;max-width:100%;width:100%}"
    ".header--lipton .regatta-header-club-logo-col{grid-column:1;grid-row:3;justify-content:center;width:100%;min-width:0;padding:2px}"''',
    ),
    (
        '''    ".regatta-name{font-size:clamp(14px,4.2vw,18px);line-height:1.25;margin-bottom:4px}"''',
        '''    ".regatta-name{font-size:clamp(11px,3.2vw,18px);line-height:1.2;margin-bottom:2px}"''',
    ),
    (
        '''    ".host-club{font-size:clamp(12px,3.4vw,15px);margin-bottom:2px;line-height:1.3}"''',
        '''    ".host-club{font-size:clamp(9px,2.5vw,13px);margin-bottom:1px;line-height:1.2}"''',
    ),
    (
        '''    ".regatta-venue{font-size:clamp(11px,3.1vw,13px);margin-bottom:2px}"''',
        '''    ".regatta-venue{font-size:clamp(9px,2.5vw,13px);margin-bottom:1px}"''',
    ),
    (
        '''    ".status-line{font-size:clamp(11px,3vw,13px);margin-top:2px;margin-bottom:0;line-height:1.3}"''',
        '''    ".status-line{font-size:clamp(8px,2.2vw,12px);margin-top:2px;margin-bottom:0;line-height:1.2}"''',
    ),
    (
        '''    ".entry-total-line{font-size:clamp(10px,2.6vw,12px);margin-top:1px}"''',
        '''    ".entry-total-line{font-size:clamp(8px,2.2vw,12px);margin-top:1px}"''',
    ),
    (
        '''    ".class-header--with-logos{padding:6px 4px;column-gap:0;row-gap:6px;grid-template-columns:minmax(0,1fr);grid-template-rows:auto auto auto;justify-items:center}"
    ".class-header-logo-col{grid-column:1;grid-row:1;justify-content:center}"
    ".class-header-main-col,.class-header-text-col{grid-column:1;grid-row:2}"
    ".class-header-club-logo-col{grid-column:1;grid-row:3;justify-content:center}"''',
        '''    ".class-header--with-logos{padding:6px 4px;column-gap:4px;row-gap:2px;grid-template-columns:minmax(0,min(22vw,72px)) minmax(0,1fr) minmax(0,min(22vw,72px));grid-template-rows:auto auto;justify-items:stretch;align-items:center}"
    ".class-header-logo-col{grid-column:1;grid-row:1;justify-content:flex-start}"
    ".class-header-main-col,.class-header-text-col{display:contents}"
    ".class-header--with-logos .fleet-title-row{grid-column:2;grid-row:1;text-align:center;min-width:0}"
    ".class-header--with-logos .sailed-line{grid-column:1/-1;grid-row:2;text-align:center;padding:0 2px}"
    ".class-header-club-logo-col{grid-column:3;grid-row:1;justify-content:flex-end}"''',
    ),
    (
        '''    ".sailed-line{font-size:10px;margin-top:4px}"''',
        '''    ".sailed-line{font-size:clamp(8px,2.2vw,12px);margin-top:2px}"''',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
