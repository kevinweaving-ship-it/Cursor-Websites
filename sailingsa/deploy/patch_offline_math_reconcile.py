"""Offline: full hit trails (no dedupe), include Staff public pages, honest totals."""
from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-offline-math-{stamp}"))
text = API.read_text(encoding="utf-8")

start = text.find("def _lean_traffic_offline_sessions")
end = text.find("\ndef lean_traffic_api_live", start)
if start < 0 or end < 0:
    raise SystemExit("bounds")

NEW = r'''def _lean_offline_path_is_public(path: str) -> bool:
    """Document-ish public path for Done/offline human trails (not admin/probe/json)."""
    p = (path or "").split("?", 1)[0].strip() or "/"
    low = p.lower()
    if _lean_is_agent_junk_path(p):
        return False
    if low.startswith("/admin") or low.startswith("/traffic") or low.startswith("/lean-traffic"):
        return False
    if low.startswith("/api/") or low.startswith("/auth"):
        return False
    if low.endswith(".json") or low.endswith(".php"):
        return False
    junk = {
        "/account", "/app", "/console", "/dashboard", "/login", "/manage", "/my",
        "/portal", "/profile", "/settings", "/signin", "/signup", "/register",
        "/user", "/user/login", "/users", "/graphql", "/v1/graphql", "/class", "/club",
    }
    if low in junk:
        return False
    return True


def _lean_offline_build_trail_from_hits(cur, *, ip: str, lookback_hours: int = 24) -> list:
    """Every public hit for IP — no consecutive-path dedupe (counts must match hits)."""
    trail = []
    try:
        cur.execute(
            """
            SELECT path, occurred_at, left_at, dwell_seconds, COALESCE(engagement,'') AS engagement
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - make_interval(hours => %s)
            ORDER BY occurred_at ASC, hit_id ASC
            LIMIT 200
            """,
            (ip, int(lookback_hours)),
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
            if not _lean_offline_path_is_public(p):
                continue
            open_hit = left is None
            if dwell is None and left is not None and occ is not None:
                try:
                    dwell = max(0, int((left - occ).total_seconds()))
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
        return trail
    return trail


def _lean_traffic_offline_sessions(cur, *, live_minutes: int = 15, lookback_hours: int = 24):
    """Completed sessions for Done/offline. Returns (humans, bots).

    Humans = non-bot IPs with public page hits (staff labeled Staff, not hidden).
    Trails list every public hit (no dedupe) so visitor URL counts match the DB.
    """
    humans = []
    bots = []
    try:
        if not table_exists("public_page_hits"):
            return humans, bots
        live_m = int(live_minutes)
        look_h = int(lookback_hours)
        cur.execute(
            """
            SELECT h.ip_address,
                   MAX(h.occurred_at) AS last_hit,
                   MIN(h.occurred_at) AS first_hit
            FROM public.public_page_hits h
            WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
              AND h.occurred_at > NOW() - make_interval(hours => %s)
              AND h.ip_address <> '102.218.215.253'
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
        for row in cur.fetchall() or []:
            if isinstance(row, dict):
                ip = (row.get("ip_address") or "").strip()
                la = row.get("last_hit")
                first_seen = row.get("first_hit")
            else:
                ip = (row[0] or "").strip()
                la = row[1]
                first_seen = row[2]
            if not ip:
                continue
            is_staff = False
            try:
                cur.execute(
                    "SELECT 1 WHERE %s IN " + _LEAN_TRAFFIC_STAFF_IP_SQL + " LIMIT 1",
                    (ip,),
                )
                is_staff = bool(cur.fetchone())
            except Exception:
                is_staff = False
            trail = _lean_offline_build_trail_from_hits(cur, ip=ip, lookback_hours=look_h)
            if not trail:
                continue
            path = trail[-1].get("path") or "/"
            is_bot = False
            try:
                if ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif (not is_staff) and (
                    _is_sailor_sas_id_path(path)
                    or _lean_behavior_confident_bot(trail, path, ip)
                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                ):
                    is_bot = True
                else:
                    # cloud single-page no engage → bot
                    try:
                        if (not is_staff) and len(trail) <= 2 and not _lean_trail_has_engagement(trail):
                            if _lean_ip_is_cloud_datacenter(ip):
                                is_bot = True
                    except Exception:
                        pass
            except Exception:
                pass
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
                pass
            if is_bot:
                kind = "bot"
                who = f"Bot {ip}"
            elif is_staff:
                kind = "signed"
                who = f"Staff {ip}"
            else:
                kind = "anon"
                who = f"Guest {ip}"
            item = {
                "kind": kind,
                "who": who,
                "ip": ip,
                "visitor_id": "",
                "path": path,
                "href": path if str(path).startswith("/") else "",
                "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else str(first_seen or ""),
                "device_type": "",
                "browser": "",
                "page_trail": trail,
                "pages_count": len(trail),
                "session_seconds": _lean_session_total_seconds(trail, first_seen=first_seen, last_activity=la),
                "session_dwell_label": _lean_fmt_dwell_seconds(
                    _lean_session_total_seconds(trail, first_seen=first_seen, last_activity=la)
                ),
                "done": True,
                "quarantined": bool(is_bot),
            }
            if is_bot:
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
    except Exception:
        return humans, bots
    return humans, bots


'''

text = text[:start] + NEW + text[end:]

# JS: treat signed/staff as valid offline rows (not only kind!==bot)
old_filter = 'var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; });'
new_filter = 'var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */'
if old_filter in text:
    text = text.replace(old_filter, new_filter, 1)

# Badge for staff in renderOfflineRows
old_badge = 'var badge=r.kind==="bot"?"bot":"anon";\n      var badgeLabel=r.kind==="bot"?"bot":"guest";'
new_badge = 'var badge=r.kind==="bot"?"bot":(r.kind==="signed"?"signed":"anon");\n      var badgeLabel=r.kind==="bot"?"bot":(r.kind==="signed"?"staff":"guest");'
if old_badge in text:
    text = text.replace(old_badge, new_badge)  # both offline row renderers if duplicated

API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK offline math fix")
