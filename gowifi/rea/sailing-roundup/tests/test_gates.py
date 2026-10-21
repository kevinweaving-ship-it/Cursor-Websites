#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from event_rewrite import facts_from_rows
from gates import (
    GateError,
    check_one_event,
    event_checksum,
    load_roster,
    require_publishable,
    run_gates,
    write_gates,
)
from publish_weekend import publish, require_gates

MONDAY = dt.date(2026, 9, 28)
SLUG = "2026-09-25-tsc-420-nationals"


def sample_rows(**overrides):
    row = {
        "event_name": "420 Nationals",
        "host_club_code": "TSC",
        "host_club_name": "Theewater Sports Club",
        "host_club_slug": "tsc",
        "class_name": "420",
        "start_date": "2026-09-26",
        "end_date": "2026-09-27",
        "result_status": "Final",
        "races_sailed": 8,
        "entries_total": 16,
        "rank": 1,
        "helm_name": "Dale Rae",
        "crew_name": "James Rae",
        "club_abbrev": "HYC",
        "sail_number": "53001",
        "nett_points_raw": 10,
    }
    row.update(overrides)
    return [
        row,
        {
            "event_name": row["event_name"],
            "host_club_code": row.get("host_club_code") or "",
            "rank": 2,
            "helm_name": "Howard Leoto",
            "crew_name": "Lebogang January",
            "club_abbrev": "RNYC",
            "sail_number": "5309",
            "nett_points_raw": 20,
        },
        {
            "event_name": row["event_name"],
            "host_club_code": row.get("host_club_code") or "",
            "rank": 3,
            "helm_name": "Kamva Mgcubhe",
            "crew_name": "Maddison Smit",
            "club_abbrev": "MAC",
            "sail_number": "54809",
            "nett_points_raw": 27,
        },
    ]


def facts_ctx(rows=None, slugs=None, **extra):
    rows = rows if rows is not None else sample_rows()
    slugs = slugs if slugs is not None else [SLUG]
    ctx = {
        "monday": MONDAY.isoformat(),
        "slugs": slugs,
        "rows_by_slug": {SLUG: rows} if slugs == [SLUG] else extra.pop("rows_by_slug", {SLUG: rows}),
        "table_events": [
            {
                "event_name": "420 Nationals",
                "regatta_id": SLUG,
                "has_results": True,
                "start_date": "2026-09-26",
                "end_date": "2026-09-27",
            }
        ],
        "articles": [],
    }
    ctx.update(extra)
    return ctx


def passing_article(slug=SLUG):
    return {
        "id": slug,
        "event_id": slug,
        "type": "regatta_report",
        "headline": "Dale Rae and James Rae win 420 Nationals",
        "hero_image": {"url": "media/420.jpg"},
        "citations": [{"n": 1, "url": "https://sailingsa.co.za/regatta/" + slug}],
        "blocks": [
            {
                "type": "paragraph",
                "text": "Dale Rae and James Rae won the 420 Nationals at Theewater Sports Club on 10 nett points [1].",
            },
            {
                "type": "image",
                "url": "media/420.jpg",
                "source_url": "https://sailingsa.co.za/regatta/" + slug,
                "caption": "Prizegiving at 420 Nationals",
            },
            {"type": "results", "rows": [["1", "Dale Rae", "James Rae"]]},
        ],
    }


def passing_feature():
    return {
        "id": "weekend-feature",
        "type": "feature",
        "headline": "Last Week's Roundup",
        "blocks": [
            {
                "type": "paragraph",
                "text": (
                    "Two national championships closed the weekend at Theewater and Henley Midmar, "
                    "with Dale Rae defending the 420 title and the Dart 18 fleet finishing Sunday."
                ),
            }
        ],
    }


