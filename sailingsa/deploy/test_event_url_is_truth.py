import unittest

from event_url_is_truth import (
    event_child_href,
    event_child_slug_from_labels,
    slug_aliases_for_block,
)


class EventUrlIsTruthTests(unittest.TestCase):
    def test_ilca4_uses_event_sheet_name_not_catalogue(self):
        slug = event_child_slug_from_labels(
            class_original="ILCA 4",
            class_canonical="Ilca 4.7",
            block_id="2026-09-13-zvyc-cape-classic:ilca-4.7-fleet",
        )
        self.assertEqual(slug, "ilca-4")

    def test_open_mixed_aliases_include_boat_classes(self):
        aliases = slug_aliases_for_block(
            class_original="Open",
            class_canonical="Open",
            block_id="2026-09-13-zvyc-cape-classic:open",
            extra_class_names=["420", "Sonnet", "Topaz", "Fireball"],
        )
        self.assertIn("open", aliases)
        self.assertIn("420", aliases)
        self.assertIn("sonnet", aliases)
        self.assertIn("topaz", aliases)
        self.assertIn("fireball", aliases)

    def test_child_href_is_under_event_url(self):
        href = event_child_href("2026-09-13-zvyc-cape-classic", "ilca-4")
        self.assertEqual(
            href, "/regatta/2026-09-13-zvyc-cape-classic/class-ilca-4"
        )

    def test_mirror_has_no_alias_when_fleet_gone(self):
        aliases = slug_aliases_for_block(
            class_original="Extra",
            block_id="2026-09-13-zvyc-cape-classic:extra-fleet",
        )
        self.assertNotIn("mirror", aliases)
        self.assertIn("extra", aliases)


if __name__ == "__main__":
    unittest.main()
