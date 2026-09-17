#!/usr/bin/env python3
from pathlib import Path
import subprocess

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
api = Path("/var/www/sailingsa/api/api.py").read_text().splitlines()


def q(sql):
    p = subprocess.run(["psql", DSN, "-c", sql], text=True, capture_output=True)
    print(p.stdout or p.stderr)


print("===== CLASSES COLS =====")
q(
    """
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='classes' ORDER BY ordinal_position;
"""
)
q("SELECT * FROM classes WHERE class_id=209 OR class_name ILIKE '%hunter 19%';")

print("===== DEFAULTS =====")
q(
    """
SELECT column_name, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='regattas'
  AND column_default IS NOT NULL
ORDER BY 1;
"""
)
q(
    """
SELECT column_name, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='regatta_blocks'
  AND column_default IS NOT NULL
ORDER BY 1;
"""
)

print("===== EMPTY UPCOMING REGATTAS =====")
q(
    """
SELECT r.regatta_id, r.event_name, r.start_date, r.result_status, r.result_type,
       r.class_layout, r.import_status,
       (SELECT COUNT(*) FROM results x WHERE x.regatta_id=r.regatta_id) AS n_res,
       (SELECT COUNT(*) FROM regatta_blocks b WHERE b.regatta_id=r.regatta_id) AS n_blk
FROM regattas r
WHERE r.start_date >= CURRENT_DATE
ORDER BY r.start_date
LIMIT 20;
"""
)

print("===== CLUB UPCOMING TABLE =====")
for i, l in enumerate(api):
    if "club-upcoming-table" in l:
        print("\n===== around", i + 1, "=====")
        for j in range(max(0, i - 25), min(len(api), i + 40)):
            print(f"{j+1}:{api[j]}")
        break

print("\n===== LEFT LOGO CLASS EVENT =====")
for i, l in enumerate(api):
    if "def _catalogue_regatta_left_logo" in l:
        for j in range(i, min(len(api), i + 80)):
            print(f"{j+1}:{api[j]}")
        break
