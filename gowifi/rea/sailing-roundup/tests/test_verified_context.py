import json
import pathlib
import tempfile
import unittest

from verified_context import attach_verified_context, build_verified_articles


def _row(place, name, country, fleet, nett, fleetpos="1"):
    return {
        "comppos": str(place),
        "compname": name,
        "compregcountry": country,
        "fleet": fleet,
        "fleetpos": fleetpos,
        "nettScore": nett,
        "results": {f"r{i}": "1.0" for i in range(1, 21)},
    }


RESULTS = {
    "event": {
        "eventname": "2026 DF95 Global Championship",
        "eventstartdate": "2026-10-16 00:00:00",
        "eventenddate": "2026-10-23 00:00:00",
    },
    "results": [
        _row(1, "Craig Richards", "GBR", "G", "29.0"),
        _row(2, "Ulf Lindberg", "SWE", "S", "45.4", "2"),
        _row(3, "Odd Ornulf Stray", "NOR", "G", "60.0", "3"),
        _row(10, "Roy Gardener", "RSA", "G", "91.0", "10"),
        _row(18, "Phil Burgess", "AUS", "S", "80.0", "1"),
        _row(35, "John Wyatt", "AUS", "B", "90.0", "1"),
        _row(62, "Brian Schneider", "AUS", "C", "100.0", "11"),
    ],
}
STORY = (
    "Craig Richards won. Ulf Lindberg was next. "
    "Phil Burgess claiming the Silver Fleet title and finishing 18th overall. "
    "The Bronze Fleet provided another story, with John Wyatt taking the division victory. "
    "In the Copper Fleet, Brian Schneider (62nd). Gold Fleet."
)
CALENDAR = [{
    "event_name": "2026 DF 95 Global Championship",
    "start_date": "2026-10-17",
    "end_date": "2026-10-23",
    "regatta_id": None,
    "has_results": False,
}]


class VerifiedContextTest(unittest.TestCase):
    def test_df95_podium_and_south_african_placing(self):
        pages = {
            "https://mysailingresults.com/api/results/get_results.php?eventid=22056": json.dumps(RESULTS),
            "https://radiosailing.org.au/news/492": STORY + '<img src="/news/dfglob1-test.png">',
        }

        def fetch(url):
            if url not in pages:
                raise OSError(url)
            return pages[url]

        def fetch_bytes(url):
            self.assertIn("dfglob1", url)
            return b"\x89PNG\r\n\x1a\n" + b"x" * 20, "image/png"

        with tempfile.TemporaryDirectory() as tmp:
            articles = build_verified_articles(
                "2026-10-26", CALENDAR, root=pathlib.Path(tmp), fetch=fetch, fetch_bytes=fetch_bytes
            )
        self.assertEqual(len(articles), 1)
        text = " ".join(block["text"] for block in articles[0]["blocks"] if block["type"] == "paragraph")
        self.assertIn("Craig Richards (GBR) won", text)
        self.assertIn("Ulf Lindberg (SWE) was second on 45.4", text)
        self.assertIn("Odd Ornulf Stray (NOR) third on 60", text)
        self.assertIn("10th Roy Gardener, Gold fleet", text)
        self.assertNotIn("11th", text)
        self.assertTrue(any(block.get("url", "").endswith(".png") for block in articles[0]["blocks"]))

    def test_keeps_verified_article_when_recheck_fails_and_skips_scored_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story = {"articles": [{"type": "regatta_report", "event_id": "tour", "headline": "Tour de Vlei", "week_fact": {"name": "2026 Tour de Vlei"}}]}
            first = attach_verified_context("2026-10-26", story, CALENDAR, root=root, fetch=lambda url: {
                "https://mysailingresults.com/api/results/get_results.php?eventid=22056": json.dumps(RESULTS),
                "https://radiosailing.org.au/news/492": STORY,
            }[url], fetch_bytes=lambda url: (_ for _ in ()).throw(OSError("no image")))
            self.assertEqual(len(first["articles"]), 2)

            def down(_url):
                raise OSError("offline")

            again = attach_verified_context("2026-10-26", {"articles": story["articles"][:1]}, CALENDAR, root=root, fetch=down)
            briefs = [article for article in again["articles"] if article["type"] == "brief"]
            self.assertEqual(len(briefs), 1)
            self.assertIn("Roy Gardener", briefs[0]["blocks"][-1]["text"])

    def test_refuses_placings_when_dates_do_not_match(self):
        bad = json.loads(json.dumps(RESULTS))
        bad["event"]["eventenddate"] = "2026-10-20 00:00:00"

        def fetch(url):
            if "get_results" in url:
                return json.dumps(bad)
            return STORY

        with tempfile.TemporaryDirectory() as tmp:
            articles = build_verified_articles("2026-10-26", CALENDAR, root=pathlib.Path(tmp), fetch=fetch, fetch_bytes=lambda url: (b"", ""))
        self.assertEqual(articles, [])


if __name__ == "__main__":
    unittest.main()
