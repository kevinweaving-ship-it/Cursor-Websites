#!/usr/bin/env python3
"""Treat agent/test sailor URLs as junk (not valid sailor pages)."""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old = '''def _is_junk_crawler_path(path: Optional[str]) -> bool:
    """Fake URLs crawlers follow: team-name sailor slugs, fleet-as-sail boat URLs."""
    p = (path or "").split("?", 1)[0].lower().rstrip("/") or "/"
    if not p.startswith("/"):
        p = "/" + p
    if re.match(r"^/sailor/[^/]*-and-[^/]*$", p):
        return True
    if re.match(r"^/boat/.+-(novice|gold|silver|bronze|open|fleet|junior|youth|masters?|ladies|women|men)$", p):
        return True
    return False'''

new = '''def _is_junk_crawler_path(path: Optional[str]) -> bool:
    """Fake URLs crawlers follow: team-name sailor slugs, fleet-as-sail boat URLs,
    and agent/test paths that real sailors never open."""
    p = (path or "").split("?", 1)[0].lower().rstrip("/") or "/"
    if not p.startswith("/"):
        p = "/" + p
    if re.match(r"^/sailor/[^/]*-and-[^/]*$", p):
        return True
    if re.match(r"^/boat/.+-(novice|gold|silver|bronze|open|fleet|junior|youth|masters?|ladies|women|men)$", p):
        return True
    # Cursor agent / clean-trail QA paths (not real sailors)
    if re.match(r"^/sailor/(clean-trail|local-trail|cleantrail)(-[a-z0-9-]*)?$", p):
        return True
    if "clean-trail" in p or "local-trail" in p:
        return True
    return False'''

if old not in text:
    if "clean-trail|local-trail|cleantrail" in text:
        print("junk path already patched")
    else:
        raise SystemExit("junk crawler fn not found")
else:
    text = text.replace(old, new, 1)

# lean SQL filter
old_line = "      AND {col} NOT LIKE '/temp-landing{pct}'"
if "%clean-trail%" in text[text.find("def _lean_traffic_path_ok_sql") : text.find("def _lean_traffic_path_ok_sql") + 1500]:
    print("lean sql already filtered")
elif old_line not in text:
    raise SystemExit("lean filter line missing")
else:
    text = text.replace(
        old_line,
        "      AND {col} NOT LIKE '/temp-landing{pct}'\n"
        "      AND {col} NOT LIKE '%clean-trail%'\n"
        "      AND {col} NOT LIKE '%local-trail%'",
        1,
    )

if text != orig:
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK (+{len(text) - len(orig)} bytes)")
else:
    print("OK no file change needed")
