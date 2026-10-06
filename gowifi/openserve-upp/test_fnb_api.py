#!/usr/bin/env python3
import unittest
from pathlib import Path

import fnb_api


class FnbApi(unittest.TestCase):
    def test_not_ready_without_keys(self):
        st = fnb_api.status({"FNB_CLIENT_ID": "", "FNB_CLIENT_SECRET": ""})
        self.assertFalse(st["ready"])
        self.assertEqual(st["via"], "fnb-api")
        self.assertIn("own behalf", st["note"].lower())

    def test_parse_and_card_are_fnb_only(self):
        self.assertEqual(fnb_api.self_test(), 0)

    def test_never_qb_host(self):
        blob = Path(fnb_api.__file__).read_text()
        self.assertNotIn("intuit.com", blob)
        self.assertNotIn("quickbooks.api", blob)


if __name__ == "__main__":
    unittest.main()
