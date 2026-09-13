#!/usr/bin/env python3
"""Keep ?query on print image URLs. Marker: PDF_ABS_ASSET_QUERY_v1

Chrome PDF rewrite was turning ?v= into %3F, so class/club row logos 404'd
while header logos without a query still loaded. Mac browser print was fine
because it uses the live URL as-is.
"""
from __future__ import annotations

from pathlib import Path

P = Path("/var/www/sailingsa/sailingsa/backend/regatta_stored_pdf.py")
MARKER = "PDF_ABS_ASSET_QUERY_v1"

OLD = '''    path = s if s.startswith("/") else "/" + s
    # Fleet HTML often already has %20; unquote first so we do not emit %2520.
    path = unquote(path)
    enc = "/".join(quote(part, safe=".-_~") for part in path.split("/"))
    if not enc.startswith("/"):
        enc = "/" + enc
    return _SITE + enc
'''

NEW = '''    # ''' + "PDF_ABS_ASSET_QUERY_v1" + '''
    from urllib.parse import urlsplit
    raw = s if s.startswith("/") else "/" + s
    parts = urlsplit("https://local" + raw)
    path = unquote(parts.path)
    enc = "/".join(quote(part, safe=".-_~") for part in path.split("/"))
    if not enc.startswith("/"):
        enc = "/" + enc
    out = _SITE.rstrip("/") + enc
    if parts.query:
        out += "?" + parts.query
    if parts.fragment:
        out += "#" + parts.fragment
    return out
'''


def main() -> int:
    text = P.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched abs_asset_url")
        return 0
    if OLD not in text:
        raise SystemExit("abs_asset_url block missing")
    text = text.replace(OLD, NEW, 1)
    if MARKER not in text:
        raise SystemExit("marker failed")
    P.write_text(text, encoding="utf-8")
    print("PATCHED", P)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
