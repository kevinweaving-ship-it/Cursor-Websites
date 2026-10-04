"""Portsmouth Yardstick catalogue, class matching, and corrected-time rounding."""
import json
import re
import unittest
from decimal import Decimal
from pathlib import Path

from py_rating.calculation import ROUNDING_RULE, apply_published_rating, corrected_time, parse_elapsed_seconds
from py_rating.catalogue import RatingEntry, load_rya_py_2026
from py_rating.match import build_review, match_entry

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "sailingsa" / "db" / "migrations" / "20261004_rating_catalogue.sql"
SNAPSHOT = ROOT / "py_rating" / "published" / "class_master_snapshot_20261004.json"
REVIEW = ROOT / "py_rating" / "published" / "rya_py_2026_class_review.json"


class CalculationTests(unittest.TestCase):
    def test_formula_and_exact_scratch_boat(self):
        result = corrected_time(
            1000,
            1000,
            system_code="RYA_PY",
            version_label="2026",
            version_number="4",
            source_class_id="12",
            source_class_name="420",
        )
        self.assertEqual(result.formula, "elapsed_seconds * 1000 / py_number")
        self.assertEqual(result.rounding_rule, ROUNDING_RULE)
        self.assertEqual(result.exact_seconds, Decimal(1000))
        self.assertEqual(result.corrected_seconds, 1000)
        self.assertEqual(result.version_label, "2026")
        self.assertEqual(result.version_number, "4")

    def test_published_example_rounds_half_up(self):
        # 47:21 at PY 1013 is 2804.541... seconds, which rounds to 2805.
        self.assertEqual(parse_elapsed_seconds("47:21"), Decimal(2841))
        self.assertEqual(parse_elapsed_seconds("0:47:21"), Decimal(2841))
        self.assertEqual(parse_elapsed_seconds("1:02:03"), Decimal(3723))
        result = corrected_time(
            "47:21",
            1013,
            system_code="RYA_PY",
            version_label="2026",
            version_number="4",
            source_class_id="example",
            source_class_name="example",
        )
        self.assertEqual(result.elapsed_seconds, Decimal(2841))
        self.assertEqual(result.exact_seconds, Decimal(2841) * 1000 / Decimal(1013))
        self.assertGreater(result.exact_seconds, Decimal("2804.5"))
        self.assertLess(result.exact_seconds, Decimal("2804.6"))
        self.assertEqual(result.corrected_seconds, 2805)

    def test_exact_half_second_rounds_up_and_below_half_rounds_down(self):
        half = corrected_time(
            1, 2000,
            system_code="RYA_PY", version_label="2026", version_number="4",
            source_class_id="x", source_class_name="x",
        )
        self.assertEqual(half.exact_seconds, Decimal("0.5"))
        self.assertEqual(half.corrected_seconds, 1)
        one_and_half = corrected_time(
            3, 2000,
            system_code="RYA_PY", version_label="2026", version_number="4",
            source_class_id="x", source_class_name="x",
        )
        self.assertEqual(one_and_half.exact_seconds, Decimal("1.5"))
        self.assertEqual(one_and_half.corrected_seconds, 2)
        below = corrected_time(
            Decimal("10.4"), 1000,
            system_code="RYA_PY", version_label="2026", version_number="4",
            source_class_id="x", source_class_name="x",
        )
        self.assertEqual(below.corrected_seconds, 10)

    def test_ilca_numbers_from_the_2026_list_reproduce_the_version(self):
        publication = load_rya_py_2026()
        expected = {"189": 1218, "190": 1156, "191": 1103}
        for source_id, py_number in expected.items():
            entry = publication.entry_by_source_id(source_id)
            result = apply_published_rating(publication, entry, py_number)
            self.assertEqual(entry.rating_value, py_number)
            self.assertEqual(result.corrected_seconds, 1000)
            self.assertEqual(result.version_label, "2026")
            self.assertEqual(result.version_number, "4")
            self.assertEqual(result.source_class_id, source_id)
            record = result.as_record()
            self.assertEqual(record["py_number"], py_number)
            self.assertEqual(record["exact_seconds"], "1000")
            self.assertEqual(record["version_number"], "4")

    def test_same_number_on_another_version_stays_a_different_record(self):
        first = corrected_time(
            1103, 1103,
            system_code="RYA_PY", version_label="2025", version_number="1",
            source_class_id="191", source_class_name="ILCA 7 / Laser",
        )
        second = corrected_time(
            1103, 1103,
            system_code="RYA_PY", version_label="2026", version_number="4",
            source_class_id="191", source_class_name="ILCA 7 / Laser",
        )
        self.assertEqual(first.corrected_seconds, second.corrected_seconds)
        self.assertNotEqual(first.as_record()["version_label"], second.as_record()["version_label"])
        self.assertNotEqual(first.as_record(), second.as_record())

    def test_rejects_bad_inputs(self):
        kwargs = dict(
            system_code="RYA_PY", version_label="2026", version_number="4",
            source_class_id="12", source_class_name="420",
        )
        with self.assertRaises(ValueError):
            corrected_time(-1, 1000, **kwargs)
        with self.assertRaises(ValueError):
            corrected_time(10, 0, **kwargs)
        with self.assertRaises(TypeError):
            corrected_time(10.5, 1000, **kwargs)
        with self.assertRaises(TypeError):
            corrected_time(10, 1000.0, **kwargs)


