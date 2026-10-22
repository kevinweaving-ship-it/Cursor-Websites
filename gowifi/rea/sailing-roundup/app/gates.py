#!/usr/bin/env python3
"""Sequential publish gates. Later steps do not run until the previous step PASSes.

  1 weekend_roster — identify every event with a results URL in that week;
                     lay out name / date / host / url / leaderboard;
                     ALL must PASS, then save the confirmed roster.
                     That roster is the only list later steps may find externally.
  2 media          — inspect each parent event URL for its own images;
                     pick the best suited hero; store it on the box
  3 story          — write Last Week's Roundup from official equals + stored hero;
                     name every scored event and same-period events with no results card;
                     scored articles biggest-fleet first; official-only is a PASS
                     (needs_external is recorded for a later 3rd-party find)
  4 render         — gold HTML (edition-lead, h1, figures)
  5 cards          — homepage cards have real copy and a real photo
  6 publish        — replace live only if steps 1–5 all PASSed

Nothing is published unless every required gate is PASS. A FAIL or BLOCKED
step stops the pipeline; the next step is not done.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from event_rewrite import (
    class_leaderboards,
    entry_kind,
    facts_from_rows,
    is_chrome_image,
    is_scored_result_row,
    _is_roster,
)
from events_weekend import SKIP_NAME, overlaps, parse_day, saturday_sunday
from desk_editor import is_generic, week_fact_from_report, week_lead_errors
from evidence_pipeline import is_scoresheet, other_event_conflict, unlisted_event_names

SLUG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
STEPS = (
    (1, "weekend_roster"),
    (2, "media"),
    (3, "story"),
    (4, "render"),
    (5, "cards"),
    (6, "publish"),
)
HEADLINE_LIST = re.compile(r"^(?:[-*•]\s+\S+.*\n){2,}", re.M)
RESULTS_HOST = "https://sailingsa.co.za/regatta/"
ROSTER_FILE = "weekend-roster.json"


class GateError(RuntimeError):
    """Raised when a required gate fails or a later step is blocked."""

    def __init__(self, run: "GateRun"):
        self.run = run
        super().__init__(run.summary())


class GateResult:
    def __init__(self, step: int, name: str, status: str, checksum: str = "", errors=None, events=None):
        self.step = step
        self.name = name
        self.status = status
        self.checksum = checksum or ""
        self.errors = list(errors or [])
        self.events = list(events or [])

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "name": self.name,
            "status": self.status,
            "checksum": self.checksum,
            "errors": self.errors,
            "events": self.events,
        }


class GateRun:
    def __init__(self, monday: str, steps: list[GateResult]):
        self.monday = monday
        self.steps = list(steps)

    def step(self, number: int) -> GateResult | None:
        for item in self.steps:
            if item.step == number:
                return item
        return None

    def ok_through(self, number: int) -> bool:
        needed = {n for n, _ in STEPS if n <= number}
        return needed <= {s.step for s in self.steps if s.ok}

    @property
    def can_publish(self) -> bool:
        return self.ok_through(6)

    @property
    def checksum(self) -> str:
        first = self.step(1)
        return first.checksum if first else ""

    def summary(self) -> str:
        lines = [f"gates {self.monday} can_publish={str(self.can_publish).lower()}"]
        for item in self.steps:
            lines.append(f"  step {item.step} {item.name}: {item.status.upper()}")
            for err in item.errors:
                lines.append(f"    - {err}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "monday": self.monday,
            "can_publish": self.can_publish,
            "checksum": self.checksum,
            "steps": [s.to_dict() for s in self.steps],
        }


def results_url(slug: str) -> str:
    slug = (slug or "").strip()
    return RESULTS_HOST + slug if slug else ""


def equals_from_facts(facts: dict) -> dict:
    """The basic equals card from the parent results URL only.

    Leaderboard is every rank. Multiple classes/fleets each get their own board.
    Fleet racing keeps the fleet names.
    """
    boards = facts.get("class_leaderboards") or class_leaderboards(facts.get("ranked_rows") or [])
    slug = facts.get("slug") or ""
    return {
        "name": facts.get("title") or "",
        "start": facts.get("start") or "",
        "end": facts.get("end") or "",
        "host": (facts.get("club") or facts.get("club_name") or "").strip(),
        "url": facts.get("url") or results_url(slug),
        "source": "parent_overall_table",
        "fleets": [b.get("fleet") or b.get("class") or "" for b in boards],
        "leaderboards": boards,
        "leaderboard": boards[0]["rows"] if boards else [],
        "scoring_system": facts.get("scoring_system") or "",
        "scoring_kind": facts.get("scoring_kind") or "",
        "identity": facts.get("identity") or "",
        "team_racing": bool(facts.get("team_racing")),
    }


def event_checksum(facts: dict) -> str:
    """Stable checksum of the basic equals card. Later steps key off this."""
    raw = json.dumps(equals_from_facts(facts), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def find_externally_for(rec: dict) -> dict:
    """What step 2+ must look for once this event is confirmed on the roster."""
    equals = rec.get("equals") or {}
    return {
        "slug": rec.get("slug") or "",
        "url": rec.get("url") or equals.get("url") or "",
        "name": equals.get("name") or rec.get("name") or "",
        "host": equals.get("host") or rec.get("host") or "",
        "start": equals.get("start") or rec.get("start") or "",
        "end": equals.get("end") or rec.get("end") or "",
        "winner": rec.get("winner") or "",
        "checksum": rec.get("checksum") or "",
        "fleets": list(equals.get("fleets") or []),
        "need": ["photos", "news", "social"],
    }


def build_roster(monday, events: list[dict], checksum: str, confirmed: bool) -> dict:
    day = _monday_date(monday)
    sat, sun = saturday_sunday(day)
    passed = [e for e in events if e.get("status") == "pass"]
    failed = [e for e in events if e.get("status") != "pass"]
    return {
        "monday": day.isoformat(),
        "weekend": [sat.isoformat(), sun.isoformat()],
        "status": "pass" if confirmed else "fail",
        "confirmed": bool(confirmed),
        "checksum": checksum or "",
        "events": list(events),
        "passed_slugs": [e.get("slug") for e in passed],
        "failed_slugs": [e.get("slug") for e in failed],
        "find_externally": [e["find_externally"] for e in passed if e.get("find_externally")] if confirmed else [],
    }


def _blocked(step: int, name: str, prev: str) -> GateResult:
    return GateResult(step, name, "blocked", errors=[f"blocked until {prev} PASSes"])


def _monday_date(monday) -> dt.date:
    if isinstance(monday, dt.date):
        if monday.weekday() != 0:
            raise ValueError("Issue date must be a Monday")
        return monday
    day = dt.date.fromisoformat(str(monday)[:10])
    if day.weekday() != 0:
        raise ValueError("Issue date must be a Monday")
    return day


def _identity_word(kind: str) -> str:
    if kind == "team":
        return "team"
    if kind == "boat":
        return "boat"
    return "sailor"


def _check_parent_leaderboards(equals: dict) -> list[str]:
    """Every class/fleet from the parent URL must have ranks 1st–X.

    Scoring can be Appendix A, team racing, PY, timed, or keelboat.
    The named identity adapts: team, boat, helm/crew, or single helm.
    """
    errors: list[str] = []
    boards = list(equals.get("leaderboards") or [])
    fleets = [b.get("fleet") or b.get("class") or "" for b in boards]
    if len(boards) > 1 and any(not name.strip() for name in fleets):
        errors.append("fleet racing is missing fleet/class names")
    if not boards or not any(b.get("rows") for b in boards):
        errors.append("empty result leaderboard")
        return errors
    for board in boards:
        name = (board.get("fleet") or board.get("class") or "fleet").strip() or "fleet"
        rows = list(board.get("rows") or [])
        kind = board.get("identity") or equals.get("identity") or ""
        who = _identity_word(kind)
        if not rows:
            errors.append(f"{name}: empty class/fleet leaderboard")
            continue
        if not any((r.get("team") or r.get("boat") or r.get("helm") or r.get("crew")) for r in rows):
            errors.append(f"{name}: leaderboard rows have no {who} names")
        scored = [r for r in rows if is_scored_result_row(r)]
        if not scored:
            errors.append(
                f"{name}: overall results table is a {who} list — not a scored leaderboard"
            )
            continue
        firsts = [
            r
            for r in scored
            if str(r.get("pos") or "").strip().lower().split(".")[0] in {"1", "1st"}
        ]
        if not firsts:
            errors.append(f"{name}: no {who} in 1st place")
        elif len(scored) > 2 and len(firsts) == len(scored):
            errors.append(f"{name}: every entry is listed as 1st — leaderboard is not a result")
    return errors


def check_one_event(monday: dt.date, slug: str, rows: list[dict], fetch_error: str = "") -> dict:
    """Pass/fail one event's name, dates, host, results URL, and leaderboard."""
    sat, sun = saturday_sunday(monday)
    errors: list[str] = []
    record = {
        "slug": slug,
        "url": results_url(slug),
        "name": "",
        "start": "",
        "end": "",
        "host": "",
        "entries": 0,
        "races": 0,
        "winner": "",
        "equals": {},
        "checksum": "",
        "find_externally": None,
        "errors": errors,
        "status": "fail",
    }
    if not SLUG_RE.match(slug or ""):
        errors.append("invalid event slug")
    if not record["url"]:
        errors.append("missing results url")
    if not rows:
        errors.append("no result rows from /api/regatta" + (f" ({fetch_error})" if fetch_error else ""))
        return record

    raw_name = (rows[0].get("event_name") or "").strip()
    if not raw_name:
        errors.append("missing event name")
    elif SKIP_NAME.search(raw_name):
        errors.append("event name is a course/meeting, not a scored event")

    facts = facts_from_rows(slug, rows)
    record["name"] = facts.get("title") or ""
    record["start"] = facts.get("start") or ""
    record["end"] = facts.get("end") or ""
    record["host"] = (facts.get("club") or facts.get("club_name") or "").strip()
    record["entries"] = facts.get("entries") or 0
    record["races"] = facts.get("races") or 0
    record["winner"] = facts.get("winner") or ""
    record["url"] = facts.get("url") or results_url(slug)
    record["equals"] = equals_from_facts(facts)
    record["checksum"] = event_checksum(facts)
    if not record["url"]:
        errors.append("missing results url")

    if raw_name and (not record["name"] or record["name"] == slug):
        errors.append("event name collapsed to the slug — not a real title")

    start = parse_day(facts.get("start"))
    end = parse_day(facts.get("end"))
    if not start:
        errors.append("missing start date")
    if not end:
        errors.append("missing end date")
    if start and end and start > end:
        errors.append("start date is after end date")
    if start and end and not overlaps(start, end, sat, sun):
        errors.append(f"dates {start.isoformat()}/{end.isoformat()} do not overlap weekend {sat.isoformat()}/{sun.isoformat()}")

    host = (facts.get("club") or "").strip()
    host_name = (facts.get("club_name") or "").strip()
    if not host and (not host_name or host_name.lower() == "the host club"):
        errors.append("missing host club")

    kind = facts.get("identity") or entry_kind(rows[0], slug=slug, rows=rows)
    boards = (record.get("equals") or {}).get("leaderboards") or []
    scored_rows = [r for r in rows if is_scored_result_row(r)]
    scored_board = [r for b in boards for r in (b.get("rows") or []) if is_scored_result_row(r)]
    if not scored_rows and not scored_board:
        errors.append(
            f"parent overall results table is a {kind or 'entry'} list — not a scored leaderboard"
        )
    if not any(r.get("pos") for r in scored_board):
        errors.append("leaderboard has no ranked rows")
    if kind in ("team", "boat") and not any(
        (r.get("boat_name") or r.get("team_name") or r.get("club_abbrev") or "").strip() for r in rows
    ):
        errors.append(f"{kind} card has no {kind} names")
    errors.extend(_check_parent_leaderboards(record.get("equals") or {}))

    winner = (facts.get("winner") or "").strip()
    if not winner or winner == "The leader":
        errors.append("leaderboard has no winner name")
    elif kind in ("team", "boat") and _is_roster(winner):
        errors.append(f"{kind} winner is a sailor roster — ranks are {kind} names")

    if (facts.get("entries") or 0) < 1 and len(rows) < 1:
        errors.append("no entries on the result card")

    record["status"] = "pass" if not errors else "fail"
    if record["status"] == "pass":
        record["find_externally"] = find_externally_for(record)
    return record


