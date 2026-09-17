#!/usr/bin/env python3
from pathlib import Path

api = Path("/var/www/sailingsa/api/api.py").read_text().splitlines()

for needle in (
    "def _club_event_table_rows",
    "allow_regatta_links",
    "event-details-btn",
    "def _club_events_dashboard",
    "_club_events_tables_html",
):
    hits = [i + 1 for i, l in enumerate(api) if needle in l]
    print("HIT", needle, hits[:15])

for i, l in enumerate(api):
    if l.startswith("def _club_event_table_rows"):
        for j in range(i, min(len(api), i + 120)):
            print(f"{j+1}:{api[j]}")
        break

print("\n===== SERVE CLUB EVENTS CHOICE =====")
for i, l in enumerate(api):
    if "_club_events_tables_html" in l and "def " not in l:
        for j in range(max(0, i - 8), min(len(api), i + 15)):
            print(f"{j+1}:{api[j]}")
        print("---")
