
import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]  # repo root
sys.path.insert(0, str(ROOT / "sailingsa"))
sys.path.insert(0, str(ROOT))
from optimize_index_script_loading import optimize_html

SAMPLE = """<!DOCTYPE html>
<html><head>
<script src="/js/early.js"></script>
<link rel="stylesheet" href="/css/main.css">
<script type="application/ld+json">{}</script>
</head>
<body>
<main>hi</main>
<script src="/js/app.js"></script>
<script src="/js/other.js" defer></script>
</body></html>
"""

class OptimizeIndexScriptLoadingTest(unittest.TestCase):
    def test_defers_body_keeps_head_sync_and_moves_after_css(self):
        out = optimize_html(SAMPLE, extract=False)
        head = out[: out.lower().index("</head>")]
        body = out[out.lower().index("</head>"):]
        self.assertLess(head.index('rel="stylesheet"'), head.index('src="/js/early.js"'))
        self.assertIn('src="/js/early.js"', head)
        self.assertNotIn(" defer", head[head.index('src="/js/early.js"') - 20 : head.index('src="/js/early.js"') + 40])
        self.assertIn('src="/js/app.js" defer', body)
        self.assertIn('src="/js/other.js" defer', body)

if __name__ == "__main__":
    unittest.main()
