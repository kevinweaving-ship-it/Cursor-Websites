"""The live pdf-share file keeps its other blocks when the fleet logo script is replaced."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sailingsa/deploy/apply-parent-event-logo-truth.py"
EXTRA = (ROOT / "sailingsa/frontend/js/parent-event-logo-truth.js").read_text(encoding="utf-8")


def load():
    spec = importlib.util.spec_from_file_location("apply_parent_event_logo_truth", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LIVE = """/* before */
(function () { var keep = 1; })();

/* PARENT_EVENT_LOGO_TRUTH_v4 */
/* replace class marks with the event logo */
(function () {
  function paintFleetEventLogo(eventSrc) {
    img.src = eventSrc;
  }
})();

/* after */
(function () { var tail = 1; })();
"""


class ReplaceParentTruthBlock(unittest.TestCase):
    def test_replaces_only_the_truth_block(self):
        mod = load()
        out = mod.replace_parent_truth_block(LIVE, EXTRA)
        self.assertIn("var keep = 1", out)
        self.assertIn("var tail = 1", out)
        self.assertNotIn("replace class marks", out)
        self.assertNotIn("src*='Class Logo'", out)
        self.assertIn('keeps the Class Logo', out)
        self.assertEqual(out.count("PARENT_EVENT_LOGO_TRUTH"), 1)
        again = mod.replace_parent_truth_block(out, EXTRA)
        self.assertEqual(again, out)


if __name__ == "__main__":
    unittest.main()
