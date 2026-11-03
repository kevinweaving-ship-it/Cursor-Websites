"""CLI: python -m sailingsa.roundup build --week 2026-10-26"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sailingsa.roundup.pipeline import build_edition, default_out
from sailingsa.roundup.gates import assert_idempotent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sailingsa.roundup", description="Rebuild one Weekly Roundup edition")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="Fact-sheet, rank, write feed/cards/edition (dry-run artifacts)")
    build.add_argument("--week", required=True, help="Edition Monday, e.g. 2026-10-26")
    build.add_argument("--live", action="store_true", help="Fetch /api/events and /api/regatta from sailingsa.co.za")
    build.add_argument("--out", default=str(default_out()), help="Artifact root (default artifacts/roundup)")

    recheck = sub.add_parser("recheck", help="Rebuild; new version only if content hash changes")
    recheck.add_argument("--week", required=True)
    recheck.add_argument("--live", action="store_true")
    recheck.add_argument("--out", default=str(default_out()))

    publish = sub.add_parser("publish", help="Dry-run only: print public paths, do not deploy")
    publish.add_argument("--week", required=True)
    publish.add_argument("--out", default=str(default_out()))

    test = sub.add_parser("test", help="Run 2026-10-26 acceptance gates")

    args = parser.parse_args(argv)
    if args.cmd == "build":
        payload = build_edition(args.week, live=args.live, out_root=Path(args.out))
        _print_build(payload)
        return 1 if payload["gate_failures"] else 0
    if args.cmd == "recheck":
        first = build_edition(args.week, live=args.live, out_root=Path(args.out))
        second = build_edition(args.week, live=args.live, out_root=Path(args.out))
        assert_idempotent(first["paths"]["hash"], second["paths"]["hash"])
        print(json.dumps({"recheck": "unchanged", "hash": first["paths"]["hash"]}, indent=2))
        return 1 if first["gate_failures"] else 0
    if args.cmd == "publish":
        week = args.week
        print("Dry-run only. No production deploy.")
        print(f"  /dev1/ card reads /sailing-roundup/feed.json")
        print(f"  Full edition: /sailing-roundup/issues/{week}/")
        print(f"  Preview: {args.out}/sailing-roundup/issues/{week}/index.html")
        print("Copy preview feed/cards into those public files on /dev1/ only after review.")
        return 0
    if args.cmd == "test":
        payload = build_edition("2026-10-26", live=False, out_root=Path(args.out) if hasattr(args, "out") else default_out())
        _print_build(payload)
        again = build_edition("2026-10-26", live=False, out_root=default_out())
        assert_idempotent(payload["paths"]["hash"], again["paths"]["hash"])
        return 1 if payload["gate_failures"] else 0
    return 2


def _print_build(payload: dict) -> None:
    print(f"Edition {payload['week']}  #{payload['edition_number']}")
    print(f"Lead: {payload['lead']['headline']}")
    print("Cards:")
    for sheet in payload["cards"]:
        print(f"  {sheet['story_score']:5.1f}  {sheet['event_id']}  {sheet['copy']['headline']}")
    if payload["awaiting"]:
        print("Awaiting:")
        for sheet in payload["awaiting"]:
            print(f"         {sheet['event_id']}")
    if payload["gate_failures"]:
        print("GATE FAILURES:")
        for fail in payload["gate_failures"]:
            print(" ", fail)
    else:
        print("Gates: PASS")
    print("Artifacts:")
    for key, path in payload["paths"].items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
