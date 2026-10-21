#!/usr/bin/env python3
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from ai_tools import available, chat, load_env, writer_name


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


if __name__ == "__main__":
    unittest.main()
