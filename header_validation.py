"""
Header Validation Layer — hard rules for regatta display headers.

header_status (2-stage, mandatory):
  DRAFT   — incomplete; no import validation (ingestion creates start here).
  READY   — user confirmed; import runs validation; must pass to proceed.
  INVALID — failed validation; fix required, then set READY again.

No silent auto-correction: failures set INVALID + audit queue (READY path only).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# Event name must not contain SAS / association branding (expand as needed).
_FORBIDDEN_NAME_RE = [
    re.compile(r"\bSAS\b", re.IGNORECASE),
    re.compile(r"South African Sailing", re.IGNORECASE),
    re.compile(r"\bSA\s+Sailing\b", re.IGNORECASE),
]

# Display status words allowed in DB / results line
_ALLOWED_STATUS = frozenset({"Provisional", "Final"})

# Regattas with at least one row in public.results (RESULT_REGATTAS; table name is "results" in this DB).
RESULT_REGATTA_IDS_SUBQUERY = "SELECT DISTINCT regatta_id FROM public.results"
SQL_WHERE_REGATTA_HAS_RESULTS = f"regatta_id IN ({RESULT_REGATTA_IDS_SUBQUERY})"
SQL_WHERE_R_HAS_RESULTS = f"r.regatta_id IN ({RESULT_REGATTA_IDS_SUBQUERY})"

HEADER_BATCH_AUDIT_MODE_RESULTS_ONLY = "results_only"


def normalise_result_status(raw: Optional[str]) -> Optional[str]:
    """
    Map common variants to canonical 'Provisional' or 'Final'. Case-insensitive; strips whitespace.
    Returns None if empty or not in the allowed mapping (caller leaves DB value unchanged).
    Maps only: p/f, provisional/preliminary, final/final results/official.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    low = s.lower()
    if low in ("p", "provisional", "preliminary"):
        return "Provisional"
    if low in ("f", "final", "final results", "official"):
        return "Final"
    if s in _ALLOWED_STATUS:
        return s
    return None


def normalise_regatta_date_range(start_date: Any, end_date: Any) -> Tuple[Optional[date], Optional[date], bool]:
    """
    If start > end, swap. If end is NULL and start is set, end = start.
    If both NULL, returns (None, None, False). Returns (sd, ed, changed).
    """
    sd = _as_date(start_date)
    ed = _as_date(end_date)
    changed = False
    if sd is None and ed is None:
        return None, None, False
    if sd is not None and ed is not None and sd > ed:
        sd, ed = ed, sd
        changed = True
    if ed is None and sd is not None:
        ed = sd
        changed = True
    return sd, ed, changed


def as_at_time_from_end_date(end_d: date) -> datetime:
    """Default snapshot time when as_at is missing: noon UTC on end_date (regattas.end_date)."""
    return datetime.combine(end_d, time(12, 0, 0), tzinfo=timezone.utc)


# Optional column regattas.results_snapshot: comma-separated race numbers only (after normalisation).
_RESULTS_SNAPSHOT_OK_RE = re.compile(r"^\d+(,\d+)*$")


def normalise_results_snapshot(raw_text: Optional[str]) -> str:
    """
    Safe formatting only: whitespace → comma, keep digits and commas, collapse commas, strip ends.
    Does not infer missing races or drop numbers (beyond stripping non-digit/non-comma noise).
    """
    if raw_text is None:
        return ""
    s = str(raw_text).strip()
    if not s:
        return ""
    s = re.sub(r"\s+", ",", s)
    s = "".join(c for c in s if c.isdigit() or c == ",")
    s = re.sub(r",+", ",", s)
    return s.strip(",")


def is_valid_normalised_results_snapshot(s: str) -> bool:
    return bool(s and _RESULTS_SNAPSHOT_OK_RE.fullmatch(s) is not None)


