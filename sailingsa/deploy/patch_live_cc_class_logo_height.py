#!/usr/bin/env python3
"""Cape Classic class-column logos: all match Sonnet height (16px). Delete the 28px width cap on class marks."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD_ART = """    elif css in (\"rs-club-row-logo-sm\", \"rs-class-row-logo\"):
        # Compact cap — never a fixed height that expands the rank row.
        _img_style = (
            'style=\"height:auto;width:auto;max-height:16px;max-width:28px;'
            'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto\" '
        )
"""

NEW_ART = """    elif css == \"rs-class-row-logo\":
        # Size from CSS: 16px = Sonnet (tallest). Do not cap width.
        _img_style = (
            'style=\"object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto\" '
        )
    elif css == \"rs-club-row-logo-sm\":
        _img_style = (
            'style=\"height:auto;width:auto;max-height:16px;max-width:28px;'
            'object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto\" '
        )
"""

OLD_CSS1 = (
    '".fleet-results-table .rs-class-row-logo,.fleet-results-table .rs-club-row-logo-sm'
    "{display:inline-block!important;height:auto!important;width:auto!important;"
    "max-height:16px!important;max-width:28px!important;object-fit:contain!important;"
    "object-position:center!important;vertical-align:middle;flex:0 0 auto!important}\""
)
NEW_CSS1 = (
    '".fleet-results-table .rs-class-row-logo'
    "{display:inline-block!important;height:16px!important;width:auto!important;"
    "max-height:16px!important;max-width:none!important;object-fit:contain!important;"
    "object-position:center!important;vertical-align:middle;flex:0 0 auto!important}\"\n"
    '    ".fleet-results-table .rs-club-row-logo-sm'
    "{display:inline-block!important;height:auto!important;width:auto!important;"
    "max-height:16px!important;max-width:28px!important;object-fit:contain!important;"
    "object-position:center!important;vertical-align:middle;flex:0 0 auto!important}\""
)

OLD_CSS2 = (
    '".fleet-results-table .rs-class-row-logo,.fleet-results-table .rs-club-row-logo-sm'
    "{height:auto!important;width:auto!important;max-height:16px!important;"
    "max-width:28px!important;object-fit:contain!important;display:inline-block!important;"
    "flex:0 0 auto!important}\""
)
NEW_CSS2 = (
    '".fleet-results-table .rs-class-row-logo'
    "{height:16px!important;width:auto!important;max-height:16px!important;"
    "max-width:none!important;object-fit:contain!important;display:inline-block!important;"
    "flex:0 0 auto!important}\"\n"
    '    ".fleet-results-table .rs-club-row-logo-sm'
    "{height:auto!important;width:auto!important;max-height:16px!important;"
    "max-width:28px!important;object-fit:contain!important;display:inline-block!important;"
    "flex:0 0 auto!important}\""
)


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if OLD_ART not in text:
        raise SystemExit("missing class/club art block")
    if OLD_CSS1 not in text:
        raise SystemExit("missing class-logo css1")
    if OLD_CSS2 not in text:
        raise SystemExit("missing class-logo css2")
    text = text.replace(OLD_ART, NEW_ART, 1)
    text = text.replace(OLD_CSS1, NEW_CSS1, 1)
    text = text.replace(OLD_CSS2, NEW_CSS2, 1)
    leftover = text.count(
        ".rs-class-row-logo,.fleet-results-table .rs-club-row-logo-sm"
        "{height:auto!important;width:auto!important;max-height:16px!important;"
        "max-width:28px"
    )
    leftover += text.count(
        ".rs-class-row-logo,.fleet-results-table .rs-club-row-logo-sm"
        "{display:inline-block!important;height:auto!important"
    )
    if leftover:
        raise SystemExit(f"combined class+club 16x28 still present x{leftover}")
    API.write_text(text, encoding="utf-8")
    print("PATCHED class-logo height = Sonnet 16px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