def gate_event_facts(ctx: dict) -> GateResult:
    """Identify every scored event in the week. ALL basics must pass before step 2."""
    monday = _monday_date(ctx["monday"])
    slugs = list(ctx.get("slugs") or [])
    rows_by_slug = ctx.get("rows_by_slug") or {}
    table_events = ctx.get("table_events") or []
    fetch_errors = ctx.get("fetch_errors") or {}
    errors: list[str] = []
    events: list[dict] = []
    facts_by_slug: dict[str, dict] = {}

    if not slugs:
        errors.append("no events with results/url found for this week")

    seen: set[str] = set()
    for slug in slugs:
        if slug in seen:
            errors.append(f"{slug}: duplicate slug")
            continue
        seen.add(slug)
        rows = rows_by_slug.get(slug) or []
        rec = check_one_event(monday, slug, rows, fetch_error=fetch_errors.get(slug) or "")
        events.append(rec)
        if rows:
            facts_by_slug[slug] = facts_from_rows(slug, rows)
        errors.extend(f"{slug}: {err}" for err in rec["errors"])

    for item in table_events:
        rid = item.get("regatta_id")
        if rid and item.get("has_results") and rid not in seen:
            errors.append(f"{rid}: scored events-table row missing from discovered slugs")

    if events and any(e.get("status") != "pass" for e in events):
        failed = [e.get("slug") for e in events if e.get("status") != "pass"]
        errors.append("weekend roster incomplete — every scored event must pass before external find: " + ", ".join(failed))

    digest = hashlib.sha256(
        "".join(e.get("checksum") or "" for e in events).encode("utf-8")
    ).hexdigest()[:16]
    confirmed = bool(events) and not errors and all(e.get("status") == "pass" for e in events)
    roster = build_roster(monday, events, digest, confirmed)
    ctx["facts_by_slug"] = facts_by_slug
    ctx["roster"] = roster
    ctx["passed_slugs"] = roster["passed_slugs"]
    return GateResult(
        1,
        "weekend_roster",
        "pass" if confirmed else "fail",
        checksum=digest,
        errors=errors,
        events=events,
    )