def validate_regatta_snapshot_race_list(raw: Optional[str]) -> Optional[HeaderIssue]:
    """
    When results_snapshot is set, stored value must match ^\\d+(,\\d+)*$ (or be fixable to that via normalise_results_snapshot).
    Empty / NULL = not using this field — no issue.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None
    if _RESULTS_SNAPSHOT_OK_RE.fullmatch(s):
        return None
    norm = normalise_results_snapshot(s)
    if is_valid_normalised_results_snapshot(norm):
        return HeaderIssue(
            field="results_snapshot",
            current_value=s[:2000],
            expected_rule="results_snapshot must be stored as comma-separated digits only, e.g. 1,2,3,4 (apply normalisation)",
            error_type="RESULTS_SNAPSHOT_FORMAT_INVALID",
        )
    return HeaderIssue(
        field="results_snapshot",
        current_value=s[:2000],
        expected_rule="results_snapshot cannot be normalised to comma-separated digits (pattern ^\\d+(,\\d+)*$)",
        error_type="RESULTS_SNAPSHOT_FORMAT_INVALID",
    )


def log_results_snapshot_parse_issue(regatta_id: str, raw: str, reason: str) -> None:
    """Append one line to logs/results_snapshot_parse_issues.log (parse failures / skipped updates)."""
    try:
        _root = os.path.dirname(os.path.abspath(__file__))
        _dir = os.path.join(_root, "logs")
        os.makedirs(_dir, exist_ok=True)
        _path = os.path.join(_dir, "results_snapshot_parse_issues.log")
        ts = datetime.now(timezone.utc).isoformat()
        with open(_path, "a", encoding="utf-8") as f:
            f.write(f"{ts}\t{regatta_id}\t{reason}\t{raw!r}\n")
    except Exception as e:
        print(f"[results_snapshot_parse_issues] log failed: {e}")

# Regatta header lifecycle (see module docstring)
HEADER_DRAFT = "DRAFT"
HEADER_READY = "READY"
HEADER_INVALID = "INVALID"


@dataclass
class HeaderIssue:
    field: str
    current_value: str
    expected_rule: str
    error_type: str


def header_issues_to_payload(issues: List[HeaderIssue]) -> List[dict]:
    return [
        {
            "field": i.field,
            "current_value": i.current_value,
            "expected_rule": i.expected_rule,
            "error_type": i.error_type,
        }
        for i in issues
    ]


def _norm_ws(s: str) -> str:
    return " ".join((s or "").split())


def validate_event_name(event_name: Optional[str]) -> Optional[HeaderIssue]:
    """Regatta title: clean text; no SAS / association words."""
    raw = (event_name or "").strip()
    if not raw:
        return HeaderIssue(
            field="event_name",
            current_value="",
            expected_rule="Non-empty event name; no leading year/regatta number; no SAS/South African Sailing wording",
            error_type="EMPTY_EVENT_NAME",
        )
    for rx in _FORBIDDEN_NAME_RE:
        if rx.search(raw):
            return HeaderIssue(
                field="event_name",
                current_value=raw,
                expected_rule="Event name must not contain SAS / South African Sailing / SA Sailing wording",
                error_type="FORBIDDEN_WORD_IN_EVENT_NAME",
            )
    # Leading year like "2025 Foo" — data rule from docs
    if re.match(r"^\s*\d{4}\s+", raw):
        return HeaderIssue(
            field="event_name",
            current_value=raw,
            expected_rule="Event name must not start with a year (year lives in regattas.year)",
            error_type="LEADING_YEAR_IN_EVENT_NAME",
        )
    return None


def _expected_host_line(club_abbrev: Optional[str], club_fullname: Optional[str]) -> str:
    a = (club_abbrev or "").strip()
    n = (club_fullname or "").strip()
    if not a and not n:
        return ""
    if a and n:
        return f"{a.upper()} - {n}"
    return a.upper() if a else n


def ensure_host_club_map_schema(cur: Any) -> None:
    """Known-safe raw host string → canonical club name. No fuzzy matching; lookup is exact CI on raw_name."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.host_club_map (
            raw_name TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        INSERT INTO public.host_club_map (raw_name, canonical_name) VALUES
        ('HYC', 'Hermanus Yacht Club'),
        ('Hermanus YC', 'Hermanus Yacht Club'),
        ('Hermanus Yacht Club', 'Hermanus Yacht Club'),
        ('MAC', 'Milnerton Aquatic Club'),
        ('Milnerton Aquatic Club', 'Milnerton Aquatic Club')
        ON CONFLICT (raw_name) DO NOTHING;
        """
    )


def normalise_host(cur: Any, raw: Optional[str]) -> str:
    """
    Trim; case-insensitive exact match on host_club_map.raw_name only.
    Returns canonical_name if found, else raw unchanged (stripped).
    """
    s = (raw or "").strip()
    if not s:
        return ""
    cur.execute(
        """
        SELECT canonical_name
        FROM public.host_club_map
        WHERE lower(btrim(raw_name)) = lower(btrim(%s))
        LIMIT 1
        """,
        (s,),
    )
    row = cur.fetchone()
    if not row:
        return s
    if isinstance(row, (list, tuple)):
        c = row[0]
    else:
        c = row.get("canonical_name")
    return (c or "").strip() if c is not None else s


def is_host_display_allowed(cur: Any, normalised: str) -> bool:
    """
    True if normalised string matches a seeded canonical name or an exact club row
    (club_fullname or club_abbrev), case-insensitive. No partial/fuzzy match.
    """
    n = (normalised or "").strip()
    if not n:
        return True
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM public.host_club_map m
            WHERE lower(trim(m.canonical_name)) = lower(trim(%s))
            UNION ALL
            SELECT 1
            FROM public.clubs c
            WHERE lower(trim(c.club_fullname)) = lower(trim(%s))
            UNION ALL
            SELECT 1
            FROM public.clubs c
            WHERE lower(trim(c.club_abbrev)) = lower(trim(%s))
        )
        """,
        (n, n, n),
    )
    row = cur.fetchone()
    if not row:
        return False
    if isinstance(row, (list, tuple)):
        return bool(row[0])
    return bool(row.get("exists"))


