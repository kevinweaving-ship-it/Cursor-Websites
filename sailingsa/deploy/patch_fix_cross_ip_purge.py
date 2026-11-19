#!/usr/bin/env python3
"""Fix: signed-in purge must not wipe guest sessions on other IPs (mobile vs wifi).

Also: Live guests from recent public_page_hits if public_sessions row was purged.
"""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

old_purge = '''def _purge_public_sessions_known_user(cur, *, ip_address: str = "", visitor_id: str = "") -> None:
    """Remove public_sessions rows that belong to a signed-in user (by IP and/or visitor cookie)."""
    try:
        if not table_exists("public_sessions"):
            return
        ip = (ip_address or "").strip()
        vid = (visitor_id or "").strip()
        if ip and vid:
            cur.execute(
                "DELETE FROM public.public_sessions WHERE ip_address = %s OR visitor_id = %s",
                (ip, vid),
            )
        elif ip:
            cur.execute("DELETE FROM public.public_sessions WHERE ip_address = %s", (ip,))
        elif vid:
            cur.execute("DELETE FROM public.public_sessions WHERE visitor_id = %s", (vid,))
    except Exception:
        pass'''

new_purge = '''def _purge_public_sessions_known_user(cur, *, ip_address: str = "", visitor_id: str = "") -> None:
    """Remove public_sessions for this signed-in IP only.

    Do NOT delete by visitor_id alone — the same ssa_vid cookie is reused on mobile
    data vs wifi; wiping by cookie removes a real guest session on another IP.
    """
    try:
        if not table_exists("public_sessions"):
            return
        ip = (ip_address or "").strip()
        vid = (visitor_id or "").strip()
        if ip and vid:
            cur.execute(
                "DELETE FROM public.public_sessions WHERE ip_address = %s",
                (ip,),
            )
        elif ip:
            cur.execute("DELETE FROM public.public_sessions WHERE ip_address = %s", (ip,))
        # visitor_id-only purge removed on purpose (cross-IP cookie leak)
    except Exception:
        pass'''

if old_purge not in text:
    raise SystemExit("purge fn not found")
text = text.replace(old_purge, new_purge, 1)

# After building rows from public_sessions in lean_traffic_api_live, add orphan guests from hits.
# Find the commit + sort + return block.
old_end = '''        try:
            conn.commit()
        except Exception:
            pass
        rows.sort(key=lambda x: x.get("last_activity") or "", reverse=True)
        return JSONResponse(
            {"ok": True, "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES, "rows": rows[:50]},
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)[:200], "rows": []}, status_code=500, headers={"Cache-Control": "no-store"})
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/traffic/api/top")
def lean_traffic_api_top(request: Request):'''

