#!/usr/bin/env python3
from pathlib import Path
import sys

OLD = "mm-lipton-reels-card.js?v=mmr124"
NEW = "mm-lipton-reels-card.js?v=mmr125"


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
    text = path.read_text(encoding="utf-8")
    if NEW in text and OLD not in text:
        print("already", path)
        return 0
    if text.count(OLD) != 1:
        raise SystemExit(f"{OLD} count {text.count(OLD)}")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