def validate_host_club_name_field(
    cur: Any,
    regatta_type: Optional[str],
    host_club_name: Optional[str],
) -> Optional[HeaderIssue]:
    """
    Optional regattas.host_club_name must be empty or, after normalise_host, allowed
    (canonical map target or exact club name/abbrev). SERIES: same as host_club_id — not checked.
    """
    rt = (regatta_type or "").strip().upper()
    if rt == "SERIES":
        return None
    raw = (host_club_name or "").strip()
    if not raw:
        return None
    n = normalise_host(cur, raw)
    if is_host_display_allowed(cur, n):
        return None
    return HeaderIssue(
        field="host",
        current_value=raw[:2000],
        expected_rule="host_club_name must match host_club_map or a club club_fullname / club_abbrev (exact, case-insensitive)",
        error_type="HOST_CLUB_NAME_INVALID",
    )


def validate_host_for_regatta(
    regatta_type: Optional[str],
    host_club_id: Optional[int],
    cur: Any,
) -> Optional[HeaderIssue]:
    """
    Host display must be CODE - Full Name matching clubs row for host_club_id.
    Series regattas (multi-host) are not validated against a single CODE - Full Name line.
    """
    rt = (regatta_type or "").strip().upper()
    if rt == "SERIES":
        return None
    if not host_club_id:
        return HeaderIssue(
            field="host",
            current_value="",
            expected_rule="host_club_id must reference clubs; display host = CODE - Full Name from that row",
            error_type="MISSING_HOST_CLUB_ID",
        )
    cur.execute(
        """
        SELECT TRIM(COALESCE(club_abbrev, '')) AS abbr,
               TRIM(COALESCE(club_fullname, '')) AS fullname
        FROM public.clubs
        WHERE club_id = %s
        """,
        (host_club_id,),
    )
    row = cur.fetchone()
    if not row:
        return HeaderIssue(
            field="host",
            current_value=str(host_club_id),
            expected_rule="host_club_id must exist in public.clubs",
            error_type="HOST_CLUB_NOT_FOUND",
        )
    if isinstance(row, (list, tuple)):
        abbr = (row[0] or "").strip() if len(row) > 0 else ""
        fullname = (row[1] or "").strip() if len(row) > 1 else ""
    else:
        abbr = (row.get("abbr") or "").strip()
        fullname = (row.get("fullname") or "").strip()
    expected = _expected_host_line(abbr, fullname)
    if not expected or " - " not in expected:
        return HeaderIssue(
            field="host",
            current_value=f"id={host_club_id}",
            expected_rule="Club must have club_abbrev and club_fullname for CODE - Full Name display",
            error_type="INCOMPLETE_CLUB_ROW",
        )
    return None


def _as_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v.strip():
        s = v.strip()[:10]
        try:
            y, m, d = s.split("-")
            return date(int(y), int(m), int(d))
        except Exception:
            return None
    return None


