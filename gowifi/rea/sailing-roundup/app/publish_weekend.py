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

from ai_tools import load_env
from article_write import write_issue, write_week_feature
from event_rewrite import (
    facts_from_rows,
    rewrite_event,
)
from events_weekend import saturday_sunday, slugs_for_weekend, weekend_events
from gates import GateError, run_gates, write_gates
from parent_hero import store_roster_heroes
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


def html_slugs(monday: dt.date) -> list[str]:
    """Slugs published on /events and /yearly-events. Always scanned — never skipped because one calendar row already has a slug."""
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


def discover_slugs(monday: dt.date) -> list[str]:
    """Union of the events table and the public Events URL. One linked event must not hide another."""
    return sorted(set(slugs_for_weekend(monday)) | set(html_slugs(monday)))


def fetch_regatta(slug: str) -> list[dict]:
    data = fetch_json("https://sailingsa.co.za/api/regatta/" + slug)
    rows = data if isinstance(data, list) else []
    if not rows:
        return []
    from tsl_board import overlay_tsl_rows

    return overlay_tsl_rows(slug, rows, fetch_json=fetch_json)


def fetch_all_regattas(slugs: list[str]) -> tuple[dict[str, list], dict[str, str]]:
    """Fetch every event's result card before any article work. Gate 1 keys off this."""
    rows_by_slug: dict[str, list] = {}
    fetch_errors: dict[str, str] = {}

    def one(slug: str):
        try:
            return slug, fetch_regatta(slug), ""
        except Exception as exc:
            return slug, [], str(exc)[:180]

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for slug, rows, err in pool.map(one, slugs):
            rows_by_slug[slug] = rows
            if err:
                fetch_errors[slug] = err
    return rows_by_slug, fetch_errors


def _gate_context(monday: dt.date, slugs, rows_by_slug, table_events, fetch_errors=None, articles=None, root=None):
    root = root or ROOT
    issue = monday.isoformat()
    public = root / "public" / "issues" / issue
    landing = root / "public" / "index.html"
    return {
        "monday": issue,
        "slugs": list(slugs or []),
        "rows_by_slug": rows_by_slug or {},
        "table_events": table_events or [],
        "fetch_errors": fetch_errors or {},
        "articles": articles or [],
        "public_dir": str(public) if public.is_dir() else "",
        "landing_html": landing.read_text(encoding="utf-8", errors="replace") if landing.is_file() else "",
        "root": str(root),
    }


def require_gates(monday: dt.date, ctx: dict, through: int, root=None):
    """Run gates 1..through. Write gates.json. Raise before the next step on FAIL."""
    run = run_gates(ctx, through=through)
    write_gates(monday.isoformat(), run, root=root or ROOT)
    if not run.ok_through(through):
        raise GateError(run)
    return run


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


def article_from_regatta(issue, slug, rows, layout="classic"):
    if not rows or skip_event_name(rows[0].get("event_name") or slug):return None
    facts=facts_from_rows(slug,rows)
    source_dir=ROOT/"issues"/issue/"sources"
    source_dir.mkdir(parents=True,exist_ok=True)
    (source_dir/(slug+"-results.json")).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    pack={"issue":issue}
    cached=source_dir/(slug+"-social.json")
    if cached.exists():
        pack.update(json.loads(cached.read_text()))
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


