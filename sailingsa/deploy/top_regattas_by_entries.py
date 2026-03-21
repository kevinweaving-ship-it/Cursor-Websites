#!/usr/bin/env python3
"""Print top N regatta URLs by entry count. Uses DATABASE_URL (same as export script)."""
import os
import re
import sys

try:
    import psycopg2
except ImportError:
    print("psycopg2 required", file=sys.stderr)
    sys.exit(1)

DB = os.getenv("DATABASE_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")
TOP_N = 15
BASE = "https://sailingsa.co.za"

def slug_from_name(name):
    if not name or not name.strip():
        return ""
    s = re.sub(r"[^\w\s\-]", "", name).strip().lower()
    s = re.sub(r"\s+", "-", s).strip("-")
    return s

def main():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT r.event_name, COUNT(DISTINCT res.result_id) AS cnt
        FROM regattas r
        LEFT JOIN results res ON res.regatta_id = r.regatta_id
        WHERE r.event_name IS NOT NULL AND TRIM(r.event_name) != ''
        GROUP BY r.regatta_id, r.event_name
        ORDER BY cnt DESC
        LIMIT %s
    """, (TOP_N,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    seen_slugs = set()
    for event_name, cnt in rows:
        slug = slug_from_name(event_name)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        print(f"{BASE}/regatta/{slug}")

if __name__ == "__main__":
    main()
