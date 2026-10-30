#!/usr/bin/env python3
"""Run traffic bot maintenance in a background thread; keep request handlers light."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

BG = r'''
# ---- Lean traffic background maintenance (never block public page requests) ----
_LEAN_TRAFFIC_BG_STARTED = False
_LEAN_TRAFFIC_BG_LOCK = threading.Lock()


def _lean_traffic_background_tick() -> None:
    """Idle-finalize + bot-shape quarantine off the request path."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            try:
                cur.execute("SET LOCAL statement_timeout = '4000'")
            except Exception:
                pass
            try:
                _finalize_idle_open_page_hits(cur, idle_seconds=120)
            except Exception:
                pass
            try:
                # Force scan even if rate-limit stamp set by a rare caller
                global _LEAN_BOT_SHAPE_SCAN_TS
                _LEAN_BOT_SHAPE_SCAN_TS = 0.0
                _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
            except Exception:
                pass
            try:
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
    except Exception:
        pass
    finally:
        if conn is not None:
            try:
                return_db_connection(conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass


def _lean_traffic_background_loop() -> None:
    import time as _time
    # Stagger start so boot stays responsive
    _time.sleep(8)
    while True:
        try:
            _lean_traffic_background_tick()
        except Exception:
            pass
        _time.sleep(45)


def _lean_traffic_ensure_background() -> None:
    global _LEAN_TRAFFIC_BG_STARTED
    with _LEAN_TRAFFIC_BG_LOCK:
        if _LEAN_TRAFFIC_BG_STARTED:
            return
        _LEAN_TRAFFIC_BG_STARTED = True
        try:
            threading.Thread(
                target=_lean_traffic_background_loop,
                name="lean-traffic-bg",
                daemon=True,
            ).start()
        except Exception:
            _LEAN_TRAFFIC_BG_STARTED = False


try:
    _lean_traffic_ensure_background()
except Exception:
    pass


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-traffic-bg-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "_lean_traffic_background_loop" not in text:
        # Insert after bot-shaped helper (or bounce helpers)
        anchor = text.find("def _lean_quarantine_bot_shaped_ips_in_range")
        if anchor < 0:
            raise SystemExit("shaped helper missing")
        # insert AFTER the whole shaped function
        # find next def at module level after shaped fn
        # shaped fn ends before def _lean_maybe_quarantine or similar
        next_def = text.find("\ndef _lean_maybe_quarantine_missed_bot", anchor)
        if next_def < 0:
            next_def = text.find("\ndef _lean_bounce_home_bot", anchor)
        if next_def < 0:
            # after shaped function: search return n\n\n\ndef
            next_def = text.find("\ndef ", anchor + 50)
        # Better: append BG after shaped function end — find "return n\n\n\n" within shaped
        end_marker = text.find("\ndef ", anchor + 10)
        # skip nested? there are none. But we want end of shaped fn specifically.
        # shaped is followed by maybe_quarantine
        mq = text.find("\ndef _lean_maybe_quarantine_missed_bot", anchor)
        if mq > 0:
            text = text[:mq] + "\n" + BG + text[mq:]
            print("inserted bg before maybe_quarantine")
        else:
            # insert right after rate-limit global / before shaped — start bg after helpers exist
            # place after entire helper block: after bounce_home_bot function
            bh = text.find("\ndef _lean_human_traffic_pass")
            if bh < 0:
                bh = text.find("\ndef _lean_behavior_confident_bot")
            # insert after shaped is defined — use end of shaped by finding LIMIT 40 block's function end
            # Fallback: after `_LEAN_BOT_SHAPE_SCAN_TS = 0.0` block's function
            raise SystemExit(f"could not find insert point mq={mq}")
    else:
        print("bg loop already present")

    # Ensure background starts even if insert was after maybe_q — also call ensure near lean live
    if "_lean_traffic_ensure_background()" not in text[text.find("def lean_traffic_api_live") : text.find("def lean_traffic_api_live") + 400]:
        pass  # started at import via try block in BG

    # Remove shaped scan from overview request
    old_ov = '''        try:
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
'''
    new_ov = '''        # Bot-shape quarantine runs in background thread (not on this request)
        try:
            _lean_traffic_ensure_background()
        except Exception:
            pass
        unified = _lean_traffic_unified_sql(since_sql)
'''
    if old_ov in text:
        text = text.replace(old_ov, new_ov)
        print("overview: removed sync shaped scan")
    else:
        print("WARN overview block missing")

    # Remove shaped scan from top
    old_top = '''        try:
            _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
        except Exception:
            pass
        unified = _lean_traffic_unified_sql(since_sql, pct_escape=True)
'''
    new_top = '''        try:
            _lean_traffic_ensure_background()
        except Exception:
            pass
        unified = _lean_traffic_unified_sql(since_sql, pct_escape=True)
'''
    if old_top in text:
        text = text.replace(old_top, new_top)
        print("top: removed sync shaped scan")
    else:
        # alternate with statement_timeout
        old_top2 = '''        try:
            cur.execute("SET LOCAL statement_timeout = '3000'")
        except Exception:
            pass
        try:
            _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
        except Exception:
            pass
'''
        if old_top2 in text:
            text = text.replace(
                old_top2,
                '''        try:
            _lean_traffic_ensure_background()
        except Exception:
            pass
''',
            )
            print("top: removed sync shaped scan (timeout variant)")
        else:
            print("WARN top block")

    # Remove finalize from live request
    old_live = '''        try:
            _finalize_idle_open_page_hits(cur, idle_seconds=120)
            conn.commit()
        except Exception:
'''
    # need more context - replace finalize with ensure bg only
    live_i = text.find("def lean_traffic_api_live")
    if live_i < 0:
        raise SystemExit("live missing")
    live_j = text.find("\ndef ", live_i + 10)
    live = text[live_i:live_j]
    if "_finalize_idle_open_page_hits" in live:
        live2 = live.replace(
            '''        try:
            _finalize_idle_open_page_hits(cur, idle_seconds=120)
            conn.commit()
        except Exception:
            pass
''',
            '''        try:
            _lean_traffic_ensure_background()
        except Exception:
            pass
''',
            1,
        )
        if live2 == live:
            live2 = live.replace(
                "_finalize_idle_open_page_hits(cur, idle_seconds=120)",
                "pass  # idle finalize moved to lean-traffic background thread",
                1,
            )
        text = text[:live_i] + live2 + text[live_j:]
        print("live: removed sync finalize")
    else:
        print("live finalize already gone")

    # Soften live same_page_swarm: skip DB COUNT on request; rely on bg quarantine + trail-only
    # Replace swarm call with try that checks quarantine / club skip only — keep function but
    # short-circuit swarm to False when env or always use cheap path.
    # Best: patch _lean_same_page_swarm_bot to return False always on request... no that's wrong.
    # Add timeout to swarm query and skip if too many live rows.
    # Simpler: in live classify, don't call swarm — bg will quarantine swarmers.
    old_swarm_wire = '''                if (not is_bot) and _lean_same_page_swarm_bot(
                    cur, ip=ip or "", path=path, page_trail=_trail_pre, window_minutes=30
                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
'''
    new_swarm_wire = '''                # same-page swarm quarantine is handled in background (avoid COUNT on Live poll)
'''
    if old_swarm_wire in text:
        text = text.replace(old_swarm_wire, new_swarm_wire, 1)
        print("live: removed sync swarm COUNT")
    else:
        print("WARN swarm wire")

    # Add swarm detection to background tick
    if "_lean_bg_quarantine_swarms" not in text:
        swarm_bg = '''
def _lean_bg_quarantine_swarms(cur, *, window_minutes: int = 30) -> int:
    """Quarantine same-page multi-IP no-engage swarms (off request path). Skip /club shares."""
    n = 0
    try:
        cur.execute(
            """
            SELECT split_part(path, '?', 1) AS p, COUNT(DISTINCT ip_address)::int AS n
            FROM public.public_page_hits
            WHERE occurred_at > NOW() - make_interval(mins => %s)
              AND ip_address IS NOT NULL AND TRIM(ip_address) <> ''
              AND split_part(path, '?', 1) NOT IN ('/', '/index.html')
              AND split_part(path, '?', 1) NOT LIKE '/club/%%'
            GROUP BY 1
            HAVING COUNT(DISTINCT ip_address) >= 3
            ORDER BY n DESC
            LIMIT 25
            """,
            (int(window_minutes),),
        )
        paths = []
        for row in cur.fetchall() or []:
            p = row[0] if not isinstance(row, dict) else row.get("p")
            if p:
                paths.append(str(p))
        for p in paths:
            if _lean_is_club_entity_path(p):
                continue
            cur.execute(
                """
                SELECT DISTINCT ip_address
                FROM public.public_page_hits
                WHERE occurred_at > NOW() - make_interval(mins => %s)
                  AND split_part(path, '?', 1) = %s
                  AND ip_address IS NOT NULL
                LIMIT 40
                """,
                (int(window_minutes), p),
            )
            for row in cur.fetchall() or []:
                ip = row[0] if not isinstance(row, dict) else row.get("ip_address")
                if not ip:
                    continue
                try:
                    if _lean_ip_has_human_browse(cur, str(ip)):
                        continue
                    if _lean_is_facebook_crawler_ip(str(ip)):
                        _lean_quarantine_ip(cur, str(ip), "facebook_crawler")
                        n += 1
                        continue
                    _lean_quarantine_ip(cur, str(ip), "same_page_swarm_no_engage")
                    n += 1
                except Exception:
                    continue
    except Exception:
        return n
    return n


'''
        # insert before background tick and call from tick
        text = text.replace(
            "def _lean_traffic_background_tick() -> None:",
            swarm_bg + "def _lean_traffic_background_tick() -> None:",
            1,
        )
        text = text.replace(
            '''            try:
                # Force scan even if rate-limit stamp set by a rare caller
                global _LEAN_BOT_SHAPE_SCAN_TS
                _LEAN_BOT_SHAPE_SCAN_TS = 0.0
                _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
            except Exception:
                pass
''',
            '''            try:
                global _LEAN_BOT_SHAPE_SCAN_TS
                _LEAN_BOT_SHAPE_SCAN_TS = 0.0
                _lean_quarantine_bot_shaped_ips_in_range(cur, hours=24)
            except Exception:
                pass
            try:
                _lean_bg_quarantine_swarms(cur, window_minutes=30)
            except Exception:
                pass
''',
            1,
        )
        print("bg: added swarm quarantine")

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK traffic bg (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
