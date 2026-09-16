#!/usr/bin/env python3
"""GOLD Event header status: Results are X / D Mon YYYY HH:MM on all Event URLs."""
from pathlib import Path
import shutil
import time

SHEET = Path("/var/www/sailingsa/sailingsa/backend/cape_classic_fleet_sheet.py")

OLD = """    wrapped = f'<div class="status-line">{raw}</div>'
    if not is_cape_classic_2026_zvy_event(regatta_id):
        return wrapped
    plain = re.sub(r"<[^>]+>", " ", raw)
"""

NEW = """    wrapped = f'<div class="status-line">{raw}</div>'
    # GOLD: all Event URLs — Results are X, then D Mon YYYY HH:MM on the next line.
    plain = re.sub(r"<[^>]+>", " ", raw)
"""


def main() -> None:
    text = SHEET.read_text()
    if "GOLD: all Event URLs — Results are X, then D Mon YYYY HH:MM" in text:
        print("ALREADY")
        return
    if OLD not in text:
        raise SystemExit("BLOCK_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = SHEET.with_name(f"cape_classic_fleet_sheet.py.bak.status_gold.{ts}")
    shutil.copy2(SHEET, bak)
    SHEET.write_text(text.replace(OLD, NEW, 1))
    print("BACKUP", bak, "PATCHED")


if __name__ == "__main__":
    main()
