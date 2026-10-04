"""Versioned rating catalogue. Portsmouth Yardstick is the first system.

The catalogue is separate from classes.rating_system and results.handicap.
Matching never creates a class.
"""

from py_rating.calculation import (
    FORMULA,
    ROUNDING_RULE,
    CorrectedTime,
    apply_published_rating,
    corrected_time,
    parse_elapsed_seconds,
)
from py_rating.catalogue import Publication, load_rya_py_2026
from py_rating.match import ClassReview, build_review, match_entry

__all__ = [
    "FORMULA",
    "ROUNDING_RULE",
    "CorrectedTime",
    "ClassReview",
    "Publication",
    "apply_published_rating",
    "build_review",
    "corrected_time",
    "load_rya_py_2026",
    "match_entry",
    "parse_elapsed_seconds",
]