def validate_results_snapshot(
    result_status: Optional[str],
    as_at_time: Any,
    start_date: Any,
    end_date: Any,
) -> Optional[HeaderIssue]:
    """
    Results line source: result_status + as_at_time.
    - Status must be Provisional or Final (full words).
    - as_at_time required for a valid snapshot.
    - Snapshot calendar date must fall on an event day (start_date..end_date inclusive) when those dates exist.
    """
    st = (result_status or "").strip()
    canon = normalise_result_status(result_status)
    if canon is not None:
        st = canon
    elif st.lower() in ("p",):
        st = "Provisional"
    elif st.lower() in ("f",):
        st = "Final"
    if not st or st not in _ALLOWED_STATUS:
        return HeaderIssue(
            field="results_snapshot",
            current_value=result_status or "",
            expected_rule="result_status must be exactly 'Provisional' or 'Final'",
            error_type="INVALID_RESULT_STATUS",
        )
    if as_at_time is None:
        return HeaderIssue(
            field="results_snapshot",
            current_value="(null as_at_time)",
            expected_rule="as_at_time must be set (Results are … as at DD Month YYYY at HH:MM from DB timestamp)",
            error_type="MISSING_AS_AT_TIME",
        )
    # Parse timestamp to date
    ad: Optional[date] = None
    if hasattr(as_at_time, "date") and callable(as_at_time.date):
        try:
            ad = as_at_time.date()
        except Exception:
            ad = None
    if ad is None and isinstance(as_at_time, str):
        try:
            from datetime import datetime as _dt

            s = as_at_time.strip().replace("Z", "+00:00")
            if "T" in s:
                ad = _dt.fromisoformat(s[:19]).date()
            else:
                ad = _as_date(s)
        except Exception:
            ad = None
    if ad is None:
        return HeaderIssue(
            field="results_snapshot",
            current_value=str(as_at_time),
            expected_rule="as_at_time must be a valid timestamp (timezone-aware preferred)",
            error_type="INVALID_AS_AT_TIME",
        )

    sd = _as_date(start_date)
    ed = _as_date(end_date)
    if sd is not None and ed is not None:
        if ad < sd or ad > ed:
            return HeaderIssue(
                field="results_snapshot",
                current_value=f"as_at date {ad.isoformat()}",
                expected_rule=f"Snapshot date must fall on event dates only ({sd.isoformat()} .. {ed.isoformat()})",
                error_type="AS_AT_OUTSIDE_EVENT_DATES",
            )
    elif sd is not None and ed is None:
        if ad != sd:
            return HeaderIssue(
                field="results_snapshot",
                current_value=f"as_at date {ad.isoformat()}",
                expected_rule=f"Snapshot date must match start_date ({sd.isoformat()}) when end_date is unset",
                error_type="AS_AT_NOT_ON_EVENT_DATE",
            )
    elif sd is None and ed is not None:
        if ad != ed:
            return HeaderIssue(
                field="results_snapshot",
                current_value=f"as_at date {ad.isoformat()}",
                expected_rule=f"Snapshot date must match end_date ({ed.isoformat()}) when start_date is unset",
                error_type="AS_AT_NOT_ON_EVENT_DATE",
            )

    return None


def list_required_field_gaps_for_mark_ready(row: dict, cur: Any) -> List[HeaderIssue]:
    """
    Structural fields that must be present before header_status may be set to READY.
    Does not include content rules (e.g. forbidden words) — those run in validate_regatta_by_id.
    """
    _ = cur  # reserved for future club-exists checks
    issues: List[HeaderIssue] = []
    en = (row.get("event_name") or "").strip()
    if not en:
        issues.append(
            HeaderIssue(
                field="event_name",
                current_value="",
                expected_rule="event_name must be set",
                error_type="REQUIRED_FIELD_MISSING",
            )
        )
    rt = (row.get("regatta_type") or "").strip().upper()
    if rt != "SERIES" and not row.get("host_club_id"):
        issues.append(
            HeaderIssue(
                field="host",
                current_value="",
                expected_rule="host_club_id is required unless regatta_type is SERIES",
                error_type="REQUIRED_FIELD_MISSING",
            )
        )
    rs = (row.get("result_status") or "").strip()
    canon_rs = normalise_result_status(row.get("result_status"))
    if canon_rs is not None:
        rs = canon_rs
    elif rs.lower() in ("p",):
        rs = "Provisional"
    elif rs.lower() in ("f",):
        rs = "Final"
    if not rs or rs not in _ALLOWED_STATUS:
        issues.append(
            HeaderIssue(
                field="results_snapshot",
                current_value=(row.get("result_status") or "") or "",
                expected_rule="result_status must be Provisional or Final",
                error_type="REQUIRED_FIELD_MISSING",
            )
        )
    if row.get("as_at_time") is None:
        issues.append(
            HeaderIssue(
                field="results_snapshot",
                current_value="(null as_at_time)",
                expected_rule="as_at_time must be set",
                error_type="REQUIRED_FIELD_MISSING",
            )
        )
    return issues


