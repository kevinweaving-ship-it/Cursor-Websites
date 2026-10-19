#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from event_rewrite import (
    facts_from_rows,
    layout_for,
    rewrite_event,
    rewrite_paragraphs,
    unique_headline,
)
from roundup import _image_block, _layout_name, _render_story, newspaper_css


def sample_rows():
    return [
        {
            "event_name": "420 Nationals",
            "host_club_code": "TSC",
            "host_club_name": "TSC",
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
            "race_scores": {"R1": "(4)", "R2": "1", "R3": "1", "R4": "1", "R5": "4", "R6": "1", "R7": "1", "R8": "1"},
        },
        {
            "event_name": "420 Nationals",
            "host_club_code": "TSC",
            "rank": 2,
            "helm_name": "Howard Leoto",
            "crew_name": "Lebogang January",
            "club_abbrev": "RNYC",
            "sail_number": "5309",
            "nett_points_raw": 20,
        },
        {
            "event_name": "420 Nationals",
            "host_club_code": "TSC",
            "rank": 3,
            "helm_name": "Kamva Mgcubhe",
            "crew_name": "Maddison Smit",
            "club_abbrev": "MAC",
            "sail_number": "54809",
            "nett_points_raw": 27,
        },
    ]


class RewriteEngine(unittest.TestCase):
    def test_unique_headline_and_article(self):
        facts = facts_from_rows("2026-09-25-tsc-420-nationals", sample_rows())
        headline = unique_headline(facts)
        self.assertNotEqual(headline, "420 Nationals")
        self.assertIn("Dale Rae", headline)
        self.assertIn("sweep", headline)
        solo = dict(facts, winner="Dylan Hall", winner_wins=12, races=12, tied_first=False, status="Final")
        self.assertIn("sweeps", unique_headline(solo))
        cluster = {
            "articles": [
                {
                    "url": "https://novanews.co.za/school/hermanus-high-schools-sailors-crowned-national-champions/",
                    "title": "Hermanus High School's sailors crowned national champions",
                    "description": "Timothy Weaving and Hayden Miller named U17 national champions",
                    "image": "https://novanews.co.za/photo.jpg",
                }
            ],
            "count": 1,
        }
        paras = rewrite_paragraphs(facts, cluster)
        blob = " ".join(paras)
        self.assertGreaterEqual(len(paras), 3)
        self.assertIn("Dale Rae and James Rae", blob)
        self.assertIn("Theewater", blob)
        self.assertNotIn("under review", blob.lower())
        self.assertNotIn("From a public social update", blob)
        self.assertIn("under-17", blob)

    def test_rewrite_has_image_and_leaderboard_only(self):
        facts = facts_from_rows("2026-09-25-tsc-420-nationals", sample_rows())
        cluster = {
            "articles": [
                {
                    "url": "https://novanews.co.za/x",
                    "title": "420",
                    "image": "https://novanews.co.za/photo.jpg",
                }
            ],
            "count": 1,
        }
        article = rewrite_event("2026-09-28", facts, pack={}, cluster=cluster, layout="photo-led")
        kinds = [b["type"] for b in article["blocks"]]
        self.assertEqual(kinds.count("results"), 1)
        self.assertIn("image", kinds)
        self.assertTrue(all(b.get("type") != "video" for b in article["blocks"]))
        results = next(b for b in article["blocks"] if b["type"] == "results")
        self.assertEqual(results["columns"], ["Pos", "Helm", "Crew", "Club", "Sail No", "Nett"])
        self.assertLessEqual(len(results["rows"]), 10)
        self.assertNotIn("source_info", article)
        html = _render_story(1, article)
        self.assertIn("story-photo-led", html)
        self.assertNotIn("Source info", html)
        self.assertNotIn("Social and media sources", html)

    def test_layouts_differ(self):
        self.assertEqual(layout_for(0, "feature"), "lead")
        self.assertEqual(layout_for(0, "regatta_report"), "photo-led")
        self.assertEqual(layout_for(1, "regatta_report"), "split")
        self.assertEqual(layout_for(2, "regatta_report"), "classic")
        self.assertEqual(layout_for(3, "regatta_report"), "compact")
        css = newspaper_css()
        self.assertIn("story-photo-led", css)
        self.assertIn("story-split", css)
        self.assertIn("story-classic", css)
        self.assertIn("@page{size:A3", css.replace(" ", ""))

    def test_image_block_always_shows_photo(self):
        html = _image_block(
            {
                "url": "media/420.jpg",
                "caption": "420 Nationals",
                "credit": "NovaNews",
                "rights_status": "external_link_only",
                "source_url": "https://novanews.co.za/x",
            }
        )
        self.assertIn("<img src=\"media/420.jpg\"", html)
        self.assertIn("<figure>", html)
        self.assertNotIn("View original photograph", html)

    def test_layout_assignment(self):
        self.assertEqual(_layout_name(0, {"type": "feature"}), "lead")
        self.assertEqual(_layout_name(1, {"type": "regatta_report", "layout": "split"}), "split")


if __name__ == "__main__":
    unittest.main()
