#!/usr/bin/env python3
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARK = "    fleet_title_inner = fleet_header_title\n"
HOOK = (
    "    if str(fleet.get(\"regatta_id\") or \"\").startswith(\"2026-09-24-hmyc-dart-18-nationals\"):\n"
    "        fleet_header_title = \"Fleet\"\n"
    + MARK
)
UNIQUE_BEFORE = (
    '                fleet_header_title = "Fleet"\n'
    "    fleet_title_inner = fleet_header_title\n"
)
UNIQUE_AFTER = (
    '                fleet_header_title = "Fleet"\n'
    "    if str(fleet.get(\"regatta_id\") or \"\").startswith(\"2026-09-24-hmyc-dart-18-nationals\"):\n"
    "        fleet_header_title = \"Fleet\"\n"
    "    fleet_title_inner = fleet_header_title\n"
)


def main() -> None:
    t = API.read_text()
    if UNIQUE_AFTER in t:
        print("ALREADY")
        print("DONE")
        return
    if UNIQUE_BEFORE not in t:
        print("FALLBACK_MARK", t.count(MARK))
        if t.count(MARK) != 1:
            raise SystemExit("NO_UNIQUE")
        t2 = t.replace(MARK, HOOK, 1)
    else:
        t2 = t.replace(UNIQUE_BEFORE, UNIQUE_AFTER, 1)
    API.write_text(t2)
    print("CHANGED", t2 != t)
    i = t2.find("2026-09-24-hmyc-dart-18-nationals\":\n        fleet_header_title = \"Fleet\"")
    print("HOOK", i)
    print(t2[i - 80 : i + 220] if i >= 0 else "MISSING")
    print("DONE")


if __name__ == "__main__":
    main()
