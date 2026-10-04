"""Official Portsmouth Yardstick elapsed time to corrected time.

The RYA scheme converts elapsed time with the UK scale of 1000:

    corrected = elapsed_seconds * 1000 / py_number

The 2026 list does not restate the half-second tie. Scoring practice,
including World Sailing race-official guidance on handicap times, rounds
to the nearer whole second and rounds an exact half second up. That rule
is named ``nearest_second_half_up``. The unrounded quotient is kept so a
later decision can re-round the same rating version without guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

FORMULA = "elapsed_seconds * 1000 / py_number"
ROUNDING_RULE = "nearest_second_half_up"
_SCALE = Decimal(1000)
_SECOND = Decimal(1)


@dataclass(frozen=True)
class CorrectedTime:
    """One reproducible PY correction. The version fields are the rating that was used."""

    elapsed_seconds: Decimal
    py_number: int
    exact_seconds: Decimal
    corrected_seconds: int
    formula: str
    rounding_rule: str
    system_code: str
    version_label: str
    version_number: str
    source_class_id: str
    source_class_name: str

    def as_record(self) -> dict:
        return {
            "system_code": self.system_code,
            "version_label": self.version_label,
            "version_number": self.version_number,
            "source_class_id": self.source_class_id,
            "source_class_name": self.source_class_name,
            "py_number": self.py_number,
            "elapsed_seconds": format(self.elapsed_seconds, "f"),
            "exact_seconds": format(self.exact_seconds, "f"),
            "corrected_seconds": self.corrected_seconds,
            "formula": self.formula,
            "rounding_rule": self.rounding_rule,
        }


def parse_elapsed_seconds(value) -> Decimal:
    """Accept seconds, or ``MM:SS`` / ``H:MM:SS`` text. Fractional seconds are allowed."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("elapsed time must be int, Decimal, or H:MM:SS text")
    if isinstance(value, Decimal):
        elapsed = value
    elif isinstance(value, int):
        elapsed = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("elapsed time is empty")
        if ":" in text:
            parts = text.split(":")
            if len(parts) == 2:
                hours = Decimal(0)
                minutes, seconds = parts
            elif len(parts) == 3:
                hours, minutes, seconds = parts
            else:
                raise ValueError(f"unrecognised elapsed time: {value!r}")
            elapsed = Decimal(hours) * 3600 + Decimal(minutes) * 60 + Decimal(seconds)
        else:
            elapsed = Decimal(text)
    else:
        raise TypeError("elapsed time must be int, Decimal, or H:MM:SS text")
    if elapsed < 0:
        raise ValueError("elapsed time cannot be negative")
    return elapsed


def corrected_time(
    elapsed,
    py_number: int,
    *,
    system_code: str,
    version_label: str,
    version_number: str,
    source_class_id: str,
    source_class_name: str,
) -> CorrectedTime:
    """Apply the UK PY formula and round to the nearest second, half up."""
    if isinstance(py_number, bool) or not isinstance(py_number, int):
        raise TypeError("py_number must be an integer")
    if py_number <= 0:
        raise ValueError("py_number must be positive")
    elapsed_seconds = parse_elapsed_seconds(elapsed)
    exact = elapsed_seconds * _SCALE / Decimal(py_number)
    rounded = int(exact.quantize(_SECOND, rounding=ROUND_HALF_UP))
    return CorrectedTime(
        elapsed_seconds=elapsed_seconds,
        py_number=py_number,
        exact_seconds=exact,
        corrected_seconds=rounded,
        formula=FORMULA,
        rounding_rule=ROUNDING_RULE,
        system_code=system_code,
        version_label=version_label,
        version_number=version_number,
        source_class_id=source_class_id,
        source_class_name=source_class_name,
    )


def apply_published_rating(publication, entry, elapsed) -> CorrectedTime:
    """Correct a time with one catalogue row and keep that row's version on the result."""
    return corrected_time(
        elapsed,
        entry.rating_value,
        system_code=publication.system_code,
        version_label=publication.version_label,
        version_number=publication.version_number,
        source_class_id=entry.source_class_id,
        source_class_name=entry.source_class_name,
    )
