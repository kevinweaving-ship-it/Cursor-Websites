#!/usr/bin/env python3
"""Every click belongs to an IP; return visits append to that IP's session/pages."""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# 1) Resolve visitor: IP identity first (returns keep same visitor_id for that IP)
old_resolve = '''def _resolve_public_visitor_id(cur, request: Request, ip_address: str) -> str:
    """Sticky visitor: cookie first, else reuse same-IP record (any age), else new id."""
    vid = _public_visitor_id_from_request(request)
    if vid:
        return vid
    ip = (ip_address or "").strip()
    if ip and not _is_noise_public_ip(ip):
        try:
            cur.execute(
                """
                SELECT visitor_id FROM public.public_sessions
                WHERE ip_address = %s
                ORDER BY last_activity DESC NULLS LAST
                LIMIT 1
                """,
                (ip,),
            )
            row = cur.fetchone()
            if row:
                existing = row[0] if not isinstance(row, dict) else row.get("visitor_id")
                if existing:
                    return str(existing)
        except Exception:
            pass
    return uuid.uuid4().hex'''

new_resolve = '''def _resolve_public_visitor_id(cur, request: Request, ip_address: str) -> str:
    """Sticky visitor by IP first (returns keep adding to same IP identity).

    Cookie is only used when this IP has no prior public_sessions row.
    """
    ip = (ip_address or "").strip()
    if ip and not _is_noise_public_ip(ip):
        try:
            cur.execute(
                """
                SELECT visitor_id FROM public.public_sessions
                WHERE ip_address = %s
                ORDER BY last_activity DESC NULLS LAST
                LIMIT 1
                """,
                (ip,),
            )
            row = cur.fetchone()
            if row:
                existing = row[0] if not isinstance(row, dict) else row.get("visitor_id")
                if existing:
                    return str(existing)
        except Exception:
            pass
    vid = _public_visitor_id_from_request(request)
    if vid:
        return vid
    return uuid.uuid4().hex'''

if old_resolve not in text:
    raise SystemExit("resolve visitor not found")
text = text.replace(old_resolve, new_resolve, 1)

# 2) Require IP on every page-hit insert
old_req = '''    ip = (ip_address or "")[:80]
    vid = (visitor_id or "").strip()
    p = _normalize_traffic_path(path)
    if not vid or not _is_document_page_path_for_hit(p):
        return False'''
new_req = '''    ip = (ip_address or "").strip()[:80]
    vid = (visitor_id or "").strip()
    p = _normalize_traffic_path(path)
    # Every click must belong to an IP (unique visitor key).
    if not ip or not vid or not _is_document_page_path_for_hit(p):
        return False'''
if old_req not in text:
    raise SystemExit("record require block not found")
text = text.replace(old_req, new_req, 1)

# 3) On return (idle): keep first_seen_at + created_at for IP — do not reset history clock
old_conflict = '''        ON CONFLICT (visitor_id) DO UPDATE SET
            last_activity = NOW(),
            last_path = EXCLUDED.last_path,
            user_agent = COALESCE(NULLIF(EXCLUDED.user_agent, ''), public.public_sessions.user_agent),
            ip_address = EXCLUDED.ip_address,
            first_seen_at = COALESCE(public.public_sessions.first_seen_at, EXCLUDED.first_seen_at, NOW()),
            created_at = CASE
                WHEN public.public_sessions.last_activity < NOW() - INTERVAL '30 minutes'
                THEN NOW()
                ELSE public.public_sessions.created_at
            END
        """,
        (visitor_id, p, ua, ip),
    )'''
new_conflict = '''        ON CONFLICT (visitor_id) DO UPDATE SET
            last_activity = NOW(),
            last_path = EXCLUDED.last_path,
            user_agent = COALESCE(NULLIF(EXCLUDED.user_agent, ''), public.public_sessions.user_agent),
            ip_address = EXCLUDED.ip_address,
            -- Keep original first_seen/created so return visits keep adding to same IP history
            first_seen_at = COALESCE(public.public_sessions.first_seen_at, EXCLUDED.first_seen_at, NOW()),
            created_at = COALESCE(public.public_sessions.created_at, EXCLUDED.created_at, NOW())
        """,
        (visitor_id, p, ua, ip),
    )'''
if old_conflict not in text:
    raise SystemExit("upsert conflict block not found")
text = text.replace(old_conflict, new_conflict, 1)

# 4) Trail by IP: from first_seen_at (cap 7d) so return visits still show earlier pages for that IP
old_trail_q = '''        # Prefer IP — pages belong to the IP, not a guessed sailor / cookie.
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
            rows = list(cur.fetchall() or [])'''

new_trail_q = '''        # Prefer IP — accumulate all pages for this IP (returns keep adding).
        if ip_s:
            since = None
            try:
                cur.execute(
                    """
                    SELECT COALESCE(first_seen_at, created_at)
                    FROM public.public_sessions
                    WHERE ip_address = %s
                    ORDER BY last_activity DESC NULLS LAST
                    LIMIT 1
                    """,
                    (ip_s,),
                )
                sr = cur.fetchone()
                if sr:
                    since = sr[0] if not isinstance(sr, dict) else next(iter(sr.values()))
            except Exception:
                since = None
            if since is not None:
                cur.execute(
                    """
                    SELECT path, occurred_at, left_at, dwell_seconds
                    FROM public.public_page_hits
                    WHERE ip_address = %s
                      AND occurred_at >= GREATEST(%s::timestamptz, NOW() - INTERVAL '7 days')
                    ORDER BY occurred_at ASC, hit_id ASC
                    LIMIT 120
                    """,
                    (ip_s, since),
                )
            else:
                cur.execute(
                    """
                    SELECT path, occurred_at, left_at, dwell_seconds
                    FROM public.public_page_hits
                    WHERE ip_address = %s
                      AND occurred_at > NOW() - INTERVAL '24 hours'
                    ORDER BY occurred_at ASC, hit_id ASC
                    LIMIT 120
                    """,
                    (ip_s,),
                )
            rows = list(cur.fetchall() or [])'''

if old_trail_q not in text:
    raise SystemExit("trail IP query not found")
text = text.replace(old_trail_q, new_trail_q, 1)

# 5) upsert: refuse without IP
old_upsert_gate = '''def _upsert_public_session(cur, visitor_id: str, path: str, user_agent: str, ip_address: str) -> None:
    """Upsert anonymous visitor session; one trail row per URL stay + dwell."""
    if not visitor_id or not _is_document_page_path_for_hit(path):
        return
    if _is_bot_user_agent(user_agent):
        return
    if _is_noise_public_ip(ip_address):
        return'''
new_upsert_gate = '''def _upsert_public_session(cur, visitor_id: str, path: str, user_agent: str, ip_address: str) -> None:
    """Upsert anonymous visitor by IP; return visits keep appending pages to that IP."""
    if not visitor_id or not _is_document_page_path_for_hit(path):
        return
    if not (ip_address or "").strip() or _is_noise_public_ip(ip_address):
        return
    if _is_bot_user_agent(user_agent):
        return'''
if old_upsert_gate not in text:
    raise SystemExit("upsert gate not found")
text = text.replace(old_upsert_gate, new_upsert_gate, 1)

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(text)-len(orig)} bytes)")
