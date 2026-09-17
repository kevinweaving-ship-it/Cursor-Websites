#!/usr/bin/env python3
"""Public class URLs are /class/420 — never /class/7-420."""
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
    (
        """h += '<td><a href="/class/' + row.class_id + '-' + slug + '">' + esc + '</a></td>';""",
        """h += '<td><a href="/class/' + slug + '">' + esc + '</a></td>';""",
    ),
    (
        """'<a href="/class/' + String(row.last_class_id).replace(/</g, '&lt;') + '-' + classSlug + '">' + classEsc + '</a>'""",
        """'<a href="/class/' + classSlug + '">' + classEsc + '</a>'""",
    ),
    (
        """'<a href="/class/' + String(row.class_id).replace(/</g, '&lt;') + '-' + slug + '">' + classEsc + '</a>'""",
        """'<a href="/class/' + slug + '">' + classEsc + '</a>'""",
    ),
    (
        """'<a href="/class/'+String(row.last_class_id).replace(/</g,'&lt;')+'-'+classSlug+'" style="color:#001f3f">'+classEsc+'</a>'""",
        """'<a href="/class/'+classSlug+'" style="color:#001f3f">'+classEsc+'</a>'""",
    ),
    (
        """'<a href="/class/'+String(row.class_id).replace(/</g,'&lt;')+'-'+slug+'" style="color:#001f3f">'+classEsc+'</a>'""",
        """'<a href="/class/'+slug+'" style="color:#001f3f">'+classEsc+'</a>'""",
    ),
    (
        'path = /class/{id}-{slug}. Sorted by class_name."""',
        'path = /class/{slug}. Sorted by class_name."""',
    ),
    (
        'homepage class search (links to /class/{id}-{slug})."""',
        'homepage class search (links to /class/{slug})."""',
    ),
]

missing = []
for old, new in repls:
    if old not in text:
        missing.append(old[:80])
        continue
    text = text.replace(old, new)

if missing:
    print("MISSING", len(missing))
    for m in missing:
        print(" ", m)
    raise SystemExit(2)

if MARK not in text:
    raise SystemExit("MARK_NOT_APPLIED")

API.write_text(text)
print("CLASS_URL_NO_ID", text.count("/class/{cid}-") + text.count("/class/{class_id}-") + text.count("/class/{cid_int}-"))
