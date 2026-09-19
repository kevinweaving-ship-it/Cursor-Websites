#!/usr/bin/env python3
"""Find DRYC / PRSC and confirm WYAC."""
import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
conn = psycopg2.connect(DSN)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("===== EXACT / LIKE =====")
cur.execute(
    """
    SELECT club_id, club_abbrev, club_fullname
    FROM clubs
    WHERE club_abbrev ILIKE '%DRYC%'
       OR club_abbrev ILIKE '%DRYC%'
       OR club_abbrev ILIKE '%PRSC%'
       OR club_abbrev ILIKE '%WYAC%'
       OR club_fullname ILIKE '%dryc%'
       OR club_fullname ILIKE '%prsc%'
       OR club_fullname ILIKE '%radio sailing%'
       OR club_fullname ILIKE '%pietermaritzburg%'
       OR club_fullname ILIKE '%durban radio%'
       OR club_fullname ILIKE '%deneysville radio%'
    ORDER BY club_abbrev
    """
)
print([dict(r) for r in cur.fetchall()])

print("\n===== ALL ABBREVS =====")
cur.execute("SELECT club_id, club_abbrev, club_fullname FROM clubs ORDER BY club_abbrev")
for r in cur.fetchall():
    ab = (r["club_abbrev"] or "").upper()
    if any(x in ab for x in ("DR", "PR", "WY", "RS", "PM", "DAC")):
        print(dict(r))

print("\n===== LUKE HISTORY =====")
cur.execute(
    """
    SELECT r.regatta_id, r.club_raw, r.club_id, c.club_abbrev
    FROM results r
    LEFT JOIN clubs c ON c.club_id = r.club_id
    WHERE r.helm_sa_sailing_id = 729
    ORDER BY r.result_id DESC
    LIMIT 8
    """
)
print([dict(r) for r in cur.fetchall()])

print("\n===== CRAIG MILLAR HISTORY =====")
cur.execute(
    """
    SELECT r.regatta_id, r.club_raw, r.club_id, c.club_abbrev
    FROM results r
    LEFT JOIN clubs c ON c.club_id = r.club_id
    WHERE r.helm_sa_sailing_id = 177
    ORDER BY r.result_id DESC
    LIMIT 8
    """
)
print([dict(r) for r in cur.fetchall()])

print("\n===== DANI HISTORY =====")
cur.execute(
    """
    SELECT r.regatta_id, r.helm_name, r.club_raw, r.club_id, c.club_abbrev
    FROM results r
    LEFT JOIN clubs c ON c.club_id = r.club_id
    WHERE r.helm_sa_sailing_id = 15579 OR r.helm_sa_sailing_id = 8444
    ORDER BY r.result_id DESC
    LIMIT 10
    """
)
print([dict(r) for r in cur.fetchall()])

cur.close()
conn.close()
