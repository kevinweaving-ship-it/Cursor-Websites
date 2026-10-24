#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from sailingsa.tools.gsc_daily.autofix import decide, evaluate_row, five_xx_count  # noqa: E402


WWW = {
    "id": "www_roundup",
    "url": "https://www.sailingsa.co.za/sailing-roundup/",
    "want_status": 301,
    "location_host": "sailingsa.co.za",
    "fix": "nginx",
}
HOME = {
    "id": "home",
    "url": "https://sailingsa.co.za/home",
    "want_status": 301,
    "location_path": "/",
    "fix": "nginx",
}
SAILORS = {
    "id": "sailors_title",
    "url": "https://sailingsa.co.za/sailors",
    "want_status": 200,
    "title_has": "South African Sailors",
    "fix": "api",
}


class AutofixDecide(unittest.TestCase):
    def test_www_200_needs_nginx(self):
        row = evaluate_row(WWW, {"status": 200, "location": "", "body": b""})
        self.assertFalse(row["ok"])
        self.assertEqual(decide([row]), ["nginx"])

    def test_www_301_apex_ok(self):
        row = evaluate_row(
            WWW,
            {"status": 301, "location": "https://sailingsa.co.za/sailing-roundup/", "body": b""},
        )
        self.assertTrue(row["ok"])
        self.assertEqual(decide([row]), [])

    def test_home_try_files_needs_nginx(self):
        row = evaluate_row(HOME, {"status": 200, "location": "", "body": b"<html>"})
        self.assertFalse(row["ok"])
        self.assertIn("nginx", decide([row]))

    def test_thin_sailors_title_needs_api(self):
        row = evaluate_row(
            SAILORS,
            {"status": 200, "location": "", "body": b"<title>Sailors</title>"},
        )
        self.assertFalse(row["ok"])
        self.assertEqual(decide([row]), ["api"])

    def test_good_sailors_title_ok(self):
        row = evaluate_row(
            SAILORS,
            {"status": 200, "location": "", "body": b"<title>South African Sailors | SailingSA</title>"},
        )
        self.assertTrue(row["ok"])

    def test_five_xx_storm_restarts_api(self):
        probes = [{"first_status": 502, "url": f"https://sailingsa.co.za/sailor/{i}"} for i in range(6)]
        self.assertEqual(five_xx_count(probes), 6)
        self.assertEqual(decide([], five_xx=6), ["restart_api"])

    def test_few_five_xx_no_restart(self):
        self.assertEqual(decide([], five_xx=2), [])


if __name__ == "__main__":
    unittest.main()
