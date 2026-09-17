#!/usr/bin/env python3
"""Public class URLs are /class/420 — never /class/7-420. Tolerant for full live api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLASS_URL_NO_ID_v1"
text = API.read_text()
if MARK in text:
    print("ALREADY")
    raise SystemExit(0)

repls = [
    (
        'path = f"/class/{cid}-{slug}" if slug else f"/class/{cid}"',
        'path = f"/class/{slug}" if slug else "/classes"  # CLASS_URL_NO_ID_v1',
    ),
    (
        'out_row["class_path"] = f"/class/{cid_int}-{canon}" if canon else f"/class/{cid_int}"',
        'out_row["class_path"] = f"/class/{canon}" if canon else "/classes"',
    ),
    (
        'class_path = f"/class/{class_id}-{cslug}" if cslug else f"/class/{class_id}"',
        'class_path = f"/class/{cslug}" if cslug else "/classes"',
    ),
    (
        'class_path = f"/class/{cid_int}-{canon}" if canon else f"/class/{cid_int}"',
        'class_path = f"/class/{canon}" if canon else "/classes"',
    ),
    (
        'path = f"/class/{cid}-{cslug}" if cslug else f"/class/{cid}"',
        'path = f"/class/{cslug}" if cslug else "/classes"',
    ),
    (
        'canonical_path = f"/class/{class_id}-{canonical_slug}" if canonical_slug else f"/class/{class_id}"',
        'canonical_path = f"/class/{canonical_slug}" if canonical_slug else "/classes"',
    ),
    (
        'cpath = f"/class/{int(rcid)}-{canon}" if canon else f"/class/{int(rcid)}"',
        'cpath = f"/class/{canon}" if canon else "/classes"',
    ),
    (
        'canonical_path = f"/class/{class_id}-{canon}" if canon else f"/class/{class_id}"',
        'canonical_path = f"/class/{canon}" if canon else "/classes"',
    ),
]

applied = 0
missing = []
for old, new in repls:
    if old not in text:
        missing.append(old[:90])
        continue
    text = text.replace(old, new)
    applied += 1

if applied < 1:
    print("ERROR no class path builders found")
    raise SystemExit(2)
if MARK not in text:
    # first replacement includes the mark
    if "CLASS_URL_NO_ID_v1" not in text:
        text = text.replace(
            "def serve_class_spa(class_slug: str):",
            "def serve_class_spa(class_slug: str):  # CLASS_URL_NO_ID_v1",
            1,
        )
API.write_text(text)
print("APPLIED", applied, "MISSING", len(missing))
for m in missing:
    print(" ", m)
