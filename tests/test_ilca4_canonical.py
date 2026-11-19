"""ILCA 4 canonical matching. No database and no class creation."""
import hashlib
import importlib.util
import re
import struct
import unittest
from pathlib import Path

import ilca4_canonical as ilca4

ROOT = Path(__file__).resolve().parents[1]
LOGO_SRC_SHA = "0ca195bf0d0f07691a6ddea5e23014fbc9cb49d08bafbff71a0be9e2c88249b7"
LOGO = ROOT / "sailingsa" / "frontend" / "artwork" / "Class Logo" / ilca4.LOGO_FILE
LEGACY_LOGO = ROOT / "sailingsa" / "frontend" / "artwork" / "Class Logo" / ilca4.LEGACY_LOGO_FILE
MIGRATION = ROOT / "sailingsa" / "db" / "migrations" / "20261004_ilca4_canonical.sql"


class Ilca4LabelTests(unittest.TestCase):
    def test_family_labels(self):
        for label in (
            "ILCA 4",
            "ILCA 4.7",
            "ILCA4.7",
            "ILCA 4,7",
            "Laser 4.7",
            "Laser Radial 4.7",
            "ilca-4.7",
            "ilca-47",
            "ilca-4-7",
            "ILCA 4.7 Fleet",
        ):
            self.assertTrue(ilca4.is_ilca4_family_label(label), label)

    def test_does_not_claim_ilca_6_or_7(self):
        for label in (
            "ILCA 6",
            "ILCA 7",
            "Laser Radial",
            "Laser Standard",
            "Laser",
            "radial",
            "ILCA",
            "ilca-6",
            "ilca-7",
        ):
            self.assertFalse(ilca4.is_ilca4_family_label(label), label)
            self.assertFalse(ilca4.is_ilca4_family_slug(label), label)

    def test_search_aliases_keep_radial_on_ilca_6(self):
        aliases = [a.casefold() for a in ilca4.search_aliases()]
        self.assertIn("ilca 4.7", aliases)
        self.assertIn("laser 4.7", aliases)
        self.assertIn("laser radial 4.7", aliases)
        self.assertNotIn("radial", aliases)
        self.assertNotIn("laser radial", aliases)
        self.assertNotIn("ilca 6", aliases)
        self.assertNotIn("ilca 7", aliases)

    def test_single_class_only(self):
        self.assertEqual(ilca4.choose_single_class_row([(8, "Ilca 4.7")]), (8, "Ilca 4.7"))
        self.assertIsNone(ilca4.choose_single_class_row([]))
        self.assertIsNone(ilca4.choose_single_class_row([(8, "Ilca 4.7"), (9, "ILCA 4")]))
        self.assertEqual(
            ilca4.choose_single_class_row([
                {"class_id": 8, "class_name": "ILCA 4"},
                {"class_id": 8, "class_name": "ILCA 4"},
            ]),
            (8, "ILCA 4"),
        )

    def test_slug_redirect_family(self):
        self.assertTrue(ilca4.is_ilca4_family_slug("ilca-4.7"))
        self.assertTrue(ilca4.is_ilca4_family_slug("ilca-4"))
        self.assertFalse(ilca4.is_ilca4_family_slug("ilca-6"))
        # The numeric id is stripped before this helper. The raw id-slug is not a name match.
        self.assertFalse(ilca4.is_ilca4_family_slug("8-ilca-4"))

    def test_canonical_url_slug(self):
        def slug(name):
            s = name.strip().lower().replace(" ", "-")
            s = re.sub(r"[^a-z0-9-]", "", s)
            return s.strip("-")

        self.assertEqual(slug("ILCA 4"), "ilca-4")
        self.assertEqual(slug("Ilca 4.7"), "ilca-47")
        self.assertNotEqual(slug("ILCA 6"), "ilca-4")
        self.assertNotEqual(slug("ILCA 7"), "ilca-4")

    def test_migration_does_not_create_or_delete_results(self):
        sql = MIGRATION.read_text().lower()
        self.assertNotIn("insert into public.classes", sql)
        self.assertNotIn("insert into public.results", sql)
        self.assertNotIn("delete from public.results", sql)
        self.assertNotIn("delete from public.classes", sql)
        self.assertNotRegex(sql, r"set\s+class_original")
        self.assertIn("raise exception", sql)
        self.assertIn("ilca 6", sql)

    def test_logo_bytes_unchanged_and_transparent(self):
        raw = LOGO.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), LOGO_SRC_SHA)
        self.assertEqual(LEGACY_LOGO.read_bytes(), raw)
        self.assertEqual(ilca4.LOGO_FILE, "ILCA-4-Class-Logo.png")
        self.assertTrue(ilca4.LOGO_URL.endswith("ILCA-4.7-Class-Logo.png"))
        self.assertEqual(raw[12:16], b"IHDR")
        _w, _h, bit, color = struct.unpack(">IIBB", raw[16:26])
        self.assertEqual(bit, 8)
        self.assertEqual(color, 6)  # RGBA, transparency retained

    def test_public_path_and_slug_match_live_ilca4_urls(self):
        for name in ("ILCA 4", "ILCA 4.7", "Ilca 4.7", "Laser 4.7", "Laser Radial 4.7"):
            self.assertEqual(ilca4.public_class_path(name), "/class/ilca-4")
        self.assertIsNone(ilca4.public_class_path("ILCA 6"))
        self.assertIsNone(ilca4.public_class_path("ILCA 7"))
        self.assertIsNone(ilca4.public_class_path("420"))
        for slug in ("ilca-4.7", "ilca-47", "ilca-4-7", "ilca-4"):
            self.assertEqual(ilca4.normalise_class_slug(slug), "ilca 4")
        self.assertEqual(ilca4.normalise_class_slug("ilca-6"), "ilca 6")
        self.assertEqual(ilca4.normalise_class_slug("ilca-7"), "ilca 7")
        self.assertEqual(ilca4.normalise_class_slug("420"), "420")

    def test_fleet_catalogue_name_keeps_ilca_6_and_7(self):
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("ILCA 4.7", ""), "ILCA 4")
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("", "ilca-4-7"), "ILCA 4")
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("", "ilca-4.7-fleet"), "ILCA 4")
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("Laser Radial 4.7", "laser-4.7"), "ILCA 4")
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("", "ilca-6"), "ILCA 6")
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("", "ilca-6-16"), "ILCA 6")
        self.assertEqual(ilca4.catalogue_class_name_for_fleet("", "ilca-7"), "ILCA 7")
        self.assertIsNone(ilca4.catalogue_class_name_for_fleet("Open", "open"))
        self.assertIsNone(ilca4.catalogue_class_name_for_fleet("ILCA 6", ""))
        self.assertIsNone(ilca4.catalogue_class_name_for_fleet("ILCA 7", ""))
        self.assertIn("ilca47", [a.casefold() for a in ilca4.search_aliases()])

    def test_logo_cache_bust_keeps_legacy_filename(self):
        src = "/artwork/Class%20Logo/ILCA-4.7-Class-Logo.png"
        shown = ilca4.artwork_url_with_cache_bust(src, ilca4.LOGO_URL)
        self.assertEqual(shown, src + "?v=" + ilca4.LOGO_CACHE_BUST)
        self.assertEqual(ilca4.LOGO_CACHE_BUST, "20261004ilca4")
        self.assertTrue(shown.endswith("ILCA-4.7-Class-Logo.png?v=20261004ilca4"))
        self.assertEqual(ilca4.artwork_url_with_cache_bust(src + "?v=old", ilca4.LOGO_URL), src + "?v=old")
        self.assertEqual(ilca4.artwork_url_with_cache_bust("/assets/logo.png", "/assets/logo.png"), "/assets/logo.png")

    def test_live_patch_preserves_production_ilca4_behaviour(self):
        patch = (ROOT / "sailingsa" / "deploy" / "patches" / "20261004_ilca4_live_api.patch").read_text()
        self.assertIn('EVENT_LOGO_ASSET_BUST = "20261004ilca4"', patch)
        self.assertIn('return "ILCA 4"', patch)
        self.assertIn('return "ILCA 6"', patch)
        self.assertIn('if tail_slug in ("ilca-7",):', patch)
        self.assertNotIn("_FLEET_TAIL_CLASS_SLUG_ALIASES", patch)
        self.assertNotIn("class_original", patch)
        self.assertIn("ilca47", patch)
        guard = (ROOT / "sailingsa" / "deploy" / "deploy_api_verified.sh").read_text()
        self.assertIn("incoming api.py is not the production lineage", guard)
        self.assertIn("ilca4_keep_live_api.sh", guard)
        aliases = _load_class_name_aliases()
        self.assertEqual(aliases.canonical_class_name("ilca 4.7"), "ILCA 4")
        self.assertEqual(aliases.canonical_class_name("ILCA 4"), "ILCA 4")
        self.assertEqual(aliases.canonical_class_name("laser 4.7"), "ILCA 4")
        self.assertEqual(aliases.canonical_class_name("laser radial"), "ILCA 6")
        self.assertEqual(aliases.canonical_class_name("ILCA 6"), "ILCA 6")
        self.assertEqual(aliases.canonical_class_name("laser standard"), "ILCA 7")
        self.assertEqual(aliases.canonical_class_name("ILCA 7"), "ILCA 7")
        self.assertEqual(aliases.canonical_class_name("radial"), "ILCA 6")

    def test_index_display_map_already_says_ilca_4(self):
        for rel in ("index.html", "sailingsa/frontend/index.html"):
            text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            self.assertIn("'ilca 4.7':'ILCA 4'", text)
            self.assertNotIn("'ilca 4.7':'ILCA 4.7'", text)
            self.assertIn("ILCA-4.7-Class-Logo.png", text)
            self.assertIn("'ilca 6':'ILCA 6'", text)


def _load_class_name_aliases():
    path = ROOT / "sailingsa" / "api" / "class_name_aliases.py"
    spec = importlib.util.spec_from_file_location("class_name_aliases", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
