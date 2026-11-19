#!/usr/bin/env python3
import unittest
from pathlib import Path

import fnb_statement


class FnbStatement(unittest.TestCase):
    def test_popup_dedup_alloc_attention(self):
        self.assertEqual(fnb_statement.self_test(), 0)

    def test_never_qb_source(self):
        blob = Path(fnb_statement.__file__).read_text()
        self.assertNotIn("intuit.com", blob)
        self.assertNotIn("quickbooks.api", blob)


if __name__ == "__main__":
    unittest.main()
