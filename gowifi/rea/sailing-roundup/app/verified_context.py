"""Verified third-party articles for calendar events without a SailingSA results card.

Placings are copied from a results file only after the event name and dates match.
A later daily rebuild re-checks that file. If the check cannot be repeated, the last
verified placings are kept and not replaced with a guess.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "SailingSA-Roundup/1.0"}
DF95_RESULTS = "https://mysailingresults.com/api/results/get_results.php?eventid=22056"
DF95_PAGE = "https://mysailingresults.com/dev/results/22056"
DF95_STORY = "https://radiosailing.org.au/news/492"
NW_NOTICE = "https://www.revolutionise.com.au/boskopyc/events/385472"
ULLMAN_NOTICE = "https://rcyc.co.za/event/2026-ladies-race-day-2/"
FLEET_LABELS = {"G": "Gold", "S": "Silver", "B": "Bronze", "C": "Copper"}


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _fetch_bytes(url: str, timeout: int = 20) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        kind = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        return resp.read(), kind


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _points(value) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        return text[:-2]
    return text


def _identity(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\b20\d{2}\b", "", (name or "").lower()))


def _snapshot_path(issue: str, root: pathlib.Path) -> pathlib.Path:
    return root / "data" / "verified-context" / f"{issue}.json"


def _load_snapshot(issue: str, root: pathlib.Path) -> dict:
    path = _snapshot_path(issue, root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_snapshot(issue: str, root: pathlib.Path, payload: dict) -> None:
    path = _snapshot_path(issue, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _image_file(issue: str, root: pathlib.Path, name: str, blob: bytes) -> str | None:
    if blob.startswith(b"\x89PNG"):
        ext = ".png"
    elif blob.startswith(b"\xff\xd8"):
        ext = ".jpg"
    else:
        return None
    folder = root / "issues" / issue / "media"
    folder.mkdir(parents=True, exist_ok=True)
    filename = name + ext
    (folder / filename).write_bytes(blob)
    return "media/" + filename


def _df95_rows(payload: dict, calendar: dict) -> list[dict] | None:
    event = payload.get("event") or {}
    name = str(event.get("eventname") or "")
    if not re.search(r"df\s*95", name, re.I) or "global" not in name.lower():
        return None
    end = str(event.get("eventenddate") or "")[:10]
    start = str(event.get("eventstartdate") or "")[:10]
    if end != str(calendar.get("end_date") or "")[:10]:
        return None
    try:
        official = dt.date.fromisoformat(start)
        listed = dt.date.fromisoformat(str(calendar.get("start_date") or "")[:10])
    except ValueError:
        return None
    if abs((official - listed).days) > 2:
        return None
    rows = payload.get("results") or []
    if not isinstance(rows, list):
        return None
    kept = []
    for row in rows:
        try:
            place = int(str(row.get("comppos") or ""))
        except ValueError:
            continue
        sailor = str(row.get("compname") or "").strip()
        if sailor:
            kept.append(dict(row, comppos=str(place)))
    kept.sort(key=lambda row: int(row["comppos"]))
    return kept or None


def _fleet_labels_verified(story: str, rows: list[dict]) -> bool:
    needed = (
        ("Craig Richards", "Gold Fleet"),
        ("Phil Burgess", "Silver Fleet"),
        ("John Wyatt", "Bronze Fleet"),
        ("Brian Schneider", "Copper Fleet"),
    )
    if any(name not in story or label not in story for name, label in needed):
        return False
    places = {row["compname"]: (row.get("fleet"), int(row["comppos"])) for row in rows}
    return (
        places.get("Craig Richards") == ("G", 1)
        and places.get("Phil Burgess") == ("S", 18)
        and places.get("John Wyatt") == ("B", 35)
        and places.get("Brian Schneider") == ("C", 62)
    )


def _df95_article(issue: str, calendar: dict, rows: list[dict], story: str, image: str | None) -> dict:
    by_place = {int(row["comppos"]): row for row in rows}
    first, second, third = by_place.get(1), by_place.get(2), by_place.get(3)
    if not first or not second or not third:
        raise ValueError("DF95 results have no overall podium")
    labelled = _fleet_labels_verified(story, rows)
    races = 0
    sample = first.get("results") or {}
    if isinstance(sample, dict):
        races = len(sample)

    opening = (
        f"{first['compname']} ({first.get('compregcountry') or ''}) won the 2026 DF95 Global Championship "
        f"at Theewater Sports Club on {_points(first.get('nettScore'))} nett points. "
        f"{second['compname']} ({second.get('compregcountry') or ''}) was second on {_points(second.get('nettScore'))} "
        f"and {third['compname']} ({third.get('compregcountry') or ''}) third on {_points(third.get('nettScore'))}. "
        f"mySailingResults lists {len(rows)} sailors"
        + (f" and {races} races" if races else "")
        + "."
    )
    south_africa = [row for row in rows if str(row.get("compregcountry") or "").upper() == "RSA"]
    if not south_africa:
        raise ValueError("DF95 results did not include a verified South African placing")
    bits = []
    for row in south_africa:
        fleet = FLEET_LABELS.get(row.get("fleet") or "", "")
        fleet_bit = f", {fleet} fleet" if labelled and fleet else ""
        bits.append(f"{_ordinal(int(row['comppos']))} {row['compname']}{fleet_bit}")
    placing = "South African placings: " + "; ".join(bits) + "."
    blocks = []
    if image:
        blocks.append({
            "type": "image",
            "url": image,
            "role": "support",
            "alt": "2026 DF95 Global Championship at Theewater Sports Club",
            "caption": "2026 DF95 Global Championship at Theewater Sports Club.",
            "credit": "Australian Radio Yachting Association",
        })
    blocks.append({"type": "paragraph", "text": opening})
    blocks.append({"type": "paragraph", "text": placing})
    return {
        "id": "2026-df95-global-championship",
        "event_id": "2026-df95-global-championship",
        "type": "brief",
        "review_status": "verified_external",
        "headline": "Craig Richards wins the DF95 Global Championship",
        "deck": "Theewater Sports Club · 16–23 October 2026",
        "kicker": "DF95",
        "class_name": "DF95",
        "start_date": calendar.get("start_date") or "",
        "end_date": calendar.get("end_date") or "",
        "blocks": blocks,
        "sources": [DF95_PAGE, DF95_STORY],
        "third_party": True,
        "needs_external": False,
        "week_fact": {
            "name": calendar.get("event_name") or "",
            "start": calendar.get("start_date") or "",
            "end": calendar.get("end_date") or "",
        },
    }


def _notice_article(issue: str, calendar: dict, page: str, spec: dict, image: str | None) -> dict | None:
    for needle in spec["needles"]:
        if needle not in page:
            return None
    blocks = []
    if image:
        blocks.append({
            "type": "image",
            "url": image,
            "role": "support",
            "alt": spec["alt"],
            "caption": spec["caption"],
            "credit": spec["credit"],
        })
    blocks.append({"type": "paragraph", "text": spec["text"]})
    return {
        "id": spec["id"],
        "event_id": spec["id"],
        "type": "brief",
        "review_status": "verified_external",
        "headline": spec["headline"],
        "deck": spec["deck"],
        "kicker": spec["kicker"],
        "class_name": spec["kicker"],
        "start_date": calendar.get("start_date") or spec.get("start") or "",
        "end_date": calendar.get("end_date") or spec.get("end") or "",
        "blocks": blocks,
        "sources": [spec["url"]],
        "third_party": True,
        "needs_external": False,
        "week_fact": {
            "name": calendar.get("event_name") or spec["headline"],
            "start": calendar.get("start_date") or spec.get("start") or "",
            "end": calendar.get("end_date") or spec.get("end") or "",
        },
    }


def _page_image(issue: str, root: pathlib.Path, page: str, page_url: str, stem: str, fetch_bytes) -> str | None:
    match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', page, re.I)
    if not match:
        match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', page, re.I)
    if not match:
        return None
    src = match.group(1)
    if "logo" in src.lower():
        return None
    if src.startswith("/"):
        origin = urllib.request.urlsplit(page_url)
        src = f"{origin.scheme}://{origin.netloc}{src}"
    try:
        blob, _kind = fetch_bytes(src)
    except Exception:
        return None
    if len(blob) < 8000:
        return None
    return _image_file(issue, root, stem, blob)


def _df95_image(issue: str, root: pathlib.Path, story: str, fetch_bytes) -> str | None:
    match = re.search(r'src=["\']([^"\']*dfglob1[^"\']*)["\']', story, re.I)
    if not match:
        return None
    src = match.group(1)
    if src.startswith("/"):
        src = "https://radiosailing.org.au" + src
    try:
        blob, _kind = fetch_bytes(src)
    except Exception:
        return None
    return _image_file(issue, root, "df95-global-2026", blob)


def build_verified_articles(issue: str, table_events: list[dict], excluded: list[dict] | None = None, root: pathlib.Path | None = None, fetch=None, fetch_bytes=None) -> list[dict]:
    root = root or ROOT
    fetch = fetch or _fetch
    fetch_bytes = fetch_bytes or _fetch_bytes
    articles = []
    seen = set()
    for event in table_events or []:
        name = event.get("event_name") or ""
        key = event.get("regatta_id") or _identity(name)
        if not key or key in seen or event.get("has_results"):
            continue
        if re.search(r"df\s*95", name, re.I) and re.search(r"global", name, re.I):
            seen.add(key)
            try:
                payload = json.loads(fetch(DF95_RESULTS))
                rows = _df95_rows(payload, event)
                story = fetch(DF95_STORY)
                if not rows or "Craig Richards" not in story or "Ulf Lindberg" not in story:
                    raise ValueError("DF95 source did not confirm the podium")
                image = _df95_image(issue, root, story, fetch_bytes)
                articles.append(_df95_article(issue, event, rows, story, image))
            except Exception:
                saved = _load_snapshot(issue, root).get("2026-df95-global-championship")
                if saved:
                    articles.append(saved)
            continue
        if _identity(name) == _identity("NW Youth Regionals Regatta"):
            seen.add(key)
            spec = {
                "id": "2026-nw-youth-regionals",
                "url": NW_NOTICE,
                "headline": "NW Youth Regionals at Boskop",
                "deck": "Boskop Yacht Club · 24–25 October 2026",
                "kicker": "YOUTH",
                "needles": ["NW Youth Regionals Regatta 2026", "Boskop Yacht Club", "24 Oct 2026"],
                "text": "Boskop Yacht Club listed the NW Youth Regionals Regatta 2026 for 24–25 October at Boskop Dam, Potchefstroom, as its youth dinghy regional championship. SailingSA has not published results.",
                "alt": "NW Youth Regionals notice",
                "caption": "NW Youth Regionals Regatta 2026 at Boskop Yacht Club.",
                "credit": "Boskop Yacht Club",
                "start": "2026-10-24",
                "end": "2026-10-25",
            }
            try:
                page = fetch(NW_NOTICE)
                image = _page_image(issue, root, page, NW_NOTICE, "nw-youth-regionals-2026", fetch_bytes)
                article = _notice_article(issue, event, page, spec, image)
                if article:
                    articles.append(article)
            except Exception:
                saved = _load_snapshot(issue, root).get(spec["id"])
                if saved:
                    articles.append(saved)
    for item in excluded or []:
        if item.get("reason") != "event_listing_without_scored_results":
            continue
        slug = item.get("slug") or ""
        if "ullman" not in slug or "2026-10-24" not in slug or slug in seen:
            continue
        seen.add(slug)
        spec = {
            "id": "2026-ullman-womens-series-day-2",
            "url": ULLMAN_NOTICE,
            "headline": "Ullman Sails Women's Series day 2",
            "deck": "Royal Cape Yacht Club · 24 October 2026",
            "kicker": "RCYC",
            "needles": ["October 24", "Women", "passed"],
            "text": "Royal Cape Yacht Club lists Ullman Sails Women's Series Race Day 2 on 24 October 2026 in Table Bay and marks the day as passed. SailingSA has not published scored results.",
            "alt": "Ullman Sails Women's Series day 2",
            "caption": "Ullman Sails Women's Series Race Day 2 at Royal Cape Yacht Club.",
            "credit": "Royal Cape Yacht Club",
            "start": "2026-10-24",
            "end": "2026-10-24",
        }
        try:
            page = fetch(ULLMAN_NOTICE)
            image = _page_image(issue, root, page, ULLMAN_NOTICE, "ullman-womens-day-2-2026", fetch_bytes)
            article = _notice_article(issue, {"event_name": "Ullman Sails Women's Series Day 2", "start_date": "2026-10-24", "end_date": "2026-10-24"}, page, spec, image)
            if article:
                articles.append(article)
        except Exception:
            saved = _load_snapshot(issue, root).get(spec["id"])
            if saved:
                articles.append(saved)
    return articles


def attach_verified_context(issue: str, story: dict, table_events: list[dict], excluded: list[dict] | None = None, root: pathlib.Path | None = None, fetch=None, fetch_bytes=None) -> dict:
    """Add compact verified articles without replacing scored SailingSA reports."""
    root = root or ROOT
    fresh = build_verified_articles(issue, table_events, excluded, root=root, fetch=fetch, fetch_bytes=fetch_bytes)
    articles = [article for article in (story.get("articles") or []) if article.get("review_status") != "verified_external"]
    seen = {_identity((article.get("week_fact") or {}).get("name") or article.get("headline") or "") for article in articles}
    kept = []
    for article in fresh:
        key = _identity((article.get("week_fact") or {}).get("name") or article.get("headline") or "")
        if key and key in seen:
            continue
        seen.add(key)
        kept.append(article)
    story["articles"] = articles + kept
    snapshot = _load_snapshot(issue, root)
    for article in kept:
        snapshot[article["id"]] = article
    if kept:
        _save_snapshot(issue, root, snapshot)
    return story
