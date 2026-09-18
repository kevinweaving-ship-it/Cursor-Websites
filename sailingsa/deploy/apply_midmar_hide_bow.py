#!/usr/bin/env python3
"""Hide Midmar Bow No for now. Flip show_bow back to True if they use it."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_HIDE_BOW_v1"

OLD = """    # MIDMAR_STD_COLS_MP_SCROLL_v1: always show Bow No + Boat Name; keep Crew for MP scroll.
    if str(fleet.get("regatta_id") or "").strip() == "2026-09-19-hmyc-midmar-cup":
        show_boat = True
        show_bow = True
        show_crew_col = True
"""

NEW = """    # MIDMAR_STD_COLS_MP_SCROLL_v1 / MIDMAR_HIDE_BOW_v1:
    # Boat Name + Crew stay on. Bow No hidden until they use it (set True).
    if str(fleet.get("regatta_id") or "").strip() == "2026-09-19-hmyc-midmar-cup":
        show_boat = True
        show_bow = False
        show_crew_col = True
"""


def main() -> None:
    api = API.read_text()
    if MARK in api and "show_bow = False" in api and "2026-09-19-hmyc-midmar-cup" in api:
        print("API_ALREADY", MARK)
        return
    if OLD not in api:
        raise SystemExit("API_ANCHOR_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.midmar_hide_bow.{ts}")
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    API.write_text(api.replace(OLD, NEW, 1))
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
