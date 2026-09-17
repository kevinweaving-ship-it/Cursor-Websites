#!/usr/bin/env python3
import subprocess

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"


def q(sql):
    p = subprocess.run(["psql", DSN, "-c", sql], text=True, capture_output=True)
    print(p.stdout or p.stderr)


q(
    """
SELECT event_id, source, source_event_id, source_url, event_name, start_date, end_date,
       host_club_id, host_club_name_raw, venue_raw, location_raw, category, event_status,
       regatta_id, result_expectation, activity_kind, class_layout, extras
FROM events WHERE event_id = 139940;
"""
)
q(
    """
SELECT regatta_id, event_name, year, host_club_id, host_club_code, host_club_name,
       province_code, province_name, start_date, end_date, result_status, result_type,
       venue, scoring_system
FROM regattas
WHERE regatta_id IN (
  '2026-07-19-hbyc-hunter-19-winter-26-saturdays',
  '2026-04-27-hunters-nationals',
  '2026-05-30-leopard-challenge-leg-2'
);
"""
)
q(
    """
SELECT block_id, fleet_label, class_canonical, class_id, races_sailed, discard_count,
       to_count, scoring_system, entries_raced
FROM regatta_blocks
WHERE regatta_id IN (
  '2026-07-19-hbyc-hunter-19-winter-26-saturdays',
  '2026-04-27-hunters-nationals'
);
"""
)
q("SELECT unnest(enum_range(NULL::regatta_result_type));")
q(
    """
SELECT column_name FROM information_schema.columns
WHERE table_name='event_regatta_links' ORDER BY 1;
"""
)
q(
    """
SELECT province_code, province_name FROM clubs WHERE club_id=98;
"""
)
q(
    """
SELECT column_name FROM information_schema.columns
WHERE table_name='regattas' AND column_name ILIKE '%venue%';
"""
)
