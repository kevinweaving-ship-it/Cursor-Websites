#!/usr/bin/env python3
"""Read-only weekly slice of the public SailingSA events table.

GET /api/events is the public projection of `public.events`
(event_name, start_date, end_date, category, regatta_id, entries, races_sailed).

The product is named Weekend Roundup but it is a **Monday weekly**:
issue Monday *M* covers events that finished in the previous week
(Monday *M-7* through Sunday *M-1*). Midweek races, long weekends, and
multi-day holds are included. Empty weeks produce no issue.

An event is assigned to exactly one Monday: the first Monday strictly
after its end date (Sunday finish → next day; Monday finish → next Monday).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.request

UA = {"User-Agent": "SailingRoundupResearch/1.0"}
EVENTS_URL = "https://sailingsa.co.za/api/events"
SKIP_CATEGORY = {"meetings", "meeting", "training", "workshop", "course"}
SKIP_NAME = re.compile(
    r"\b(course|workshop|training|meeting|seminar|clinic|agm|safety boat|instructor|safeguarding)\b",
    re.I,
)
# Admin / standing rows (e.g. 2019–2026 appointments) must not land in every week.
MAX_EVENT_DAYS = 21
REFERENCE_WEEKEND = (dt.date(2026, 9, 21), dt.date(2026, 9, 27))
REFERENCE_MONDAY = dt.date(2026, 9, 28)


def previous_week(monday: dt.date) -> tuple[dt.date, dt.date]:
    """Monday through Sunday immediately before the issue Monday."""
    if monday.weekday() != 0:
        raise ValueError("Issue date must be a Monday")
    return monday - dt.timedelta(days=7), monday - dt.timedelta(days=1)


def saturday_sunday(monday: dt.date) -> tuple[dt.date, dt.date]:
    """Sat–Sun inside the previous week (kept for decks / older callers)."""
    start, end = previous_week(monday)
    return start + dt.timedelta(days=5), end


def issue_monday_for_end(end: dt.date) -> dt.date:
    """First Monday strictly after the last racing day."""
    days = (7 - end.weekday()) % 7
    if days == 0:
        return end + dt.timedelta(days=7)
    return end + dt.timedelta(days=days)


def parse_day(value) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def overlaps(start: dt.date, end: dt.date, window_start: dt.date, window_end: dt.date) -> bool:
    return start <= window_end and end >= window_start


def skip_event(ev: dict) -> bool:
    cat = (ev.get("category") or "").strip().lower()
    if cat in SKIP_CATEGORY:
        return True
    if SKIP_NAME.search(ev.get("event_name") or ""):
        return True
    start = parse_day(ev.get("start_date"))
    end = parse_day(ev.get("end_date")) or start
    if start and end:
        if end < start:
            return True
        if (end - start).days > MAX_EVENT_DAYS:
            return True
    return False


def _fetch_events() -> list[dict]:
    req = urllib.request.Request(EVENTS_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    return data if isinstance(data, list) else []


def normalize(ev: dict) -> dict | None:
    start = parse_day(ev.get("start_date"))
    end = parse_day(ev.get("end_date")) or start
    if not start:
        return None
    rid = ev.get("regatta_id")
    slug = str(rid).strip() if rid and re.match(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+$", str(rid).strip()) else None
    return {
        "event_name": (ev.get("event_name") or "").strip(),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "category": ev.get("category"),
        "regatta_id": slug,
        "entries": int(ev.get("entries") or 0),
        "races_sailed": int(ev.get("races_sailed") or 0),
        "has_results": bool(slug and (int(ev.get("entries") or 0) or int(ev.get("races_sailed") or 0))),
    }


def weekend_events(monday: dt.date, events: list[dict] | None = None) -> list[dict]:
    """Events that finished in the previous week (Mon–Sun) before `monday`."""
    if monday.weekday() != 0:
        raise ValueError("Issue date must be a Monday")
    rows = events if events is not None else _fetch_events()
    out = []
    seen = set()
    for raw in rows:
        if skip_event(raw):
            continue
        item = normalize(raw)
        if not item:
            continue
        end = parse_day(item["end_date"])
        if not end or issue_monday_for_end(end) != monday:
            continue
        key = item["regatta_id"] or (item["event_name"].lower(), item["start_date"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    out.sort(key=lambda e: (e["start_date"], e["event_name"]))
    return out


def slugs_for_weekend(monday: dt.date, events: list[dict] | None = None) -> list[str]:
    return [e["regatta_id"] for e in weekend_events(monday, events) if e.get("regatta_id")]


def year_issue_mondays(year: int, events: list[dict] | None = None) -> list[dt.date]:
    """Mondays in `year` that have at least one finished racing event.

    Empty weeks are omitted. Several events finishing in the same week share one Monday.
    """
    if year < 1990 or year > 2100:
        raise ValueError("year out of range")
    rows = events if events is not None else _fetch_events()
    found: set[dt.date] = set()
    for raw in rows:
        if skip_event(raw):
            continue
        item = normalize(raw)
        if not item:
            continue
        end = parse_day(item["end_date"])
        if not end:
            continue
        monday = issue_monday_for_end(end)
        if monday.year == year:
            found.add(monday)
    return sorted(found)