def collect_header_issues(
    *,
    event_name: Optional[str],
    regatta_type: Optional[str],
    host_club_id: Optional[int],
    host_club_name: Optional[str] = None,
    result_status: Optional[str],
    as_at_time: Any,
    start_date: Any,
    end_date: Any,
    cur: Any,
    results_snapshot_text: Optional[str] = None,
) -> List[HeaderIssue]:
    issues: List[HeaderIssue] = []
    ev = validate_event_name(event_name)
    if ev:
        issues.append(ev)
    hv = validate_host_for_regatta(regatta_type, host_club_id, cur)
    if hv:
        issues.append(hv)
    hnv = validate_host_club_name_field(cur, regatta_type, host_club_name)
    if hnv:
        issues.append(hnv)
    rv = validate_results_snapshot(result_status, as_at_time, start_date, end_date)
    if rv:
        issues.append(rv)
    sv = validate_regatta_snapshot_race_list(results_snapshot_text)
    if sv:
        issues.append(sv)
    return issues


def ensure_result_status_map_schema(cur: Any) -> None:
    """
    Manual curation: exact raw regattas.result_status -> Provisional | Final only.
    Applied by scripts/apply_result_status_map.py (RESULT_REGATTAS only). No fuzzy matching.
    """
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.result_status_map (
            raw_status TEXT PRIMARY KEY,
            canonical_status TEXT NOT NULL,
            CONSTRAINT result_status_map_canonical_ok
                CHECK (canonical_status IN ('Provisional', 'Final'))
        );
        """
    )


def ensure_header_audit_schema(cur: Any) -> None:
    """Create admin_audit_queue, header_status, legacy header_validation_status, host_club_map, result_status_map if missing."""
    ensure_host_club_map_schema(cur)
    ensure_result_status_map_schema(cur)
    cur.execute(
        """
        ALTER TABLE public.regattas
        ADD COLUMN IF NOT EXISTS header_validation_status TEXT;
        """
    )
    cur.execute(
        """
        ALTER TABLE public.regattas
        ADD COLUMN IF NOT EXISTS header_status TEXT DEFAULT 'READY';
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.admin_audit_queue (
            id SERIAL PRIMARY KEY,
            regatta_id TEXT NOT NULL REFERENCES public.regattas(regatta_id) ON DELETE CASCADE,
            field_name TEXT NOT NULL,
            current_value TEXT,
            expected_rule TEXT NOT NULL,
            error_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_queue_regatta
        ON public.admin_audit_queue(regatta_id);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_queue_open
        ON public.admin_audit_queue(status) WHERE status = 'OPEN';
        """
    )
    cur.execute(
        """
        CREATE OR REPLACE VIEW public.admin_header_audit_view AS
        SELECT
            q.id,
            q.regatta_id,
            q.field_name AS field,
            q.current_value,
            q.expected_rule,
            q.error_type,
            q.status,
            q.created_at,
            r.event_name AS regatta_event_name,
            r.header_validation_status,
            r.header_status
        FROM public.admin_audit_queue q
        LEFT JOIN public.regattas r ON r.regatta_id = q.regatta_id
        WHERE q.status = 'OPEN'
          AND COALESCE(r.header_status, 'READY') IN ('READY', 'INVALID')
        ORDER BY q.created_at DESC;
        """
    )


def persist_validation_outcome(cur: Any, regatta_id: str, issues: List[HeaderIssue]) -> None:
    """Set regattas.header_status (+ legacy header_validation_status); replace OPEN queue rows for this regatta."""
    ensure_header_audit_schema(cur)
    if not issues:
        cur.execute(
            """
            UPDATE public.regattas
            SET header_validation_status = 'OK',
                header_status = %s
            WHERE regatta_id = %s
            """,
            (HEADER_READY, regatta_id),
        )
        cur.execute(
            """
            DELETE FROM public.admin_audit_queue
            WHERE regatta_id = %s AND status = 'OPEN'
            """,
            (regatta_id,),
        )
        return
    cur.execute(
        """
        UPDATE public.regattas
        SET header_validation_status = 'INVALID_HEADER',
            header_status = %s
        WHERE regatta_id = %s
        """,
        (HEADER_INVALID, regatta_id),
    )
    cur.execute(
        """
        DELETE FROM public.admin_audit_queue
        WHERE regatta_id = %s AND status = 'OPEN'
        """,
        (regatta_id,),
    )
    for iss in issues:
        cur.execute(
            """
            INSERT INTO public.admin_audit_queue
            (regatta_id, field_name, current_value, expected_rule, error_type, status)
            VALUES (%s, %s, %s, %s, %s, 'OPEN')
            """,
            (
                regatta_id,
                iss.field,
                (iss.current_value or "")[:2000],
                iss.expected_rule[:2000],
                iss.error_type,
            ),
        )


def load_regatta_header_row(cur: Any, regatta_id: str) -> Optional[dict]:
    cur.execute(
        """
        SELECT regatta_id, event_name, regatta_type, host_club_id,
               TRIM(COALESCE(host_club_name, '')) AS host_club_name,
               start_date, end_date,
               NULLIF(TRIM(result_status), '') AS result_status,
               as_at_time,
               NULLIF(TRIM(header_status), '') AS header_status,
               NULLIF(TRIM(COALESCE(results_snapshot, '')), '') AS results_snapshot
        FROM public.regattas
        WHERE regatta_id = %s
        """,
        (regatta_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _normalize_header_status(raw: Optional[str]) -> str:
    """NULL/legacy empty → READY (existing regattas stay importable)."""
    s = (raw or "").strip().upper()
    if not s:
        return HEADER_READY
    return s


def validate_regatta_by_id(
    cur: Any, regatta_id: str, *, ensure_schema: bool = True
) -> Tuple[bool, List[HeaderIssue]]:
    """Run all header checks for a regatta; does not persist. Set ensure_schema=False after a single ensure_header_audit_schema for batch QA."""
    if ensure_schema:
        ensure_header_audit_schema(cur)
    row = load_regatta_header_row(cur, regatta_id)
    if not row:
        return False, [
            HeaderIssue(
                field="regatta",
                current_value=regatta_id,
                expected_rule="regatta_id must exist",
                error_type="REGATTA_NOT_FOUND",
            )
        ]
    issues = collect_header_issues(
        event_name=row.get("event_name"),
        regatta_type=row.get("regatta_type"),
        host_club_id=row.get("host_club_id"),
        host_club_name=row.get("host_club_name"),
        result_status=row.get("result_status"),
        as_at_time=row.get("as_at_time"),
        start_date=row.get("start_date"),
        end_date=row.get("end_date"),
        cur=cur,
        results_snapshot_text=row.get("results_snapshot"),
    )
    return (len(issues) == 0), issues


def revalidate_and_persist(conn: Any, regatta_id: str) -> Tuple[bool, List[HeaderIssue]]:
    """Validate and write status + queue (call inside transaction). Persists header_status / audit queue only — never mutates event_name, host, or snapshot fields."""
    from regatta_host_code import persist_regatta_host_club_code_from_clubs_cur

    with conn.cursor() as cur:
        ok, issues = validate_regatta_by_id(cur, regatta_id, ensure_schema=True)
        persist_validation_outcome(cur, regatta_id, issues)
        persist_regatta_host_club_code_from_clubs_cur(cur, regatta_id)
    return ok, issues


# Admin batch summary buckets (map HeaderIssue.error_type / field → category)
AUDIT_CATEGORY_REGATTA_NAME = "REGATTA_NAME_INVALID"
AUDIT_CATEGORY_HOST = "HOST_FORMAT_INVALID"
AUDIT_CATEGORY_RESULTS_LINE = "RESULTS_LINE_INVALID"
AUDIT_CATEGORY_REQUIRED = "REQUIRED_FIELD_MISSING"
AUDIT_CATEGORY_OTHER = "OTHER"


HEADER_AUDIT_DRILLDOWN_CATEGORIES = frozenset(
    {
        AUDIT_CATEGORY_REGATTA_NAME,
        AUDIT_CATEGORY_HOST,
        AUDIT_CATEGORY_RESULTS_LINE,
        AUDIT_CATEGORY_REQUIRED,
        AUDIT_CATEGORY_OTHER,
    }
)


def audit_category_for_issue(issue: HeaderIssue) -> str:
    """Group validation issues for admin batch reports."""
    et = (issue.error_type or "").strip()
    if et == "REQUIRED_FIELD_MISSING":
        return AUDIT_CATEGORY_REQUIRED
    if et == "EMPTY_EVENT_NAME":
        return AUDIT_CATEGORY_REQUIRED
    fld = (issue.field or "").strip()
    if fld == "event_name":
        return AUDIT_CATEGORY_REGATTA_NAME
    if fld == "host":
        return AUDIT_CATEGORY_HOST
    if fld == "results_snapshot":
        return AUDIT_CATEGORY_RESULTS_LINE
    if fld == "regatta":
        return AUDIT_CATEGORY_REQUIRED
    return AUDIT_CATEGORY_OTHER


def run_header_batch_audit(conn: Any, mode: Optional[str] = None) -> Dict[str, Any]:
    """
    NON-DESTRUCTIVE QA: READY/INVALID regattas only (DRAFT skipped). Each row: validate_regatta_by_id only — no persist,
    no regatta field updates, no audit_queue writes, no cross-regatta deletes. Read-only checks in memory.

    mode:
      - None / "" : all READY/INVALID regattas (legacy).
      - "results_only" : only RESULT_REGATTAS (regatta_id in public.results), plus READY/INVALID.
    """
    m = (mode or "").strip().lower()
    results_only = m == HEADER_BATCH_AUDIT_MODE_RESULTS_ONLY
    extra = ""
    if results_only:
        extra = f" AND ({SQL_WHERE_REGATTA_HAS_RESULTS})"

    with conn.cursor() as cur:
        ensure_header_audit_schema(cur)
        cur.execute(
            f"""
            SELECT regatta_id, event_name, header_status
            FROM public.regattas
            WHERE header_status IN ('READY', 'INVALID')
            {extra}
            ORDER BY regatta_id
            """
        )
        rows = cur.fetchall() or []

    distinct_rr: Optional[int] = None
    if results_only:
        with conn.cursor() as cur2:
            cur2.execute(f"SELECT COUNT(*) FROM ({RESULT_REGATTA_IDS_SUBQUERY}) AS _rr")
            row = cur2.fetchone()
            if row:
                if isinstance(row, (list, tuple)):
                    distinct_rr = int(row[0])
                elif isinstance(row, dict):
                    distinct_rr = int(next(iter(row.values())))
                else:
                    distinct_rr = int(row)

    def _rid(row: Any) -> str:
        if isinstance(row, dict):
            return str(row.get("regatta_id") or "")
        return str(row[0] if row else "")

    buckets: Dict[str, Set[str]] = {
        AUDIT_CATEGORY_REGATTA_NAME: set(),
        AUDIT_CATEGORY_HOST: set(),
        AUDIT_CATEGORY_RESULTS_LINE: set(),
        AUDIT_CATEGORY_REQUIRED: set(),
        AUDIT_CATEGORY_OTHER: set(),
    }

    total_checked = len(rows)
    total_invalid = 0
    total_ready_ok = 0

    for row in rows:
        rid = _rid(row)
        if not rid:
            continue
        with conn.cursor() as cur:
            ok, issues = validate_regatta_by_id(cur, rid, ensure_schema=False)
        if ok:
            total_ready_ok += 1
        else:
            total_invalid += 1
            for iss in issues:
                cat = audit_category_for_issue(iss)
                if cat not in buckets:
                    cat = AUDIT_CATEGORY_OTHER
                buckets[cat].add(rid)

    def _serialise(ids: Set[str]) -> Dict[str, Any]:
        sorted_ids = sorted(ids)
        return {"count": len(sorted_ids), "regatta_ids": sorted_ids}

    breakdown: Dict[str, Any] = {
        AUDIT_CATEGORY_REGATTA_NAME: _serialise(buckets[AUDIT_CATEGORY_REGATTA_NAME]),
        AUDIT_CATEGORY_HOST: _serialise(buckets[AUDIT_CATEGORY_HOST]),
        AUDIT_CATEGORY_RESULTS_LINE: _serialise(buckets[AUDIT_CATEGORY_RESULTS_LINE]),
        AUDIT_CATEGORY_REQUIRED: _serialise(buckets[AUDIT_CATEGORY_REQUIRED]),
    }
    if buckets[AUDIT_CATEGORY_OTHER]:
        breakdown[AUDIT_CATEGORY_OTHER] = _serialise(buckets[AUDIT_CATEGORY_OTHER])

    out: Dict[str, Any] = {
        "mode": HEADER_BATCH_AUDIT_MODE_RESULTS_ONLY if results_only else "all_ready_invalid",
        "total_checked": total_checked,
        "total_invalid": total_invalid,
        "total_ready_ok": total_ready_ok,
        "breakdown": breakdown,
    }
    if results_only:
        out["TOTAL_RESULTS_REGATTAS"] = total_checked
        out["INVALID"] = total_invalid
        out["BREAKDOWN"] = breakdown
        if distinct_rr is not None:
            out["distinct_results_table_regatta_ids"] = distinct_rr
    return out


def get_header_audit_category_drilldown(
    conn: Any, category: str, mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read-only: regattas in READY/INVALID with at least one issue in the given category.
    Returns event_name, header_status, and issues for that category only (no DB writes).
    mode: pass HEADER_BATCH_AUDIT_MODE_RESULTS_ONLY to restrict to RESULT_REGATTAS (public.results).
    """
    cat = (category or "").strip()
    if cat not in HEADER_AUDIT_DRILLDOWN_CATEGORIES:
        return {
            "ok": False,
            "error": f"Invalid category; use one of: {', '.join(sorted(HEADER_AUDIT_DRILLDOWN_CATEGORIES))}",
            "rows": [],
        }

    m = (mode or "").strip().lower()
    results_only = m == HEADER_BATCH_AUDIT_MODE_RESULTS_ONLY
    extra = f" AND ({SQL_WHERE_REGATTA_HAS_RESULTS})" if results_only else ""

    with conn.cursor() as cur:
        ensure_header_audit_schema(cur)
        cur.execute(
            f"""
            SELECT regatta_id, event_name, header_status
            FROM public.regattas
            WHERE header_status IN ('READY', 'INVALID')
            {extra}
            ORDER BY regatta_id
            """
        )
        rows = cur.fetchall() or []

    out: List[Dict[str, Any]] = []

    for row in rows:
        rid = row["regatta_id"] if isinstance(row, dict) else row[0]
        rid = str(rid or "")
        if not rid:
            continue
        with conn.cursor() as cur:
            ok, issues = validate_regatta_by_id(cur, rid, ensure_schema=False)
        if ok:
            continue
        matched = [i for i in issues if audit_category_for_issue(i) == cat]
        if not matched:
            continue
        ev = row["event_name"] if isinstance(row, dict) else (row[1] if len(row) > 1 else "")
        hs = row["header_status"] if isinstance(row, dict) else (row[2] if len(row) > 2 else "")
        out.append(
            {
                "regatta_id": rid,
                "event_name": ev,
                "header_status": hs,
                "issues": header_issues_to_payload(matched),
            }
        )

    return {
        "ok": True,
        "category": cat,
        "mode": HEADER_BATCH_AUDIT_MODE_RESULTS_ONLY if results_only else "all_ready_invalid",
        "rows": out,
    }


class HeaderValidationError(Exception):
    """Raised when READY regatta fails header rules (status becomes INVALID)."""

    def __init__(self, regatta_id: str, issues: List[HeaderIssue]):
        self.regatta_id = regatta_id
        self.issues = issues
        msg = "; ".join(f"{i.field}:{i.error_type}" for i in issues)
        super().__init__(msg)


class HeaderImportBlockedError(Exception):
    """Import blocked before validation (e.g. DRAFT, INVALID until fixed and set to READY)."""

    def __init__(self, code: str, regatta_id: str, message: str):
        self.code = code
        self.regatta_id = regatta_id
        super().__init__(message)


def assert_regatta_header_allows_import(conn: Any, regatta_id: str) -> None:
    """
    Import path only:
    - Requires header_status == READY (legacy NULL/empty counts as READY).
    - Does not validate DRAFT regattas (incomplete workflow).
    - On READY: run validation; persist INVALID + queue on failure; commit before raising.

    Commits validation outcome before raising HeaderValidationError so import rollback does not undo status/queue.
    """
    with conn.cursor() as cur:
        ensure_header_audit_schema(cur)
        row = load_regatta_header_row(cur, regatta_id)
        if not row:
            raise HeaderValidationError(
                regatta_id,
                [
                    HeaderIssue(
                        field="regatta",
                        current_value=regatta_id,
                        expected_rule="regatta_id must exist",
                        error_type="REGATTA_NOT_FOUND",
                    )
                ],
            )
        hs = _normalize_header_status(row.get("header_status"))
        if hs == HEADER_DRAFT:
            raise HeaderImportBlockedError(
                HEADER_DRAFT,
                regatta_id,
                "header_status must be READY before import (currently DRAFT). Set READY when the header is complete.",
            )
        if hs == HEADER_INVALID:
            raise HeaderImportBlockedError(
                HEADER_INVALID,
                regatta_id,
                "header_status is INVALID; fix header fields in the database, set header_status to READY, then import again.",
            )
        if hs != HEADER_READY:
            raise HeaderImportBlockedError(
                hs,
                regatta_id,
                f"header_status must be READY before import (got {hs!r}).",
            )

    ok, issues = revalidate_and_persist(conn, regatta_id)
    conn.commit()
    if not ok:
        raise HeaderValidationError(regatta_id, issues)
