#!/usr/bin/env python3
"""Fetch live proof: regattas per club, NULL count. Run on live with DB_URL."""
import os
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(os.getenv("DB_URL"))
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
    SELECT c.club_abbrev, COUNT(DISTINCT reg.regatta_id) AS regattas
    FROM results res
    JOIN regattas reg ON reg.regatta_id = res.regatta_id
    JOIN clubs c ON c.club_id = reg.host_club_id
    WHERE res.raced = TRUE
    GROUP BY c.club_abbrev
    ORDER BY regattas DESC
""")
rows = cur.fetchall()
total = sum(r["regattas"] for r in rows)
print("LIVE - Regattas per club (from results)")
print("==================")
for r in rows:
    print(f"{r['club_abbrev']:6} | {r['regattas']}")
print("------|-----")
print(f"TOTAL | {total}")
print("")
print(f"Date: 2026-02-13 | Total regattas with results: {total}")
cur.execute("SELECT COUNT(DISTINCT r.regatta_id) FROM regattas r JOIN results res ON res.regatta_id = r.regatta_id WHERE res.raced = TRUE AND r.host_club_id IS NULL")
n = cur.fetchone()[0]
print(f"Regattas with NULL host_club_id: {n}")
cur.close()
conn.close()
