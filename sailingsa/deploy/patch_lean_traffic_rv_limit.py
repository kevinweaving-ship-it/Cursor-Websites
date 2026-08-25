#!/usr/bin/env python3
"""Raise real-visitor IP scan limit for 7d/30d/Ever so list is not capped at 250."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"PATCH FAIL {label}: count={n}")
    return text.replace(old, new, 1)


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if "limit_n = 250 if look_h < 24 * 7 else" in text:
        print("ALREADY_PATCHED")
        return
    bak = Path(f"/root/backups/api.py.rv_limit.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    old = """        look_h = int(lookback_hours)
        # All IPs with hits in lookback; Done vs Live decided later from last *public* trail time
        cur.execute(
            \"\"\"
            SELECT h.ip_address,
                   MAX(h.occurred_at) AS last_hit,
                   MIN(h.occurred_at) AS first_hit
            FROM public.public_page_hits h
            WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
              AND h.occurred_at > NOW() - make_interval(hours => %s)
              AND h.occurred_at >= %s::timestamptz
              AND h.ip_address <> '102.218.215.253'
            GROUP BY h.ip_address
            ORDER BY MAX(h.occurred_at) DESC
            LIMIT 250
            \"\"\",
            (look_h, _lean_traffic_real_since()),
        )
"""
    new = """        look_h = int(lookback_hours)
        # Scan enough IPs for longer ranges (was hard-capped at 250 → Ever/30d undercount).
        limit_n = 250 if look_h < 24 * 7 else (800 if look_h < 24 * 30 else 2000)
        cur.execute(
            \"\"\"
            SELECT h.ip_address,
                   MAX(h.occurred_at) AS last_hit,
                   MIN(h.occurred_at) AS first_hit
            FROM public.public_page_hits h
            WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
              AND h.occurred_at > NOW() - make_interval(hours => %s)
              AND h.occurred_at >= %s::timestamptz
              AND h.ip_address <> '102.218.215.253'
            GROUP BY h.ip_address
            ORDER BY MAX(h.occurred_at) DESC
            LIMIT %s
            \"\"\",
            (look_h, _lean_traffic_real_since(), limit_n),
        )
"""
    text = must_replace(text, old, new, "offline ip limit")
    # Also raise response slice slightly for long ranges — keep API returning humans[:200]
    # bump to 500 when lookback is long
    old2 = """                \"offline\": humans[:200],
                \"offline_bots\": bots[:40],
"""
    new2 = """                \"offline\": humans[:500],
                \"offline_bots\": bots[:80],
"""
    text = must_replace(text, old2, new2, "api slice")
    API.write_text(text, encoding="utf-8")
    print("PATCHED")


if __name__ == "__main__":
    main()
