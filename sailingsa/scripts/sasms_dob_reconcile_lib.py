#!/usr/bin/env python3
"""Pure reconciliation rules for authorised SAS DOB datasets.

No network I/O. No scraper. Safe to unit-test offline.

Strict rules:
- Match by exact SAS ID string, then verify name.
- Never overwrite an existing full date_of_birth.
- Preserve existing year_of_birth when DOB is unavailable / conflicted.
- Flag birth-year and identity discrepancies.
- Ignore legacy membership status "Lapsed" (do not drive updates from it).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Optional


IGNORED_STATUSES = frozenset({"lapsed"})


@dataclass(frozen=True)
class SourceRecord:
    sas_id: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    date_of_birth: Optional[date] = None
    year_of_birth: Optional[int] = None
    membership_status: str = ""
    source_row: int = 0


@dataclass(frozen=True)
class DbSailor:
    sas_id: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    date_of_birth: Optional[date] = None
    year_of_birth: Optional[int] = None


@dataclass
class Decision:
    action: str
    reason: str
    sas_id: str
    flags: list[str] = field(default_factory=list)
    set_date_of_birth: Optional[date] = None
    set_year_of_birth: Optional[int] = None
    preserve_date_of_birth: Optional[date] = None
    preserve_year_of_birth: Optional[int] = None
    source_row: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.set_date_of_birth is not None:
            d["set_date_of_birth"] = self.set_date_of_birth.isoformat()
        if self.preserve_date_of_birth is not None:
            d["preserve_date_of_birth"] = self.preserve_date_of_birth.isoformat()
        return d


def normalize_sas_id(raw: Any) -> str:
    """Exact SAS ID identity: trim; keep digits as decimal string without leading zeros removed.

    Leading zeros are significant only if present in source/DB as text. We compare the
    trimmed string forms exactly after stripping whitespace. Numeric-only IDs from CSV
    that lost leading zeros stay as their digit string (e.g. '355').
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    # Reject non-digit IDs for this dataset (authorised SAS DOB feed).
    if not re.fullmatch(r"[0-9]+", s):
        return s  # still return; caller may flag
    return s


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def names_match(source: SourceRecord, sailor: DbSailor) -> bool:
    """Verify identity by name after exact SAS ID match.

    Accept if:
    - folded full names equal (when both present), or
    - folded first+last equal (order-insensitive on last/first pair), or
    - source first/last both appear in sailor full_name tokens.
    """
    src_full = _fold(source.full_name) or _fold(f"{source.first_name} {source.last_name}")
    db_full = _fold(sailor.full_name) or _fold(f"{sailor.first_name} {sailor.last_name}")
    if src_full and db_full and src_full == db_full:
        return True

    src_first, src_last = _fold(source.first_name), _fold(source.last_name)
    db_first, db_last = _fold(sailor.first_name), _fold(sailor.last_name)
    if src_first and src_last and db_first and db_last:
        if src_first == db_first and src_last == db_last:
            return True
        # Surname comma form already normalised above; allow swapped display.
        if src_first == db_last and src_last == db_first:
            return True

    if src_first and src_last and db_full:
        tokens = set(db_full.split())
        if src_first in tokens and src_last in tokens:
            return True
    if db_first and db_last and src_full:
        tokens = set(src_full.split())
        if db_first in tokens and db_last in tokens:
            return True
    return False


def parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # ISO-ish
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def parse_year(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        y = int(str(value).strip()[:4])
    except (TypeError, ValueError):
        return None
    if y < 1900 or y > date.today().year + 1:
        return None
    return y


def effective_source_year(src: SourceRecord) -> Optional[int]:
    if src.date_of_birth is not None:
        return src.date_of_birth.year
    return src.year_of_birth


def effective_db_year(sailor: DbSailor) -> Optional[int]:
    if sailor.date_of_birth is not None:
        return sailor.date_of_birth.year
    return sailor.year_of_birth


def status_ignored(status: str) -> bool:
    return _fold(status) in IGNORED_STATUSES


def decide(source: SourceRecord, sailor: Optional[DbSailor]) -> Decision:
    """Compute a single-row reconciliation decision. Never mutates DB state."""
    sas_id = normalize_sas_id(source.sas_id)
    base = dict(source_row=source.source_row, sas_id=sas_id)

    if not sas_id or not re.fullmatch(r"[0-9]+", sas_id):
        return Decision(action="skip", reason="invalid_sas_id", flags=["invalid_sas_id"], **base)

    if status_ignored(source.membership_status):
        return Decision(
            action="ignore",
            reason="legacy_lapsed_status",
            flags=["ignored_lapsed"],
            details={"membership_status": source.membership_status},
            **base,
        )

    if sailor is None:
        return Decision(action="flag", reason="sas_id_not_found", flags=["sas_id_not_found"], **base)

    if normalize_sas_id(sailor.sas_id) != sas_id:
        return Decision(
            action="flag",
            reason="sas_id_mismatch",
            flags=["sas_id_mismatch"],
            details={"db_sas_id": sailor.sas_id},
            **base,
        )

    if not names_match(source, sailor):
        return Decision(
            action="flag",
            reason="identity_name_mismatch",
            flags=["identity_discrepancy"],
            details={
                "source_name": source.full_name or f"{source.first_name} {source.last_name}".strip(),
                "db_name": sailor.full_name or f"{sailor.first_name} {sailor.last_name}".strip(),
            },
            preserve_date_of_birth=sailor.date_of_birth,
            preserve_year_of_birth=sailor.year_of_birth,
            **base,
        )

    src_dob = source.date_of_birth
    src_yob = source.year_of_birth
    if src_dob is None and src_yob is None:
        return Decision(action="skip", reason="source_missing_birth", flags=["source_missing_birth"], **base)

    if src_dob is not None and src_yob is not None and src_dob.year != src_yob:
        return Decision(
            action="flag",
            reason="source_internal_year_conflict",
            flags=["source_internal_year_conflict"],
            details={"source_dob": src_dob.isoformat(), "source_yob": src_yob},
            preserve_date_of_birth=sailor.date_of_birth,
            preserve_year_of_birth=sailor.year_of_birth,
            **base,
        )

    src_year = effective_source_year(source)
    db_year = effective_db_year(sailor)

    # --- Existing full DOB is sacred ---
    if sailor.date_of_birth is not None:
        flags = ["preserve_existing_dob"]
        if src_year is not None and src_year != sailor.date_of_birth.year:
            flags.append("birth_year_discrepancy")
            return Decision(
                action="flag",
                reason="birth_year_conflict_existing_dob",
                flags=flags,
                preserve_date_of_birth=sailor.date_of_birth,
                preserve_year_of_birth=sailor.year_of_birth or sailor.date_of_birth.year,
                details={
                    "existing_dob": sailor.date_of_birth.isoformat(),
                    "source_year": src_year,
                    "source_dob": src_dob.isoformat() if src_dob else None,
                },
                **base,
            )
        if src_dob is not None and src_dob != sailor.date_of_birth:
            flags.append("source_dob_differs_preserved")
            return Decision(
                action="flag",
                reason="existing_dob_preserved",
                flags=flags,
                preserve_date_of_birth=sailor.date_of_birth,
                preserve_year_of_birth=sailor.year_of_birth or sailor.date_of_birth.year,
                details={
                    "existing_dob": sailor.date_of_birth.isoformat(),
                    "source_dob": src_dob.isoformat(),
                },
                **base,
            )
        return Decision(
            action="noop",
            reason="existing_dob_unchanged",
            flags=flags,
            preserve_date_of_birth=sailor.date_of_birth,
            preserve_year_of_birth=sailor.year_of_birth or sailor.date_of_birth.year,
            **base,
        )

    # --- No full DOB; may have YOB ---
    if sailor.year_of_birth is not None:
        if src_year is not None and src_year != sailor.year_of_birth:
            return Decision(
                action="flag",
                reason="birth_year_conflict_existing_yob",
                flags=["birth_year_discrepancy", "preserve_existing_yob"],
                preserve_year_of_birth=sailor.year_of_birth,
                details={
                    "existing_yob": sailor.year_of_birth,
                    "source_year": src_year,
                    "source_dob": src_dob.isoformat() if src_dob else None,
                },
                **base,
            )
        # Years agree (or source year missing after earlier checks — shouldn't happen)
        if src_dob is not None:
            return Decision(
                action="apply",
                reason="fill_dob_matching_existing_yob",
                flags=["fill_dob", "preserve_existing_yob"],
                set_date_of_birth=src_dob,
                preserve_year_of_birth=sailor.year_of_birth,
                **base,
            )
        return Decision(
            action="noop",
            reason="existing_yob_unchanged",
            flags=["preserve_existing_yob"],
            preserve_year_of_birth=sailor.year_of_birth,
            **base,
        )

    # --- Empty birth fields ---
    if src_dob is not None:
        return Decision(
            action="apply",
            reason="set_dob_and_yob",
            flags=["set_dob", "set_yob"],
            set_date_of_birth=src_dob,
            set_year_of_birth=src_dob.year,
            **base,
        )
    return Decision(
        action="apply",
        reason="set_yob_only",
        flags=["set_yob"],
        set_year_of_birth=src_yob,
        **base,
    )


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize(decisions: Iterable[Decision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in decisions:
        counts[d.action] = counts.get(d.action, 0) + 1
        for flag in d.flags:
            key = f"flag:{flag}"
            counts[key] = counts.get(key, 0) + 1
    return counts


def source_from_mapping(row: Mapping[str, Any], row_num: int = 0) -> SourceRecord:
    """Map flexible authorised-dataset headers onto SourceRecord."""
    def g(*keys: str) -> Any:
        lower = {str(k).strip().lower(): v for k, v in row.items()}
        for key in keys:
            if key.lower() in lower and lower[key.lower()] not in (None, ""):
                return lower[key.lower()]
        return None

    sas = normalize_sas_id(g("sas_id", "sa_sailing_id", "sa_id", "id"))
    dob = parse_date(g("date_of_birth", "dob", "birth_date", "birthdate"))
    yob = parse_year(g("year_of_birth", "yob", "birth_year", "born"))
    return SourceRecord(
        sas_id=sas,
        first_name=str(g("first_name", "firstname", "given_name") or "").strip(),
        last_name=str(g("last_name", "lastname", "surname") or "").strip(),
        full_name=str(g("full_name", "name", "member_name") or "").strip(),
        date_of_birth=dob,
        year_of_birth=yob,
        membership_status=str(g("membership_status", "status", "member_status") or "").strip(),
        source_row=row_num,
    )
