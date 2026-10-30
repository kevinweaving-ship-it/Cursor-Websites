#!/usr/bin/env python3
"""Release quarantines where IP had scroll/click engagement."""
import psycopg2
import psycopg2.extras

DB = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute(
    """
    WITH eng AS (
      SELECT DISTINCT ip_address
      FROM public.public_page_hits
      WHERE occurred_at > NOW() - INTERVAL '48 hours'
        AND COALESCE(engagement::text,'') NOT IN ('','[]','null','None')
    )
    UPDATE public.traffic_quarantine_ips q
    SET active = false,
        reason = LEFT(COALESCE(reason,'') || '|released_scroll_click', 80),
        last_seen_at = NOW()
    FROM eng
    WHERE q.ip_address = eng.ip_address
      AND COALESCE(q.active, true) = true
      AND q.ip_address <> '102.218.215.253'
    RETURNING q.ip_address, q.reason
    """
)
print("RELEASED", cur.fetchall())
conn.commit()
# Ekow / Thabo status
for ip in ("102.219.170.27", "43.172.196.83", "43.172.195.69"):
    cur.execute(
        "SELECT reason, active FROM public.traffic_quarantine_ips WHERE ip_address=%s",
        (ip,),
    )
    print(ip, cur.fetchone())
conn.close()
print("DONE")
