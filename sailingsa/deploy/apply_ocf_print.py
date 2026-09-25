#!/usr/bin/env python3
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    t = API.read_text()
    before = t
    reps = [
        (
            'WC_AUTO_CODES = frozenset(\n    {"DNC", "DNS", "OCS", "UFD", "BFD", "DNF", "RET", "DSQ", "DNE", "NSC"}\n)',
            'WC_AUTO_CODES = frozenset(\n    {"DNC", "DNS", "OCS", "UFD", "BFD", "DNF", "RET", "DSQ", "DNE", "NSC", "OCF"}\n)',
        ),
        (
            '_WC_ENTRIES_PLUS1_CODES = ("DNC",)',
            '_WC_ENTRIES_PLUS1_CODES = ("DNC", "OCF")',
        ),
    ]
    for a, b in reps:
        n = t.count(a)
        print("MARK", n, a[:40])
        if n != 1:
            raise SystemExit(f"MARK_COUNT {n}")
        t = t.replace(a, b, 1)
    if t == before:
        print("NOCHANGE")
    else:
        API.write_text(t)
    t2 = API.read_text()
    print("AUTO_OCF", '"OCF"' in t2[t2.find("WC_AUTO_CODES") : t2.find("WC_AUTO_CODES") + 200])
    print("ENT_OCF", '("DNC", "OCF")' in t2)
    print("CHANGED", t2 != before)
    print("DONE")


if __name__ == "__main__":
    main()
