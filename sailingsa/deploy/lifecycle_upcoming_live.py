#!/usr/bin/env python3
"""Live-compatible lifecycle helper: future start is never Full/Final Results.

Does not replace live api.py. Applied surgically on the server.
#136 (_pass_b_named_event_series / row_by_slug) is locked.

Live catalogue HTML is built by /var/www/sailingsa/deploy/events_logos_gallery.py
because _events_logos_gallery_deps() inserts that deploy/ dir on sys.path.
Patch that file — not only api/events_logos_gallery.py.
"""


def edition_is_upcoming(start_date, edition_year=None, *, today=None):
    """Shared rule: start still in the future → upcoming.

    Date is used only to classify upcoming vs live/past.
    It is never used alone to infer results finality.
    """
    from datetime import date as _date

    today = today or _date.today()
    st = start_date
    if hasattr(st, "date") and callable(st.date) and not hasattr(st, "year"):
        try:
            st = st.date()
        except Exception:
            st = None
    if isinstance(st, str) and len(st) >= 10:
        try:
            st = _date.fromisoformat(st[:10])
        except Exception:
            st = None
    if st and hasattr(st, "year"):
        return st > today
    try:
        ey = int(edition_year) if edition_year else 0
    except (TypeError, ValueError):
        ey = 0
    return bool(ey and ey > today.year)


def club_action_for_future_start(event_href: str, website: str):
    if event_href:
        return event_href, "Upcoming Event", False
    if (website or "").startswith("http"):
        return website, "Event Info", True
    return "", "", False
