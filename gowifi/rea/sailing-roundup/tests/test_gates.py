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
from tsl_board import apply_parent_tsl_board
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


def tsl_mac_rows():
    """SA Sailing WC Team Sailing — /api/regatta has teams, rank/nett stay empty."""
    teams = (
        ("MAC", "MAC", "Maddison Smit; Tristan Gress; Unam Lubhelwana", "Kamva Mgcubhe; Thandokazi Sibanyoni; Alexa Aab", 21336),
        ("MATIES", "USYC", "Corben Smith; Robyn Roselli; Conrad Holm", "Chiara Fruet", 21337),
        ("Eden District", "EDYC", "Christian Cilliers; Arthur Watson; Lulonke Lenks", "", 21338),
        ("RCYCA A", "RCYC", "Hayden Miller; Aphendule Mqwalaseli; Sesona Ntsaluba", "", 21342),
        ("University of Cape Town Yacht Club", "UCTYC", "Jessie Basson; Rebecca Hall; Eric Leach", "", 21346),
        ("izivungu", "IZV", "", "", 21368),
        ("RCYC Sailing Academy", "RCYC", "", "", 21369),
    )
    rows = []
    for boat, club, helm, crew, result_id in teams:
        rows.append(
            {
                "event_name": "SA Sailing WC Team Sailing Event",
                "host_club_code": "MAC",
                "host_club_name": "MAC",
                "host_club_slug": "mac",
                "class_name": "TSL",
                "class_canonical": "TSL",
                "start_date": "2026-10-17",
                "end_date": "2026-10-18",
                "result_status": "Final",
                "races_sailed": 0,
                "entries_total": 7,
                "scoring_system": "Team Racing",
                "result_id": result_id,
                "rank": None,
                "nett_points_raw": None,
                "total_points_raw": None,
                "helm_name": helm,
                "crew_name": crew,
                "boat_name": boat,
                "club_abbrev": club,
            }
        )
    return rows


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
        "entries": 16,
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
                    "with Dale Rae defending the 420 Nationals title and the Dart 18 fleet finishing Sunday."
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
        self.assertEqual(rec["equals"]["source"], "parent")
        self.assertEqual(rec["equals"]["fleets"], ["420"])
        self.assertEqual(rec["equals"]["leaderboard"][0]["helm"], "Dale Rae")
        self.assertEqual([row["pos"] for row in rec["equals"]["leaderboard"]], ["1", "2", "3"])
        self.assertEqual(len(rec["equals"]["leaderboards"][0]["rows"]), 3)
        self.assertTrue(rec["checksum"])
        self.assertEqual(rec["find_externally"]["need"], ["photos", "news", "social"])
        self.assertEqual(rec["find_externally"]["fleets"], ["420"])

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

    def test_parent_leaderboard_keeps_every_rank(self):
        rows = sample_rows()
        extra = dict(rows[2])
        extra["rank"] = 4
        extra["helm_name"] = "Fourth Helm"
        extra["nett_points_raw"] = 40
        fifth = dict(rows[2])
        fifth["rank"] = 5
        fifth["helm_name"] = "Fifth Helm"
        fifth["nett_points_raw"] = 50
        rec = check_one_event(MONDAY, SLUG, rows + [extra, fifth])
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual([row["pos"] for row in rec["equals"]["leaderboard"]], ["1", "2", "3", "4", "5"])
        self.assertEqual(rec["equals"]["leaderboard"][-1]["helm"], "Fifth Helm")

    def test_each_class_gets_its_own_full_leaderboard(self):
        rows = [
            {
                "event_name": "Free State Youth Provincial Champs",
                "host_club_code": "LDYC",
                "host_club_name": "Lake Deneys Yacht Club",
                "class_name": "Dabchick",
                "start_date": "2026-09-26",
                "end_date": "2026-09-27",
                "rank": 1,
                "helm_name": "Maximilian Malan",
                "nett_points_raw": 6,
            },
            {
                "event_name": "Free State Youth Provincial Champs",
                "host_club_code": "LDYC",
                "class_name": "Dabchick",
                "rank": 2,
                "helm_name": "Ethan Biagio",
                "nett_points_raw": 8,
            },
            {
                "event_name": "Free State Youth Provincial Champs",
                "host_club_code": "LDYC",
                "class_name": "Optimist A",
                "rank": 1,
                "helm_name": "Taylor Milln",
                "nett_points_raw": 8,
            },
            {
                "event_name": "Free State Youth Provincial Champs",
                "host_club_code": "LDYC",
                "class_name": "Optimist B",
                "rank": 1,
                "helm_name": "Danny Coetzer",
                "nett_points_raw": 10,
            },
        ]
        rec = check_one_event(MONDAY, "2026-09-26-ldyc-free-state-youth-provincial-champs", rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        fleets = rec["equals"]["fleets"]
        self.assertEqual(fleets, ["Dabchick", "Optimist A", "Optimist B"])
        by_fleet = {b["fleet"]: b["rows"] for b in rec["equals"]["leaderboards"]}
        self.assertEqual([r["helm"] for r in by_fleet["Dabchick"]], ["Maximilian Malan", "Ethan Biagio"])
        self.assertEqual(by_fleet["Optimist A"][0]["pos"], "1")
        self.assertEqual(by_fleet["Optimist B"][0]["helm"], "Danny Coetzer")

    def test_fleet_racing_keeps_fleet_names(self):
        rows = sample_rows()
        rows[0]["fleet_label"] = "Gold Fleet"
        rows[1]["fleet_label"] = "Gold Fleet"
        rows[2]["fleet_label"] = "Silver Fleet"
        rows[2]["rank"] = 1
        rec = check_one_event(MONDAY, SLUG, rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["equals"]["fleets"], ["Gold Fleet", "Silver Fleet"])
        gold = rec["equals"]["leaderboards"][0]
        self.assertEqual(gold["fleet"], "Gold Fleet")
        self.assertEqual(len(gold["rows"]), 2)
        self.assertEqual(rec["equals"]["leaderboards"][1]["fleet"], "Silver Fleet")

    def test_course_name_fails(self):
        rec = check_one_event(MONDAY, "2026-09-26-ityc-instructor-course", sample_rows(event_name="Instructor Course"))
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("course/meeting" in e for e in rec["errors"]))

    def test_tsl_file_order_without_parent_sheet_fails(self):
        monday = dt.date(2026, 10, 19)
        slug = "2026-10-17-mac-tsl-wc-team-sailing"
        rec = check_one_event(monday, slug, tsl_mac_rows())
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("parent sheet" in e or "no ranked rows" in e or "1st place" in e for e in rec["errors"]))
        self.assertNotEqual(rec["winner"], "RCYCA A")

    def test_tsl_team_racing_ranks_from_parent_sheet(self):
        monday = dt.date(2026, 10, 19)
        slug = "2026-10-17-mac-tsl-wc-team-sailing"
        fixture = pathlib.Path(__file__).resolve().parent / "fixtures" / "mac-tsl-state.json"
        state = json.loads(fixture.read_text())
        rows = apply_parent_tsl_board(tsl_mac_rows(), state)
        rec = check_one_event(monday, slug, rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["name"], "SA Sailing WC Team Sailing Event")
        self.assertEqual(rec["winner"], "RCYCA A")
        self.assertTrue(rec["equals"]["team_racing"])
        self.assertEqual(rec["equals"]["scoring_system"], "Team Racing")
        self.assertEqual(rec["equals"]["fleets"], ["TSL"])
        board = rec["equals"]["leaderboard"]
        self.assertEqual([row["pos"] for row in board], ["1", "2", "3", "4", "5"])
        self.assertEqual([row["helm"] for row in board], [
            "RCYCA A",
            "Eden District",
            "MAC",
            "MATIES",
            "University of Cape Town Yacht Club",
        ])
        self.assertEqual(board[0]["team"], "RCYCA A")
        self.assertEqual(board[0]["wins"], "4")
        self.assertEqual(board[0]["nett"], "34")
        self.assertFalse(any("no ranked rows" in e for e in rec["errors"]))
        self.assertFalse(any("1st place" in e for e in rec["errors"]))

    def test_missing_first_place_still_fails(self):
        rows = sample_rows()
        for row in rows:
            row["rank"] = int(row["rank"]) + 1
        rec = check_one_event(MONDAY, SLUG, rows)
        self.assertEqual(rec["status"], "fail")
        self.assertTrue(any("1st place" in e for e in rec["errors"]))

    def test_lipton_ranks_boats_not_skippers(self):
        monday = dt.date(2026, 8, 31)
        slug = "2026-08-29-lipton-challenge-cup"
        rows = [
            {
                "event_name": "Lipton Challenge Cup",
                "host_club_code": "RCYC",
                "host_club_name": "Royal Cape Yacht Club",
                "class_name": "J22",
                "start_date": "2026-08-29",
                "end_date": "2026-08-30",
                "scoring_system": "Appendix A",
                "entries_total": 3,
                "rank": pos,
                "boat_name": boat,
                "helm_name": skipper,
                "club_abbrev": boat,
                "nett_points_raw": nett,
            }
            for pos, boat, skipper, nett in (
                (1, "HYC", "David Rae", 44),
                (2, "RCYC", "Rick Nankin", 46),
                (3, "UCTYC", "Dave Hudson", 51),
            )
        ]
        rec = check_one_event(monday, slug, rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["winner"], "HYC")
        self.assertEqual(rec["equals"]["identity"], "boat")
        self.assertEqual([row["helm"] for row in rec["equals"]["leaderboard"]], ["HYC", "RCYC", "UCTYC"])
        self.assertEqual([row["pos"] for row in rec["equals"]["leaderboard"]], ["1", "2", "3"])

    def test_py_handicap_ranks_boats(self):
        rows = [
            {
                "event_name": "Club PY Pursuit",
                "host_club_code": "ZYC",
                "host_club_name": "ZVYC",
                "class_name": "PY",
                "start_date": "2026-09-26",
                "end_date": "2026-09-27",
                "scoring_system": "PY",
                "entries_total": 3,
                "rank": pos,
                "boat_name": boat,
                "helm_name": helm,
                "corrected_time": time,
            }
            for pos, boat, helm, time in (
                (1, "Chinook", "Sam Peters", "1:12:04"),
                (2, "Sea Breeze", "Pat Naidoo", "1:14:22"),
                (3, "Storm", "Lee Adams", "1:18:01"),
            )
        ]
        rec = check_one_event(MONDAY, "2026-09-26-zyc-club-py-pursuit", rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["winner"], "Chinook")
        self.assertEqual(rec["equals"]["identity"], "boat")
        self.assertEqual(rec["equals"]["scoring_system"], "PY")
        self.assertEqual([row["pos"] for row in rec["equals"]["leaderboard"]], ["1", "2", "3"])
        self.assertEqual(rec["equals"]["leaderboard"][0]["boat"], "Chinook")

    def test_timed_race_ranks_from_finish_order(self):
        rows = [
            {
                "event_name": "Agulhas Timed Race",
                "host_club_code": "HMYC",
                "host_club_name": "Henley Midmar Yacht Club",
                "class_name": "Open",
                "start_date": "2026-09-26",
                "end_date": "2026-09-27",
                "scoring_system": "Timed",
                "entries_total": 3,
                "rank": None,
                "boat_name": boat,
                "helm_name": helm,
                "elapsed_time": time,
            }
            for boat, helm, time in (
                ("Orion", "Chris Bell", "2:01:10"),
                ("Mistral", "Ann Bell", "2:04:40"),
                ("Swift", "Jon Reed", "2:11:05"),
            )
        ]
        rec = check_one_event(MONDAY, "2026-09-26-hmyc-agulhas-timed-race", rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["winner"], "Orion")
        self.assertEqual(rec["equals"]["identity"], "boat")
        self.assertEqual([row["pos"] for row in rec["equals"]["leaderboard"]], ["1", "2", "3"])

    def test_py_mixed_fleet_is_one_overall_board(self):
        monday = dt.date(2026, 10, 12)
        slug = "2026-10-10-hmyc-dam-bottle-sprints"
        rows = [
            {
                "event_name": "Dam Bottle Sprints",
                "host_club_code": "HMYC",
                "host_club_name": "Henley Midmar Yacht Club",
                "class_name": klass,
                "start_date": "2026-10-10",
                "end_date": "2026-10-11",
                "scoring_system": "Portsmouth Yardstick (PY)",
                "entries_total": 4,
                "rank": pos,
                "helm_name": helm,
                "boat_name": None,
                "nett_points_raw": nett,
            }
            for klass, pos, helm, nett in (
                ("Dart 18", 1, "Lorrian Wells", 5),
                ("Ilca 7", 2, "Simon Dommett", 7),
                ("Hunter 19", 3, "Bryan Paxman", 13),
                ("Hunter 19", 4, "Tim Kerry", 18),
            )
        ]
        rec = check_one_event(monday, slug, rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["winner"], "Lorrian Wells")
        self.assertEqual(rec["equals"]["identity"], "helm")
        self.assertEqual(rec["equals"]["fleets"], ["PY"])
        self.assertEqual([row["pos"] for row in rec["equals"]["leaderboard"]], ["1", "2", "3", "4"])
        self.assertEqual(rec["equals"]["leaderboard"][0]["helm"], "Lorrian Wells")
        self.assertFalse(any("1st place" in e for e in rec["errors"]))

    def test_single_handed_still_ranks_the_helm(self):
        rows = sample_rows(crew_name="")
        rows[0]["class_name"] = "ILCA 7"
        rows[0]["helm_name"] = "Simon Dommett"
        rows[0]["crew_name"] = ""
        rows[1]["crew_name"] = ""
        rows[2]["crew_name"] = ""
        rec = check_one_event(MONDAY, SLUG, rows)
        self.assertEqual(rec["status"], "pass", rec["errors"])
        self.assertEqual(rec["winner"], "Simon Dommett")
        self.assertEqual(rec["equals"]["identity"], "helm")
        self.assertEqual(rec["equals"]["leaderboard"][0]["helm"], "Simon Dommett")


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

    def test_media_passes_when_parent_was_inspected_and_empty(self):
        ctx = facts_ctx(
            heroes={
                SLUG: {
                    "slug": SLUG,
                    "status": "empty",
                    "inspected": True,
                    "empty": True,
                    "local_path": "",
                    "parent_has_media": False,
                }
            }
        )
        run = run_gates(ctx, through=2)
        self.assertEqual(run.step(1).status, "pass")
        self.assertEqual(run.step(2).status, "pass", run.summary())

    def test_step1_pass_allows_step2_which_fails_without_photos(self):
        run = run_gates(facts_ctx(), through=6)
        self.assertEqual(run.step(1).status, "pass")
        self.assertEqual(run.step(2).status, "fail")
        self.assertTrue(any("no hero stored on box" in e or "hero file missing" in e for e in run.step(2).errors))
        self.assertEqual(run.step(3).status, "blocked")
        self.assertFalse(run.can_publish)
        self.assertTrue(run.ok_through(1))
        self.assertFalse(run.ok_through(2))

    def _stored_hero(self, root, slug=SLUG):
        rel = f"media/{slug}-hero.jpg"
        path = root / "issues" / MONDAY.isoformat() / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"real-photo-bytes-" + slug.encode())
        return {
            "slug": slug,
            "status": "pass",
            "local_path": rel,
            "parent_has_media": True,
            "source_url": "https://sailingsa.co.za/regatta/" + slug,
            "title": "420 Nationals prizegiving",
        }

    def test_all_steps_pass_unlocks_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            public = root / "public"
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
                root=str(root),
                heroes={SLUG: self._stored_hero(root)},
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
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            ctx = facts_ctx(
                articles=[passing_feature(), passing_article(), passing_article("2026-10-10-hmyc-dam-bottle-sprints")],
                root=str(root),
                heroes={SLUG: self._stored_hero(root)},
            )
            run = run_gates(ctx, through=6)
        self.assertEqual(run.step(1).status, "pass")
        self.assertEqual(run.step(2).status, "fail")
        self.assertTrue(any("not on confirmed weekend roster" in e for e in run.step(2).errors))
        self.assertEqual(run.step(3).status, "blocked")

    def test_story_fails_when_feature_omits_unlisted_calendar_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            ctx = facts_ctx(
                articles=[passing_feature(), passing_article()],
                table_events=[
                    {
                        "event_name": "420 Nationals",
                        "regatta_id": SLUG,
                        "has_results": True,
                        "start_date": "2026-09-26",
                        "end_date": "2026-09-27",
                    },
                    {"event_name": "Agulhas Race", "regatta_id": None, "has_results": False},
                ],
                root=str(root),
                heroes={SLUG: self._stored_hero(root)},
            )
            run = run_gates(ctx, through=3)
        self.assertEqual(run.step(2).status, "pass", run.summary())
        self.assertEqual(run.step(3).status, "fail")
        self.assertTrue(any("Agulhas Race" in e and "no results card" in e for e in run.step(3).errors))
        self.assertFalse(run.ok_through(3))

    def test_story_fails_when_scored_articles_are_not_biggest_first(self):
        dart = "2026-09-24-hmyc-dart-18-nationals"
        dart_rows = sample_rows(
            event_name="Dart 18 Nationals",
            host_club_code="HMYC",
            host_club_name="Henley Midmar Yacht Club",
            start_date="2026-09-24",
            end_date="2026-09-27",
            entries_total=8,
        )
        small = passing_article(dart)
        small["headline"] = "Bradley Levin wins Dart 18 Nationals"
        small["entries"] = 8
        small["blocks"] = [
            {
                "type": "paragraph",
                "text": "Bradley Levin won the Dart 18 Nationals at Henley Midmar Yacht Club [1].",
            }
        ]
        small["citations"] = [{"n": 1, "url": "https://sailingsa.co.za/regatta/" + dart}]
        feature = {
            "id": "weekend-feature",
            "type": "feature",
            "headline": "Last Week's Roundup",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": (
                        "Last week's roundup covers two scored events. Dale Rae and James Rae win 420 Nationals "
                        "headed the list. Also decided were Bradley Levin wins Dart 18 Nationals."
                    ),
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            ctx = facts_ctx(
                slugs=[SLUG, dart],
                rows_by_slug={SLUG: sample_rows(), dart: dart_rows},
                table_events=[
                    {"event_name": "420 Nationals", "regatta_id": SLUG, "has_results": True},
                    {"event_name": "Dart 18 Nationals", "regatta_id": dart, "has_results": True},
                ],
                articles=[feature, small, passing_article()],
                root=str(root),
                heroes={SLUG: self._stored_hero(root), dart: self._stored_hero(root, dart)},
            )
            run = run_gates(ctx, through=3)
        self.assertEqual(run.step(1).status, "pass", run.summary())
        self.assertEqual(run.step(2).status, "pass", run.summary())
        self.assertEqual(run.step(3).status, "fail")
        self.assertTrue(any("sorted by entries" in e for e in run.step(3).errors))


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
