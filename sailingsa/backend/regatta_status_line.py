"""Results status line for sheets and stored PDFs.

Default: Provisional as at the event's last day at 17:30.
Override: set regattas.as_at_time and/or regattas.result_status (Final).
Do not use results.as_at_time (row-save clock).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

DEFAULT_STATUS = "Provisional"
DEFAULT_AS_AT_CLOCK = time(17, 30)


def _as_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def _as_datetime(value) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, DEFAULT_AS_AT_CLOCK)
    s = str(value).strip()
    s2 = s[:19].replace("Z", "").replace("+00:00", "").strip()
    try:
        if "T" in s2:
            return datetime.strptime(s2, "%Y-%m-%dT%H:%M:%S")
        if len(s2) >= 16 and " " in s2:
            return datetime.strptime(s2[:16], "%Y-%m-%d %H:%M")
        day = _as_date(s)
        if day:
            return datetime.combine(day, DEFAULT_AS_AT_CLOCK)
    except ValueError:
        return None
    return None


def normalize_result_status(status_word: str) -> str:
    word = (status_word or "").strip()
    return word or DEFAULT_STATUS


def resolve_status_as_at(as_at_time, end_date=None, start_date=None) -> Optional[datetime]:
    """regattas.as_at_time if set, else last event day at 17:30."""
    dt = _as_datetime(as_at_time)
    if dt:
        return dt
    day = _as_date(end_date) or _as_date(start_date)
    if day:
        return datetime.combine(day, DEFAULT_AS_AT_CLOCK)
    return None


def format_results_status_line(
    status_word: str,
    as_at_time=None,
    end_date=None,
    start_date=None,
) -> str:
    word = normalize_result_status(status_word)
    dt = resolve_status_as_at(as_at_time, end_date=end_date, start_date=start_date)
    if not dt:
        return f"Results are {word} (snapshot time not recorded)"
    return f"Results are {word} as at {dt.strftime('%d %B %Y at %H:%M')}"
