#!/usr/bin/env python3
"""MP only: shrink event + host logos on regatta/fleet headers to landing 48h size.

Landing already fits portrait with max-height min(14vw,52px) / max-width min(20vw,80px).
Event URL still used min(34vw,180px), so the 3-col header (and stacked portrait) overflowed.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

REPLACEMENTS = [
    (
        '''    ".regatta-name{font-size:18px}"
    ".regatta-name-input{font-size:16px}"''',
        '''    ".regatta-name{font-size:18px}"
    ".regatta-header-logo-img,.regatta-header-left-logo-img,.regatta-header-club-logo-img{max-height:min(14vw,52px)!important;max-width:min(20vw,80px)!important}"
    ".class-header-logo-img,.class-header-club-logo-col .regatta-header-logo-img{max-height:min(14vw,52px)!important;max-width:min(20vw,80px)!important}"
    ".regatta-name-input{font-size:16px}"''',
    ),
    (
        '''    ".regatta-header-logo-img,"
    ".regatta-header-left-logo-img,"
    ".regatta-header-club-logo-img{height:auto;max-height:min(34vw,180px);width:auto;max-width:min(62vw,440px);object-fit:contain}"''',
        '''    ".regatta-header-logo-img,"
    ".regatta-header-left-logo-img,"
    ".regatta-header-club-logo-img{height:auto;max-height:min(14vw,52px);width:auto;max-width:min(20vw,80px);object-fit:contain}"''',
    ),
    (
        '''    ".class-header-logo-img,"
    ".class-header-club-logo-col .regatta-header-logo-img{max-height:min(18vw,80px);max-width:min(42vw,220px)}"''',
        '''    ".class-header-logo-img,"
    ".class-header-club-logo-col .regatta-header-logo-img{max-height:min(14vw,52px);max-width:min(20vw,80px)}"''',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n} for:\n{old[:220]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
