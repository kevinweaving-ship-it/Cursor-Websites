#!/usr/bin/env python3
"""Prepare a pre-screened diff for the read-only Grok reviewer.

Accepts a patch already exported by GitHub or a local audit, or a
read-only local ``git diff`` of explicit paths. Writes a redacted file
of at most 80 KB, then runs ``grok_review.py``.

No GitHub token, SSH session, or xAI request is used. ``--execute`` is
forwarded only when the caller sets it; the default is a dry run.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from grok_review import MAX_INPUT_BYTES, main as grok_main, sanitize_input

FORBIDDEN_PARTS = frozenset({"dev1", "roundups", "roundup"})
FORBIDDEN_PREFIXES = (
    Path("/var/www"),
    Path("/opt/rea"),
    Path("/opt/rea-ops"),
)


def refuse_production_path(path: Path) -> None:
    resolved = path.expanduser().resolve()
    parts = {part.lower() for part in resolved.parts}
    if parts & FORBIDDEN_PARTS:
        raise ValueError(f"refusing production path: {resolved}")
    for prefix in FORBIDDEN_PREFIXES:
        try:
            resolved.relative_to(prefix)
        except ValueError:
            continue
        raise ValueError(f"refusing production path: {resolved}")


def load_patch_file(path: Path) -> str:
    refuse_production_path(path)
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Review input exceeds 80,000 bytes; provide a smaller diff.")
    return data.decode("utf-8")


def git_diff(repo: Path, paths: list[str]) -> str:
    if not paths:
        raise ValueError("pass explicit paths; a whole-repo diff is not prepared")
    refuse_production_path(repo)
    repo_resolved = repo.expanduser().resolve()
    if not (repo_resolved / ".git").exists():
        raise ValueError("not a git checkout")
    for rel in paths:
        candidate = (repo_resolved / rel).resolve()
        refuse_production_path(candidate)
        try:
            candidate.relative_to(repo_resolved)
        except ValueError:
            raise ValueError("diff path escapes the repository") from None
    cmd = [
        "git",
        "-C",
        str(repo_resolved),
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--unified=3",
        "--",
        *paths,
    ]
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "false"
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=20)
    if proc.returncode != 0:
        raise ValueError("git diff failed")
    text = proc.stdout
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Review input exceeds 80,000 bytes; provide a smaller diff.")
    if not text.strip():
        raise ValueError("git diff is empty")
    return text


def prepare_text(text: str) -> str:
    cleaned = sanitize_input(text)
    if len(cleaned.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Review input exceeds 80,000 bytes; provide a smaller diff.")
    if not cleaned.strip():
        raise ValueError("Review input must not be empty.")
    return cleaned


def write_prepared(text: str, dest: Path) -> None:
    refuse_production_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    dest.chmod(0o600)


def default_output_path() -> Path:
    folder = Path(__file__).resolve().parent / ".review-input"
    folder.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix="review-", suffix=".diff", dir=folder)
    os.close(handle)
    return Path(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a bounded diff and dry-run Grok review")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-file", help="Patch already exported by GitHub or a local audit")
    source.add_argument("--from-git", action="store_true", help="Read-only git diff of explicit paths")
    parser.add_argument("--repo", default=".", help="Checkout for --from-git")
    parser.add_argument("--output", help="Where to write the redacted diff")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Forward --execute to grok_review.py (one billable request; not the default)",
    )
    parser.add_argument("paths", nargs="*", help="Repo-relative paths for --from-git")
    args = parser.parse_args(argv)
    try:
        if args.input_file:
            raw = load_patch_file(Path(args.input_file))
        else:
            raw = git_diff(Path(args.repo), args.paths)
        cleaned = prepare_text(raw)
        dest = Path(args.output) if args.output else default_output_path()
        write_prepared(cleaned, dest)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    print(f"prepared_file: {dest}", file=sys.stderr)
    forwarded = ["--input-file", str(dest)]
    if args.execute:
        forwarded.append("--execute")
    return grok_main(forwarded)


if __name__ == "__main__":
    sys.exit(main())
