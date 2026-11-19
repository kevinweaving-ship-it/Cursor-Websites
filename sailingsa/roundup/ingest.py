"""Event-URL-first ingest: SailingSA event/regatta pages before any external source."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
except ImportError:  # fixture-only builds do not need the live client
    httpx = None

from sailingsa.roundup.models import slugify
from sailingsa.roundup.week import select_week_events

LIVE_ORIGIN = "https://sailingsa.co.za"
USER_AGENT = "SailingSA-RoundupRebuild/0.1 (+https://sailingsa.co.za)"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def fixture_dir(week: str) -> Path:
    return package_root() / "fixtures" / week


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _client():
    if httpx is None:
        raise RuntimeError("httpx is required for --live ingest (pip install httpx)")
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    )


def fetch_live_events() -> list[dict]:
    with _client() as client:
        response = client.get(f"{LIVE_ORIGIN}/api/events")
        response.raise_for_status()
        data = response.json()
    return data if isinstance(data, list) else []


def fetch_live_regatta(regatta_id: str) -> list[dict]:
    with _client() as client:
        response = client.get(f"{LIVE_ORIGIN}/api/regatta/{regatta_id}")
        response.raise_for_status()
        data = response.json()
    return data if isinstance(data, list) else []


def fetch_live_summary(regatta_id: str) -> dict:
    with _client() as client:
        response = client.get(f"{LIVE_ORIGIN}/api/regatta/{regatta_id}/results-summary")
        response.raise_for_status()
        data = response.json()
    return data if isinstance(data, dict) else {}


def guess_event_id(event: dict) -> str:
    rid = str(event.get("regatta_id") or "").strip()
    if rid:
        return rid
    name = slugify(str(event.get("event_name") or "event"))
    year = str(event.get("end_date") or event.get("start_date") or "")[:4]
    if "df95" in name or "df-95" in name:
        return "2026-df95-global-championship" if year == "2026" else name
    if "nw-youth" in name or "nw-youth-regionals" in name:
        return "2026-nw-youth-regionals"
    return name or "unknown-event"


def load_week_bundle(week: str, live: bool = False) -> dict:
    """Load events + event-URL-first results. Fixtures are the default dry-run path."""
    from datetime import date

    edition = date.fromisoformat(week)
    fx = fixture_dir(week)
    if live:
        events = fetch_live_events()
    else:
        if not (fx / "events.json").exists():
            raise FileNotFoundError(
                f"No fixtures for {week}. Run with --live or add fixtures under {fx}"
            )
        events = load_json(fx / "events.json")
    selected = select_week_events(events, edition)
    items: list[dict] = []
    for event in selected["owned"] + selected["late"]:
        items.append(_attach_event_payload(event, fx=fx, live=live, late=event in selected["late"]))
    selected["items"] = items
    selected["sources"] = _load_sources(fx)
    return selected


def _attach_event_payload(event: dict, fx: Path, live: bool, late: bool) -> dict:
    event_id = guess_event_id(event)
    rid = str(event.get("regatta_id") or "").strip() or None
    payload = {
        "event_id": event_id,
        "event": event,
        "late": late,
        "regatta_id": rid,
        "event_url": f"{LIVE_ORIGIN}/regatta/{rid}" if rid else None,
        "results": [],
        "summary": {},
        "page": {},
        "ingest_order": ["event_url_first"],
    }
    if rid:
        results_path = fx / "regatta" / f"{rid}.json"
        summary_path = fx / "summaries" / f"{rid}.json"
        page_path = fx / "pages" / f"{rid}.json"
        if live:
            payload["results"] = fetch_live_regatta(rid)
            payload["summary"] = fetch_live_summary(rid)
            payload["page"] = {
                "url": payload["event_url"],
                "title": "",
                "images": [],
                "fetched_from": "event_url_first_live",
            }
        else:
            payload["results"] = load_json(results_path) if results_path.exists() else []
            payload["summary"] = load_json(summary_path) if summary_path.exists() else {}
            payload["page"] = load_json(page_path) if page_path.exists() else {}
    else:
        payload["ingest_order"].append("no_sailingsa_regatta_page")
    return payload


def _load_sources(fx: Path) -> list[dict]:
    sources: list[dict] = []
    src_dir = fx / "sources"
    if not src_dir.exists():
        return sources
    for path in sorted(src_dir.glob("*.json")):
        sources.append(load_json(path))
    return sources


def absolute_media_url(url: str | None) -> str | None:
    if not url:
        return None
    return urljoin(LIVE_ORIGIN, url)
