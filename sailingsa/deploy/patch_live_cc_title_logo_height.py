#!/usr/bin/env python3
"""Cape Classic title logos: height = Fleet word. Delete the 22x40 width cap."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD_INLINE = """    elif css == \"rs-fleet-title-logo\":
        _img_style = (
            'style=\"height:auto;width:auto;max-height:22px;max-width:40px;'
            'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto\" '
        )
"""

NEW_INLINE = """    elif css == \"rs-fleet-title-logo\":
        # Size from CSS (1.1em = Fleet word). Do not cap width.
        _img_style = (
            'style=\"object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto\" '
        )
"""

OLD_CSS = (
    ".fleet-title-with-logo .rs-fleet-title-logo{"
    "height:auto;width:auto;max-height:22px;max-width:40px;"
    "object-fit:contain;flex:0 0 auto}\""
)
NEW_CSS = (
    ".fleet-title-with-logo .rs-fleet-title-logo{"
    "height:1.1em!important;width:auto!important;max-height:1.1em!important;"
    "max-width:none!important;object-fit:contain;flex:0 0 auto}\""
)


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if OLD_INLINE not in text:
        raise SystemExit("missing inline title-logo block")
    if OLD_CSS not in text:
        raise SystemExit("missing title-logo css")
    text = text.replace(OLD_INLINE, NEW_INLINE, 1)
    text = text.replace(OLD_CSS, NEW_CSS, 1)
    leftover = text.count("max-height:22px;max-width:40px")
    if leftover:
        raise SystemExit(f"22x40 cap still present x{leftover}")
    API.write_text(text, encoding="utf-8")
    print("PATCHED title-logo height")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
