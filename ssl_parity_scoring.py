"""
SSL parity scoring (Phase 2 / Step 4).

Official and checksum modes: SSL Categories 1–7 only. Category 8 is rejected.

SSA mode: exactly two boats score as Category 8 (first 2.00, second 1.00),
then class, restriction, and time coefficients. One boat scores zero.
SSA Category 9 is not implemented.

Points = placement(category, place, N) × class × restriction × time.
Skipper/helm and crew receive the same points for the same result.

Championship status is passed explicitly into the classifier
(`is_championship`, `championship_exception` / `official_status`).
Event name and SSL category are not used to guess championship.

Does not recalculate rankings into the database, export published.json, or deploy.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Optional

from ssl_parity_classification import (
    MODE_CHECKSUM,
    MODE_OFFICIAL,
    MODE_SSA,
    SSL_CATEGORY_SSA_TWO_BOAT,
    classify_ssl_category,
)

# Official SSL category winner points (Categories 1–7). Not SSA 500/350/250/150.
CATEGORY_BASE = {
    1: 4000.0,  # MAJOR
    2: 2500.0,  # WORLD
    3: 1000.0,  # CONTINENTAL
    4: 500.0,  # INTERNATIONAL
    5: 250.0,  # NATIONAL
    6: 100.0,  # REGIONAL
    7: 10.0,  # LOCAL
}

CATEGORY_NAMES = {
    1: "MAJOR",
    2: "WORLD",
    3: "CONTINENTAL",
    4: "INTERNATIONAL",
    5: "NATIONAL",
    6: "REGIONAL",
    7: "LOCAL",
    SSL_CATEGORY_SSA_TWO_BOAT: "SSA_8",
}

# SSA Category 8 placement only (exactly two boats). Not a Categories 1–7 winner table.
SSA_CAT8_FIRST = 2.00
SSA_CAT8_SECOND = 1.00

# Last ranked gets 1 point, except Category 1 last ranked gets 50.
DEFAULT_LAST_PLACE = 1.0
CATEGORY_1_LAST_PLACE = 50.0

# 4 linear stages on absolute place: 1→5, 5→10, 10→20, 20→last.
# Stage-2 end 0.19 is the official short-fleet interpolation that makes
# Cat 5 P6 of N≥10 = 109.5 (Sean ILCA Nationals P6/N13, Olympic, open, recent).
PLACE_KNOTS = (
    (1, 1.00),
    (5, 0.50),
    (10, 0.19),
    (20, 0.08),
)

FULL_VALUE_WEEKS = 52
ZERO_VALUE_WEEKS = 104
AGE_HALF = 0.5

OPEN_FULL = 1.0
OPEN_RESTRICTED = 0.40
OPEN_DOUBLE_RESTRICTED = 0.20

CLASS_OLYMPIC = 1.0
CLASS_WS = 0.85
CLASS_OTHER = 0.75

OLYMPIC_CLASSES = {
    "ilca 7",
    "ilca 6",
    "ilca7",
    "ilca6",
    "laser",
    "laser radial",
    "49er",
    "49erfx",
    "49er fx",
    "nacra 17",
    "470",
    "470 mixed",
}

WS_CLASSES = {
    "ilca 4.7",
    "ilca 4",
    "optimist a",
    "optimist b",
    "optimist",
    "420",
    "29er",
    "finn",
    "505",
    "5o5",
    "hobie 16",
    "hobie tiger",
    "j70",
    "j/70",
    "star",
    "snipe",
    "moth",
    "tp52",
    "tp 52",
    "melges 24",
    "dragon",
    "sunfish",
}

CLASS_COEFFICIENT = {}
CLASS_COEFFICIENT.update({name: CLASS_OLYMPIC for name in OLYMPIC_CLASSES})
CLASS_COEFFICIENT.update({name: CLASS_WS for name in WS_CLASSES})
# Remaining local/national classes (Status 3).
CLASS_COEFFICIENT.update(
    {
        "sonnet": CLASS_OTHER,
        "dabchick": CLASS_OTHER,
        "extra": CLASS_OTHER,
        "mirror": CLASS_OTHER,
        "j22": CLASS_OTHER,
        "j/22": CLASS_OTHER,
        "hobie 14": CLASS_OTHER,
        "flying 15": CLASS_OTHER,
        "flying fifteen": CLASS_OTHER,
        "rs tera": CLASS_OTHER,
        "topper 5.3": CLASS_OTHER,
        "soling": CLASS_OTHER,
        "windsurfer lt": CLASS_OTHER,
        "stadt 23": CLASS_OTHER,
        "hunter": CLASS_OTHER,
        "hunter 19": CLASS_OTHER,
        "l26": CLASS_OTHER,
        "halcat": CLASS_OTHER,
        "topaz": CLASS_OTHER,
        "pacer 27": CLASS_OTHER,
        "dart 18": CLASS_OTHER,
    }
)

DEFAULT_CLASS_COEFFICIENT = CLASS_OTHER

PUBLISHED_AS_AT = date(2026, 7, 27)


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def class_coefficient(class_name: Any) -> float:
    key = str(class_name or "").strip().lower()
    if key in CLASS_COEFFICIENT:
        return CLASS_COEFFICIENT[key]
    return DEFAULT_CLASS_COEFFICIENT


def open_coefficient(is_open: Any = True, restriction_count: Any = 0) -> float:
    """Type 1 open 100%; Type 2 restricted 40%; two or more restrictions 20%."""
    try:
        n_rest = int(restriction_count or 0)
    except (TypeError, ValueError):
        n_rest = 0
    if n_rest >= 2:
        return OPEN_DOUBLE_RESTRICTED
    if is_open is False or n_rest >= 1:
        return OPEN_RESTRICTED
    return OPEN_FULL


def parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def age_weeks(event_date: Any, as_at: Any = None) -> Optional[float]:
    start = parse_date(event_date)
    end = parse_date(as_at) or PUBLISHED_AS_AT
    if start is None:
        return None
    return (end - start).days / 7.0


def time_coefficient(event_date: Any, as_at: Any = None) -> float:
    """Official time validity: ≤52 weeks 100%; 53–104 weeks 50%; older 0%."""
    weeks = age_weeks(event_date, as_at)
    if weeks is None:
        return 1.0
    if weeks <= FULL_VALUE_WEEKS:
        return 1.0
    if weeks <= ZERO_VALUE_WEEKS:
        return AGE_HALF
    return 0.0


def age_factor(event_date: Any, as_at: Any = None) -> float:
    """Alias of time_coefficient (SSL time validity)."""
    return time_coefficient(event_date, as_at)


def last_place_points(category: int) -> float:
    if int(category) == 1:
        return CATEGORY_1_LAST_PLACE
    return DEFAULT_LAST_PLACE


def _placement_knots(category: int, fleet: int) -> list[tuple[int, float]]:
    """
    Official 4-stage table, short-fleet interpolated.

    Knots at places 1, 5, 10, 20 are fractions of the category winner.
    If the fleet is shorter than a knot, that knot is dropped and last
    place is pinned to 1 (or 50 for Category 1). Places between remaining
    knots are linear.
    """
    winner = CATEGORY_BASE[category]
    last = last_place_points(category)
    n = max(int(fleet), 1)
    knots: list[tuple[int, float]] = []
    for place, frac in PLACE_KNOTS:
        if place > n:
            break
        if place == n:
            knots.append((n, last))
            return knots
        knots.append((place, winner * frac))
    if not knots or knots[-1][0] != n:
        knots.append((n, last))
    else:
        knots[-1] = (n, last)
    return knots


def ssa_cat8_placement(place: Any, fleet: Any) -> float:
    """SSA Category 8: exactly two boats; first 2.00, second 1.00. Else 0."""
    try:
        p = int(place)
        n = int(fleet)
    except (TypeError, ValueError):
        return 0.0
    if n != 2 or p < 1:
        return 0.0
    if p == 1:
        return SSA_CAT8_FIRST
    if p == 2:
        return SSA_CAT8_SECOND
    return 0.0


def placement_points(category: Any, place: Any, fleet: Any = None) -> float:
    """Placement points: Categories 1–7 official table, or SSA Category 8 two-boat."""
    try:
        cat = int(category)
        p = int(place)
    except (TypeError, ValueError):
        return 0.0
    if p < 1:
        return 0.0
    try:
        n = int(fleet) if fleet is not None else p
    except (TypeError, ValueError):
        n = p
    if n < 1:
        return 0.0
    if cat == SSL_CATEGORY_SSA_TWO_BOAT:
        return ssa_cat8_placement(p, n)
    if cat not in CATEGORY_BASE:
        return 0.0
    if p > n:
        p = n
    knots = _placement_knots(cat, n)
    if p <= knots[0][0]:
        return knots[0][1]
    for i in range(1, len(knots)):
        p0, v0 = knots[i - 1]
        p1, v1 = knots[i]
        if p <= p1:
            if p1 == p0:
                return v1
            t = (p - p0) / float(p1 - p0)
            return v0 + (v1 - v0) * t
    return knots[-1][1]


def place_factor(place: Any, fleet: Any = None, category: Any = 5) -> float:
    """Placement as a fraction of the category winner (for diagnostics)."""
    try:
        cat = int(category)
    except (TypeError, ValueError):
        cat = 5
    if cat == SSL_CATEGORY_SSA_TWO_BOAT:
        pts = placement_points(cat, place, fleet)
        return pts / SSA_CAT8_FIRST if SSA_CAT8_FIRST else 0.0
    if cat not in CATEGORY_BASE:
        return 0.0
    pts = placement_points(cat, place, fleet)
    winner = CATEGORY_BASE[cat]
    if winner <= 0:
        return 0.0
    return pts / winner


@dataclass(frozen=True)
class SSLScore:
    points: float
    eligible: bool
    category: Optional[int]
    category_name: Optional[str]
    category_base: float
    class_coefficient: float
    open_coefficient: float
    place_factor: float
    placement_points: float
    age_factor: float
    role: Optional[str]
    ssa_rating: Optional[int]
    reason: str

    def as_dict(self) -> dict:
        return {
            "points": self.points,
            "eligible": self.eligible,
            "category": self.category,
            "category_name": self.category_name,
            "category_base": self.category_base,
            "class_coefficient": self.class_coefficient,
            "open_coefficient": self.open_coefficient,
            "place_factor": self.place_factor,
            "placement_points": self.placement_points,
            "age_factor": self.age_factor,
            "role": self.role,
            "ssa_rating": self.ssa_rating,
            "reason": self.reason,
        }


def _ineligible_score(
    class_name: Any,
    event_date: Any,
    as_at: Any,
    role_key: Optional[str],
    ssa_rating: Optional[int],
    is_open: Any,
    restriction_count: Any,
    reason: str,
) -> SSLScore:
    return SSLScore(
        points=0.0,
        eligible=False,
        category=None,
        category_name=None,
        category_base=0.0,
        class_coefficient=class_coefficient(class_name),
        open_coefficient=open_coefficient(is_open, restriction_count),
        place_factor=0.0,
        placement_points=0.0,
        age_factor=time_coefficient(event_date, as_at),
        role=role_key,
        ssa_rating=ssa_rating,
        reason=reason,
    )


def score_result(
    event_name: Any,
    valid_boats: Any,
    place: Any,
    class_name: Any,
    event_date: Any = None,
    role: Any = None,
    official_status: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    ssa_rating: Optional[int] = None,
    as_at: Any = None,
    category: Optional[int] = None,
    is_championship: Optional[bool] = None,
    championship_exception: Optional[str] = None,
    championship: Optional[bool] = None,
    exception: Optional[str] = None,
    is_open: Any = True,
    restriction_count: Any = 0,
    mode: Optional[str] = None,
) -> SSLScore:
    """
    Score one result.

    Official/checksum: Categories 1–7 only; Category 8 is rejected.
    SSA mode: N=1 scores zero; N=2 is Category 8 (first 2.00, second 1.00)
    then class × restriction × time. Category 9 is not implemented.

    `role` (helm/skipper/crew) does not change points. Same boat, same place,
    same fleet → same points for skipper and crew.

    `ssa_rating` is echoed only; it is not a multiplier.
    """
    champ_flag = is_championship if is_championship is not None else championship
    champ_exc = championship_exception if championship_exception is not None else exception
    classification = classify_ssl_category(
        event_name,
        valid_boats,
        official_status=official_status,
        metadata=metadata,
        ssa_rating=ssa_rating,
        championship=champ_flag,
        exception=champ_exc,
        mode=mode,
    )
    resolved_mode = classification.mode
    cat = category if category is not None else classification.category
    if resolved_mode == MODE_SSA and classification.category == SSL_CATEGORY_SSA_TWO_BOAT:
        cat = SSL_CATEGORY_SSA_TWO_BOAT
    role_key = str(role or "").strip().lower() or None

    def _reject(reason: str) -> SSLScore:
        return _ineligible_score(
            class_name,
            event_date,
            as_at,
            role_key,
            ssa_rating,
            is_open,
            restriction_count,
            reason,
        )

    if resolved_mode in (MODE_OFFICIAL, MODE_CHECKSUM) and cat == SSL_CATEGORY_SSA_TWO_BOAT:
        return _reject("official/checksum mode rejects SSA Category 8")

    if not classification.eligible or cat is None:
        return _reject(classification.reason or "ineligible")

    try:
        cat_i = int(cat)
    except (TypeError, ValueError):
        cat_i = -1

    if cat_i == SSL_CATEGORY_SSA_TWO_BOAT:
        if resolved_mode != MODE_SSA:
            return _reject("official/checksum mode rejects SSA Category 8")
        placed = ssa_cat8_placement(place, valid_boats)
        if placed <= 0:
            return _reject("SSA Category 8 is only for exactly two boats")
        coeff = class_coefficient(class_name)
        open_c = open_coefficient(is_open, restriction_count)
        pf = place_factor(place, valid_boats, cat_i)
        af = time_coefficient(event_date, as_at)
        points = _round2(placed * coeff * open_c * af)
        return SSLScore(
            points=points,
            eligible=True,
            category=cat_i,
            category_name=CATEGORY_NAMES.get(cat_i),
            category_base=SSA_CAT8_FIRST,
            class_coefficient=coeff,
            open_coefficient=open_c,
            place_factor=pf,
            placement_points=placed,
            age_factor=af,
            role=role_key,
            ssa_rating=ssa_rating,
            reason="SSA Cat 8 placement × class × restriction × time; role ignored",
        )

    if cat_i not in CATEGORY_BASE:
        return _reject(
            "SSA category 9 not implemented"
            if cat_i == 9
            else "SSA categories 8–9 not implemented"
        )

    base = CATEGORY_BASE[cat_i]
    coeff = class_coefficient(class_name)
    open_c = open_coefficient(is_open, restriction_count)
    placed = placement_points(cat_i, place, valid_boats)
    pf = place_factor(place, valid_boats, cat_i)
    af = time_coefficient(event_date, as_at)
    raw = placed * coeff * open_c * af
    points = _round2(raw)
    return SSLScore(
        points=points,
        eligible=True,
        category=cat_i,
        category_name=CATEGORY_NAMES.get(cat_i)
        if category is not None
        else (classification.category_name or CATEGORY_NAMES.get(cat_i)),
        category_base=base,
        class_coefficient=coeff,
        open_coefficient=open_c,
        place_factor=pf,
        placement_points=placed,
        age_factor=af,
        role=role_key,
        ssa_rating=ssa_rating,
        reason="placement × class × restriction × time; role ignored",
    )


def score_published_row(
    row: Mapping[str, Any],
    as_at: Any = None,
    reclassify: bool = True,
) -> SSLScore:
    live_cat = row.get("category") if not reclassify else None
    championship = row.get("championship") if isinstance(row, Mapping) else None
    if championship in ("true", "True", 1):
        championship = True
    elif championship in ("false", "False", 0):
        championship = False
    elif championship is not True and championship is not False:
        championship = None
    is_open = True
    if isinstance(row, Mapping) and "is_open" in row:
        is_open = row.get("is_open")
    return score_result(
        event_name=row.get("event") or row.get("eventSlug") or row.get("regattaId"),
        valid_boats=row.get("fleet"),
        place=row.get("place"),
        class_name=row.get("className"),
        event_date=row.get("eventDate"),
        role=row.get("role"),
        official_status=row.get("official_status") if isinstance(row, Mapping) else None,
        metadata=row,
        ssa_rating=row.get("rating"),
        as_at=as_at or PUBLISHED_AS_AT,
        category=live_cat,
        is_championship=championship,
        championship_exception=row.get("exception") if isinstance(row, Mapping) else None,
        is_open=is_open,
        restriction_count=row.get("restriction_count") if isinstance(row, Mapping) else 0,
        mode=MODE_CHECKSUM,
    )


# ---------------------------------------------------------------------------
# Inline self-check
#
# live_points is comparison metadata only. Never use it to derive expect_points.
# WCDC 0.79 is excluded: SAS and WoS finishing positions differ.
# ---------------------------------------------------------------------------

_TESTS = [
    {
        "id": "sean-ilca-nationals-p6-n13-109.5",
        "event": "2026-05-03 ILCA Nationals",
        "n": 13,
        "place": 6,
        "class_name": "Ilca 7",
        "event_date": "2026-05-03",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "is_open": True,
        "expect_points": 109.5,
        "expect_category": 5,
        "sailor": "Sean Kavanagh",
        "live_points": 108.0,  # SSA published comparison only; not the expect
    },
    {
        "id": "thomas-henshilwood-2026-rsa-29er-nationals-p4-n10",
        "event": "2026 RSA 29er Nationals",
        "n": 10,
        "place": 4,
        "class_name": "29er",
        "event_date": "2026-03-30",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "is_open": True,
        "expect_category": 5,
        # Cat5 P4/N10 raw 156.25 × 0.85 WS × 1.00 open = 132.81
        "expect_points": 132.81,
        "compare_roles": ("crew", "helm"),
        "sailor": "Thomas Henshilwood",
        "sa_sailing_id": 9612,
        "slug": "thomas-henshilwood",
        # WoS 35.16 is 156.25 × 0.225 undocumented Junior/non-open. Not the expect.
        "live_points": 35.16,
        "live_points_note": (
            "WoS 35.16 = 156.25 × 0.225 undocumented Junior/non-open; "
            "official is 156.25 × 0.85 × 1.00 = 132.81"
        ),
    },
    {
        "id": "ilca6-nationals-p1",
        "event": "2026-05-03 ILCA Nationals",
        "n": 29,
        "place": 1,
        "class_name": "Ilca 6",
        "event_date": "2026-05-03",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "expect_points": 250.0,
        "expect_category": 5,
    },
    {
        "id": "youth-nationals-optA-p1-non-open",
        "event": "2025-12-19 SA Youth Nationals Dec 2025",
        "n": 33,
        "place": 1,
        "class_name": "Optimist A",
        "event_date": "2025-12-19",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "is_open": False,
        "expect_points": 85.0,  # 250 × 0.85 WS × 0.40 non-open
        "expect_category": 5,
    },
    {
        "id": "420-nationals-p2",
        "event": "2025-10-04 420 National Championship Results",
        "n": 18,
        "place": 2,
        "class_name": "420",
        "event_date": "2025-10-04",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "expect_points": 185.94,  # 218.75 × 0.85
        "expect_category": 5,
    },
    {
        "id": "29er-nationals-n6-drops-to-cat6-p1",
        "event": "2025-05-04 29er Nationals Results",
        "n": 6,
        "place": 1,
        "class_name": "29er",
        "event_date": "2025-05-04",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "expect_category": 6,
        "expect_points": 42.5,  # 100 × 0.85 × 0.5 age
    },
    {
        "id": "sean-cape-classic-sonnet-p2-now-cat6",
        "event": "2026-02-16 HYC Cape Classic 2026",
        "n": 15,
        "place": 2,
        "class_name": "Sonnet",
        "event_date": "2026-02-16",
        "ssa_rating": 250,
        "is_championship": False,
        "expect_category": 6,
        "expect_points": 65.63,  # 87.5 placement × 0.75
        "live_points": 164.06,
    },
    {
        "id": "overberg-optA-p1-drops-to-cat7",
        "event": "2025-04-05 Overberg Regional Championships 2025",
        "n": 5,
        "place": 1,
        "class_name": "Optimist A",
        "event_date": "2025-04-05",
        "ssa_rating": 150,
        "is_championship": True,
        "official_status": "regional_championship",
        "expect_category": 7,
        "expect_points": 4.25,  # 10 × 0.85 × 0.5 age
        "live_points": 4.25,
    },
    {
        "id": "helm-crew-same-points",
        "event": "2025-10-04 420 National Championship Results",
        "n": 18,
        "place": 4,
        "class_name": "420",
        "event_date": "2025-10-04",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "expect_points": 132.81,  # 156.25 × 0.85
        "expect_category": 5,
        "compare_roles": ("helm", "crew"),
    },
    {
        "id": "ssa-rating-not-used",
        "event": "Club Open Regatta",
        "n": 20,
        "place": 1,
        "class_name": "Ilca 6",
        "event_date": "2026-06-01",
        "ssa_rating": 500,
        "expect_category": 6,
        "expect_points": 100.0,
    },
    {
        "id": "n2-ineligible",
        "event": "ILCA Nationals",
        "n": 2,
        "place": 1,
        "class_name": "Ilca 6",
        "event_date": "2026-05-03",
        "ssa_rating": 500,
        "is_championship": True,
        "official_status": "national_championship",
        "expect_points": 0.0,
        "expect_eligible": False,
    },
    {
        "id": "cat1-winner-4000",
        "event": "Olympic Games",
        "n": 40,
        "place": 1,
        "class_name": "Ilca 7",
        "event_date": "2026-06-01",
        "category": 1,
        "is_championship": True,
        "official_status": "world_championship",
        "expect_category": 1,
        "expect_points": 4000.0,
    },
    {
        "id": "ssa-cat8-not-implemented",
        "event": "Handicap Club Series",
        "n": 20,
        "place": 1,
        "class_name": "Sonnet",
        "event_date": "2026-06-01",
        "category": 8,
        "expect_points": 0.0,
        "expect_eligible": False,
    },
    {
        "id": "championship-exception-national-n9-cat6",
        "event": "Club Open Regatta",
        "n": 9,
        "place": 1,
        "class_name": "Ilca 7",
        "event_date": "2026-06-01",
        "is_championship": True,
        "championship_exception": "national_championship",
        "expect_category": 6,
        "expect_points": 100.0,
    },
    {
        "id": "time-midterm-50-percent",
        "event": "Club Open Regatta",
        "n": 20,
        "place": 1,
        "class_name": "Ilca 6",
        "event_date": "2025-01-01",
        "as_at": "2026-07-27",
        "expect_category": 6,
        "expect_points": 50.0,
    },
    # --- SSA Category 8 (exactly two boats) ---
    {
        "id": "ssa-n1-scores-zero",
        "event": "Club Open Regatta",
        "n": 1,
        "place": 1,
        "class_name": "Optimist",
        "event_date": "2023-12-01",
        "as_at": "2024-01-01",
        "mode": "ssa",
        "expect_points": 0.0,
        "expect_eligible": False,
        "expect_category": None,
    },
    {
        "id": "ssa-cat8-p1-n2-first-2.00",
        "event": "Club Open Regatta",
        "n": 2,
        "place": 1,
        "class_name": "Ilca 7",
        "event_date": "2026-06-01",
        "mode": "ssa",
        "is_open": True,
        "expect_category": 8,
        "expect_points": 2.0,  # 2.00 × 1.00 Olympic × 1.00 restriction × 1.00 time
    },
    {
        "id": "ssa-cat8-p1-n2-restricted",
        "event": "Club Open Regatta",
        "n": 2,
        "place": 1,
        "class_name": "Ilca 7",
        "event_date": "2026-06-01",
        "mode": "ssa",
        "is_open": False,
        "expect_category": 8,
        "expect_points": 0.8,  # 2.00 × 1.00 × 0.40 restriction
    },
    {
        "id": "timothy-weaving-2023-optimist-p2-n2",
        "event": "2023 Optimist",
        "n": 2,
        "place": 2,
        "class_name": "Optimist",
        "event_date": "2023-12-01",
        "as_at": "2024-01-01",
        "mode": "ssa",
        "is_open": True,
        "expect_category": 8,
        # 1.00 × 0.85 WS × 1.00 restriction × 1.00 time
        "expect_points": 0.85,
        "sailor": "Timothy Weaving",
        "sa_sailing_id": 21172,
        "slug": "timothy-weaving",
    },
    {
        "id": "checksum-n2-rejects-cat8",
        "event": "2023 Optimist",
        "n": 2,
        "place": 2,
        "class_name": "Optimist",
        "event_date": "2023-12-01",
        "as_at": "2024-01-01",
        "mode": "checksum",
        "expect_points": 0.0,
        "expect_eligible": False,
        "forbid_category": 8,
    },
    {
        "id": "checksum-n2-metadata-ssa-rejects-cat8",
        "event": "2023 Optimist",
        "n": 2,
        "place": 2,
        "class_name": "Optimist",
        "event_date": "2023-12-01",
        "as_at": "2024-01-01",
        "mode": "checksum",
        "metadata": {"mode": "ssa"},
        "expect_points": 0.0,
        "expect_eligible": False,
        "forbid_category": 8,
    },
    {
        "id": "official-forced-cat8-n2-rejects",
        "event": "2023 Optimist",
        "n": 2,
        "place": 2,
        "class_name": "Optimist",
        "event_date": "2023-12-01",
        "as_at": "2024-01-01",
        "mode": "official",
        "category": 8,
        "expect_points": 0.0,
        "expect_eligible": False,
        "forbid_category": 8,
    },
]


def _run_inline_tests() -> list[dict]:
    out = []
    for spec in _TESTS:
        roles = spec.get("compare_roles") or (spec.get("role"),)
        scores = []
        as_at = spec.get("as_at", PUBLISHED_AS_AT)
        for role in roles:
            scores.append(
                score_result(
                    spec["event"],
                    spec["n"],
                    spec["place"],
                    spec["class_name"],
                    event_date=spec.get("event_date"),
                    role=role,
                    official_status=spec.get("official_status"),
                    metadata=spec.get("metadata"),
                    ssa_rating=spec.get("ssa_rating"),
                    as_at=as_at,
                    category=spec.get("category"),
                    is_championship=spec.get("is_championship"),
                    championship_exception=spec.get("championship_exception"),
                    is_open=spec.get("is_open", True),
                    restriction_count=spec.get("restriction_count", 0),
                    mode=spec.get("mode"),
                )
            )
        got = scores[0]
        # live_points is metadata only and must never decide pass/fail.
        expect_eligible = spec.get(
            "expect_eligible",
            spec.get("expect_points", 0) != 0 or spec.get("expect_category") is not None,
        )
        if spec.get("expect_eligible") is False:
            expect_eligible = False
        ok = True
        if "expect_category" in spec and got.category != spec["expect_category"]:
            ok = False
        if "expect_points" in spec and abs(got.points - spec["expect_points"]) > 0.011:
            ok = False
        if spec.get("expect_eligible") is False and (got.eligible or got.points != 0):
            ok = False
        if spec.get("forbid_category") is not None and got.category == spec["forbid_category"]:
            ok = False
        if got.category == SSL_CATEGORY_SSA_TWO_BOAT and spec.get("mode") in (
            None,
            "official",
            "checksum",
            "parity",
        ):
            ok = False
        if spec.get("ssa_rating") is not None and got.ssa_rating != spec["ssa_rating"]:
            ok = False
        if len(scores) == 2 and scores[0].points != scores[1].points:
            ok = False
        out.append(
            {
                "id": spec["id"],
                "ok": ok,
                "got_points": got.points,
                "expect_points": spec.get("expect_points"),
                "got_category": got.category,
                "expect_category": spec.get("expect_category"),
                "live_points": spec.get("live_points"),
                "live_points_note": spec.get("live_points_note"),
                "roles": [s.points for s in scores],
                "ssa_rating": got.ssa_rating,
                "reason": got.reason,
            }
        )
    published = score_published_row(
        {
            "event": "2023 Optimist",
            "fleet": 2,
            "place": 2,
            "className": "Optimist",
            "mode": "ssa",
            "eventDate": "2023-12-01",
        },
        as_at="2024-01-01",
        reclassify=True,
    )
    published_ok = (
        published.category != SSL_CATEGORY_SSA_TWO_BOAT
        and published.points == 0.0
        and published.eligible is False
    )
    out.append(
        {
            "id": "published-row-checksum-never-cat8",
            "ok": published_ok,
            "got_points": published.points,
            "expect_points": 0.0,
            "got_category": published.category,
            "expect_category": None,
            "live_points": None,
            "live_points_note": None,
            "roles": [published.points],
            "ssa_rating": published.ssa_rating,
            "reason": published.reason,
        }
    )
    return out


def project_published_impact(payload: Mapping[str, Any]) -> dict:
    breakdowns = payload.get("breakdowns") or {}
    sailor_delta: dict[str, dict] = {}
    event_changes = []
    seen_event = set()
    n_rows = 0
    n_point_change = 0

    for slug, rows in breakdowns.items():
        live_sum = 0.0
        replay_sum = 0.0
        new_sum = 0.0
        row_changes = []
        for row in rows or []:
            n_rows += 1
            live_pts = float(row.get("points") or 0)
            live_sum += live_pts
            replay = score_published_row(row, as_at=PUBLISHED_AS_AT, reclassify=False)
            scored = score_published_row(row, as_at=PUBLISHED_AS_AT, reclassify=True)
            replay_sum += replay.points
            new_sum += scored.points
            cat_changed = scored.category != row.get("category")
            if cat_changed or abs(scored.points - live_pts) > 0.02:
                n_point_change += 1
                label = "%s | %s | P=%s N=%s | cat %s→%s | live %s replay %s new %s" % (
                    row.get("event"),
                    row.get("className"),
                    row.get("place"),
                    row.get("fleet"),
                    row.get("category"),
                    scored.category,
                    live_pts,
                    replay.points,
                    scored.points,
                )
                row_changes.append(label)
                key = (row.get("event"), row.get("className"), row.get("fleet"))
                if key not in seen_event:
                    seen_event.add(key)
                    event_changes.append(
                        {
                            "event": row.get("event"),
                            "className": row.get("className"),
                            "fleet": row.get("fleet"),
                            "live_category": row.get("category"),
                            "new_category": scored.category,
                            "live_points_example": live_pts,
                            "replay_points": replay.points,
                            "new_points_example": scored.points,
                        }
                    )
        if row_changes:
            sailor_delta[slug] = {
                "live_sum": round(live_sum, 2),
                "replay_sum": round(replay_sum, 2),
                "new_sum": round(new_sum, 2),
                "delta_vs_replay": round(new_sum - replay_sum, 2),
                "changes": row_changes,
            }

    named = {}
    for slug in ("sean-kavanagh", "thomas-henshilwood", "timothy-weaving"):
        named[slug] = sailor_delta.get(
            slug,
            {
                "live_sum": None,
                "replay_sum": None,
                "new_sum": None,
                "delta_vs_replay": 0,
                "changes": [],
            },
        )

    return {
        "breakdown_rows": n_rows,
        "rows_with_point_or_category_change": n_point_change,
        "affected_event_class_count": len(event_changes),
        "projected_affected_sailor_count": len(sailor_delta),
        "named_sailors": named,
    }


def _load_published_readonly() -> Optional[dict]:
    import os
    from pathlib import Path
    from urllib.request import urlopen

    candidates = []
    env = os.environ.get("SSL_PARITY_PUBLISHED_JSON")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("/tmp/published.json"))
    for path in candidates:
        if path.is_file():
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    try:
        with urlopen("https://sailingsa.co.za/rankings/data/published.json", timeout=30) as resp:
            return json.load(resp)
    except Exception:
        return None


def main(argv: Optional[Iterable[str]] = None) -> int:
    _ = argv
    print("SSL parity scoring self-check (Categories 1–7 official; SSA Cat 8 two-boat)")
    print("No recalc / DB write / export / deploy")
    print("-" * 60)
    results = _run_inline_tests()
    failed = [r for r in results if not r["ok"]]
    for r in results:
        flag = "PASS" if r["ok"] else "FAIL"
        print(
            "%s  %s  cat %s→%s  pts expect=%s got=%s  live_meta=%s  roles=%s"
            % (
                flag,
                r["id"],
                r.get("expect_category"),
                r["got_category"],
                r["expect_points"],
                r["got_points"],
                r.get("live_points"),
                r["roles"],
            )
        )
        if r.get("live_points_note"):
            print("    %s" % r["live_points_note"])
    print("-" * 60)
    print("tests: %s passed, %s failed, %s total" % (len(results) - len(failed), len(failed), len(results)))

    payload = _load_published_readonly()
    if not payload:
        print("projection: published.json not available (skipped)")
        return 1 if failed else 0

    impact = project_published_impact(payload)
    print("-" * 60)
    print("projection vs live published.json (read-only, reclassified + rescored)")
    print("breakdown rows: %s" % impact["breakdown_rows"])
    print("rows with point or category change: %s" % impact["rows_with_point_or_category_change"])
    print("affected-event-class count: %s" % impact["affected_event_class_count"])
    print("projected affected-sailor count: %s" % impact["projected_affected_sailor_count"])
    print("named sailors:")
    for slug, info in impact["named_sailors"].items():
        print(
            "  %s  live_sum=%s  replay_sum=%s  new_sum=%s  delta_vs_replay=%s"
            % (
                slug,
                info.get("live_sum"),
                info.get("replay_sum"),
                info.get("new_sum"),
                info.get("delta_vs_replay"),
            )
        )
        for line in (info.get("changes") or [])[:8]:
            print("    %s" % line)

    print("STOP: scoring only. No recalculation, database writes, export, or deployment.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
