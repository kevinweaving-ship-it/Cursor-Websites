#!/usr/bin/env python3
"""Monday publisher: weekend events → social/media pack → landing HTML + PDF."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from event_rewrite import (
    facts_from_rows,
    layout_for,
    rewrite_event,
    rewrite_weekend_feature,
)
from events_weekend import (
    _fetch_events,
    issue_monday_for_end,
    previous_week,
    slugs_for_weekend,
    weekend_events,
    year_issue_mondays,
)
from sailor_mentions import parse_day

UA = {"User-Agent": "SailingRoundupResearch/1.0"}
EVENTS_PAGES = (
    "https://sailingsa.co.za/events",
    "https://sailingsa.co.za/yearly-events",
)
SKIP_NAME = re.compile(
    r"\b(course|workshop|training|meeting|seminar|clinic|agm|safety boat|instructor)\b",
    re.I,
)
STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "2026",
    "2025",
    "2024",
    "sailing",
    "event",
    "sa",
    "sas",
    "inc",
    "incorporating",
}


def fetch_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def last_monday(today: dt.date | None = None) -> dt.date:
    today = today or dt.datetime.now(__import__("zoneinfo").ZoneInfo("Africa/Johannesburg")).date()
    return today - dt.timedelta(days=today.weekday())


def weekend_bounds(monday: dt.date) -> tuple[dt.date, dt.date]:
    """Previous calendar week (Mon–Sun) covered by this Monday issue."""
    return previous_week(monday)


def issue_mondays(today: dt.date | None = None, backfill: int = 4) -> list[dt.date]:
    monday = last_monday(today)
    return [monday - dt.timedelta(weeks=i) for i in range(backfill)]


def skip_event_name(name: str) -> bool:
    return bool(SKIP_NAME.search(name or ""))


def event_terms(*parts: str) -> list[str]:
    text = " ".join(p or "" for p in parts).lower()
    words = re.findall(r"[a-z0-9]+", text)
    out = []
    for word in words:
        if word in STOP or len(word) < 3 or word in out:
            continue
        out.append(word)
    return out[:16]


def scrape_slugs(html: str) -> set[str]:
    return set(re.findall(r"/regatta/(\d{4}-\d{2}-\d{2}-[a-z0-9-]+)", html or ""))


def discover_slugs(monday: dt.date) -> list[str]:
    """Primary source is the public events table. HTML slugs are a fallback."""
    slugs = slugs_for_weekend(monday)
    if slugs:
        return slugs
    week_start, week_end = previous_week(monday)
    found: set[str] = set()
    for url in EVENTS_PAGES:
        try:
            found |= scrape_slugs(fetch_text(url))
        except Exception:
            continue
    chosen = []
    for slug in sorted(found):
        try:
            day = dt.date.fromisoformat(slug[:10])
        except ValueError:
            continue
        if skip_event_name(slug):
            continue
        if issue_monday_for_end(day) == monday or week_start <= day <= week_end:
            chosen.append(slug)
    return chosen


def fetch_regatta(slug: str) -> list[dict]:
    data = fetch_json("https://sailingsa.co.za/api/regatta/" + slug)
    return data if isinstance(data, list) else []


def sailor_ids(rows: list[dict], limit: int = 24) -> list[str]:
    """Collect SAS IDs from each class fleet so Media-tab notes can checksum."""
    ids = []
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for row in rows:
        key = (row.get("class_name") or row.get("class_canonical") or "").strip() or "_"
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    per_class = max(4, limit // max(1, len(order)))
    for key in order:
        taken = 0
        for row in grouped[key]:
            for field in (
                "helm_sa_sailing_id",
                "crew_sa_sailing_id",
                "crew2_sa_sailing_id",
                "crew3_sa_sailing_id",
            ):
                sid = row.get(field)
                if sid is None:
                    continue
                sid = str(sid).strip()
                if sid.isdigit() and sid not in ids:
                    ids.append(sid)
                    taken += 1
                if len(ids) >= limit or taken >= per_class:
                    break
            if len(ids) >= limit or taken >= per_class:
                break
    return ids[:limit]


def media_pack(issue, slug, rows, facts):
    """Club/class sources + sailor Media-tab mentions for this event only."""
    pack = {"issue": issue}
    source_dir = ROOT / "issues" / issue / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    cached = source_dir / (slug + "-social.json")
    if cached.exists():
        try:
            pack.update(json.loads(cached.read_text()))
        except Exception:
            pass
    try:
        start = dt.date.fromisoformat(str(facts.get("start") or "")[:10])
        end = dt.date.fromisoformat(str(facts.get("end") or start.isoformat())[:10])
    except ValueError:
        return pack
    from sailor_mentions import collect_for_sailors

    ids = sailor_ids(rows)
    terms = event_terms(facts.get("title"), facts.get("class_name"), facts.get("club_name"), slug)
    mentions = collect_for_sailors(ids, start, end, terms)
    pack["sailor_mentions"] = mentions
    images = list(pack.get("images") or [])
    for item in mentions.get("matched") or []:
        url = item.get("image") or item.get("image_url") or item.get("thumbnail")
        if url:
            images.append(
                {
                    "image_url": url,
                    "source_url": item.get("url"),
                    "source_title": item.get("headline") or item.get("title") or facts.get("title"),
                    "platform": item.get("source") or "",
                }
            )
    pack["images"] = images
    (source_dir / (slug + "-media.json")).write_text(json.dumps(mentions, indent=2, ensure_ascii=False))
    return pack


def article_from_regatta(issue, slug, rows, layout="classic"):
    if not rows or skip_event_name(rows[0].get("event_name") or slug):return None
    facts=facts_from_rows(slug,rows)
    source_dir=ROOT/"issues"/issue/"sources"
    source_dir.mkdir(parents=True,exist_ok=True)
    (source_dir/(slug+"-results.json")).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    pack=media_pack(issue,slug,rows,facts)
    return rewrite_event(issue,facts,pack=pack,layout=layout)


def enrich_existing(issue: str, article: dict) -> dict:
    slug = article.get("id") or article.get("event_id")
    if not slug:
        return article
    try:
        rows = fetch_regatta(slug)
    except Exception:
        rows = []
    if article.get("review_status") == "edited":
        return article
    if rows:
        built = article_from_regatta(issue, slug, rows, layout=article.get("layout") or "classic")
        if built:
            return built
    return article


def weekend_feature(issue: str, monday: dt.date, events: list[dict], articles: list[dict]) -> dict:
    return rewrite_weekend_feature(issue, monday, events, articles)


def publish(
    monday: str | dt.date,
    rebuild: bool = False,
    enrich: bool = True,
    *,
    allow_incomplete: bool = False,
    notify_google: bool = False,
) -> dict:
    if isinstance(monday, str):
        monday = dt.date.fromisoformat(monday)
    if monday.weekday() != 0:
        raise ValueError("Issue date must be a Monday")
    issue = monday.isoformat()
    dest = ROOT / "issues" / issue / "issue.json"
    logs = []
    if dest.exists() and not rebuild:
        data = json.loads(dest.read_text())
        if enrich:
            data["articles"] = [enrich_existing(issue, a) for a in data.get("articles") or []]
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        from landing import write_public_index
        from roundup import render

        render(issue)
        write_public_index()
        ping = _maybe_notify(issue, notify_google)
        return {"issue": issue, "action": "enriched", "articles": len(data.get("articles") or []), "google": ping}
    table_events = weekend_events(monday)
    if not table_events:
        return {"issue": issue, "action": "skipped_empty_weekend"}
    slugs = sorted(set(e["regatta_id"] for e in table_events if e.get("regatta_id"))) or discover_slugs(monday)
    articles = []
    def build_event(pair):
        index,slug=pair
        try:
            rows=fetch_regatta(slug)
            if not rows:return None,{"event":slug,"status":"skipped_no_api_rows"}
            article=article_from_regatta(issue,slug,rows,layout=layout_for(index,"regatta_report"))
            if not article:return None,{"event":slug,"status":"skipped"}
            return article,{"event":slug,"status":"draft","rows":len(rows)}
        except Exception as exc:
            return None,{"event":slug,"status":"error","error":str(exc)[:180]}
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for article,log in pool.map(build_event,enumerate(slugs)):
            if article:articles.append(article)
            logs.append(log)
    failed = [x for x in logs if x["status"] in ("error", "skipped_no_api_rows")]
    if failed and not allow_incomplete:
        raise RuntimeError("Edition incomplete: " + json.dumps(failed))
    dest.parent.mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources").mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources" / "events-weekend.json").write_text(
        json.dumps({"monday": issue, "events": table_events}, indent=2, ensure_ascii=False)
    )
    feature = weekend_feature(issue, monday, table_events, articles)
    data = {
        "schema_version": "1.0",
        "issue_id": issue,
        "title": "South African Sailing — The Weekend Roundup",
        "edition_date": issue,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "draft",
        "articles": [feature] + articles,
    }
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    (dest.parent / "sources" / "build-log.json").write_text(json.dumps(logs, indent=2))
    from landing import write_public_index
    from roundup import render

    render(issue)
    write_public_index()
    ping = _maybe_notify(issue, notify_google)
    return {"issue": issue, "action": "created", "articles": len(articles), "events": logs, "google": ping}


def _maybe_notify(issue: str, notify_google: bool) -> dict | None:
    if not notify_google:
        return None
    try:
        from google_index import notify_issue

        return notify_issue(issue)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:180]}


def publish_due(today: dt.date | None = None, backfill: int = 4, rebuild: bool = False) -> list:
    results = []
    for monday in issue_mondays(today, backfill):
        results.append(publish(monday, rebuild=rebuild, enrich=True))
    return results


def publish_year(
    year: int,
    *,
    rebuild: bool = False,
    keep_existing: bool = True,
    notify_google: bool = False,
    events: list[dict] | None = None,
) -> list:
    """Build every weekend in `year` that had racing events.

    Uses the same REA rewrite + search/evidence path as Monday publish.
    Existing editorial issues are kept unless rebuild=True.
    Empty weekends are not created. Calendar-only events still produce an issue.
    """
    rows = events if events is not None else _fetch_events()
    results = []
    for monday in year_issue_mondays(year, rows):
        dest = ROOT / "issues" / monday.isoformat() / "issue.json"
        if dest.exists() and keep_existing and not rebuild:
            results.append({"issue": monday.isoformat(), "action": "kept_existing"})
            continue
        results.append(
            publish(
                monday,
                rebuild=rebuild,
                enrich=True,
                allow_incomplete=True,
                notify_google=notify_google,
            )
        )
    from landing import write_public_index

    write_public_index()
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--monday")
    p.add_argument("--year", type=int, help="Build every weekend in this year that had events (historical depth)")
    p.add_argument("--backfill", type=int, default=4)
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--due", action="store_true", help="Publish last Monday plus missing backfill weeks")
    p.add_argument("--test-weekend", action="store_true", help="Rebuild the 26–27 Sep 2026 reference weekend")
    p.add_argument("--notify-google", action="store_true", help="Ping Indexing API URL_UPDATED after each new issue")
    p.add_argument("--list-year", type=int, help="Print Mondays that would be built for a year and exit")
    args = p.parse_args()
    if args.list_year:
        mondays = year_issue_mondays(args.list_year)
        print(json.dumps({"year": args.list_year, "count": len(mondays), "mondays": [m.isoformat() for m in mondays]}, indent=2))
        return
    if args.test_weekend:
        print(json.dumps(publish("2026-09-28", rebuild=True, notify_google=args.notify_google), indent=2))
        return
    if args.year:
        print(json.dumps(publish_year(args.year, rebuild=args.rebuild, notify_google=args.notify_google), indent=2))
        return
    if args.due or not args.monday:
        print(json.dumps(publish_due(backfill=args.backfill, rebuild=args.rebuild), indent=2))
    else:
        print(json.dumps(publish(args.monday, rebuild=args.rebuild, notify_google=args.notify_google), indent=2))


if __name__ == "__main__":
    main()
