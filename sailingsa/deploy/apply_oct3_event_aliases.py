#!/usr/bin/env python3
"""Surgical live api.py alias add for 420/505/Dabchick event URLs. Do not replace whole file."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

NEW = [
    '    "505-nationals": "2026-09-24-ayc-505-nationals",\n',
    '    "2026-505-nationals": "2026-09-24-ayc-505-nationals",\n',
    '    "dabchick-gauteng-regionals": "2026-09-24-ayc-dabchick-gauteng-regionals",\n',
    '    "2026-dabchick-gauteng-regionals": "2026-09-24-ayc-dabchick-gauteng-regionals",\n',
    '    "gauteng-regionals-2026": "2026-09-24-ayc-dabchick-gauteng-regionals",\n',
]


def main() -> None:
    t = API.read_text()
    mark = '    "2026-420-nationals": "2026-09-25-tsc-420-nationals",\n'
    if "2026-09-24-ayc-505-nationals" in t:
        print("ALIASES_ALREADY")
    elif mark not in t:
        raise SystemExit("MARK_MISSING")
    else:
        t = t.replace(mark, mark + "".join(NEW), 1)
        API.write_text(t)
        print("ALIASES_ADDED")
    t2 = API.read_text()
    print("HAS_505", "2026-09-24-ayc-505-nationals" in t2)
    print("HAS_DAB", "2026-09-24-ayc-dabchick-gauteng-regionals" in t2)
    print("HAS_420", "420-nationals" in t2)


if __name__ == "__main__":
    main()