def _reports(ctx: dict) -> list[dict]:
    return [a for a in (ctx.get("articles") or []) if a.get("type") == "regatta_report"]


def _passed_slugs(ctx: dict) -> list[str]:
    roster = ctx.get("roster") or {}
    return list(roster.get("passed_slugs") or ctx.get("passed_slugs") or [])


def _roster_coverage_errors(ctx: dict, reports: list[dict], step: str) -> list[str]:
    """Later steps may only cover the confirmed roster. That list is what to find externally."""
    roster = ctx.get("roster") or {}
    if roster and not roster.get("confirmed"):
        return ["weekend roster is not confirmed — cannot find externally"]
    passed = _passed_slugs(ctx)
    errors: list[str] = []
    report_ids = [a.get("event_id") or a.get("id") or "" for a in reports]
    for slug in passed:
        if slug not in report_ids:
            errors.append(f"{slug}: on confirmed roster but missing from {step}")
    for slug in report_ids:
        if passed and slug not in passed:
            errors.append(f"{slug}: not on confirmed weekend roster — cannot find externally")
    return errors


def _hero_file(ctx: dict, hero: dict) -> pathlib.Path | None:
    rel = hero.get("local_path") or ""
    if not rel:
        return None
    root = pathlib.Path(ctx["root"]) if ctx.get("root") else ROOT
    monday = str(ctx.get("monday") or "")
    for base in (
        root / "issues" / monday / rel,
        root / "public" / "issues" / monday / rel,
        pathlib.Path(ctx["public_dir"]) / rel if ctx.get("public_dir") else None,
    ):
        if base and base.is_file():
            return base
    return None


