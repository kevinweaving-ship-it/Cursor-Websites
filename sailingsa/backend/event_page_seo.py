"""Pass B: truthful crawlable event title/description/status/JSON-LD.

No new lifecycle table. Derives state from existing dates / result_status / raced rows / real as_at.
Never invents an as_at timestamp (no end-date 17:30).
"""
from __future__ import annotations

import html as html_module
import json
import re
from datetime import date, datetime
from typing import Any, Iterable, Optional

LASTMOD_FLOOR = "2000-01-01"
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _as_date(d: Any) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if hasattr(d, "date") and callable(d.date):
        try:
            got = d.date()
            if isinstance(got, date):
                return got
        except Exception:
            pass
    s = str(d).strip()
    if len(s) >= 10:
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            return None
    return None


def _has_real_as_at(as_at_time: Any) -> bool:
    if as_at_time is None:
        return False
    s = str(as_at_time).strip()
    if not s or s.lower() in ("none", "null"):
        return False
    iso = s[:10]
    if iso <= LASTMOD_FLOOR:
        return False
    return True


def compact_event_date_range(start_date: Any, end_date: Any) -> str:
    """Existing SailingSA short form: 25–27 Sep 2026 / 19–20 Sep 2026 / 24–29 Aug 2026."""
    st = _as_date(start_date)
    en = _as_date(end_date) or st
    if not st:
        return ""
    if not en or en == st:
        return f"{st.day} {_MONTHS[st.month - 1]} {st.year}"
    if st.year == en.year and st.month == en.month:
        return f"{st.day}–{en.day} {_MONTHS[st.month - 1]} {st.year}"
    if st.year == en.year:
        return (
            f"{st.day} {_MONTHS[st.month - 1]} – "
            f"{en.day} {_MONTHS[en.month - 1]} {st.year}"
        )
    return (
        f"{st.day} {_MONTHS[st.month - 1]} {st.year} – "
        f"{en.day} {_MONTHS[en.month - 1]} {en.year}"
    )


def _fleet_entry_label(f: dict) -> str:
    for key in ("class_name", "class_canonical", "fleet_label", "name", "fleet_name"):
        val = str(f.get(key) or "").strip()
        if val and val.lower() not in {"fleet", "overall"}:
            return val
    return "Fleet"


def count_event_entries_by_fleet(fleets: Optional[Iterable[Any]]) -> tuple[int, int, list[tuple[str, int]]]:
    """Event total = SUM of per-fleet entries. Never max(one fleet).

    Fleet n = result rows in that fleet if present, else entries / entries_raced.
    """
    raced = 0
    total = 0
    per_fleet: list[tuple[str, int]] = []
    for f in fleets or []:
        if not isinstance(f, dict):
            continue
        rows = f.get("rows") or []
        n_rows = len(rows) if isinstance(rows, list) else 0
        if isinstance(rows, list):
            raced += sum(1 for r in rows if isinstance(r, dict) and r.get("raced"))
        try:
            n_decl = int(f.get("entries") or f.get("entries_raced") or 0)
        except (TypeError, ValueError):
            n_decl = 0
        n = n_rows if n_rows else n_decl
        if n <= 0:
            continue
        total += n
        per_fleet.append((_fleet_entry_label(f), n))
    return raced, total, per_fleet


def count_raced_and_entries(fleets: Optional[Iterable[Any]]) -> tuple[int, int]:
    raced, entries, _fleets = count_event_entries_by_fleet(fleets)
    return raced, entries


def derive_event_lifecycle(
    *,
    start_date: Any,
    end_date: Any,
    result_status: Any,
    as_at_time: Any,
    raced_count: int = 0,
    today: Optional[date] = None,
) -> str:
    """PRE-POPULATED/UPCOMING → LIVE → RESULTS → FINAL/HISTORY from existing fields only."""
    today = today or date.today()
    st = _as_date(start_date)
    en = _as_date(end_date) or st
    status = (str(result_status or "")).strip().lower()
    if st and st > today:
        return "upcoming"
    if st and en and st <= today <= en:
        return "live"
    if status == "final":
        return "final"
    if en and en < today:
        if status.startswith("provisional"):
            return "provisional"
        return "historical"
    if int(raced_count or 0) > 0 or _has_real_as_at(as_at_time):
        if status.startswith("provisional"):
            return "provisional"
        return "historical"
    return "upcoming"


def event_document_title(display_name: str, state: str, start_date: Any, end_date: Any) -> str:
    name = (display_name or "Regatta").strip() or "Regatta"
    dates = compact_event_date_range(start_date, end_date)
    if state == "upcoming":
        mid = f"{name} — {dates}" if dates else name
    elif state == "live":
        mid = f"{name} — Live"
    elif state == "provisional":
        mid = f"{name} — Provisional Results"
    elif state == "final":
        mid = f"{name} — Final Results"
    else:
        mid = f"{name} — Results" if dates else name
    return f"{mid} | SailingSA"


