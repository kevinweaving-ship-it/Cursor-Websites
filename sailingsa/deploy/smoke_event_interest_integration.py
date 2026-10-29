#!/usr/bin/env python3
"""Local integration smoke for Stages 1–3 (no production).

Checks:
  - Stage 1 schema validator
  - Stage 2 API tests (TestClient)
  - api.py registers register_event_interest_routes
  - frontend assets exist and mount selectors match
  - blank patcher dry-run against a fixture with live-like cards
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAILS = 0


def check(ok: bool, msg: str) -> None:
    global FAILS
    print(("PASS" if ok else "FAIL"), msg)
    if not ok:
        FAILS += 1


def main() -> int:
    api_txt = (ROOT / "api.py").read_text(encoding="utf-8", errors="replace")
    check(
        "register_event_interest_routes" in api_txt
        and "from sailingsa.backend.event_interest import register_event_interest_routes" in api_txt,
        "api.py registers event interest routes",
    )

    for rel in (
        "sailingsa/backend/event_interest.py",
        "sailingsa/backend/event_interest_schema.py",
        "sailingsa/deploy/event_class_interest.sql",
        "sailingsa/deploy/event_class_interest_rollback.sql",
        "sailingsa/frontend/js/event-interest.js",
        "sailingsa/frontend/css/event-interest.css",
        "sailingsa/deploy/patch_blank_event_interest.py",
        "sailingsa/deploy/EVENT_INTEREST_DEPLOY.md",
    ):
        check((ROOT / rel).is_file(), f"artifact present: {rel}")

    js = (ROOT / "sailingsa/frontend/js/event-interest.js").read_text(encoding="utf-8")
    check("landing-event-card[data-event-id]" in js, "JS mounts on data-event-id cards")
    check("/api/events/interest" in js, "JS calls Stage 2 batch endpoint")
    check("interest/withdraw" in js, "JS supports withdraw")

    css = (ROOT / "sailingsa/frontend/css/event-interest.css").read_text(encoding="utf-8")
    check("14px" in css and ".eci-btn" in css, "CSS has 14px logos and interest button")

    # Fixture patcher
    fixture = ROOT / "sailingsa/deploy/_eci_blank_fixture.html"
    fixture.write_text(
        """<!DOCTYPE html><html><head>
<link rel="stylesheet" href="/css/main.css">
</head><body>
<article class="sa-home-regatta-card landing-event-card landing-event-card--upcoming" data-landing-event-slot="1" data-state="upcoming"></article>
<article class="sa-home-regatta-card landing-event-card landing-event-card--upcoming" data-landing-event-slot="2" data-state="upcoming"></article>
<article class="sa-home-regatta-card landing-event-card landing-event-card--upcoming" data-landing-event-slot="3" data-state="upcoming"></article>
<article class="sa-home-regatta-card landing-event-card landing-event-card--upcoming" data-landing-event-slot="4" data-state="upcoming"></article>
</body></html>
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(ROOT / "sailingsa/deploy/patch_blank_event_interest.py"), "--file", str(fixture), "--write"],
        capture_output=True,
        text=True,
    )
    check(r.returncode == 0, "patcher --write on fixture")
    patched = fixture.read_text(encoding="utf-8")
    for eid in ("168679", "246456", "248485", "45"):
        check(f'data-event-id="{eid}"' in patched, f"fixture has data-event-id={eid}")
    check("event-interest.css" in patched and "event-interest.js" in patched, "fixture has CSS+JS tags")
    # cleanup fixture + bak
    for p in fixture.parent.glob("_eci_blank_fixture.html*"):
        p.unlink(missing_ok=True)

    # Stage 1 + 2 suites (require local DSN)
    import os

    dsn = (
        os.environ.get("EVENT_INTEREST_VALIDATE_DSN")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    check(bool(dsn), "EVENT_INTEREST_VALIDATE_DSN set for local suites")
    if dsn:
        r1 = subprocess.run(
            [sys.executable, str(ROOT / "sailingsa/deploy/validate_event_class_interest_schema.py")],
            cwd=str(ROOT),
        )
        check(r1.returncode == 0, "Stage 1 schema validator")
        r2 = subprocess.run(
            [sys.executable, str(ROOT / "sailingsa/deploy/test_event_interest_api.py")],
            cwd=str(ROOT),
        )
        check(r2.returncode == 0, "Stage 2 API tests")

    print()
    if FAILS:
        print(f"Integration smoke: {FAILS} failed — do not deploy")
        return 1
    print("Integration smoke: all checks passed (still not deployed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