def gate_media(ctx: dict) -> GateResult:
    """Parent URL inspected, best hero stored on the box for every confirmed event."""
    roster = ctx.get("roster") or {}
    if roster and not roster.get("confirmed"):
        return GateResult(2, "media", "fail", errors=["weekend roster is not confirmed — cannot find externally"])
    passed = _passed_slugs(ctx)
    reports = _reports(ctx)
    errors: list[str] = _roster_coverage_errors(ctx, reports, "media") if reports else []
    if not passed:
        errors.append("no confirmed roster events to inspect for media")
        return GateResult(2, "media", "fail", errors=errors)
    heroes = dict(ctx.get("heroes") or {})
    if not heroes:
        from parent_hero import load_heroes

        heroes = load_heroes(str(ctx.get("monday") or ""), passed, root=pathlib.Path(ctx["root"]) if ctx.get("root") else ROOT)
    events: list[dict] = []
    hashes: set[str] = set()
    for slug in passed:
        hero = heroes.get(slug) or {}
        rec = {
            "slug": slug,
            "parent_has_media": bool(hero.get("parent_has_media")),
            "local_path": hero.get("local_path") or "",
            "errors": [],
        }
        inspected_empty = hero.get("status") == "empty" and hero.get("inspected")
        if inspected_empty:
            rec["empty"] = True
            events.append(rec)
            continue
        if hero.get("status") != "pass":
            rec["errors"].append(hero.get("error") or "no hero stored on box")
        path = _hero_file(ctx, hero)
        if not path:
            rec["errors"].append("hero file missing on box")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in hashes:
                rec["errors"].append("duplicate photograph")
            hashes.add(digest)
        src = hero.get("source_url") or hero.get("remote_url") or ""
        cap = hero.get("title") or ""
        if src and is_chrome_image(src, cap):
            rec["errors"].append("chrome/logo photograph")
        if src and is_scoresheet({"url": src, "title": cap, "caption": cap}):
            rec["errors"].append("scoresheet photograph")
        events.append(rec)
        errors.extend(f"{slug}: {err}" for err in rec["errors"])
    return GateResult(2, "media", "pass" if not errors else "fail", errors=errors, events=events)