def event_meta_description(
    *,
    display_name: str,
    state: str,
    start_date: Any,
    end_date: Any,
    host_club: str = "",
    class_names: Optional[Iterable[str]] = None,
    entries: int = 0,
    raced_count: int = 0,
) -> str:
    name = (display_name or "Regatta").strip() or "Regatta"
    dates = compact_event_date_range(start_date, end_date)
    host = re.sub(r"\s+", " ", (host_club or "").strip())
    classes = [c.strip() for c in (class_names or []) if str(c).strip()]
    class_bit = ""
    if len(classes) == 1:
        class_bit = f" {classes[0]} sailing"
    elif 1 < len(classes) <= 4:
        class_bit = " " + ", ".join(classes)

    loc = f" at {host}" if host else ""
    when = f", {dates}" if dates else ""

    if state == "upcoming":
        extra = ""
        if entries > 0:
            extra = f" {entries} entries listed."
        else:
            extra = " Upcoming event page on SailingSA."
        return f"{name}{loc}{when}.{class_bit}.{extra}".replace("..", ".").strip()
    if state == "live":
        extra = " Live event on SailingSA."
        if raced_count > 0:
            extra = " Live results updating on SailingSA."
        return f"{name}{loc}{when}.{class_bit}.{extra}".replace("..", ".").strip()
    if state == "provisional":
        return f"{name}{loc}{when}. Provisional results on SailingSA.".replace("..", ".").strip()
    if state == "final":
        return f"{name}{loc}{when}. Final results on SailingSA.".replace("..", ".").strip()
    return f"{name}{loc}{when}. Results on SailingSA.".replace("..", ".").strip()


def event_visible_status_text(
    state: str,
    start_date: Any,
    end_date: Any,
    *,
    as_at_time: Any = None,
    formatted_results_line: str = "",
) -> str:
    """Visible header status. Upcoming/no snapshot must not claim Provisional Results or invent as_at."""
    dates = compact_event_date_range(start_date, end_date)
    if state == "upcoming":
        return f"Upcoming Event — {dates}" if dates else "Upcoming Event"
    if state == "live" and not _has_real_as_at(as_at_time):
        return f"Live Event — {dates}" if dates else "Live Event"
    if formatted_results_line and _has_real_as_at(as_at_time):
        return formatted_results_line
    if state == "final":
        return "Results are Final" + (" (snapshot time not recorded)" if not _has_real_as_at(as_at_time) else "")
    if state == "provisional":
        return "Results are Provisional" + (
            " (snapshot time not recorded)" if not _has_real_as_at(as_at_time) else ""
        )
    return formatted_results_line or (f"Event — {dates}" if dates else "Event")


def event_schema_status(state: str) -> Optional[str]:
    """Official schema.org EventStatusType only. Omit for completed/final/history."""
    if state in ("upcoming", "live"):
        return "https://schema.org/EventScheduled"
    return None


def sports_event_json_ld(
    *,
    name: str,
    canonical_url: str,
    state: str,
    start_date: Any,
    end_date: Any,
    description: str = "",
    host_club: str = "",
    host_club_url: str = "",
    province: str = "",
    image_url: str = "",
    series_name: str = "",
    series_url: str = "",
) -> dict:
    st = _as_date(start_date)
    en = _as_date(end_date)
    out: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": (name or "").strip(),
        "sport": "Sailing",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
    }
    if canonical_url:
        out["url"] = canonical_url
    ev_status = event_schema_status(state)
    if ev_status:
        out["eventStatus"] = ev_status
    if st:
        out["startDate"] = st.isoformat()
    if en:
        out["endDate"] = en.isoformat()
    if description:
        out["description"] = description
    if host_club:
        org: dict[str, Any] = {"@type": "Organization", "name": host_club}
        if host_club_url:
            org["url"] = host_club_url
        out["organizer"] = org
        addr: dict[str, Any] = {"@type": "PostalAddress", "addressCountry": "ZA"}
        if province:
            addr["addressLocality"] = province
        out["location"] = {"@type": "Place", "name": host_club, "address": addr}
    if image_url:
        out["image"] = image_url
    if series_name and series_url:
        out["superEvent"] = {
            "@type": "SportsEvent",
            "name": series_name,
            "url": series_url,
        }
    return out


def breadcrumb_json_ld(*, event_name: str, canonical_url: str, base_url: str) -> dict:
    base = (base_url or "https://sailingsa.co.za").rstrip("/")
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Events", "item": f"{base}/events"},
            {
                "@type": "ListItem",
                "position": 3,
                "name": (event_name or "Event").strip() or "Event",
                "item": canonical_url,
            },
        ],
    }


def _class_href(class_name: str) -> str:
    s = (class_name or "").strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s)
    if s and re.match(r"^\d+-", s):
        s = s.split("-", 1)[1]
    return f"/class/{s}" if s else ""


