#!/usr/bin/env python3
"""Reorder fleet results columns: Rank, Bow No, Sail No, Boat Name, Club, Helm, Crew, …"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

# Applied live 2026-08-15: move show_bow block before sail_no in thead + row_html
# of _render_result_sheet_fleet. Restore from api.py.bak_col_order_* if needed.

def main() -> int:
    text = API.read_text(encoding="utf-8")
    # idempotent check: Bow No th appears before Sail No th in thead builder
    i = text.find('sail_label = "SailNo" if')
    j = text.find("thead = \"\"", i)
    k = text.find("if show_races:", j)
    chunk = text[j:k]
    bow_i = chunk.find("Bow No")
    sail_i = chunk.find("sail-col")
    if bow_i >= 0 and sail_i >= 0 and bow_i < sail_i:
        print("column order already Rank…Bow…Sail")
        return 0
    print("manual patch required — see live bak_col_order backup")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
