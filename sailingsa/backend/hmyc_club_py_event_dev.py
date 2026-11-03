"""HMYC club-admin PY event (dev).

GET /dev-1/club/hmyc/event — standard Back / Title / Stats / Data-card layout.
Clones the last HMYC Dart 18 fleet (2025 HMYC Grand Slam, 27 Jan 2025).
Wind and Media cards match that event (no recorded wind / no media).
Fleet table is the only change: Time (empty, club-admin entry) and PY (795).

First Non-SAS event: category Club, sanction CLUB (not SAS calendar).
Keep Club events separate from sanctioned SAS events.
"""

from __future__ import annotations

import html as html_module
import re
from typing import Iterable, List, Sequence

PAGE_PATH = "/dev-1/club/hmyc/event"
PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}

SOURCE_REGATTA_ID = "304-2025-hmyc-grand-slam-final"
SOURCE_EVENT_NAME = "2025 HMYC Grand Slam"
SOURCE_DATE_ISO = "2025-01-27"
SOURCE_DATE_LABEL = "27 January 2025"
SOURCE_STATUS_LINE = "Results are Final as at 27 January 2025 at 20:33"

CLASS_NAME = "Dart 18"
CLASS_SLUG = "dart-18"
CLASS_LOGO = "/artwork/Class Logo/Dart-18-Class-Logo.png"
CLASS_PY = 795  # RYA PN 2026 Dart 18 — do not invent other class PY here

CLUB_CODE = "HMYC"
CLUB_NAME = "Henley Midmar Yacht Club"
CLUB_SLUG = "hmyc"

# First Non-SAS / club-origin event. Do not tag as SAS calendar.
EVENT_SOURCE = "club"
EVENT_CATEGORY = "Club"
EVENT_CATEGORY_SLUG = "club"
SANCTION_LEVEL = "CLUB"
SANCTION_LABEL = "Non SAS"

# Last HMYC Dart 18 fleet: Grand Slam 27 Jan 2025, 17 boats, Appendix A places.
# Time is blank for club-admin elapsed-time entry. PY is the class number.
DART_FLEET: Sequence[dict] = (
    {"rank": "1st", "sail": "520", "club": "HMYC", "helm": "Lorrian Wells", "crew": "", "races": ("3", "1", "(11)", "1", "1"), "total": "17", "nett": "6"},
    {"rank": "2nd", "sail": "7909", "club": "ZYC", "helm": "Clinton Wissekerke", "crew": "Madison Wissekerke", "races": ("2", "(4)", "1", "2", "4"), "total": "13", "nett": "9"},
    {"rank": "3rd", "sail": "4537", "club": "HMYC", "helm": "Stephan Proudfoot", "crew": "", "races": ("(8)", "5", "4", "3", "2"), "total": "22", "nett": "14"},
    {"rank": "4th", "sail": "5770", "club": "SYC", "helm": "Vernon Brown", "crew": "", "races": ("4", "(7)", "2", "6", "5"), "total": "24", "nett": "17"},
    {"rank": "5th", "sail": "3604", "club": "HMYC", "helm": "Alistair Clulow", "crew": "", "races": ("6", "3", "5", "4", "(10)"), "total": "28", "nett": "18"},
    {"rank": "6th", "sail": "4665", "club": "HMYC", "helm": "Kim Phillips", "crew": "Abigail Weber", "races": ("1", "8", "3", "7", "(18) DNF"), "total": "37", "nett": "19"},
    {"rank": "7th", "sail": "5179", "club": "HMYC", "helm": "Gregory Dobson", "crew": "", "races": ("5", "2", "6", "8", "(11)"), "total": "32", "nett": "21"},
    {"rank": "8th", "sail": "5454", "club": "KSYC", "helm": "Clinton Gauld", "crew": "Megan Gauld", "races": ("7", "6", "(8)", "5", "6"), "total": "32", "nett": "24"},
    {"rank": "9th", "sail": "5416", "club": "ZYC", "helm": "Charles Ackerman", "crew": "", "races": ("9", "10", "7", "(18) DNC", "3"), "total": "47", "nett": "29"},
    {"rank": "10th", "sail": "3269", "club": "HMYC", "helm": "Gavin Smit", "crew": "", "races": ("12", "11", "9", "11", "(18) DNF"), "total": "61", "nett": "43"},
    {"rank": "11th", "sail": "3207", "club": "ZYC", "helm": "Barend Visser", "crew": "Tannith Visser", "races": ("11", "(18) DNC", "12", "9", "12"), "total": "62", "nett": "44"},
    {"rank": "12th", "sail": "2286", "club": "HMYC", "helm": "Nick Smart", "crew": "", "races": ("13", "13", "(18) DNC", "13", "8"), "total": "65", "nett": "47"},
    {"rank": "13th", "sail": "3931", "club": "ZYC", "helm": "Shawn Pretorius", "crew": "", "races": ("(14)", "14", "10", "14", "9"), "total": "61", "nett": "47"},
    {"rank": "14th", "sail": "4664", "club": "HMYC", "helm": "Fynn Clulow", "crew": "", "races": ("10", "9", "(18) DNC", "12", "18 DNF"), "total": "67", "nett": "49"},
    {"rank": "15th", "sail": "3349", "club": "HMYC", "helm": "Jacques Kruger", "crew": "Jethro Milne", "races": ("(18) DNC", "12", "18 DNC", "18 DNC", "7"), "total": "73", "nett": "55"},
    {"rank": "16th", "sail": "5971P", "club": "HMYC", "helm": "Nick Somerville", "crew": "Jean-Pierre Myburgh", "races": ("(18) DNC", "18 DNC", "18 DNC", "10", "18 DNC"), "total": "82", "nett": "64"},
    {"rank": "17th", "sail": "7037", "club": "HMYC", "helm": "Neil Greyling", "crew": "", "races": ("(18) DNC", "18 DNC", "18 DNC", "18 DNC", "18 DNC"), "total": "90", "nett": "72"},
)

