"""R6 week ownership: event belongs to the Mon–Sun week of its end date (SAST)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

NON_RACING_HINTS = (
    "workshop",
    "course",
    "meeting",
    "meetings",
    "training",
    "appointment",
    "clearance",
    "seminar",
    "agm",
)
NON_RACING_CATEGORIES = {
    "training",
    "meeting",
    "meetings",
}


def parse_iso_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def edition_window(edition_date: date) -> tuple[date, date]:
    """Monday edition date covers the previous Mon–Sun (the week that just ended)."""
    publish_monday = monday_of(edition_date)
    week_end = publish_monday - timedelta(days=1)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end


def event_end_date(event: dict) -> date | None:
    return parse_iso_date(event.get("end_date") or event.get("start_date"))


def is_non_racing(event: dict) -> bool:
    cat = str(event.get("category") or "").strip().lower()
    if cat in NON_RACING_CATEGORIES:
        return True
    name = str(event.get("event_name") or "").lower()
    return any(hint in name for hint in NON_RACING_HINTS)


def in_window(end: date | None, start: date, stop: date) -> bool:
    return bool(end and start <= end <= stop)


def is_late_result(end: date | None, week_start: date, max_days: int = 14) -> bool:
    if not end or end >= week_start:
        return False
    return (week_start - end).days <= max_days


def event_key(event: dict) -> str:
    rid = str(event.get("regatta_id") or "").strip()
    if rid:
        return f"regatta:{rid}"
    name = str(event.get("event_name") or "").strip().lower()
    end = str(event.get("end_date") or event.get("start_date") or "")
    return f"name:{name}|{end}"


def dedupe_events(events: Iterable[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for event in events:
        key = event_key(event)
        current = best.get(key)
        if current is None:
            best[key] = event
            continue
        cur_entries = int(current.get("entries") or 0)
        new_entries = int(event.get("entries") or 0)
        if new_entries > cur_entries:
            best[key] = event
        elif not current.get("regatta_id") and event.get("regatta_id"):
            best[key] = event
    return list(best.values())


def select_week_events(events: Iterable[dict], edition_date: date) -> dict:
    week_start, week_end = edition_window(edition_date)
    owned: list[dict] = []
    late: list[dict] = []
    skipped: list[dict] = []
    for event in events:
        end = event_end_date(event)
        if is_non_racing(event):
            skipped.append(event)
            continue
        if in_window(end, week_start, week_end):
            owned.append(event)
        elif is_late_result(end, week_start):
            late.append(event)
        else:
            skipped.append(event)
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "edition_date": edition_date.isoformat(),
        "owned": dedupe_events(owned),
        "late": dedupe_events(late),
        "skipped_count": len(skipped),
    }
