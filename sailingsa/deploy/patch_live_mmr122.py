#!/usr/bin/env python3
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
OLD = "mm-lipton-reels-card.js?v=mmr121"
NEW = "mm-lipton-reels-card.js?v=mmr122"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    n = text.count(OLD)
    if n < 1:
        if NEW in text:
            print("already mmr122")
            return 0
        raise SystemExit(f"{path}: {OLD} count {n}")
    path.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("bumped", n, "to mmr122")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
