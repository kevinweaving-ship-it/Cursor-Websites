#!/usr/bin/env python3
"""Patch live api.py: Lipton next race is max(filled)+1, not first hole.

race_times often only stores R4/R5. First-hole logic would arm R1 if DB blips.
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_NEXT_RN_MAX_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''    for n in range(1, max(max_n + 2, 2)):
        if n not in filled:
            return f"R{n}"
    return f"R{max_n + 1}" if max_n else "R1"
'''

NEW = '''    if "lipton" in rid.lower() and filled:
        # ''' + MARKER + ''' race_times may only hold latest Rn; don't arm R1.
        return f"R{max(filled) + 1}"
    for n in range(1, max(max_n + 2, 2)):
        if n not in filled:
            return f"R{n}"
    return f"R{max_n + 1}" if max_n else "R1"
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL next-key: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
