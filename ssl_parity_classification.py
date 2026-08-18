"""
SSL parity event classification.

Championship status is an explicit caller/metadata input. Event names and
SSL categories are never used to guess championship or exception status.

Championships with N < 10 drop exactly one category (5→6, 6→7).
Fewer than 3 valid boats are ineligible, including championships.

SSA event ratings (500 / 350 / 250 / 150) are independent and must not
be derived from, or written into, the SSL category.

This module classifies only. It does not recalculate rankings, write the
database, export published.json, or deploy.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional

# SSL categories (distinct from SSA ratings)
SSL_CATEGORY_NATIONAL = 5
SSL_CATEGORY_REGIONAL = 6
SSL_CATEGORY_LOCAL = 7

SSL_CATEGORY_NAMES = {
    SSL_CATEGORY_NATIONAL: "NATIONAL",
    SSL_CATEGORY_REGIONAL: "REGIONAL",
    SSL_CATEGORY_LOCAL: "LOCAL",
}

# Scoring floor: fewer than this many valid boats never score.
MIN_VALID_BOATS = 3

# Ordinary (non-championship) fleet-size fallback, and championship full-category floor.
ORDINARY_REGIONAL_MIN_BOATS = 10  # 10+ → Cat 6; 3–9 → Cat 7
CHAMPIONSHIP_FULL_CATEGORY_MIN_BOATS = 10  # under 10 drops exactly one category

# SSA ratings — kept here only so callers do not mix them with SSL categories.
SSA_RATING_NATIONAL = 500
SSA_RATING_REGIONAL = 350
SSA_RATING_CLUB = 250
SSA_RATING_LOCAL = 150

OFFICIAL_NATIONAL = "national_championship"
OFFICIAL_REGIONAL = "regional_championship"
OFFICIAL_PROVINCIAL = "provincial_championship"
OFFICIAL_DISTRICT = "district_championship"
OFFICIAL_WORLD = "world_championship"

_NATIONAL_STATUS = {OFFICIAL_NATIONAL, OFFICIAL_WORLD, "nationals", "national"}
_REGIONAL_STATUS = {
    OFFICIAL_REGIONAL,
    OFFICIAL_PROVINCIAL,
    OFFICIAL_DISTRICT,
    "regional",
    "provincial",
    "district",
}

_NATIONAL_NAME_RE = re.compile(
    r"\b(?:national championships?|nationals|national champ|\bnational\b|world championships?|worlds)\b",
    re.I,
)
_INTERNATIONAL_RE = re.compile(r"\binternational\b", re.I)
_REGIONAL_NAME_RE = re.compile(
    r"\b(?:regional championships?|regionals?|provincial championships?|provincials?|"
    r"district championships?)\b",
    re.I,
)
_CAPE_CLASSIC_RE = re.compile(r"\bcape\s+classic\b", re.I)


@dataclass(frozen=True)
class SSLClassification:
    """SSL category decision. SSA rating is echoed unchanged when supplied."""

    category: Optional[int]
    category_name: Optional[str]
    eligible: bool
    official_status: Optional[str]
    source: str  # official_status | fleet_fallback | ineligible
    valid_boats: int
    ssa_rating: Optional[int] = None
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "category_name": self.category_name,
            "eligible": self.eligible,
            "official_status": self.official_status,
            "source": self.source,
            "valid_boats": self.valid_boats,
            "ssa_rating": self.ssa_rating,
            "reason": self.reason,
        }


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def is_cape_classic(event_name: Any) -> bool:
    """HYC / TSC / ZVYC / Southern Charter / Series Cape Classic events."""
    return bool(_CAPE_CLASSIC_RE.search(_norm(event_name)))


def _normalize_official_status(raw: Any) -> Optional[str]:
    """Map an explicit championship/exception token to a status constant."""
    if raw is None or raw is False:
        return None
    token = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    if not token:
        return None
    if token in _NATIONAL_STATUS or token in {OFFICIAL_NATIONAL, OFFICIAL_WORLD}:
        return OFFICIAL_WORLD if "world" in token else OFFICIAL_NATIONAL
    if token in _REGIONAL_STATUS:
        if "provincial" in token:
            return OFFICIAL_PROVINCIAL
        if "district" in token:
            return OFFICIAL_DISTRICT
        return OFFICIAL_REGIONAL
    return None


def _status_from_metadata(metadata: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Explicit metadata keys only. Does not read event names or SSL category."""
    if not metadata:
        return None
    for key in (
        "official_status",
        "championship_classification",
        "championship_type",
        "ssl_official_status",
        "exception",
    ):
        status = _normalize_official_status(metadata.get(key))
        if status:
            return status
    if metadata.get("is_national_championship") is True:
        return OFFICIAL_NATIONAL
    if metadata.get("is_regional_championship") is True:
        return OFFICIAL_REGIONAL
    return None


