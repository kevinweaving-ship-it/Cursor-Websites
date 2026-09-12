#!/usr/bin/env python3
"""Apply live-only pdf_slug fix: child PDF path = public child event URL.

Live api.py _rebuild_regatta_stored_pdfs must write
/var/www/sailingsa/data/regatta-pdfs/{parent}-{fleet-tail}/results.pdf
using _fleet_shell_public_url_slug, not the raw block_id tail.

Run on the live host:
  python3 sailingsa/deploy/patch_rebuild_pdf_child_slug.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
OLD = '''        bid = str(f.get("block_id") or "")
        tail = bid.split(":", 1)[-1].strip() if ":" in bid else cslug
        pdf_slug = f"{rid}-{tail}" if tail else ""
'''
NEW = '''        bid = str(f.get("block_id") or "")
        try:
            pdf_slug = _fleet_shell_public_url_slug(
                rid,
                block_id=bid,
                fleet_label=f.get("fleet_label"),
                class_canonical=f.get("class_canonical"),
                class_name=f.get("class_original") or f.get("name") or f.get("fleet_label"),
            ) or ""
        except Exception:
            pdf_slug = ""
        if not pdf_slug and cslug:
            pdf_slug = f"{rid}-{cslug}"
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if NEW in text:
        print("already_patched")
        return 0
    if OLD not in text:
        print("OLD_BLOCK_MISSING")
        return 1
    subprocess.run(["chattr", "-i", str(API)], check=False)
    API.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    subprocess.run(["chattr", "+i", str(API)], check=False)
    print("patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
