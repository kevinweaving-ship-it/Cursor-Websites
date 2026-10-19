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
from events_weekend import saturday_sunday, slugs_for_weekend, weekend_events
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
    today = today or dt.date.today()
    return today - dt.timedelta(days=today.weekday())


def weekend_bounds(monday: dt.date) -> tuple[dt.date, dt.date]:
    return monday - dt.timedelta(days=4), monday - dt.timedelta(days=1)


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
    sat, sun = saturday_sunday(monday)
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
        if sat - dt.timedelta(days=2) <= day <= sun and not skip_event_name(slug):
            chosen.append(slug)
    return chosen


def fetch_regatta(slug: str) -> list[dict]:
    data = fetch_json("https://sailingsa.co.za/api/regatta/" + slug)
    return data if isinstance(data, list) else []


def sailor_ids(rows: list[dict], limit: int = 8) -> list[str]:
    ids = []
    for row in rows:
        for key in (
            "helm_sa_sailing_id",
            "crew_sa_sailing_id",
            "crew2_sa_sailing_id",
            "crew3_sa_sailing_id",
        ):
            sid = row.get(key)
            if sid is None:
                continue
            sid = str(sid).strip()
            if sid.isdigit() and sid not in ids:
                ids.append(sid)
        if len(ids) >= limit:
            break
    return ids[:limit]


def article_from_regatta(issue: str, slug: str, rows: list[dict], layout: str = "classic") -> dict | None:
    if not rows:
        return None
    first = rows[0]
    title = (first.get("event_name") or slug).strip()
    if skip_event_name(title):
        return None
    facts = facts_from_rows(slug, rows)
    club = facts["club"]
    klass = facts["class_name"]
    start = parse_day(first.get("start_date")) or dt.date.fromisoformat(slug[:10])
    end = parse_day(first.get("end_date")) or start
    url = facts["url"]
    from social_collect import collect as collect_social

    terms = event_terms(title, club, klass, slug)
    pack = collect_social(
        issue,
        {
            "id": slug,
            "title": title,
            "club": club,
            "club_name": facts["club_name"],
            "class_name": klass,
            "host_club_slug": facts.get("host_club_slug") or "",
            "class_canonical": first.get("class_canonical") or "",
            "event_url": url,
            "start": facts["start"],
            "end": facts["end"],
            "result_names": [r for r in (
                [row.get("helm_name") for row in rows[:8]] + [row.get("crew_name") for row in rows[:8]]
            ) if r],
        },
        sailor_ids(rows),
        terms,
        start,
        end,
        rows=rows,
    )
    article = rewrite_event(issue, facts, pack=pack, layout=layout)
    dest = ROOT / "issues" / issue / "sources"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{slug}-social.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False))
    return article


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


def publish(monday: str | dt.date, rebuild: bool = False, enrich: bool = True) -> dict:
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
        return {"issue": issue, "action": "enriched", "articles": len(data.get("articles") or [])}
    table_events = weekend_events(monday)
    slugs = [e["regatta_id"] for e in table_events if e.get("regatta_id")] or discover_slugs(monday)
    articles = []
    for slug in slugs:
        try:
            rows = fetch_regatta(slug)
            if not rows:
                logs.append({"event": slug, "status": "skipped_no_api_rows"})
                continue
            article = article_from_regatta(issue, slug, rows, layout=layout_for(len(articles), "regatta_report"))
            if not article:
                logs.append({"event": slug, "status": "skipped"})
                continue
            articles.append(article)
            logs.append({"event": slug, "status": "draft", "rows": len(rows)})
        except Exception as exc:
            logs.append({"event": slug, "status": "error", "error": str(exc)[:180]})
    dest.parent.mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources").mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources" / "events-weekend.json").write_text(
        json.dumps({"monday": issue, "events": table_events}, indent=2, ensure_ascii=False)
    )
    feature = weekend_feature(issue, monday, table_events, articles)
    data = {
        "schema_version": "1.0",
        "issue_id": issue,
        "title": "Weekend Sailing Roundup",
        "edition_date": issue,
        "status": "draft",
        "articles": [feature] + articles,
    }
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    (dest.parent / "sources" / "build-log.json").write_text(json.dumps(logs, indent=2))
    from landing import write_public_index
    from roundup import render

    render(issue)
    write_public_index()
    return {"issue": issue, "action": "created", "articles": len(articles), "events": logs}


def publish_due(today: dt.date | None = None, backfill: int = 4, rebuild: bool = False) -> list:
    results = []
    for monday in issue_mondays(today, backfill):
        results.append(publish(monday, rebuild=rebuild, enrich=True))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--monday")
    p.add_argument("--backfill", type=int, default=4)
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--due", action="store_true", help="Publish last Monday plus missing backfill weeks")
    p.add_argument("--test-weekend", action="store_true", help="Rebuild the 26–27 Sep 2026 reference weekend")
    args = p.parse_args()
    if args.test_weekend:
        print(json.dumps(publish("2026-09-28", rebuild=True), indent=2))
        return
    if args.due or not args.monday:
        print(json.dumps(publish_due(backfill=args.backfill, rebuild=args.rebuild), indent=2))
    else:
        print(json.dumps(publish(args.monday, rebuild=args.rebuild), indent=2))


if __name__ == "__main__":
    main()