def infer_official_status(
    event_name: Any,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """
    Name-based helper kept for callers that still need it.

    classify_ssl_category does not use this. Championship classification
    requires official_status, exception, championship=False/True, or metadata.
    """
    from_meta = _status_from_metadata(metadata)
    if from_meta:
        return from_meta

    name = _norm(event_name)
    if not name:
        return None

    # Cape Classic is never NATIONAL unless metadata said so (already returned).
    if is_cape_classic(name):
        if _REGIONAL_NAME_RE.search(name):
            return OFFICIAL_REGIONAL
        return None

    if _NATIONAL_NAME_RE.search(name) and not _INTERNATIONAL_RE.search(name):
        if re.search(r"\bworlds?\b|\bworld championships?\b", name, re.I):
            return OFFICIAL_WORLD
        return OFFICIAL_NATIONAL

    if _REGIONAL_NAME_RE.search(name):
        if re.search(r"\bprovincial", name, re.I):
            return OFFICIAL_PROVINCIAL
        if re.search(r"\bdistrict", name, re.I):
            return OFFICIAL_DISTRICT
        return OFFICIAL_REGIONAL

    return None


def _resolve_explicit_status(
    official_status: Optional[str],
    exception: Optional[str],
    championship: Optional[bool],
    metadata: Optional[Mapping[str, Any]],
) -> Optional[str]:
    """
    Championship/exception from explicit inputs only.

    Never inferred from event name or from an SSL category number.
    championship=False forces ordinary fleet-size fallback.
    """
    if championship is False:
        return None
    status = _normalize_official_status(official_status)
    if status is None:
        status = _normalize_official_status(exception)
    if status is None:
        status = _status_from_metadata(metadata)
    return status


def _championship_category(base_category: int, boats: int) -> tuple[int, str]:
    """Drop exactly one category when championship fleet is under 10."""
    if boats >= CHAMPIONSHIP_FULL_CATEGORY_MIN_BOATS:
        return base_category, (
            "explicit championship with %s+ valid boats keeps Category %s"
            % (CHAMPIONSHIP_FULL_CATEGORY_MIN_BOATS, base_category)
        )
    dropped = min(base_category + 1, SSL_CATEGORY_LOCAL)
    return dropped, (
        "championship under 10 valid boats drops exactly one category (%s→%s)"
        % (base_category, dropped)
    )


def classify_ssl_category(
    event_name: Any,
    valid_boats: Any,
    official_status: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    ssa_rating: Optional[int] = None,
    championship: Optional[bool] = None,
    exception: Optional[str] = None,
) -> SSLClassification:
    """
    Classify one event (or class fleet) for SSL.

    Precedence:
      1. N < 3 → ineligible (never scores), including championships.
      2. Explicit national/world championship: N ≥ 10 → Category 5;
         3 ≤ N < 10 → Category 6 (exactly one drop).
      3. Explicit regional/provincial/district championship: N ≥ 10 → Category 6;
         3 ≤ N < 10 → Category 7 (exactly one drop).
      4. Ordinary events (no explicit championship/exception): 10+ → Category 6;
         3–9 → Category 7. Never Category 5 by fleet size or event name.

    Championship/exception must be passed as official_status, exception,
    championship=False to disable, or metadata keys. Event name and SSL
    category are not used to guess championship status.

    Cape Classic (HYC/TSC/ZVYC/Southern Charter/Series) is never Category 5
    unless an explicit national/world championship input is supplied.

    `ssa_rating` is passed through unchanged and is not used for SSL category.
    `event_name` is accepted for callers/projection; it does not classify.
    """
    _ = event_name
    try:
        boats = int(valid_boats)
    except (TypeError, ValueError):
        boats = 0

    status = _resolve_explicit_status(
        official_status, exception, championship, metadata
    )

    if boats < MIN_VALID_BOATS:
        return SSLClassification(
            category=None,
            category_name=None,
            eligible=False,
            official_status=status,
            source="ineligible",
            valid_boats=boats,
            ssa_rating=ssa_rating,
            reason="fewer than 3 valid boats",
        )

    if status in {OFFICIAL_NATIONAL, OFFICIAL_WORLD}:
        category, reason = _championship_category(SSL_CATEGORY_NATIONAL, boats)
        return SSLClassification(
            category=category,
            category_name=SSL_CATEGORY_NAMES[category],
            eligible=True,
            official_status=status,
            source="official_status",
            valid_boats=boats,
            ssa_rating=ssa_rating,
            reason=reason,
        )

    if status in {OFFICIAL_REGIONAL, OFFICIAL_PROVINCIAL, OFFICIAL_DISTRICT}:
        category, reason = _championship_category(SSL_CATEGORY_REGIONAL, boats)
        return SSLClassification(
            category=category,
            category_name=SSL_CATEGORY_NAMES[category],
            eligible=True,
            official_status=status,
            source="official_status",
            valid_boats=boats,
            ssa_rating=ssa_rating,
            reason=reason,
        )

    if boats >= ORDINARY_REGIONAL_MIN_BOATS:
        category = SSL_CATEGORY_REGIONAL
        reason = "ordinary event with 10+ valid boats → Category 6 (never Cat 5 by fleet size)"
    else:
        category = SSL_CATEGORY_LOCAL
        reason = "ordinary event with 3–9 valid boats → Category 7"

    return SSLClassification(
        category=category,
        category_name=SSL_CATEGORY_NAMES[category],
        eligible=True,
        official_status=status,
        source="fleet_fallback",
        valid_boats=boats,
        ssa_rating=ssa_rating,
        reason=reason,
    )


def classify_published_row(row: Mapping[str, Any]) -> SSLClassification:
    """Classify a published.json breakdown row. Does not mutate the row.

    Uses explicit row fields only. Event name is not a championship signal.
    """
    championship = row.get("championship") if isinstance(row, Mapping) else None
    if championship in ("true", "True", 1):
        championship = True
    elif championship in ("false", "False", 0):
        championship = False
    elif championship is not True and championship is not False:
        championship = None
    return classify_ssl_category(
        event_name=row.get("event") or row.get("eventSlug") or row.get("regattaId"),
        valid_boats=row.get("fleet"),
        official_status=row.get("official_status") if isinstance(row, Mapping) else None,
        metadata=row if isinstance(row, Mapping) else None,
        ssa_rating=row.get("rating"),
        championship=championship,
        exception=row.get("exception") if isinstance(row, Mapping) else None,
    )


# ---------------------------------------------------------------------------
# Inline self-check (same file only). No ranking recalc / DB / export.
# ---------------------------------------------------------------------------

_TESTS = [
    # Sean Kavanagh: 2026 HYC Cape Classic N=15  Cat 5 → 6
    {
        "id": "sean-kavanagh-hyc-cape-classic-2026",
        "event": "2026-02-16 HYC Cape Classic 2026",
        "n": 15,
        "expect_category": 6,
        "live_category": 5,
        "ssa_rating": 250,
    },
    # Timothy Weaving / Joshua Keytel: 2024 TSC Cape Classic N=13  Cat 5 → 6
    {
        "id": "timothy-tsc-cape-classic-2024",
        "event": "2024-12-01 TSC Cape Classic",
        "n": 13,
        "expect_category": 6,
        "live_category": 5,
        "ssa_rating": 250,
    },
    # Timothy Weaving / Joshua Keytel: Southern Charter Cape Classic N=14  Cat 5 → 6
    {
        "id": "timothy-southern-charter-cape-classic-2024",
        "event": "2024-09-08 Southern Charter Cape Classic",
        "n": 14,
        "expect_category": 6,
        "live_category": 5,
        "ssa_rating": 250,
    },
    {
        "id": "joshua-tsc-cape-classic-2024",
        "event": "2024-12-01 TSC Cape Classic",
        "n": 13,
        "expect_category": 6,
        "live_category": 5,
        "ssa_rating": 250,
    },
    {
        "id": "joshua-southern-charter-cape-classic-2024",
        "event": "2024-09-08 Southern Charter Cape Classic",
        "n": 14,
        "expect_category": 6,
        "live_category": 5,
        "ssa_rating": 250,
    },
    # Cape Classic 3–9 stays / becomes Cat 7
    {
        "id": "cape-classic-small-fleet",
        "event": "2025-12-08 TSC CAPE CLASSIC Dec 2025",
        "n": 8,
        "expect_category": 7,
        "live_category": 7,
        "ssa_rating": 250,
    },
    # Explicit national championship N=6 drops 5→6 (not keep Cat 5, not auto Local)
    {
        "id": "2025-29er-nationals-n6-drops-to-cat6",
        "event": "2025-05-04 29er Nationals Results",
        "n": 6,
        "official_status": "national_championship",
        "expect_category": 6,
        "live_category": 7,
        "ssa_rating": 500,
    },
    # Name "Nationals" without explicit championship is ordinary, not Cat 5
    {
        "id": "29er-nationals-name-only-n6-not-guessed",
        "event": "2025-05-04 29er Nationals Results",
        "n": 6,
        "expect_category": 7,
        "ssa_rating": 500,
    },
    # Explicit regional championship N=5 drops 6→7
    {
        "id": "overberg-regional-n5-drops-to-cat7",
        "event": "2025-04-05 Overberg Regional Championships 2025",
        "n": 5,
        "official_status": "regional_championship",
        "expect_category": 7,
        "live_category": 7,
        "ssa_rating": 150,
    },
    {
        "id": "sa-youth-nationals",
        "event": "2025-12-19 SA Youth Nationals Dec 2025",
        "n": 33,
        "official_status": "national_championship",
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
    },
    {
        "id": "ilca-nationals",
        "event": "2026-05-03 ILCA Nationals",
        "n": 29,
        "official_status": "national_championship",
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
    },
    {
        "id": "420-nationals",
        "event": "2025-10-04 420 National Championship Results",
        "n": 18,
        "official_status": "national_championship",
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
    },
    # Ordinary 10+ must not become Cat 5
    {
        "id": "ordinary-large-fleet-never-cat5",
        "event": "Club Open Regatta",
        "n": 20,
        "expect_category": 6,
        "live_category": None,
        "ssa_rating": 250,
    },
    # N=2 never scores, even with explicit National championship
    {
        "id": "nationals-n2-ineligible",
        "event": "ILCA Nationals",
        "n": 2,
        "official_status": "national_championship",
        "expect_category": None,
        "live_category": None,
        "ssa_rating": 500,
        "expect_eligible": False,
    },
    # Metadata can designate Cape Classic as National; name alone cannot
    {
        "id": "cape-classic-metadata-national-override",
        "event": "HYC Cape Classic",
        "n": 15,
        "expect_category": 5,
        "metadata": {"official_status": "national_championship"},
        "ssa_rating": 500,
    },
    # --- Thomas Henshilwood (SAS 9612, slug thomas-henshilwood) ---
    {
        "id": "thomas-henshilwood-2026-rsa-29er-nationals-n10",
        "event": "2026 RSA 29er Nationals",
        "n": 10,
        "official_status": "national_championship",
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
        "sailor": "Thomas Henshilwood",
        "sa_sailing_id": 9612,
        "slug": "thomas-henshilwood",
    },
    {
        "id": "thomas-henshilwood-2026-rsa-29er-nationals-n9",
        "event": "2026 RSA 29er Nationals",
        "n": 9,
        "official_status": "national_championship",
        "expect_category": 6,
        "ssa_rating": 500,
        "sailor": "Thomas Henshilwood",
        "sa_sailing_id": 9612,
        "slug": "thomas-henshilwood",
    },
    {
        "id": "thomas-henshilwood-2026-rsa-29er-nationals-n3",
        "event": "2026 RSA 29er Nationals",
        "n": 3,
        "official_status": "national_championship",
        "expect_category": 6,
        "ssa_rating": 500,
        "sailor": "Thomas Henshilwood",
        "sa_sailing_id": 9612,
        "slug": "thomas-henshilwood",
    },
    {
        "id": "thomas-henshilwood-2026-rsa-29er-nationals-n2",
        "event": "2026 RSA 29er Nationals",
        "n": 2,
        "official_status": "national_championship",
        "expect_category": None,
        "expect_eligible": False,
        "ssa_rating": 500,
        "sailor": "Thomas Henshilwood",
        "sa_sailing_id": 9612,
        "slug": "thomas-henshilwood",
    },
    # National championship fleet-size boundaries (explicit input)
    {
        "id": "national-championship-n2-ineligible",
        "event": "National Championship",
        "n": 2,
        "official_status": "national_championship",
        "expect_category": None,
        "expect_eligible": False,
    },
    {
        "id": "national-championship-n3-drops-to-cat6",
        "event": "National Championship",
        "n": 3,
        "official_status": "national_championship",
        "expect_category": 6,
    },
    {
        "id": "national-championship-n9-drops-to-cat6",
        "event": "National Championship",
        "n": 9,
        "official_status": "national_championship",
        "expect_category": 6,
    },
    {
        "id": "national-championship-n10-keeps-cat5",
        "event": "National Championship",
        "n": 10,
        "official_status": "national_championship",
        "expect_category": 5,
    },
    # Regional championship fleet-size boundaries (explicit input)
    {
        "id": "regional-championship-n2-ineligible",
        "event": "Regional Championship",
        "n": 2,
        "official_status": "regional_championship",
        "expect_category": None,
        "expect_eligible": False,
    },
    {
        "id": "regional-championship-n3-drops-to-cat7",
        "event": "Regional Championship",
        "n": 3,
        "official_status": "regional_championship",
        "expect_category": 7,
    },
    {
        "id": "regional-championship-n9-drops-to-cat7",
        "event": "Regional Championship",
        "n": 9,
        "official_status": "regional_championship",
        "expect_category": 7,
    },
    {
        "id": "regional-championship-n10-keeps-cat6",
        "event": "Regional Championship",
        "n": 10,
        "official_status": "regional_championship",
        "expect_category": 6,
    },
    # Ordinary (no championship input) fleet-size boundaries
    {
        "id": "ordinary-n2-ineligible",
        "event": "Club Open Regatta",
        "n": 2,
        "expect_category": None,
        "expect_eligible": False,
    },
    {
        "id": "ordinary-n3-cat7",
        "event": "Club Open Regatta",
        "n": 3,
        "expect_category": 7,
    },
    {
        "id": "ordinary-n9-cat7",
        "event": "Club Open Regatta",
        "n": 9,
        "expect_category": 7,
    },
    {
        "id": "ordinary-n10-cat6",
        "event": "Club Open Regatta",
        "n": 10,
        "expect_category": 6,
    },
    # Exception input is explicit championship type (not inferred from name)
    {
        "id": "exception-national-n9-drops-to-cat6",
        "event": "Club Open Regatta",
        "n": 9,
        "exception": "national_championship",
        "expect_category": 6,
    },
    {
        "id": "exception-national-n10-keeps-cat5",
        "event": "Club Open Regatta",
        "n": 10,
        "exception": "national_championship",
        "expect_category": 5,
    },
    # championship=False ignores explicit national metadata (ordinary fallback)
    {
        "id": "championship-false-ignores-national-metadata",
        "event": "2026 RSA 29er Nationals",
        "n": 10,
        "championship": False,
        "metadata": {"official_status": "national_championship"},
        "expect_category": 6,
    },
    # championship=True without a type does not guess National from the name
    {
        "id": "championship-true-without-type-does-not-guess",
        "event": "2026 RSA 29er Nationals",
        "n": 10,
        "championship": True,
        "expect_category": 6,
    },
    # Live SSL category is not a championship signal
    {
        "id": "live-category-5-does-not-guess-championship",
        "event": "Club Open Regatta",
        "n": 10,
        "live_category": 5,
        "expect_category": 6,
    },
]


def _run_inline_tests() -> list[dict]:
    results = []
    for spec in _TESTS:
        got = classify_ssl_category(
            spec["event"],
            spec["n"],
            official_status=spec.get("official_status"),
            metadata=spec.get("metadata"),
            ssa_rating=spec.get("ssa_rating"),
            championship=spec.get("championship"),
            exception=spec.get("exception"),
        )
        expect_eligible = spec.get("expect_eligible", spec["expect_category"] is not None)
        ok = got.category == spec["expect_category"] and got.eligible == expect_eligible
        if spec.get("ssa_rating") is not None and got.ssa_rating != spec["ssa_rating"]:
            ok = False
        results.append(
            {
                "id": spec["id"],
                "ok": ok,
                "event": spec["event"],
                "n": spec["n"],
                "expect": spec["expect_category"],
                "got": got.category,
                "got_name": got.category_name,
                "source": got.source,
                "ssa_rating": got.ssa_rating,
                "live_category": spec.get("live_category"),
                "reason": got.reason,
            }
        )
    return results


def project_published_impact(payload: Mapping[str, Any]) -> dict:
    """
    Read-only projection against a published.json payload.
    Does not write files or recalculate points.
    """
    breakdowns = payload.get("breakdowns") or {}
    event_keys = {}
    sailor_hits: dict[str, list[str]] = {}

    for slug, rows in breakdowns.items():
        for row in rows or []:
            live_cat = row.get("category")
            event = row.get("event") or ""
            class_name = row.get("className") or ""
            fleet = row.get("fleet")
            key = (event, class_name, fleet, live_cat)
            decision = classify_published_row(row)
            if key not in event_keys:
                event_keys[key] = {
                    "event": event,
                    "className": class_name,
                    "fleet": fleet,
                    "live_category": live_cat,
                    "live_category_name": row.get("categoryName"),
                    "new_category": decision.category,
                    "new_category_name": decision.category_name,
                    "ssa_rating": row.get("rating"),
                    "changed": decision.category != live_cat,
                    "source": decision.source,
                    "reason": decision.reason,
                    "sailors": set(),
                }
            event_keys[key]["sailors"].add(slug)
            if decision.category != live_cat:
                sailor_hits.setdefault(slug, [])
                label = "%s | %s | N=%s | %s→%s" % (
                    event,
                    class_name,
                    fleet,
                    live_cat,
                    decision.category,
                )
                if label not in sailor_hits[slug]:
                    sailor_hits[slug].append(label)

    changed = [v for v in event_keys.values() if v["changed"]]
    unchanged = [v for v in event_keys.values() if not v["changed"]]

    def _freeze(row: dict) -> dict:
        out = dict(row)
        out["sailors"] = sorted(row["sailors"])
        out["sailor_count"] = len(row["sailors"])
        return out

    by_transition: dict[str, int] = {}
    for row in changed:
        k = "%s→%s" % (row["live_category"], row["new_category"])
        by_transition[k] = by_transition.get(k, 0) + 1

    named = {
        "sean-kavanagh": [x for x in sailor_hits.get("sean-kavanagh", []) if "cape classic" in x.lower()],
        "timothy-weaving": [x for x in sailor_hits.get("timothy-weaving", [])],
        "joshua-keytel": [x for x in sailor_hits.get("joshua-keytel", []) if "cape classic" in x.lower()],
    }

    return {
        "unique_event_class_rows": len(event_keys),
        "affected_event_count": len(changed),
        "unchanged_event_count": len(unchanged),
        "projected_affected_sailor_count": len(sailor_hits),
        "transitions": by_transition,
        "named_sailor_changes": named,
        "changed_events": [_freeze(v) for v in sorted(changed, key=lambda r: r["event"])],
    }


def _load_published_readonly() -> Optional[dict]:
    import os
    from pathlib import Path

    candidates = []
    env = os.environ.get("SSL_PARITY_PUBLISHED_JSON")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path("/tmp/published.json"),
        ]
    )
    for path in candidates:
        if path.is_file():
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    # Optional live read for projection only — never written back.
    try:
        from urllib.request import urlopen

        with urlopen("https://sailingsa.co.za/rankings/data/published.json", timeout=30) as resp:
            return json.load(resp)
    except Exception:
        return None