class CatalogueTests(unittest.TestCase):
    def test_2026_version_4_list_is_complete_and_unique(self):
        publication = load_rya_py_2026()
        self.assertEqual(publication.publisher, "Royal Yachting Association")
        self.assertEqual(publication.version_label, "2026")
        self.assertEqual(publication.version_number, "4")
        self.assertEqual(publication.effective_from, "2026-04-22")
        self.assertEqual(publication.source_last_update_printed, "22/04/206")
        self.assertEqual(publication.formula, "elapsed_seconds * 1000 / py_number")
        self.assertEqual(publication.rounding_rule, "nearest_second_half_up")
        self.assertEqual(len(publication.entries), 107)
        sections = {}
        for entry in publication.entries:
            sections[entry.list_section] = sections.get(entry.list_section, 0) + 1
            self.assertGreater(entry.rating_value, 0)
        self.assertEqual(sections, {"dinghy_base": 87, "multihull_base": 8, "experimental": 12})
        self.assertEqual(publication.entry_by_source_id("12").rating_value, 1110)
        self.assertEqual(publication.entry_by_source_id("282").rating_value, 1629)
        self.assertEqual(publication.entry_by_source_id("379").rating_value, 1369)
        self.assertEqual(publication.entry_by_source_id("380").rating_value, 1450)

    def test_migration_seeds_the_same_numbers_and_does_not_rewrite_other_tables(self):
        publication = load_rya_py_2026()
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertNotRegex(
            sql,
            r"(?i)(insert into|update|delete from)\s+public\.(classes|class_aliases|results|ranking_standings|standings_recalc_queue)\b",
        )
        self.assertNotIn("class_original", sql.lower())
        self.assertIn("CREATE TABLE IF NOT EXISTS public.rating_catalogue_entry", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS public.rating_time_application", sql)
        for entry in publication.entries:
            self.assertIn(
                f"'{entry.source_class_id}', '{entry.source_class_name}', {entry.crew_count}, "
                f"'{entry.rig}', '{entry.spinnaker}', '{entry.variant}', {entry.rating_value},",
                sql,
            )
        seeded = re.findall(r"^\('(?:dinghy_base|multihull_base|experimental)'", sql, re.M)
        self.assertEqual(len(seeded), 107)


class MatchTests(unittest.TestCase):
    def test_ambiguous_when_name_and_alias_point_at_different_classes(self):
        entry = RatingEntry(
            list_section="dinghy_base",
            source_class_id="1",
            source_class_name="OPTIMIST A",
            crew_count=1,
            rig="U",
            spinnaker="0",
            variant="",
            rating_value=1629,
            change_from_previous=0,
            source_notes="",
        )
        classes = [
            {"class_id": 1, "class_name": "Optimist"},
            {"class_id": 62, "class_name": "Optimist A"},
        ]
        aliases = [{"class_id": 1, "alias": "OPTIMIST A"}]
        review = match_entry(entry, classes, aliases)
        self.assertEqual(review.match_status, "ambiguous")
        self.assertIsNone(review.class_id)
        self.assertEqual(review.candidate_class_ids, (1, 62))

    def test_unmatched_does_not_invent_a_class(self):
        entry = RatingEntry(
            list_section="dinghy_base",
            source_class_id="350",
            source_class_name="SOLO",
            crew_count=1,
            rig="U",
            spinnaker="0",
            variant="",
            rating_value=1139,
            change_from_previous=0,
            source_notes="",
        )
        review = match_entry(entry, [{"class_id": 7, "class_name": "420"}], [])
        self.assertEqual(review.match_status, "unmatched")
        self.assertIsNone(review.class_id)
        self.assertEqual(review.candidate_class_ids, ())

    def test_live_snapshot_links_only_one_existing_class(self):
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        publication = load_rya_py_2026()
        review = build_review(publication, snapshot["classes"], snapshot["aliases"])
        stored = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual(review["counts"], {"matched": 18, "unmatched": 89, "ambiguous": 0})
        self.assertEqual(stored["counts"], review["counts"])
        by_source = {row["source_class_id"]: row for row in review["rows"]}
        ilca4 = by_source["189"]
        self.assertEqual(ilca4["match_status"], "matched")
        self.assertEqual(ilca4["class_id"], 8)
        self.assertEqual(ilca4["class_name"], "ILCA 4")
        self.assertEqual(ilca4["candidate_class_ids"], [8])
        self.assertEqual(ilca4["rating_value"], 1218)
        ilca6 = by_source["190"]
        self.assertEqual(ilca6["class_id"], 45)
        self.assertEqual(ilca6["class_name"], "Ilca 6")
        self.assertEqual(ilca6["candidate_class_ids"], [45])
        ilca7 = by_source["191"]
        self.assertEqual(ilca7["class_id"], 46)
        self.assertEqual(ilca7["candidate_class_ids"], [46])
        self.assertNotIn(8, ilca7["candidate_class_ids"])
        self.assertEqual(by_source["323"]["class_id"], 151)
        self.assertEqual(by_source["324"]["class_id"], 247)
        self.assertEqual(by_source["379"]["class_id"], 75)
        self.assertEqual(by_source["380"]["class_id"], 153)
        self.assertEqual(by_source["95"]["class_id"], 246)
        self.assertEqual(by_source["318"]["match_status"], "unmatched")
        self.assertIn(278, [hint["class_id"] for hint in by_source["318"]["hints"]])
        flying = by_source["142"]
        self.assertEqual(flying["match_status"], "unmatched")
        self.assertIn(206, [hint["class_id"] for hint in flying["hints"]])
        self.assertNotIn(206, flying["candidate_class_ids"])
        for row in review["rows"]:
            self.assertIn(row["match_status"], {"matched", "unmatched", "ambiguous"})
            if row["match_status"] == "matched":
                self.assertEqual(row["candidate_class_ids"], [row["class_id"]])
            else:
                self.assertIsNone(row["class_id"])


if __name__ == "__main__":
    unittest.main()
