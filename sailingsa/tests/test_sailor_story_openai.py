"""Offline tests for SailingSA GPT adapter (no network or API key needed)."""
import json
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sailor_story_openai import generate_story, story_fingerprint, StoryGenerationError

FACTS = {
    "first_name": "Timothy",
    "regatta_count": 2,
    "race_entries_count": 12,
    "source_results": [
        {"id": "r1", "regatta": "Example championship", "rank": 1, "entries": 33},
        {"id": "r2", "regatta": "Example club regatta", "rank": 3, "entries": 12},
    ],
}

class FakeResponse:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return json.dumps(self.data).encode()

class AdapterTests(unittest.TestCase):
    def test_fingerprint_stable(self):
        self.assertEqual(story_fingerprint("123", FACTS), story_fingerprint("123", dict(reversed(list(FACTS.items())))))

    def test_requires_sas_id(self):
        with self.assertRaises(ValueError):
            generate_story("Timothy", FACTS, api_key="test")

    def test_requires_evidence(self):
        with self.assertRaises(ValueError):
            generate_story("123", {"source_results":[]}, api_key="test")

    def test_missing_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(StoryGenerationError):
                generate_story("123", FACTS)

    @patch("urllib.request.urlopen")
    def test_valid_response(self, urlopen):
        teaser = "You have recorded results across your sailing history, including finishes in different fleets. Your SailingSA archive keeps the evidence linked to each result, so you can revisit your events and compare how your recorded performances have changed over time. Claim your profile to explore the underlying results."
        content = json.dumps({"headline": "Your recorded sailing story", "teaser": teaser, "evidence_ids":["r1"]})
        urlopen.return_value = FakeResponse({"output":[{"type":"message","content":[{"type":"output_text","text":content}]}]})
        result = generate_story("123", FACTS, api_key="test")
        self.assertEqual(result["evidence_ids"], ["r1"])
        self.assertIn("cache_key", result)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertFalse(json.loads(request.data)["store"])

    @patch("urllib.request.urlopen")
    def test_rejects_unbacked_evidence_reference(self, urlopen):
        teaser = " ".join(["Your recorded sailing results should always be connected to a real race result."]*4)
        content = json.dumps({"headline":"Your story","teaser":teaser,"evidence_ids":["fabricated"]})
        urlopen.return_value = FakeResponse({"output":[{"type":"message","content":[{"type":"output_text","text":content}]}]})
        with self.assertRaises(StoryGenerationError):
            generate_story("123", FACTS, api_key="test")

if __name__ == "__main__":
    unittest.main()
