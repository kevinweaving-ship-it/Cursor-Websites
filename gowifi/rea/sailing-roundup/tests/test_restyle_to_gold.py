#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from restyle_to_gold import GOLD_LOCK, gold_deck, restyle_issue


class RestyleGold(unittest.TestCase):
    def test_refuses_gold_default(self):
        with self.assertRaisesRegex(ValueError, "2026-09-28"):
            restyle_issue(GOLD_LOCK)

    def test_gold_deck_drops_winner_prefix(self):
        deck = gold_deck(
            {"deck": "Lorrian Wells · Dam Bottle Sprints · Henley Midmar Yacht Club · 5 nett · 4 entries"}
        )
        self.assertEqual(deck, "Henley Midmar Yacht Club · 5 nett · 4 entries")

    def test_restyle_writes_gold_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            issue = root / "issues" / "2026-10-19"
            issue.mkdir(parents=True)
            (issue / "issue.json").write_text(
                json.dumps(
                    {
                        "title": "Weekend Sailing Roundup",
                        "articles": [
                            {
                                "id": "sailing-2026-10-19",
                                "type": "feature",
                                "layout": "lead",
                                "headline": "Weekend sailing roundup",
                                "deck": "13–19 October 2026",
                                "blocks": [{"type": "paragraph", "text": "One scored event."}],
                            }
                        ],
                    }
                )
            )
            with patch("restyle_to_gold.ROOT", root), patch("restyle_to_gold.render", lambda _issue: None):
                (root / "public" / "issues" / "2026-10-19").mkdir(parents=True)
                html = "<title>The Weekend Roundup — 2026-10-19</title><style>:root{--accent:#8b6c43}</style>"
                (root / "public" / "issues" / "2026-10-19" / "index.html").write_text(html)
                result = restyle_issue("2026-10-19")
            data = json.loads((issue / "issue.json").read_text())
            self.assertEqual(data["title"], "South African Sailing — The Weekend Roundup")
            self.assertEqual(data["articles"][0]["headline"], "South African Sailing — The Weekend Roundup")
            self.assertEqual(result["action"], "restyled_gold")


if __name__ == "__main__":
    unittest.main()
