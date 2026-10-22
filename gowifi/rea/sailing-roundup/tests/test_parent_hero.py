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
    content_hash,
    event_search_queries,
    images_from_html,
    inspect_parent,
    pick_best_hero,
    score_hero,
    select_images,
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

    def test_external_junk_is_not_a_hero(self):
        dam = {
            "url": "https://storage.googleapis.com/x/how-are-river-dams-built.jpg",
            "source_url": "https://example.com/how-are-river-dams-built.html",
            "title": "How river dams are built",
            "from_external": True,
        }
        ad = {
            "url": "https://lowendtalk.com/ad.jpg",
            "source_url": "https://lowendtalk.com/discussion/191501/real-deals-here-win-big",
            "title": "REAL DEALS HERE -- WIN BIG WITH THOUSANDS IN PRIZES",
            "from_external": True,
        }
        self.assertLess(score_hero(dam, {"title": "Dam Bottle Sprints", "slug": "2026-10-10-hmyc-dam-bottle-sprints"}), 0)
        self.assertLess(score_hero(ad, {"title": "KZN Mirror Regionals", "winner": "Mark Flack"}), 0)

    def test_empty_parent_is_inspected_not_a_hard_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            pack = collect_event_hero(
                "2026-09-28",
                {"slug": SLUG, "url": PARENT, "status": "pass", "name": "420 Nationals"},
                facts(),
                root=root,
                html="<html><body>results only</body></html>",
                extra=[],
                use_external=False,
            )
            self.assertEqual(pack["status"], "empty")
            self.assertTrue(pack["inspected"])
            self.assertTrue(pack["empty"])
            self.assertFalse(pack["parent_has_media"])

    def test_available_images_parent_first(self):
        parent = [{"url": "https://a/parent.jpg", "from_parent": True}]
        extra = [{"url": "https://b/extra.jpg"}]
        got = available_images(facts(), parent, extra=extra)
        self.assertEqual(got[0]["url"], "https://a/parent.jpg")
        self.assertEqual([i["url"] for i in got][1:], ["https://b/extra.jpg"])

    def test_505_collage_keeps_photo_panels_only(self):
        from io import BytesIO

        from PIL import Image

        from parent_hero import _collage_panels

        buf = BytesIO()
        Image.new("RGB", (2160, 3840), (20, 40, 80)).save(buf, format="JPEG", quality=85)
        panels = _collage_panels(
            "2026-09-24-ayc-505-nationals",
            buf.getvalue(),
            {"url": "https://rsa505.org.za/images/20261013_101619-COLLAGE.jpg", "title": "collage", "hero_score": 50},
        )
        labels = [p["title"] for p in panels]
        self.assertEqual(labels, ["505 Nationals prizegiving", "505 Nationals on-water racing"])
        self.assertNotIn([0, 1280, 2160, 1280], [p["source_region"] for p in panels])

    def test_srcset_and_lazy_images_are_harvested(self):
        html = (
            "<html><body><main>"
            '<img src="/tiny.jpg" srcset="/tiny.jpg 400w, /full-on-water.jpg 1600w" alt="on water">'
            '<img data-src="/lazy-prizegiving.jpg" alt="prizegiving">'
            "</main></body></html>"
        )
        found = images_from_html(PARENT, html)
        urls = " ".join(item["url"] for item in found)
        self.assertIn("full-on-water.jpg", urls)
        self.assertIn("lazy-prizegiving.jpg", urls)

    def test_event_search_queries_use_exact_name_year_venue(self):
        queries = event_search_queries(
            {"title": "Dabchick Gauteng Regionals", "start": "2026-09-24", "club_name": "Aeolians Yacht Club"}
        )
        self.assertTrue(any("Dabchick Gauteng Regionals 2026 Aeolians" in q for q in queries))
        self.assertTrue(any(q.endswith("photos") for q in queries))

    def test_user_selected_order_overrides_score(self):
        chosen = select_images(
            [
                {"url": "https://a/on-water.jpg", "title": "on water", "hero_score": 90, "content_hash": "1"},
                {"url": "https://a/u17.jpg", "title": "U17 boys", "hero_score": 40, "content_hash": "2"},
                {
                    "url": "https://www.facebook.com/share/1DGs9FyLwT/boat.jpg",
                    "source_url": "https://www.facebook.com/share/1DGs9FyLwT/",
                    "title": "boat",
                    "hero_score": 40,
                    "user_selected": True,
                    "content_hash": "3",
                },
                {"url": "https://a/prize.jpg", "title": "overall winners prizegiving", "hero_score": 80, "content_hash": "4"},
            ],
            SLUG,
        )
        titles = [item["title"] for item in chosen]
        self.assertEqual(titles[:3], ["420 Nationals overall winners", "420 Nationals U17 boys", "420 Nationals boat"])

    def test_duplicate_hash_and_logo_are_rejected(self):
        digest = content_hash(b"same-photo")
        chosen = select_images(
            [
                {"url": "https://a/one.jpg", "title": "prizegiving", "hero_score": 90, "content_hash": digest},
                {"url": "https://b/copy.jpg", "title": "prizegiving copy", "hero_score": 90, "content_hash": digest},
                {"url": "https://c/logo.png", "title": "logo", "hero_score": 90, "content_hash": "logo", "vision": {"category": "logo", "role": "reject"}},
            ],
            SLUG,
            analyses={digest: {"category": "prizegiving", "role": "supporting"}, "logo": {"category": "logo", "role": "reject"}},
        )
        self.assertEqual(len(chosen), 1)

    def test_failed_discovery_keeps_verified_previous(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            folder = root / "issues" / "2026-09-28" / "media"
            folder.mkdir(parents=True)
            (folder / f"{SLUG}.jpg").write_bytes(b"verified-photo-bytes")
            pack = collect_event_hero(
                "2026-09-28",
                {"slug": SLUG, "url": PARENT, "status": "pass", "name": "420 Nationals"},
                facts(),
                root=root,
                html="<html><body>results only</body></html>",
                extra=[],
                use_external=False,
                analyze=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("vision down")),
            )
            self.assertEqual(pack["status"], "pass")
            self.assertTrue(pack.get("preserved_previous") or pack.get("images"))
            self.assertTrue((root / "issues" / "2026-09-28" / "media" / f"{SLUG}-hero.jpg").is_file())


if __name__ == "__main__":
    unittest.main()
