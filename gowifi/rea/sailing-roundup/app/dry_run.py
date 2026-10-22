#!/usr/bin/env python3
"""Dry-run Last Week's Roundup. Fetches live results, writes drafts, does not publish.

  python3 app/dry_run.py --last-week
  python3 app/dry_run.py --october 2026
  python3 app/dry_run.py --monday 2026-10-19
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from events_weekend import saturday_sunday, weekend_events
from gates import GateError, load_gates, load_roster
from publish_weekend import last_monday, publish

DRY_ROOT = ROOT / "dry-runs" / "work"


def october_mondays(year: int) -> list[dt.date]:
    day = dt.date(year, 10, 1)
    out = []
    while day.month == 10:
        if day.weekday() == 0:
            out.append(day)
        day += dt.timedelta(days=1)
    return out


def mondays_to_run(today: dt.date | None = None, last_week=False, october=None, monday=None) -> list[dt.date]:
    today = today or dt.date.today()
    chosen: list[dt.date] = []
    if monday:
        chosen.append(dt.date.fromisoformat(str(monday)[:10]))
    if last_week or (not monday and october is None):
        chosen.append(last_monday(today))
    if october:
        year = int(october)
        chosen.extend(d for d in october_mondays(year) if d <= today)
    seen = set()
    out = []
    for day in chosen:
        if day in seen:
            continue
        seen.add(day)
        out.append(day)
    out.sort()
    return out


def _calendar(root: pathlib.Path, issue: str) -> list[dict]:
    path = root / "issues" / issue / "sources" / "events-weekend.json"
    if not path.is_file():
        return []
    return [
        {
            "name": e.get("event_name"),
            "regatta_id": e.get("regatta_id"),
            "has_results": bool(e.get("has_results")),
            "start": e.get("start_date"),
            "end": e.get("end_date"),
        }
        for e in (json.loads(path.read_text()).get("events") or [])
    ]


def _paras(article: dict) -> list[str]:
    return [b.get("text") or "" for b in (article.get("blocks") or []) if b.get("type") == "paragraph"]


def _image(article: dict) -> dict | None:
    hero = article.get("hero_image") or {}
    if hero.get("url"):
        return hero
    block = next((b for b in (article.get("blocks") or []) if b.get("type") == "image"), None)
    return {"url": block.get("url"), "caption": block.get("caption"), "source_url": block.get("source_url")} if block else None


def summarize_issue(monday: dt.date, root: pathlib.Path) -> dict:
    issue = monday.isoformat()
    sat, sun = saturday_sunday(monday)
    gates = load_gates(issue, root=root) or {}
    roster = load_roster(issue, root=root) or {}
    issue_json = root / "issues" / issue / "issue.json"
    data = json.loads(issue_json.read_text()) if issue_json.is_file() else {}
    articles = list(data.get("articles") or [])
    feature = next((a for a in articles if a.get("type") == "feature"), None)
    reports = [a for a in articles if a.get("type") == "regatta_report"]
    steps = {s.get("name"): s for s in (gates.get("steps") or [])}
    return {
        "monday": issue,
        "weekend": [sat.isoformat(), sun.isoformat()],
        "label": "last_week" if monday == last_monday() else "october",
        "can_publish": bool(gates.get("can_publish")),
        "ok_through": max([s.get("step") or 0 for s in (gates.get("steps") or []) if s.get("status") == "pass"] or [0]),
        "gates": [
            {
                "step": s.get("step"),
                "name": s.get("name"),
                "status": s.get("status"),
                "errors": s.get("errors") or [],
            }
            for s in (gates.get("steps") or [])
        ],
        "calendar_events": _calendar(root, issue),
        "roster": [
            {
                "slug": e.get("slug"),
                "name": e.get("name") or (e.get("equals") or {}).get("name"),
                "status": e.get("status"),
                "entries": e.get("entries"),
                "winner": e.get("winner"),
                "url": e.get("url") or (e.get("equals") or {}).get("url"),
                "errors": e.get("errors") or [],
            }
            for e in (roster.get("events") or [])
        ],
        "unlisted": data.get("unlisted_events") or [],
        "feature": {
            "headline": (feature or {}).get("headline"),
            "deck": (feature or {}).get("deck"),
            "paragraphs": _paras(feature or {}),
        }
        if feature
        else None,
        "articles": [
            {
                "headline": a.get("headline"),
                "deck": a.get("deck"),
                "event_id": a.get("event_id"),
                "entries": a.get("entries"),
                "ai_writer": a.get("ai_writer"),
                "paragraphs": _paras(a),
                "image": _image(a),
            }
            for a in reports
        ],
        "needs_external": data.get("needs_external") or [],
        "errors": [err for s in (gates.get("steps") or []) for err in (s.get("errors") or []) if s.get("status") == "fail"],
        "step2": (steps.get("media") or {}).get("status"),
        "step3": (steps.get("story") or {}).get("status"),
    }


def markdown_report(report: dict) -> str:
    lines = ["# October / last-week roundup dry run", "", f"Live publish: **no**. Ran {report.get('ran_at')}.", ""]
    for week in report.get("weeks") or []:
        sat, sun = (week.get("weekend") or ["", ""])[:2]
        lines.append(f"## {week.get('monday')} ({sat}–{sun}) — {week.get('label')}")
        lines.append("")
        for step in week.get("gates") or []:
            errs = "; ".join(step.get("errors") or [])
            extra = f" — {errs}" if errs else ""
            lines.append(f"- Step {step.get('step')} {step.get('name')}: **{(step.get('status') or '').upper()}**{extra}")
        if not week.get("gates"):
            lines.append("- Gates: none written (run failed before step 1)")
        lines.append("")
        lines.append("### Calendar")
        for ev in week.get("calendar_events") or []:
            flag = "results" if ev.get("has_results") else "no results card"
            lines.append(f"- {ev.get('name')} ({ev.get('start')}–{ev.get('end')}) — {flag}")
        if not week.get("calendar_events"):
            lines.append("- none")
        lines.append("")
        lines.append("### Draft")
        feat = week.get("feature") or {}
        if feat.get("headline"):
            lines.append(f"**{feat.get('headline')}** — {feat.get('deck')}")
            for para in feat.get("paragraphs") or []:
                lines.append(f"> {para}")
        for art in week.get("articles") or []:
            lines.append(f"#### {art.get('headline')}")
            lines.append(f"{art.get('deck')}")
            img = art.get("image") or {}
            if img.get("url"):
                lines.append(f"Image: `{img.get('url')}` — {img.get('caption') or ''}")
            else:
                lines.append("Image: none")
            for para in art.get("paragraphs") or []:
                lines.append(f"> {para}")
        if week.get("unlisted"):
            lines.append("")
            lines.append("Unlisted (happened, no results card): " + ", ".join(week["unlisted"]))
        lines.append("")
    return "\n".join(lines) + "\n"


def draft_passed(monday: dt.date, root: pathlib.Path) -> None:
    """When the week gate fails, still draft the events that did pass so we can see copy and photos."""
    from article_write import write_issue
    from event_rewrite import facts_from_rows
    from parent_hero import store_roster_heroes

    issue = monday.isoformat()
    roster = load_roster(issue, root=root) or {}
    passed = [e for e in (roster.get("events") or []) if e.get("status") == "pass"]
    if not passed:
        return
    facts = {}
    for rec in passed:
        slug = rec.get("slug") or ""
        path = root / "issues" / issue / "sources" / f"{slug}-results.json"
        rows = json.loads(path.read_text()) if path.is_file() else []
        if rows:
            facts[slug] = facts_from_rows(slug, rows)
    if not facts:
        return
    heroes = store_roster_heroes(issue, passed, facts, root=root)
    table = []
    weekend_path = root / "issues" / issue / "sources" / "events-weekend.json"
    if weekend_path.is_file():
        table = json.loads(weekend_path.read_text()).get("events") or []
    write_issue(issue, monday, passed, table, facts, heroes, root=root, polish=lambda *a, **k: None)


def run_week(monday: dt.date, root: pathlib.Path) -> dict:
    try:
        publish(monday, rebuild=True, root=root, through=3, polish=lambda *a, **k: None)
    except GateError as exc:
        write = getattr(exc, "run", None)
        if write:
            from gates import write_gates

            write_gates(monday.isoformat(), write, root=root)
        try:
            draft_passed(monday, root)
        except Exception:
            pass
    except Exception as exc:
        return {
            "monday": monday.isoformat(),
            "weekend": [d.isoformat() for d in saturday_sunday(monday)],
            "label": "last_week" if monday == last_monday() else "october",
            "can_publish": False,
            "ok_through": 0,
            "gates": [],
            "errors": [str(exc)[:300]],
            "calendar_events": [],
            "roster": [],
            "articles": [],
            "feature": None,
            "unlisted": [],
        }
    return summarize_issue(monday, root)


def run(todays=None, last_week=False, october=None, monday=None, root=None) -> dict:
    today = todays or dt.date.today()
    root = pathlib.Path(root) if root else DRY_ROOT
    root.mkdir(parents=True, exist_ok=True)
    weeks = [run_week(day, root) for day in mondays_to_run(today, last_week=last_week, october=october, monday=monday)]
    report = {
        "ran_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "live_publish": False,
        "root": str(root),
        "weeks": weeks,
    }
    dest = root.parent
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (dest / "REPORT.md").write_text(markdown_report(report))
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dry-run weekend roundups. No live publish.")
    p.add_argument("--last-week", action="store_true", help="Issue Monday of last weekend")
    p.add_argument("--october", help="All October Mondays in this year that have already happened")
    p.add_argument("--monday", help="One issue Monday YYYY-MM-DD")
    p.add_argument("--root", help="Override dry-run work root")
    args = p.parse_args(argv)
    report = run(last_week=args.last_week, october=args.october, monday=args.monday, root=args.root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    failed = any((w.get("gates") or [{}]) and any(s.get("status") == "fail" for s in (w.get("gates") or [])) or w.get("errors") for w in report.get("weeks") or [])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
