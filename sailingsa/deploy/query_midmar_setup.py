#!/usr/bin/env python3
import subprocess

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"


def q(sql):
    print(sql.strip()[:120])
    print(
        subprocess.check_output(["psql", DSN, "-c", sql], text=True, stderr=subprocess.STDOUT)
    )


q(
    """
SELECT club_id, club_abbrev, club_fullname, province_name
FROM clubs
WHERE club_abbrev ILIKE 'hmyc' OR club_fullname ILIKE '%henley%midmar%'
ORDER BY 1;
"""
)
q(
    """
SELECT class_id, class_name, is_race_class
FROM classes
WHERE class_name ILIKE '%hunter%'
ORDER BY 1;
"""
)
q(
    r"""
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name='events' AND table_schema='public'
ORDER BY ordinal_position;
"""
)
q(
    """
SELECT event_id, event_name, start_date, end_date, host_club_id, host_club_name_raw, regatta_id, category, venue_raw
FROM events
WHERE event_name ILIKE '%midmar%'
   OR (host_club_id = (SELECT club_id FROM clubs WHERE club_abbrev='HMYC' LIMIT 1)
       AND start_date >= CURRENT_DATE)
ORDER BY start_date NULLS LAST;
"""
)
q(
    """
SELECT regatta_id, event_name, start_date, end_date, host_club_id, host_club_code, result_status
FROM regattas
WHERE event_name ILIKE '%midmar%' OR regatta_id ILIKE '%midmar%' OR regatta_id ILIKE '%hmyc%'
ORDER BY start_date DESC NULLS LAST
LIMIT 20;
"""
)
q(
    r"""
SELECT column_name FROM information_schema.columns
WHERE table_name='event_regatta_links' AND table_schema='public'
ORDER BY 1;
"""
)
q(
    """
SELECT event_id, event_name, start_date, end_date, host_club_id, regatta_id, category
FROM events
WHERE host_club_id = (SELECT club_id FROM clubs WHERE club_abbrev='HMYC' LIMIT 1)
ORDER BY start_date DESC NULLS LAST
LIMIT 15;
"""
)
