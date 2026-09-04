#!/usr/bin/env python3
"""Surgical: Real visitors list includes Live + deep-link humans (match Visitors card better)."""
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
    marker = "offline_include_live_and_deeplink_v1"
    if marker in text:
        print("ALREADY_PATCHED")
        return

    bak = Path(f"/root/backups/api.py.rv_match_top.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    # Marker near offline builder
    text = must_replace(
        text,
        'def _lean_traffic_offline_sessions(cur, *, live_minutes: int = 15, lookback_hours: int = 24):\n    """Completed sessions for Done/offline. Returns (humans, bots).\n',
        'def _lean_traffic_offline_sessions(cur, *, live_minutes: int = 15, lookback_hours: int = 24):\n    """Real visitors for selected lookback (humans, bots). ' + marker + '\n',
        "offline docstring marker",
    )

    text = must_replace(
        text,
        """                # Real people scroll or click. No engagement → not a Guest on Done.
                if (not is_bot) and (not is_staff):
                    try:
                        if not _lean_trail_has_engagement(trail):
                            is_bot = True
                    except Exception:
                        pass
""",
        """                # Real = scroll/click OR human content deep-link (same idea as Visitors card).
                if (not is_bot) and (not is_staff):
                    try:
                        has_eng = False
                        try:
                            has_eng = bool(_lean_trail_has_engagement(trail))
                        except Exception:
                            has_eng = False
                        if not has_eng:
                            # site_traffic beacon path (shared-link phones)
                            try:
                                cur.execute(
                                    (
                                        "SELECT 1 FROM public.site_traffic_events ste "
                                        "WHERE ste.ip_address = %s "
                                        "AND COALESCE(ste.is_bot, false) = false "
                                        "AND ste.event_type IN ('scroll', 'click') "
                                        "AND ste.created_at > NOW() - make_interval(hours => %s) "
                                        "LIMIT 1"
                                    ),
                                    (ip, look_h),
                                )
                                has_eng = bool(cur.fetchone())
                            except Exception:
                                pass
                        deep = False
                        try:
                            for pt in trail or []:
                                pp = (pt.get("path") if isinstance(pt, dict) else "") or ""
                                if (
                                    pp.startswith("/sailor/")
                                    or pp.startswith("/club/")
                                    or pp.startswith("/regatta/")
                                    or pp.startswith("/class/")
                                    or pp.startswith("/boat/")
                                    or pp.startswith("/boat-name/")
                                ):
                                    deep = True
                                    break
                        except Exception:
                            deep = False
                        if not has_eng and not deep:
                            is_bot = True
                    except Exception:
                        pass
""",
        "offline real = engage or deep-link",
    )

    text = must_replace(
        text,
        """            if is_bot:
                if ip:
                    try:
                        if not _lean_trail_has_engagement(trail):
                            _lean_quarantine_ip(cur, ip, "offline_bot")
                    except Exception:
                        pass
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
""",
        """            if is_bot:
                if ip:
                    try:
                        if not _lean_trail_has_engagement(trail):
                            _lean_quarantine_ip(cur, ip, "offline_bot")
                    except Exception:
                        pass
                bots.append(item)
            else:
                # Include Live + Done so list matches top Visitors for the chosen range
                item["done"] = not bool(in_live_window)
                item["live_now"] = bool(in_live_window)
                humans.append(item)
""",
        "offline include live humans",
    )

    API.write_text(text, encoding="utf-8")
    print("PATCHED", API)


if __name__ == "__main__":
    main()
