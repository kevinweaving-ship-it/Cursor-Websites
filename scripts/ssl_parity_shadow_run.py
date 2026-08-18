#!/usr/bin/env python3
"""SSL Parity SHADOW run — Phase 1 + SSA-v2 path.

Completely separate from sas-points-v1.x.
Default path writes ONLY ranking_audit* for a new audit. Does NOT publish.
Does NOT touch api.py.

--mode=ssa-v2 is read-only: reuses live SAS extraction/dedup, scores with
PR13 score_result(mode="ssa") using SAS event type/classification (not WoS),
writes audit JSON to a non-published path. Forbids DB writes and published.json.

Feature flag (required for default path):
  export SSL_PARITY_ENGINE=1
  OR pass --enable-ssl-parity

Usage:
  SSL_PARITY_ENGINE=1 DB_URL=... python3 scripts/ssl_parity_shadow_run.py \\
    --apply --version 2026-07-26-003 --out-dir /tmp/ssl_parity_003

  python3 scripts/ssl_parity_shadow_run.py --mode=ssa-v2 --as-of 2026-07-27 \\
    --out-dir /tmp/ssl_parity_ssa_v2_2026-07-27
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
import unicodedata
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "utils"))

DEFAULT_VERSION = "2026-07-26-003"
BASELINE_VERSION = "2026-07-26-002"
DEFAULT_MODE = "parity"
SSA_V2_MODE = "ssa-v2"
PUBLISHED_AS_AT = date(2026, 7, 27)
BEST_N_NON_LOCAL = 6
LOCAL_OR_SSA8 = {7, 8}
WINDOW_WEEKS = 104
VALIDATION_NAMES = (
    "Sean Kavanagh",
    "Joshua Keytel",
    "Blaine Dodds",
    "Timothy Weaving",
)
SSA_V2_VALIDATION_NAMES = (
    "Sean Kavanagh",
    "Timothy Weaving",
    "Joshua Keytel",
    "Thomas Henshilwood",
)
FORBIDDEN_PUBLISH_PATHS = (
    "published.json",
    "/var/www/sailingsa/rankings/data",
)

# Authoritative SAS event_rating_type / event_scope / event_rating_level only.
# Never inferred from event names or WoS.
_SAS_TYPE_MAP = {
    "world championship / olympics": ("world", "world_championship", 2),
    "continental championship": ("continental", None, 3),
    "south african championship / nationals": ("national", "national_championship", 5),
    "provincial championship": ("regional", "regional_championship", 6),
    "regional championship": ("regional", "regional_championship", 6),
    "major open regatta": ("ordinary", None, None),
    "club championship": ("ordinary", None, None),
}
_SAS_SCOPE_MAP = {
    "WORLD": ("world", "world_championship", 2),
    "CONTINENTAL": ("continental", None, 3),
    "INTERNATIONAL": ("international", None, 4),
    "NATIONAL": ("national", "national_championship", 5),
    "NATIONAL_OPEN": ("ordinary", None, None),
    "PROVINCIAL": ("regional", "regional_championship", 6),
    "REGIONAL": ("regional", "regional_championship", 6),
    "CLUB": ("ordinary", None, None),
    "CLUB_SERIES": ("ordinary", None, None),
}
_SAS_LEVEL_MAP = {
    1000: ("world", "world_championship", 2),
    750: ("continental", None, 3),
    600: ("international", None, 4),
    500: ("national", "national_championship", 5),
    350: ("regional", "regional_championship", 6),
    250: ("ordinary", None, None),
    150: ("regional", "regional_championship", 6),
    100: ("ordinary", None, None),
    75: ("ordinary", None, None),
    50: ("ordinary", None, None),
}
_CHAMP_KINDS = {"world", "continental", "international", "national", "regional"}


def _norm_sas_type(raw: Any) -> str:
    return re.sub(r"\s+", " ", str(raw or "").strip().lower())


def _parse_sas_level(raw: Any) -> Optional[int]:
    try:
        if raw in (None, ""):
            return None
        return int(raw)
    except (TypeError, ValueError):
        return None


def _resolve_sas_event_type(row: Any) -> dict:
    """Map SAS event type/scope/level. Unknown types are reported, not Cat 6."""
    type_raw = getattr(row, "event_rating_type", None)
    scope_raw = getattr(row, "event_scope", None)
    level = _parse_sas_level(getattr(row, "event_rating_level", None))
    from_type = _SAS_TYPE_MAP.get(_norm_sas_type(type_raw))
    from_scope = _SAS_SCOPE_MAP.get(str(scope_raw or "").strip().upper()) or None
    from_level = _SAS_LEVEL_MAP.get(level) if level is not None else None
    chosen = from_type or from_scope or from_level
    sources = [s for s in (from_type, from_scope, from_level) if s]
    if chosen is None or (len({s[0] for s in sources}) > 1):
        return {
            "kind": "unknown",
            "official_status": None,
            "base_category": None,
            "event_rating_type": type_raw,
            "event_scope": scope_raw,
            "event_rating_level": level,
            "reason": "unknown_or_conflicting_sas_event_type",
        }
    kind, official_status, base_cat = chosen
    return {
        "kind": kind,
        "official_status": official_status,
        "base_category": base_cat,
        "event_rating_type": type_raw,
        "event_scope": scope_raw,
        "event_rating_level": level,
        "reason": None,
    }


def _championship_category_after_fleet(base_category: int, fleet: int) -> int:
    """Under-10 championships drop exactly one category. N>=10 keeps the base."""
    if fleet >= 10:
        return int(base_category)
    return min(int(base_category) + 1, 7)


def connect(db_url: str):
    import psycopg2

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def assert_db(conn) -> None:
    cur = conn.cursor()
    cur.execute("SELECT current_database()")
    db = cur.fetchone()[0]
    if db != "sailors_master":
        raise SystemExit(f"Refusing to run: database is {db!r}, expected sailors_master")


def write_reports(
    out_dir: Path,
    *,
    skippers,
    crews,
    audit_meta: dict,
    todos,
    baseline_ranks: dict,
    formula_version: str,
    formula_notes_fn,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_board(path: Path, sailors):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "rank",
                    "previous_rank",
                    "rank_change",
                    "ssl_points",
                    "sailor_name",
                    "sas_id",
                    "club_name",
                    "class_name",
                    "sail_number",
                    "total_rated_events",
                    "total_rated_races",
                    "board",
                ],
            )
            w.writeheader()
            for s in sailors[:100]:
                w.writerow(
                    {
                        "rank": s.rank,
                        "previous_rank": s.previous_rank,
                        "rank_change": s.rank_change,
                        "ssl_points": s.total_points,
                        "sailor_name": s.sailor_name,
                        "sas_id": s.sas_id or "",
                        "club_name": s.club_name or "",
                        "class_name": s.class_name or "",
                        "sail_number": s.sail_number or "",
                        "total_rated_events": s.total_rated_events,
                        "total_rated_races": s.total_rated_races,
                        "board": s.board,
                    }
                )

    write_board(out_dir / "top100_skippers.csv", skippers)
    write_board(out_dir / "top100_crews.csv", crews)

    movements = []
    for s in skippers:
        pr = baseline_ranks.get(s.identity_key)
        if pr is None:
            movements.append(
                {
                    "sailor_name": s.sailor_name,
                    "sas_id": s.sas_id,
                    "rank_003": s.rank,
                    "rank_002": None,
                    "delta": None,
                    "note": "new_or_unmatched",
                    "points_003": s.total_points,
                }
            )
            continue
        delta = int(pr) - int(s.rank)
        movements.append(
            {
                "sailor_name": s.sailor_name,
                "sas_id": s.sas_id,
                "rank_003": s.rank,
                "rank_002": pr,
                "delta": delta,
                "note": "compared",
                "points_003": s.total_points,
            }
        )
    improved = sorted([m for m in movements if m["delta"] is not None], key=lambda m: -m["delta"])[:30]
    declined = sorted([m for m in movements if m["delta"] is not None], key=lambda m: m["delta"])[:30]
    (out_dir / "movements_vs_002.json").write_text(
        json.dumps({"biggest_improvers": improved, "biggest_decliners": declined}, indent=2),
        encoding="utf-8",
    )

    def find_sailor(name: str):
        target = name.lower()
        for s in skippers:
            if s.sailor_name.lower() == target:
                return s
        for s in skippers:
            if target in s.sailor_name.lower():
                return s
        return None

    validation = []
    for name in VALIDATION_NAMES:
        s = find_sailor(name)
        if not s:
            validation.append({"sailor": name, "found": False})
            continue
        pr = baseline_ranks.get(s.identity_key)
        validation.append(
            {
                "sailor": name,
                "found": True,
                "rank_003_skipper": s.rank,
                "points_003": s.total_points,
                "events_counted": s.total_rated_events,
                "rank_002": pr,
                "delta_vs_002": (int(pr) - int(s.rank)) if pr is not None else None,
                "top_contribs": [
                    {
                        "points": c.points,
                        "event": c.event_name,
                        "place": c.place,
                        "fleet": c.fleet_size,
                        "category": c.category_name,
                        "date": c.event_date.isoformat(),
                        "time_coeff": c.time_coeff,
                    }
                    for c in s.contribs_counted[:8]
                ],
            }
        )
    (out_dir / "validation_sailors.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")

    todo_counts: dict[str, int] = {}
    for t in todos:
        todo_counts[t.code] = todo_counts.get(t.code, 0) + 1
    todo_doc = {
        "required_edge_case_todos": [
            "local_interpolation",
            "dnf_dns_dsq",
            "eq1_anomaly",
            "exact_rounding",
        ],
        "counts_during_calculation": todo_counts,
        "samples": [{"code": t.code, "detail": t.detail} for t in todos[:80]],
    }
    (out_dir / "todos.json").write_text(json.dumps(todo_doc, indent=2), encoding="utf-8")

    summary = {
        "audit_meta": audit_meta,
        "formula_version": formula_version,
        "formula_notes": formula_notes_fn(),
        "skipper_count": len(skippers),
        "crew_count": len(crews),
        "baseline_audit": BASELINE_VERSION,
        "validation": validation,
        "todo_counts": todo_counts,
        "top10_skippers": [
            {"rank": s.rank, "name": s.sailor_name, "points": s.total_points}
            for s in skippers[:10]
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _assert_non_published_out_dir(out_dir: Path) -> None:
    resolved = str(out_dir.resolve()) if out_dir.exists() or out_dir.parent.exists() else str(out_dir)
    lowered = resolved.lower()
    for bad in FORBIDDEN_PUBLISH_PATHS:
        if bad in lowered:
            raise SystemExit(f"ssa-v2 forbids writing under {bad!r}: {out_dir}")
    if out_dir.name == "published.json" or lowered.endswith("published.json"):
        raise SystemExit("ssa-v2 forbids writing published.json")


def _load_module_from_path(modname: str, path: Path):
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {modname} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_live_engine():
    for extra in (Path("/var/www/sailingsa/utils"), Path("/var/www/sailingsa"), _ROOT / "utils"):
        if extra.is_dir() and str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    import ssl_parity_engine as eng  # noqa: WPS433

    return eng


def _load_pr13_score_result():
    """Load PR13 scorer without displacing live ssl_parity_classification used by the engine."""
    cls_path = _ROOT / "ssl_parity_classification.py"
    score_path = _ROOT / "ssl_parity_scoring.py"
    if not cls_path.is_file() or not score_path.is_file():
        raise SystemExit(
            "PR13 ssl_parity_classification.py / ssl_parity_scoring.py not found next to scripts/"
        )
    saved = sys.modules.get("ssl_parity_classification")
    pr13_cls = _load_module_from_path("ssl_parity_classification_pr13", cls_path)
    sys.modules["ssl_parity_classification"] = pr13_cls
    try:
        pr13_score = _load_module_from_path("ssl_parity_scoring_pr13", score_path)
    finally:
        if saved is not None:
            sys.modules["ssl_parity_classification"] = saved
        else:
            sys.modules.pop("ssl_parity_classification", None)
    return pr13_score.score_result, pr13_cls


def _slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unknown"


def _identity_key(sas_id: Optional[str], name: str) -> str:
    sid = (sas_id or "").strip()
    if sid:
        return f"sas:{sid}"
    return f"name:{_slugify(name)}"


def _load_published_readonly() -> Optional[dict]:
    candidates = []
    env = os.environ.get("SSL_PARITY_PUBLISHED_JSON")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path("/tmp/published.json"),
            Path("/var/www/sailingsa/rankings/data/published.json"),
            _ROOT / "rankings" / "data" / "published.json",
        ]
    )
    for path in candidates:
        if path.is_file() and path.name == "published.json":
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    return None


def _select_best6_plus_local_cat8(items: list[dict]) -> tuple[list[dict], float]:
    """Best six non-local (Cat 1–6) plus all local (7) and SSA Cat 8."""
    localish = [s for s in items if s.get("category") in LOCAL_OR_SSA8 and (s.get("points") or 0) > 0]
    non_local = sorted(
        [s for s in items if s.get("category") not in LOCAL_OR_SSA8 and (s.get("points") or 0) > 0],
        key=lambda x: -float(x["points"]),
    )
    counted = non_local[:BEST_N_NON_LOCAL] + localish
    total = round(sum(float(s["points"]) for s in counted), 2)
    return counted, total


def _find_named(sailors: list[dict], name: str) -> Optional[dict]:
    target = name.lower()
    for s in sailors:
        if (s.get("sailor_name") or "").lower() == target:
            return s
    for s in sailors:
        if target in (s.get("sailor_name") or "").lower():
            return s
    return None


def run_ssa_v2(conn, *, as_of: date, out_dir: Path) -> dict:
    _assert_non_published_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor()
    try:
        cur.execute("SET default_transaction_read_only = on")
    except Exception:
        pass
    cur.execute("SELECT COUNT(*) FROM results")
    results_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM regattas")
    regattas_before = cur.fetchone()[0]

    eng = _import_live_engine()
    pr13_score_result, _pr13_cls = _load_pr13_score_result()
    window_start = as_of - timedelta(weeks=WINDOW_WEEKS)
    raw_rows = eng.fetch_result_rows(conn, history_start=window_start)

    errors: list[dict] = []
    n1_exclusions = 0
    cat_classified: dict[str, int] = defaultdict(int)
    unknown_type_keys: dict[str, int] = defaultdict(int)
    contribs: list[Any] = []

    for r in raw_rows:
        fleet = int(getattr(r, "fleet_size", 0) or 0)
        if fleet == 1:
            n1_exclusions += 1
        place = getattr(r, "place", None)
        sas_event = _resolve_sas_event_type(r)
        if sas_event["kind"] == "unknown":
            key = "%s|%s|%s" % (
                sas_event.get("event_scope"),
                sas_event.get("event_rating_type"),
                sas_event.get("event_rating_level"),
            )
            unknown_type_keys[key] += 1
            errors.append(
                {
                    "code": "unknown_event_type",
                    "result_id": getattr(r, "result_id", None),
                    "regatta_id": getattr(r, "regatta_id", None),
                    "event": getattr(r, "event_name", None),
                    "sailor": getattr(r, "sailor_name", None),
                    "event_scope": sas_event.get("event_scope"),
                    "event_rating_type": sas_event.get("event_rating_type"),
                    "event_rating_level": sas_event.get("event_rating_level"),
                }
            )
            cat_classified["unknown"] += 1
            continue
        if place is None:
            errors.append(
                {
                    "code": "missing_place",
                    "result_id": getattr(r, "result_id", None),
                    "event": getattr(r, "event_name", None),
                    "sailor": getattr(r, "sailor_name", None),
                }
            )
            cat_classified["none"] += 1
            continue
        kind = sas_event["kind"]
        official_status = sas_event["official_status"]
        is_champ = kind in _CHAMP_KINDS
        # N=2 is SSA Cat 8 only. Do not force a championship category.
        score_kwargs: dict[str, Any] = {
            "event_date": getattr(r, "event_date", None),
            "role": getattr(r, "role", None),
            "as_at": as_of,
            "mode": "ssa",
            "is_open": True,
            "restriction_count": 0,
            "championship": False if (kind == "ordinary" or fleet == 2) else is_champ,
            "official_status": None if (kind == "ordinary" or fleet == 2) else official_status,
            "championship_exception": None if (kind == "ordinary" or fleet == 2) else official_status,
        }
        if is_champ and fleet >= 3 and sas_event["base_category"] is not None:
            # World/Continental/International: PR13 maps world→Cat5, so lock the
            # SAS championship category here, then apply the under-10 one-tier drop.
            if kind in {"world", "continental", "international"}:
                score_kwargs["category"] = _championship_category_after_fleet(
                    int(sas_event["base_category"]), fleet
                )
        try:
            scored = pr13_score_result(
                getattr(r, "event_name", None),
                fleet,
                place,
                getattr(r, "class_name", None),
                **score_kwargs,
            )
        except Exception as exc:  # noqa: BLE001 — shadow audit must not abort the dataset
            errors.append(
                {
                    "code": "score_exception",
                    "result_id": getattr(r, "result_id", None),
                    "event": getattr(r, "event_name", None),
                    "sailor": getattr(r, "sailor_name", None),
                    "detail": str(exc),
                }
            )
            continue

        cat = scored.category
        cat_classified[str(cat if cat is not None else "none")] += 1
        ident = _identity_key(getattr(r, "sas_id", None), getattr(r, "sailor_name", "") or "")
        counts = bool(scored.eligible and scored.points > 0)
        contribs.append(
            SimpleNamespace(
                identity_key=ident,
                sas_id=getattr(r, "sas_id", None),
                sailor_slug=_slugify(getattr(r, "sailor_name", "") or ""),
                sailor_name=getattr(r, "sailor_name", "") or "",
                result_id=getattr(r, "result_id", None),
                regatta_id=getattr(r, "regatta_id", None),
                event_name=getattr(r, "event_name", None),
                board="all",
                role=getattr(r, "role", None),
                place=int(place),
                fleet_size=fleet,
                races_sailed=int(getattr(r, "races_sailed", 0) or 0),
                category=cat,
                category_name=scored.category_name,
                points=float(scored.points or 0),
                time_coeff=float(scored.age_factor or 0),
                class_name=getattr(r, "class_name", None),
                club_name=getattr(r, "club_name", None),
                sail_number=getattr(r, "sail_number", None),
                event_date=getattr(r, "event_date", None),
                counts_toward_rank=counts,
                eligible=bool(scored.eligible),
                sas_event_kind=kind,
                reason=scored.reason,
                underlying_entry_key=f"result:{getattr(r, 'result_id', '')}",
                selected_for_regatta=None,
                selected_result_id=None,
                exclusion_reason=None,
            )
        )

    # Same identity + same result: one role-neutral row (keep higher points).
    best: dict[tuple, Any] = {}
    for c in contribs:
        key = (c.identity_key, c.result_id)
        prev = best.get(key)
        if prev is None or float(c.points) > float(prev.points):
            best[key] = c
    contribs = list(best.values())

    dedup_groups: list[dict] = []
    if hasattr(eng, "dedupe_same_regatta_contributions"):
        contribs, dedup_groups = eng.dedupe_same_regatta_contributions(contribs)
        for c in contribs:
            if getattr(c, "selected_for_regatta", True) is False:
                c.counts_toward_rank = False
                c.points = 0.0

    by_id: dict[str, list[Any]] = defaultdict(list)
    for c in contribs:
        by_id[c.identity_key].append(c)

    sailors: list[dict] = []
    cat_counting: dict[str, int] = defaultdict(int)
    for ident, items in by_id.items():
        payload = []
        for c in items:
            if getattr(c, "counts_toward_rank", False) and c.points > 0:
                payload.append(
                    {
                        "points": float(c.points),
                        "category": c.category,
                        "category_name": c.category_name,
                        "event": c.event_name,
                        "place": c.place,
                        "fleet": c.fleet_size,
                        "class_name": c.class_name,
                        "date": c.event_date.isoformat() if c.event_date else None,
                        "time_coeff": c.time_coeff,
                        "role": c.role,
                        "result_id": c.result_id,
                    }
                )
        counted, total = _select_best6_plus_local_cat8(payload)
        if total <= 0:
            continue
        tip = items[0]
        for it in items:
            if it.sas_id:
                tip = it
                break
        for row in counted:
            cat_counting[str(row.get("category"))] += 1
        sailors.append(
            {
                "identity_key": ident,
                "sas_id": next((c.sas_id for c in items if c.sas_id), tip.sas_id),
                "sailor_name": tip.sailor_name,
                "slug": tip.sailor_slug,
                "club_name": tip.club_name,
                "class_name": tip.class_name,
                "total_points": total,
                "events_counted": len(counted),
                "contribs_counted": counted,
            }
        )

    sailors.sort(
        key=lambda s: (
            -float(s["total_points"]),
            -int(s["events_counted"]),
            (s.get("sailor_name") or "").lower(),
        )
    )
    for i, s in enumerate(sailors, start=1):
        s["rank"] = i

    published = _load_published_readonly()
    pub_by_sas: dict[str, dict] = {}
    pub_by_slug: dict[str, dict] = {}
    if published:
        for row in published.get("sailors") or []:
            sas = str(row.get("sasId") or "").strip()
            slug = str(row.get("slug") or "").strip()
            if sas:
                pub_by_sas[sas] = row
            if slug:
                pub_by_slug[slug] = row

    for s in sailors:
        live = None
        if s.get("sas_id"):
            live = pub_by_sas.get(str(s["sas_id"]).strip())
        if live is None:
            live = pub_by_slug.get(s.get("slug") or "")
        if live is None:
            s["published_rank"] = None
            s["published_points"] = None
            s["delta_rank"] = None
            s["delta_points"] = None
            continue
        s["published_rank"] = live.get("overallRank") or live.get("rank")
        s["published_points"] = live.get("overallPoints") or live.get("points")
        if s["published_rank"] is not None:
            s["delta_rank"] = int(s["published_rank"]) - int(s["rank"])
        else:
            s["delta_rank"] = None
        if s["published_points"] is not None:
            s["delta_points"] = round(float(s["total_points"]) - float(s["published_points"]), 2)
        else:
            s["delta_points"] = None

    validation = []
    for name in SSA_V2_VALIDATION_NAMES:
        s = _find_named(sailors, name)
        if not s:
            validation.append({"sailor": name, "found": False})
            continue
        validation.append(
            {
                "sailor": name,
                "found": True,
                "sas_id": s.get("sas_id"),
                "proposed_rank": s.get("rank"),
                "proposed_points": s.get("total_points"),
                "published_rank": s.get("published_rank"),
                "published_points": s.get("published_points"),
                "delta_rank": s.get("delta_rank"),
                "delta_points": s.get("delta_points"),
                "events_counted": s.get("events_counted"),
                "top_contribs": (s.get("contribs_counted") or [])[:8],
            }
        )

    ranked_with_pub = [s for s in sailors if s.get("published_rank") is not None]
    audit = {
        "mode": SSA_V2_MODE,
        "as_of": as_of.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": as_of.isoformat(),
        "is_published": False,
        "db_writes": False,
        "published_json_written": False,
        "raw_extracted_rows": len(raw_rows),
        "scored_contribs": len(contribs),
        "proposed_sailor_count": len(sailors),
        "category_classified_counts": dict(sorted(cat_classified.items(), key=lambda kv: str(kv[0]))),
        "category_counting_counts": dict(sorted(cat_counting.items(), key=lambda kv: str(kv[0]))),
        "n1_exclusions": n1_exclusions,
        "unknown_event_types": dict(sorted(unknown_type_keys.items(), key=lambda kv: -kv[1])),
        "unknown_event_type_count": sum(unknown_type_keys.values()),
        "exceptions": errors[:200],
        "exception_count": len(errors),
        "dedup_groups": len(dedup_groups),
        "top10": [
            {
                "rank": s["rank"],
                "name": s["sailor_name"],
                "sas_id": s.get("sas_id"),
                "points": s["total_points"],
                "published_rank": s.get("published_rank"),
                "delta_rank": s.get("delta_rank"),
                "delta_points": s.get("delta_points"),
            }
            for s in sailors[:10]
        ],
        "validation": validation,
        "delta_summary": {
            "matched_to_published": len(ranked_with_pub),
            "unmatched_proposed": len(sailors) - len(ranked_with_pub),
            "mean_delta_points": (
                round(sum(s["delta_points"] for s in ranked_with_pub if s.get("delta_points") is not None)
                      / max(len([s for s in ranked_with_pub if s.get("delta_points") is not None]), 1), 2)
                if ranked_with_pub
                else None
            ),
        },
        "aggregation": "best_6_non_local_plus_all_local_and_ssa_cat8",
        "scoring": (
            "PR13 score_result(mode=ssa) from SAS rank/class/fleet/date plus "
            "authoritative SAS event type/scope/level; WoS unused"
        ),
    }

    cur.execute("SELECT COUNT(*) FROM results")
    results_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM regattas")
    regattas_after = cur.fetchone()[0]
    if results_after != results_before or regattas_after != regattas_before:
        raise RuntimeError("Safety check failed: results/regattas counts changed")
    conn.rollback()

    (out_dir / "audit.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    (out_dir / "proposed_sailors.json").write_text(
        json.dumps(
            [
                {
                    "rank": s["rank"],
                    "sailor_name": s["sailor_name"],
                    "sas_id": s.get("sas_id"),
                    "slug": s.get("slug"),
                    "points": s["total_points"],
                    "events_counted": s["events_counted"],
                    "published_rank": s.get("published_rank"),
                    "published_points": s.get("published_points"),
                    "delta_rank": s.get("delta_rank"),
                    "delta_points": s.get("delta_points"),
                }
                for s in sailors
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    return audit


def run_default_parity(conn, args, out_dir: Path, as_of: date) -> dict:
    eng = _import_live_engine()
    from ssl_parity_formula import FORMULA_VERSION, formula_notes  # noqa: WPS433

    if not eng.feature_enabled(explicit=args.enable_ssl_parity):
        raise SystemExit(
            f"SSL parity engine disabled. Set {eng.FEATURE_FLAG_ENV}=1 or pass --enable-ssl-parity"
        )
    if not args.apply and not args.dry_run:
        raise SystemExit("Specify --apply or --dry-run")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM results")
    results_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM regattas")
    regattas_before = cur.fetchone()[0]

    skippers, crews, _contribs, todos, window_start, window_end, as_of = eng.compute_ssl_parity_ranking(
        conn, as_of=as_of
    )
    baseline_ranks = eng.load_ranks_for_version(conn, BASELINE_VERSION)
    eng.apply_previous_ranks(skippers, baseline_ranks)

    audit_meta = {
        "ranking_version": args.version,
        "formula_version": FORMULA_VERSION,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "as_of": as_of.isoformat(),
        "is_published": False,
        "dry_run": bool(args.dry_run and not args.apply),
        "mode": DEFAULT_MODE,
    }

    if args.apply:
        published = eng.publish_shadow_audit(
            conn,
            skippers=skippers,
            crews=crews,
            ranking_version=args.version,
            window_start=window_start,
            window_end=window_end,
            as_of=as_of,
            todos=todos,
            replace=args.replace,
        )
        audit_meta.update(published)

    cur.execute("SELECT COUNT(*) FROM results")
    results_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM regattas")
    regattas_after = cur.fetchone()[0]
    if results_after != results_before or regattas_after != regattas_before:
        raise RuntimeError("Safety check failed: results/regattas counts changed")

    write_reports(
        out_dir,
        skippers=skippers,
        crews=crews,
        audit_meta=audit_meta,
        todos=todos,
        baseline_ranks=baseline_ranks,
        formula_version=FORMULA_VERSION,
        formula_notes_fn=formula_notes,
    )
    return audit_meta


def main() -> None:
    ap = argparse.ArgumentParser(description="SSL Parity shadow audit runner")
    ap.add_argument("--apply", action="store_true", help="Write shadow audit to DB (default path only)")
    ap.add_argument("--dry-run", action="store_true", help="Compute only, no DB write")
    ap.add_argument("--enable-ssl-parity", action="store_true", help="Enable feature flag for this run")
    ap.add_argument("--version", default=DEFAULT_VERSION, help="Audit ranking_version")
    ap.add_argument("--as-of", default="", help="YYYY-MM-DD (default today; ssa-v2 default 2026-07-27)")
    ap.add_argument("--out-dir", default="", help="Output directory (required for default path)")
    ap.add_argument("--replace", action="store_true", help="Replace existing same version (dangerous)")
    ap.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        choices=(DEFAULT_MODE, SSA_V2_MODE),
        help="parity = existing engine (default); ssa-v2 = PR13 SSA scoring, read-only",
    )
    args = ap.parse_args()

    if args.mode == SSA_V2_MODE and args.apply:
        raise SystemExit("ssa-v2 forbids --apply / DB writes / published.json")

    db_url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DB_URL / DATABASE_URL required")

    if args.mode == SSA_V2_MODE:
        as_of = date.fromisoformat(args.as_of) if args.as_of else PUBLISHED_AS_AT
        out_dir = Path(args.out_dir) if args.out_dir else Path(f"/tmp/ssl_parity_ssa_v2_{as_of.isoformat()}")
    else:
        if not args.out_dir:
            raise SystemExit("--out-dir is required")
        as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
        out_dir = Path(args.out_dir)

    conn = connect(db_url)
    try:
        assert_db(conn)
        if args.mode == SSA_V2_MODE:
            audit = run_ssa_v2(conn, as_of=as_of, out_dir=out_dir)
            print(json.dumps({"ok": True, "mode": SSA_V2_MODE, "audit": audit, "out_dir": str(out_dir)}, indent=2, default=str))
        else:
            audit_meta = run_default_parity(conn, args, out_dir, as_of)
            print(json.dumps({"ok": True, "audit": audit_meta, "out_dir": str(out_dir)}, indent=2))
    finally:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


if __name__ == "__main__":
    main()
