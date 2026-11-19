#!/usr/bin/env python3
"""Fix Most popular Class/Sailor/Club missing real test visits (420, Tim, SBYC).

Bugs:
1. `_lean_resolve_class_for_traffic` wiped digit-only slugs (420 → "") so href became
   `/classes` and entity rows were dropped.
2. Staff IPs excluded from unified popular — signed-in Tim browse never appears in
   Class/Sailor/Club lists even with scroll/click.
3. Past trails still missing nav engage — one-shot SQL stamp for A→B without click.
"""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD_WIPE = '''    s = (slug or "").strip().strip("/")
    # Strip accidental legacy leading id-
    if s and re.match(r"^\\d+-", s):
        s = s.split("-", 1)[1]
    if s and re.match(r"^\\d+$", s):
        s = ""
    s_key = _class_canonical_slug(s.replace("-", " ")) or s.lower()
'''

NEW_WIPE = '''    s = (slug or "").strip().strip("/")
    # Strip accidental legacy leading id- (e.g. 12-optimist → optimist)
    if s and re.match(r"^\\d+-", s):
        s = s.split("-", 1)[1]
    # Keep digit-only class names (420, 470, 505) — wiping them made href=/classes
    # and dropped the Class list row entirely.
    s_key = _class_canonical_slug(s.replace("-", " ")) or s.lower()
'''

OLD_STAFF = '''        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_STAFF_IP_SQL})
        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
        {real_ip_sql}
        {bot_prefix_sql}
'''

NEW_STAFF = '''        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
        {real_ip_sql}
        {bot_prefix_sql}
'''


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = API.with_suffix(f".py.bak_popular_entities_{ts}")
    shutil.copy2(API, bak)
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    if "Keep digit-only class names (420, 470, 505)" not in text:
        if OLD_WIPE not in text:
            raise SystemExit("class wipe block not found")
        text = text.replace(OLD_WIPE, NEW_WIPE, 1)
        print("OK keep digit-only class slugs")
    else:
        print("SKIP class wipe already fixed")

    # Only change unified SQL staff exclusion (popular/overview continuum), once
    marker = "def _lean_traffic_unified_sql"
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit("unified sql missing")
    end = text.find("\n@app.get", idx)
    chunk = text[idx:end]
    if "Staff engaged hits count in popular" in chunk:
        print("SKIP staff already included in unified")
    else:
        if OLD_STAFF not in chunk:
            raise SystemExit("staff exclusion line not in unified sql")
        # NOTE: never put Python '#' comments inside the SQL f-string body
        chunk2 = chunk.replace(OLD_STAFF, NEW_STAFF, 1)
        # Update docstring
        chunk2 = chunk2.replace(
            "Post-cutover hits: REAL only — IP must have scroll/click in-range; exclude staff,\n"
            "    quarantine, Meta/cloud prefixes. Page hits = full trail for those IPs.",
            "Post-cutover hits: REAL only — IP must have scroll/click in-range; exclude\n"
            "    quarantine + cloud prefixes (staff reals included so Class/Sailor/Club lists update).",
            1,
        )
        text = text[:idx] + chunk2 + text[end:]
        print("OK include staff reals in unified popular")

    # Most popular entity tables: show top 10 (server already returns 10)
    if "list.slice(0,6).forEach(function(e){" in text:
        text = text.replace(
            "list.slice(0,6).forEach(function(e){",
            "list.slice(0,10).forEach(function(e){",
        )
        print("OK entity UI lists show top 10")
    else:
        print("SKIP entity UI slice already 10 or absent")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print(f"OK api compiled bak={bak}")
    else:
        print("api unchanged")


if __name__ == "__main__":
    main()
