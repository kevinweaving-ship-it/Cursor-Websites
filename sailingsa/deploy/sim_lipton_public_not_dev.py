#!/usr/bin/env python3
"""Sim: public Lipton slug is not routed to the -dev playback page."""
from __future__ import annotations


def route(slug: str) -> str:
    slug_s = str(slug or "").strip()
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return "dev"
    return "live"


def main() -> int:
    assert route("2026-08-29-lipton-challenge-cup-dev") == "dev"
    assert route("2026-08-29-lipton-challenge-cup") == "live"
    assert route("other") == "live"
    print("PASS public slug is live board; -dev stays sandbox")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