def edition_headline(data: dict) -> str:
    """Name every event in the edition. Scored results lead; other events are not left out of the title."""
    feature = next((a for a in data.get("articles") or [] if a.get("type") == "feature"), {})
    def ident(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", re.sub(r"\b20\d{2}\b", "", str(name or "").lower()))
    names: list[str] = []
    seen: list[str] = []
    def add(name) -> None:
        name = re.sub(r"\s+", " ", str(name or "")).strip()
        key = ident(name)
        if not key:
            return
        for old in seen:
            if key == old or key in old or old in key:
                return
        seen.append(key)
        names.append(name)
    for card in feature.get("week_cards") or []:
        add((card or {}).get("name"))
    for article in data.get("articles") or []:
        if article.get("type") not in {"regatta_report", "brief"}:
            continue
        fact = article.get("week_fact") or {}
        add(fact.get("name") or article.get("event_title"))
    for name in feature.get("unlisted_events") or []:
        add(name)
    if not names:
        return feature.get("editorial_headline") or "South African sailing this week"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + " and " + names[-1]


def weekend_feature(issue: str, monday: dt.date, events: list[dict], articles: list[dict], polish=None) -> dict:
    reports = [a for a in (articles or []) if a.get("type") == "regatta_report"]
    return write_week_feature(issue, monday, events, reports, polish=polish)


def publish(monday: str | dt.date, rebuild: bool = False, enrich: bool = True, **inject) -> dict:
    """Build an issue only after sequential gates pass. Step 1 must PASS before articles exist."""
    if isinstance(monday, str):
        monday = dt.date.fromisoformat(monday)
    if monday.weekday() != 0:
        raise ValueError("Issue date must be a Monday")
    load_env(root=inject.get("root"))
    root = inject.get("root") or ROOT
    issue = monday.isoformat()
    dest = root / "issues" / issue / "issue.json"
    table_events = inject["table_events"] if "table_events" in inject else weekend_events(monday)
    slugs = inject["slugs"] if "slugs" in inject else discover_slugs(monday)
    if "rows_by_slug" in inject:
        rows_by_slug = dict(inject["rows_by_slug"] or {})
        fetch_errors = dict(inject.get("fetch_errors") or {})
    else:
        rows_by_slug, fetch_errors = fetch_all_regattas(slugs)

    dest.parent.mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources").mkdir(parents=True, exist_ok=True)
    (dest.parent / "sources" / "events-weekend.json").write_text(
        json.dumps({"monday": issue, "events": table_events, "slugs": slugs}, indent=2, ensure_ascii=False)
    )
    for slug, rows in rows_by_slug.items():
        (dest.parent / "sources" / f"{slug}-results.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False)
        )
    ctx = _gate_context(monday, slugs, rows_by_slug, table_events, fetch_errors, root=root)
    run = require_gates(monday, ctx, through=1, root=root)
    step1 = run.step(1)
    slugs = list((step1.events and [e["slug"] for e in step1.events if e.get("status") == "pass"]) or [])
    if not slugs:
        raise GateError(run)
    facts_by_slug = ctx.get("facts_by_slug") or {}
    hero_hooks = dict(inject.get("hero_hooks") or {})
    hero_hooks.setdefault("use_external", True)
    heroes = store_roster_heroes(issue, step1.events, facts_by_slug, root=root, **hero_hooks)
    ctx["heroes"] = heroes
    require_gates(monday, ctx, through=2, root=root)
    through = int(inject.get("through") or 6)
    polish = inject.get("polish")

    if dest.exists() and not rebuild:
        data = json.loads(dest.read_text())
        if enrich:
            data["articles"] = [enrich_existing(issue, a) for a in data.get("articles") or []]
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        ctx["articles"] = data.get("articles") or []
        require_gates(monday, ctx, through=3, root=root)
        if through < 4:
            return {
                "issue": issue,
                "action": "enriched",
                "articles": len([a for a in ctx["articles"] if a.get("type") == "regatta_report"]),
                "unlisted": data.get("unlisted_events") or [],
                "needs_external": data.get("needs_external") or [],
                "can_publish": False,
            }
        from landing import write_public_index
        from roundup import render

        render(issue)
        ctx = _gate_context(monday, slugs, rows_by_slug, table_events, fetch_errors, articles=ctx["articles"], root=root)
        require_gates(monday, ctx, through=6, root=root)
        write_public_index()
        return {"issue": issue, "action": "enriched", "articles": len(data.get("articles") or []), "can_publish": True}

    data = write_issue(
        issue,
        monday,
        step1.events,
        table_events,
        facts_by_slug,
        heroes,
        root=root,
        polish=polish,
    )
    from verified_context import attach_verified_context
    data = attach_verified_context(issue, data, table_events, locals().get("excluded") or [], root=root)
    feature = next((a for a in data.get("articles") or [] if a.get("type") == "feature"), None)
    if feature:
        feature["editorial_headline"] = edition_headline(data)
    data["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    reports = [a for a in data.get("articles") or [] if a.get("type") == "regatta_report"]
    logs = [
        {
            "event": a.get("event_id"),
            "status": "draft",
            "third_party": bool(a.get("third_party")),
            "needs_external": bool(a.get("needs_external")),
        }
        for a in reports
    ]
    (dest.parent / "sources" / "build-log.json").write_text(json.dumps(logs, indent=2))
    ctx["articles"] = data.get("articles") or []
    require_gates(monday, ctx, through=3, root=root)
    if through < 4:
        return {
            "issue": issue,
            "action": "drafted",
            "articles": len(reports),
            "events": logs,
            "unlisted": data.get("unlisted_events") or [],
            "needs_external": data.get("needs_external") or [],
            "can_publish": False,
        }
    from landing import write_public_index
    from roundup import render

    render(issue)
    ctx = _gate_context(monday, slugs, rows_by_slug, table_events, fetch_errors, articles=data["articles"], root=root)
    require_gates(monday, ctx, through=6, root=root)
    write_public_index()
    return {"issue": issue, "action": "created", "articles": len(reports), "events": logs, "can_publish": True}


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
    p.add_argument("--dry-run", action="store_true", help="Stop after story drafts. Never publish.")
    p.add_argument("--through", type=int, default=0, help="Stop after this gate (3 = story).")
    args = p.parse_args()
    if args.dry_run:
        from dry_run import run as dry_run

        print(json.dumps(dry_run(last_week=not args.monday, monday=args.monday), indent=2, ensure_ascii=False))
        return
    inject = {}
    if args.through:
        inject["through"] = args.through
    if args.test_weekend:
        print(json.dumps(publish("2026-09-28", rebuild=True, **inject), indent=2))
        return
    if args.due or not args.monday:
        print(json.dumps(publish_due(backfill=args.backfill, rebuild=args.rebuild), indent=2))
    else:
        print(json.dumps(publish(args.monday, rebuild=args.rebuild, **inject), indent=2))


if __name__ == "__main__":
    main()
