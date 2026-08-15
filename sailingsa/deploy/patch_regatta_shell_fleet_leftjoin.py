#!/usr/bin/env python3
"""Allow empty result shells to still render fleet + sailed lines (LEFT JOIN)."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
OLD = '''            regatta_scoring = (row.get("scoring_system") or "").strip().lower()
            is_mac_endurance = regatta_scoring.startswith("mac endurance")
            results_join = "LEFT JOIN results res" if is_mac_endurance else "JOIN results res"'''
NEW = '''            regatta_scoring = (row.get("scoring_system") or "").strip().lower()
            is_mac_endurance = regatta_scoring.startswith("mac endurance")
            # Shells with blocks but no result rows yet: still render fleet + sailed lines.
            cur.execute(
                "SELECT 1 FROM results WHERE regatta_id = %s LIMIT 1",
                (regatta_id,),
            )
            has_result_rows = cur.fetchone() is not None
            results_join = (
                "LEFT JOIN results res"
                if (is_mac_endurance or not has_result_rows)
                else "JOIN results res"
            )'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if "Shells with blocks but no result rows" in text:
        print("already patched")
        return 0
    if OLD not in text:
        raise SystemExit("anchor not found")
    bak = API.with_suffix(f".py.bak_fleet_leftjoin_{int(time.time())}")
    shutil.copy2(API, bak)
    API.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
