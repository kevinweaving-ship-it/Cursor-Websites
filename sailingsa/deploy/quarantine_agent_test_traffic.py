#!/usr/bin/env python3
"""Quarantine + purge Cursor agent / clean-trail test junk from live traffic."""
from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor

DB = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"


def main() -> None:
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.traffic_quarantine_ips (
            ip_address text PRIMARY KEY,
            reason text,
            active boolean NOT NULL DEFAULT true,
            hit_count integer NOT NULL DEFAULT 1,
            first_seen_at timestamptz NOT NULL DEFAULT NOW(),
            last_seen_at timestamptz NOT NULL DEFAULT NOW()
        )
        """
    )

    cur.execute(
        r"""
        SELECT DISTINCT ip_address FROM public.public_page_hits
        WHERE occurred_at > NOW() - INTERVAL '6 hours'
          AND (
            path ~* '^/sailor/(clean-trail|local-trail|cleantrail)'
            OR path ILIKE '%%clean-trail%%'
            OR path ILIKE '%%local-trail%%'
            OR visitor_id LIKE 'cleantrail%%'
            OR visitor_id LIKE 'localtrail%%'
            OR visitor_id LIKE 'testclean%%'
          )
        """
    )
    ips = sorted({(r["ip_address"] or "").strip() for r in cur.fetchall() if r["ip_address"]})

    # Known agent / self-test IPs from tonight (even if hits already purged)
    for extra in (
        "102.218.215.253",
        "13.219.19.81",
        "3.234.162.247",
        "52.20.19.128",
        "18.215.58.177",
        "34.237.170.126",
        "54.85.237.109",
        "50.19.105.50",
        "35.174.58.0",
    ):
        if extra not in ips:
            ips.append(extra)

    print("quarantine ips:", ips)
    for ip in ips:
        if not ip or ip in ("127.0.0.1", "::1"):
            continue
        cur.execute(
            """
            INSERT INTO public.traffic_quarantine_ips
                (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
            VALUES (%s, %s, true, 1, NOW(), NOW())
            ON CONFLICT (ip_address) DO UPDATE SET
                active = true,
                reason = EXCLUDED.reason,
                hit_count = public.traffic_quarantine_ips.hit_count + 1,
                last_seen_at = NOW()
            """,
            (ip[:80], "agent_test_traffic"),
        )
        print("  quarantined", ip)

    cur.execute(
        r"""
        DELETE FROM public.public_page_hits
        WHERE path ~* '^/sailor/(clean-trail|local-trail|cleantrail)'
           OR path ILIKE '%%clean-trail%%'
           OR path ILIKE '%%local-trail%%'
        """
    )
    print("deleted fake-path hits", cur.rowcount)

    if ips:
        cur.execute(
            """
            DELETE FROM public.public_page_hits
            WHERE ip_address = ANY(%s)
              AND occurred_at > NOW() - INTERVAL '6 hours'
            """,
            (ips,),
        )
        print("deleted hits from agent ips (6h)", cur.rowcount)

        cur.execute(
            """
            DELETE FROM public.public_sessions
            WHERE ip_address = ANY(%s)
               OR visitor_id LIKE 'cleantrail%%'
               OR visitor_id LIKE 'localtrail%%'
               OR visitor_id LIKE 'testclean%%'
            """,
            (ips,),
        )
        print("deleted sessions", cur.rowcount)

        try:
            cur.execute(
                """
                DELETE FROM public.public_visit_sessions
                WHERE ip_address = ANY(%s)
                   OR visitor_id LIKE 'cleantrail%%'
                   OR visitor_id LIKE 'localtrail%%'
                """,
                (ips,),
            )
            print("deleted visit_sessions", cur.rowcount)
        except Exception as e:
            print("visit_sessions", e)

    conn.commit()

    cur.execute(
        """
        SELECT visitor_id, ip_address, last_path, last_activity
        FROM public.public_sessions
        WHERE last_activity > NOW() - INTERVAL '15 minutes'
        ORDER BY last_activity DESC LIMIT 12
        """
    )
    print("remaining live sessions:")
    for r in cur.fetchall():
        print(" ", dict(r))

    cur.execute(
        """
        SELECT ip_address, reason, active FROM public.traffic_quarantine_ips
        WHERE reason = 'agent_test_traffic' ORDER BY last_seen_at DESC
        """
    )
    print("agent quarantines:", len(cur.fetchall()))
    conn.close()
    print("DONE")


if __name__ == "__main__":
    main()
