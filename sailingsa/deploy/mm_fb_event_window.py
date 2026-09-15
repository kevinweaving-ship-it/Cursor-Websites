#!/usr/bin/env python3
"""Cape Classic MM Facebook jobs run only while the event is active.

ACTIVE = today (Africa/Johannesburg) is on or between the first and last
event dates. Upcoming and past days skip Chrome/Graph polling and disable
the 5s live-watch + 90s fetch timers.

Dates default to ZVYC Cape Classic 2026 (12–13 Sep). Override with
MM_FB_EVENT_DATES=YYYY-MM-DD,YYYY-MM-DD.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
DEFAULT_RID = "2026-09-13-zvyc-cape-classic"
DEFAULT_DATES = ("2026-09-12", "2026-09-13")
WATCH_TIMER = "mm-fb-watch-live-cape.timer"
FETCH_TIMER = "mm-fb-fetch-cape.timer"
WATCH_SERVICE = "mm-fb-watch-live-cape.service"
FETCH_SERVICE = "mm-fb-fetch-cape.service"


def event_rid() -> str:
    return (os.environ.get("MM_FB_EVENT_RID") or DEFAULT_RID).strip()


def event_dates() -> tuple[date, date]:
    raw = (os.environ.get("MM_FB_EVENT_DATES") or "").strip()
    parts = [p.strip() for p in raw.replace(",", " ").split() if p.strip()]
    if not parts:
        parts = list(DEFAULT_DATES)
    days = sorted(date.fromisoformat(p) for p in parts)
    return days[0], days[-1]


def today_sast(now: datetime | date | None = None) -> date:
    if isinstance(now, date) and not isinstance(now, datetime):
        return now
    if now is None:
        now = datetime.now(SAST)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=SAST)
    return now.astimezone(SAST).date()


def event_status(today: datetime | date | None = None) -> str:
    start, end = event_dates()
    day = today_sast(today)
    if day < start:
        return "upcoming"
    if day > end:
        return "past"
    return "active"


def event_is_active(today: datetime | date | None = None) -> bool:
    return event_status(today) == "active"


def skip_payload(today: datetime | date | None = None) -> dict:
    start, end = event_dates()
    status = event_status(today)
    return {
        "ok": True,
        "skipped": "event_not_active",
        "status": status,
        "regatta": event_rid(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "today": today_sast(today).isoformat(),
    }


def _systemctl(args: list[str]) -> dict:
    try:
        proc = subprocess.run(
            ["systemctl", *args],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return {
            "args": args,
            "rc": proc.returncode,
            "err": (proc.stderr or "").strip()[:300],
        }
    except Exception as exc:
        return {"args": args, "rc": -1, "err": str(exc)[:300]}


def sync_cape_fb_timers(active: bool | None = None) -> dict:
    """Enable 5s watch + 90s fetch only while the event is running."""
    if active is None:
        active = event_is_active()
    if active:
        results = [
            _systemctl(["enable", "--now", WATCH_TIMER]),
            _systemctl(["enable", "--now", FETCH_TIMER]),
        ]
    else:
        results = [
            _systemctl(["disable", "--now", WATCH_TIMER]),
            _systemctl(["disable", "--now", FETCH_TIMER]),
            _systemctl(["stop", WATCH_SERVICE]),
            _systemctl(["stop", FETCH_SERVICE]),
        ]
    return {
        "active": active,
        "status": event_status(),
        "units": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync-timers",
        action="store_true",
        help="Enable or disable Cape FB watch/fetch timers for today's date",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print window status as JSON",
    )
    args = parser.parse_args(argv)
    payload = skip_payload() if not event_is_active() else {
        "ok": True,
        "skipped": None,
        "status": "active",
        "regatta": event_rid(),
        "start": event_dates()[0].isoformat(),
        "end": event_dates()[1].isoformat(),
        "today": today_sast().isoformat(),
    }
    if args.sync_timers:
        payload["timers"] = sync_cape_fb_timers(event_is_active())
    if args.json or args.sync_timers:
        print(json.dumps(payload))
        return 0
    start, end = event_dates()
    print(
        f"{event_status()} {event_rid()} {start.isoformat()}..{end.isoformat()} "
        f"today={today_sast().isoformat()}"
    )
    return 0 if event_is_active() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