def _report_entries(article: dict, facts: dict) -> int:
    for raw in (article.get("entries"), (facts or {}).get("entries")):
        try:
            if raw not in (None, ""):
                return int(raw)
        except (TypeError, ValueError):
            continue
    return 0


def gate_story(ctx: dict) -> GateResult:
    articles = list(ctx.get("articles") or [])
    reports = _reports(ctx)
    facts_by_slug = ctx.get("facts_by_slug") or {}
    errors: list[str] = _roster_coverage_errors(ctx, reports, "story")
    events: list[dict] = []
    if not reports:
        errors.append("no event articles to check for written copy")
        return GateResult(3, "story", "fail", errors=errors)
    feature = next((a for a in articles if a.get("type") == "feature"), None)
    if not feature:
        errors.append("missing Last Week's Roundup feature lead")
    else:
        paras = [b.get("text") or "" for b in (feature.get("blocks") or []) if b.get("type") == "paragraph"]
        blob = "\n".join(paras).strip()
        if "last week" not in (feature.get("headline") or "").lower():
            errors.append("feature lead is not titled Last Week's Roundup")
        if len(blob.split()) < 20:
            errors.append("feature lead is too short to be a written story")
        if HEADLINE_LIST.search(blob) and len(blob.split()) < 40:
            errors.append("feature lead is a headline list, not a story")
        if is_generic(blob):
            errors.append("feature lead is generic filler, not desk copy")
        cards = [a.get("week_fact") or week_fact_from_report(a) for a in reports]
        covered = {a.get("event_id") or a.get("id") or "" for a in reports}
        unlisted = unlisted_event_names(ctx.get("table_events") or [], covered)
        errors.extend("feature lead: " + err for err in week_lead_errors(blob, cards, unlisted))
        for rec in (ctx.get("roster") or {}).get("events") or []:
            if rec.get("status") != "pass":
                continue
            name = ((rec.get("equals") or {}).get("name") or rec.get("name") or "").strip()
            if name and name.lower() not in blob.lower():
                errors.append(f"feature lead does not name scored event {name}")
        for name in unlisted:
            if name.lower() not in blob.lower():
                errors.append(f"feature lead does not name {name} (happened, no results card)")
    vals = [_report_entries(a, facts_by_slug.get(a.get("event_id") or a.get("id") or "") or {}) for a in reports]
    if vals != sorted(vals, reverse=True):
        errors.append("scored event articles are not sorted by entries (biggest first)")
    for article in reports:
        slug = article.get("event_id") or article.get("id") or ""
        paras = [b.get("text") or "" for b in (article.get("blocks") or []) if b.get("type") == "paragraph"]
        blob = " ".join(paras)
        rec = {
            "slug": slug,
            "paragraphs": len(paras),
            "third_party": bool(article.get("third_party")),
            "needs_external": bool(article.get("needs_external", not article.get("third_party"))),
            "errors": [],
        }
        if not paras:
            rec["errors"].append("no written paragraphs")
        for text in paras:
            if re.search(r"\[\d+\]", text):
                rec["errors"].append("cite marks in public copy")
            if other_event_conflict(
                {"url": "", "title": "", "body": text},
                {"slug": slug, "title": article.get("headline") or slug},
                require_identity=False,
            ):
                rec["errors"].append("article quotes another event")
        facts = facts_by_slug.get(slug) or {}
        headline = article.get("headline") or ""
        if facts.get("team_racing") or facts.get("identity") == "team":
            if _is_roster(headline):
                rec["errors"].append("team racing headline is a sailor roster — winner is the team name")
            team = (facts.get("winner_team") or facts.get("winner") or "").strip()
            if team and team != "The leader" and team.lower() not in headline.lower():
                rec["errors"].append(f"team racing headline is not the team name {team!r}")
        helm = (facts.get("winner_helm") or facts.get("winner") or "").strip()
        token = helm.split()[0] if helm else ""
        if token and token != "The" and token.lower() not in blob.lower():
            rec["errors"].append(f"winner {helm!r} missing from story")
        if is_generic(blob):
            rec["errors"].append("generic filler — not desk copy")
        events.append(rec)
        errors.extend(f"{slug}: {err}" for err in rec["errors"])
    return GateResult(3, "story", "pass" if not errors else "fail", errors=errors, events=events)


