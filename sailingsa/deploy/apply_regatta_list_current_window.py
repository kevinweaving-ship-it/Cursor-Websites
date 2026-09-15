#!/usr/bin/env python3
"""ALL events in the current start-date window must show on the landing Regatta list."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = '''        # Results list + any event whose date range includes today (SA).
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

NEW = '''        # ALL events: have results, OR start date is current / in the live window
        # (today through +5 days SA). Must show even before results land.
        conditions.append("""(
            COALESCE(ec.entries_count, 0) > 0
            OR (
                r.start_date IS NOT NULL
                AND r.start_date <= (timezone('Africa/Johannesburg', now()))::date + 5
                AND COALESCE(r.end_date, r.start_date)
                    >= (timezone('Africa/Johannesburg', now()))::date
            )
        )""")'''


def main() -> None:
    text = API.read_text()
    if "start date is current / in the live window" in text:
        print("ALREADY")
        return
    if OLD not in text:
        raise SystemExit("BLOCK_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.list_current_window.{ts}")
    shutil.copy2(API, bak)
    API.write_text(text.replace(OLD, NEW, 1))
    print("BACKUP", bak, "PATCHED")


if __name__ == "__main__":
    main()
