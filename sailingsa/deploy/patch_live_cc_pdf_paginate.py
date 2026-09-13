#!/usr/bin/env python3
"""Give compact Class-column sheets a slightly taller fleet estimate so Open is not clipped."""
from pathlib import Path

P = Path("/var/www/sailingsa/sailingsa/backend/regatta_stored_pdf.py")
OLD = """    page_mm = 188 if orient == \"landscape\" else 275
    row_mm = 4.0 if orient == \"landscape\" else 4.3
    used = 22.0
    out: list[dict] = []
    for i, fleet in enumerate(fleets):
        item = dict(fleet)
        html = item.get(\"html\") or \"\"
        n_rows = int(item.get(\"n_rows\") or 0)
        h = 16.0 + n_rows * row_mm
"""
NEW = """    page_mm = 188 if orient == \"landscape\" else 262
    row_mm = 4.0 if orient == \"landscape\" else 4.3
    used = 22.0
    out: list[dict] = []
    for i, fleet in enumerate(fleets):
        item = dict(fleet)
        html = item.get(\"html\") or \"\"
        n_rows = int(item.get(\"n_rows\") or 0)
        compact = \"rs-compact-row-logos\" in html
        rm = (4.8 if orient != \"landscape\" else row_mm) if compact else row_mm
        hdr = 18.5 if compact else 16.0
        h = hdr + n_rows * rm
"""


def main() -> int:
    text = P.read_text(encoding="utf-8")
    if "compact = \"rs-compact-row-logos\" in html" in text:
        print("already patched paginate")
        return 0
    if OLD not in text:
        raise SystemExit("paginate block missing")
    P.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", P)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
