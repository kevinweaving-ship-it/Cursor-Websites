"""Event URLs that must appear on landing search + hub before a live SQL apply.

Landing upcoming cards and /api/regattas/with-counts only see rows with a
regatta_id. Calendar-only events (Dart 18 Nationals 2026) stay invisible until
this registry attaches the Event URL — same shape as 420 Nationals once it had
a live regattas row.
"""

from __future__ import annotations

from datetime import date

HMYC_DART_18_NATIONALS_SLUG = "2026-09-24-hmyc-dart-18-nationals"

PRELOADED_EVENT_URLS = (
    {
        "regatta_id": HMYC_DART_18_NATIONALS_SLUG,
        "event_name": "Dart 18 Nationals incorporating the KZN provincials",
        "year": 2026,
        "start_date": "2026-09-24",
        "end_date": "2026-09-27",
        "host_club_code": "HMYC",
        "host_club_name": "HMYC",
        "host_club_fullname": "Henley Midmar Yacht Club",
        "province": "KZN",
        "regatta_number": 999010,
        "source_event_ids": frozenset({"367984"}),
        "fleet_label": "Dart 18",
    },
)


def _norm(s) -> str:
    return str(s or "").strip().lower()


def _is_dart_18_nationals_title(name: str) -> bool:
    n = _norm(name)
    if "dart 18" not in n and "dart18" not in n.replace(" ", ""):
        return False
    if "national" not in n:
        return False
    if "single" in n and "handed" in n:
        return False
    if " sh " in f" {n} ":
        return False
    return True


def preloaded_by_id(regatta_id: str) -> dict | None:
    rid = str(regatta_id or "").strip()
    if not rid:
        return None
    for item in PRELOADED_EVENT_URLS:
        if item["regatta_id"] == rid:
            return item
    return None


def match_preloaded_event(
    event_name: str = "",
    start_date=None,
    source_event_id: str = "",
    source_url: str = "",
) -> dict | None:
    sid = str(source_event_id or "").strip()
    surl = _norm(source_url)
    sd = str(start_date or "")[:10]
    for item in PRELOADED_EVENT_URLS:
        if sid and sid in item["source_event_ids"]:
            return item
        if any(eid and eid in surl for eid in item["source_event_ids"]):
            return item
        if _is_dart_18_nationals_title(event_name) and (
            not sd or sd == item["start_date"] or sd.startswith(str(item["year"]))
        ):
            if item["regatta_id"] == HMYC_DART_18_NATIONALS_SLUG:
                return item
    return None


def attach_preloaded_regatta_ids(items: list | None) -> list:
    """Set events.regatta_id on calendar rows that match a preload."""
    out = items if isinstance(items, list) else []
    for ev in out:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("regatta_id") or "").strip():
            continue
        hit = match_preloaded_event(
            ev.get("event_name") or ev.get("regatta_event_name") or "",
            ev.get("start_date"),
            ev.get("source_event_id") or ev.get("external_event_id") or ev.get("event_id") or "",
            ev.get("source_url") or ev.get("details_url") or "",
        )
        if not hit:
            continue
        ev["regatta_id"] = hit["regatta_id"]
        ev["has_regatta"] = True
        ev["host_club_code"] = ev.get("host_club_code") or hit["host_club_code"]
        ev["host_club_name"] = ev.get("host_club_name") or hit["host_club_name"]
    return out


def _hay(item: dict) -> str:
    return " ".join(
        [
            str(item.get("event_name") or ""),
            str(item.get("regatta_id") or ""),
            str(item.get("host_club_code") or ""),
            str(item.get("host_club_name") or ""),
            str(item.get("start_date") or ""),
            str(item.get("end_date") or ""),
            "dart nationals kzn provincials hmyc",
        ]
    ).lower()


def search_query_matches_preload(q: str, item: dict) -> bool:
    raw = (q or "").strip()
    if not raw:
        return True
    hay = _hay(item)
    for term in raw.lower().split():
        if term.isdigit() and len(term) == 4:
            if term not in hay and term != str(item.get("year") or ""):
                return False
            continue
        if term not in hay:
            return False
    return True


def search_row(item: dict) -> dict:
    return {
        "regatta_id": item["regatta_id"],
        "event_name": item["event_name"],
        "year": item["year"],
        "regatta_number": item["regatta_number"],
        "start_date": item["start_date"],
        "end_date": item["end_date"],
        "host_club_name": item["host_club_fullname"],
        "host_club_code": item["host_club_code"],
        "entries_count": 0,
        "match_reason": "Best match",
        "match_reason_term": None,
        "slug": item["regatta_id"],
        "is_live": False,
        "preloaded_event_url": True,
    }


def inject_preloaded_into_search(rows: list | None, q: str | None = None) -> list:
    out = list(rows) if isinstance(rows, list) else []
    have = {str(r.get("regatta_id") or "").strip() for r in out if isinstance(r, dict)}
    for item in PRELOADED_EVENT_URLS:
        rid = item["regatta_id"]
        if rid in have:
            continue
        if not search_query_matches_preload(q, item):
            continue
        out.insert(0, search_row(item))
        have.add(rid)
    return out


def preloaded_results_summary(regatta_id: str) -> dict | None:
    item = preloaded_by_id(regatta_id)
    if not item:
        return None
    return {
        "entries_total": 0,
        "races_total": 0,
        "regatta_id": item["regatta_id"],
        "result_name": item["event_name"],
        "event_name": item["event_name"],
        "start_date": item["start_date"],
        "end_date": item["end_date"],
        "result_status": "None",
        "as_at_time": None,
        "host_club_code": item["host_club_code"],
        "host_club_name": item["host_club_name"],
        "host_club_id": None,
        "fleet_classes": [],
        "fleet_stats": [],
        "fleet_count": 0,
        "entries_checksum_ok": True,
        "blank_hub_news_badge_label": "Upcoming Event",
        "blank_hub_news_image_url": None,
        "blank_hub_news_album": [],
        "blank_hub_news_show_hero": True,
        "preloaded_event_url": True,
    }


def preloaded_slug_tuple(regatta_id: str):
    item = preloaded_by_id(regatta_id)
    if not item:
        return None
    return (
        item["regatta_id"],
        item["event_name"],
        date.fromisoformat(item["start_date"]),
        date.fromisoformat(item["end_date"]),
        item["host_club_name"],
        None,
    )


def preloaded_full_page_data(regatta_id: str):
    item = preloaded_by_id(regatta_id)
    if not item:
        return None
    fleets = [
        {
            "block_id": f"{item['regatta_id']}:dart-18",
            "name": item["fleet_label"],
            "fleet_label": item["fleet_label"],
            "class_canonical": item["fleet_label"],
            "races_sailed": 0,
            "discard_count": 0,
            "to_count": 0,
            "scoring_system": "Appendix A",
            "rows": [],
            "regatta_id": item["regatta_id"],
            "class_slug": "dart-18",
            "entries": 0,
        }
    ]
    return (
        item["event_name"],
        item["host_club_name"],
        date.fromisoformat(item["start_date"]),
        date.fromisoformat(item["end_date"]),
        fleets,
        "Provisional",
        None,
        item["province"],
        item["host_club_code"],
        item["host_club_fullname"],
    )
