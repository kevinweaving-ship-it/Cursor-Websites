#!/usr/bin/env python3
"""Patch live api.py: Lipton Event Logo uses the event year, not hardcoded 2025.

2026 Lipton URL was serving /artwork/Event Logo/Lipton-Challenge-Cup-2025.png.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

DEFAULT_PATH = Path("/var/www/sailingsa/api/api.py")

HELPER = '''def _lipton_challenge_event_logo(regatta_id: str) -> str:
    """Year-stamped Lipton Event Logo; fall back to 2025 file if that year is missing on disk."""
    fallback = "/artwork/Event Logo/Lipton-Challenge-Cup-2025.png"
    rid = str(regatta_id or "").strip()
    m = re.match(r"^(\\d{4})-", rid)
    if not m:
        return fallback
    y = m.group(1)
    rel = f"Event Logo/Lipton-Challenge-Cup-{y}.png"
    public = f"/artwork/{rel}"
    roots = []
    try:
        roots.append(os.path.join(ARTWORK_DIR, rel))
    except Exception:
        pass
    roots.append(f"/var/www/sailingsa/artwork/{rel}")
    roots.append(f"/var/www/sailingsa/api/artwork/{rel}")
    for path in roots:
        try:
            if os.path.isfile(path):
                return public
        except Exception:
            pass
    return fallback


'''

IS_LIPTON_FN = '''def _regatta_is_lipton_challenge(regatta_id: str) -> bool:
    rid = str(regatta_id or "").strip().lower()
    return "lipton-challenge-cup" in rid or rid.endswith("-lipton-cup")


'''

FLEET_OLD = '''    if rid and _regatta_is_lipton_challenge(rid):
        event_logo = "/artwork/Event Logo/Lipton-Challenge-Cup-2025.png"
        for needle, src, _label in _CLUB_EVENT_LOGO_RULES:
            if "lipton" in str(needle).lower() and src:
                event_logo = src
                break
'''

FLEET_NEW = '''    if rid and _regatta_is_lipton_challenge(rid):
        event_logo = _lipton_challenge_event_logo(rid)
'''

NAMED_OLD = '''    """Named Event/Class/Sponsor artwork from _CLUB_EVENT_LOGO_RULES — fill blanks, never invent."""
    hay = f"{(regatta_name or '').lower()} {str(regatta_id or '').lower()}"
'''

NAMED_NEW = '''    """Named Event/Class/Sponsor artwork from _CLUB_EVENT_LOGO_RULES — fill blanks, never invent."""
    if _regatta_is_lipton_challenge(regatta_id or ""):
        return _lipton_challenge_event_logo(regatta_id or "")
    hay = f"{(regatta_name or '').lower()} {str(regatta_id or '').lower()}"
'''

CATALOGUE_OLD = '''    if key:
        row = idx.get(key)
        path = str((row or {}).get("path") or "").strip()
        href = _catalogue_event_href_for_row(row)
        if path and href:
            return path, href
'''

CATALOGUE_NEW = '''    if key:
        row = idx.get(key)
        path = str((row or {}).get("path") or "").strip()
        href = _catalogue_event_href_for_row(row)
        if path and href:
            if _regatta_is_lipton_challenge(rid):
                path = _lipton_challenge_event_logo(rid)
            return path, href
'''


def patch_text(s: str) -> str:
    if (
        "def _lipton_challenge_event_logo(" in s
        and FLEET_NEW in s
        and NAMED_NEW in s
        and CATALOGUE_NEW in s
    ):
        return s
    if IS_LIPTON_FN not in s:
        raise SystemExit("_regatta_is_lipton_challenge block not found")
    if s.count(IS_LIPTON_FN) != 1:
        raise SystemExit("_regatta_is_lipton_challenge block not unique")
    if "def _lipton_challenge_event_logo(" not in s:
        s = s.replace(IS_LIPTON_FN, IS_LIPTON_FN + HELPER, 1)
    if FLEET_OLD not in s:
        if FLEET_NEW not in s:
            raise SystemExit("Lipton fleet logo assignment not found")
    else:
        if s.count(FLEET_OLD) != 1:
            raise SystemExit("Lipton fleet logo assignment not unique")
        s = s.replace(FLEET_OLD, FLEET_NEW, 1)
    if NAMED_OLD not in s:
        if NAMED_NEW not in s:
            raise SystemExit("named-rules hay assignment not found")
    else:
        if s.count(NAMED_OLD) != 1:
            raise SystemExit("named-rules hay assignment not unique")
        s = s.replace(NAMED_OLD, NAMED_NEW, 1)
    if CATALOGUE_OLD not in s:
        if CATALOGUE_NEW not in s:
            raise SystemExit("catalogue left-logo return not found")
    else:
        if s.count(CATALOGUE_OLD) != 1:
            raise SystemExit("catalogue left-logo return not unique")
        s = s.replace(CATALOGUE_OLD, CATALOGUE_NEW, 1)
    if "def _lipton_challenge_event_logo(" not in s:
        raise SystemExit("helper missing after patch")
    if FLEET_OLD in s:
        raise SystemExit("hardcoded 2025 fleet logo assignment still present")
    return s


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH)
    original = path.read_text(encoding="utf-8")
    updated = patch_text(original)
    if updated == original:
        print("already patched", path)
        return 0
    bak = path.with_name(path.name + ".bak-lipton-logo-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, bak)
    path.write_text(updated, encoding="utf-8")
    print("patched", path)
    print("backup", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