class EventFactsGate(unittest.TestCase):
    def test_good_card_passes_step1(self):
        rec = check_one_event(MONDAY, SLUG, sample_rows())
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["name"], "420 Nationals")
        self.assertEqual(rec["host"], "TSC")
        self.assertEqual(rec["start"], "2026-09-26")
        self.assertEqual(rec["winner"], "Dale Rae and James Rae")
        self.assertEqual(rec["url"], "https://sailingsa.co.za/regatta/" + SLUG)
        self.assertEqual(rec["equals"]["name"], "420 Nationals")
        self.assertEqual(rec["equals"]["host"], "TSC")
        self.assertEqual(rec["equals"]["url"], rec["url"])
        self.assertEqual(rec["equals"]["leaderboard"][0]["helm"], "Dale Rae")
        self.assertTrue(rec["checksum"])
        self.assertEqual(rec["find_externally"]["need"], ["photos", "news", "social"])

    def test_checksum_stable_and_changes_with_winner(self):
        a = event_checksum(facts_from_rows(SLUG, sample_rows()))
        b = event_checksum(facts_from_rows(SLUG, sample_rows()))
        self.assertEqual(a, b)
        other = sample_rows()
        other[0]["helm_name"] = "Someone Else"
        c = event_checksum(facts_from_rows(SLUG, other))
        self.assertNotEqual(a, c)

    def test_missing_name_fails(self):
        rec = check_one_event(MONDAY, SLUG, sample_rows(event_name=""))
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("missing event name" in e for e in rec["errors"]))

    def test_missing_host_fails(self):
        rec = check_one_event(MONDAY, SLUG, sample_rows(host_club_code="", host_club_name=""))
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("missing host club" in e for e in rec["errors"]))

    def test_dates_must_overlap_weekend(self):
        rec = check_one_event(
            MONDAY, SLUG, sample_rows(start_date="2026-08-01", end_date="2026-08-02")
        )
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("do not overlap weekend" in e for e in rec["errors"]))

    def test_no_rows_fails(self):
        rec = check_one_event(MONDAY, SLUG, [])
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("no result rows" in e for e in rec["errors"]))

    def test_no_first_place_fails(self):
        rows = sample_rows()
        for row in rows:
            row["rank"] = int(row["rank"]) + 4
        rec = check_one_event(MONDAY, SLUG, rows)
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("1st place" in e or "first rank" in e for e in rec["errors"]))

    def test_everyone_listed_first_fails(self):
        rows = sample_rows()
        for row in rows:
            row["rank"] = 1
        rec = check_one_event(MONDAY, SLUG, rows)
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("every entry is listed as 1st" in e for e in rec["errors"]))

    def test_no_winner_name_fails(self):
        rows = sample_rows(helm_name="", crew_name="")
        rec = check_one_event(MONDAY, SLUG, rows)
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("no winner name" in e for e in rec["errors"]))

    def test_course_name_fails(self):
        rec = check_one_event(MONDAY, "2026-09-26-ityc-instructor-course", sample_rows(event_name="Instructor Course"))
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("course/meeting" in e for e in rec["errors"]))


