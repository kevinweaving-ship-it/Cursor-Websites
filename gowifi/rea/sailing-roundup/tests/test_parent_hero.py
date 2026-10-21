#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from parent_hero import (
    available_images,
    collect_event_hero,
    inspect_parent,
    pick_best_hero,
    store_on_box,
    store_roster_heroes,
)

SLUG = "2026-09-25-tsc-420-nationals"
PARENT = "https://sailingsa.co.za/regatta/" + SLUG


def facts():
    return {
        "slug": SLUG,
        "title": "420 Nationals",
        "class_name": "420",
        "url": PARENT,
        "fleets": ["420"],
    }


class ParentHero(unittest.TestCase):
    def test_inspect_parent_finds_og_and_gallery(self):
        html = (
            "<html><head><title>420 Nationals</title>"
            f'<meta property="og:image" content="{PARENT}/og-prizegiving.jpg">'
            "</head><body><main>"
            '<img src="/gallery/on-water.jpg" alt="420 Nationals on the water">'
            '<img src="/artwork/club-logo.png" alt="club logo">'
            "</main></body></html>"
        )
        found = inspect_parent(PARENT, html=html)
        self.assertTrue(found["has_media"])
        urls = " ".join(item["url"] for item in found["images"])
        self.assertIn("og-prizegiving.jpg", urls)
        self.assertIn("on-water.jpg", urls)
        self.assertNotIn("club-logo", urls)
        self.assertTrue(all(item.get("from_parent") for item in found["images"]))

    def test_parent_without_photos_is_recorded(self):
        found = inspect_parent(PARENT, html="<html><body><table><tr><td>1</td></tr></table></body></html>")
        self.assertFalse(found["has_media"])
        self.assertEqual(found["images"], [])

    def test_picker_chooses_prizegiving_over_logo(self):
        best, ranked = pick_best_hero(
            [
                {"url": "https://example/club-logo.png", "source_url": PARENT, "title": "club logo"},
                {
                    "url": "https://example/420-nationals-prizegiving.jpg",
                    "source_url": PARENT,
                    "title": "420 Nationals prizegiving",
                    "from_parent": True,
                },
            ],
            facts(),
        )
        self.assertIsNotNone(best)
        self.assertIn("prizegiving", best["url"])
        self.assertGreater(best["hero_score"], 40)

    def test_store_writes_hero_on_the_box(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            stored = store_on_box(
                "2026-09-28",
                SLUG,
                {"url": "https://example/prize.jpg", "source_url": PARENT, "title": "prize", "hero_score": 90},
                b"photo-bytes-on-box",
                root=root,
            )
            self.assertEqual(stored["status"], "pass")
            self.assertTrue((root / "issues" / "2026-09-28" / "media" / f"{SLUG}-hero.jpg").is_file())
            self.assertTrue((root / "public" / "issues" / "2026-09-28" / "media" / f"{SLUG}-hero.jpg").is_file())

    def test_collect_uses_parent_then_stores_seed_if_needed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            seed = root / "seed.jpg"
            seed.write_bytes(b"seed-photo-bytes")
            rec = {"slug": SLUG, "url": PARENT, "status": "pass", "name": "420 Nationals"}
            pack = collect_event_hero(
                "2026-09-28",
                rec,
                facts(),
                root=root,
                html="<html><body>results only</body></html>",
                extra=[{"url": str(seed), "local_file": str(seed), "source_url": PARENT, "title": "420 Nationals", "seed": True}],
            )
            self.assertEqual(pack["status"], "pass", pack)
            self.assertFalse(pack["parent_has_media"])
            self.assertTrue((root / "issues" / "2026-09-28" / "sources" / f"{SLUG}-parent-media.json").is_file())
            self.assertTrue((root / "issues" / "2026-09-28" / "sources" / f"{SLUG}-hero.json").is_file())
            hero = json.loads((root / "issues" / "2026-09-28" / "sources" / f"{SLUG}-hero.json").read_text())
            self.assertEqual(hero["local_path"], f"media/{SLUG}-hero.jpg")

    def test_roster_store_skips_failed_events(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            seed = root / "seed.jpg"
            seed.write_bytes(b"seed-photo-bytes")
            events = [
                {"slug": SLUG, "url": PARENT, "status": "pass", "name": "420 Nationals"},
                {"slug": "2026-09-24-hmyc-dart-18-nationals", "url": "https://sailingsa.co.za/regatta/x", "status": "fail"},
            ]
            heroes = store_roster_heroes(
                "2026-09-28",
                events,
                {SLUG: facts()},
                root=root,
                html="<html></html>",
                extra=[{"url": str(seed), "local_file": str(seed), "source_url": PARENT, "title": "420 Nationals", "seed": True}],
            )
            self.assertIn(SLUG, heroes)
            self.assertNotIn("2026-09-24-hmyc-dart-18-nationals", heroes)

    def test_available_images_parent_first(self):
        parent = [{"url": "https://a/parent.jpg", "from_parent": True}]
        extra = [{"url": "https://b/extra.jpg"}]
        got = available_images(facts(), parent, extra=extra)
        self.assertEqual(got[0]["url"], "https://a/parent.jpg")
        self.assertEqual([i["url"] for i in got][1:], ["https://b/extra.jpg"])


if __name__ == "__main__":
    unittest.main()