new_end = '''        # Recover guests whose public_sessions row was purged (e.g. later login on another IP)
        # but who still have recent page hits.
        try:
            if table_exists("public_page_hits"):
                seen_vids = {
                    (r.get("visitor_id") or "").strip()
                    for r in rows
                    if (r.get("visitor_id") or "").strip()
                }
                seen_ips = {(r.get("ip") or "").strip() for r in rows if (r.get("ip") or "").strip()}
                cur.execute(
                    """
                    SELECT DISTINCT ON (h.visitor_id)
                        h.visitor_id,
                        h.ip_address,
                        h.path,
                        h.occurred_at AS last_activity
                    FROM public.public_page_hits h
                    WHERE h.occurred_at > NOW() - make_interval(mins => %s)
                      AND h.visitor_id IS NOT NULL
                      AND h.visitor_id NOT LIKE 'sess:%%'
                      AND (h.ip_address IS NULL OR h.ip_address NOT IN """
                    + _LEAN_TRAFFIC_STAFF_IP_SQL
                    + """)
                      AND COALESCE(h.path, '') NOT LIKE '/temp-landing%%'
                      AND COALESCE(h.path, '') NOT LIKE '/dev-1%%'
                      AND COALESCE(h.path, '') NOT LIKE '/traffic%%'
                      AND COALESCE(h.path, '') NOT LIKE '/admin%%'
                    ORDER BY h.visitor_id, h.occurred_at DESC
                    LIMIT 40
                    """,
                    (_LEAN_TRAFFIC_LIVE_MINUTES,),
                )
                for r in cur.fetchall() or []:
                    d = r if isinstance(r, dict) else {
                        "visitor_id": r[0],
                        "ip_address": r[1],
                        "path": r[2],
                        "last_activity": r[3],
                    }
                    full_vid = (d.get("visitor_id") or "").strip()
                    ip = (d.get("ip_address") or "").strip()
                    if not full_vid or full_vid in seen_vids:
                        continue
                    if ip and ip in seen_ips:
                        continue
                    path = d.get("path") or "—"
                    la = d.get("last_activity")
                    vid = full_vid[:10]
                    is_bot = False
                    ua_live = ""
                    try:
                        cur.execute(
                            "SELECT COALESCE(user_agent,'') FROM public.public_sessions WHERE visitor_id=%s LIMIT 1",
                            (full_vid,),
                        )
                        ur = cur.fetchone()
                        if ur:
                            ua_live = (ur[0] if not isinstance(ur, dict) else ur.get("user_agent")) or ""
                    except Exception:
                        ua_live = ""
                    if not ua_live:
                        try:
                            cur.execute(
                                """
                                SELECT COALESCE(user_agent,'') FROM public.public_visit_sessions
                                WHERE visitor_id=%s OR ip_address=%s
                                ORDER BY started_at DESC NULLS LAST LIMIT 1
                                """,
                                (full_vid, ip),
                            )
                            ur = cur.fetchone()
                            if ur:
                                ua_live = (ur[0] if not isinstance(ur, dict) else next(iter(ur.values()))) or ""
                        except Exception:
                            pass
                    try:
                        if _is_sailor_sas_id_path(path) or _lean_visitor_used_sas_id_url(cur, full_vid, ip):
                            is_bot = True
                        elif _lean_human_traffic_pass(ua_live or "Mozilla/5.0 (iPhone) Safari/604.1", path):
                            is_bot = False
                        elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                            is_bot = True
                    except Exception:
                        is_bot = False
                    likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
                    if not is_bot:
                        try:
                            likely = _public_likely_sailor_for_ip(cur, ip, path) or likely
                        except Exception:
                            pass
                    likely_name = (likely.get("name") or "").strip()
                    likely_slug = (likely.get("slug") or "").strip()
                    if is_bot:
                        who = f"Bot {vid}" if vid else "Bot"
                        who_href = ""
                    else:
                        who = likely_name if likely_name else (f"Guest {vid}" if vid else "Guest")
                        who_href = f"/sailor/{likely_slug}" if likely_slug else ""
                    trail = []
                    try:
                        trail = _lean_session_page_trail(cur, visitor_id=full_vid, ip=ip)
                    except Exception:
                        trail = []
                    device_type, browser = "", ""
                    try:
                        device_type, browser = _traffic_ua_meta(ua_live)
                    except Exception:
                        pass
                    rows.append({
                        "kind": "bot" if is_bot else "anon",
                        "who": who,
                        "who_href": who_href,
                        "guessed": bool(likely_name) and not is_bot,
                        "likely_hits": int(likely.get("hits") or 0) if not is_bot else 0,
                        "sas_id": (likely.get("sas_id") or "") if not is_bot else "",
                        "ip": ip,
                        "visitor_id": full_vid,
                        "path": path,
                        "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                        "device": (ua_live or "")[:80],
                        "device_type": device_type,
                        "browser": browser,
                        "href": path if str(path).startswith("/") else "",
                        "page_trail": trail,
                        "pages_count": len(trail),
                    })
                    seen_vids.add(full_vid)
                    if ip:
                        seen_ips.add(ip)
        except Exception:
            pass
        try:
            conn.commit()
        except Exception:
            pass
        rows.sort(key=lambda x: x.get("last_activity") or "", reverse=True)
        return JSONResponse(
            {"ok": True, "live_minutes": _LEAN_TRAFFIC_LIVE_MINUTES, "rows": rows[:50]},
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)[:200], "rows": []}, status_code=500, headers={"Cache-Control": "no-store"})
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/traffic/api/top")
def lean_traffic_api_top(request: Request):'''

if old_end not in text:
    raise SystemExit("live end block not found")
text = text.replace(old_end, new_end, 1)

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(text)-len(orig)} bytes)")
