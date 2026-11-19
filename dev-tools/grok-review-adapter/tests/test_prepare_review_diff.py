import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_review_diff import main, refuse_production_path


class PrepareReviewDiffTest(unittest.TestCase):
    def test_refuses_production_paths(self):
        for raw in ("/var/www/sailingsa/api.py", "/opt/rea/ops/rea_ops.py", "/tmp/dev1/app.js", "/tmp/roundups/feed.txt"):
            with self.assertRaises(ValueError):
                refuse_production_path(Path(raw))

    def test_input_file_dry_run_zero_http(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "safe.diff"
            source.write_text("diff --git a/example.py b/example.py\n+print('ok')\n", encoding="utf-8")
            output = Path(directory) / "prepared.diff"
            with patch("urllib.request.urlopen", side_effect=AssertionError("network called")):
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    code = main(["--input-file", str(source), "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertIn("DRY_RUN_NO_API_CALL", stdout.getvalue())
            prepared = output.read_text(encoding="utf-8")
            self.assertIn("example.py", prepared)
            self.assertNotIn("Authorization", prepared)

    def test_redacts_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "secret.diff"
            source.write_text("diff --git a/a b/a\n+xai_token=abc123456\n", encoding="utf-8")
            output = Path(directory) / "prepared.diff"
            with patch("sys.stdout", new_callable=io.StringIO):
                code = main(["--input-file", str(source), "--output", str(output)])
            self.assertEqual(code, 0)
            prepared = output.read_text(encoding="utf-8")
            self.assertNotIn("abc123456", prepared)
            self.assertIn("[REDACTED]", prepared)

    def test_oversized_rejected_without_http(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "big.diff"
            source.write_text("x" * 80001, encoding="utf-8")
            with patch("urllib.request.urlopen", side_effect=AssertionError("network called")):
                with patch("sys.stderr", new_callable=io.StringIO):
                    code = main(["--input-file", str(source)])
            self.assertEqual(code, 2)

    def test_from_git_explicit_path_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "example.py").write_text("print(1)\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "example.py"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.email=review@localhost", "-c", "user.name=review", "commit", "-m", "init"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "example.py").write_text("print(2)\n", encoding="utf-8")
            output = repo / "prepared.diff"
            with patch("urllib.request.urlopen", side_effect=AssertionError("network called")):
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    code = main(["--from-git", "--repo", str(repo), "--output", str(output), "--", "example.py"])
            self.assertEqual(code, 0)
            self.assertIn("DRY_RUN_NO_API_CALL", stdout.getvalue())
            self.assertIn("example.py", output.read_text(encoding="utf-8"))

    def test_from_git_refuses_dev1(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            target = repo / "dev1"
            target.mkdir()
            (target / "app.js").write_text("var x = 1;\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            with patch("urllib.request.urlopen", side_effect=AssertionError("network called")):
                with patch("sys.stderr", new_callable=io.StringIO):
                    code = main(["--from-git", "--repo", str(repo), "--", "dev1/app.js"])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
