#!/usr/bin/env python3
"""Cape Classic stored PDF: split DNC codes; header logo/Fleet → event child."""
from __future__ import annotations

from pathlib import Path

P = Path("/var/www/sailingsa/sailingsa/backend/regatta_stored_pdf.py")
MARKER = "CC_PRINT_HEADER_SCORE_v1"

OLD = '''    fleets = [dict(f, html=rewrite_print_images(f.get("html") or "")) for f in fleets]
'''

NEW = '''    def _prep_cc_print_html(html: str, fleet: dict) -> str:
        # ''' + MARKER + '''
        h = rewrite_print_images(html or "")
        try:
            from sailingsa.backend.cape_classic_fleet_sheet import (
                is_cape_classic_2026_zvy_event,
                split_plain_race_code_spans,
                print_header_links_to_event_child,
            )
        except Exception:
            return h
        if not is_cape_classic_2026_zvy_event(slug):
            return h
        h = split_plain_race_code_spans(h)
        child = (fleet.get("pdf_slug") or "").strip()
        if child:
            href = child if str(child).startswith("/regatta/") else "/regatta/" + child
            h = print_header_links_to_event_child(h, href)
        return h

    fleets = [dict(f, html=_prep_cc_print_html(f.get("html") or "", f)) for f in fleets]
'''


def main() -> int:
    text = P.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched stored_pdf print html")
        return 0
    if OLD not in text:
        raise SystemExit("rewrite_print_images fleet list missing")
    text = text.replace(OLD, NEW, 1)
    if MARKER not in text:
        raise SystemExit("marker failed")
    P.write_text(text, encoding="utf-8")
    print("PATCHED", P)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
