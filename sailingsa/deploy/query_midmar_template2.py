#!/usr/bin/env python3
from pathlib import Path
import subprocess

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
api = Path("/var/www/sailingsa/api/api.py").read_text().splitlines()


def q(sql):
    p = subprocess.run(["psql", DSN, "-c", sql], text=True, capture_output=True)
    print(p.stdout or p.stderr)


q(
    """
SELECT regatta_id, event_name, year, host_club_id, host_club_code, host_club_name,
       province_code, province_name, start_date, end_date, result_status, result_type,
       scoring_system
FROM regattas WHERE regatta_id='2026-04-27-hunters-nationals';
"""
)
q("SELECT province_code FROM clubs WHERE club_id=98;")
q(
    """
SELECT column_name FROM information_schema.columns
WHERE table_name='regattas' AND column_name IN
('venue','venue_raw','scoring_system','class_layout','import_status','result_type');
"""
)

for needle in (
    "club-upcoming-table",
    "is_upcoming:",
    "details_url = source_url",
):
    hits = [i + 1 for i, l in enumerate(api) if needle in l]
    print("HIT", needle, hits[:8])

for i, l in enumerate(api):
    if 'is_upcoming:' in l and "details_url" in "".join(api[i : i + 8]):
        print("\n===== around", i + 1, "=====")
        for j in range(i, min(len(api), i + 20)):
            print(f"{j+1}:{api[j]}")
        break

for i, l in enumerate(api):
    if "club-upcoming-table" in l and "def " in "".join(api[max(0, i - 30) : i + 1]):
        pass
for i, l in enumerate(api):
    if l.startswith("def ") and "club" in l.lower() and "upcoming" in l.lower():
        print("FN", i + 1, l)
