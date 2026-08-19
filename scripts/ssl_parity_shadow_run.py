#!/usr/bin/env python3
"""SSL Parity SHADOW run — Phase 1 + SSA-v2 path.

Completely separate from sas-points-v1.x.
Default path writes ONLY ranking_audit* for a new audit. Does NOT publish.
Does NOT touch api.py.

--mode=ssa-v2 is read-only: reuses live SAS extraction plus live
age-division classification, drops U17/U19/Youth subdivision rows when
Overall/Open exists for the same sailor/regatta/class (never summed),
then scores with PR13 score_result(mode="ssa") using SAS event type
(not WoS). Writes audit JSON to a non-published path. Forbids DB writes
and published.json.

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
from collections import Counter, defaultdict
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

# Live championship classification (utils/ssl_parity_classification.py on live).
# Overall/Open/class tables win; age-subdivision sheets are excluded, never summed.
_MAIN_FLEET_TYPES = frozenset({"OVERALL", "OPEN", "CLASS"})
_SUBDIVISION_TYPES = frozenset({"U17", "U19", "YOUTH", "JUNIOR"})
_DROP_WHEN_MAIN = _SUBDIVISION_TYPES | frozenset({"SENIOR", "INCIDENTAL"})
_KEEP_ORDER = {
    "OVERALL": 0,
    "OPEN": 1,
    "CLASS": 2,
    "SENIOR": 3,
    "U19": 4,
    "YOUTH": 5,
    "JUNIOR": 6,
    "U17": 7,
    "UNKNOWN": 8,
    "INCIDENTAL": 99,
}
TIM_SAS_ID = "21172"
TIM_420_OVERALL_RESULT_ID = 837
TIM_420_DIVISION_RESULT_IDS = frozenset({10381, 10382})
AGE_DIVISION_EXCLUSION_REASON = (
    "Duplicate age-division sheet for the same sailor/regatta/class — "
    "Overall/Open retained; U17/U19/Youth subdivision excluded (never summed)."
)
BEST6_EXCLUSION_REASON = "outside_best_6_non_local"
ROLE_COLLAPSE_EXCLUSION_REASON = "same_result_lower_role_points"
LIVE_DEDUP_EXCLUSION_REASON = (
    "Duplicate classification within same regatta — higher eligible championship contribution selected."
)


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


def _iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _median(values: list[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return round(float(ordered[mid]), 4)
    return round((float(ordered[mid - 1]) + float(ordered[mid])) / 2.0, 4)


def _contrib_key(row: dict) -> tuple:
    return (row.get("result_id"), row.get("role"), row.get("identity_key"))


def _full_contrib_dict(c: Any) -> dict:
    """All scoring inputs/outputs plus exclusion metadata for one contribution."""
    dt = getattr(c, "event_date", None)
    return {
        "identity_key": getattr(c, "identity_key", None),
        "sas_id": getattr(c, "sas_id", None),
        "sailor_name": getattr(c, "sailor_name", None),
        "result_id": getattr(c, "result_id", None),
        "regatta_id": getattr(c, "regatta_id", None),
        "event": getattr(c, "event_name", None),
        "event_date": _iso_date(dt),
        "class_name": getattr(c, "class_name", None),
        "sail_number": getattr(c, "sail_number", None),
        "club_name": getattr(c, "club_name", None),
        "role": getattr(c, "role", None),
        "place": getattr(c, "place", None),
        "fleet": getattr(c, "fleet_size", None),
        "races_sailed": getattr(c, "races_sailed", None),
        "block_id": getattr(c, "block_id", None),
        "fleet_label": getattr(c, "fleet_label", None),
        "age_category": getattr(c, "age_category", None),
        "championship_type": getattr(c, "classification_type", None),
        "championship_label": getattr(c, "classification_label", None),
        "classification_breadth": getattr(c, "classification_breadth", None),
        "official_classification": getattr(c, "official_classification", None),
        "underlying_entry_key": getattr(c, "underlying_entry_key", None),
        "live_underlying_entry_key": getattr(c, "live_underlying_entry_key", None),
        "sas_event_kind": getattr(c, "sas_event_kind", None),
        "event_rating_type": getattr(c, "event_rating_type", None),
        "event_scope": getattr(c, "event_scope", None),
        "event_rating_level": getattr(c, "event_rating_level", None),
        "mode": "ssa",
        "as_at": _iso_date(getattr(c, "as_at", None)),
        "is_open": getattr(c, "is_open", True),
        "restriction_count": getattr(c, "restriction_count", 0),
        "championship": getattr(c, "championship", None),
        "official_status": getattr(c, "official_status", None),
        "championship_exception": getattr(c, "championship_exception", None),
        "category_override": getattr(c, "category_override", None),
        "points": float(getattr(c, "points", 0) or 0),
        "eligible": bool(getattr(c, "eligible", False)),
        "category": getattr(c, "category", None),
        "category_name": getattr(c, "category_name", None),
        "category_base": getattr(c, "category_base", None),
        "class_coefficient": getattr(c, "class_coefficient", None),
        "open_coefficient": getattr(c, "open_coefficient", None),
        "place_factor": getattr(c, "place_factor", None),
        "placement_points": getattr(c, "placement_points", None),
        "time_coeff": getattr(c, "time_coeff", None),
        "ssa_rating": getattr(c, "ssa_rating", None),
        "reason": getattr(c, "reason", None),
        "exclusion_reason": getattr(c, "exclusion_reason", None),
        "counts_toward_rank": bool(getattr(c, "counts_toward_rank", False)),
        "selected_for_regatta": getattr(c, "selected_for_regatta", None),
        "selected_result_id": getattr(c, "selected_result_id", None),
    }


def _cat78_and_concentration(sailors: list[dict]) -> dict:
    """Audit summaries: Cat7/8 share of counted points, one-event concentration."""
    all_counting_points = 0.0
    cat7_points = 0.0
    cat8_points = 0.0
    cat7_events = 0
    cat8_events = 0
    sailors_any_7 = 0
    sailors_any_8 = 0
    sailors_majority_78 = 0
    max_shares: list[float] = []
    ge50 = 0
    ge75 = 0
    single_only = 0
    concentrated: list[dict] = []
    for s in sailors:
        counted = s.get("contribs_counted") or []
        total = float(s.get("total_points") or 0)
        s7 = 0.0
        s8 = 0.0
        n7 = 0
        n8 = 0
        for row in counted:
            pts = float(row.get("points") or 0)
            all_counting_points += pts
            cat = row.get("category")
            if cat == 7:
                cat7_points += pts
                cat7_events += 1
                s7 += pts
                n7 += 1
            elif cat == 8:
                cat8_points += pts
                cat8_events += 1
                s8 += pts
                n8 += 1
        if n7:
            sailors_any_7 += 1
        if n8:
            sailors_any_8 += 1
        share78 = round((s7 + s8) / total, 4) if total else None
        s["cat7_points"] = round(s7, 2)
        s["cat8_points"] = round(s8, 2)
        s["cat7_8_share"] = share78
        if share78 is not None and share78 >= 0.5:
            sailors_majority_78 += 1
        if counted and total:
            top = max(counted, key=lambda r: float(r.get("points") or 0))
            share = round(float(top.get("points") or 0) / total, 4)
        else:
            top = None
            share = None
        s["max_event_share"] = share
        s["max_event"] = (top or {}).get("event")
        s["max_event_points"] = float((top or {}).get("points") or 0) if top else 0.0
        if share is not None:
            max_shares.append(share)
            if share >= 0.5:
                ge50 += 1
            if share >= 0.75:
                ge75 += 1
            if len(counted) == 1:
                single_only += 1
            concentrated.append(
                {
                    "sailor_name": s.get("sailor_name"),
                    "sas_id": s.get("sas_id"),
                    "rank": s.get("rank"),
                    "total_points": s.get("total_points"),
                    "max_event_share": share,
                    "event": s.get("max_event"),
                    "event_points": s.get("max_event_points"),
                    "events_counted": s.get("events_counted"),
                }
            )
    concentrated.sort(key=lambda r: -float(r["max_event_share"]))
    denom = all_counting_points or 1.0
    return {
        "cat7_8_share": {
            "counting_points_all": round(all_counting_points, 2),
            "cat7_counting_events": cat7_events,
            "cat8_counting_events": cat8_events,
            "cat7_counting_points": round(cat7_points, 2),
            "cat8_counting_points": round(cat8_points, 2),
            "cat7_share": round(cat7_points / denom, 4) if all_counting_points else 0.0,
            "cat8_share": round(cat8_points / denom, 4) if all_counting_points else 0.0,
            "cat7_or_8_share": round((cat7_points + cat8_points) / denom, 4) if all_counting_points else 0.0,
            "sailors_with_any_cat7": sailors_any_7,
            "sailors_with_any_cat8": sailors_any_8,
            "sailors_majority_cat7_or_8": sailors_majority_78,
        },
        "one_event_concentration": {
            "mean_max_event_share": round(sum(max_shares) / len(max_shares), 4) if max_shares else None,
            "median_max_event_share": _median(max_shares),
            "sailors_one_event_ge_50pct": ge50,
            "sailors_one_event_ge_75pct": ge75,
            "sailors_single_event_only": single_only,
            "top_concentrated": concentrated[:25],
        },
    }


def _find_named(sailors: list[dict], name: str) -> Optional[dict]:
    target = name.lower()
    for s in sailors:
        if (s.get("sailor_name") or "").lower() == target:
            return s
    for s in sailors:
        if target in (s.get("sailor_name") or "").lower():
            return s
    return None


def _load_live_age_division_cls(eng) -> Any:
    """Load live championship classification from next to ssl_parity_engine.

    Must not use PR13 ssl_parity_classification.py (no age-division resolver).
    """
    candidates = []
    if getattr(eng, "__file__", None):
        candidates.append(Path(eng.__file__).resolve().parent / "ssl_parity_classification.py")
    candidates.extend(
        [
            Path("/var/www/sailingsa/utils/ssl_parity_classification.py"),
            Path("/tmp/ssl_parity_classification.live.py"),
        ]
    )
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        mod = _load_module_from_path("ssl_parity_age_division_cls", path)
        if hasattr(mod, "resolve_championship_classification") and hasattr(mod, "underlying_entry_key"):
            return mod
    raise SystemExit(
        "Live age-division classification not found next to ssl_parity_engine "
        "(need resolve_championship_classification / underlying_entry_key)"
    )


def _row_attr(row: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(row, name):
            val = getattr(row, name)
            if val not in (None, ""):
                return val
        elif isinstance(row, dict) and row.get(name) not in (None, ""):
            return row.get(name)
    return default


def _classify_raw_row(row: Any, cls_mod: Any) -> Any:
    return cls_mod.resolve_championship_classification(
        fleet_label=_row_attr(row, "fleet_label"),
        age_category=_row_attr(row, "age_category"),
        block_id=_row_attr(row, "block_id"),
        block_label=_row_attr(row, "block_label", "block_label_raw"),
        class_name=_row_attr(row, "class_name"),
    )


def _underlying_entry_key_for_row(row: Any, cls_mod: Any) -> str:
    return cls_mod.underlying_entry_key(
        regatta_id=_row_attr(row, "regatta_id") or "",
        class_name=_row_attr(row, "class_name"),
        class_slug=_row_attr(row, "class_slug"),
        sail_number=_row_attr(row, "sail_number"),
        entry_id=_row_attr(row, "entry_id"),
        sas_id=_row_attr(row, "sas_id"),
        result_id=_row_attr(row, "result_id"),
    )


def _age_division_group_key(row: Any, ident: str) -> tuple:
    """Same sailor / regatta / class — not per result_id or entry_id.

    Live underlying_entry_key prefers entry_id/result_id, which splits Overall
    vs U17/U19 sheets for the same boat. Group by sailor+regatta+class instead.
    """
    cls = (_row_attr(row, "class_slug", "class_name") or "").strip().lower()
    return (ident, _row_attr(row, "regatta_id"), cls)


def _keep_rank(classification_type: str) -> int:
    return int(_KEEP_ORDER.get(classification_type or "UNKNOWN", 50))


def _row_place_fleet(row: Any) -> tuple[int, int]:
    try:
        place = int(_row_attr(row, "place") or 10**9)
    except (TypeError, ValueError):
        place = 10**9
    try:
        fleet = int(_row_attr(row, "fleet_size") or 0)
    except (TypeError, ValueError):
        fleet = 0
    return place, fleet


def _pick_one_age_division_row(items: list[tuple]) -> tuple:
    """items: list of (row, clf, uek). Prefer Overall, then Open, then class."""

    def sort_key(item: tuple):
        row, clf, _uek = item
        place, fleet = _row_place_fleet(row)
        rid = int(_row_attr(row, "result_id") or 0)
        return (_keep_rank(clf.classification_type), -fleet, place, rid)

    ranked = sorted(items, key=sort_key)
    return ranked[0], ranked[1:]


def filter_age_division_rows_before_scoring(
    raw_rows: list, cls_mod: Any
) -> tuple[list, list[dict], list[dict], list]:
    """Reuse live championship classification; keep Overall/Open; never sum subdivisions.

    Returns (rows_to_count, exclusion_audit, collapsed_group_audit, excluded_rows).
    Excluded rows are scored for audit only and never enter Best 6.
    """
    grouped: dict[tuple, list[tuple]] = defaultdict(list)
    for row in raw_rows:
        ident = _identity_key(_row_attr(row, "sas_id"), _row_attr(row, "sailor_name") or "")
        clf = _classify_raw_row(row, cls_mod)
        uek = _underlying_entry_key_for_row(row, cls_mod)
        grouped[_age_division_group_key(row, ident)].append((row, clf, uek))

    kept: list = []
    exclusions: list[dict] = []
    groups_audit: list[dict] = []
    excluded_rows: list = []
    for key, items in grouped.items():
        types = {clf.classification_type for _row, clf, _uek in items}
        drop_types = _DROP_WHEN_MAIN if (types & _MAIN_FLEET_TYPES) else frozenset({"INCIDENTAL"})
        survivors = [it for it in items if it[1].classification_type not in drop_types]
        dropped = [it for it in items if it[1].classification_type in drop_types]
        if not survivors:
            survivors = [it for it in items if it[1].classification_type != "INCIDENTAL"]
            dropped = [it for it in items if it[1].classification_type == "INCIDENTAL"]
        winner, extras = _pick_one_age_division_row(survivors) if survivors else (None, [])
        dropped.extend(extras)
        if winner is not None:
            row, clf, uek = winner
            row.classification_type = clf.classification_type
            row.classification_label = clf.classification_label
            row.official_classification = bool(clf.official_classification)
            row.classification_breadth = int(getattr(clf, "breadth", 0) or 0)
            row.underlying_entry_key = "|".join("" if x is None else str(x) for x in key)
            row.live_underlying_entry_key = uek
            row.exclusion_reason = None
            row.selected_result_id = _row_attr(row, "result_id")
            kept.append(row)
        if dropped:
            win_id = _row_attr(winner[0], "result_id") if winner is not None else None
            win_type = winner[1].classification_type if winner is not None else None
            groups_audit.append(
                {
                    "identity_key": key[0],
                    "regatta_id": key[1],
                    "class_name": key[2],
                    "candidate_count": len(items),
                    "selected_result_id": win_id,
                    "selected_classification": win_type,
                    "excluded_result_ids": [_row_attr(r, "result_id") for r, _c, _u in dropped],
                    "excluded_classifications": [c.classification_type for _r, c, _u in dropped],
                }
            )
            for row, clf, uek in dropped:
                row.classification_type = clf.classification_type
                row.classification_label = clf.classification_label
                row.official_classification = bool(clf.official_classification)
                row.classification_breadth = int(getattr(clf, "breadth", 0) or 0)
                row.underlying_entry_key = "|".join("" if x is None else str(x) for x in key)
                row.live_underlying_entry_key = uek
                row.exclusion_reason = AGE_DIVISION_EXCLUSION_REASON
                row.selected_result_id = win_id
                excluded_rows.append(row)
                exclusions.append(
                    {
                        "result_id": _row_attr(row, "result_id"),
                        "sas_id": _row_attr(row, "sas_id"),
                        "sailor_name": _row_attr(row, "sailor_name"),
                        "event_name": _row_attr(row, "event_name"),
                        "regatta_id": _row_attr(row, "regatta_id"),
                        "class_name": _row_attr(row, "class_name"),
                        "place": _row_attr(row, "place"),
                        "fleet_size": _row_attr(row, "fleet_size"),
                        "championship_type": clf.classification_type,
                        "championship_label": clf.classification_label,
                        "block_id": _row_attr(row, "block_id"),
                        "fleet_label": _row_attr(row, "fleet_label"),
                        "age_category": _row_attr(row, "age_category"),
                        "selected_result_id": win_id,
                        "selected_classification": win_type,
                        "live_underlying_entry_key": uek,
                        "reason": AGE_DIVISION_EXCLUSION_REASON,
                    }
                )
    return kept, exclusions, groups_audit, excluded_rows


def _score_row_to_contrib(
    r: Any,
    *,
    as_of: date,
    pr13_score_result,
    preset_exclusion: Optional[str] = None,
) -> tuple[Any, Optional[dict], dict]:
    """Score one SAS row. Age-division losers are scored for audit but never count."""
    fleet = int(getattr(r, "fleet_size", 0) or 0)
    place = getattr(r, "place", None)
    sas_event = _resolve_sas_event_type(r)
    ident = _identity_key(getattr(r, "sas_id", None), getattr(r, "sailor_name", "") or "")
    kind = sas_event["kind"]
    official_status = sas_event["official_status"]
    is_champ = kind in _CHAMP_KINDS
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
    category_override = None
    if is_champ and fleet >= 3 and sas_event["base_category"] is not None:
        if kind in {"world", "continental", "international"}:
            category_override = _championship_category_after_fleet(int(sas_event["base_category"]), fleet)
            score_kwargs["category"] = category_override

    def _base_contrib(**extra: Any) -> Any:
        ns = SimpleNamespace(
            identity_key=ident,
            sas_id=getattr(r, "sas_id", None),
            sailor_slug=_slugify(getattr(r, "sailor_name", "") or ""),
            sailor_name=getattr(r, "sailor_name", "") or "",
            result_id=getattr(r, "result_id", None),
            regatta_id=getattr(r, "regatta_id", None),
            event_name=getattr(r, "event_name", None),
            board="all",
            role=getattr(r, "role", None),
            place=int(place) if place is not None else None,
            fleet_size=fleet,
            races_sailed=int(getattr(r, "races_sailed", 0) or 0),
            class_name=getattr(r, "class_name", None),
            club_name=getattr(r, "club_name", None),
            sail_number=getattr(r, "sail_number", None),
            event_date=getattr(r, "event_date", None),
            block_id=getattr(r, "block_id", None),
            fleet_label=getattr(r, "fleet_label", None),
            age_category=getattr(r, "age_category", None),
            classification_type=getattr(r, "classification_type", None),
            classification_label=getattr(r, "classification_label", None),
            classification_breadth=getattr(r, "classification_breadth", 0),
            official_classification=getattr(r, "official_classification", True),
            underlying_entry_key=getattr(r, "underlying_entry_key", None)
            or f"result:{getattr(r, 'result_id', '')}",
            live_underlying_entry_key=getattr(r, "live_underlying_entry_key", None),
            sas_event_kind=kind,
            event_rating_type=sas_event.get("event_rating_type"),
            event_scope=sas_event.get("event_scope"),
            event_rating_level=sas_event.get("event_rating_level"),
            as_at=as_of,
            is_open=True,
            restriction_count=0,
            championship=score_kwargs["championship"],
            official_status=score_kwargs["official_status"],
            championship_exception=score_kwargs["championship_exception"],
            category_override=category_override,
            category=None,
            category_name=None,
            category_base=None,
            class_coefficient=None,
            open_coefficient=None,
            place_factor=None,
            placement_points=None,
            time_coeff=None,
            ssa_rating=None,
            points=0.0,
            eligible=False,
            reason=None,
            counts_toward_rank=False,
            selected_for_regatta=preset_exclusion is None,
            selected_result_id=getattr(r, "selected_result_id", None),
            exclusion_reason=preset_exclusion,
        )
        for k, v in extra.items():
            setattr(ns, k, v)
        return ns

    if kind == "unknown":
        err = {
            "code": "unknown_event_type",
            "result_id": getattr(r, "result_id", None),
            "regatta_id": getattr(r, "regatta_id", None),
            "event": getattr(r, "event_name", None),
            "sailor": getattr(r, "sailor_name", None),
            "event_scope": sas_event.get("event_scope"),
            "event_rating_type": sas_event.get("event_rating_type"),
            "event_rating_level": sas_event.get("event_rating_level"),
        }
        return (
            _base_contrib(
                reason="unknown_or_conflicting_sas_event_type",
                exclusion_reason=preset_exclusion or "unknown_or_conflicting_sas_event_type",
            ),
            err,
            sas_event,
        )
    if place is None:
        err = {
            "code": "missing_place",
            "result_id": getattr(r, "result_id", None),
            "event": getattr(r, "event_name", None),
            "sailor": getattr(r, "sailor_name", None),
        }
        return (
            _base_contrib(
                reason="missing_place",
                exclusion_reason=preset_exclusion or "missing_place",
            ),
            err,
            sas_event,
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
        err = {
            "code": "score_exception",
            "result_id": getattr(r, "result_id", None),
            "event": getattr(r, "event_name", None),
            "sailor": getattr(r, "sailor_name", None),
            "detail": str(exc),
        }
        return (
            _base_contrib(reason=str(exc), exclusion_reason=preset_exclusion or "score_exception"),
            err,
            sas_event,
        )

    exclusion = preset_exclusion
    counts = bool(scored.eligible and scored.points > 0 and exclusion is None)
    if exclusion is None and not counts:
        exclusion = scored.reason or "ineligible_or_zero"
    contrib = _base_contrib(
        category=scored.category,
        category_name=scored.category_name,
        category_base=getattr(scored, "category_base", None),
        class_coefficient=getattr(scored, "class_coefficient", None),
        open_coefficient=getattr(scored, "open_coefficient", None),
        place_factor=getattr(scored, "place_factor", None),
        placement_points=getattr(scored, "placement_points", None),
        time_coeff=float(scored.age_factor or 0),
        ssa_rating=getattr(scored, "ssa_rating", None),
        points=float(scored.points or 0),
        eligible=bool(scored.eligible),
        reason=scored.reason,
        counts_toward_rank=counts,
        exclusion_reason=exclusion,
        selected_for_regatta=exclusion is None,
    )
    return contrib, None, sas_event


def _is_tim_420_nationals(row: Any) -> bool:
    sas = str(_row_attr(row, "sas_id") or "").strip()
    event = (_row_attr(row, "event_name") or "").lower()
    return sas == TIM_SAS_ID and "420 national" in event


def timothy_420_nationals_regression(kept_rows: list, exclusions: list[dict]) -> dict:
    """P5/N12 (result 837) counted once; both P1/N3 division rows excluded."""
    counted_ids = sorted(
        {
            int(_row_attr(r, "result_id"))
            for r in kept_rows
            if _is_tim_420_nationals(r) and _row_attr(r, "result_id") is not None
        }
    )
    excluded_ids = sorted(
        {
            int(x["result_id"])
            for x in exclusions
            if str(x.get("sas_id") or "").strip() == TIM_SAS_ID
            and "420 national" in (x.get("event_name") or "").lower()
            and x.get("result_id") is not None
        }
    )
    ok = counted_ids == [TIM_420_OVERALL_RESULT_ID] and set(excluded_ids) == set(TIM_420_DIVISION_RESULT_IDS)
    return {
        "sailor": "Timothy Weaving",
        "sas_id": TIM_SAS_ID,
        "event": "2025-10-04 420 National Champ",
        "expect_counted_result_ids": [TIM_420_OVERALL_RESULT_ID],
        "expect_excluded_result_ids": sorted(TIM_420_DIVISION_RESULT_IDS),
        "counted_result_ids": counted_ids,
        "excluded_result_ids": excluded_ids,
        "counted_place_fleet": "P5/N12" if TIM_420_OVERALL_RESULT_ID in counted_ids else None,
        "ok": ok,
    }


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
    age_div_cls = _load_live_age_division_cls(eng)
    window_start = as_of - timedelta(weeks=WINDOW_WEEKS)
    raw_rows = eng.fetch_result_rows(conn, history_start=window_start)
    score_rows, age_div_exclusions, age_div_groups, excluded_rows = (
        filter_age_division_rows_before_scoring(raw_rows, age_div_cls)
    )
    tim_420_regression = timothy_420_nationals_regression(score_rows, age_div_exclusions)

    errors: list[dict] = []
    n1_exclusions = 0
    cat_classified: dict[str, int] = defaultdict(int)
    unknown_type_keys: dict[str, int] = defaultdict(int)
    contribs: list[Any] = []

    scored_pairs: list[tuple[Any, Optional[str]]] = [(r, None) for r in score_rows]
    scored_pairs.extend((r, getattr(r, "exclusion_reason", None) or AGE_DIVISION_EXCLUSION_REASON) for r in excluded_rows)
    for r, preset_excl in scored_pairs:
        fleet = int(getattr(r, "fleet_size", 0) or 0)
        if fleet == 1 and preset_excl is None:
            n1_exclusions += 1
        contrib, err, sas_event = _score_row_to_contrib(
            r, as_of=as_of, pr13_score_result=pr13_score_result, preset_exclusion=preset_excl
        )
        if sas_event["kind"] == "unknown":
            key = "%s|%s|%s" % (
                sas_event.get("event_scope"),
                sas_event.get("event_rating_type"),
                sas_event.get("event_rating_level"),
            )
            unknown_type_keys[key] += 1
            if preset_excl is None:
                cat_classified["unknown"] += 1
        elif contrib.place is None:
            if preset_excl is None:
                cat_classified["none"] += 1
        elif preset_excl is None:
            cat_classified[str(contrib.category if contrib.category is not None else "none")] += 1
        if err is not None:
            errors.append(err)
        contribs.append(contrib)

    # Same identity + same result: one role-neutral row (keep higher points).
    best: dict[tuple, Any] = {}
    role_losers: list[Any] = []
    for c in contribs:
        key = (c.identity_key, c.result_id)
        prev = best.get(key)
        if prev is None:
            best[key] = c
            continue
        if float(c.points) > float(prev.points):
            prev.counts_toward_rank = False
            if not prev.exclusion_reason:
                prev.exclusion_reason = ROLE_COLLAPSE_EXCLUSION_REASON
            role_losers.append(prev)
            best[key] = c
        else:
            c.counts_toward_rank = False
            if not c.exclusion_reason:
                c.exclusion_reason = ROLE_COLLAPSE_EXCLUSION_REASON
            role_losers.append(c)
    contribs = list(best.values()) + role_losers

    dedup_groups: list[dict] = []
    if hasattr(eng, "dedupe_same_regatta_contributions"):
        contribs, dedup_groups = eng.dedupe_same_regatta_contributions(contribs)
        for c in contribs:
            if getattr(c, "selected_for_regatta", True) is False:
                c.counts_toward_rank = False
                if not c.exclusion_reason:
                    c.exclusion_reason = getattr(c, "exclusion_reason", None) or LIVE_DEDUP_EXCLUSION_REASON

    scored_by_result: dict[int, Any] = {}
    for c in contribs:
        rid = getattr(c, "result_id", None)
        if rid is not None:
            scored_by_result[int(rid)] = c
    for row in age_div_exclusions:
        rid = row.get("result_id")
        scored = scored_by_result.get(int(rid)) if rid is not None else None
        if scored is None:
            continue
        row["points"] = float(scored.points or 0)
        row["category"] = scored.category
        row["category_name"] = scored.category_name
        row["category_base"] = scored.category_base
        row["class_coefficient"] = scored.class_coefficient
        row["open_coefficient"] = scored.open_coefficient
        row["place_factor"] = scored.place_factor
        row["placement_points"] = scored.placement_points
        row["time_coeff"] = scored.time_coeff
        row["eligible"] = scored.eligible
        row["score_reason"] = scored.reason
        row["role"] = scored.role
        row["event_date"] = _iso_date(scored.event_date)
        row["exclusion_reason"] = scored.exclusion_reason or AGE_DIVISION_EXCLUSION_REASON

    by_id: dict[str, list[Any]] = defaultdict(list)
    for c in contribs:
        by_id[c.identity_key].append(c)

    sailors: list[dict] = []
    cat_counting: dict[str, int] = defaultdict(int)
    for ident, items in by_id.items():
        records = [_full_contrib_dict(c) for c in items]
        eligible_payload = [
            rec
            for rec in records
            if rec.get("counts_toward_rank") and float(rec.get("points") or 0) > 0 and not rec.get("exclusion_reason")
        ]
        counted, total = _select_best6_plus_local_cat8(eligible_payload)
        counted_keys = {_contrib_key(rec) for rec in counted}
        for rec in records:
            if _contrib_key(rec) in counted_keys:
                rec["counts_toward_rank"] = True
                rec["exclusion_reason"] = None
                continue
            rec["counts_toward_rank"] = False
            if not rec.get("exclusion_reason"):
                if rec.get("eligible") and float(rec.get("points") or 0) > 0:
                    rec["exclusion_reason"] = BEST6_EXCLUSION_REASON
                else:
                    rec["exclusion_reason"] = rec.get("reason") or "ineligible_or_zero"
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
                "contribs_excluded": [rec for rec in records if _contrib_key(rec) not in counted_keys],
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

    share_summaries = _cat78_and_concentration(sailors)

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
                "cat7_points": s.get("cat7_points"),
                "cat8_points": s.get("cat8_points"),
                "cat7_8_share": s.get("cat7_8_share"),
                "max_event_share": s.get("max_event_share"),
                "max_event": s.get("max_event"),
                "contribs_counted": s.get("contribs_counted") or [],
                "contribs_excluded": s.get("contribs_excluded") or [],
                "duplicate_division_exclusions": [
                    x
                    for x in age_div_exclusions
                    if str(x.get("sas_id") or "") == str(s.get("sas_id") or "")
                    or (
                        (x.get("sailor_name") or "").lower()
                        == (s.get("sailor_name") or "").lower()
                    )
                ],
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
        "age_division_kept_rows": len(score_rows),
        "age_division_excluded_count": len(age_div_exclusions),
        "age_division_groups_collapsed": len(age_div_groups),
        "age_division_exclusion_types": dict(
            sorted(Counter(str(x.get("championship_type")) for x in age_div_exclusions).items())
        ),
        "timothy_2025_420_nationals": tim_420_regression,
        "duplicate_division_exclusions": age_div_exclusions,
        "cat7_8_share": share_summaries["cat7_8_share"],
        "one_event_concentration": share_summaries["one_event_concentration"],
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
            "Live age-division filter (Overall/Open kept, U17/U19/Youth excluded, "
            "never summed) then PR13 score_result(mode=ssa) from SAS rank/class/"
            "fleet/date plus authoritative SAS event type/scope/level; WoS unused"
        ),
        "age_division_groups": age_div_groups,
    }

    cur.execute("SELECT COUNT(*) FROM results")
    results_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM regattas")
    regattas_after = cur.fetchone()[0]
    if results_after != results_before or regattas_after != regattas_before:
        raise RuntimeError("Safety check failed: results/regattas counts changed")
    conn.rollback()

    (out_dir / "audit.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    (out_dir / "age_division_exclusions.json").write_text(
        json.dumps(
            {
                "count": len(age_div_exclusions),
                "groups_collapsed": len(age_div_groups),
                "timothy_2025_420_nationals": tim_420_regression,
                "exclusions": age_div_exclusions,
                "groups": age_div_groups,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
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
                    "cat7_points": s.get("cat7_points"),
                    "cat8_points": s.get("cat8_points"),
                    "cat7_8_share": s.get("cat7_8_share"),
                    "max_event_share": s.get("max_event_share"),
                    "max_event": s.get("max_event"),
                    "contribs_counted": s.get("contribs_counted") or [],
                    "contribs_excluded": s.get("contribs_excluded") or [],
                }
                for s in sailors
            ],
            indent=2,
            default=str,
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
            print(
                json.dumps(
                    {
                        "ok": True,
                        "mode": SSA_V2_MODE,
                        "out_dir": str(out_dir),
                        "proposed_sailor_count": audit.get("proposed_sailor_count"),
                        "age_division_excluded_count": audit.get("age_division_excluded_count"),
                        "age_division_exclusion_types": audit.get("age_division_exclusion_types"),
                        "timothy_2025_420_nationals": audit.get("timothy_2025_420_nationals"),
                        "duplicate_division_exclusion_count": len(audit.get("duplicate_division_exclusions") or []),
                        "duplicate_division_exclusions": audit.get("duplicate_division_exclusions") or [],
                        "cat7_8_share": audit.get("cat7_8_share"),
                        "one_event_concentration": {
                            k: v
                            for k, v in (audit.get("one_event_concentration") or {}).items()
                            if k != "top_concentrated"
                        },
                        "validation": [
                            {
                                "sailor": v.get("sailor"),
                                "found": v.get("found"),
                                "sas_id": v.get("sas_id"),
                                "proposed_rank": v.get("proposed_rank"),
                                "proposed_points": v.get("proposed_points"),
                                "published_rank": v.get("published_rank"),
                                "published_points": v.get("published_points"),
                                "events_counted": v.get("events_counted"),
                                "counted_result_ids": [c.get("result_id") for c in (v.get("contribs_counted") or [])],
                                "excluded_result_ids": [c.get("result_id") for c in (v.get("contribs_excluded") or [])],
                            }
                            for v in (audit.get("validation") or [])
                        ],
                    },
                    indent=2,
                    default=str,
                )
            )
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