def event_context_footer_html(
    *,
    display_name: str,
    state: str,
    start_date: Any,
    end_date: Any,
    host_club: str = "",
    host_club_href: str = "",
    venue: str = "",
    class_names: Optional[Iterable[str]] = None,
    entries: int = 0,
    fleet_counts: Optional[list[tuple[str, int]]] = None,
    as_at_display: str = "",
    series_name: str = "",
    series_href: str = "",
    edition_year: Optional[int] = None,
    previous_editions: Optional[list[dict]] = None,
) -> str:
    """Additive crawlable context only. Never repeat name/date/status/host/venue/class/entries."""
    bits: list[str] = []
    if series_name and series_href:
        yr = f"{edition_year} edition" if edition_year else "this edition"
        bits.append(
            "<p>Part of "
            f'<a href="{html_module.escape(series_href)}">{html_module.escape(series_name)}</a>'
            f" — {html_module.escape(yr)}"
            f' · <a href="{html_module.escape(series_href)}">previous editions</a></p>'
        )
        prevs = []
        for row in previous_editions or []:
            url = str(row.get("url") or "").strip()
            year = row.get("year")
            if not url.startswith("/regatta/") or not year:
                continue
            if edition_year and int(year) == int(edition_year):
                continue
            prevs.append(
                f'<a href="{html_module.escape(url)}">{html_module.escape(str(year))}</a>'
            )
            if len(prevs) >= 4:
                break
        if prevs:
            bits.append("<p>Previous editions: " + ", ".join(prevs) + "</p>")

    inner = "".join(bits)
    if not inner:
        return ""
    if any(tok in inner for tok in ("Host:", "Venue:", "Classes:", "Entries:", "Upcoming Event")):
        return ""
    return f'<section class="regatta-event-context" aria-label="Event information">{inner}</section>'


def json_ld_script_tags(*payloads: dict) -> str:
    parts = []
    for p in payloads:
        if p:
            parts.append(
                f'<script type="application/ld+json">{json.dumps(p, ensure_ascii=False)}</script>'
            )
    return "".join(parts)


def build_regatta_pass_b(
    *,
    display_name: str,
    canonical_url: str,
    base_url: str,
    start_date: Any,
    end_date: Any,
    result_status: Any,
    as_at_time: Any,
    fleets: Optional[Iterable[Any]] = None,
    host_club: str = "",
    host_club_href: str = "",
    province: str = "",
    venue: str = "",
    class_names: Optional[list[str]] = None,
    series_name: str = "",
    series_href: str = "",
    previous_editions: Optional[list[dict]] = None,
    formatted_results_line: str = "",
    as_at_display: str = "",
    image_url: str = "",
    today: Optional[date] = None,
) -> dict:
    raced, entries, fleet_counts = count_event_entries_by_fleet(fleets)
    state = derive_event_lifecycle(
        start_date=start_date,
        end_date=end_date,
        result_status=result_status,
        as_at_time=as_at_time,
        raced_count=raced,
        today=today,
    )
    title = event_document_title(display_name, state, start_date, end_date)
    description = event_meta_description(
        display_name=display_name,
        state=state,
        start_date=start_date,
        end_date=end_date,
        host_club=host_club,
        class_names=class_names,
        entries=entries,
        raced_count=raced,
    )
    status_visible = event_visible_status_text(
        state,
        start_date,
        end_date,
        as_at_time=as_at_time,
        formatted_results_line=formatted_results_line,
    )
    edition_year = None
    st = _as_date(start_date)
    if st:
        edition_year = st.year
    sport = sports_event_json_ld(
        name=display_name,
        canonical_url=canonical_url,
        state=state,
        start_date=start_date,
        end_date=end_date,
        description=description,
        host_club=host_club,
        host_club_url=host_club_href if host_club_href.startswith("http") else (
            (base_url.rstrip("/") + host_club_href) if host_club_href else ""
        ),
        province=province,
        image_url=image_url,
        series_name=series_name,
        series_url=(
            series_href
            if series_href.startswith("http")
            else ((base_url.rstrip("/") + series_href) if series_href else "")
        ),
    )
    crumbs = breadcrumb_json_ld(
        event_name=display_name, canonical_url=canonical_url, base_url=base_url
    )
    footer = event_context_footer_html(
        display_name=display_name,
        state=state,
        start_date=start_date,
        end_date=end_date,
        host_club=host_club,
        host_club_href=host_club_href,
        venue=venue,
        class_names=class_names,
        entries=entries,
        fleet_counts=fleet_counts,
        as_at_display=as_at_display if _has_real_as_at(as_at_time) else "",
        series_name=series_name,
        series_href=series_href,
        edition_year=edition_year,
        previous_editions=previous_editions,
    )
    return {
        "state": state,
        "title": title,
        "description": description,
        "status_visible": status_visible,
        "json_ld_html": json_ld_script_tags(sport, crumbs),
        "footer_html": footer,
        "schema_event_status": event_schema_status(state),
        "entries": entries,
        "raced": raced,
    }
