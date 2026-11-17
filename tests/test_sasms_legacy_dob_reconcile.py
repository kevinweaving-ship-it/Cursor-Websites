"""Offline unit tests for authorised SAS DOB reconciliation rules.

No live DB, no scraper, no production writes.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "sailingsa" / "scripts" / "sasms_dob_reconcile_lib.py"
SCRIPT = ROOT / "sailingsa" / "scripts" / "sasms_legacy_dob_reconcile.py"
SCRIPTS_DIR = str(ROOT / "sailingsa" / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # required for @dataclass under exec_module
    spec.loader.exec_module(mod)
    return mod


lib = _load("sasms_dob_reconcile_lib", LIB)
script = _load("sasms_legacy_dob_reconcile", SCRIPT)


class NameAndIdTests(unittest.TestCase):
    def test_exact_sas_id_normalizes_trim_only(self):
        self.assertEqual(lib.normalize_sas_id(" 355 "), "355")
        self.assertEqual(lib.normalize_sas_id("00355"), "00355")

    def test_names_match_full_and_parts(self):
        src = lib.SourceRecord(sas_id="1", first_name="Arin", last_name="Weaving")
        db = lib.DbSailor(sas_id="1", full_name="Arin Weaving")
        self.assertTrue(lib.names_match(src, db))
        db2 = lib.DbSailor(sas_id="1", first_name="Other", last_name="Person", full_name="Other Person")
        self.assertFalse(lib.names_match(src, db2))


class DecisionMatrixTests(unittest.TestCase):
    def test_ignore_lapsed(self):
        src = lib.SourceRecord(
            sas_id="10",
            first_name="A",
            last_name="B",
            date_of_birth=date(2000, 1, 2),
            membership_status="Lapsed",
        )
        db = lib.DbSailor(sas_id="10", first_name="A", last_name="B")
        d = lib.decide(src, db)
        self.assertEqual(d.action, "ignore")
        self.assertIn("ignored_lapsed", d.flags)

    def test_preserve_existing_dob_on_conflict(self):
        src = lib.SourceRecord(
            sas_id="11",
            first_name="Ada",
            last_name="Lovelace",
            date_of_birth=date(1999, 5, 5),
        )
        db = lib.DbSailor(
            sas_id="11",
            first_name="Ada",
            last_name="Lovelace",
            date_of_birth=date(2001, 1, 1),
            year_of_birth=2001,
        )
        d = lib.decide(src, db)
        self.assertEqual(d.action, "flag")
        self.assertIn("preserve_existing_dob", d.flags)
        self.assertIn("birth_year_discrepancy", d.flags)
        self.assertEqual(d.preserve_date_of_birth, date(2001, 1, 1))
        self.assertIsNone(d.set_date_of_birth)

    def test_preserve_yob_on_year_conflict(self):
        src = lib.SourceRecord(
            sas_id="12",
            first_name="Ada",
            last_name="Lovelace",
            year_of_birth=1990,
        )
        db = lib.DbSailor(
            sas_id="12",
            first_name="Ada",
            last_name="Lovelace",
            year_of_birth=1991,
        )
        d = lib.decide(src, db)
        self.assertEqual(d.action, "flag")
        self.assertIn("preserve_existing_yob", d.flags)
        self.assertEqual(d.preserve_year_of_birth, 1991)
        self.assertIsNone(d.set_year_of_birth)

    def test_fill_dob_when_yob_matches(self):
        src = lib.SourceRecord(
            sas_id="13",
            first_name="Ada",
            last_name="Lovelace",
            date_of_birth=date(1991, 3, 4),
        )
        db = lib.DbSailor(
            sas_id="13",
            first_name="Ada",
            last_name="Lovelace",
            year_of_birth=1991,
        )
        d = lib.decide(src, db)
        self.assertEqual(d.action, "apply")
        self.assertEqual(d.set_date_of_birth, date(1991, 3, 4))
        self.assertEqual(d.preserve_year_of_birth, 1991)

    def test_set_yob_only_when_empty(self):
        src = lib.SourceRecord(
            sas_id="14",
            first_name="Ada",
            last_name="Lovelace",
            year_of_birth=1992,
        )
        db = lib.DbSailor(sas_id="14", first_name="Ada", last_name="Lovelace")
        d = lib.decide(src, db)
        self.assertEqual(d.action, "apply")
        self.assertEqual(d.reason, "set_yob_only")
        self.assertEqual(d.set_year_of_birth, 1992)
        self.assertIsNone(d.set_date_of_birth)

    def test_identity_flag_does_not_apply(self):
        src = lib.SourceRecord(
            sas_id="15",
            first_name="Wrong",
            last_name="Person",
            date_of_birth=date(2000, 1, 1),
        )
        db = lib.DbSailor(sas_id="15", first_name="Ada", last_name="Lovelace")
        d = lib.decide(src, db)
        self.assertEqual(d.action, "flag")
        self.assertIn("identity_discrepancy", d.flags)
        self.assertIsNone(d.set_date_of_birth)

    def test_missing_sas_id(self):
        src = lib.SourceRecord(sas_id="99999", first_name="X", last_name="Y", year_of_birth=2000)
        d = lib.decide(src, None)
        self.assertEqual(d.action, "flag")
        self.assertEqual(d.reason, "sas_id_not_found")


class OfflineRunnerTests(unittest.TestCase):
    def test_dry_run_offline_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            dataset = tdir / "auth.csv"
            dataset.write_text(
                "sas_id,first_name,last_name,date_of_birth,year_of_birth,membership_status\n"
                "13,Ada,Lovelace,1991-03-04,1991,\n"
                "12,Ada,Lovelace,,1990,\n"
                "77,Ghost,Sailor,2000-01-01,,Lapsed\n",
                encoding="utf-8",
            )
            dbjson = tdir / "db.json"
            dbjson.write_text(
                json.dumps(
                    [
                        {
                            "sa_sailing_id": "13",
                            "first_name": "Ada",
                            "last_name": "Lovelace",
                            "full_name": "Ada Lovelace",
                            "year_of_birth": 1991,
                        },
                        {
                            "sa_sailing_id": "12",
                            "first_name": "Ada",
                            "last_name": "Lovelace",
                            "full_name": "Ada Lovelace",
                            "year_of_birth": 1991,
                        },
                    ]
                ),
                encoding="utf-8",
            )
            audit = tdir / "audit.jsonl"
            ckpt = tdir / "ckpt.json"
            rc = script.main(
                [
                    "--dataset",
                    str(dataset),
                    "--offline-db-json",
                    str(dbjson),
                    "--audit-log",
                    str(audit),
                    "--checkpoint",
                    str(ckpt),
                ]
            )
            self.assertEqual(rc, 0)
            lines = [json.loads(x) for x in audit.read_text().splitlines() if x.strip()]
            actions = [x.get("action") for x in lines if "action" in x]
            self.assertIn("apply", actions)
            self.assertIn("flag", actions)
            self.assertIn("ignore", actions)

    def test_apply_refused_without_production_flag(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            dataset = tdir / "auth.csv"
            dataset.write_text(
                "sas_id,first_name,last_name,year_of_birth\n14,Ada,Lovelace,1992\n",
                encoding="utf-8",
            )
            dbjson = tdir / "db.json"
            dbjson.write_text(
                json.dumps(
                    [
                        {
                            "sa_sailing_id": "14",
                            "first_name": "Ada",
                            "last_name": "Lovelace",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            rc = script.main(
                [
                    "--dataset",
                    str(dataset),
                    "--offline-db-json",
                    str(dbjson),
                    "--audit-log",
                    str(tdir / "a.jsonl"),
                    "--checkpoint",
                    str(tdir / "c.json"),
                    "--apply",
                    "--expected-sha256",
                    "0" * 64,
                ]
            )
            self.assertEqual(rc, 4)


if __name__ == "__main__":
    unittest.main()
