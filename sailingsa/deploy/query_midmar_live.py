#!/usr/bin/env python3
"""Dump live Midmar / Hunter 19 / HMYC facts needed to create the Event URL."""
from pathlib import Path
import subprocess

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
api = Path("/var/www/sailingsa/api/api.py").read_text().splitlines()


def q(sql):
    p = subprocess.run(["psql", DSN, "-c", sql], text=True, capture_output=True)
    print(p.stdout or p.stderr)
    if p.returncode:
        print("ERR", p.stderr)


print("===== EVENT 139940 =====")
q(
    """
SELECT event_id, event_name, start_date, end_date, event_status, class_layout,
       host_club_id, host_club_name_raw, venue_raw, location_raw, category,
       source, source_event_id, source_url, regatta_id, result_expectation,
       activity_kind
FROM events WHERE event_id = 139940;
"""
)

print("===== HMYC / HUNTER 19 =====")
q("SELECT club_id, club_abbrev, club_fullname, province_code FROM clubs WHERE club_id=98;")
q(
    """
SELECT class_id, class_name, class_canonical, logo_url, logo_path
FROM classes WHERE class_id=209 OR class_name ILIKE '%hunter 19%';
"""
)

print("===== REGATTAS COLS =====")
q(
    """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='regattas'
ORDER BY ordinal_position;
"""
)

print("===== BLOCKS COLS =====")
q(
    """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='regatta_blocks'
ORDER BY ordinal_position;
"""
)

print("===== HUNTER TEMPLATES =====")
q(
    """
SELECT * FROM regattas
WHERE regatta_id IN (
  '2026-07-19-hbyc-hunter-19-winter-26-saturdays',
  '2026-04-27-hunters-nationals'
);
"""
)
q(
    """
SELECT block_id, regatta_id, fleet_label, class_canonical, class_id,
       races_sailed, discard_count, to_count, scoring_system, entries_raced,
       rating_system
FROM regatta_blocks
WHERE regatta_id IN (
  '2026-07-19-hbyc-hunter-19-winter-26-saturdays',
  '2026-04-27-hunters-nationals'
);
"""
)

print("===== HMYC UPCOMING EVENTS =====")
q(
    """
SELECT event_id, event_name, start_date, end_date, host_club_id, regatta_id,
       event_status, source_url
FROM events
WHERE host_club_id = 98
  AND (end_date >= CURRENT_DATE OR (end_date IS NULL AND start_date >= CURRENT_DATE))
ORDER BY start_date;
"""
)

print("===== EVENT_REGATTA_LINKS SAMPLE =====")
q(
    """
SELECT * FROM event_regatta_links
WHERE event_id IN (
  SELECT event_id FROM events WHERE host_club_id=98 AND regatta_id IS NOT NULL LIMIT 3
)
LIMIT 5;
"""
)

print("===== LIVE API HITS =====")
for needle in (
    "details_url = source_url",
    "is_upcoming:",
    "club-upcoming-table",
    "_gold_event_header_all_v1_marker",
    "_catalogue_regatta_left_logo",
):
    hits = [i + 1 for i, l in enumerate(api) if needle in l]
    print("HIT", needle, hits[:10])

for i, l in enumerate(api):
    if "if is_upcoming:" in l and i + 3 < len(api) and "details_url" in api[i + 1]:
        print("\n===== upcoming details around", i + 1, "=====")
        for j in range(i, min(len(api), i + 12)):
            print(f"{j+1}:{api[j]}")
        break
