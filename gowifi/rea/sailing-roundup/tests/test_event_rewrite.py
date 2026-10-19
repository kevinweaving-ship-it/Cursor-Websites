#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from event_rewrite import (
    citation_index,
    cluster_coverage,
    event_finished,
    facts_from_rows,
    layout_for,
    pick_image,
    pick_images,
    rewrite_event,
    rewrite_paragraphs,
    unique_headline,
    _event_photo_score,
    _facebook_page_chrome,
    _is_event_photograph,
    _keep_cluster_item,
    _wiki_url,
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
        self.assertGreaterEqual(len(paras), 4)
        self.assertIn("Dale Rae and James Rae", blob)
        self.assertIn("Theewater", blob)
        self.assertGreater(len(blob), 300)
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
        self.assertTrue(all(b.get("type") != "video" for b in article["blocks"]))
        results = next(b for b in article["blocks"] if b["type"] == "results")
        self.assertEqual(results["columns"], ["Pos", "Helm", "Crew", "Club", "Sail No", "Nett"])
        self.assertEqual(len(results["rows"]), 3)
        self.assertEqual([r[0] for r in results["rows"]], ["1", "2", "3"])
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
        self.assertIn("flex-direction:column", css)
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

    def test_dart_uses_hmyc_facebook_source(self):
        rows = [
            {
                "event_name": "Dart 18 Nationals",
                "host_club_code": "HMYC",
                "host_club_name": "Henley Midmar Yacht Club",
                "class_name": "Dart 18",
                "start_date": "2026-09-24",
                "end_date": "2026-09-27",
                "result_status": "Provisional",
                "races_sailed": 7,
                "entries_total": 38,
                "rank": 1,
                "helm_name": "Bradley Levin",
                "club_abbrev": "SYC",
                "sail_number": "7951",
                "nett_points_raw": 20,
                "race_scores": {"R1": "3", "R2": "(15)", "R3": "4"},
            },
            {
                "event_name": "Dart 18 Nationals",
                "host_club_code": "HMYC",
                "rank": 2,
                "helm_name": "Kyle Boman",
                "club_abbrev": "TCC",
                "sail_number": "2460",
                "nett_points_raw": 26,
            },
            {
                "event_name": "Dart 18 Nationals",
                "host_club_code": "HMYC",
                "rank": 3,
                "helm_name": "Bradley Stemmett",
                "crew_name": "Saskia Stemmett",
                "club_abbrev": "VYC",
                "sail_number": "3862",
                "nett_points_raw": 27,
            },
        ]
        facts = facts_from_rows("2026-09-24-hmyc-dart-18-nationals", rows)
        cluster = {
            "articles": [
                {
                    "url": "https://www.facebook.com/share/p/1PGpY1pGh1/",
                    "share_url": "https://www.facebook.com/share/p/1PGpY1pGh1/",
                    "title": "HMYC - Henley Midmar Yacht Club",
                    "description": (
                        "DART 18 NATIONALS – Final results!\n\n"
                        "What a day on the water! Congratulations to all the sailors competing in the Dart 18 Nationals.\n\n"
                        "OVERALL TOP 3\n1st – Bradley Levin (SYC) – Sail 7951\n"
                        "2nd – Kyle Boman (TCC) – Sail 2460\n"
                        "3rd – Bradley Stemmett (VYC) – Sail 3862\n\n"
                        "HMYC TOP 3\n5th – Kim Phillips – Sail 4665\n"
                        "7th – Lorrian Wells – Sail 520\n"
                        "8th – Gregory Dobson – Sail 5179\n\n"
                        "And a special mention to Josh Pretorius, finishing 9th overall for HMYC!"
                    ),
                    "engine": "host_club_post",
                    "provenance": "host_club_post",
                }
            ],
            "count": 1,
        }
        paras = rewrite_paragraphs(facts, cluster)
        blob = " ".join(paras)
        self.assertIn("What a day on the water", blob)
        self.assertIn("Kim Phillips", blob)
        self.assertIn("Josh Pretorius", blob)
        self.assertIn("Kyle Boman", blob)
        self.assertNotIn("weekend", blob.lower())
        self.assertNotIn("Outside the scoreboard", blob)
        article = rewrite_event("2026-09-28", facts, pack={}, cluster=cluster, layout="split")
        self.assertTrue(any("1PGpY1pGh1" in (s or "") for s in article["sources"]))
        results = next(b for b in article["blocks"] if b["type"] == "results")
        self.assertEqual(len(results["rows"]), 3)
        self.assertNotRegex(article["headline"], r"\bleads\b")
        self.assertNotIn("day 2 of", " ".join(paras).lower())
        self.assertTrue(event_finished(facts, "2026-09-28"))
        live = dict(facts, finished=False, status="Provisional")
        self.assertIn("lead", unique_headline(live))
        self.assertTrue(any("[1]" in p or "[2]" in p for p in paras))

    def test_event_photos_not_wiki_and_more_than_one(self):
        facts = facts_from_rows("2026-09-24-hmyc-dart-18-nationals", sample_rows())
        facts["class_name"] = "Dart 18"
        facts["slug"] = "2026-09-24-hmyc-dart-18-nationals"
        cluster = {
            "articles": [
                {
                    "url": "https://www.facebook.com/share/p/1PGpY1pGh1/",
                    "title": "Dart 18 Nationals final results",
                    "image": "https://scontent.xx.fbcdn.net/prizegiving.jpg",
                },
                {
                    "url": "https://www.facebook.com/henleymidmaryachtclub",
                    "title": "Dart 18 Nationals on the water",
                    "image": "https://lookaside.fbsbx.com/lookaside/crawler/media/?media_id=1632007242054050",
                },
                {
                    "url": "https://commons.wikimedia.org/wiki/File:Old_boat.jpg",
                    "title": "Random 1954 dinghy",
                    "image": "https://upload.wikimedia.org/wikipedia/commons/4/41/Regate_420.JPG",
                },
            ]
        }
        photos = pick_images(facts, cluster)
        self.assertGreaterEqual(len(photos), 2)
        self.assertTrue(all(not _wiki_url(p["url"]) and not _wiki_url(p["source_url"]) for p in photos))
        self.assertIsNone(pick_image(facts, {"articles": [cluster["articles"][2]]}))
        prize = {
            "url": "https://scontent.xx.fbcdn.net/prizegiving.jpg",
            "source_url": "https://www.facebook.com/share/p/1PGpY1pGh1/",
            "title": "1st Bradley Levin prizegiving",
        }
        self.assertGreaterEqual(_event_photo_score(prize, facts), 40)
        wiki = {
            "url": "https://upload.wikimedia.org/wikipedia/commons/7/7d/505er_001.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File:505er_001.jpg",
            "title": "505",
        }
        self.assertLess(_event_photo_score(wiki, facts), 0)
        self.assertTrue(_facebook_page_chrome("https://www.facebook.com/int505"))
        self.assertTrue(_facebook_page_chrome("https://www.facebook.com/420nationalssouthafrica/"))
        self.assertFalse(_facebook_page_chrome("https://www.facebook.com/share/p/1PGpY1pGh1/"))
        logo = {
            "url": "https://scontent.xx.fbcdn.net/v/t39.30808-1/logo.jpg",
            "source_url": "https://www.facebook.com/420nationalssouthafrica/",
            "title": "420 class logo",
        }
        self.assertLess(_event_photo_score(logo, facts), 0)
        dups = pick_images(
            facts,
            {
                "articles": [
                    cluster["articles"][0],
                    {
                        "url": "https://www.facebook.com/share/p/1PGpY1pGh1/",
                        "title": "same prizegiving",
                        "image": "https://scontent.xx.fbcdn.net/prizegiving.jpg",
                    },
                ]
            },
        )
        self.assertEqual(len(dups), 1)

    def test_reject_logo_flag_and_poster_bytes(self):
        from pathlib import Path

        photos = Path("/tmp/roundup-photos")
        if not (photos / "2026-09-24-hmyc-dart-18-nationals.jpg").exists():
            self.skipTest("live photo fixtures not downloaded")
        self.assertTrue(_is_event_photograph((photos / "2026-09-24-hmyc-dart-18-nationals.jpg").read_bytes()))
        self.assertTrue(_is_event_photograph((photos / "2026-09-24-ayc-505-nationals.jpg").read_bytes()))
        self.assertTrue(_is_event_photograph((photos / "2026-09-25-tsc-420-nationals-3.jpg").read_bytes()))
        self.assertFalse(_is_event_photograph((photos / "2026-09-24-ayc-dabchick-gauteng-regionals.png").read_bytes()))
        self.assertFalse(_is_event_photograph((photos / "2026-09-24-ayc-505-nationals-3.jpg").read_bytes()))
        self.assertFalse(_is_event_photograph((photos / "2026-09-25-tsc-420-nationals.jpg").read_bytes()))

    def test_cluster_drops_coverage_outside_event_window(self):
        facts = facts_from_rows("2026-09-25-tsc-420-nationals", sample_rows())
        old = {
            "url": "https://novanews.co.za/2024/03/01/old-420-story",
            "title": "420 Nationals 2024 Dale Rae TSC",
            "published": "2024-03-01",
            "description": "Dale Rae won the 420 Nationals at TSC",
            "engine": "google_news",
        }
        fresh = {
            "url": "https://novanews.co.za/2026/09/30/hermanus-high-schools-sailors-crowned-national-champions/",
            "title": "Hermanus High School's sailors crowned national champions",
            "published": "2026-09-30",
            "description": "Dale Rae and James Rae won the 420 Nationals at Theewater",
            "engine": "google_news",
        }
        self.assertFalse(_keep_cluster_item(old, facts))
        self.assertTrue(_keep_cluster_item(fresh, facts))

    def test_cluster_always_keeps_sailingsa_results(self):
        facts = facts_from_rows("2026-09-25-tsc-420-nationals", sample_rows())
        official = {
            "url": "https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
            "title": "420 Nationals — SailingSA results",
            "engine": "sailingsa",
            "role": "official_results",
        }
        other = {
            "url": "https://sailingsa.co.za/regatta/2026-09-24-hmyc-dart-18-nationals",
            "title": "Dart 18 Nationals — SailingSA results",
            "engine": "sailingsa",
            "role": "official_results",
        }
        self.assertTrue(_keep_cluster_item(official, facts))
        self.assertFalse(_keep_cluster_item(other, facts))
        cluster = cluster_coverage(facts, pack=None, fetch=False)
        urls = [item["url"] for item in cluster["articles"]]
        self.assertIn(facts["url"], urls)
        cites = citation_index(cluster, facts)
        self.assertEqual(cites[0]["url"], facts["url"])


if __name__ == "__main__":
    unittest.main()
