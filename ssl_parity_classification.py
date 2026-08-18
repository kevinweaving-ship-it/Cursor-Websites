"""
SSL parity event classification.

Championship / official event status outranks fleet-size fallback.
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

# Ordinary (non-championship) fleet-size fallback.
ORDINARY_REGIONAL_MIN_BOATS = 10  # 10+ → Cat 6; 3–9 → Cat 7

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


def _status_from_metadata(metadata: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not metadata:
        return None
    for key in (
        "official_status",
        "championship_classification",
        "championship_type",
        "ssl_official_status",
    ):
        raw = metadata.get(key)
        if raw is None or raw is False:
            continue
        token = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        if token in _NATIONAL_STATUS or token in {
            "national_championship",
            "world_championship",
        }:
            if token in {"world", "world_championship"}:
                return OFFICIAL_WORLD
            return OFFICIAL_NATIONAL
        if token in _REGIONAL_STATUS:
            if "provincial" in token:
                return OFFICIAL_PROVINCIAL
            if "district" in token:
                return OFFICIAL_DISTRICT
            return OFFICIAL_REGIONAL
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
    Resolve official championship status.

    Authoritative metadata wins. Cape Classic titles never infer National
    Championship from the name alone.
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


def classify_ssl_category(
    event_name: Any,
    valid_boats: Any,
    official_status: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    ssa_rating: Optional[int] = None,
) -> SSLClassification:
    """
    Classify one event (or class fleet) for SSL.

    Precedence:
      1. N < 3 → ineligible (never scores).
      2. Official National Championship / Nationals / Worlds → Category 5,
         even when 3 ≤ N < 10.
      3. Official Regional / Provincial / District Championship → Category 6,
         even when 3 ≤ N < 10.
      4. Ordinary events: 10+ → Category 6; 3–9 → Category 7.
         Ordinary events are never promoted to Category 5 by fleet size.

    Cape Classic (HYC/TSC/ZVYC/Southern Charter/Series) is never Category 5
    unless metadata explicitly designates a National Championship.

    `ssa_rating` is passed through unchanged and is not used for SSL category.
    """
    try:
        boats = int(valid_boats)
    except (TypeError, ValueError):
        boats = 0

    status = None
    if official_status:
        token = str(official_status).strip().lower().replace(" ", "_").replace("-", "_")
        if token in _NATIONAL_STATUS or token in {OFFICIAL_NATIONAL, OFFICIAL_WORLD}:
            status = OFFICIAL_WORLD if "world" in token else OFFICIAL_NATIONAL
        elif token in _REGIONAL_STATUS:
            if "provincial" in token:
                status = OFFICIAL_PROVINCIAL
            elif "district" in token:
                status = OFFICIAL_DISTRICT
            else:
                status = OFFICIAL_REGIONAL
    if status is None:
        status = infer_official_status(event_name, metadata)

    # Cape Classic name cannot be Category 5 without explicit national metadata.
    if is_cape_classic(event_name) and status in {OFFICIAL_NATIONAL, OFFICIAL_WORLD}:
        if _status_from_metadata(metadata) not in {OFFICIAL_NATIONAL, OFFICIAL_WORLD}:
            if not official_status:
                status = None

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
        return SSLClassification(
            category=SSL_CATEGORY_NATIONAL,
            category_name=SSL_CATEGORY_NAMES[SSL_CATEGORY_NATIONAL],
            eligible=True,
            official_status=status,
            source="official_status",
            valid_boats=boats,
            ssa_rating=ssa_rating,
            reason="official national/world championship overrides fleet-size fallback",
        )

    if status in {OFFICIAL_REGIONAL, OFFICIAL_PROVINCIAL, OFFICIAL_DISTRICT}:
        return SSLClassification(
            category=SSL_CATEGORY_REGIONAL,
            category_name=SSL_CATEGORY_NAMES[SSL_CATEGORY_REGIONAL],
            eligible=True,
            official_status=status,
            source="official_status",
            valid_boats=boats,
            ssa_rating=ssa_rating,
            reason="official regional/provincial/district championship overrides fleet-size fallback",
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
    """Classify a published.json breakdown row. Does not mutate the row."""
    return classify_ssl_category(
        event_name=row.get("event") or row.get("eventSlug") or row.get("regattaId"),
        valid_boats=row.get("fleet"),
        metadata=row if isinstance(row, Mapping) else None,
        ssa_rating=row.get("rating"),
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
    # 2025 29er Nationals N=6 remains Cat 5 (official National Championship)
    {
        "id": "2025-29er-nationals-n6",
        "event": "2025-05-04 29er Nationals Results",
        "n": 6,
        "expect_category": 5,
        "live_category": 7,
        "ssa_rating": 500,
    },
    # Overberg Regional N=5 remains/becomes Cat 6 (official status overrides fallback)
    {
        "id": "overberg-regional-n5",
        "event": "2025-04-05 Overberg Regional Championships 2025",
        "n": 5,
        "expect_category": 6,
        "live_category": 7,
        "ssa_rating": 150,
    },
    {
        "id": "sa-youth-nationals",
        "event": "2025-12-19 SA Youth Nationals Dec 2025",
        "n": 33,
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
    },
    {
        "id": "ilca-nationals",
        "event": "2026-05-03 ILCA Nationals",
        "n": 29,
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
    },
    {
        "id": "29er-nationals-official",
        "event": "2026 RSA 29er Nationals",
        "n": 10,
        "expect_category": 5,
        "live_category": 5,
        "ssa_rating": 500,
    },
    {
        "id": "420-nationals",
        "event": "2025-10-04 420 National Championship Results",
        "n": 18,
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
    # N=2 never scores, even if National
    {
        "id": "nationals-n2-ineligible",
        "event": "ILCA Nationals",
        "n": 2,
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
]


def _run_inline_tests() -> list[dict]:
    results = []
    for spec in _TESTS:
        got = classify_ssl_category(
            spec["event"],
            spec["n"],
            metadata=spec.get("metadata"),
            ssa_rating=spec.get("ssa_rating"),
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
    required = [
        ("2026-02-16 HYC Cape Classic 2026", "Sonnet", 15, 5, 6),
        ("2024-12-01 TSC Cape Classic", "Optimist A", 13, 5, 6),
        ("2024-09-08 Southern Charter Cape Classic", "Optimist A", 14, 5, 6),
        ("2025-05-04 29er Nationals Results", "29er", 6, 7, 5),
        ("2025-04-05 Overberg Regional Championships 2025", "Optimist A", 5, 7, 6),
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