def gate_render(ctx: dict) -> GateResult:
    public = pathlib.Path(ctx["public_dir"]) if ctx.get("public_dir") else None
    html_text = ctx.get("html") or ""
    if public:
        page = public / "index.html"
        if page.is_file():
            html_text = page.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    if not html_text.strip():
        return GateResult(4, "render", "fail", errors=["HTML not rendered — render step has not run"])
    if "edition-lead" not in html_text:
        errors.append("missing edition-lead")
    if not re.search(r"<h1\b", html_text, re.I):
        errors.append("missing h1")
    from roundup import public_html_banned

    errors.extend(public_html_banned(html_text))
    if "<figure" not in html_text and _reports(ctx):
        images = [
            b
            for a in _reports(ctx)
            for b in (a.get("blocks") or [])
            if b.get("type") == "image"
        ]
        if images:
            errors.append("photographs missing from rendered HTML")
    return GateResult(4, "render", "pass" if not errors else "fail", errors=errors)


def gate_cards(ctx: dict) -> GateResult:
    landing = ctx.get("landing_html") or ""
    lead = (ctx.get("feature_excerpt") or "").strip()
    articles = list(ctx.get("articles") or [])
    if not lead:
        feature = next((a for a in articles if a.get("type") == "feature"), None)
        if feature:
            lead = " ".join(
                b.get("text") or "" for b in (feature.get("blocks") or []) if b.get("type") == "paragraph"
            ).strip()
    errors: list[str] = []
    if len(lead.split()) < 12:
        errors.append("homepage card has no real copy")
    reports = _reports(ctx)
    if reports:
        has_photo = False
        for article in reports:
            hero = ((article.get("hero_image") or {}) or {}).get("url") or ""
            if hero and not is_chrome_image(hero, article.get("headline") or ""):
                has_photo = True
                break
            if any(b.get("type") == "image" for b in (article.get("blocks") or [])):
                has_photo = True
                break
        if not has_photo:
            errors.append("homepage card has no real photograph")
    if landing and "Last Week" not in landing and "roundup" not in landing.lower():
        errors.append("landing page does not name the roundup")
    return GateResult(5, "cards", "pass" if not errors else "fail", errors=errors)


