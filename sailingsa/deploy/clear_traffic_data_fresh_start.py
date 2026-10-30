#!/usr/bin/env python3
"""Wipe lean/public traffic data on live so /traffic starts fresh.

Does NOT touch user_accounts, user_sessions, results, sailors, etc.
Keeps traffic_quarantine_ips table but clears rows (optional re-seed server IP).
"""
from __future__ import annotations

import psycopg2

DB = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"

TABLES = [
    "public_page_hits",
    "public_sessions",
    "public_visit_sessions",
    "session_page_hits",
    "traffic_events",
    "traffic_quarantine_ips",
]

# Optional: keep our own server/agent IPs blocked so self-hits stay out of Live
RESEED_QUARANTINE = [
    ("102.218.215.253", "server_self"),
]


def main() -> None:
    conn = psycopg2.connect(DB)
    conn.autocommit = False
    cur = conn.cursor()
    print("=== before ===")
    for t in TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM public.{t}")
            print(f"  {t}: {cur.fetchone()[0]}")
        except Exception as e:
            conn.rollback()
            print(f"  {t}: skip ({e})")

    for t in TABLES:
        try:
            cur.execute(f"TRUNCATE TABLE public.{t} RESTART IDENTITY CASCADE")
            print(f"TRUNCATED {t}")
        except Exception as e:
            conn.rollback()
            try:
                cur.execute(f"DELETE FROM public.{t}")
                print(f"DELETED {t} ({cur.rowcount})")
            except Exception as e2:
                conn.rollback()
                print(f"FAIL {t}: {e2}")

    for ip, reason in RESEED_QUARANTINE:
        try:
            cur.execute(
                """
                INSERT INTO public.traffic_quarantine_ips
                    (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
                VALUES (%s, %s, true, 1, NOW(), NOW())
                ON CONFLICT (ip_address) DO UPDATE SET
                    active = true,
                    reason = EXCLUDED.reason,
                    last_seen_at = NOW()
                """,
                (ip, reason),
            )
            print(f"reseed quarantine {ip} ({reason})")
        except Exception as e:
            conn.rollback()
            print(f"reseed fail {ip}: {e}")

    conn.commit()
    print("=== after ===")
    for t in TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM public.{t}")
            print(f"  {t}: {cur.fetchone()[0]}")
        except Exception as e:
            conn.rollback()
            print(f"  {t}: skip ({e})")
    cur.close()
    conn.close()
    print("DONE — traffic slate clean")


if __name__ == "__main__":
    main()