# Last Dart event had 5 races and no stored wind / media rows.
WIND_RACES: Sequence[str] = ("R1", "R2", "R3", "R4", "R5")

_esc = html_module.escape


def _name_slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s


def _sailor_link(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return ""
    slug = _name_slug(n)
    if not slug:
        return _esc(n)
    return f'<a href="/sailor/{_esc(slug)}">{_esc(n)}</a>'


def _club_link(code: str) -> str:
    c = (code or "").strip()
    if not c:
        return ""
    return f'<a href="/club/{_esc(c.lower())}">{_esc(c)}</a>'


def _site_header() -> str:
    """Directory-page site-header (same nav). Do not edit locked header JS."""
    return (
        '<header class="site-header"><div class="container">'
        '<a href="/" class="logo js-go-home" title="Home">'
        '<img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>'
        '<nav class="nav-inline" aria-label="Main">'
        '<a href="/">Home</a>'
        '<a href="/sailors">Sailors</a>'
        '<a href="/regattas">Regattas</a>'
        '<a href="/classes">Classes</a>'
        '<a href="/clubs">Clubs</a>'
        '<a href="https://sailingsa.co.za/events">Events</a>'
        '<a href="/stats">Statistics</a>'
        '<a href="/about">About</a>'
        "</nav>"
        '<div class="header-auth"></div>'
        "</div></header>"
    )


def _title_card() -> str:
    icon = (
        f'<div class="class-hero-left">'
        f'<img src="{_esc(CLASS_LOGO)}" alt="" class="class-icon" onerror="this.style.display=\'none\'">'
        f"</div>"
    )
    desc = (
        f"First {EVENT_CATEGORY} ({SANCTION_LABEL}) event — not a sanctioned SAS calendar event. "
        f"Club admin PY event for {CLUB_CODE}. Fleet cloned from the last {CLUB_CODE} "
        f"{CLASS_NAME} result ({SOURCE_EVENT_NAME}, {SOURCE_DATE_LABEL}). "
        f"Time is for club elapsed-time entry. PY is the {CLASS_NAME} number ({CLASS_PY})."
    )
    assoc = (
        f'<div class="class-assoc">Category: '
        f'<a href="/events/type/{_esc(EVENT_CATEGORY_SLUG)}">{_esc(EVENT_CATEGORY)}</a>'
        f" · Sanction: {_esc(SANCTION_LABEL)}"
        f" · Host: "
        f'<a href="/club/{_esc(CLUB_SLUG)}">{_esc(CLUB_CODE)} - {_esc(CLUB_NAME)}</a>'
        f"</div>"
    )
    main = (
        f'<div class="class-hero-main"><h1>{_esc(CLUB_CODE)} Club Event</h1>'
        f'<p class="class-bio">{_esc(desc)}</p>{assoc}</div>'
    )
    return f'<div class="card class-hero">{icon}{main}</div>'


def _stats_card() -> str:
    links = (
        (f"/events/type/{EVENT_CATEGORY_SLUG}", f"Category: {EVENT_CATEGORY}"),
        ("#category", f"Sanction: {SANCTION_LABEL}"),
        (f"/club/{CLUB_SLUG}", f"Host: {CLUB_CODE}"),
        (f"/class/{CLASS_SLUG}", f"Class: {CLASS_NAME}"),
        (f"/regatta/{SOURCE_REGATTA_ID}", f"Source: {SOURCE_EVENT_NAME}"),
        ("#fleet", "Entries: 17"),
        ("#fleet", f"PY: {CLASS_PY}"),
    )
    parts = "".join(
        f'<a class="stats-link" href="{_esc(href)}">{_esc(label)}</a>'
        for href, label in links
    )
    return f'<div class="card stats-card"><div class="class-stats">{parts}</div></div>'


def _data_card(card_id: str, title: str, table_html: str) -> str:
    return (
        f'<div id="{_esc(card_id)}" class="card">'
        f'<h2 class="section-title">{_esc(title)}</h2>'
        f'<div class="table-container">{table_html}</div>'
        f"</div>"
    )


def _fleet_table() -> str:
    intro = (
        f'<p>Sailed: 5, Discards: 1, To count: 4, Entries: 17, Scoring system: Appendix A. '
        f'{_esc(SOURCE_STATUS_LINE)}.</p>'
    )
    heads = (
        "Rank", "Sail No", "Club", "Helm", "Crew",
        "Time", "PY",
        "R1", "R2", "R3", "R4", "R5", "Total", "Nett",
    )
    thead = "<thead><tr>" + "".join(f"<th>{_esc(h)}</th>" for h in heads) + "</tr></thead>"
    rows: List[str] = []
    for boat in DART_FLEET:
        helm = boat["helm"]
        crew = boat["crew"]
        sail_cell = (
            f'<a href="/sailor/{_esc(_name_slug(helm))}">{_esc(boat["sail"])}</a>'
            if helm else _esc(boat["sail"])
        )
        time_input = (
            f'<label class="visually-hidden" for="time-{_esc(_name_slug(helm))}">{_esc(helm)} elapsed time</label>'
            f'<input id="time-{_esc(_name_slug(helm))}" name="time" type="text" '
            f'placeholder="hh:mm:ss" autocomplete="off" inputmode="decimal">'
        )
        cells = [
            _esc(boat["rank"]),
            sail_cell,
            _club_link(boat["club"]),
            _sailor_link(helm),
            _sailor_link(crew),
            time_input,
            str(CLASS_PY),
            *[_esc(x) for x in boat["races"]],
            _esc(boat["total"]),
            _esc(boat["nett"]),
        ]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    table = f'<table class="table"><caption class="visually-hidden">{_esc(CLASS_NAME)} fleet</caption>{thead}<tbody>{"".join(rows)}</tbody></table>'
    return intro + table


def _wind_table() -> str:
    """Same last Dart event: five races, no stored wind readings."""
    heads = ("Race", "Direction", "Speed", "Gust", "Notes")
    thead = "<thead><tr>" + "".join(f"<th>{_esc(h)}</th>" for h in heads) + "</tr></thead>"
    rows = []
    for race in WIND_RACES:
        rows.append(
            "<tr>"
            + "".join(f"<td>{_esc(c)}</td>" for c in (race, "—", "—", "—", "Not recorded on source event"))
            + "</tr>"
        )
    return (
        f'<table class="table"><caption class="visually-hidden">Wind</caption>'
        f"{thead}<tbody>{''.join(rows)}</tbody></table>"
    )


def _media_table() -> str:
    """Same last Dart event: no public media rows on that fleet."""
    heads = ("Source", "Headline", "Date")
    thead = "<thead><tr>" + "".join(f"<th>{_esc(h)}</th>" for h in heads) + "</tr></thead>"
    body = (
        '<tbody><tr><td colspan="3">No public mentions on the source HMYC Dart event.</td></tr></tbody>'
    )
    return f'<table class="table"><caption class="visually-hidden">Media</caption>{thead}{body}</table>'


def _layout_css() -> str:
    """Design-system tokens only (docs/design_system.md). No new colours or fonts."""
    return """
.visually-hidden { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
.master-page-layout { max-width: 1100px; margin: auto; padding: 0.75rem 12px 2rem; }
.master-page-layout .back-to-home { display: inline-block; margin-bottom: 12px; }
.card { background: #ffffff; border: 2px solid #001f3f; border-radius: 8px; box-shadow: 0 1px 3px rgba(0, 31, 63, 0.08); padding: 0.5rem 0.75rem; margin-bottom: 16px; }
.card.class-hero { display: grid; grid-template-columns: 60px 1fr; gap: 16px; align-items: center; }
.card.class-hero h1 { font-size: 1rem; font-weight: 700; color: #001f3f; letter-spacing: 0.02em; margin: 0 0 0.25rem 0; }
.class-icon { width: 56px; height: 56px; object-fit: contain; }
.class-bio { margin: 6px 0 4px 0; font-size: 0.85rem; color: #334155; font-weight: 400; line-height: 1.35; }
.class-assoc { font-size: 0.85rem; color: #334155; font-weight: 400; margin-top: 0.25rem; }
.card .section-title { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em; border-bottom: 2px solid #001f3f; margin: 0 0 0.4rem 0; padding-bottom: 0.35rem; color: #001f3f; }
.table-container { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.table-container p { font-size: 0.9rem; color: #334155; margin: 0 0 0.5rem 0; }
table.table { width: 100%; border-collapse: collapse; }
table.table th, table.table td { padding: 0.4rem 0.6rem; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
table.table th { min-height: 44px; border-bottom: 2px solid #001f3f; color: #001f3f; font-weight: 600; text-align: left; }
table.table a { color: #001f3f; font-weight: 600; }
table.table input { min-height: 44px; min-width: 7rem; font: inherit; color: #1e293b; border: 1px solid #ddd; border-radius: 6px; padding: 0.4rem 0.6rem; background: #ffffff; }
.stats-card .class-stats { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; }
.stats-link { color: #001f3f; font-weight: 600; margin-bottom: 0.5rem; }
.stats-link:last-child { margin-bottom: 0; }
@media (min-width: 600px) {
  .card { padding: 0.5rem 0.85rem; }
}
@media (max-width: 768px) {
  .card.class-hero { grid-template-columns: 1fr; }
}
"""


def page_html() -> str:
    category_table = (
        '<table class="table"><caption class="visually-hidden">Category</caption>'
        "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>Category</td><td><a href=\"/events/type/{_esc(EVENT_CATEGORY_SLUG)}\">{_esc(EVENT_CATEGORY)}</a></td></tr>"
        f"<tr><td>Sanction</td><td>{_esc(SANCTION_LABEL)} ({_esc(SANCTION_LEVEL)})</td></tr>"
        f"<tr><td>Source</td><td>{_esc(EVENT_SOURCE)}</td></tr>"
        "<tr><td>SAS calendar</td><td>No — club event, keep separate from sanctioned SAS events</td></tr>"
        "</tbody></table>"
    )
    data_cards = "".join(
        [
            _data_card("category", "Category", category_table),
            _data_card("fleet", "Fleet", _fleet_table()),
            _data_card("wind", "Wind", _wind_table()),
            _data_card("media", "Media", _media_table()),
        ]
    )
    body = (
        f'<div class="master-page-layout container" data-event-category="{_esc(EVENT_CATEGORY_SLUG)}" '
        f'data-sanction-level="{_esc(SANCTION_LEVEL)}" data-event-source="{_esc(EVENT_SOURCE)}">'
        f'<a href="/club/{_esc(CLUB_SLUG)}" class="back-to-home">← Back to { _esc(CLUB_CODE) }</a>'
        f"{_title_card()}{_stats_card()}{data_cards}"
        "</div>"
    )
    title = f"{CLUB_CODE} Club Event — {CLASS_NAME} | SailingSA"
    return (
        "<!DOCTYPE html><html lang=\"en-US\"><head>"
        "<meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{_esc(title)}</title>"
        "<meta name=\"robots\" content=\"noindex, nofollow\">"
        f"<meta name=\"description\" content=\"{_esc(CLUB_CODE)} club admin PY event (dev). {CLASS_NAME} fleet cloned from {SOURCE_EVENT_NAME}.\">"
        f"<link rel=\"canonical\" href=\"https://sailingsa.co.za{PAGE_PATH}\">"
        "<link rel=\"icon\" type=\"image/png\" sizes=\"48x48\" href=\"/favicon-48.png\">"
        "<link rel=\"stylesheet\" href=\"/css/main.css\">"
        f"<style>{_layout_css()}</style>"
        "</head><body>"
        f"{_site_header()}"
        f'<main class="main-content">{body}</main>'
        "</body></html>"
    )


def _assert_page_contract(html: str) -> None:
    required: Iterable[str] = (
        'class="master-page-layout container"',
        'id="fleet"',
        'id="wind"',
        'id="media"',
        ">Time<",
        ">PY<",
        str(CLASS_PY),
        "Lorrian Wells",
        "Neil Greyling",
        "placeholder=\"hh:mm:ss\"",
        SOURCE_EVENT_NAME,
        'id="category"',
        EVENT_CATEGORY,
        SANCTION_LABEL,
        'data-sanction-level="CLUB"',
        'data-event-source="club"',
    )
    missing = [item for item in required if item not in html]
    if missing:
        raise AssertionError(f"HMYC club PY event page missing: {missing}")


if __name__ == "__main__":
    doc = page_html()
    _assert_page_contract(doc)
    print(f"ok {len(doc)} bytes {PAGE_PATH}")
