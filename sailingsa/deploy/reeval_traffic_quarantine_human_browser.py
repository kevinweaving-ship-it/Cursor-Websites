#!/usr/bin/env python3
"""Release quarantine IPs that look like real browser traffic on valid page URLs."""
from __future__ import annotations

import os
import sys

import psycopg2
import psycopg2.extras

DB = os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
if not DB:
    # pull from systemd
    import subprocess

    env = subprocess.check_output(
        ["systemctl", "show", "sailingsa-api", "-p", "Environment", "--value"], text=True
    )
    for part in env.split():
        if part.startswith("DATABASE_URL=") or part.startswith("DB_URL="):
            DB = part.split("=", 1)[1]
            break
if not DB:
    print("No DATABASE_URL", file=sys.stderr)
    sys.exit(1)

SQL = """
WITH candidates AS (
  SELECT DISTINCT q.ip_address
  FROM public.traffic_quarantine_ips q
  WHERE COALESCE(q.active, true) = true
    AND (
      EXISTS (
        SELECT 1 FROM public.public_sessions s
        WHERE s.ip_address = q.ip_address
          AND COALESCE(s.user_agent, '') ~* 'Mozilla/'
          AND COALESCE(s.user_agent, '') ~* '(Chrome/|CriOS/|Firefox/|FxiOS/|Safari/|Edg/|EdgiOS/)'
          AND COALESCE(s.user_agent, '') !~* '(bot|crawl|spider|slurp|headless|wget|curl/|python-requests|scrapy|facebookexternalhit)'
          AND COALESCE(s.user_agent, '') ~* '(iPhone|iPad|Android|Mobile|Windows NT|Macintosh|Mac OS X|CrOS|Linux x86_64|X11)'
          AND COALESCE(s.last_path, '') ~ '^/(sailor|boat|regatta|class|club|events|news|about|stats|rankings|standings)(/|$)'
      )
      OR EXISTS (
        SELECT 1 FROM public.public_page_hits h
        WHERE h.ip_address = q.ip_address
          AND COALESCE(h.path, '') ~ '^/(sailor|boat|regatta|class|club|events|news|about|stats|rankings|standings)(/|$)'
          AND EXISTS (
            SELECT 1 FROM public.public_sessions s2
            WHERE s2.ip_address = q.ip_address
              AND COALESCE(s2.user_agent, '') ~* 'Mozilla/'
              AND COALESCE(s2.user_agent, '') ~* '(Chrome/|CriOS/|Firefox/|Safari/|Edg/)'
              AND COALESCE(s2.user_agent, '') !~* '(bot|crawl|spider|headless|wget|curl/|python-requests|scrapy)'
          )
      )
    )
)
UPDATE public.traffic_quarantine_ips q
SET active = false,
    reason = LEFT(COALESCE(q.reason, '') || '|released_human_browser', 80),
    last_seen_at = NOW()
FROM candidates c
WHERE q.ip_address = c.ip_address
  AND COALESCE(q.active, true) = true
RETURNING q.ip_address, q.reason;
"""

conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute(SQL)
rows = cur.fetchall() or []
conn.commit()
print(f"released={len(rows)}")
for r in rows[:20]:
    print(dict(r))
if len(rows) > 20:
    print(f"... and {len(rows) - 20} more")
cur.execute(
    "SELECT COUNT(*)::int AS active FROM public.traffic_quarantine_ips WHERE COALESCE(active,true)=true"
)
print("quarantine_still_active", (cur.fetchone() or {}).get("active"))
cur.close()
conn.close()
