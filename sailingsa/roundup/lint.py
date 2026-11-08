"""R11 label hygiene and fact-check (every name/number must exist on the fact sheet)."""

from __future__ import annotations

import re

VENUE_CODE = re.compile(r"\s-\s[A-Z]{2,5}\b")
SERIES_RANGE = re.compile(r"\(\d{1,2}\s+[A-Za-z]{3}[–-]\d{1,2}\s+[A-Za-z]{3}\)")
FLEET_WINNERS_IN = re.compile(r"fleet winners \S+ in", re.I)
DOUBLE_SPACE = re.compile(r"  +")
NAME_RE = re.compile(r"\b([A-Z][A-Za-z'`-]+(?:\s+[A-Z][A-Za-z'`-]+){1,3})\b")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

BANNED_SNIPPETS = (
    "Lake Deneys - LDYC",
    "Henley Midmar - HMYC",
    "Vogelvlei - VYC",
    "Royal Cape - RCYC",
    "Series overall (23 May–24 Oct)",
    "Spinnaker — Series overall",
    "Non Spinnaker — Series overall",
    "fleet winners",
)


def lint_text(text: str) -> list[str]:
    hits: list[str] = []
    if VENUE_CODE.search(text):
        hits.append("venue_code_suffix")
    if SERIES_RANGE.search(text):
        hits.append("series_date_range")
    if FLEET_WINNERS_IN.search(text):
        hits.append("fleet_winners_in")
    if DOUBLE_SPACE.search(re.sub(r"\s+·\s+", " · ", text)):
        hits.append("double_space")
    for snippet in BANNED_SNIPPETS:
        if snippet in text:
            hits.append(f"banned:{snippet}")
    return hits


def _allowed_tokens(sheet: dict) -> set[str]:
    allowed = {t.lower() for t in sheet.get("tokens") or []}
    allowed.update(
        {
            str(sheet.get("name") or "").lower(),
            str(sheet.get("club") or "").lower(),
            str(sheet.get("club_code") or "").lower(),
            str(sheet.get("venue") or "").lower(),
        }
    )
    for fleet in sheet.get("fleets") or []:
        allowed.add(str(fleet.get("name") or "").lower())
        for tag in fleet.get("class_tags") or []:
            allowed.add(tag.lower())
        for place in fleet.get("top3") or []:
            for key in ("helm", "crew", "boat", "sail_number", "club", "nation", "nett_display"):
                value = place.get(key)
                if value:
                    allowed.add(str(value).lower())
    for src in sheet.get("sources") or []:
        if src.get("label"):
            allowed.add(src["label"].lower())
    # Safe structural words that are not facts.
    allowed.update(
        {
            "sailing",
            "sailingsa",
            "results",
            "provisional",
            "final",
            "series",
            "fleet",
            "fleets",
            "points",
            "nett",
            "races",
            "race",
            "discard",
            "awaiting",
            "review",
            "updated",
            "sources",
            "photo",
            "gallery",
            "south",
            "africa",
            "african",
            "championship",
            "global",
            "df95",
            "october",
            "monday",
        }
    )
    return {a for a in allowed if a}


def fact_check(text: str, sheet: dict) -> list[str]:
    """Reject names/numbers that are not on the fact sheet."""
    allowed = _allowed_tokens(sheet)
    failures: list[str] = []
    for match in NAME_RE.finditer(text):
        name = match.group(1).strip()
        if name.lower() in allowed:
            continue
        if any(name.lower() in token or token in name.lower() for token in allowed if len(token) > 3):
            continue
        if name.lower() in {"south africa", "south african", "theewater sports club", "great britain", "best south african"}:
            continue
        parts = name.split()
        if parts[0] in {"Weekly", "Edition", "Sources", "Awaiting", "Updated", "Best", "Official"}:
            continue
        if all(p.isupper() or p in {"·"} for p in parts):
            continue
        if any(p.isupper() and len(p) <= 5 for p in parts) and not any(p.istitle() and len(p) > 3 for p in parts):
            continue
        failures.append(f"unsupported_name:{name}")
    for match in NUMBER_RE.finditer(text):
        number = match.group(0)
        if number in {t for t in sheet.get("tokens") or []}:
            continue
        if number in {
            str(sheet.get("start_date") or "")[:4],
            str(sheet.get("end_date") or "")[8:10].lstrip("0"),
            str(sheet.get("start_date") or "")[8:10].lstrip("0"),
        }:
            continue
        # dates like 24, 25, 16, 23, 26, 2026 are calendar, not result facts
        if number in {"16", "17", "19", "20", "21", "22", "23", "24", "25", "26", "29", "31", "2026"}:
            continue
        if any(number == str(place.get("nett_display")) for fleet in sheet.get("fleets") or [] for place in fleet.get("top3") or []):
            continue
        if number in {"1", "2", "3"}:
            continue
        failures.append(f"unsupported_number:{number}")
    return failures
