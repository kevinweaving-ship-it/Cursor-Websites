#!/usr/bin/env python3
"""Page/URL trails and stay logging keyed by IP (not sailor guess / shared cookie)."""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old_trail = '''def _lean_session_page_trail(cur, *, visitor_id: str = "", ip: str = "", session_id: str = "") -> list:
    """Chronological URL stays for one live session (path + dwell)."""
    trail = []
    vid = (visitor_id or "").strip()
    ip_s = (ip or "").strip()
    sid = (session_id or "").strip()
    try:
        if not table_exists("public_page_hits"):
            return []
        rows = []
        if vid:
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (vid,),
            )
            rows = list(cur.fetchall() or [])
        if not rows and sid:
            sess_vid = f"sess:{sid[:32]}"
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (sess_vid,),
            )
            rows = list(cur.fetchall() or [])
        if not rows and ip_s and table_exists("session_page_hits") and sid:
            try:
                cur.execute(
                    """
                    SELECT path, occurred_at, NULL::timestamptz AS left_at, NULL::int AS dwell_seconds
                    FROM public.session_page_hits
                    WHERE session_id = %s
                      AND occurred_at > NOW() - INTERVAL '45 minutes'
                    ORDER BY occurred_at ASC
                    LIMIT 60
                    """,
                    (sid,),
                )
                rows = list(cur.fetchall() or [])
            except Exception:
                rows = []'''

new_trail = '''def _lean_session_page_trail(cur, *, visitor_id: str = "", ip: str = "", session_id: str = "") -> list:
    """Chronological URL stays for one IP session (path + dwell).

    Unique key = IP. Do not merge by sailor guess or shared ssa_vid across IPs.
    """
    trail = []
    vid = (visitor_id or "").strip()
    ip_s = (ip or "").strip()
    sid = (session_id or "").strip()
    try:
        if not table_exists("public_page_hits"):
            return []
        rows = []
        # Prefer IP — pages belong to the IP, not a guessed sailor / cookie.
        if ip_s:
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE ip_address = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (ip_s,),
            )
            rows = list(cur.fetchall() or [])
        elif sid:
            sess_vid = f"sess:{sid[:32]}"
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (sess_vid,),
            )
            rows = list(cur.fetchall() or [])
            if not rows and table_exists("session_page_hits"):
                try:
                    cur.execute(
                        """
                        SELECT path, occurred_at, NULL::timestamptz AS left_at, NULL::int AS dwell_seconds
                        FROM public.session_page_hits
                        WHERE session_id = %s
                          AND occurred_at > NOW() - INTERVAL '45 minutes'
                        ORDER BY occurred_at ASC
                        LIMIT 60
                        """,
                        (sid,),
                    )
                    rows = list(cur.fetchall() or [])
                except Exception:
                    rows = []
        elif vid:
            cur.execute(
                """
                SELECT path, occurred_at, left_at, dwell_seconds
                FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                ORDER BY occurred_at ASC, hit_id ASC
                LIMIT 60
                """,
                (vid,),
            )
            rows = list(cur.fetchall() or [])'''

if old_trail not in text:
    raise SystemExit("trail fn head not found")
text = text.replace(old_trail, new_trail, 1)

# Fix _record_url_stay_hit to dedupe/open by IP when present
old_rec = '''    lock_key = f"traffic:vid:{vid}" if vid else f"traffic:ip:{ip}"
    try:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (lock_key,))
    except Exception:
        pass
    try:
        cur.execute(
            """
            SELECT path, left_at, hit_id FROM public.public_page_hits
            WHERE visitor_id = %s
            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
            LIMIT 1
            """,
            (vid,),
        )'''

new_rec = '''    # Lock + open-hit check by IP when known (unique visitor); else visitor_id.
    lock_key = f"traffic:ip:{ip}" if ip else f"traffic:vid:{vid}"
    try:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (lock_key,))
    except Exception:
        pass
    try:
        if ip:
            cur.execute(
                """
                SELECT path, left_at, hit_id FROM public.public_page_hits
                WHERE ip_address = %s
                ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (ip,),
            )
        else:
            cur.execute(
                """
                SELECT path, left_at, hit_id FROM public.public_page_hits
                WHERE visitor_id = %s
                ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (vid,),
            )'''

if old_rec not in text:
    raise SystemExit("record_url_stay_hit lock block not found")
text = text.replace(old_rec, new_rec, 1)

# Close open hits: already supports ip+visitor — ensure callers pass IP.
# Soft hint note already says maybe — ensure trail-meta lists IP first (already does).

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(text)-len(orig)} bytes)")
