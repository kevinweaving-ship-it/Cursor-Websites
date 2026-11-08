#!/usr/bin/env python3
"""Only reopen a just-closed same-URL stay within 2s (race), else new stay."""
from __future__ import annotations
import pathlib, sys, py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old = '''            if last_path is not None and _normalize_traffic_path(str(last_path)) == p:
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
                    return False'''

new = '''            if last_path is not None and _normalize_traffic_path(str(last_path)) == p:
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
                # Same URL closed moments ago → race/double beacon; reopen.
                # Longer gap → real return visit; fall through to insert a new stay.
                try:
                    cur.execute(
                        """
                        SELECT (left_at IS NOT NULL AND left_at > NOW() - INTERVAL '2 seconds') AS recent
                        FROM public.public_page_hits WHERE hit_id = %s
                        """,
                        (hit_id,),
                    )
                    rr = cur.fetchone()
                    recent = False
                    if rr:
                        recent = bool(rr[0] if not isinstance(rr, dict) else rr.get("recent"))
                    if recent:
                        cur.execute(
                            """
                            UPDATE public.public_page_hits
                            SET left_at = NULL, dwell_seconds = NULL,
                                ip_address = COALESCE(%s, ip_address)
                            WHERE hit_id = %s
                            """,
                            (ip or None, hit_id),
                        )
                        return False
                except Exception:
                    pass'''

if old not in text:
    raise SystemExit("reopen block not found")
text = text.replace(old, new, 1)
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(text)-len(orig)} bytes)")
