#!/usr/bin/env python3
"""Release wrongly quarantined club-share IPs; keep Facebook crawlers quarantined."""
import psycopg2
import psycopg2.extras

DB = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Mark FB crawlers as facebook_crawler (from UA on sessions)
cur.execute(
    """
    UPDATE public.traffic_quarantine_ips q
    SET reason = 'facebook_crawler',
        active = true,
        last_seen_at = NOW()
    FROM public.public_sessions s
    WHERE s.ip_address = q.ip_address
      AND COALESCE(q.active, true) = true
      AND (
        LOWER(COALESCE(s.user_agent,'')) LIKE '%%facebookexternalhit%%'
        OR LOWER(COALESCE(s.user_agent,'')) LIKE '%%facebot%%'
        OR LOWER(COALESCE(s.user_agent,'')) LIKE '%%meta-external%%'
      )
    RETURNING q.ip_address
    """
)
print("FB_MARKED", len(cur.fetchall()))

# First: club-only hits from known Facebook IP ranges → facebook_crawler (preview bot)
cur.execute(
    """
    WITH club_only AS (
      SELECT ip_address
      FROM public.public_page_hits
      WHERE occurred_at > NOW() - INTERVAL '48 hours'
        AND ip_address IS NOT NULL
      GROUP BY ip_address
      HAVING BOOL_AND(split_part(path,'?',1) LIKE '/club/%%'
                      AND split_part(path,'?',1) <> '/club'
                      AND split_part(path,'?',1) <> '/clubs')
    )
    UPDATE public.traffic_quarantine_ips q
    SET reason = 'facebook_crawler',
        active = true,
        last_seen_at = NOW()
    FROM club_only c
    WHERE q.ip_address = c.ip_address
      AND (
        q.ip_address LIKE '173.252.%%'
        OR q.ip_address LIKE '69.63.%%'
        OR q.ip_address LIKE '69.171.%%'
        OR q.ip_address LIKE '31.13.%%'
        OR q.ip_address LIKE '66.220.%%'
        OR q.ip_address LIKE '157.240.%%'
        OR q.ip_address LIKE '185.60.%%'
      )
    RETURNING q.ip_address
    """
)
print("FB_IP_MARKED", len(cur.fetchall()))

# Also insert quarantine for FB-range club-only not yet in table
cur.execute(
    """
    WITH club_only AS (
      SELECT ip_address
      FROM public.public_page_hits
      WHERE occurred_at > NOW() - INTERVAL '48 hours'
        AND ip_address IS NOT NULL
      GROUP BY ip_address
      HAVING BOOL_AND(split_part(path,'?',1) LIKE '/club/%%'
                      AND split_part(path,'?',1) <> '/club'
                      AND split_part(path,'?',1) <> '/clubs')
    )
    INSERT INTO public.traffic_quarantine_ips
      (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
    SELECT c.ip_address, 'facebook_crawler', true, 1, NOW(), NOW()
    FROM club_only c
    WHERE (
        c.ip_address LIKE '173.252.%%'
        OR c.ip_address LIKE '69.63.%%'
        OR c.ip_address LIKE '69.171.%%'
        OR c.ip_address LIKE '31.13.%%'
        OR c.ip_address LIKE '66.220.%%'
        OR c.ip_address LIKE '157.240.%%'
        OR c.ip_address LIKE '185.60.%%'
      )
      AND NOT EXISTS (
        SELECT 1 FROM public.traffic_quarantine_ips q WHERE q.ip_address = c.ip_address
      )
    RETURNING ip_address
    """
)
print("FB_IP_INSERTED", len(cur.fetchall()))

# Release club-only trails that are NOT facebook crawler / FB IP
cur.execute(
    """
    WITH club_only AS (
      SELECT ip_address,
             array_agg(DISTINCT split_part(path,'?',1)) AS paths
      FROM public.public_page_hits
      WHERE occurred_at > NOW() - INTERVAL '48 hours'
        AND ip_address IS NOT NULL
      GROUP BY ip_address
      HAVING BOOL_AND(split_part(path,'?',1) LIKE '/club/%%'
                      AND split_part(path,'?',1) <> '/club'
                      AND split_part(path,'?',1) <> '/clubs')
    )
    UPDATE public.traffic_quarantine_ips q
    SET active = false,
        reason = LEFT(COALESCE(reason,'') || '|released_club_share', 80),
        last_seen_at = NOW()
    FROM club_only c
    WHERE q.ip_address = c.ip_address
      AND COALESCE(q.active, true) = true
      AND COALESCE(q.reason,'') NOT LIKE '%%facebook_crawler%%'
      AND q.ip_address <> '102.218.215.253'
      AND q.ip_address NOT LIKE '173.252.%%'
      AND q.ip_address NOT LIKE '69.63.%%'
      AND q.ip_address NOT LIKE '69.171.%%'
      AND q.ip_address NOT LIKE '31.13.%%'
      AND q.ip_address NOT LIKE '66.220.%%'
      AND q.ip_address NOT LIKE '157.240.%%'
      AND q.ip_address NOT LIKE '185.60.%%'
      AND NOT EXISTS (
        SELECT 1 FROM public.public_sessions s
        WHERE s.ip_address = q.ip_address
          AND (
            LOWER(COALESCE(s.user_agent,'')) LIKE '%%facebookexternalhit%%'
            OR LOWER(COALESCE(s.user_agent,'')) LIKE '%%facebot%%'
            OR LOWER(COALESCE(s.user_agent,'')) LIKE '%%meta-external%%'
          )
      )
    RETURNING q.ip_address, q.reason
    """
)
rel = cur.fetchall()
print("RELEASED_CLUB", len(rel))
for r in rel[:15]:
    print(dict(r))
conn.commit()

# show gbyc status
cur.execute(
    """
    SELECT DISTINCT h.ip_address, q.reason, q.active,
           LEFT(COALESCE(s.user_agent,''), 80) AS ua
    FROM public.public_page_hits h
    LEFT JOIN public.traffic_quarantine_ips q ON q.ip_address = h.ip_address
    LEFT JOIN public.public_sessions s ON s.ip_address = h.ip_address
    WHERE h.path LIKE '/club/gbyc%%'
      AND h.occurred_at > NOW() - INTERVAL '6 hours'
    """
)
print("GBYC")
for r in cur.fetchall():
    print(dict(r))
conn.close()
print("DONE")
