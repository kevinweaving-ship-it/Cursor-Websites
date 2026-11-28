#!/usr/bin/env python3
"""Deep-link without engage: mobile UA only (WhatsApp/in-app), not desktop scrape swarm."""
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
    bak = Path(f"/root/backups/api.py.spike_mobile.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    old = """            AND (
                 lower(ps.user_agent) LIKE '%%iphone%%'
              OR lower(ps.user_agent) LIKE '%%ipad%%'
              OR lower(ps.user_agent) LIKE '%%android%%'
              OR lower(ps.user_agent) LIKE '%%mobile%%'
              OR lower(ps.user_agent) LIKE '%%chrome/%%'
              OR lower(ps.user_agent) LIKE '%%safari/%%'
              OR lower(ps.user_agent) LIKE '%%firefox/%%'
              OR lower(ps.user_agent) LIKE '%%edg/%%'
            )
            AND (
              COALESCE(h2.dwell_seconds, 0) >= 5
              OR (
                SELECT COUNT(*) FROM public.public_page_hits h2b
                WHERE h2b.ip_address = h2.ip_address
                  {since_clause_h2b}
              ) >= 2
            )
"""
    new = """            AND (
                 lower(ps.user_agent) LIKE '%%iphone%%'
              OR lower(ps.user_agent) LIKE '%%ipad%%'
              OR lower(ps.user_agent) LIKE '%%android%%'
              OR lower(ps.user_agent) LIKE '%%mobile%%'
              OR lower(ps.user_agent) LIKE '%%whatsapp%%'
            )
            AND (
              COALESCE(h2.dwell_seconds, 0) >= 5
              OR (
                SELECT COUNT(*) FROM public.public_page_hits h2b
                WHERE h2b.ip_address = h2.ip_address
                  {since_clause_h2b}
              ) >= 2
            )
"""
    text = must_replace(text, old, new, "mobile-only deep-link")
    API.write_text(text, encoding="utf-8")
    print("PATCHED")


if __name__ == "__main__":
    main()
