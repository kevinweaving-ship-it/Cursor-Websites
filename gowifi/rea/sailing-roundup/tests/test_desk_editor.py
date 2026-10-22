#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from desk_editor import angle, edit_event, edit_week, is_generic, photo_caption, qa
from gates import run_gates

SLUG = "2026-09-25-tsc-420-nationals"


def facts(**extra):
    base = {
        "slug": SLUG,
        "title": "420 Nationals",
        "class_name": "420",
        "club": "TSC",
        "club_name": "Theewater Sports Club",
        "start": "2026-09-26",
        "end": "2026-09-27",
        "entries": 16,
        "races": 8,
        "status": "Final",
        "winner": "Dale Rae and James Rae",
        "winner_helm": "Dale Rae",
        "winner_nett": "10",
        "winner_wins": 0,
        "winner_scores": {},
        "second": "Howard Leoto and Lebogang January",
        "second_nett": "20",
        "third": "Kamva Mgcubhe and Maddison Smit",
        "third_nett": "27",
        "tied_first": False,
        "mixed_class": False,
        "classes": ["420"],
        "ranked_rows": [],
    }
    base.update(extra)
    return base


class DeskEditor(unittest.TestCase):
    def test_win_reads_like_a_result_not_a_prompt(self):
        paras = edit_event(facts())
        blob = " ".join(paras)
        self.assertIn("Dale Rae and James Rae won the 420 Nationals at Theewater Sports Club", blob)
        self.assertIn("10 nett points", blob)
        self.assertIn("16-boat 420 fleet", blob)
        self.assertIn("Howard Leoto", blob)
        self.assertIn("10 points behind", blob)
        self.assertIn("[1]", blob)
        self.assertFalse(is_generic(blob))
        self.assertEqual(qa(blob, facts()), [])

    def test_sweep_angle_from_box_score(self):
        scores = {f"R{i}": "1" for i in range(1, 9)}
        f = facts(winner_scores=scores, winner_wins=8)
        self.assertEqual(angle(f), "sweep")
        blob = " ".join(edit_event(f))
        self.assertIn("swept the 420 Nationals", blob)
        self.assertIn("winning all 8 races", blob)

    def test_tie_does_not_invent_countback(self):
        f = facts(tied_first=True, second_nett="10")
        self.assertEqual(angle(f), "tie")
        blob = " ".join(edit_event(f))
        self.assertIn("level on nett points", blob)
        self.assertNotIn("countback", blob)

    def test_provisional_stays_provisional(self):
        blob = " ".join(edit_event(facts(status="Provisional")))
        self.assertIn("finished first in the published", blob)
        self.assertIn("remain provisional", blob)

    def test_mixed_fleet_keeps_class_podiums_separate(self):
        f = facts(
            title="Free State Youth Provincial Champs",
            club_name="Lake Deneys Yacht Club",
            winner="Maximilian Malan",
            winner_helm="Maximilian Malan",
            winner_class="Dabchick",
            mixed_class=True,
            classes=["Dabchick", "Optimist A", "Optimist B"],
            entries=26,
            races=7,
            winner_nett="6",
            ranked_rows=[
                {"class_name": "Dabchick", "helm_name": "Maximilian Malan"},
                {"class_name": "Dabchick", "helm_name": "Ethan Biagio"},
                {"class_name": "Optimist A", "helm_name": "Taylor Milln"},
                {"class_name": "Optimist B", "helm_name": "Danny Coetzer"},
            ],
        )
        blob = " ".join(edit_event(f))
        self.assertIn("Ethan Biagio", blob)
        self.assertIn("Dabchick", blob)
        self.assertIn("Optimist A", blob)
        self.assertNotIn("Taylor Milln finished second", blob)

    def test_photo_caption_uses_real_title_not_system_speak(self):
        hero = {"status": "pass", "local_path": "media/x.jpg", "title": "420 Nationals prizegiving"}
        self.assertEqual(photo_caption(hero, facts()), "420 Nationals prizegiving.")
        blob = " ".join(edit_event(facts(), hero))
        self.assertIn("photograph with this report is 420 Nationals prizegiving", blob)
        self.assertNotIn("stored hero", blob)

    def test_tsl_copy_names_teams_not_sailor_nett(self):
        f = facts(
            title="SA Sailing WC Team Sailing Event",
            class_name="TSL",
            club="MAC",
            club_name="MAC",
            start="2026-10-17",
            end="2026-10-18",
            entries=7,
            races=15,
            winner="RCYCA A",
            winner_helm="RCYCA A",
            winner_team="RCYCA A",
            winner_wins=4,
            winner_nett="",
            second="Eden District",
            second_nett="",
            third="MAC",
            third_nett="",
            team_racing=True,
            scoring_system="Team Racing",
        )
        blob = " ".join(edit_event(f))
        self.assertIn("RCYCA A won the SA Sailing WC Team Sailing Event", blob)
        self.assertIn("7-team TSL field", blob)
        self.assertIn("Eden District finished second", blob)
        self.assertIn("MAC finished third", blob)
        self.assertNotIn("nett points", blob)
        self.assertNotIn("Maddison", blob)
        self.assertEqual(qa(blob, f), [])
        sailors = "Maddison Smit; Tristan Gress; Unam Lubhelwana and Kamva Mgcubhe; Thandokazi Sibanyoni; Alexa Aab"
        fixed = " ".join(edit_event(dict(f, winner=sailors, winner_helm=sailors)))
        self.assertIn("RCYCA A won", fixed)
        self.assertNotIn("Maddison", fixed)
        with self.assertRaises(ValueError):
            edit_event(dict(f, winner=sailors, winner_team="", winner_helm=sailors))

    def test_py_overall_names_the_helm_not_a_class_split(self):
        f = facts(
            title="Dam Bottle Sprints",
            class_name="",
            club="HMYC",
            club_name="Henley Midmar Yacht Club",
            start="2026-10-10",
            end="2026-10-11",
            entries=4,
            races=3,
            winner="Lorrian Wells",
            winner_helm="Lorrian Wells",
            winner_class="Dart 18",
            winner_nett="5",
            second="Simon Dommett",
            second_nett="7",
            third="Bryan Paxman",
            third_nett="13",
            identity="helm",
            overall=True,
            mixed_class=True,
            classes=["Dart 18", "Ilca 7", "Hunter 19"],
            scoring_system="Portsmouth Yardstick (PY)",
            scoring_kind="handicap",
        )
        blob = " ".join(edit_event(f))
        self.assertIn("Lorrian Wells won the Dam Bottle Sprints", blob)
        self.assertIn("4-boat PY fleet", blob)
        self.assertNotIn("taking the Dart 18 fleet", blob)
        self.assertEqual(qa(blob, f), [])

    def test_lipton_copy_names_the_boat(self):
        f = facts(
            title="Lipton Challenge Cup",
            class_name="J22",
            club="RCYC",
            club_name="Royal Cape Yacht Club",
            start="2026-08-29",
            end="2026-08-30",
            entries=17,
            races=10,
            winner="HYC",
            winner_helm="HYC",
            winner_team="HYC",
            winner_nett="",
            second="RCYC",
            third="UCTYC",
            identity="boat",
            scoring_system="Appendix A",
        )
        blob = " ".join(edit_event(f))
        self.assertIn("HYC won the Lipton Challenge Cup", blob)
        self.assertIn("17-boat J22 fleet", blob)
        self.assertIn("RCYC finished second", blob)
        self.assertNotIn("nett points", blob)
        self.assertEqual(qa(blob, f), [])

    def test_rejects_generic_filler(self):
        self.assertTrue(is_generic("Sailors took to the water for an exciting weekend."))
        self.assertTrue(qa("An exciting weekend of sailing. Dale won.", facts()))

    def test_week_lead_names_scored_and_unlisted(self):
        reports = [
            {"headline": "Dale Rae wins 420 Nationals", "event_id": "a", "type": "regatta_report", "entries": 32},
            {"headline": "Free State Youth Provincial Champs", "event_id": "b", "type": "regatta_report", "entries": 26},
            {"headline": "Mirror Regionals at PYC", "event_id": "c", "type": "regatta_report", "entries": 18},
            {"headline": "Small Club Open at PYC", "event_id": "d", "type": "regatta_report", "entries": 8},
        ]
        paras = edit_week("26–27 September 2026", reports, ["Agulhas Race", "Lipton Cup Practice"])
        blob = " ".join(paras)
        self.assertIn("was led by Dale Rae wins 420 Nationals", blob)
        self.assertIn("Agulhas Race", blob)
        self.assertIn("Lipton Cup Practice", blob)
        self.assertNotIn("Last week's roundup covers", blob)

    def test_generic_story_fails_the_gate(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            rel = f"media/{SLUG}-hero.jpg"
            path = root / "issues" / "2026-09-28" / rel
            path.parent.mkdir(parents=True)
            path.write_bytes(b"desk-photo")
            ctx = {
            "monday": "2026-09-28",
            "root": str(root),
            "heroes": {
                SLUG: {
                    "status": "pass",
                    "local_path": rel,
                    "source_url": "https://sailingsa.co.za/regatta/" + SLUG,
                    "title": "420 Nationals prizegiving",
                }
            },
            "slugs": [SLUG],
            "rows_by_slug": {
                SLUG: [
                    {
                        "event_name": "420 Nationals",
                        "host_club_code": "TSC",
                        "host_club_name": "Theewater Sports Club",
                        "class_name": "420",
                        "start_date": "2026-09-26",
                        "end_date": "2026-09-27",
                        "rank": 1,
                        "helm_name": "Dale Rae",
                        "crew_name": "James Rae",
                        "nett_points_raw": 10,
                        "entries_total": 16,
                    },
                    {"event_name": "420 Nationals", "host_club_code": "TSC", "rank": 2, "helm_name": "Howard Leoto", "nett_points_raw": 20},
                    {"event_name": "420 Nationals", "host_club_code": "TSC", "rank": 3, "helm_name": "Kamva Mgcubhe", "nett_points_raw": 27},
                ]
            },
            "table_events": [{"event_name": "420 Nationals", "regatta_id": SLUG, "has_results": True}],
            "articles": [
                {
                    "type": "feature",
                    "headline": "Last Week's Roundup",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Sailors took to the water for an exciting weekend at the 420 Nationals and it was a weekend to remember.",
                        }
                    ],
                },
                {
                    "type": "regatta_report",
                    "event_id": SLUG,
                    "id": SLUG,
                    "headline": "Dale Rae wins 420 Nationals",
                    "entries": 16,
                    "citations": [{"n": 1, "url": "https://sailingsa.co.za/regatta/" + SLUG}],
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Dale Rae won the 420 Nationals in an exciting weekend of sailing [1].",
                        }
                    ],
                },
            ],
            "roster": {"confirmed": True, "passed_slugs": [SLUG], "events": [{"slug": SLUG, "status": "pass", "name": "420 Nationals", "equals": {"name": "420 Nationals"}}]},
            }
            run = run_gates(ctx, through=3)
            self.assertEqual(run.step(1).status, "pass", run.summary())
            self.assertEqual(run.step(3).status, "fail")
            self.assertTrue(any("generic" in e for e in run.step(3).errors), run.summary())


if __name__ == "__main__":
    unittest.main()
