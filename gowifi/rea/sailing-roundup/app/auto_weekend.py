#!/usr/bin/env python3
"""Compatibility wrapper. Monday publication now lives in publish_weekend.py."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_weekend import publish


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--monday", required=True)
    p.add_argument("--rebuild", action="store_true")
    args = p.parse_args()
    print(json.dumps(publish(args.monday, rebuild=args.rebuild)))
