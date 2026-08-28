#!/usr/bin/env python3
"""Patch live api.py: merge icon mirrors per-regatta; write all copies via cp.

Newest-mtime wholesale replace let a 1-key Lipton stub wipe the catalog and left
stale R5 / 15:51 copies. Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_ICONS_MERGE_READ_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD_PATHS = '''def _wc_regatta_header_icons_mirror_paths() -> list:
    """All on-disk copies that must stay in sync (API + events_logos_gallery readers)."""
    primary = _wc_regatta_header_icons_json_path()
    out = [primary]
    for p in (
        Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
    ):
        try:
            if p.resolve() != primary.resolve():
                out.append(p)
        except Exception:
            if str(p) != str(primary):
                out.append(p)
    return out
'''

NEW_PATHS = '''def _wc_regatta_header_icons_mirror_paths() -> list:
    """All on-disk copies that must stay in sync (API + events_logos_gallery readers)."""
    # LIPTON_ICONS_MERGE_READ_V1
    primary = _wc_regatta_header_icons_json_path()
    extras = (
        Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/api/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/api/data/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
        Path("/var/www/sailingsa/deploy/wc_regatta_header_icons.json"),
    )
    out = []
    seen = set()
    for p in (primary,) + extras:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out
'''

OLD_READ = '''def _read_wc_regatta_header_icons() -> dict:
    """Read icons JSON; if mirrors diverge, prefer newest mtime (fixes split static/data SSOT)."""
    best: dict = {}
    best_mtime = -1.0
    for p in _wc_regatta_header_icons_mirror_paths():
        try:
            if not p.is_file():
                continue
            mt = float(p.stat().st_mtime)
            o = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(o, dict):
                continue
            if mt >= best_mtime:
                best = o
                best_mtime = mt
        except Exception:
            continue
    return best
'''

NEW_READ = '''def _read_wc_regatta_header_icons() -> dict:
    """Merge mirrors per-regatta; newest mtime wins per key so a 1-entry stub cannot wipe the catalog."""
    # LIPTON_ICONS_MERGE_READ_V1
    merged: dict = {}
    rid_mt: dict = {}
    for p in _wc_regatta_header_icons_mirror_paths():
        try:
            if not p.is_file():
                continue
            mt = float(p.stat().st_mtime)
            o = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(o, dict):
                continue
            for rid, rec in o.items():
                k = str(rid)
                if k not in merged or mt >= rid_mt.get(k, -1.0):
                    merged[k] = rec
                    rid_mt[k] = mt
        except Exception:
            continue
    return merged
'''

OLD_WRITE = '''def _write_wc_regatta_header_icons(data: dict) -> None:
    """Write icons JSON to every known path so API + gallery always agree."""
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\\n"
    for p in _wc_regatta_header_icons_mirror_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(payload, encoding="utf-8")
        except Exception:
            continue
'''

NEW_WRITE = '''def _write_wc_regatta_header_icons(data: dict) -> None:
    """Write icons JSON to every known path so API + gallery always agree."""
    # LIPTON_ICONS_MERGE_READ_V1
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\\n"
    tmp = Path("/tmp/wc_regatta_header_icons.json.tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
    except Exception:
        return
    for p in _wc_regatta_header_icons_mirror_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            os.system("cp %s %s" % (tmp, p))
            os.system("chown www-data:www-data %s >/dev/null 2>&1 || true" % p)
            os.system("chmod 664 %s >/dev/null 2>&1 || true" % p)
        except Exception:
            continue
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    for label, old, new in (
        ("paths", OLD_PATHS, NEW_PATHS),
        ("read", OLD_READ, NEW_READ),
        ("write", OLD_WRITE, NEW_WRITE),
    ):
        n = text.count(old)
        if n != 1:
            print(f"FAIL {label}: found {n}", file=sys.stderr)
            return 1
        text = text.replace(old, new, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