def gate_publish(ctx: dict) -> GateResult:
    """Meta-gate: publish is allowed only after 1–5 PASSed."""
    prior = ctx.get("_prior_ok")
    if prior:
        return GateResult(6, "publish", "pass")
    return GateResult(6, "publish", "fail", errors=["publish blocked — earlier gates have not all PASSed"])


_GATE_FNS = {
    1: gate_event_facts,
    2: gate_media,
    3: gate_story,
    4: gate_render,
    5: gate_cards,
    6: gate_publish,
}


def run_gates(ctx: dict, through: int = 6) -> GateRun:
    """Run steps 1..through in order. A FAIL blocks every later step."""
    monday = str(ctx.get("monday") or "")
    if isinstance(ctx.get("monday"), dt.date):
        monday = ctx["monday"].isoformat()
    results: list[GateResult] = []
    blocked = False
    prior_name = "weekend_roster"
    for number, name in STEPS:
        if number > through:
            break
        if blocked:
            results.append(_blocked(number, name, prior_name))
            continue
        if number == 6:
            ctx["_prior_ok"] = all(s.ok for s in results)
        result = _GATE_FNS[number](ctx)
        results.append(result)
        if not result.ok:
            blocked = True
            prior_name = name
    if results and not results[-1].ok:
        present = {s.step for s in results}
        for number, name in STEPS:
            if number not in present:
                results.append(_blocked(number, name, prior_name))
    return GateRun(monday, results)


def write_roster(monday: str, roster: dict, root: pathlib.Path | None = None) -> pathlib.Path:
    root = root or ROOT
    path = root / "issues" / monday / "sources" / ROSTER_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(roster, indent=2, ensure_ascii=False) + "\n")
    return path


def load_roster(monday: str, root: pathlib.Path | None = None) -> dict | None:
    root = root or ROOT
    path = root / "issues" / monday / "sources" / ROSTER_FILE
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def write_gates(monday: str, run: GateRun, root: pathlib.Path | None = None) -> pathlib.Path:
    root = root or ROOT
    path = root / "issues" / monday / "sources" / "gates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False) + "\n")
    step1 = run.step(1)
    if step1:
        write_roster(monday, build_roster(monday, step1.events, step1.checksum, step1.ok), root=root)
    return path


def load_gates(monday: str, root: pathlib.Path | None = None) -> dict | None:
    root = root or ROOT
    path = root / "issues" / monday / "sources" / "gates.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def require_publishable(monday: str, root: pathlib.Path | None = None) -> dict:
    data = load_gates(monday, root=root)
    if not data:
        raise ValueError("Missing gates.json — publish blocked")
    if not data.get("can_publish"):
        raise ValueError("Publish blocked: gates did not all pass")
    return data


