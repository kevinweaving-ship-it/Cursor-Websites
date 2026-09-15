#!/usr/bin/env python3
"""Landing Regatta list: refresh on race day and when results are amended."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD_TTL = "_REGATTA_WITH_COUNTS_TTL_SEC = 7 * 24 * 3600.0"
NEW_TTL = (
    "_REGATTA_WITH_COUNTS_TTL_SEC = 120.0  "
    "# Race day + amendments must show; 7-day freeze hid Vulcan."
)

OLD_COND = '        conditions.append("COALESCE(ec.entries_count, 0) > 0")'
NEW_COND = '''        # Results list + any event whose date range includes today (SA).
        # Start-date-current events must show even before results land.
        conditions.append("""(
            COALESCE(ec.entries_count, 0) > 0
            OR (
                r.start_date IS NOT NULL
                AND r.start_date <= (timezone('Africa/Johannesburg', now()))::date
                AND COALESCE(r.end_date, r.start_date)
                    >= (timezone('Africa/Johannesburg', now()))::date
            )
        )""")'''


def main() -> None:
    text = API.read_text()
    if "Race day + amendments must show" in text and "Start-date-current events must show" in text:
        print("ALREADY")
        return
    missing = []
    if OLD_TTL not in text:
        missing.append("TTL")
    if OLD_COND not in text:
        missing.append("COND")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.regatta_list_fresh.{ts}")
    shutil.copy2(API, bak)
    text = text.replace(OLD_TTL, NEW_TTL, 1)
    text = text.replace(OLD_COND, NEW_COND, 1)
    API.write_text(text)
    print("BACKUP", bak, "PATCHED")


if __name__ == "__main__":
    main()
