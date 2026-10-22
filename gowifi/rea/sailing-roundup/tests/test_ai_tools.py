#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from ai_tools import analyze_image, available, chat, load_env, search_images, writer_name


class SharedAITools(unittest.TestCase):
    def test_news_media_serpapi_alias_is_wired(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            env = root / "data" / "roundup.env"
            env.parent.mkdir(parents=True)
            env.write_text("SERPAPI_KEY=serp-news-media-key\n")
            environ = {}
            load_env(root=root, environ=environ)
            tools = available(environ)
            self.assertEqual(tools["search"], ["serpapi"])
            self.assertIn("serpapi", tools["media_news_keys"])
            self.assertTrue(tools["wired"])
            self.assertIsNone(tools["writer"])
            blob = json.dumps(tools)
            self.assertNotIn("serp-news-media-key", blob)
            self.assertEqual(environ.get("SERPAPI_API_KEY"), "serp-news-media-key")

    def test_chatgpt_alias_becomes_openai_writer(self):
        environ = {"CHATGPT_API_KEY": "sk-test-writer"}
        load_env(root=pathlib.Path("/tmp/does-not-exist"), environ=environ)
        self.assertEqual(writer_name(environ), "openai")
        tools = available(environ)
        self.assertEqual(tools["writer"], "openai")
        self.assertEqual(tools["openai_model"], "gpt-4o-mini")
        self.assertNotIn("sk-test-writer", json.dumps(tools))

    def test_existing_env_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            env = root / ".env"
            env.write_text("OPENAI_API_KEY=from-file\n")
            environ = {"OPENAI_API_KEY": "already-set"}
            load_env(root=root, extra_files=[env], environ=environ)
            self.assertEqual(environ["OPENAI_API_KEY"], "already-set")

    def test_chat_uses_openai_first(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "Dale Rae won."}}]}).encode()

        opener = MagicMock(return_value=Response())
        environ = {"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": "gpt-4o-mini"}
        text, provider = chat("sys", "user", environ=environ, opener=opener)
        self.assertEqual(provider, "openai")
        self.assertEqual(text, "Dale Rae won.")
        req = opener.call_args[0][0]
        self.assertEqual(req.full_url, "https://api.openai.com/v1/chat/completions")

    def test_chat_falls_back_to_official_without_keys(self):
        text, provider = chat("sys", "user", environ={})
        self.assertEqual(text, "")
        self.assertEqual(provider, "official")

    def test_analyze_image_sends_pixels_and_never_uses_chat(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "description": "boats on water",
                                            "category": "on-water",
                                            "role": "lead",
                                            "relevance": 0.9,
                                        }
                                    )
                                }
                            }
                        ]
                    }
                ).encode()

        opener = MagicMock(return_value=Response())
        pixels = b"\xff\xd8\xff" + b"photo-bytes" * 20
        with tempfile.TemporaryDirectory() as temp:
            result = analyze_image(
                pixels,
                {"title": "420 Nationals"},
                environ={"OPENAI_API_KEY": "sk-test"},
                opener=opener,
                cache_root=temp,
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["category"], "on-water")
        payload = json.loads(opener.call_args[0][0].data.decode())
        content = payload["messages"][1]["content"]
        self.assertTrue(any(part.get("type") == "image_url" for part in content))
        self.assertIn("data:image/jpeg;base64,", json.dumps(content))
        self.assertNotEqual(payload["model"], "gpt-4o-mini")

    def test_analyze_image_does_not_fall_back_to_text_chat(self):
        empty = analyze_image(b"", environ={"OPENAI_API_KEY": ""})
        self.assertEqual(empty["status"], "download_failed")
        missing = analyze_image(b"pixels", environ={})
        self.assertEqual(missing["status"], "vision_unavailable")
        class Boom:
            def __call__(self, *a, **k):
                raise TimeoutError("vision down")

        failed = analyze_image(b"pixels", environ={"OPENAI_API_KEY": "sk"}, opener=Boom(), retries=1, cache_root="/tmp/does-not-exist-vision")
        self.assertEqual(failed["status"], "analysis_failed")
        self.assertNotIn("official", failed.get("reason", "").lower())

    def test_search_images_reports_empty_and_blocked(self):
        class Empty:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"images_results": []}).encode()

        opener = MagicMock(return_value=Empty())
        result = search_images("420 Nationals 2026 photos", environ={"SERPAPI_API_KEY": "k"}, opener=opener, bing_search=lambda q: [])
        self.assertEqual(result["status"], "empty")
        none = search_images("x", environ={}, bing_search=lambda q: (_ for _ in ()).throw(RuntimeError("bing down")))
        self.assertEqual(none["status"], "provider_failure")
        bing = search_images(
            "505 Nationals 2026 photos",
            environ={},
            bing_search=lambda q: [{"image_url": "https://rsa505.org.za/a.jpg", "source_url": "https://rsa505.org.za/", "title": "505 Nationals"}],
        )
        self.assertEqual(bing["status"], "ok")
        self.assertEqual(bing["provider"], "bing_html")
        self.assertEqual(bing["items"][0]["url"], "https://rsa505.org.za/a.jpg")


if __name__ == "__main__":
    unittest.main()
