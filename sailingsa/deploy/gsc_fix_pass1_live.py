#!/usr/bin/env python3
"""GSC FIX PASS #1 — surgical live patches only.

Applies two exact replacements on live /var/www/sailingsa/api/api.py:

1. _html_with_gold_header: if extra_head already has a canonical, strip the
   header.html home canonical so /events emits exactly one
   https://sailingsa.co.za/events canonical.
2. _sailor_spa: 404 when the slug does not resolve to a real sailor
   (do not treat the raw slug as existence proof). If the SEO helper
   misses, reuse `_get_sas_id_by_slug` so hyphenated surnames still 200.

Does not recreate sitemap-priority.xml, does not touch pool/#128 DB code,
does not change header.html, and does not generalise 404s to other entities.

Idempotent. Run on the live host only after a scoped api.py snapshot.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
ROBOTS = Path("/var/www/sailingsa/robots.txt")

OLD_GOLD = (
    "    if extra_head:\n"
    '        header_html = re.sub(r"</head>", extra_head + "</head>", header_html, count=1, flags=re.I)\n'
)
NEW_GOLD = (
    "    if extra_head:\n"
    "        # GSC FIX PASS #1: page-supplied canonical replaces header.html home canonical\n"
    '        if re.search(r\'rel=["\\\']canonical["\\\']\', extra_head, flags=re.I):\n'
    "            header_html = re.sub(\n"
    '                r\'<link\\b[^>]*\\brel=["\\\']canonical["\\\'][^>]*>\',\n'
    '                "",\n'
    "                header_html,\n"
    "                count=1,\n"
    "                flags=re.I,\n"
    "            )\n"
    '        header_html = re.sub(r"</head>", extra_head + "</head>", header_html, count=1, flags=re.I)\n'
)

OLD_SAILOR = (
    "def _sailor_spa(slug: str, request: Request):\n"
    "    name, canonical_slug = _get_sailor_name_by_slug(slug)\n"
    '    want = (canonical_slug or slug or "").strip()\n'
    "    if not want:\n"
    '        raise HTTPException(status_code=404, detail="Sailor not found")\n'
    "    if canonical_slug and slug.strip().lower() != canonical_slug.lower():\n"
    '        return RedirectResponse(url=f"/sailor/{canonical_slug}", status_code=301)\n'
    "    return serve_dev1_rank_page(request, sailor=want)\n"
)
# First-pass 404 (helper only). Too strict: hyphenated surnames resolve via
# /api/sailor/resolve and _get_sas_id_by_slug but not _get_sailor_name_by_slug.
SAILOR_HELPER_ONLY = (
    "def _sailor_spa(slug: str, request: Request):\n"
    "    name, canonical_slug = _get_sailor_name_by_slug(slug)\n"
    "    if not name or not canonical_slug:\n"
    '        raise HTTPException(status_code=404, detail="Sailor not found")\n'
    "    if slug.strip().lower() != canonical_slug.lower():\n"
    '        return RedirectResponse(url=f"/sailor/{canonical_slug}", status_code=301)\n'
    "    return serve_dev1_rank_page(request, sailor=canonical_slug)\n"
)
NEW_SAILOR = (
    "def _sailor_spa(slug: str, request: Request):\n"
    "    name, canonical_slug = _get_sailor_name_by_slug(slug)\n"
    "    if not name or not canonical_slug:\n"
    "        sid = _get_sas_id_by_slug(slug)\n"
    "        if sid:\n"
    "            name, canonical_slug = _get_sailor_by_sas_id_for_redirect(str(sid))\n"
    "    if not name or not canonical_slug:\n"
    '        raise HTTPException(status_code=404, detail="Sailor not found")\n'
    "    if slug.strip().lower() != canonical_slug.lower():\n"
    '        return RedirectResponse(url=f"/sailor/{canonical_slug}", status_code=301)\n'
    "    return serve_dev1_rank_page(request, sailor=canonical_slug)\n"
)

OLD_ROBOTS_LINE = "Sitemap: https://sailingsa.co.za/sitemap-priority.xml\n"
KEEP_ROBOTS_LINE = "Sitemap: https://sailingsa.co.za/sitemap.xml"


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n == 0:
        if new in text:
            print(f"OK already applied: {label}")
            return text
        raise SystemExit(f"FAIL {label}: old block not found and new block not present")
    if n != 1:
        raise SystemExit(f"FAIL {label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def apply_api(path: Path = API) -> str:
    text = path.read_text(encoding="utf-8")
    text = _replace_once(text, OLD_GOLD, NEW_GOLD, "_html_with_gold_header extra_head")
    if SAILOR_HELPER_ONLY in text:
        text = _replace_once(text, SAILOR_HELPER_ONLY, NEW_SAILOR, "_sailor_spa resolve fallback")
    else:
        text = _replace_once(text, OLD_SAILOR, NEW_SAILOR, "_sailor_spa unknown-slug 404")
    if 'want = (canonical_slug or slug or "").strip()' in text:
        raise SystemExit("FAIL _sailor_spa slug fallback still present")
    if "page-supplied canonical replaces header.html home canonical" not in text:
        raise SystemExit("FAIL gold-header canonical strip missing")
    path.write_text(text, encoding="utf-8")
    return _md5(path)


def apply_robots(path: Path = ROBOTS) -> None:
    text = path.read_text(encoding="utf-8")
    if KEEP_ROBOTS_LINE not in text:
        raise SystemExit("FAIL robots.txt missing sitemap-index reference")
    if OLD_ROBOTS_LINE not in text:
        if "sitemap-priority.xml" not in text:
            print("OK robots.txt already has no sitemap-priority.xml")
            return
        raise SystemExit("FAIL robots.txt still mentions sitemap-priority.xml in unexpected form")
    path.write_text(text.replace(OLD_ROBOTS_LINE, "", 1), encoding="utf-8")
    leftover = path.read_text(encoding="utf-8")
    if "sitemap-priority.xml" in leftover:
        raise SystemExit("FAIL robots.txt still mentions sitemap-priority.xml")
    if KEEP_ROBOTS_LINE not in leftover:
        raise SystemExit("FAIL robots.txt lost sitemap.xml index reference")


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    if not target.is_file():
        raise SystemExit(f"FAIL missing {target}")
    before = _md5(target)
    print(f"api.py before md5 {before} lines {target.read_text(encoding='utf-8').count(chr(10))+1}")
    after = apply_api(target)
    print(f"api.py after md5 {after}")
    if ROBOTS.is_file() and target == API:
        apply_robots(ROBOTS)
        print("robots.txt updated")
        print(ROBOTS.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