class SequentialGates(unittest.TestCase):
    def test_step1_fail_blocks_every_later_step(self):
        run = run_gates(facts_ctx(rows=[]), through=6)
        self.assertEqual(run.step(1).status, "fail")
        for number in (2, 3, 4, 5, 6):
            self.assertEqual(run.step(number).status, "blocked", number)
        self.assertFalse(run.can_publish)
        self.assertFalse(run.ok_through(1))

    def test_empty_weekend_fails_step1(self):
        run = run_gates(facts_ctx(rows=[], slugs=[], rows_by_slug={}, table_events=[]), through=1)
        self.assertEqual(run.step(1).status, "fail")
        self.assertTrue(any("no events with results/url" in e for e in run.step(1).errors))

    def test_step1_pass_allows_step2_which_fails_without_photos(self):
        run = run_gates(facts_ctx(), through=6)
        self.assertEqual(run.step(1).status, "pass")
        self.assertEqual(run.step(2).status, "fail")
        self.assertEqual(run.step(3).status, "blocked")
        self.assertFalse(run.can_publish)
        self.assertTrue(run.ok_through(1))
        self.assertFalse(run.ok_through(2))

    def test_all_steps_pass_unlocks_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            public = pathlib.Path(temp) / "public"
            public.mkdir()
            html = (
                '<article class="edition-lead"><h1>Last Week\'s Roundup</h1>'
                "<figure><img src='media/420.jpg'></figure></article>"
            )
            (public / "index.html").write_text(html)
            photo = public / "media"
            photo.mkdir()
            (photo / "420.jpg").write_bytes(b"real-photo")
            ctx = facts_ctx(
                articles=[passing_feature(), passing_article()],
                public_dir=str(public),
                landing_html=html,
                feature_excerpt="Two national championships closed the weekend with a written story, not a headline list.",
            )
            run = run_gates(ctx, through=6)
            self.assertEqual([s.status for s in run.steps], ["pass"] * 6, run.summary())
            self.assertTrue(run.can_publish)

    def test_through_1_does_not_claim_publish(self):
        run = run_gates(facts_ctx(), through=1)
        self.assertTrue(run.ok_through(1))
        self.assertFalse(run.can_publish)
        self.assertIsNone(run.step(2))

    def test_write_and_require_publishable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            run = run_gates(facts_ctx(rows=[]), through=6)
            path = write_gates(MONDAY.isoformat(), run, root=root)
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text())
            self.assertFalse(data["can_publish"])
            roster = load_roster(MONDAY.isoformat(), root=root)
            self.assertFalse(roster["confirmed"])
            self.assertEqual(roster["find_externally"], [])
            with self.assertRaisesRegex(ValueError, "gates did not all pass"):
                require_publishable(MONDAY.isoformat(), root=root)
            with self.assertRaisesRegex(ValueError, "Missing gates.json"):
                require_publishable("2026-10-05", root=root)

    def test_all_scored_events_must_pass_before_external_find(self):
        dart = "2026-09-24-hmyc-dart-18-nationals"
        dart_rows = sample_rows(
            event_name="Dart 18 Nationals",
            host_club_code="HMYC",
            host_club_name="Henley Midmar Yacht Club",
            start_date="2026-09-24",
            end_date="2026-09-27",
        )
        ctx = facts_ctx(
            slugs=[SLUG, dart],
            rows_by_slug={SLUG: sample_rows(), dart: sample_rows(host_club_code="", host_club_name="")},
            table_events=[
                {"event_name": "420 Nationals", "regatta_id": SLUG, "has_results": True},
                {"event_name": "Dart 18 Nationals", "regatta_id": dart, "has_results": True},
            ],
        )
        run = run_gates(ctx, through=6)
        self.assertEqual(run.step(1).status, "fail")
        self.assertEqual(run.step(2).status, "blocked")
        self.assertIn(dart, run.step(1).errors[-1] if run.step(1).errors else "")
        self.assertEqual(ctx["roster"]["passed_slugs"], [SLUG])
        self.assertEqual(ctx["roster"]["failed_slugs"], [dart])
        self.assertFalse(ctx["roster"]["confirmed"])
        self.assertEqual(ctx["roster"]["find_externally"], [])

    def test_confirmed_roster_is_what_must_be_found_externally(self):
        dart = "2026-09-24-hmyc-dart-18-nationals"
        dart_rows = sample_rows(
            event_name="Dart 18 Nationals",
            host_club_code="HMYC",
            host_club_name="Henley Midmar Yacht Club",
            start_date="2026-09-24",
            end_date="2026-09-27",
        )
        ctx = facts_ctx(
            slugs=[SLUG, dart],
            rows_by_slug={SLUG: sample_rows(), dart: dart_rows},
            table_events=[
                {"event_name": "420 Nationals", "regatta_id": SLUG, "has_results": True},
                {"event_name": "Dart 18 Nationals", "regatta_id": dart, "has_results": True},
            ],
        )
        run = run_gates(ctx, through=1)
        self.assertEqual(run.step(1).status, "pass", run.summary())
        self.assertTrue(ctx["roster"]["confirmed"])
        self.assertEqual(ctx["roster"]["passed_slugs"], [SLUG, dart])
        needs = {item["slug"]: item["need"] for item in ctx["roster"]["find_externally"]}
        self.assertEqual(set(needs), {SLUG, dart})
        self.assertEqual(needs[SLUG], ["photos", "news", "social"])
        self.assertEqual(ctx["roster"]["events"][0]["equals"]["url"], "https://sailingsa.co.za/regatta/" + SLUG)

    def test_media_cannot_cover_an_event_off_the_roster(self):
        ctx = facts_ctx(articles=[passing_feature(), passing_article(), passing_article("2026-10-10-hmyc-dam-bottle-sprints")])
        run = run_gates(ctx, through=6)
        self.assertEqual(run.step(1).status, "pass")
        self.assertEqual(run.step(2).status, "fail")
        self.assertTrue(any("not on confirmed weekend roster" in e for e in run.step(2).errors))
        self.assertEqual(run.step(3).status, "blocked")


class PublishStopsOnStep1(unittest.TestCase):
    def test_publish_does_not_write_articles_when_step1_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            with self.assertRaises(GateError) as ctx:
                publish(
                    MONDAY,
                    rebuild=True,
                    root=root,
                    slugs=[SLUG],
                    table_events=[],
                    rows_by_slug={SLUG: []},
                )
            self.assertEqual(ctx.exception.run.step(1).status, "fail")
            self.assertFalse((root / "issues" / MONDAY.isoformat() / "issue.json").exists())
            gates = json.loads((root / "issues" / MONDAY.isoformat() / "sources" / "gates.json").read_text())
            self.assertEqual(gates["steps"][0]["status"], "fail")
            self.assertFalse(gates["can_publish"])
            self.assertEqual(gates["steps"][1]["status"], "blocked")
            roster = load_roster(MONDAY.isoformat(), root=root)
            self.assertFalse(roster["confirmed"])
            self.assertEqual(roster["find_externally"], [])
            self.assertTrue((root / "issues" / MONDAY.isoformat() / "sources" / f"{SLUG}-results.json").is_file())

    def test_require_gates_writes_then_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            ctx = facts_ctx(rows=[])
            with self.assertRaises(GateError):
                require_gates(MONDAY, ctx, through=1, root=root)
            data = json.loads((root / "issues" / MONDAY.isoformat() / "sources" / "gates.json").read_text())
            self.assertEqual(data["steps"][0]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
