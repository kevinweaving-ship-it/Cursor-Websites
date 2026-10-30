#!/usr/bin/env python3
"""Event Logo vs class=fleet: combined artwork must not steal a sole-class header."""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from event_logo_class_compat import (  # noqa: E402
    KZN_MIRROR_ILCA_EVENT_LOGO,
    MIDMAR_CUP_EVENT_LOGO,
    MIRROR_CLASS_LOGO,
    event_logo_src_compatible_with_event,
    named_event_logo_url,
)

MIRROR_ONLY_NAME = "KZN Mirror Regionals"
MIRROR_ONLY_ID = "2026-10-17-pyc-kzn-mirror-regionals"
MIRROR_ONLY_HAY = f"{MIRROR_ONLY_NAME.lower()} {MIRROR_ONLY_ID.replace('-', ' ')}"
COMBINED_HAY = (
    "kzn mirror ilca regional championship 2023 10 22 "
    "kzn mirror ilca regional championship"
)


class EventLogoClassCompatTest(unittest.TestCase):
    def test_combined_ilca_logo_rejected_for_mirror_only(self):
        self.assertFalse(
            event_logo_src_compatible_with_event(KZN_MIRROR_ILCA_EVENT_LOGO, MIRROR_ONLY_HAY)
        )

    def test_combined_logo_kept_when_both_classes_in_name(self):
        self.assertTrue(
            event_logo_src_compatible_with_event(KZN_MIRROR_ILCA_EVENT_LOGO, COMBINED_HAY)
        )

    def test_kzn_mirror_ilca_needle_does_not_match_mirror_only(self):
        self.assertNotIn("kzn mirror ilca", MIRROR_ONLY_HAY)
        self.assertIn("kzn mirror", MIRROR_ONLY_HAY)

    def test_mirror_only_named_event_uses_mirror_class_logo(self):
        self.assertEqual(
            named_event_logo_url(MIRROR_ONLY_ID, MIRROR_ONLY_NAME),
            MIRROR_CLASS_LOGO,
        )

    def test_ilca_only_rejects_filename_that_also_names_mirror(self):
        hay = "kzn ilca regionals 2025 07 20 kzn regionals kzn ilca regionals"
        self.assertFalse(event_logo_src_compatible_with_event(KZN_MIRROR_ILCA_EVENT_LOGO, hay))

    def test_generic_event_logo_without_class_token_ok(self):
        self.assertTrue(
            event_logo_src_compatible_with_event(
                "/artwork/Event Logo/Cape-Classic-Series.png",
                "cape classic series",
            )
        )

    def test_midmar_cup_uses_named_event_logo(self):
        self.assertEqual(
            named_event_logo_url("2026-09-19-hmyc-midmar-cup", "The Midmar Cup"),
            MIDMAR_CUP_EVENT_LOGO,
        )


if __name__ == "__main__":
    unittest.main()
