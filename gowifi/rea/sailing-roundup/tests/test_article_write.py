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

from article_write import (
    ai_polish,
    media_note,
    polish_copy,
    raw_context,
    write_event_article,
    write_issue,
)
from event_rewrite import facts_from_rows
from gates import run_gates
from publish_weekend import publish

MONDAY = dt.date(2026, 9, 28)
SLUG = "2026-09-25-tsc-420-nationals"
DART = "2026-09-24-hmyc-dart-18-nationals"
YOUTH = "2026-09-26-ldyc-free-state-youth-provincial-champs"
SMALL = "2026-09-26-pyc-small-club-open"


def sample_rows(name="420 Nationals", club="TSC", club_name="Theewater Sports Club", start="2026-09-26", end="2026-09-27", entries=16, helm="Dale Rae", crew="James Rae"):
    return [
        {
            "event_name": name,
            "host_club_code": club,
            "host_club_name": club_name,
            "class_name": name.split()[0],
            "start_date": start,
            "end_date": end,
            "result_status": "Final",
            "races_sailed": 8,
            "entries_total": entries,
            "rank": 1,
            "helm_name": helm,
            "crew_name": crew,
            "club_abbrev": "HYC",
            "sail_number": "53001",
            "nett_points_raw": 10,
        },
        {
            "event_name": name,
            "host_club_code": club,
            "rank": 2,
            "helm_name": "Howard Leoto",
            "crew_name": "Lebogang January",
            "nett_points_raw": 20,
        },
        {
            "event_name": name,
            "host_club_code": club,
            "rank": 3,
            "helm_name": "Kamva Mgcubhe",
            "crew_name": "Maddison Smit",
            "nett_points_raw": 27,
        },
    ]


def roster_event(slug, rows):
    facts = facts_from_rows(slug, rows)
    return {
        "slug": slug,
        "status": "pass",
        "name": facts["title"],
        "entries": facts["entries"],
        "winner": facts["winner"],
        "url": facts["url"],
        "equals": {
            "name": facts["title"],
            "host": facts["club"],
            "start": facts["start"],
            "end": facts["end"],
            "url": facts["url"],
            "fleets": facts.get("fleets") or [],
            "leaderboards": facts.get("class_leaderboards") or [],
        },
    }, facts


def stored_hero(root, slug, extra=b""):
    rel = f"media/{slug}-hero.jpg"
    path = root / "issues" / MONDAY.isoformat() / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"photo-" + slug.encode() + extra)
    return {
        "slug": slug,
        "status": "pass",
        "local_path": rel,
        "parent_has_media": True,
        "source_url": "https://sailingsa.co.za/regatta/" + slug,
        "title": slug,
    }


