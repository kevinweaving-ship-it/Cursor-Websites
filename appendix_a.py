"""World Sailing RRS Appendix A — series order when **assigning rank** on new/updated results.

Low score wins. A tie is not broken by result_id, row id, or DOM order.

A8.1: list counted race scores best → worst; first difference wins.
A8.2: if still tied, last race in sail order (then the race before that, …).
      A8.2 uses those race scores even if a discard is shown in parens.

Do **not** use this to re-order already-published result pages / other events.
Existing sheets keep stored rank. New events and score-saves that compute rank
must use this key instead of result_id.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable, List, Optional, Sequence, Tuple

_SCORE_LEAD = re.compile(r"[-+]?\d+(?:\.\d+)?")
_RACE_KEY = re.compile(r"^R(\d+)$", re.I)
_PAD = 32
_INF = 10**9


def _as_dict(scores: Any) -> dict:
    if isinstance(scores, dict):
        return scores
    if isinstance(scores, str) and scores.strip():
        try:
            parsed = json.loads(scores)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return {}


def parse_race_place(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    m = _SCORE_LEAD.search(text.replace("(", " ").replace(")", " "))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def race_places_sail_order(scores: Any) -> Tuple[List[float], List[float]]:
    """Return (counted_places, all_places_including_discards) in R1..Rn order."""
    d = _as_dict(scores)
    keyed: List[Tuple[int, Any]] = []
    for k, v in d.items():
        m = _RACE_KEY.match(str(k).strip())
        if not m:
            continue
        keyed.append((int(m.group(1)), v))
    keyed.sort(key=lambda x: x[0])
    counted: List[float] = []
    all_places: List[float] = []
    for _n, raw in keyed:
        place = parse_race_place(raw)
        if place is None:
            continue
        all_places.append(place)
        if not (isinstance(raw, str) and "(" in raw and ")" in raw):
            counted.append(place)
    return counted, all_places


def _pad(seq: Sequence[float]) -> Tuple[float, ...]:
    out = list(seq)[:_PAD]
    while len(out) < _PAD:
        out.append(_INF)
    return tuple(out)


def _num(v: Any, default: Any = _INF) -> Any:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def appendix_a_result_sort_key(row: dict) -> tuple:
    """Sort key for one result row. Never includes result_id.

    Nett (low score), then A8.1, then A8.2 last-race chain.
    Stored rank is not used: a wrong rank (or result_id fallback) must not beat the rule.
    """
    counted, all_places = race_places_sail_order(row.get("race_scores"))
    nett = _num(row.get("nett_points_raw"), None)
    if nett is None:
        nett = _num(row.get("nett"), None)
    if nett is None:
        nett = _num(row.get("total_points_raw"), _INF)
    a81 = _pad(sorted(counted))
    a82 = _pad(list(reversed(all_places)))
    return (nett, a81, a82)


def sort_result_rows_appendix_a(rows: Iterable[dict]) -> List[dict]:
    """Stable per-fleet Appendix A order. Block grouping preserved. No result_id."""
    lst = list(rows or [])
    lst.sort(
        key=lambda r: (
            str(r.get("block_id") or ""),
            appendix_a_result_sort_key(r),
        )
    )
    return lst