def main(argv: Optional[Iterable[str]] = None) -> int:
    _ = argv
    print("SSL parity classification self-check")
    print("No recalc / DB write / export / deploy")
    print("-" * 60)
    results = _run_inline_tests()
    failed = [r for r in results if not r["ok"]]
    for r in results:
        flag = "PASS" if r["ok"] else "FAIL"
        print(
            "%s  %s  N=%s  expect=%s got=%s (%s)  ssa_rating=%s"
            % (flag, r["id"], r["n"], r["expect"], r["got"], r["got_name"], r["ssa_rating"])
        )
    print("-" * 60)
    print("tests: %s passed, %s failed, %s total" % (len(results) - len(failed), len(failed), len(results)))

    payload = _load_published_readonly()
    if not payload:
        print("projection: published.json not available (skipped)")
        return 1 if failed else 0

    impact = project_published_impact(payload)
    print("-" * 60)
    print("projection vs live published.json (read-only)")
    print("unique event-class rows: %s" % impact["unique_event_class_rows"])
    print("affected-event count: %s" % impact["affected_event_count"])
    print("unchanged-event count: %s" % impact["unchanged_event_count"])
    print("projected affected-sailor count: %s" % impact["projected_affected_sailor_count"])
    print("transitions: %s" % impact["transitions"])
    print("named sailor changes:")
    for slug, rows in impact["named_sailor_changes"].items():
        print("  %s: %s" % (slug, rows or "(none in filter)"))

    # Explicit required rows
    # Name-only published rows are not championships. Cape Classic stays Cat 6.
    # 29er Nationals / Overberg need explicit championship input to drop 5→6 / 6→7.
    required = [
        ("2026-02-16 HYC Cape Classic 2026", "Sonnet", 15, 5, 6),
        ("2024-12-01 TSC Cape Classic", "Optimist A", 13, 5, 6),
        ("2024-09-08 Southern Charter Cape Classic", "Optimist A", 14, 5, 6),
        ("2025-05-04 29er Nationals Results", "29er", 6, 7, 7),
        ("2025-04-05 Overberg Regional Championships 2025", "Optimist A", 5, 7, 7),
    ]
    print("required live-row checks:")
    req_fail = 0
    lookup = {}
    for _slug, rows in (payload.get("breakdowns") or {}).items():
        for row in rows or []:
            lookup[(row.get("event"), row.get("className"), row.get("fleet"))] = row
    for event, class_name, n, live, new in required:
        row = lookup.get((event, class_name, n))
        if not row:
            print("  MISS  %s | %s | N=%s (not in published breakdowns)" % (event, class_name, n))
            req_fail += 1
            continue
        got = classify_published_row(row)
        ok = row.get("category") == live and got.category == new
        if not ok:
            req_fail += 1
        print(
            "  %s  %s | %s | live=%s expect_live=%s → new=%s expect_new=%s"
            % (
                "PASS" if ok else "FAIL",
                event,
                class_name,
                row.get("category"),
                live,
                got.category,
                new,
            )
        )

    if failed or req_fail:
        return 1
    print("STOP: classification only. No recalculation, database writes, export, or deployment.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
