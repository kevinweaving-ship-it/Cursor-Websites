#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from live_patch_gsc_api import patch  # noqa: E402

SNIPPET = '''
@app.get("/regatta/class/podium/podium.html")
def _regatta_podium_html():
    path = os.path.join(_static_dir(), "regatta", "class", "podium", "podium.html")
    if os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="regatta/class/podium/podium.html not found")

@app.get("/sailors", response_class=HTMLResponse)
def _directory_sailors_page():
    items = _directory_sailors()
    return HTMLResponse(_directory_page_html("/sailors", items, "sailor", "Sailors"))
'''


class LivePatchGscApiTests(unittest.TestCase):
    def test_podium_and_sailors_title(self) -> None:
        out = patch(SNIPPET)
        self.assertIn('query_params.get("regatta_id")', out)
        self.assertIn("RedirectResponse(url=\"/events\", status_code=301)", out)
        self.assertIn("South African Sailors", out)
        self.assertNotIn('_directory_page_html("/sailors", items, "sailor", "Sailors")', out)
        twice = patch(out)
        self.assertEqual(out.count("query_params.get"), 1)
        self.assertEqual(twice.count("South African Sailors"), 1)


if __name__ == "__main__":
    unittest.main()
