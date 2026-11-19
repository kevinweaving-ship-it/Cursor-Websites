#!/usr/bin/env python3
"""Rebuild Done/offline humans from page hits by IP (sessions optional)."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


NEW_HELPER = r'''def _lean_traffic_offline_sessions(cur, *, live_minutes: int = 15, lookback_hours: int = 24):
    """Completed sessions for Done/offline.

    Returns (humans, bots).
    Humans are discovered from public_page_hits by IP (session row optional) so
    real visitors are not lost when public_sessions was purged.
    """
    humans = []
    bots = []
    try:
        if not table_exists("public_page_hits"):
            return humans, bots
        live_m = int(live_minutes)
        look_h = int(lookback_hours)
        # Candidate IPs: last hit outside live window, within lookback; not staff.
        cur.execute(
            """
            SELECT h.ip_address,
                   MAX(h.occurred_at) AS last_hit,
                   MIN(h.occurred_at) AS first_hit,
                   COUNT(*)::int AS hit_n,
                   (ARRAY_AGG(h.path ORDER BY h.occurred_at DESC, h.hit_id DESC))[1] AS last_path
            FROM public.public_page_hits h
            WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
              AND h.occurred_at > NOW() - make_interval(hours => %s)
              AND h.ip_address NOT IN """
            + _LEAN_TRAFFIC_STAFF_IP_SQL
            + """
            GROUP BY h.ip_address
            HAVING MAX(h.occurred_at) <= NOW() - make_interval(mins => %s)
                OR h.ip_address IN (
                     SELECT ip_address FROM public.traffic_quarantine_ips
                     WHERE COALESCE(active, true) = true
                       AND COALESCE(first_seen_at, last_seen_at) <= NOW() - INTERVAL '60 seconds'
                   )
            ORDER BY MAX(h.occurred_at) DESC
            LIMIT 80
            """,
            (look_h, live_m),
        )
        candidates = list(cur.fetchall() or [])
        for row in candidates:
            if isinstance(row, dict):
                ip = (row.get("ip_address") or "").strip()
                la = row.get("last_hit")
                first_seen = row.get("first_hit")
                path = row.get("last_path") or "—"
            else:
                ip = (row[0] or "").strip()
                la = row[1]
                first_seen = row[2]
                path = row[4] or "—"
            if not ip:
                continue
            if _lean_is_agent_junk_path(path):
                continue
            # UA from latest session if any
            ua = ""
            device_type = ""
            browser = ""
            vid = ""
            try:
                cur.execute(
                    """
                    SELECT visitor_id, COALESCE(user_agent,''), COALESCE(device_type,''), COALESCE(browser,''),
                           COALESCE(first_seen_at, created_at), last_activity
                    FROM public.public_sessions
                    WHERE ip_address = %s
                    ORDER BY last_activity DESC NULLS LAST
                    LIMIT 1
                    """,
                    (ip,),
                )
                sr = cur.fetchone()
                if sr:
                    if isinstance(sr, dict):
                        vid = (sr.get("visitor_id") or "").strip()
                        ua = sr.get("user_agent") or ""
                        device_type = sr.get("device_type") or ""
                        browser = sr.get("browser") or ""
                        if sr.get("first_seen_at") or sr.get("created_at"):
                            first_seen = sr.get("first_seen") or first_seen
                    else:
                        vid = (sr[0] or "").strip()
                        ua = sr[1] or ""
                        device_type = sr[2] or ""
                        browser = sr[3] or ""
                        if sr[4] is not None:
                            first_seen = sr[4]
            except Exception:
                pass
            trail = []
            try:
                trail = _lean_session_page_trail(cur, visitor_id=vid, ip=ip)
            except Exception:
                trail = []
            # If session missing, trail helper may still work via IP+since; if empty, build from hits
            if not trail:
                try:
                    cur.execute(
                        """
                        SELECT path, occurred_at, left_at, dwell_seconds, COALESCE(engagement,'') AS engagement
                        FROM public.public_page_hits
                        WHERE ip_address = %s
                          AND occurred_at > NOW() - make_interval(hours => %s)
                        ORDER BY occurred_at ASC, hit_id ASC
                        LIMIT 120
                        """,
                        (ip, look_h),
                    )
                    for hr in cur.fetchall() or []:
                        if isinstance(hr, dict):
                            p = (hr.get("path") or "/").split("?", 1)[0] or "/"
                            occ = hr.get("occurred_at")
                            left = hr.get("left_at")
                            dwell = hr.get("dwell_seconds")
                            eng_raw = hr.get("engagement") or ""
                        else:
                            p = (hr[0] or "/").split("?", 1)[0] or "/"
                            occ, left, dwell = hr[1], hr[2], hr[3]
                            eng_raw = hr[4] if len(hr) > 4 else ""
                        if _lean_is_agent_junk_path(p):
                            continue
                        open_hit = left is None
                        if dwell is None and left is not None and occ is not None:
                            try:
                                dwell = int((left - occ).total_seconds())
                            except Exception:
                                dwell = None
                        eng_toks = _lean_parse_engage_tokens(eng_raw)
                        trail.append(
                            {
                                "path": p,
                                "occurred_at": occ.isoformat() if hasattr(occ, "isoformat") else str(occ or ""),
                                "dwell_seconds": int(dwell) if dwell is not None else None,
                                "dwell_label": _lean_fmt_dwell_seconds(dwell) + (" (open)" if open_hit else ""),
                                "open": bool(open_hit),
                                "engagement": eng_toks,
                                "engagement_label": _lean_engage_summary_label(eng_toks),
                            }
                        )
                except Exception:
                    trail = trail or []
            # Drop agent/dev junk paths from trail; skip IP if nothing left
            trail = [
                t
                for t in trail
                if isinstance(t, dict) and not _lean_is_agent_junk_path(t.get("path"))
            ]
            if not trail:
                continue
            is_bot = False
            try:
                if ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
            except Exception:
                pass
            # Prefer last trail path for display
            if trail:
                path = trail[-1].get("path") or path
            in_live_window = False
            try:
                if la is not None:
                    cur.execute(
                        "SELECT (%s::timestamptz > NOW() - make_interval(mins => %s))",
                        (la, live_m),
                    )
                    rr = cur.fetchone()
                    if rr:
                        in_live_window = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
            except Exception:
                in_live_window = False
            item = {
                "kind": "bot" if is_bot else "anon",
                "who": (f"Bot {ip}" if is_bot else f"Guest {ip}") if ip else ("Bot" if is_bot else "Guest"),
                "ip": ip,
                "visitor_id": vid,
                "path": path,
                "href": path if str(path).startswith("/") else "",
                "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else str(first_seen or ""),
                "device_type": device_type or (_traffic_ua_meta(ua)[0] if ua else ""),
                "browser": browser or (_traffic_ua_meta(ua)[1] if ua else ""),
                "page_trail": trail,
                "pages_count": len(trail),
                "session_seconds": _lean_session_total_seconds(
                    trail, first_seen=first_seen, last_activity=la
                ),
                "session_dwell_label": _lean_fmt_dwell_seconds(
                    _lean_session_total_seconds(trail, first_seen=first_seen, last_activity=la)
                ),
                "done": True,
                "quarantined": bool(is_bot),
            }
            if is_bot:
                bots.append(item)
            elif not in_live_window and len(trail) >= 1:
                humans.append(item)
    except Exception:
        return humans, bots
    return humans, bots


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-offline-from-hits-{stamp}"))
    text = API.read_text(encoding="utf-8")
    start = text.find("def _lean_traffic_offline_sessions")
    end = text.find("\ndef lean_traffic_api_live", start)
    if start < 0 or end < 0:
        raise SystemExit("helper bounds missing")
    text = text[:start] + NEW_HELPER + text[end:]
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK offline from hits (+{len(NEW_HELPER)} helper)")


if __name__ == "__main__":
    main()
