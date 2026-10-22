#!/usr/bin/env python3
"""Live vision smoke: pass only when downloaded pixels get a valid visual assessment.

vision_unavailable or a mocked response is not success. Run as the same account
that owns the Monday scheduler (rea) after load_env().
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from ai_tools import analyze_image, load_env, vision_model


def _candidate_bytes() -> tuple[bytes, str]:
    for path in (
        ROOT / "data" / "seed-media" / "2026-09-25-tsc-420-nationals-boat.jpg",
        ROOT / "data" / "seed-media" / "2026-09-25-tsc-420-nationals-overall.jpg",
        pathlib.Path("/tmp/roundup-photos/420-boat.jpg"),
        pathlib.Path("/tmp/roundup-photos/505-bottom.jpg"),
    ):
        if path.is_file() and path.stat().st_size > 12000:
            return path.read_bytes(), str(path)
    return b"", ""


def main() -> int:
    load_env(root=ROOT)
    raw, source = _candidate_bytes()
    if not raw:
        print(json.dumps({"status": "download_failed", "reason": "no candidate photograph on the box"}))
        return 2
    result = analyze_image(
        raw,
        {"title": "smoke", "source": source, "do_not_infer_identity": True},
    )
    safe = {k: result.get(k) for k in ("status", "id", "model", "category", "role", "reason", "analysis_version") if k in result}
    safe["source"] = source
    safe["bytes"] = len(raw)
    safe["vision_model"] = vision_model()
    print(json.dumps(safe, ensure_ascii=False))
    if result.get("status") != "ok":
        return 2
    if not result.get("description") or result.get("category") not in {
        "on-water",
        "prizegiving",
        "portrait",
        "poster",
        "results-sheet",
        "logo",
        "other",
    }:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
