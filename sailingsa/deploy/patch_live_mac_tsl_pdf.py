#!/usr/bin/env python3
"""Surgical live api.py patch: TSL Print/Share/Download PDF is the Event URL.

Never wholesale-replace /var/www/sailingsa/api/api.py.
Never serve the stored individual-results table for this slug.
Never rebuild TSL from fleet HTML.

  python3 sailingsa/deploy/patch_live_mac_tsl_pdf.py /var/www/sailingsa/api/api.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SLUG = "2026-10-17-mac-tsl-wc-team-sailing"
MARKER = "TSL_LIVE_PAGE_PDF_v1"
OLD_BOOT = '<style id="mac-tsl-boot-css">@page{size:297mm 210mm;margin:8mm}</style>'
NEW_BOOT = '<style id="mac-tsl-boot-css">@page{size:A4 landscape;size:297mm 210mm;margin:8mm}</style>'
OLD_PIN = "mac-tsl-admin.js?v=20261022v"
NEW_PIN = "mac-tsl-admin.js?v=20261022w"

REBUILD_ANCHOR = (
    "    rid = str(slug or \"\").strip()\n"
    "    if not rid:\n"
    "        return None\n"
    "    data = _get_regatta_full_page_data(rid)\n"
)
REBUILD_INSERT = (
    "    rid = str(slug or \"\").strip()\n"
    "    if not rid:\n"
    "        return None\n"
    f"    if rid == \"{SLUG}\":  # {MARKER} — do not rebuild from fleet HTML\n"
    "        return None\n"
    "    data = _get_regatta_full_page_data(rid)\n"
)

SERVE_ANCHOR = (
    "    cslug = (class_slug or \"\").strip() or None\n"
    "    if not rid:\n"
    "        raise HTTPException(status_code=404, detail=\"PDF not found\")\n"
    "    fluid = _event_still_fluid(rid)\n"
)
SERVE_INSERT = (
    "    cslug = (class_slug or \"\").strip() or None\n"
    "    if not rid:\n"
    "        raise HTTPException(status_code=404, detail=\"PDF not found\")\n"
    f"    if rid == \"{SLUG}\":  # {MARKER} — stored live-page PDF only\n"
    "        path = pdf_abs_path(rid, cslug)\n"
    "        if not path.is_file() or path.stat().st_size < 500:\n"
    "            raise HTTPException(status_code=404, detail=\"PDF not found\")\n"
    "        fn = pdf_download_name(rid, cslug)\n"
    "        disp = \"attachment\" if download else \"inline\"\n"
    "        return FileResponse(\n"
    "            path,\n"
    "            media_type=\"application/pdf\",\n"
    "            headers={\n"
    "                \"Content-Disposition\": f'{disp}; filename=\"{fn}\"',\n"
    "                \"Cache-Control\": \"no-store\",\n"
    "            },\n"
    "        )\n"
    "    fluid = _event_still_fluid(rid)\n"
)


def patch(text: str) -> str:
    n = text.count(OLD_PIN)
    if n:
        text = text.replace(OLD_PIN, NEW_PIN)
        print("pin replaced", n)
    elif NEW_PIN in text:
        print("pin already 22v")
    else:
        raise SystemExit("TSL admin pin 22u/22v not found")
    if OLD_BOOT in text:
        text = text.replace(OLD_BOOT, NEW_BOOT)
        print("boot css landscape")
    elif NEW_BOOT in text:
        print("boot css already landscape")
    elif "mac-tsl-boot-css" in text:
        text = text.replace(
            "@page{size:297mm 210mm;margin:8mm}",
            "@page{size:A4 landscape;size:297mm 210mm;margin:8mm}",
        )
        print("boot css landscape (generic)")
    else:
        raise SystemExit("mac-tsl-boot-css missing")
    if MARKER in text and "do not rebuild from fleet HTML" in text:
        print("rebuild skip already present")
    else:
        if text.count(REBUILD_ANCHOR) != 1:
            raise SystemExit(f"rebuild anchor not unique: {text.count(REBUILD_ANCHOR)}")
        text = text.replace(REBUILD_ANCHOR, REBUILD_INSERT, 1)
        print("rebuild skip inserted")
    if MARKER in text and "stored live-page PDF only" in text:
        print("serve skip already present")
    else:
        if text.count(SERVE_ANCHOR) != 1:
            raise SystemExit(f"serve anchor not unique: {text.count(SERVE_ANCHOR)}")
        text = text.replace(SERVE_ANCHOR, SERVE_INSERT, 1)
        print("serve skip inserted")
    return text


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_live_mac_tsl_pdf.py /path/to/api.py", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    orig = path.read_text(encoding="utf-8")
    out = patch(orig)
    path.write_text(out, encoding="utf-8")
    print(f"Wrote {path} ({len(orig.splitlines())} -> {len(out.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
