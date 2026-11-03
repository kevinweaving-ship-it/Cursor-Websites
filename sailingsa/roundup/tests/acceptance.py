"""Acceptance tests for edition 2026-10-26 (playbook T3, T5, T7–T10, T12, T14, T15)."""

from __future__ import annotations

import unittest
from datetime import date

from sailingsa.roundup.factsheet import build_factsheet
from sailingsa.roundup.ingest import load_week_bundle
from sailingsa.roundup.pipeline import build_edition
from sailingsa.roundup.week import edition_window, select_week_events


class WeekOwnership(unittest.TestCase):
    def test_monday_edition_covers_previous_mon_sun(self):
        start, end = edition_window(date(2026, 10, 26))
        self.assertEqual(start.isoformat(), "2026-10-19")
        self.assertEqual(end.isoformat(), "2026-10-25")

    def test_df95_belongs_to_10_26_not_10_19(self):
        events = [
            {
                "event_name": "2026 DF 95 Global Championship",
                "start_date": "2026-10-16",
                "end_date": "2026-10-23",
                "category": None,
                "regatta_id": None,
            }
        ]
        this = select_week_events(events, date(2026, 10, 26))
        prev = select_week_events(events, date(2026, 10, 19))
        self.assertEqual(len(this["owned"]), 1)
        self.assertEqual(len(prev["owned"]), 0)


class Edition20261026(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_edition("2026-10-26", live=False)

    def test_df95_leads(self):
        self.assertTrue(self.payload["cards"][0]["event_id"].startswith("2026-df95"))
        self.assertIn("DF95", self.payload["lead"]["headline"])

    def test_nw_youth_awaiting_not_card(self):
        awaiting_ids = [s["event_id"] for s in self.payload["awaiting"]]
        card_ids = [s["event_id"] for s in self.payload["cards"]]
        self.assertTrue(any("nw-youth" in i for i in awaiting_ids))
        self.assertFalse(any("nw-youth" in i for i in card_ids))

    def test_ullman_not_provisional(self):
        ullman = next(s for s in self.payload["cards"] if "ullman" in s["event_id"])
        self.assertEqual(ullman["status"]["status"], "series_final")
        self.assertNotIn("provisional", ullman["copy"]["headline"].lower())
        self.assertNotIn("DART 18", ullman["copy"]["kicker"])
        self.assertNotIn("23 May", ullman["copy"]["kicker"] + ullman["copy"]["paras"][0])

    def test_dam_bottle_py_and_angles(self):
        dam = next(s for s in self.payload["cards"] if "dam-bottle" in s["event_id"])
        self.assertIn("PY (handicap)", dam["class_tags"])
        blob = " ".join(dam["copy"]["paras"])
        self.assertIn("Alistair Clulow", blob)
        self.assertIn("R1", blob)
        self.assertIn("consistency", blob.lower())
        self.assertIn("Zane Gaze", " ".join(p.get("crew") or "" for f in dam["fleets"] for p in f["top3"]))

    def test_no_raw_labels(self):
        text = self.payload["lead"]["excerpt"] + self.payload["lead"]["headline"]
        for sheet in self.payload["cards"]:
            text += sheet["copy"]["headline"] + sheet["copy"]["kicker"] + "".join(sheet["copy"]["paras"])
        self.assertNotIn("Series overall (23 May", text)
        self.assertNotIn("Vogelvlei - VYC", text)
        self.assertNotIn("Henley Midmar - HMYC", text)

    def test_sources_and_conflict_note(self):
        df95 = next(s for s in self.payload["cards"] if "df95" in s["event_id"])
        urls = " ".join(s["url"] for s in df95["sources"])
        self.assertTrue("radiosailing.org.au" in urls or "mysailingresults.com" in urls)
        self.assertTrue(df95["conflicts"])
        blob = " ".join(df95["copy"]["paras"])
        self.assertIn("71", blob)
        self.assertIn("20", blob)

    def test_feed_and_cards_match_live_contract(self):
        feed = self.payload["feed_item"]
        for key in ("title", "headline", "url", "excerpt", "published_at", "image", "source", "category"):
            self.assertIn(key, feed)
        self.assertTrue(feed["url"].endswith("/sailing-roundup/issues/2026-10-26/"))
        issue = self.payload["cards_issue"]
        self.assertEqual(issue["html"], "issues/2026-10-26/")
        self.assertEqual(issue["cards"][0]["id"], "2026-df95-global-championship")

    def test_gates_and_idempotent(self):
        self.assertEqual(self.payload["gate_failures"], [], msg=self.payload["gate_failures"])
        again = build_edition("2026-10-26", live=False)
        self.assertEqual(self.payload["paths"]["hash"], again["paths"]["hash"])

    def test_conflict_detector_on_fixtures(self):
        bundle = load_week_bundle("2026-10-26", live=False)
        df95 = next(i for i in bundle["items"] if "df95" in i["event_id"])
        sheet = build_factsheet(df95, date(2026, 10, 26), bundle["sources"])
        self.assertTrue(sheet["conflicts"])
        fields = {c["field"] for c in sheet["conflicts"]}
        self.assertIn("entries", fields)
        self.assertIn("races_sailed", fields)


if __name__ == "__main__":
    unittest.main()
