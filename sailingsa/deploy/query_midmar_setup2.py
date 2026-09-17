#!/usr/bin/env python3
import subprocess

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"


def q(sql):
    print("SQL", sql[:80].replace("\n", " "))
    p = subprocess.run(["psql", DSN, "-c", sql], text=True, capture_output=True)
    print(p.stdout)
    if p.returncode:
        print("ERR", p.stderr)


q("SELECT club_id, club_abbrev, club_fullname FROM clubs WHERE club_abbrev ILIKE 'hmyc';")
q("SELECT class_id, class_name FROM classes WHERE class_name ILIKE '%hunter%';")
q(
    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='events' ORDER BY ordinal_position;"
)
q(
    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='regattas' AND column_name IN ('regatta_id','event_name','start_date','end_date','host_club_id','host_club_code','host_club_name','result_status','year','venue','province_code','province_name','result_type');"
)
q("SELECT event_id, event_name, start_date, end_date, host_club_id, regatta_id FROM events WHERE event_name ILIKE '%midmar%' ORDER BY start_date;")
q("SELECT regatta_id, event_name, start_date, host_club_id FROM regattas WHERE event_name ILIKE '%midmar%' OR regatta_id ILIKE '%midmar%' ORDER BY start_date DESC LIMIT 15;")
q("SELECT event_id, event_name, start_date, end_date, host_club_id, regatta_id FROM events WHERE host_club_id IN (SELECT club_id FROM clubs WHERE club_abbrev ILIKE 'hmyc') AND start_date >= CURRENT_DATE - 30 ORDER BY start_date;")
q("\\d events")
