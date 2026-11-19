#!/usr/bin/env python3
"""Dedupe URL stays by visitor_id (stable) not only IP (egress can rotate)."""
from __future__ import annotations
import pathlib, sys, py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old_open = '''def _open_public_page_hit_path(cur, ip_address: str) -> Optional[str]:
    """Path of the currently open (left_at IS NULL) hit for this IP, if any."""
    ip = (ip_address or "").strip()
    if not ip:
        return None
    try:
        cur.execute(
            """
            SELECT path FROM public.public_page_hits
            WHERE ip_address = %s AND left_at IS NULL
            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
            LIMIT 1
            """,
            (ip,),
        )
        row = cur.fetchone()
        if not row:
            return None
        raw = row[0] if not isinstance(row, dict) else row.get("path")
        return _normalize_traffic_path(str(raw)) if raw is not None else None
    except Exception:
        return None'''

new_open = '''def _open_public_page_hit_path(
    cur, ip_address: str = "", visitor_id: str = ""
) -> Optional[str]:
    """Path of the currently open hit for this visitor (preferred) or IP."""
    vid = (visitor_id or "").strip()
    ip = (ip_address or "").strip()
    if not vid and not ip:
        return None
    try:
        if vid:
            cur.execute(
                """
                SELECT path FROM public.public_page_hits
                WHERE visitor_id = %s AND left_at IS NULL
                ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (vid,),
            )
        else:
            cur.execute(
                """
                SELECT path FROM public.public_page_hits
                WHERE ip_address = %s AND left_at IS NULL
                ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                LIMIT 1
                """,
                (ip,),
            )
        row = cur.fetchone()
        if not row:
            return None
        raw = row[0] if not isinstance(row, dict) else row.get("path")
        return _normalize_traffic_path(str(raw)) if raw is not None else None
    except Exception:
        return None'''

if old_open not in text:
    raise SystemExit("open path fn missing")
text = text.replace(old_open, new_open, 1)

# Expand close to accept visitor_id
old_close = '''def _close_open_public_page_hit(cur, ip_address: str, at=None) -> None:
    """Close all open page hits for this IP (sets left_at + dwell_seconds)."""
    ip = (ip_address or "").strip()
    if not ip:
        return
    try:
        if at is None:
            cur.execute(
                """
                UPDATE public.public_page_hits
                SET left_at = NOW(),
                    dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - occurred_at))::int)
                WHERE ip_address = %s AND left_at IS NULL
                """,
                (ip,),
            )
        else:
            cur.execute(
                """
                UPDATE public.public_page_hits
                SET left_at = %s,
                    dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (%s - occurred_at))::int)
                WHERE ip_address = %s AND left_at IS NULL
                """,
                (at, at, ip),
            )
    except Exception:
        pass'''

new_close = '''def _close_open_public_page_hit(cur, ip_address: str = "", at=None, visitor_id: str = "") -> None:
    """Close open page hits for this visitor and/or IP (sets left_at + dwell)."""
    ip = (ip_address or "").strip()
    vid = (visitor_id or "").strip()
    if not ip and not vid:
        return
    try:
        if at is None:
            if vid and ip:
                cur.execute(
                    """
                    UPDATE public.public_page_hits
                    SET left_at = NOW(),
                        dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - occurred_at))::int)
                    WHERE left_at IS NULL AND (visitor_id = %s OR ip_address = %s)
                    """,
                    (vid, ip),
                )
            elif vid:
                cur.execute(
                    """
                    UPDATE public.public_page_hits
                    SET left_at = NOW(),
                        dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - occurred_at))::int)
                    WHERE visitor_id = %s AND left_at IS NULL
                    """,
                    (vid,),
                )
            else:
                cur.execute(
                    """
                    UPDATE public.public_page_hits
                    SET left_at = NOW(),
                        dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - occurred_at))::int)
                    WHERE ip_address = %s AND left_at IS NULL
                    """,
                    (ip,),
                )
        else:
            if vid and ip:
                cur.execute(
                    """
                    UPDATE public.public_page_hits
                    SET left_at = %s,
                        dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (%s - occurred_at))::int)
                    WHERE left_at IS NULL AND (visitor_id = %s OR ip_address = %s)
                    """,
                    (at, at, vid, ip),
                )
            elif vid:
                cur.execute(
                    """
                    UPDATE public.public_page_hits
                    SET left_at = %s,
                        dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (%s - occurred_at))::int)
                    WHERE visitor_id = %s AND left_at IS NULL
                    """,
                    (at, at, vid),
                )
            else:
                cur.execute(
                    """
                    UPDATE public.public_page_hits
                    SET left_at = %s,
                        dwell_seconds = GREATEST(0, EXTRACT(EPOCH FROM (%s - occurred_at))::int)
                    WHERE ip_address = %s AND left_at IS NULL
                    """,
                    (at, at, ip),
                )
    except Exception:
        pass'''

