"""Copy last same-club Event URL cards onto a newly preloaded event.

Rule: when creating / preloading an Event URL, look up the host club's live-card
profile (from the last event that already used it) and attach the same cards.

Date-first slugs (`YYYY-MM-DD-club-name`) are the new Event URL shape, e.g.
`2026-09-19-hmyc-midmar-cup`. Older result slugs (`317-2025-hmyc-…`) stay
results-only.

HMYC profile (from Midmar Cup): Leader Board, weather, media, live camera.
New HMYC events get the same stack; media starts empty unless that slug already
has seeded clips. Clips are per-event (`/mm-clips` on this slug), never Midmar
leftovers. See docs/CLUB_EVENT_LIVE_CARDS.md before the next Event URL
(SSH live; do not touch blank69 or breaking-news-card.js).
"""

from __future__ import annotations

import re

DATE_FIRST_EVENT_SLUG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})-([a-z0-9]+)(?:-.+)?$",
    re.IGNORECASE,
)

# First live Event URL per club that defined the card stack. Later date-first
# Event URLs at the same club inherit these cards.
CLUB_LIVE_CARD_PROFILES = {
    "HMYC": {
        "source_event_slug": "2026-09-19-hmyc-midmar-cup",
        "weather_club": "HMYC",
        "weather_station": "agromet-midmar",
        "cards": ("leaderboard", "weather", "media", "camera"),
        "empty_media_default": True,
        "seed_media_slugs": frozenset({"2026-09-19-hmyc-midmar-cup"}),
    }
}

LIVE_CARD_SCRIPTS_HTML = (
    '<script src="/js/midmar-live-media.js?v=clubcards1" defer></script>'
    '<script src="/js/midmar-leaderboard.js?v=clubcards1" defer></script>'
    '<script src="/js/midmar-media-rotate.js?v=clubcards1" defer></script>'
)


def date_first_event_club(regatta_id: str) -> str:
    """Return club token from `YYYY-MM-DD-club-…`, else ''."""
    m = DATE_FIRST_EVENT_SLUG_RE.match(str(regatta_id or "").strip())
    return m.group(2).upper() if m else ""


def club_live_card_profile(host_abbrev: str = "", regatta_id: str = "") -> dict | None:
    key = (host_abbrev or date_first_event_club(regatta_id) or "").strip().upper()
    return CLUB_LIVE_CARD_PROFILES.get(key)


def should_attach_club_live_cards(regatta_id: str, host_abbrev: str = "") -> bool:
    """True when this is a new Event URL for a club that already has a card stack."""
    if not date_first_event_club(regatta_id):
        return False
    return club_live_card_profile(host_abbrev, regatta_id) is not None


def club_live_event_scripts_html(regatta_id: str, host_abbrev: str = "") -> str:
    if not should_attach_club_live_cards(regatta_id, host_abbrev):
        return ""
    return LIVE_CARD_SCRIPTS_HTML


def club_live_page_attrs(regatta_id: str, host_abbrev: str = "") -> str:
    """Attribute string for the `.regatta-page` div (includes leading space)."""
    rid = str(regatta_id or "").strip()
    if not should_attach_club_live_cards(rid, host_abbrev):
        return ' class="regatta-page"'
    club = (host_abbrev or date_first_event_club(rid) or "").strip().upper()
    attrs = f' class="regatta-page" data-club-live-cards="{club}"'
    if club == "HMYC":
        attrs += ' data-hmyc-live="1"'
    if rid == "2026-09-19-hmyc-midmar-cup":
        attrs += ' data-midmar-cup="1"'
    return attrs
