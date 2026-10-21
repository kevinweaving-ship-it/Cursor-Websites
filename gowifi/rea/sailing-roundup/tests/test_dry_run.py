#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dry_run import markdown_report, mondays_to_run, october_mondays, summarize_issue
from parent_hero import download_hero_bytes


class DryRunHelpers(unittest.TestCase):
    def test_october_2026_mondays(self):
        self.assertEqual(
            october_mondays(2026),
            [dt.date(2026, 10, 5), dt.date(2026, 10, 12), dt.date(2026, 10, 19), dt.date(2026, 10, 26)],
        )

    def test_last_week_from_21_oct_is_19(self):
        days = mondays_to_run(dt.date(2026, 10, 21), last_week=True)
        self.assertEqual(days, [dt.date(2026, 10, 19)])

    def test_october_up_to_today_skips_future(self):
        days = mondays_to_run(dt.date(2026, 10, 21), october=2026)
        self.assertEqual(days, [dt.date(2026, 10, 5), dt.date(2026, 10, 12), dt.date(2026, 10, 19)])

    def test_summarize_and_markdown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            issue = root / "issues" / "2026-10-19"
            source = issue / "sources"
            source.mkdir(parents=True)
            (source / "events-weekend.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {"event_name": "KZN Mirror Regionals", "regatta_id": "2026-10-17-pyc-kzn-mirror-regionals", "has_results": True, "start_date": "2026-10-17", "end_date": "2026-10-18"},
                            {"event_name": "Agulhas Race", "regatta_id": None, "has_results": False, "start_date": "2026-10-17", "end_date": "2026-10-18"},
                        ]
                    }
                )
            )
            (source / "weekend-roster.json").write_text(
                json.dumps({"events": [{"slug": "2026-10-17-pyc-kzn-mirror-regionals", "name": "KZN Mirror Regionals", "status": "pass", "entries": 12, "winner": "Pat Helm"}]})
            )
            (source / "gates.json").write_text(
                json.dumps(
                    {
                        "can_publish": False,
                        "steps": [
                            {"step": 1, "name": "weekend_roster", "status": "pass", "errors": []},
                            {"step": 2, "name": "media", "status": "fail", "errors": ["no hero stored on box"]},
                            {"step": 3, "name": "story", "status": "blocked", "errors": ["blocked until media PASSes"]},
                        ],
                    }
                )
            )
            (issue / "issue.json").write_text(
                json.dumps(
                    {
                        "unlisted_events": ["Agulhas Race"],
                        "articles": [
                            {"type": "feature", "headline": "Last Week's Roundup", "deck": "17–18 October 2026", "blocks": [{"type": "paragraph", "text": "The weekend was led by KZN Mirror Regionals."}]},
                            {
                                "type": "regatta_report",
                                "headline": "Pat Helm wins KZN Mirror Regionals",
                                "deck": "12 entries",
                                "event_id": "2026-10-17-pyc-kzn-mirror-regionals",
                                "blocks": [
                                    {"type": "image", "url": "media/hero.jpg", "caption": "Prizegiving."},
                                    {"type": "paragraph", "text": "Pat Helm won at Point Yacht Club [1]."},
                                ],
                            },
                        ],
                    }
                )
            )
            week = summarize_issue(dt.date(2026, 10, 19), root)
            self.assertEqual(week["ok_through"], 1)
            empty = summarize_issue(dt.date(2026, 10, 5), root)
            self.assertEqual(empty["ok_through"], 0)
            self.assertEqual(week["articles"][0]["headline"], "Pat Helm wins KZN Mirror Regionals")
            self.assertEqual(week["articles"][0]["image"]["url"], "media/hero.jpg")
            self.assertEqual(week["unlisted"], ["Agulhas Race"])
            md = markdown_report({"ran_at": "now", "weeks": [week]})
            self.assertIn("PASS", md)
            self.assertIn("FAIL", md)
            self.assertIn("Pat Helm wins KZN Mirror Regionals", md)

    def test_download_hero_bytes_reads_local_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "hero.jpg"
            path.write_bytes(b"photo")
            self.assertEqual(download_hero_bytes({"local_file": str(path)}), b"photo")


if __name__ == "__main__":
    unittest.main()
