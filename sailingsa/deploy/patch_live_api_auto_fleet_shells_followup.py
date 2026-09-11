#!/usr/bin/env python3
"""Follow-up: escape LIKE %%; never treat 'Ilca 4' as a class (catalogue is Ilca 4.7)."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
REPLACEMENTS = [
    (
        "AND %s LIKE (rb.regatta_id || '-%')",
        "AND %s LIKE (rb.regatta_id || '-%%')",
    ),
    (
        '''    if tail_slug in ("ilca-4-16", "ilca-4-7", "ilca-4.7", "ilca-47", "ilca-4"):
        return "ILCA 4.7"''',
        '''    # There is no class "Ilca 4". classes.class_name is Ilca 4.7.
    fl_compact = re.sub(r"[^a-z0-9]+", "", fl.lower())
    if fl_compact in ("ilca4", "laser4"):
        return "ILCA 4.7"
    if tail_slug in ("ilca-4-16", "ilca-4-7", "ilca-4.7", "ilca-47", "ilca-4"):
        return "ILCA 4.7"''',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
