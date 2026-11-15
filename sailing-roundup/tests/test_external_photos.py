import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from external_photos import apply_manifest, parse_manifest

MANIFEST = """
| edition | event id | local file | image URL | source_url | caption | credit |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-02 | 2026-10-31-ilca-masters | ilca.jpg | https://cdn.example/ilca.jpg | https://www.facebook.com/benonisailing/posts/1 | ILCA fleet at Benoni. | Benoni Sailing Club / Facebook |
| 2026-10-26 | 2026-10-24-hmyc-dam-bottle-sprints | dam.jpg | https://cdn.example/dam.jpg | https://www.facebook.com/hmyc/posts/2 | Dart 18s at Midmar. | Henley Midmar Yacht Club / Facebook | EXCLUDED |
| 2026-10-05 | 2026-10-04-free-state-youth | old.jpg | | https://club.example/photo | Dabchicks at Lake Deneys. | Free State Youth |
"""

JPEG = b"\xff\xd8\xff" + b"\x00" * 32


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self._data[:limit]


def issue(event_id, winner):
    return {
        "issue_id": event_id[:10],
        "articles": [
            {
                "id": "lead",
                "type": "feature",
                "event_id": "lead",
                "hero_image": None,
                "blocks": [{"type": "paragraph", "text": f"{winner} won."}],
            },
            {
                "id": event_id,
                "type": "regatta_report",
                "event_id": event_id,
                "needs_external": True,
                "hero_image": None,
                "week_fact": {"winner": winner, "races": 6},
                "blocks": [
                    {"type": "paragraph", "text": f"{winner} won all 6 races."},
                    {"type": "results", "rows": [["1st", winner]], "source_event_url": "https://sailingsa.co.za/regatta/" + event_id},
                ],
            },
        ],
        "needs_external": [event_id],
    }


class ExternalPhotosTest(unittest.TestCase):
    def test_parse_skips_excluded(self):
        rows = parse_manifest(MANIFEST)
        self.assertEqual([row["event_id"] for row in rows], ["2026-10-31-ilca-masters", "2026-10-04-free-state-youth"])

    def test_applies_download_and_keeps_story(self):
        with self._tree() as root:
            def opener(request, timeout):
                self.assertIn("ilca.jpg", request.full_url)
                return FakeResponse(JPEG)

            applied = apply_manifest(root, root / "external-photos" / "MANIFEST.md", opener=opener)
            self.assertEqual(
                applied,
                [
                    "2026-11-02/2026-10-31-ilca-masters",
                    "2026-10-05/2026-10-04-free-state-youth",
                ],
            )
            issue_path = root / "issues" / "2026-11-02" / "issue.json"
            saved = json.loads(issue_path.read_text(encoding="utf-8"))
            article = saved["articles"][1]
            self.assertEqual(article["week_fact"]["winner"], "Leon de Raay")
            self.assertEqual(article["blocks"][1]["text"], "Leon de Raay won all 6 races.")
            self.assertEqual(article["blocks"][2]["rows"][0][1], "Leon de Raay")
            self.assertFalse(article["needs_external"])
            self.assertEqual(saved["needs_external"], [])
            self.assertEqual(article["blocks"][0]["role"], "hero")
            self.assertTrue((root / "issues" / "2026-11-02" / "media" / "2026-10-31-ilca-masters-hero.jpg").is_file())
            html = (root / "issues" / "2026-11-02" / "index.html").read_text(encoding="utf-8")
            self.assertIn("media/2026-10-31-ilca-masters-hero.jpg", html)
            self.assertIn("Leon de Raay won all 6 races.", html)
            feed = json.loads((root / "feed.json").read_text(encoding="utf-8"))
            self.assertIn("2026-10-31-ilca-masters-hero.jpg", feed[0]["image"])
            self.assertEqual(feed[0]["image_caption"], "ILCA fleet at Benoni.")
            self.assertEqual(feed[1]["image"], "https://sailingsa.co.za/sailing-roundup/issues/2026-10-26/media/keep.jpg")

    def test_local_file_when_url_fails_and_older_edition(self):
        with self._tree() as root:
            def opener(request, timeout):
                raise OSError("offline")

            applied = apply_manifest(root, root / "external-photos" / "MANIFEST.md", opener=opener)
            self.assertEqual(applied, ["2026-10-05/2026-10-04-free-state-youth"])
            article = json.loads((root / "issues" / "2026-10-05" / "issue.json").read_text(encoding="utf-8"))["articles"][1]
            self.assertEqual(article["week_fact"]["winner"], "Maximilian Malan")
            self.assertFalse(article["needs_external"])
            self.assertTrue((root / "issues" / "2026-10-05" / "media" / "2026-10-04-free-state-youth-hero.jpg").is_file())

    def _tree(self):
        import tempfile

        class _Ctx:
            def __enter__(self):
                self.tmp = tempfile.TemporaryDirectory()
                root = Path(self.tmp.name)
                photos = root / "external-photos"
                photos.mkdir()
                (photos / "MANIFEST.md").write_text(MANIFEST, encoding="utf-8")
                (photos / "old.jpg").write_bytes(JPEG)
                self._write_issue(root, "2026-11-02", "2026-10-31-ilca-masters", "Leon de Raay")
                self._write_issue(root, "2026-10-05", "2026-10-04-free-state-youth", "Maximilian Malan")
                (root / "feed.json").write_text(json.dumps([
                    {"published_at": "2026-11-02", "url": "https://sailingsa.co.za/sailing-roundup/issues/2026-11-02/", "image": "", "headline": "ILCA Masters"},
                    {"published_at": "2026-10-26", "url": "https://sailingsa.co.za/sailing-roundup/issues/2026-10-26/", "image": "https://sailingsa.co.za/sailing-roundup/issues/2026-10-26/media/keep.jpg", "headline": "Keep me"},
                ]), encoding="utf-8")
                self.root = root
                return root

            def _write_issue(self, root, edition, event_id, winner):
                folder = root / "issues" / edition
                folder.mkdir(parents=True)
                (folder / "issue.json").write_text(json.dumps(issue(event_id, winner)), encoding="utf-8")
                (folder / "index.html").write_text(
                    f'<article class="story" id="{event_id}"><header><h2>{winner}</h2></header>'
                    f'<div class="copy"><p class=\'lede\'>{winner} won all 6 races.</p></div></article>',
                    encoding="utf-8",
                )

            def __exit__(self, *args):
                self.tmp.cleanup()

        return _Ctx()


if __name__ == "__main__":
    unittest.main()
