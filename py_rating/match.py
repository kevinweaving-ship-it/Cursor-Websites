"""Match a published rating row to an existing class. Never inserts a class."""

from __future__ import annotations

import re
from dataclasses import dataclass

from py_rating.catalogue import Publication, RatingEntry

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalise_label(value: str) -> str:
    text = (value or "").casefold().replace("&", " and ")
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


def lookup_labels(source_class_name: str) -> list[str]:
    """The printed name, plus each side of an RYA 'A / B' alternative."""
    name = " ".join((source_class_name or "").split())
    labels = [name]
    if " / " in name:
        labels.extend(part.strip() for part in name.split(" / ") if part.strip())
    seen = set()
    out = []
    for label in labels:
        key = normalise_label(label)
        if key and key not in seen:
            seen.add(key)
            out.append(label)
    return out


@dataclass(frozen=True)
class ClassRef:
    class_id: int
    class_name: str


@dataclass(frozen=True)
class ClassReview:
    source_class_id: str
    source_class_name: str
    list_section: str
    rating_value: int
    variant: str
    crew_count: int
    rig: str
    spinnaker: str
    match_status: str
    class_id: int | None
    class_name: str | None
    matched_on: tuple[str, ...]
    candidate_class_ids: tuple[int, ...]
    hints: tuple[dict, ...]


def _index(classes: list[dict], aliases: list[dict]) -> tuple[dict[str, set[int]], dict[int, str]]:
    by_id = {}
    names: dict[str, set[int]] = {}
    for row in classes:
        class_id = int(row["class_id"])
        name = row["class_name"]
        by_id[class_id] = name
        names.setdefault(normalise_label(name), set()).add(class_id)
    alias_index: dict[str, set[int]] = {}
    for row in aliases:
        class_id = int(row["class_id"])
        if class_id not in by_id:
            continue
        alias_index.setdefault(normalise_label(row["alias"]), set()).add(class_id)
    return _merge(names, alias_index), by_id


def _merge(left: dict[str, set[int]], right: dict[str, set[int]]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for key in set(left) | set(right):
        out[key] = set(left.get(key, set())) | set(right.get(key, set()))
    return out


def _hints(source_name: str, by_id: dict[int, str], taken: set[int]) -> tuple[dict, ...]:
    """Nearby existing classes for a person to review. These are not matches."""
    source = normalise_label(source_name)
    first = source.split(" ", 1)[0] if source else ""
    found = []
    for class_id, class_name in sorted(by_id.items(), key=lambda item: item[0]):
        if class_id in taken:
            continue
        other = normalise_label(class_name)
        other_first = other.split(" ", 1)[0] if other else ""
        reason = ""
        if len(other) >= 4 and len(source) >= 4 and (
            source.startswith(other + " ") or other.startswith(source + " ")
        ):
            reason = "name prefix only; not an automatic match"
        elif len(first) >= 4 and first == other_first:
            reason = "same first word only; not an automatic match"
        if reason:
            found.append({"class_id": class_id, "class_name": class_name, "reason": reason})
    return tuple(found)


def match_entry(entry: RatingEntry, classes: list[dict], aliases: list[dict]) -> ClassReview:
    index, by_id = _index(classes, aliases)
    matched_on = []
    found: set[int] = set()
    for label in lookup_labels(entry.source_class_name):
        ids = index.get(normalise_label(label), set())
        if not ids:
            continue
        matched_on.append(label)
        found |= ids
    candidates = tuple(sorted(found))
    if len(candidates) == 1:
        status = "matched"
        class_id = candidates[0]
        class_name = by_id[class_id]
    elif len(candidates) == 0:
        status = "unmatched"
        class_id = None
        class_name = None
    else:
        status = "ambiguous"
        class_id = None
        class_name = None
    return ClassReview(
        source_class_id=entry.source_class_id,
        source_class_name=entry.source_class_name,
        list_section=entry.list_section,
        rating_value=entry.rating_value,
        variant=entry.variant,
        crew_count=entry.crew_count,
        rig=entry.rig,
        spinnaker=entry.spinnaker,
        match_status=status,
        class_id=class_id,
        class_name=class_name,
        matched_on=tuple(matched_on),
        candidate_class_ids=candidates,
        hints=_hints(entry.source_class_name, by_id, found),
    )


def build_review(publication: Publication, classes: list[dict], aliases: list[dict]) -> dict:
    rows = [match_entry(entry, classes, aliases) for entry in publication.entries]
    counts = {"matched": 0, "unmatched": 0, "ambiguous": 0}
    encoded = []
    for row in rows:
        counts[row.match_status] += 1
        encoded.append({
            "source_class_id": row.source_class_id,
            "source_class_name": row.source_class_name,
            "list_section": row.list_section,
            "rating_value": row.rating_value,
            "variant": row.variant,
            "crew_count": row.crew_count,
            "rig": row.rig,
            "spinnaker": row.spinnaker,
            "match_status": row.match_status,
            "class_id": row.class_id,
            "class_name": row.class_name,
            "matched_on": list(row.matched_on),
            "candidate_class_ids": list(row.candidate_class_ids),
            "hints": list(row.hints),
        })
    return {
        "system_code": publication.system_code,
        "version_label": publication.version_label,
        "version_number": publication.version_number,
        "effective_from": publication.effective_from,
        "class_master_captured_on": "2026-10-04",
        "counts": counts,
        "rows": encoded,
    }
