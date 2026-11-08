import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grok_review import prepare_payload, sanitize_input, extract_output, call_api, main


class FakeResponse:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return json.dumps(self.data).encode()


class GrokReviewTest(unittest.TestCase):
    def test_redacts_secrets(self):
        text = 'Authorization: Bearer secret123 xai_token=abc123456 ghp_abcdefghijklmno'
        result = sanitize_input(text)
        self.assertNotIn('secret123', result)
        self.assertNotIn('abc123456', result)
        self.assertNotIn('ghp_abcdefghijklmno', result)

    def test_payload_read_only(self):
        p = prepare_payload('diff --git a/x b/x')
        self.assertEqual(p['store'], False)
        self.assertNotIn('tools', p)
        self.assertEqual(p['max_output_tokens'], 1200)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError): prepare_payload('  ')

    def test_oversized_rejected(self):
        with self.assertRaises(ValueError): prepare_payload('x' * 80001)

    def test_no_key_rejected_without_http(self):
        with self.assertRaises(ValueError): call_api(prepare_payload('test'), '')

    def test_parses_responses_format(self):
        self.assertEqual(extract_output({'output':[{'type':'message','content':[{'type':'output_text','text':'Issue 1'}]}]}), 'Issue 1')

    def test_mocked_request(self):
        seen = []
        def opener(req, timeout):
            seen.append((req.full_url, req.get_method(), timeout))
            return FakeResponse({'output':[{'type':'message','content':[{'type':'output_text','text':'PASS: mock'}]}]})
        self.assertEqual(call_api(prepare_payload('review'), 'test-key', opener=opener), 'PASS: mock')
        self.assertEqual(seen[0][1], 'POST')

    def test_dry_run_zero_http(self):
        with tempfile.TemporaryDirectory() as d:
            filename = Path(d) / 'diff.txt'
            filename.write_text('diff --git a/a b/a')
            with patch('urllib.request.urlopen', side_effect=AssertionError('network called')):
                with patch('sys.stdout', new_callable=io.StringIO) as out:
                    self.assertEqual(main(['--input-file',str(filename)]), 0)
                    self.assertIn('DRY_RUN_NO_API_CALL', out.getvalue())


if __name__ == '__main__': unittest.main()
