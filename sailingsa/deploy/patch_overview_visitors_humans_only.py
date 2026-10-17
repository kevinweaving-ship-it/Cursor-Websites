#!/usr/bin/env python3
"""Before overview/top counts: quarantine bot-shaped IPs so Visitors matches Done/offline humans."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = r'''def _lean_quarantine_bot_shaped_ips_in_range(cur, *, hours: int = 24) -> int:
    """Scan recent IPs and quarantine bounce/junk/sterile/deep-link bots (no engage).

    Runs before overview Visitors/Hits and Most popular so KPIs match Done/offline humans.
    Never quarantines IPs with scroll/click engagement.
    """
    n = 0
    try:
        hours = max(1, min(int(hours or 24), 168))
    except Exception:
        hours = 24
    try:
        cur.execute(
            """
            SELECT DISTINCT ip_address
            FROM public.public_page_hits
            WHERE occurred_at > NOW() - make_interval(hours => %s)
              AND ip_address IS NOT NULL AND TRIM(ip_address) <> ''
              AND ip_address NOT IN (
                SELECT ip_address FROM public.traffic_quarantine_ips
                WHERE COALESCE(active, true) = true
              )
            LIMIT 200
            """,
            (hours,),
        )
        ips = []
        for row in cur.fetchall() or []:
            ip = row[0] if not isinstance(row, dict) else row.get("ip_address")
            if ip:
                ips.append(str(ip)[:80])
    except Exception:
        return 0
    for ip in ips:
        try:
            # skip staff
            try:
                cur.execute(
                    "SELECT 1 FROM (" + _LEAN_TRAFFIC_STAFF_IP_SQL + ") s WHERE s.ip_address = %s LIMIT 1",
                    (ip,),
                )
                if cur.fetchone():
                    continue
            except Exception:
                pass
            if _lean_ip_has_human_browse(cur, ip):
                continue
            cur.execute(
                """
                SELECT path, dwell_seconds, engagement, left_at
                FROM public.public_page_hits
                WHERE ip_address = %s
                  AND occurred_at > NOW() - make_interval(hours => %s)
                ORDER BY occurred_at ASC
                LIMIT 40
                """,
                (ip, hours),
            )
            trail = []
            for row in cur.fetchall() or []:
                if isinstance(row, dict):
                    trail.append(
                        {
                            "path": row.get("path"),
                            "dwell_seconds": row.get("dwell_seconds"),
                            "engagement": row.get("engagement"),
                            "open": row.get("left_at") is None,
                        }
                    )
                else:
                    trail.append(
                        {
                            "path": row[0],
                            "dwell_seconds": row[1],
                            "engagement": row[2],
                            "open": row[3] is None,
                        }
                    )
            if _lean_trail_has_engagement(trail):
                continue
            path = ""
            if trail:
                path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
            if any(
                _lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "")
                for t in trail
            ) or _lean_is_junk_false_path(path):
                _lean_quarantine_ip(cur, ip, "junk_false_path")
                n += 1
                continue
            if _lean_sterile_short_trail_bot(trail, path, ip):
                reason = (
                    "cloud_sterile_short"
                    if _lean_ip_is_cloud_datacenter(ip)
                    else "sterile_single_page"
                )
                _lean_quarantine_ip(cur, ip, reason)
                n += 1
                continue
            if _lean_bounce_home_bot(trail, path):
                _lean_quarantine_ip(cur, ip, "bounce_home_no_engage")
                n += 1
                continue
            if _lean_behavior_confident_bot(trail, path, ip):
                _lean_quarantine_ip(cur, ip, "behavior_deep_link_swarm")
                n += 1
                continue
            paths = []
            any_open = False
            for pt in trail:
                if not isinstance(pt, dict):
                    continue
                pp = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
                paths.append(pp)
                if pt.get("open"):
                    any_open = True
            if (not any_open) and paths and not any(p in ("/", "/index.html") for p in paths):
                first = paths[0]
                deep = (
                    first.startswith("/boat/")
                    or first.startswith("/sailor/")
                    or first.startswith("/regatta/")
                    or first.startswith("/club/")
                    or first.startswith("/class/")
                    or first.startswith("/sponsors/")
                )
                if deep and len(set(paths)) <= 2:
                    _lean_quarantine_ip(cur, ip, "behavior_deep_link_swarm")
                    n += 1
        except Exception:
            continue
    return n


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-overview-human-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_quarantine_bot_shaped_ips_in_range" not in text:
        anchor = text.find("def _lean_maybe_quarantine_missed_bot")
        if anchor < 0:
            anchor = text.find("def _lean_bounce_home_bot")
        if anchor < 0:
            raise SystemExit("no anchor")
        text = text[:anchor] + HELPER + text[anchor:]

    old = '''        unified = _lean_traffic_unified_sql(since_sql)
        cur.execute(f"SELECT COUNT(*) AS hits, COUNT(DISTINCT visitor_key) AS visitors FROM ({unified}) x")
'''
    new = '''        try:
            hrs = 24
            if since_sql:
                try:
                    parts = str(since_sql).split()
                    hrs = int(parts[0]) if parts and parts[0].isdigit() else 24
                    if len(parts) > 1 and parts[1].startswith("day"):
                        hrs = int(parts[0]) * 24
                    elif len(parts) > 1 and parts[1].startswith("hour"):
                        hrs = max(1, int(parts[0]))
                except Exception:
                    hrs = 24
            _lean_quarantine_bot_shaped_ips_in_range(cur, hours=hrs)
        except Exception:
            pass
        unified = _lean_traffic_unified_sql(since_sql)
        cur.execute(f"SELECT COUNT(*) AS hits, COUNT(DISTINCT visitor_key) AS visitors FROM ({unified}) x")
'''
    if old not in text:
        raise SystemExit("overview unified count not found")
    count = text.count(old)
    text = text.replace(old, new)
    print(f"wired overview count x{count}")

    # top with pct_escape
    old_top = "        unified = _lean_traffic_unified_sql(since_sql, pct_escape=True)\n"
    if old_top in text:
        # only add if not already preceded by quarantine call nearby
        idx = 0
        added = 0
        while True:
            i = text.find(old_top, idx)
            if i < 0:
                break
            prev = text[max(0, i - 120) : i]
            if "_lean_quarantine_bot_shaped_ips_in_range" not in prev:
                text = (
                    text[:i]
                    + "        try:\n            _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)\n        except Exception:\n            pass\n"
                    + text[i:]
                )
                added += 1
                idx = i + 200
            else:
                idx = i + len(old_top)
        print(f"wired top pct_escape x{added}")

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK overview=humans (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
