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
    thu, sun = weekend_bounds(monday)
    slugs: set[str] = set()
    for url in EVENTS_PAGES:
        try:
            slugs |= scrape_slugs(fetch_text(url))
        except Exception:
            continue
    chosen = set()
    for slug in slugs:
        try:
            day = dt.date.fromisoformat(slug[:10])
        except ValueError:
            continue
        if thu - dt.timedelta(days=2) <= day <= sun:
            chosen.add(slug)
    try:
        events = fetch_json("https://sailingsa.co.za/api/events")
    except Exception:
        events = []
    for ev in events if isinstance(events, list) else []:
        name = ev.get("event_name") or ""
        if skip_event_name(name):
            continue
        start = parse_day(ev.get("start_date"))
        end = parse_day(ev.get("end_date")) or start
        if not start or start > sun or end < thu:
            continue
        rid = str(ev.get("regatta_id") or "").strip()
        if re.match(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+$", rid):
            chosen.add(rid)
    return sorted(s for s in chosen if not skip_event_name(s))


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


def results_table(rows: list[dict]) -> tuple[list[str], list[list[str]]]:
    ranked = [r for r in rows if r.get("rank") not in (None, "")]
    ranked.sort(key=lambda r: int(r["rank"]) if str(r.get("rank")).isdigit() else 999)
    use = ranked or rows
    cols = ["Rank", "Class", "Sail No", "Club", "Helm", "Crew", "Nett"]
    table = []
    for row in use[:80]:
        table.append(
            [
                "" if row.get("rank") in (None, "") else str(row.get("rank")),
                str(row.get("class_name") or row.get("class_canonical") or ""),
                str(row.get("sail_number") or ""),
                str(row.get("club_abbrev") or row.get("club_raw") or ""),
                str(row.get("helm_name") or ""),
                str(row.get("crew_name") or ""),
                "" if row.get("nett_points_raw") in (None, "") else str(row.get("nett_points_raw")),
            ]
        )
    return cols, table


def lead_sentence(title: str, rows: list[dict]) -> str:
    ranked = [r for r in rows if r.get("rank") not in (None, "")]
    ranked.sort(key=lambda r: int(r["rank"]) if str(r.get("rank")).isdigit() else 999)
    if not ranked:
        return f"Published entries are listed for {title}."
    top = ranked[0]
    names = [n for n in (top.get("helm_name"), top.get("crew_name")) if n]
    who = " and ".join(names) if names else "The leader"
    nett = top.get("nett_points_raw")
    if nett not in (None, ""):
        return f"{who} leads the published {title} standings on {nett} nett points."
    return f"{who} tops the published {title} standings."


def attach_media(article: dict, pack: dict):
    sources = list(article.get("sources") or [])
    social = list(article.get("social_sources") or [])
    for post in pack.get("posts") or []:
        url = post.get("url")
        if url and url not in sources:
            sources.append(url)
        if post and not any(x.get("url") == url for x in social):
            social.append(post)
        desc = (post.get("description") or post.get("title") or "").strip()
        if desc and not any(b.get("source_url") == url for b in article["blocks"]):
            article["blocks"].insert(
                0,
                {
                    "type": "paragraph",
                    "text": "From a public social update: " + desc[:400],
                    "source_url": url,
                },
            )
        if post.get("image") and not any(
            b.get("type") == "image" and b.get("source_url") == url for b in article["blocks"]
        ):
            article["blocks"].append(
                {
                    "type": "image",
                    "url": post["image"],
                    "alt": post.get("title") or "",
                    "caption": post.get("title") or "",
                    "credit": post.get("platform") or "",
                    "source_url": url,
                    "rights_status": "external_link_only",
                }
            )
    for mention in pack.get("sailor_mentions", {}).get("matched") or []:
        url = mention.get("url")
        if url and url not in sources:
            sources.append(url)
    article["sources"] = sources
    article["social_sources"] = social
    if not article.get("hero_image"):
        for block in article["blocks"]:
            if block.get("type") == "image" and block.get("url"):
                article["hero_image"] = {
                    "url": block["url"],
                    "source_url": block.get("source_url"),
                    "rights_status": block.get("rights_status"),
                }
                break


def article_from_regatta(issue: str, slug: str, rows: list[dict]) -> dict | None:
    if not rows:
        return None
    first = rows[0]
    title = (first.get("event_name") or slug).strip()
    if skip_event_name(title):
        return None
    club = first.get("host_club_code") or first.get("host_club_name") or ""
    klass = first.get("class_name") or first.get("class_canonical") or ""
    start = parse_day(first.get("start_date")) or dt.date.fromisoformat(slug[:10])
    end = parse_day(first.get("end_date")) or start
    cols, table = results_table(rows)
    lead = lead_sentence(title, rows)
    url = "https://sailingsa.co.za/regatta/" + slug
    article = {
        "id": slug,
        "type": "regatta_report",
        "headline": title,
        "deck": lead,
        "byline": "Weekend Sailing Roundup",
        "published_at": issue,
        "event_id": slug,
        "hero_image": None,
        "blocks": [
            {"type": "paragraph", "text": lead},
            {
                "type": "results",
                "source_event_url": url,
                "columns": cols,
                "rows": table,
                "as_of": issue,
            },
        ],
        "sources": [url],
        "review_status": "draft",
        "club": club,
        "class_name": klass,
        "host_club_slug": first.get("host_club_slug") or "",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    from social_collect import collect as collect_social

    terms = event_terms(title, club, klass, slug)
    pack = collect_social(
        issue,
        {
            "id": slug,
            "title": title,
            "club": club,
            "class_name": klass,
            "host_club_slug": first.get("host_club_slug") or "",
            "class_canonical": first.get("class_canonical") or "",
        },
        sailor_ids(rows),
        terms,
        start,
        end,
    )
    attach_media(article, pack)
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
    if rows:
        built = article_from_regatta(issue, slug, rows)
        if built:
            # Keep previously edited copy if it already has extra sources; merge social.
            existing_sources = article.get("sources") or []
            built["sources"] = list(dict.fromkeys(existing_sources + (built.get("sources") or [])))
            if article.get("blocks"):
                seen = {(b.get("type"), b.get("source_url"), b.get("text")) for b in built["blocks"]}
                for block in article["blocks"]:
                    key = (block.get("type"), block.get("source_url"), block.get("text"))
                    if key not in seen:
                        built["blocks"].append(block)
            return built
    return article


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
    slugs = discover_slugs(monday)
    articles = []
    for slug in slugs:
        try:
            rows = fetch_regatta(slug)
            if not rows:
                logs.append({"event": slug, "status": "skipped_no_api_rows"})
                continue
            article = article_from_regatta(issue, slug, rows)
            if not article:
                logs.append({"event": slug, "status": "skipped"})
                continue
            articles.append(article)
            logs.append({"event": slug, "status": "draft", "rows": len(rows)})
        except Exception as exc:
            logs.append({"event": slug, "status": "error", "error": str(exc)[:180]})
    dest.parent.mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources").mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "issue_id": issue,
        "title": "Weekend Sailing Roundup",
        "edition_date": issue,
        "status": "draft",
        "articles": articles,
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
    args = p.parse_args()
    if args.due or not args.monday:
        print(json.dumps(publish_due(backfill=args.backfill, rebuild=args.rebuild), indent=2))
    else:
        print(json.dumps(publish(args.monday, rebuild=args.rebuild), indent=2))


if __name__ == "__main__":
    main()