def _load_local_rows(monday: str, slugs: list[str], root: pathlib.Path) -> dict[str, list]:
    out: dict[str, list] = {}
    source = root / "issues" / monday / "sources"
    for slug in slugs:
        path = source / f"{slug}-results.json"
        if path.is_file():
            data = json.loads(path.read_text())
            out[slug] = data if isinstance(data, list) else []
    return out


def _context_from_disk(monday: str, root: pathlib.Path, slugs=None, rows_by_slug=None, table_events=None) -> dict:
    issue_dir = root / "issues" / monday
    public_dir = root / "public" / "issues" / monday
    articles = []
    issue_json = issue_dir / "issue.json"
    if issue_json.is_file():
        articles = (json.loads(issue_json.read_text()).get("articles") or [])
    weekend = {}
    weekend_path = issue_dir / "sources" / "events-weekend.json"
    if weekend_path.is_file():
        weekend = json.loads(weekend_path.read_text())
    slugs = list(slugs or weekend.get("slugs") or [])
    table_events = list(table_events if table_events is not None else weekend.get("events") or [])
    rows_by_slug = dict(rows_by_slug or {})
    rows_by_slug.update({k: v for k, v in _load_local_rows(monday, slugs, root).items() if k not in rows_by_slug})
    landing = ""
    landing_path = root / "public" / "index.html"
    if landing_path.is_file():
        landing = landing_path.read_text(encoding="utf-8", errors="replace")
    roster = load_roster(monday, root=root)
    from parent_hero import load_heroes

    passed = list((roster or {}).get("passed_slugs") or [])
    return {
        "monday": monday,
        "root": str(root),
        "slugs": slugs,
        "rows_by_slug": rows_by_slug,
        "table_events": table_events,
        "articles": articles,
        "public_dir": str(public_dir) if public_dir.is_dir() else "",
        "landing_html": landing,
        "roster": roster or {},
        "passed_slugs": passed,
        "heroes": load_heroes(monday, passed, root=root),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run sequential publish gates. Step 1 must PASS before later steps run.")
    p.add_argument("--monday", required=True, help="Issue Monday YYYY-MM-DD")
    p.add_argument("--step", type=int, default=6, help="Run only through this step (default 6 = all)")
    p.add_argument("--root", help="Override repo root (tests)")
    args = p.parse_args(argv)
    root = pathlib.Path(args.root) if args.root else ROOT
    ctx = _context_from_disk(args.monday, root)
    if not ctx["slugs"] or not ctx["rows_by_slug"]:
        try:
            from events_weekend import slugs_for_weekend, weekend_events
            from publish_weekend import discover_slugs, fetch_regatta

            monday = dt.date.fromisoformat(args.monday)
            if not ctx["table_events"]:
                ctx["table_events"] = weekend_events(monday)
            if not ctx["slugs"]:
                ctx["slugs"] = discover_slugs(monday) or slugs_for_weekend(monday)
            missing = [s for s in ctx["slugs"] if s not in ctx["rows_by_slug"]]
            for slug in missing:
                try:
                    ctx["rows_by_slug"][slug] = fetch_regatta(slug)
                except Exception as exc:
                    ctx.setdefault("fetch_errors", {})[slug] = str(exc)[:180]
                    ctx["rows_by_slug"][slug] = []
        except Exception as exc:
            if not ctx["slugs"]:
                print(json.dumps({"monday": args.monday, "can_publish": False, "error": str(exc)[:200]}))
                return 1
    run = run_gates(ctx, through=max(1, min(args.step, 6)))
    write_gates(args.monday, run, root=root)
    print(json.dumps(run.to_dict(), indent=2))
    return 0 if (run.ok_through(args.step) if args.step < 6 else run.can_publish) else 1


if __name__ == "__main__":
    sys.exit(main())