class ArticleWrite(unittest.TestCase):
    def test_raw_context_is_headline_plus_official_equals(self):
        rec, facts = roster_event(SLUG, sample_rows())
        ctx = raw_context(rec, facts, {"local_path": "media/hero.jpg"})
        self.assertIn("420 Nationals", ctx["headline"])
        self.assertEqual(ctx["name"], "420 Nationals")
        self.assertEqual(ctx["winner"], "Dale Rae and James Rae")
        self.assertEqual(ctx["entries"], 16)
        self.assertEqual(ctx["hero"], "media/hero.jpg")
        self.assertFalse(ctx["third_party"])

    def test_official_only_article_passes_without_third_party(self):
        rec, facts = roster_event(SLUG, sample_rows())
        hero = {"status": "pass", "local_path": "media/hero.jpg", "source_url": facts["url"], "title": "420 Nationals"}
        article = write_event_article("2026-09-28", rec, facts, hero, polish=lambda *a, **k: None)
        blob = " ".join(b.get("text") or "" for b in article["blocks"] if b.get("type") == "paragraph")
        self.assertIn("Dale Rae", blob)
        self.assertIn("420 Nationals", blob)
        self.assertNotIn("[1]", blob)
        self.assertTrue(any(b.get("type") == "image" for b in article["blocks"]))
        self.assertTrue(any(b.get("type") == "results" for b in article["blocks"]))
        self.assertFalse(article["third_party"])
        self.assertTrue(article["needs_external"])
        self.assertEqual(article["ai_writer"], "desk")
        self.assertNotIn("stored hero photograph", blob)
        cap = next(b.get("caption") for b in article["blocks"] if b.get("type") == "image")
        self.assertIn("420 Nationals", cap)
        self.assertEqual(article["sources"][0], facts["url"])

    def test_article_keeps_up_to_four_stored_images(self):
        rec, facts = roster_event(SLUG, sample_rows())
        hero = {
            "status": "pass",
            "local_path": "media/hero.jpg",
            "source_url": facts["url"],
            "title": "overall winners",
            "images": [
                {"status": "pass", "local_path": "media/a.jpg", "title": "overall winners", "source_url": facts["url"]},
                {"status": "pass", "local_path": "media/b.jpg", "title": "U17 boys", "source_url": facts["url"]},
                {"status": "pass", "local_path": "media/c.jpg", "title": "boat", "source_url": "https://www.facebook.com/share/1DGs9FyLwT/"},
                {"status": "reject", "local_path": "media/sheet.jpg", "title": "results sheet"},
            ],
        }
        article = write_event_article("2026-09-28", rec, facts, hero, polish=lambda *a, **k: None)
        images = [b for b in article["blocks"] if b.get("type") == "image"]
        self.assertEqual([b["url"] for b in images], ["media/a.jpg", "media/b.jpg", "media/c.jpg"])
        self.assertEqual(article["media_layout"], "paired-then-full")
        self.assertTrue(any(b.get("type") == "results" for b in article["blocks"]))

    def test_polish_discarded_when_winner_or_title_missing(self):
        rec, facts = roster_event(SLUG, sample_rows())
        article = write_event_article(
            "2026-09-28",
            rec,
            facts,
            None,
            polish=lambda *a, **k: "A lovely weekend of sailing with no names at all.",
        )
        blob = " ".join(b.get("text") or "" for b in article["blocks"] if b.get("type") == "paragraph")
        self.assertIn("Dale Rae", blob)
        self.assertNotIn("lovely weekend", blob)

    def test_polish_kept_when_facts_stay_locked(self):
        rec, facts = roster_event(SLUG, sample_rows())
        article = write_event_article(
            "2026-09-28",
            rec,
            facts,
            None,
            polish=lambda *a, **k: (
                "Dale Rae and James Rae sealed the 420 Nationals at Theewater Sports Club [1]. "
                "Howard Leoto finished second."
            ),
        )
        blob = " ".join(b.get("text") or "" for b in article["blocks"] if b.get("type") == "paragraph")
        self.assertIn("sealed the 420 Nationals", blob)
        self.assertIn("Dale Rae", blob)

    def test_ai_polish_returns_none_without_keys(self):
        rec, facts = roster_event(SLUG, sample_rows())
        empty = {
            "OPENAI_API_KEY": "",
            "CHATGPT_API_KEY": "",
            "GPT_API_KEY": "",
            "PERPLEXITY_API_KEY": "",
        }
        with patch.dict("os.environ", empty, clear=False):
            self.assertIsNone(ai_polish("event article", raw_context(rec, facts), facts, "draft"))
        self.assertIn("prizegiving", media_note({"status": "pass", "local_path": "media/x.jpg", "title": "420 Nationals prizegiving"}, facts))

    def test_week_roundup_names_four_scored_and_two_unlisted_biggest_first(self):
        packs = [
            roster_event(SMALL, sample_rows("Small Club Open", "PYC", "Point Yacht Club", entries=8, helm="Pat Small")),
            roster_event(DART, sample_rows("Dart 18 Nationals", "HMYC", "Henley Midmar Yacht Club", start="2026-09-24", entries=18, helm="Bradley Levin", crew="")),
            roster_event(SLUG, sample_rows(entries=32)),
            roster_event(YOUTH, sample_rows("Free State Youth Provincial Champs", "LDYC", "Lake Deneys Yacht Club", entries=26, helm="Maximilian Malan", crew="")),
        ]
        table = [
            {"event_name": "420 Nationals", "regatta_id": SLUG, "has_results": True},
            {"event_name": "Dart 18 Nationals", "regatta_id": DART, "has_results": True},
            {"event_name": "Free State Youth Provincial Champs", "regatta_id": YOUTH, "has_results": True},
            {"event_name": "Small Club Open", "regatta_id": SMALL, "has_results": True},
            {"event_name": "Agulhas Race", "regatta_id": None, "has_results": False},
            {"event_name": "Lipton Cup Practice", "regatta_id": "", "has_results": False},
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            roster = [p[0] for p in packs]
            facts = {p[0]["slug"]: p[1] for p in packs}
            heroes = {p[0]["slug"]: stored_hero(root, p[0]["slug"]) for p in packs}
            story = write_issue(
                "2026-09-28",
                MONDAY,
                roster,
                table,
                facts,
                heroes,
                root=root,
                polish=lambda *a, **k: None,
            )
            reports = [a for a in story["articles"] if a.get("type") == "regatta_report"]
            lead = story["articles"][0]
            blob = " ".join(b.get("text") or "" for b in lead["blocks"] if b.get("type") == "paragraph")
            self.assertEqual(lead["headline"], "Last Week's Roundup")
            self.assertEqual(lead["type"], "feature")
            self.assertEqual([a["event_id"] for a in reports], [SLUG, YOUTH, DART, SMALL])
            self.assertEqual(story["unlisted_events"], ["Agulhas Race", "Lipton Cup Practice"])
            self.assertEqual(set(story["needs_external"]), {SLUG, YOUTH, DART, SMALL})
            for name in ("420 Nationals", "Dart 18 Nationals", "Free State Youth Provincial Champs", "Small Club Open", "Agulhas Race", "Lipton Cup Practice"):
                self.assertIn(name, blob)
            self.assertTrue((root / "issues" / "2026-09-28" / "sources" / "weekend-story.json").is_file())
            ctx = {
                "monday": "2026-09-28",
                "slugs": [p[0]["slug"] for p in packs],
                "rows_by_slug": {p[0]["slug"]: sample_rows(p[1]["title"], p[1]["club"], p[1]["club_name"], p[1]["start"], p[1]["end"], p[1]["entries"], p[1]["winner_helm"], p[1].get("winner_crew") or "") for p in packs},
                "table_events": table,
                "articles": story["articles"],
                "roster": {"confirmed": True, "passed_slugs": [p[0]["slug"] for p in packs], "events": roster},
                "facts_by_slug": facts,
                "heroes": heroes,
                "root": str(root),
            }
            run = run_gates(ctx, through=3)
            self.assertEqual(run.step(3).status, "pass", run.summary())
            self.assertTrue(all(e.get("needs_external") for e in run.step(3).events))
            self.assertTrue(all(not e.get("third_party") for e in run.step(3).events))
            self.assertNotIn("scored event", blob)
            self.assertNotIn("also posting results", blob)
            self.assertIn("week_fact", reports[0])

    def test_week_polish_rejects_tally_and_keeps_desk_narrative(self):
        cards = [
            {
                "name": "505 Nationals",
                "winner": "Peter Funke",
                "short_venue": "Aeolians",
                "status": "final",
                "tied_first": True,
                "angle": "tie",
            },
            {
                "name": "Dabchick Gauteng Regionals",
                "winner": "Dylan Hall",
                "short_venue": "Aeolians",
                "status": "final",
                "sweep": True,
                "races": 12,
                "angle": "sweep",
            },
        ]
        facts = {"week_cards": cards, "unlisted": []}
        text, writer = polish_copy(
            "week feature",
            {"events": cards},
            facts,
            "desk draft",
            polish=lambda *a, **k: "4 scored events. The weekend was led by 505 Nationals.",
        )
        self.assertIsNone(text)
        self.assertEqual(writer, "desk")
        good = (
            "A points tie settled the 505 Nationals at Aeolians, where Dylan Hall "
            "also won all 12 races in the Dabchick Gauteng Regionals."
        )
        text, writer = polish_copy(
            "week feature",
            {"events": cards},
            facts,
            "desk draft",
            polish=lambda *a, **k: good,
        )
        self.assertEqual(text, good)
        self.assertEqual(writer, "injected")

    def test_week_polish_api_failure_keeps_desk_narrative(self):
        cards = [{"name": "420 Nationals", "winner": "Dale Rae", "short_venue": "Theewater", "status": "final"}]
        facts = {"week_cards": cards, "unlisted": []}
        with patch.dict("os.environ", {"ROUNDUP_USE_AI": "1", "OPENAI_API_KEY": "sk", "PERPLEXITY_API_KEY": ""}, clear=False):
            with patch("article_write.ai_chat", return_value=("", "official")):
                text, writer = polish_copy("week feature", {"events": cards}, facts, "Dale Rae won the 420 Nationals at Theewater.")
        self.assertIsNone(text)
        self.assertEqual(writer, "desk")


class PublishStopsAfterStory(unittest.TestCase):
    def test_publish_writes_official_articles_and_does_not_claim_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            seed = root / "seed.jpg"
            seed.write_bytes(b"hero-bytes-on-box")
            result = publish(
                MONDAY,
                rebuild=True,
                root=root,
                slugs=[SLUG],
                table_events=[
                    {"event_name": "420 Nationals", "regatta_id": SLUG, "has_results": True},
                    {"event_name": "Agulhas Race", "regatta_id": None, "has_results": False},
                ],
                rows_by_slug={SLUG: sample_rows()},
                hero_hooks={
                    "html": "<html></html>",
                    "extra": [
                        {
                            "url": str(seed),
                            "local_file": str(seed),
                            "source_url": "https://sailingsa.co.za/regatta/" + SLUG,
                            "title": "420 Nationals prizegiving",
                            "seed": True,
                        }
                    ],
                },
                polish=lambda *a, **k: None,
                through=3,
            )
            self.assertEqual(result["action"], "drafted")
            self.assertFalse(result["can_publish"])
            self.assertEqual(result["unlisted"], ["Agulhas Race"])
            self.assertEqual(result["needs_external"], [SLUG])
            story = json.loads((root / "issues" / "2026-09-28" / "issue.json").read_text())
            lead = story["articles"][0]
            blob = " ".join(b.get("text") or "" for b in lead["blocks"] if b.get("type") == "paragraph")
            self.assertEqual(lead["headline"], "Last Week's Roundup")
            self.assertIn("420 Nationals", blob)
            self.assertIn("Agulhas Race", blob)
            report = story["articles"][1]
            self.assertTrue(report["needs_external"])
            self.assertFalse(report["third_party"])
            gates = json.loads((root / "issues" / "2026-09-28" / "sources" / "gates.json").read_text())
            self.assertEqual(gates["steps"][2]["status"], "pass")
            self.assertFalse(gates["can_publish"])
            self.assertFalse((root / "public" / "issues" / "2026-09-28" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
