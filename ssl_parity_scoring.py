"""
SSL parity scoring (Phase 2).

Uses Phase 1 SSL *category* (5/6/7), not SSA event rating (500/350/250/150).
Skipper and crew receive the same points for the same result. Board assignment
(skipper list vs crew list) is not this module.

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
    SSL_CATEGORY_LOCAL,
    SSL_CATEGORY_NATIONAL,
    SSL_CATEGORY_REGIONAL,
    classify_ssl_category,
)

# Category bases fitted to ssl-parity-v1-shadow published.json (audit 2026-07-27-011).
# Independent of SSA ratings.
CATEGORY_BASE = {
    SSL_CATEGORY_NATIONAL: 250.0,  # Cat 5
    SSL_CATEGORY_REGIONAL: 100.0,  # Cat 6
    SSL_CATEGORY_LOCAL: 10.0,  # Cat 7
}

FULL_VALUE_WEEKS = 52
ZERO_VALUE_WEEKS = 104
AGE_HALF = 0.5
LAST_PLACE_FLOOR = 0.004

# Class coefficients fitted from P=1 published rows.
CLASS_COEFFICIENT = {
    "ilca 6": 1.0,
    "ilca 7": 1.0,
    "ilca 4.7": 0.85,
    "ilca 4": 0.85,
    "optimist a": 0.85,
    "optimist b": 0.85,
    "optimist": 0.85,
    "420": 0.85,
    "29er": 0.85,
    "finn": 0.85,
    "mirror": 0.85,
    "j22": 0.85,
    "dart 18": 0.85,
    "hobie 16": 0.85,
    "hobie 14": 0.85,
    "hobie tiger": 0.85,
    "flying 15": 0.85,
    "flying fifteen": 0.85,
    "505": 0.85,
    "rs tera": 0.85,
    "topper 5.3": 0.85,
    "soling": 0.85,
    "sonnet": 0.75,
    "dabchick": 0.75,
    "extra": 0.75,
    "windsurfer lt": 0.75,
    "stadt 23": 0.75,
    "hunter": 0.75,
    "hunter 19": 0.75,
    "l26": 0.75,
    "halcat": 0.75,
    "topaz": 0.75,
    "pacer 27": 0.75,
}

DEFAULT_CLASS_COEFFICIENT = 0.85

PUBLISHED_AS_AT = date(2026, 7, 27)


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def class_coefficient(class_name: Any) -> float:
    key = str(class_name or "").strip().lower()
    if key in CLASS_COEFFICIENT:
        return CLASS_COEFFICIENT[key]
    return DEFAULT_CLASS_COEFFICIENT


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


def age_factor(event_date: Any, as_at: Any = None) -> float:
    weeks = age_weeks(event_date, as_at)
    if weeks is None:
        return 1.0
    if weeks <= FULL_VALUE_WEEKS:
        return 1.0
    if weeks <= ZERO_VALUE_WEEKS:
        return AGE_HALF
    return 0.0


def place_factor(place: Any, fleet: Any = None) -> float:
    """
    Provisional place curve fitted to published medians (ssl-parity-v1-shadow).

    P1–P5: 1.000, 0.875, 0.750, 0.625, 0.500
    P6–P10: drop 0.068 per place
    P11+: drop 0.016 per place, floor 0.004
    """
    try:
        p = int(place)
    except (TypeError, ValueError):
        return 0.0
    if p < 1:
        return 0.0
    try:
        n = int(fleet) if fleet is not None else None
    except (TypeError, ValueError):
        n = None
    if n is not None and p > n:
        p = n
    if p <= 5:
        return 1.0 - 0.125 * (p - 1)
    if p <= 10:
        return 0.5 - 0.068 * (p - 5)
    return max(LAST_PLACE_FLOOR, 0.160 - 0.016 * (p - 10))


@dataclass(frozen=True)
class SSLScore:
    points: float
    eligible: bool
    category: Optional[int]
    category_name: Optional[str]
    category_base: float
    class_coefficient: float
    place_factor: float
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
            "place_factor": self.place_factor,
            "age_factor": self.age_factor,
            "role": self.role,
            "ssa_rating": self.ssa_rating,
            "reason": self.reason,
        }


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
) -> SSLScore:
    """
    Score one result.

    `role` (helm/skipper/crew) does not change points. Same boat, same place,
    same fleet → same points for skipper and crew.

    `ssa_rating` is echoed only; it is not a multiplier.
    """
    classification = classify_ssl_category(
        event_name,
        valid_boats,
        official_status=official_status,
        metadata=metadata,
        ssa_rating=ssa_rating,
    )
    cat = category if category is not None else classification.category
    role_key = str(role or "").strip().lower() or None

    if not classification.eligible or cat is None:
        return SSLScore(
            points=0.0,
            eligible=False,
            category=None,
            category_name=None,
            category_base=0.0,
            class_coefficient=class_coefficient(class_name),
            place_factor=0.0,
            age_factor=age_factor(event_date, as_at),
            role=role_key,
            ssa_rating=ssa_rating,
            reason=classification.reason or "ineligible",
        )

    base = CATEGORY_BASE[cat]
    coeff = class_coefficient(class_name)
    pf = place_factor(place, valid_boats)
    af = age_factor(event_date, as_at)
    raw = base * coeff * pf * af
    points = _round2(raw)
    return SSLScore(
        points=points,
        eligible=True,
        category=cat,
        category_name=classification.category_name if category is None else {
            SSL_CATEGORY_NATIONAL: "NATIONAL",
            SSL_CATEGORY_REGIONAL: "REGIONAL",
            SSL_CATEGORY_LOCAL: "LOCAL",
        }.get(cat),
        category_base=base,
        class_coefficient=coeff,
        place_factor=pf,
        age_factor=af,
        role=role_key,
        ssa_rating=ssa_rating,
        reason="base × class × place × age; role ignored",
    )


def score_published_row(
    row: Mapping[str, Any],
    as_at: Any = None,
    reclassify: bool = True,
) -> SSLScore:
    live_cat = row.get("category") if not reclassify else None
    return score_result(
        event_name=row.get("event") or row.get("eventSlug") or row.get("regattaId"),
        valid_boats=row.get("fleet"),
        place=row.get("place"),
        class_name=row.get("className"),
        event_date=row.get("eventDate"),
        role=row.get("role"),
        metadata=row,
        ssa_rating=row.get("rating"),
        as_at=as_at or PUBLISHED_AS_AT,
        category=live_cat,
    )


# ---------------------------------------------------------------------------
# Inline self-check
# ---------------------------------------------------------------------------

_TESTS = [
    {
        "id": "ilca6-nationals-p1",
        "event": "2026-05-03 ILCA Nationals",
        "n": 29,
        "place": 1,
        "class_name": "Ilca 6",
        "event_date": "2026-05-03",
        "ssa_rating": 500,
        "expect_points": 250.0,
        "expect_category": 5,
    },
    {
        "id": "youth-nationals-optA-p1",
        "event": "2025-12-19 SA Youth Nationals Dec 2025",
        "n": 33,
        "place": 1,
        "class_name": "Optimist A",
        "event_date": "2025-12-19",
        "ssa_rating": 500,
        "expect_points": 212.5,
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
        "expect_points": 185.94,
        "expect_category": 5,
    },
    {
        "id": "29er-nationals-n6-stays-cat5-p1",
        "event": "2025-05-04 29er Nationals Results",
        "n": 6,
        "place": 1,
        "class_name": "29er",
        "event_date": "2025-05-04",
        "ssa_rating": 500,
        "expect_category": 5,
        "expect_points": 106.25,  # 250 * 0.85 * 1.0 * 0.5 age
    },
    {
        "id": "sean-cape-classic-sonnet-p2-now-cat6",
        "event": "2026-02-16 HYC Cape Classic 2026",
        "n": 15,
        "place": 2,
        "class_name": "Sonnet",
        "event_date": "2026-02-16",
        "ssa_rating": 250,
        "expect_category": 6,
        "expect_points": 65.63,  # 100 * 0.75 * 0.875 → 65.625 → 65.63
        "live_points": 164.06,
    },
    {
        "id": "timothy-tsc-2024-p5-now-cat6",
        "event": "2024-12-01 TSC Cape Classic",
        "n": 13,
        "place": 5,
        "class_name": "Optimist A",
        "event_date": "2024-12-01",
        "ssa_rating": 250,
        "expect_category": 6,
        "expect_points": 21.25,  # 100 * 0.85 * 0.5 * 0.5
        "live_points": 53.12,
    },
    {
        "id": "timothy-southern-charter-2024-p5-now-cat6",
        "event": "2024-09-08 Southern Charter Cape Classic",
        "n": 14,
        "place": 5,
        "class_name": "Optimist A",
        "event_date": "2024-09-08",
        "ssa_rating": 250,
        "expect_category": 6,
        "expect_points": 21.25,
        "live_points": 53.12,
    },
    {
        "id": "overberg-optA-p1-now-cat6",
        "event": "2025-04-05 Overberg Regional Championships 2025",
        "n": 5,
        "place": 1,
        "class_name": "Optimist A",
        "event_date": "2025-04-05",
        "ssa_rating": 150,
        "expect_category": 6,
        "expect_points": 42.5,  # 100 * 0.85 * 1.0 * 0.5 age
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
        "expect_points": 132.81,
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
        "expect_points": 100.0,  # ordinary 10+ → cat 6 base 100, not SSA 500
    },
    {
        "id": "n2-ineligible",
        "event": "ILCA Nationals",
        "n": 2,
        "place": 1,
        "class_name": "Ilca 6",
        "event_date": "2026-05-03",
        "ssa_rating": 500,
        "expect_points": 0.0,
        "expect_eligible": False,
    },
]


def _run_inline_tests() -> list[dict]:
    out = []
    for spec in _TESTS:
        roles = spec.get("compare_roles") or (spec.get("role"),)
        scores = []
        for role in roles:
            scores.append(
                score_result(
                    spec["event"],
                    spec["n"],
                    spec["place"],
                    spec["class_name"],
                    event_date=spec.get("event_date"),
                    role=role,
                    ssa_rating=spec.get("ssa_rating"),
                    as_at=PUBLISHED_AS_AT,
                )
            )
        got = scores[0]
        expect_eligible = spec.get("expect_eligible", spec.get("expect_points", 0) != 0 or spec.get("expect_category") is not None)
        if spec.get("expect_eligible") is False:
            expect_eligible = False
        ok = True
        if "expect_category" in spec and got.category != spec["expect_category"]:
            ok = False
        if "expect_points" in spec and abs(got.points - spec["expect_points"]) > 0.011:
            ok = False
        if got.eligible != expect_eligible and spec.get("expect_eligible") is False:
            ok = False
        if spec.get("expect_eligible") is False and got.points != 0:
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
                "roles": [s.points for s in scores],
                "ssa_rating": got.ssa_rating,
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
            if cat_changed:
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
    for slug in ("sean-kavanagh", "timothy-weaving", "joshua-keytel"):
        named[slug] = sailor_delta.get(
            slug,
            {"live_sum": None, "replay_sum": None, "new_sum": None, "delta_vs_replay": 0, "changes": []},
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
    print("SSL parity scoring self-check (Phase 2)")
    print("No recalc / DB write / export / deploy")
    print("-" * 60)
    results = _run_inline_tests()
    failed = [r for r in results if not r["ok"]]
    for r in results:
        flag = "PASS" if r["ok"] else "FAIL"
        print(
            "%s  %s  cat %s→%s  pts expect=%s got=%s  live=%s  roles=%s"
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
