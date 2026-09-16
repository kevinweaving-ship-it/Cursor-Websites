#!/usr/bin/env python3
"""WC Dinghy is no longer the SA pilot. Treat it as a Final gold Event URL."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD_SLUGS = """REGATTA_SA_PILOT_STANDALONE_SLUGS: FrozenSet[str] = frozenset(
    (
        WC_DINGHY_CHAMPS_REGATTA_SLUG,
"""
NEW_SLUGS = """REGATTA_SA_PILOT_STANDALONE_SLUGS: FrozenSet[str] = frozenset(
    (
"""

OLD_SHEET = """    is_wc_fleet_sheet = str(regatta_id or "") == WC_DINGHY_CHAMPS_REGATTA_SLUG
"""
NEW_SHEET = """    is_wc_fleet_sheet = False
"""


def main() -> None:
    api = API.read_text()
    if OLD_SLUGS not in api:
        raise SystemExit("PILOT_SLUG_LIST_MISSING")
    if OLD_SHEET not in api:
        raise SystemExit("WC_FLEET_SHEET_GATE_MISSING")
    api = api.replace(OLD_SLUGS, NEW_SLUGS, 1)
    api = api.replace(OLD_SHEET, NEW_SHEET, 1)
    if "WC_DINGHY_CHAMPS_REGATTA_SLUG," in api.split("REGATTA_SA_PILOT_STANDALONE_SLUGS", 1)[1][:400]:
        raise SystemExit("SLUG_STILL_IN_PILOT")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.wc_depilot.{ts}")
    shutil.copy2(API, bak)
    print("BAK", bak)
    API.write_text(api)
    print("WC_DEPILOT_OK")


if __name__ == "__main__":
    main()
