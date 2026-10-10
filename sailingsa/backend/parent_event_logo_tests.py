import json
import os
import tempfile
import unittest

from parent_event_logo import (
    header_left_url,
    is_class_logo_path,
    is_event_logo_path,
    parent_event_logo_url,
)


class ParentEventLogoTests(unittest.TestCase):
    def test_path_kinds(self):
        self.assertTrue(is_event_logo_path("/artwork/Event Logo/Dam-Bottle-Sprints.png"))
        self.assertTrue(is_event_logo_path("/artwork/Event%20Logo/Dam-Bottle-Sprints.png?v=1"))
        self.assertFalse(is_event_logo_path("/artwork/Class Logo/Open-Class-Logo-v20260913h.png"))
        self.assertTrue(is_class_logo_path("/artwork/Class%20Logo/Open-Class-Logo-v20260913h.png"))

    def test_parent_prefers_header_event_logo(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "wc_regatta_header_icons.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "2026-10-10-hmyc-dam-bottle-sprints": {
                            "left": "/artwork/Event Logo/Dam-Bottle-Sprints.png?v=pt1",
                            "right": "/artwork/Club Logo/HMYC.png",
                        },
                        "2026-09-25-tsc-420-nationals": {
                            "left": "/artwork/Class Logo/420-Class-Logo.png",
                        },
                    },
                    fh,
                )
            ev = parent_event_logo_url(
                "2026-10-10-hmyc-dam-bottle-sprints",
                series={"logo": "/artwork/Class Logo/Open-Class-Logo-v20260913h.png"},
                header_path=p,
            )
            self.assertTrue(is_event_logo_path(ev))
            self.assertIn("Dam-Bottle-Sprints", ev)
            self.assertEqual(
                parent_event_logo_url("2026-09-25-tsc-420-nationals", header_path=p),
                "",
            )
            self.assertTrue(
                is_event_logo_path(
                    header_left_url("2026-10-10-hmyc-dam-bottle-sprints", header_path=p)
                )
            )


if __name__ == "__main__":
    unittest.main()
