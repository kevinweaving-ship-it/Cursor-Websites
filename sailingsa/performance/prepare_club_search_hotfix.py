#!/usr/bin/env python3
"""Prepare a surgical SailingSA club-search fix from an exact live API snapshot.

Only writes the explicitly requested staged output, never production. Deployment
must still pass the existing Gold-hash/approved-revisions process.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path

AUDITED_LIVE_SHA256 = "415f6c38ce85dbdb21e20f8975fcb2da7697c8bd0418fbffbfde0079ffd5408f"
OLD = """    rows = q(sql, params)
    for r in rows or []:
        name = (r.get("name") or r.get("code") or "").strip()
"""
NEW = """    # Use the supplied parameter tuple and dictionary cursor, not the shadowed q helper.
    with db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = [dict(row) for row in cur.fetchall()]
    for r in rows or []:
        name = (r.get("name") or r.get("code") or "").strip()
"""


def prepare(source: Path, output: Path, *, expected_sha256: str) -> str:
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("Refusing to overwrite original source")
    raw = source.read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected_sha256:
        raise ValueError(f"Source digest mismatch: {observed}")
    txt = raw.decode("utf-8")
    start = txt.index("def api_search_clubs(")
    end = txt.index('@app.get("/api/member/search")', start)
    segment = txt[start:end]
    if segment.count(OLD) != 1:
        raise ValueError("Expected exact club-search block not found once")
    changed = txt[:start] + segment.replace(OLD, NEW, 1) + txt[end:]
    ast.parse(changed)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(changed.encode("utf-8"))
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256", default=AUDITED_LIVE_SHA256)
    args = parser.parse_args()
    print(prepare(args.source, args.output, expected_sha256=args.expected_sha256))


if __name__ == "__main__":
    main()
