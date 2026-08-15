#!/usr/bin/env python3
"""Remove heavy bot-quarantine work from page-hit / close hot path (was hanging /clubs)."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-speed-hotpath-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # 1) Remove maybe_quarantine from record_url_stay_hit (every page view)
    old_rec = '''    try:
        _lean_maybe_quarantine_missed_bot(cur, ip, p)
    except Exception:
        pass
    return True
'''
    if old_rec in text:
        text = text.replace(old_rec, "    return True\n", 1)
        print("removed record_url_stay quarantine")
    else:
        print("WARN record hook missing")

    # 2) Remove maybe_quarantine from close_open_public_page_hit
    old_close = '''    try:
        if ip:
            _lean_maybe_quarantine_missed_bot(cur, ip)
    except Exception:
        pass



'''
    # may appear once at end of close
    ci = text.find("def _close_open_public_page_hit")
    cj = text.find("\ndef ", ci + 10)
    close = text[ci:cj]
    if "_lean_maybe_quarantine_missed_bot(cur, ip)" in close:
        close2 = close.replace(
            '''    try:
        if ip:
            _lean_maybe_quarantine_missed_bot(cur, ip)
    except Exception:
        pass
''',
            "",
            1,
        )
        text = text[:ci] + close2 + text[cj:]
        print("removed close quarantine")
    else:
        print("WARN close hook missing")

    # 3) Remove per-IP maybe_quarantine loop from finalize_idle (can scan 80 IPs)
    old_fin = '''        n = int(cur.rowcount or 0)
        if n:
            try:
                cur.execute(
                    """
                    SELECT DISTINCT h.ip_address
                    FROM public.public_page_hits h
                    JOIN public.public_sessions s ON s.ip_address = h.ip_address
                    WHERE h.left_at IS NOT NULL
                      AND h.left_at > NOW() - INTERVAL '10 minutes'
                      AND s.last_activity < NOW() - make_interval(secs => %s)
                    LIMIT 80
                    """,
                    (idle,),
                )
                for row in cur.fetchall() or []:
                    ipx = row[0] if not isinstance(row, dict) else row.get("ip_address")
                    if ipx:
                        _lean_maybe_quarantine_missed_bot(cur, str(ipx))
            except Exception:
                pass
        return n
'''
    # try alternate finalize from earlier patch
    if old_fin in text:
        text = text.replace(
            old_fin,
            "        return int(cur.rowcount or 0)\n",
            1,
        )
        print("removed finalize loop")
    else:
        # other variant
        fi = text.find("def _finalize_idle_open_page_hits")
        fj = text.find("\ndef ", fi + 10)
        fin = text[fi:fj]
        if "_lean_maybe_quarantine_missed_bot" in fin:
            # strip block from n = int through return n, keep simple return
            import re

            fin2, cnt = re.subn(
                r"\n        n = int\(cur\.rowcount or 0\).*?\n        return n\n",
                "\n        return int(cur.rowcount or 0)\n",
                fin,
                count=1,
                flags=re.S,
            )
            if cnt:
                text = text[:fi] + fin2 + text[fj:]
                print("removed finalize loop via regex")
            else:
                # simpler: remove calls only
                fin2 = fin.replace(
                    "                        _lean_maybe_quarantine_missed_bot(cur, str(ipx))\n",
                    "                        pass  # quarantine deferred off hot path\n",
                )
                text = text[:fi] + fin2 + text[fj:]
                print("neutralized finalize maybe_q calls")
        else:
            print("finalize already clean")

    # 4) Rate-limit overview bot-shaped scan (once / 60s) + hard cap
    old_shaped_fn_start = '''def _lean_quarantine_bot_shaped_ips_in_range(cur, *, hours: int = 24) -> int:
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
'''
    new_shaped_fn_start = '''_LEAN_BOT_SHAPE_SCAN_TS = 0.0

def _lean_quarantine_bot_shaped_ips_in_range(cur, *, hours: int = 24) -> int:
    """Scan recent IPs and quarantine bounce/junk/sterile/deep-link bots (no engage).

    Runs before overview Visitors/Hits and Most popular so KPIs match Done/offline humans.
    Never quarantines IPs with scroll/click engagement.
    Rate-limited — must not block public page requests on the single API worker.
    """
    global _LEAN_BOT_SHAPE_SCAN_TS
    import time as _time
    now = _time.time()
    if now - float(_LEAN_BOT_SHAPE_SCAN_TS or 0) < 60.0:
        return 0
    _LEAN_BOT_SHAPE_SCAN_TS = now
    n = 0
    try:
        hours = max(1, min(int(hours or 24), 168))
    except Exception:
        hours = 24
    try:
        try:
            cur.execute("SET LOCAL statement_timeout = '1500'")
        except Exception:
            pass
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
            LIMIT 40
            """,
            (hours,),
        )
'''
    if old_shaped_fn_start in text:
        text = text.replace(old_shaped_fn_start, new_shaped_fn_start, 1)
        print("rate-limited shaped scan")
    elif "_LEAN_BOT_SHAPE_SCAN_TS" in text:
        print("rate limit already")
    else:
        # try just LIMIT 200 -> 40 and add rate limit after def line
        if "LIMIT 200\n           \",\n            (hours,),\n        )\n        ips = []\n        for row in cur.fetchall() or []:\n            ip = row[0] if not isinstance(row, dict) else row.get(\"ip_address\")\n            if ip:\n                ips.append(str(ip)[:80])\n    except Exception:\n        return 0\n    for ip in ips:" in text:
            text = text.replace(
                "LIMIT 200\n",
                "LIMIT 40\n",
                1,
            )
        si = text.find("def _lean_quarantine_bot_shaped_ips_in_range")
        if si >= 0 and "_LEAN_BOT_SHAPE_SCAN_TS" not in text:
            insert = '''_LEAN_BOT_SHAPE_SCAN_TS = 0.0

'''
            text = text[:si] + insert + text[si:]
            # after n = 0 add rate limit
            text = text.replace(
                '''def _lean_quarantine_bot_shaped_ips_in_range(cur, *, hours: int = 24) -> int:
    """Scan recent IPs and quarantine bounce/junk/sterile/deep-link bots (no engage).

    Runs before overview Visitors/Hits and Most popular so KPIs match Done/offline humans.
    Never quarantines IPs with scroll/click engagement.
    """
    n = 0
''',
                '''def _lean_quarantine_bot_shaped_ips_in_range(cur, *, hours: int = 24) -> int:
    """Scan recent IPs and quarantine bounce/junk/sterile/deep-link bots (no engage).

    Rate-limited so traffic admin polls do not stall public /clubs pages.
    """
    global _LEAN_BOT_SHAPE_SCAN_TS
    import time as _time
    now = _time.time()
    if now - float(_LEAN_BOT_SHAPE_SCAN_TS or 0) < 60.0:
        return 0
    _LEAN_BOT_SHAPE_SCAN_TS = now
    n = 0
''',
                1,
            )
            print("rate-limited shaped scan (fallback)")
        else:
            print("WARN shaped fn patch")

    # 5) Ultra-light junk-only check on record (optional, cheap) — skip to keep path fast

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK hotpath speed (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
