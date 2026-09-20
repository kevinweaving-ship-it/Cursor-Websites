#!/usr/bin/env python3
"""Remove Youth Helm note from Midmar fleet sailed line."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_DROP_SAILED_YH_v1"

OLD = '''    if any(
        isinstance((r.get("race_scores") or {}), dict)
        and (r.get("race_scores") or {}).get("_no_discard")
        for r in rows
    ):
        _sailed_parts.append("Youth Helm races (blue) cannot be discarded")
    sailed_line = ", ".join(_sailed_parts)
'''
NEW = '''    sailed_line = ", ".join(_sailed_parts)  # MIDMAR_DROP_SAILED_YH_v1
'''


def main() -> None:
    text = API.read_text()
    if MARK in text and "Youth Helm races (blue) cannot be discarded" not in text:
        print("ALREADY", MARK)
        return
    if OLD not in text:
        raise SystemExit("ANCHOR")
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.drop_sailed_yh.{ts}"))
    API.write_text(text.replace(OLD, NEW, 1))
    print("OK", MARK)


if __name__ == "__main__":
    main()
