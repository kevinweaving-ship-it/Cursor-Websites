#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from roundup import (
    SINGLE_IMAGE_CENTER_MARK,
    apply_single_image_center_css,
    newspaper_css,
)


class SingleImageCenterCss(unittest.TestCase):
    def test_css_centers_single_non_full_width_images(self):
        css = newspaper_css() + apply_single_image_center_css("<style></style>")
        self.assertIn(SINGLE_IMAGE_CENTER_MARK, css)
        self.assertIn("justify-self:center", css)
        self.assertIn(".photo-set:not(.pair):not(.paired-then-full)", css)
        self.assertIn(".edition-lead figure{justify-self:center", css.replace("\n", ""))

    def test_apply_is_idempotent_and_injects_before_style_close(self):
        page = "<style>.edition-lead figure{aspect-ratio:16/9;max-height:220px}</style><h1>Lead</h1>"
        once = apply_single_image_center_css(page)
        twice = apply_single_image_center_css(once)
        self.assertEqual(once, twice)
        self.assertTrue(once.index(SINGLE_IMAGE_CENTER_MARK) < once.index("</style>"))
        self.assertEqual(once.count(SINGLE_IMAGE_CENTER_MARK), 1)


if __name__ == "__main__":
    unittest.main()