if old_close not in text:
    raise SystemExit("close fn missing for v3")
text = text.replace(old_close, new_close, 1)

old_rec = '''def _record_url_stay_hit(
    cur,
    *,
    visitor_id: str,
    ip_address: str,
    path: str,
) -> bool:
    """Open one trail row for this URL stay. Skip if already on same URL.
    Returns True when a new row was inserted.
    """
    ip = (ip_address or "")[:80]
    p = _normalize_traffic_path(path)
    if not ip or not visitor_id or not _is_document_page_path_for_hit(p):
        return False
    try:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"traffic:{ip}",))
    except Exception:
        pass
    try:
        cur.execute(
            """
            SELECT path, left_at FROM public.public_page_hits
            WHERE ip_address = %s
            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
            LIMIT 1
            """,
            (ip,),
        )
        row = cur.fetchone()
        if row:
            last_path = row[0] if not isinstance(row, dict) else row.get("path")
            left_at = row[1] if not isinstance(row, dict) else row.get("left_at")
            if last_path is not None and _normalize_traffic_path(str(last_path)) == p:
                if left_at is None:
                    return False
                # Same URL just closed (race / double beacon): keep one stay, reopen
                try:
                    cur.execute(
                        """
                        UPDATE public.public_page_hits
                        SET left_at = NULL, dwell_seconds = NULL
                        WHERE hit_id = (
                            SELECT hit_id FROM public.public_page_hits
                            WHERE ip_address = %s
                            ORDER BY occurred_at DESC NULLS LAST, hit_id DESC
                            LIMIT 1
                        )
                        """,
                        (ip,),
                    )
                    return False
                except Exception:
                    return False
    except Exception:
        pass
    _close_open_public_page_hit(cur, ip)
    cur.execute(
        """
        INSERT INTO public.public_page_hits
            (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
        VALUES (%s, %s, %s, NOW(), NULL, NULL)
        """,
        (visitor_id, ip, p),
    )
    return True'''

new_rec = '''def _record_url_stay_hit(
    cur,
    *,
    visitor_id: str,
    ip_address: str,
    path: str,
) -> bool:
    """Open one trail row for this URL stay. Skip if visitor already on same URL.
    Returns True when a new row was inserted.
    """
    ip = (ip_address or "")[:80]
    vid = (visitor_id or "").strip()
    p = _normalize_traffic_path(path)
    if not vid or not _is_document_page_path_for_hit(p):
        return False
    lock_key = f"traffic:vid:{vid}" if vid else f"traffic:ip:{ip}"
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
        )
        row = cur.fetchone()
        if row:
            last_path = row[0] if not isinstance(row, dict) else row.get("path")
            left_at = row[1] if not isinstance(row, dict) else row.get("left_at")
            hit_id = row[2] if not isinstance(row, dict) else row.get("hit_id")
            if last_path is not None and _normalize_traffic_path(str(last_path)) == p:
                if left_at is None:
                    # Keep stay open; refresh IP if egress rotated
                    if ip:
                        try:
                            cur.execute(
                                "UPDATE public.public_page_hits SET ip_address = %s WHERE hit_id = %s",
                                (ip, hit_id),
                            )
                        except Exception:
                            pass
                    return False
                # Same URL just closed (race): reopen one stay
                try:
                    cur.execute(
                        """
                        UPDATE public.public_page_hits
                        SET left_at = NULL, dwell_seconds = NULL, ip_address = COALESCE(%s, ip_address)
                        WHERE hit_id = %s
                        """,
                        (ip or None, hit_id),
                    )
                    return False
                except Exception:
                    return False
    except Exception:
        pass
    _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid)
    cur.execute(
        """
        INSERT INTO public.public_page_hits
            (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
        VALUES (%s, %s, %s, NOW(), NULL, NULL)
        """,
        (vid, ip, p),
    )
    return True'''

if old_rec not in text:
    raise SystemExit("record fn missing for v3")
text = text.replace(old_rec, new_rec, 1)

# Update leave beacon to close by visitor_id when known
old_leave = '''            _ensure_public_sessions_table(cur)
            _close_open_public_page_hit(cur, ip)
            conn.commit()
            return _public_visitor_id_from_request(request) or None'''
new_leave = '''            _ensure_public_sessions_table(cur)
            vid_leave = _public_visitor_id_from_request(request) or ""
            _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid_leave)
            conn.commit()
            return vid_leave or None'''
if old_leave not in text:
    raise SystemExit("leave close block missing")
text = text.replace(old_leave, new_leave, 1)

# same_url branch open check should pass visitor_id
text2 = text.replace(
    "if _open_public_page_hit_path(cur, ip) is None:",
    "if _open_public_page_hit_path(cur, ip_address=ip, visitor_id=visitor_id) is None:",
)
# may appear in signed-in touch too
text = text2

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK {API} (+{len(text)-len(orig)} bytes)")
