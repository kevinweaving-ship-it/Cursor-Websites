"""One-edition rebuild: ingest → fact sheet → rank → write → gates → artifacts."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sailingsa.roundup.factsheet import build_factsheet
from sailingsa.roundup.gates import run_gates
from sailingsa.roundup.ingest import load_week_bundle
from sailingsa.roundup.media_pool import write_pool
from sailingsa.roundup.rank import rank_sheets
from sailingsa.roundup.render import build_payload, write_artifacts


def default_out() -> Path:
    return Path(__file__).resolve().parents[2] / "artifacts" / "roundup"


def build_edition(week: str, live: bool = False, out_root: Path | None = None) -> dict:
    bundle = load_week_bundle(week, live=live)
    edition = date.fromisoformat(week)
    sheets = [
        build_factsheet(item, edition, extra_sources=bundle.get("sources") or [])
        for item in bundle["items"]
    ]
    ranked = rank_sheets(sheets)
    payload = build_payload(ranked, week)
    payload["window"] = {
        "week_start": bundle["week_start"],
        "week_end": bundle["week_end"],
    }
    failures = run_gates(payload)
    payload["gate_failures"] = failures
    dest = Path(out_root) if out_root else default_out()
    paths = write_artifacts(payload, dest)
    write_pool(payload, dest)
    payload["paths"] = paths
    return payload
