#!/usr/bin/env python3
"""Fail if public URLs are built as /{entity}/{db_id}-{slug}.

Inbound 301s of old /class/7-420 bookmarks are allowed. Emitting that shape is not.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIR_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    "sailingsa/deploy",
}

SKIP_NAME_PREFIXES = ("dump_", "apply_class_url_no_id", "restore_live_api_urls")
SKIP_NAMES = {Path(__file__).name}

# Construction only. Mentions of the banned form as "never" are not these strings.
FORBIDDEN = (
    '/class/{cid}-',
    '/class/{class_id}-',
    '/class/{cid_int}-',
    '/class/{int(rcid)}-',
    "row.class_id + '-'",
    "class_id) + '-'",
    "classId) + '-'",
    "String(cid) + '-'",
    "String(c.class_id) + '-'",
    "/club/club-{cid}",
    "/club/club-{id}",
    "{cid}-{_class_canonical_slug",
    "{class_id}-{_class_canonical_slug",
    "{cid_int}-{canon}",
)

SCAN_SUFFIXES = {".py", ".js", ".html"}


def skip_path(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if path.name in SKIP_NAMES:
        return True
    if path.name.startswith(SKIP_NAME_PREFIXES):
        return True
    parts = set(path.parts)
    if parts & SKIP_DIR_PARTS:
        return True
    if "sailingsa/deploy" in rel:
        return True
    return False


def main() -> int:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if skip_path(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for needle in FORBIDDEN:
            if needle in text:
                hits.append(f"{rel}: {needle}")
    if hits:
        print("FORBIDDEN public URL builders (database id glued onto slug):")
        for h in hits:
            print(f"  {h}")
        print("\nPublic class URL is /class/420 — never /class/7-420.")
        return 1
    print("ok: no {id}-{slug} public URL builders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
