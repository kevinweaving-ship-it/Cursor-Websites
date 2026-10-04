"""Load a published rating list. The file is the catalogue; classes are not created from it."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent / "published" / "rya_pn_2026.json"


@dataclass(frozen=True)
class RatingEntry:
    list_section: str
    source_class_id: str
    source_class_name: str
    crew_count: int
    rig: str
    spinnaker: str
    variant: str
    rating_value: int
    change_from_previous: int
    source_notes: str


@dataclass(frozen=True)
class Publication:
    system_code: str
    system_name: str
    publisher: str
    version_label: str
    version_number: str
    announced_on: str
    source_last_update: str
    source_last_update_printed: str
    effective_from: str
    effective_to: str | None
    source_title: str
    source_url: str
    announcement_url: str
    scheme_url: str
    formula: str
    rounding_rule: str
    scale_numerator: int
    notes: str
    entries: tuple[RatingEntry, ...]

    def entry_by_source_id(self, source_class_id: str) -> RatingEntry:
        wanted = str(source_class_id)
        for entry in self.entries:
            if entry.source_class_id == wanted:
                return entry
        raise KeyError(wanted)


def load_rya_py_2026(path: Path | None = None) -> Publication:
    raw = json.loads((path or DATA).read_text(encoding="utf-8"))
    entries = tuple(
        RatingEntry(
            list_section=row["list_section"],
            source_class_id=str(row["source_class_id"]),
            source_class_name=row["source_class_name"],
            crew_count=int(row["crew_count"]),
            rig=row["rig"],
            spinnaker=row["spinnaker"],
            variant=row["variant"],
            rating_value=int(row["rating_value"]),
            change_from_previous=int(row["change_from_previous"]),
            source_notes=row["source_notes"],
        )
        for row in raw["entries"]
    )
    ids = [entry.source_class_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate RYA class id in the catalogue")
    return Publication(
        system_code=raw["system_code"],
        system_name=raw["system_name"],
        publisher=raw["publisher"],
        version_label=raw["version_label"],
        version_number=raw["version_number"],
        announced_on=raw["announced_on"],
        source_last_update=raw["source_last_update"],
        source_last_update_printed=raw["source_last_update_printed"],
        effective_from=raw["effective_from"],
        effective_to=raw["effective_to"],
        source_title=raw["source_title"],
        source_url=raw["source_url"],
        announcement_url=raw["announcement_url"],
        scheme_url=raw["scheme_url"],
        formula=raw["formula"],
        rounding_rule=raw["rounding_rule"],
        scale_numerator=int(raw["scale_numerator"]),
        notes=raw["notes"],
        entries=entries,
    )
