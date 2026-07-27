#!/usr/bin/env python3
from __future__ import annotations
"""
Shared helpers for manual parsed-results ingestion into `results`.
- Strict class resolution: exact match on classes.class_name (case-insensitive) or class_aliases.
- No fuzzy match, no auto-create classes, no guessing.
- Unknown classes → block insert, write to ingestion_issues, return error summary.
- Sailor resolution: use resolve_helm_to_sa_id(); if None → leave helm_sa_sailing_id NULL (review queue).
  Never create or assign a fake SAS ID.
"""
import json
import os
import re
import subprocess
from difflib import SequenceMatcher
from hashlib import md5, sha256
from pathlib import Path
from typing import Literal
import urllib.request
from urllib.parse import urlparse

import psycopg2

ROOT = Path(__file__).resolve().parent
RESULTS_PDF_ROOT = ROOT / "data" / "results_pdfs"
SAS_RESULTS_REFERER = "https://www.sailing.org.za/"
SAS_RESULTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SailingSA Results Ingestion/1.0)",
    "Referer": SAS_RESULTS_REFERER,
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
}


def normalize_class_label(raw_label: str) -> str:
    """TRIM, collapse whitespace, casefold for comparison. No fuzzy match."""
    if not raw_label or not isinstance(raw_label, str):
        return ""
    s = raw_label.strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s


def ensure_class_aliases_table(conn):
    """Create class_aliases if missing: alias -> class_id for variants (e.g. ILCA 4 -> Ilca 4.7)."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS class_aliases (
            id SERIAL PRIMARY KEY,
            alias TEXT NOT NULL,
            class_id INTEGER NOT NULL REFERENCES classes(class_id),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS class_aliases_normalised_key
        ON class_aliases (LOWER(TRIM(alias)))
    """)
    conn.commit()
    cur.close()


def ensure_ingestion_issues_table(conn):
    """Create ingestion_issues if missing: unknown class labels blocked from insert."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_issues (
            id SERIAL PRIMARY KEY,
            regatta_id TEXT NOT NULL,
            source_file TEXT,
            raw_class_label TEXT NOT NULL,
            sample_row_json JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            status TEXT NOT NULL DEFAULT 'OPEN'
        )
    """)
    conn.commit()
    cur.close()


def resolve_class_id(cur, raw_label: str):
    """
    Resolve raw class label to classes.class_id.
    - Normalise: TRIM, collapse whitespace, casefold.
    - Lookup classes.class_name (exact match on normalised).
    - If not found, lookup class_aliases (alias -> class_id).
    - Return class_id (int) or None. No fuzzy match, no auto-create.
    """
    norm = normalize_class_label(raw_label)
    if not norm:
        return None
    cur.execute(
        """
        SELECT class_id FROM classes
        WHERE LOWER(TRIM(class_name)) = %s
        LIMIT 1
        """,
        (norm,),
    )
    row = cur.fetchone()
    if row:
        return row["class_id"] if isinstance(row, dict) else row[0]
    cur.execute(
        """
        SELECT class_id FROM class_aliases
        WHERE LOWER(TRIM(alias)) = %s
        LIMIT 1
        """,
        (norm,),
    )
    row = cur.fetchone()
    if row:
        return row["class_id"] if isinstance(row, dict) else row[0]
    return None


def get_class_name_by_id(cur, class_id: int) -> str | None:
    """Return classes.class_name for class_id (for writing results.class_canonical)."""
    if class_id is None:
        return None
    cur.execute("SELECT class_name FROM classes WHERE class_id = %s LIMIT 1", (class_id,))
    row = cur.fetchone()
    if not row:
        return None
    return row["class_name"] if isinstance(row, dict) else row[0]


def record_ingestion_issue(cur, regatta_id: str, source_file: str | None, raw_class_label: str, sample_row_json: dict | None, status: str = "OPEN"):
    """Write one row to ingestion_issues. sample_row_json stored as JSONB."""
    cur.execute(
        """
        INSERT INTO ingestion_issues (regatta_id, source_file, raw_class_label, sample_row_json, status)
        VALUES (%s, %s, %s, %s::jsonb, %s)
        """,
        (regatta_id, source_file or "", raw_class_label, json.dumps(sample_row_json) if sample_row_json else None, status),
    )


def _is_race_class(cur, class_id: int) -> bool | None:
    """
    Return True if class is allowed in results (is_race_class = TRUE), False if family/aggregate-only.
    Return None if classes.is_race_class column does not exist (backward compat: allow).
    """
    try:
        cur.execute(
            "SELECT is_race_class FROM classes WHERE class_id = %s LIMIT 1",
            (class_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        val = row.get("is_race_class") if isinstance(row, dict) else row[0]
        return bool(val) if val is not None else True
    except Exception as e:
        if "is_race_class" in str(e) or "does not exist" in str(e).lower():
            return None
        raise


def require_class_id(conn, cur, raw_label: str, regatta_id: str, source_file: str | None, sample_row: dict | None):
    """
    Resolve class_id from classes (LOWER(TRIM(class_name)) or class_aliases).
    If not found: ensure ingestion_issues table, log row, commit, raise RuntimeError (stop batch).
    If class has is_race_class = FALSE (family/aggregate-only): log to ingestion_issues, raise RuntimeError.
    Returns (class_id, class_canonical) for use in INSERT. class_canonical is from classes.class_name.
    """
    ensure_ingestion_issues_table(conn)
    class_id = resolve_class_id(cur, raw_label)
    if class_id is None:
        record_ingestion_issue(cur, regatta_id, source_file, raw_label, sample_row, "OPEN")
        conn.commit()
        raise RuntimeError(
            f"Unknown class label: {raw_label!r}. Row logged to ingestion_issues. Add class or alias and re-run."
        )
    is_race = _is_race_class(cur, class_id)
    if is_race is False:
        record_ingestion_issue(
            cur, regatta_id, source_file, raw_label, sample_row, "OPEN"
        )
        conn.commit()
        raise RuntimeError(
            f"Class {raw_label!r} (class_id={class_id}) is a family/aggregate class (is_race_class = FALSE). "
            "Only race classes may be inserted into results. Row logged to ingestion_issues."
        )
    class_canonical = get_class_name_by_id(cur, class_id)
    if not class_canonical:
        raise RuntimeError(f"class_id {class_id} resolved but class_name not found in classes.")
    return (class_id, class_canonical)


def resolve_helm_to_sa_id(cur, helm_name: str | None, sail_number: str | None, class_id: int | None = None):
    """
    Resolve helm to a single sa_sailing_id from sailor_helm_aliases, sail_number_history,
    or sas_id_personal only. Order: (1) sailor_helm_aliases, (2) sail_number_history (if table exists),
    (3) sas_id_personal by primary_sailno, (4) sas_id_personal by full_name.
    Returns int (sa_sailing_id) only when exactly one candidate; otherwise None.
    Use for ingestion: if None, set helm_sa_sailing_id = NULL (review queue). Never assign a fake ID.
    """
    if not helm_name or not str(helm_name).strip():
        return None
    helm_norm = str(helm_name).strip().lower()
    sail_norm = str(sail_number).strip() if sail_number else ""
    candidates = set()

    # 1) sailor_helm_aliases
    cur.execute(
        "SELECT sa_sailing_id FROM sailor_helm_aliases WHERE helm_name_alias = %s LIMIT 1",
        (helm_norm,),
    )
    row = cur.fetchone()
    if row:
        sid = row["sa_sailing_id"] if isinstance(row, dict) else row[0]
        if sid is not None:
            candidates.add(int(sid))

    # 2) sail_number_history (if table exists and we have sail_number + class_id)
    if sail_norm and class_id is not None:
        try:
            cur.execute(
                """
                SELECT sa_sailing_id FROM sail_number_history
                WHERE sail_number = %s AND class_id = %s
                """,
                (sail_norm, class_id),
            )
            for row in cur.fetchall():
                sid = row["sa_sailing_id"] if isinstance(row, dict) else row[0]
                if sid is not None:
                    candidates.add(int(sid))
        except Exception:
            pass  # table may not exist yet

    # 3) sas_id_personal by primary_sailno (exact sail number)
    if sail_norm:
        cur.execute(
            """
            SELECT (sa_sailing_id::text)::int AS sid FROM sas_id_personal
            WHERE TRIM(COALESCE(primary_sailno, '')) = %s AND (sa_sailing_id::text) ~ '^[0-9]+$'
            """,
            (sail_norm,),
        )
        for row in cur.fetchall():
            sid = row["sid"] if isinstance(row, dict) else row[0]
            if sid is not None:
                candidates.add(int(sid))

    # 4) sas_id_personal by full_name exact match
    cur.execute(
        """
        SELECT (sa_sailing_id::text)::int AS sid FROM sas_id_personal
        WHERE LOWER(TRIM(COALESCE(full_name, ''))) = %s AND (sa_sailing_id::text) ~ '^[0-9]+$'
        """,
        (helm_norm,),
    )
    full_name_rows = cur.fetchall() or []
    full_name_only_ids = set()
    for row in full_name_rows:
        sid = row["sid"] if isinstance(row, dict) else row[0]
        if sid is not None:
            full_name_only_ids.add(int(sid))
            candidates.add(int(sid))

    # Exact full_name match only when exactly one record in sas_id_personal (no duplicates).
    # If duplicates exist for that full_name, do not auto-match; leave for review.
    if len(full_name_only_ids) == 1:
        return full_name_only_ids.pop()

    if len(candidates) == 1:
        return candidates.pop()
    return None


def _get_db_url() -> str:
    return os.getenv(
        "DB_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master",
        ),
    )


def _extract_year_from_title(title: str | None):
    if not title:
        return None
    match = re.search(r"\b(20\d{2})\b", str(title))
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _clean_event_name_from_result_title(title: str | None) -> str:
    if not title:
        return ""
    name = str(title).strip()
    name = re.sub(r"\.[A-Za-z0-9]{2,6}$", "", name)
    name = re.sub(r"^\s*20\d{2}\b[\s\-_]*", "", name, flags=re.I)
    name = re.sub(r"\bresults?\b", " ", name, flags=re.I)
    name = re.sub(r"\bfinal\b", " ", name, flags=re.I)
    name = re.sub(r"\bprovisional\b", " ", name, flags=re.I)
    name = re.sub(r"\bILCA\s*4\b", " ", name, flags=re.I)
    name = re.sub(r"\bILCA\s*6\b", " ", name, flags=re.I)
    name = re.sub(r"\bILCA\s*7\b", " ", name, flags=re.I)
    name = re.sub(r"\bClass\s*[ABC]\b", " ", name, flags=re.I)
    name = re.sub(r"[_]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -_")
    return name


def _club_phrases_for_title_matching(cur) -> set[str]:
    phrases = set()
    try:
        cur.execute(
            """
            SELECT lower(trim(val))
            FROM (
                SELECT club_fullname AS val FROM clubs WHERE club_fullname IS NOT NULL AND trim(club_fullname) != ''
                UNION
                SELECT club_abbrev AS val FROM clubs WHERE club_abbrev IS NOT NULL AND trim(club_abbrev) != ''
                UNION
                SELECT alias AS val FROM club_aliases WHERE alias IS NOT NULL AND trim(alias) != ''
            ) q
            """
        )
        for row in cur.fetchall() or []:
            raw = (row[0] or "").strip().lower()
            if not raw:
                continue
            raw = re.sub(r"\s+", " ", raw)
            phrases.add(raw)
    except Exception:
        pass
    phrases.update(
        {
            "hermanus yacht club",
            "at hermanus yacht club",
            "hyc",
            "rcyc",
            "mbsc",
        }
    )
    return {p for p in phrases if len(p) >= 3}


def _canonical_event_name(name: str | None, club_phrases: set[str] | None = None) -> str:
    cleaned = _clean_event_name_from_result_title(name).casefold()
    cleaned = re.sub(r"\bresults?\b", " ", cleaned)
    cleaned = re.sub(r"\bregatta\b", " ", cleaned)
    cleaned = re.sub(r"\bevent\b", " ", cleaned)
    cleaned = re.sub(r"\bmonohull\b", " ", cleaned)
    cleaned = re.sub(r"\bmultihull\b", " ", cleaned)
    cleaned = re.sub(r"\bfleet\b", " ", cleaned)
    cleaned = re.sub(r"\bat\s+[^,;:()]*?\byacht club\b", " ", cleaned)
    cleaned = re.sub(r"\b[^,;:()]*?\byacht club\b", " ", cleaned)
    if club_phrases:
        ordered = sorted(club_phrases, key=len, reverse=True)
        for phrase in ordered:
            escaped = re.escape(phrase)
            cleaned = re.sub(rf"\bat\s+{escaped}\b", " ", cleaned)
            cleaned = re.sub(rf"\b{escaped}\b", " ", cleaned)
    cleaned = re.sub(r"[^\w\s#-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _normalize_regatta_name_for_match(name: str | None, club_phrases: set[str] | None = None) -> str:
    return _canonical_event_name(name, club_phrases)


def _slugify_event_name(name: str) -> str:
    """
    Match the main API slugging logic for event names without importing the full app.
    """
    if not name:
        return ""
    s = (name or "").strip().lower()
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def _regattas_optional_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'regattas'
        """
    )
    return {row[0] for row in cur.fetchall() or []}


def _find_regatta_by_source_url(cur, source_url: str):
    cur.execute(
        """
        SELECT regatta_id, event_name
        FROM regattas
        WHERE source_url = %s
        LIMIT 1
        """,
        (source_url,),
    )
    return cur.fetchone()


def _name_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio() * 100.0


def _display_name_for_new_regatta(name: str, club_phrases: set[str] | None = None) -> str:
    canonical = _canonical_event_name(name, club_phrases)
    if not canonical:
        canonical = _clean_event_name_from_result_title(name)
    parts = []
    for token in canonical.split():
        if token.startswith("#"):
            parts.append(token.upper())
        elif token.isupper() and len(token) <= 5:
            parts.append(token)
        else:
            parts.append(token.capitalize())
    return " ".join(parts).strip()


def _find_matching_event_name(cur, event_name_clean: str, year: int, club_phrases: set[str] | None = None):
    try:
        cur.execute(
            """
            SELECT event_name
            FROM events
            WHERE event_name IS NOT NULL
              AND COALESCE(start_date, end_date) IS NOT NULL
              AND EXTRACT(YEAR FROM COALESCE(start_date, end_date)) = %s
            """,
            (year,),
        )
    except Exception:
        return None

    target_clean = _clean_event_name_from_result_title(event_name_clean)
    target_canonical = _canonical_event_name(event_name_clean, club_phrases)
    best_name = None
    best_score = 0.0
    for row in cur.fetchall() or []:
        event_name = row[0] or ""
        candidate_clean = _clean_event_name_from_result_title(event_name)
        candidate_canonical = _canonical_event_name(event_name, club_phrases)
        score = max(
            _name_similarity(target_clean.casefold(), candidate_clean.casefold()),
            _name_similarity(target_canonical, candidate_canonical),
        )
        if score >= 90.0 and score > best_score:
            best_name = event_name
            best_score = score
    return best_name


def _find_existing_regatta_for_result(cur, event_name_clean: str, year: int, slug: str, club_phrases: set[str] | None = None):
    target_norm = _canonical_event_name(event_name_clean, club_phrases)
    cur.execute(
        """
        SELECT regatta_id, event_name, start_date, end_date
        FROM regattas
        WHERE year = %s
        ORDER BY regatta_number ASC NULLS LAST, regatta_id ASC
        """,
        (year,),
    )
    fuzzy_best = None
    fuzzy_score = 0.0
    for regatta_id, event_name, start_date, end_date in cur.fetchall() or []:
        regatta_norm = _canonical_event_name(event_name, club_phrases)
        regatta_slug = _slugify_event_name(event_name or "")
        if regatta_norm == target_norm or regatta_slug == slug:
            return regatta_id, event_name
        score = _name_similarity(target_norm, regatta_norm)
        # Date assist placeholder: when month data becomes available on incoming items,
        # same-year and same-month windows can increase confidence here.
        if score >= 90.0 and score > fuzzy_score:
            fuzzy_best = (regatta_id, event_name, start_date, end_date)
            fuzzy_score = score
    if fuzzy_best:
        return fuzzy_best[0], fuzzy_best[1]
    return None


def _next_regatta_number(cur) -> int:
    cur.execute("SELECT COALESCE(MAX(regatta_number), 0) + 1 FROM regattas WHERE regatta_number IS NOT NULL")
    row = cur.fetchone()
    return int((row[0] if row else 1) or 1)


def _file_name_from_item(item: dict) -> str:
    title_text = (item.get("title_text") or "").strip()
    if title_text:
        return title_text
    source_url = (item.get("source_url") or "").strip()
    if not source_url:
        return ""
    return (urlparse(source_url).path or "").rstrip("/").split("/")[-1]


def ensure_results_staging_source_columns(conn):
    """
    Extend results_staging to hold raw SAS source tracking.

    Notes:
    - source_site can be enforced immediately via default.
    - source_url/source_title_raw are created first, then tightened to NOT NULL only
      when no existing NULLs remain. This avoids rewriting legacy rows.
    """
    cur = conn.cursor()
    cur.execute(
        """
        ALTER TABLE public.results_staging
        ADD COLUMN IF NOT EXISTS source_url TEXT,
        ADD COLUMN IF NOT EXISTS source_title_raw TEXT,
        ADD COLUMN IF NOT EXISTS source_site TEXT NOT NULL DEFAULT 'SAS'
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_results_staging_source_url
        ON public.results_staging (source_url)
        WHERE source_url IS NOT NULL
        """
    )
    cur.execute("SELECT COUNT(*) FROM public.results_staging WHERE source_url IS NULL OR source_title_raw IS NULL")
    missing = int((cur.fetchone() or [0])[0] or 0)
    if missing == 0:
        cur.execute("ALTER TABLE public.results_staging ALTER COLUMN source_url SET NOT NULL")
        cur.execute("ALTER TABLE public.results_staging ALTER COLUMN source_title_raw SET NOT NULL")
    conn.commit()
    cur.close()


def ensure_results_pdf_storage_schema(conn):
    sql = (ROOT / "database" / "migrations" / "180_results_pdf_local_storage.sql").read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def _results_staging_optional_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'results_staging'
        """
    )
    return {row[0] for row in cur.fetchall() or []}


def _deterministic_results_pdf_path(source_url: str, title_text: str, year: int | None) -> Path:
    year_part = str(year) if year else "unknown"
    clean_name = _clean_event_name_from_result_title(title_text) or _file_name_from_item(
        {"title_text": title_text, "source_url": source_url}
    )
    slug = _slugify_event_name(clean_name) or "sas-result"
    year_dir = RESULTS_PDF_ROOT / year_part
    primary = year_dir / f"{slug}.pdf"
    if primary.exists():
        suffix = sha256(source_url.encode("utf-8")).hexdigest()[:10]
        return year_dir / f"{slug}-{suffix}.pdf"
    return primary


def _download_pdf_to_local_path(source_url: str, pdf_path: Path) -> str:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        return "cached"
    if pdf_path.exists():
        pdf_path.unlink(missing_ok=True)

    req = urllib.request.Request(source_url, headers=SAS_RESULTS_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, pdf_path.open("wb") as handle:
            handle.write(resp.read())
    except Exception:
        result = subprocess.run(
            [
                "curl",
                "-L",
                "--fail",
                "-A",
                SAS_RESULTS_HEADERS["User-Agent"],
                "-e",
                SAS_RESULTS_REFERER,
                "-o",
                str(pdf_path),
                source_url,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pdf_path.unlink(missing_ok=True)
            raise RuntimeError((result.stderr or "pdf download failed").strip() or "pdf download failed")

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        pdf_path.unlink(missing_ok=True)
        raise RuntimeError("downloaded pdf is empty")
    if not pdf_path.read_bytes()[:5].startswith(b"%PDF"):
        pdf_path.unlink(missing_ok=True)
        raise RuntimeError("downloaded file is not a valid PDF")
    return "downloaded"


def record_ingestion_log(conn, new_regattas: int, new_results_rows: int, parse_failures: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.ingestion_log (
                new_regattas,
                new_results_rows,
                parse_failures
            )
            VALUES (%s, %s, %s)
            """,
            (new_regattas, new_results_rows, parse_failures),
        )


# =============================================================================
# PROVENANCE FUNCTIONS (Source → Artifact → Regatta/Result linking)
# =============================================================================

# Authority levels (higher = more trustworthy)
AUTHORITY_LEVELS = {
    "sas_pdf": 90,           # Official SAS results PDF
    "sas_html": 85,          # SAS web page
    "sailwave": 80,          # Sailwave file/results
    "windsail": 78,          # Windsail results
    "club_official": 75,     # Club-published results
    "external_scrape": 50,   # Third-party scraped
    "manual_admin": 30,      # Manual admin entry
    "sailingsa_live": 95,    # SailingSA Live (future)
    "unknown": 10,           # Unknown source
}


def _infer_source_type_from_url(url: str) -> str:
    """
    Infer source_type from URL based on domain + file extension/content type.
    
    Rules:
    - .pdf extension + SAS domain → sas_pdf
    - SAS domain without .pdf → sas_html
    - .blw extension or sailwave domain → sailwave
    - windsail domain → windsail
    - Known club domains → club_official
    - Other → external_scrape
    
    Returns source_type string.
    
    TODO: Move club_patterns to database table (source_domains) so Super Admin
    can add/change club domains (HYC, LDYC, RCYC, ZVYC, international clubs)
    without code changes. See INGESTION_PIPELINE_UPDATE_PLAN.md.
    """
    if not url:
        return "unknown"
    
    url_lower = url.lower()
    
    # SAS domain checks (most specific first)
    if "sailing.org.za" in url_lower:
        if url_lower.endswith('.pdf'):
            return "sas_pdf"
        return "sas_html"
    
    # Sailwave - .blw extension or sailwave domain
    if url_lower.endswith('.blw'):
        return "sailwave"
    if "sailwave.com" in url_lower or "sailwave.co" in url_lower:
        return "sailwave"
    
    # Windsail
    if "windsail" in url_lower:
        return "windsail"
    
    # Club domains - common patterns for SA sailing clubs
    club_patterns = [
        "yacht", "sailing", "boat", "dinghy", "yc.", "sc.",
        "royalcapeyc", "rcyc", "zvyc", "zvsc", "hbyc", "thyc",
        "langebaan", "saldanha", "durban", "knysna", "mossel",
        "club.co.za", "club.org.za"
    ]
    for pattern in club_patterns:
        if pattern in url_lower and "sailing.org.za" not in url_lower:
            return "club_official"
    
    # Default for unknown external sources
    return "external_scrape"


def _compute_file_checksum(file_path: Path | str) -> str | None:
    """Compute MD5 checksum of a file. Returns None if file doesn't exist."""
    path = Path(file_path) if isinstance(file_path, str) else file_path
    if not path.exists():
        return None
    hasher = md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_source_artifact(
    conn,
    source_url: str | None,
    source_type: str,
    import_method: str,
    authority_level: int | None = None,
    raw_file_path: str | None = None,
    checksum_md5: str | None = None,
    captured_by: str = "ingestion",
    parse_notes: str | None = None,
) -> int | None:
    """
    Create or get existing source_artifact, return artifact_id.
    
    Idempotent: if source_url already exists, returns existing artifact_id.
    If raw_file_path provided and checksum not given, computes it.
    
    Args:
        conn: Database connection
        source_url: URL of the source (can be None for local-only files)
        source_type: One of source_types.type_code (sas_pdf, club_official, etc.)
        import_method: One of import_methods.method_code (scrape_auto, manual_entry, etc.)
        authority_level: Override authority level (default from AUTHORITY_LEVELS)
        raw_file_path: Local path to stored file
        checksum_md5: MD5 hash of file (computed if not provided)
        captured_by: Who/what captured this artifact
        parse_notes: Optional notes about parsing
        
    Returns:
        artifact_id (int) or None if creation failed
    """
    if authority_level is None:
        authority_level = AUTHORITY_LEVELS.get(source_type, AUTHORITY_LEVELS["unknown"])
    
    # Compute checksum if file exists and not provided
    if raw_file_path and not checksum_md5:
        checksum_md5 = _compute_file_checksum(raw_file_path)
    
    cur = conn.cursor()
    
    # Check for existing artifact by source_url (idempotent)
    if source_url:
        cur.execute(
            "SELECT artifact_id FROM source_artifacts WHERE source_url = %s LIMIT 1",
            (source_url,),
        )
        row = cur.fetchone()
        if row:
            cur.close()
            return row[0] if not isinstance(row, dict) else row["artifact_id"]
    
    # Check for existing artifact by checksum (same file, different URL)
    if checksum_md5:
        cur.execute(
            "SELECT artifact_id FROM source_artifacts WHERE checksum_md5 = %s LIMIT 1",
            (checksum_md5,),
        )
        row = cur.fetchone()
        if row:
            cur.close()
            return row[0] if not isinstance(row, dict) else row["artifact_id"]
    
    # Insert new artifact
    try:
        cur.execute(
            """
            INSERT INTO source_artifacts (
                source_type, import_method, authority_level, artifact_status,
                source_url, raw_file_path, checksum_md5,
                first_retrieved_at, last_retrieved_at,
                captured_by, parse_notes
            )
            VALUES (%s, %s, %s, 'active', %s, %s, %s, NOW(), NOW(), %s, %s)
            RETURNING artifact_id
            """,
            (source_type, import_method, authority_level, source_url, raw_file_path, 
             checksum_md5, captured_by, parse_notes),
        )
        row = cur.fetchone()
        artifact_id = row[0] if row else None
        conn.commit()
        cur.close()
        return artifact_id
    except Exception as e:
        conn.rollback()
        cur.close()
        # Table may not exist yet - return None gracefully
        if "source_artifacts" in str(e) and "does not exist" in str(e).lower():
            return None
        raise


def link_regatta_to_artifact(
    conn,
    regatta_id: str,
    artifact_id: int,
    source_scope: str = "regatta",
    is_original: bool = True,
    is_primary: bool = True,
    scope_class_id: int | None = None,
    scope_result_id: int | None = None,
    covers_all_classes: bool = True,
    covers_all_races: bool = True,
    class_ids_covered: list[int] | None = None,
    race_numbers_covered: list[int] | None = None,
    validation_status: str = "pending_review",
    created_by: str = "ingestion",
    notes: str | None = None,
) -> int | None:
    """
    Create regatta_sources entry linking regatta to artifact.
    
    Idempotent: if link already exists, returns existing regatta_source_id.
    Respects exactly-one-primary constraint via database triggers.
    
    Args:
        conn: Database connection
        regatta_id: Regatta ID to link
        artifact_id: Source artifact ID
        source_scope: One of source_scopes (regatta, class, fleet, race, entry, result, boat)
        is_original: Whether this is the original source (immutable once set)
        is_primary: Whether this is the current primary source
        scope_class_id: For class-scope sources, which class
        scope_result_id: For result-scope sources, which result
        covers_all_classes: Whether source covers all classes in regatta
        covers_all_races: Whether source covers all races
        class_ids_covered: Array of class_ids if partial coverage
        race_numbers_covered: Array of race numbers if partial coverage
        validation_status: One of validation_statuses (draft, pending_review, validated, etc.)
        created_by: Who created this link
        notes: Optional notes
        
    Returns:
        regatta_source_id (int) or None if creation failed
    """
    cur = conn.cursor()
    
    # Get authority_level from artifact
    cur.execute(
        "SELECT authority_level FROM source_artifacts WHERE artifact_id = %s",
        (artifact_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    authority_level = row[0] if not isinstance(row, dict) else row["authority_level"]
    
    # Check for existing link (idempotent)
    cur.execute(
        """
        SELECT regatta_source_id FROM regatta_sources 
        WHERE regatta_id = %s AND artifact_id = %s
        LIMIT 1
        """,
        (regatta_id, artifact_id),
    )
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0] if not isinstance(row, dict) else row["regatta_source_id"]
    
    # Insert new link
    try:
        cur.execute(
            """
            INSERT INTO regatta_sources (
                regatta_id, artifact_id, source_scope,
                scope_class_id, scope_result_id,
                is_original, is_primary, authority_level,
                validation_status, covers_all_classes, covers_all_races,
                class_ids_covered, race_numbers_covered,
                created_by, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING regatta_source_id
            """,
            (regatta_id, artifact_id, source_scope, scope_class_id, scope_result_id,
             is_original, is_primary, authority_level, validation_status,
             covers_all_classes, covers_all_races, class_ids_covered, race_numbers_covered,
             created_by, notes),
        )
        row = cur.fetchone()
        regatta_source_id = row[0] if row else None
        conn.commit()
        cur.close()
        return regatta_source_id
    except Exception as e:
        conn.rollback()
        cur.close()
        # Table may not exist yet - return None gracefully
        if "regatta_sources" in str(e) and "does not exist" in str(e).lower():
            return None
        raise


def link_result_to_artifact(
    conn,
    result_id: int,
    artifact_id: int,
    is_original: bool = True,
    is_current: bool = True,
    source_locator: str | None = None,
    fields_from_source: list[str] | None = None,
    race_numbers_from_source: list[int] | None = None,
    created_by: str = "ingestion",
    notes: str | None = None,
) -> int | None:
    """
    Create result_sources entry linking result to artifact.
    
    Idempotent: if link already exists, returns existing result_source_id.
    
    Args:
        conn: Database connection
        result_id: Result ID to link
        artifact_id: Source artifact ID
        is_original: Whether this is the original source (immutable)
        is_current: Whether this is the current active source
        source_locator: Page/row/cell reference within source document
        fields_from_source: Which fields came from this source
        race_numbers_from_source: Which race results came from this source
        created_by: Who created this link
        notes: Optional notes
        
    Returns:
        result_source_id (int) or None if creation failed
    """
    cur = conn.cursor()
    
    # Verify artifact exists
    cur.execute(
        "SELECT artifact_id FROM source_artifacts WHERE artifact_id = %s",
        (artifact_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    
    # Check for existing link (idempotent)
    cur.execute(
        """
        SELECT result_source_id FROM result_sources 
        WHERE result_id = %s AND artifact_id = %s
        LIMIT 1
        """,
        (result_id, artifact_id),
    )
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0] if not isinstance(row, dict) else row["result_source_id"]
    
    # Insert new link
    try:
        cur.execute(
            """
            INSERT INTO result_sources (
                result_id, artifact_id, is_original, is_current,
                source_locator, fields_from_source, race_numbers_from_source,
                created_by, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING result_source_id
            """,
            (result_id, artifact_id, is_original, is_current,
             source_locator, fields_from_source, race_numbers_from_source,
             created_by, notes),
        )
        row = cur.fetchone()
        result_source_id = row[0] if row else None
        conn.commit()
        cur.close()
        return result_source_id
    except Exception as e:
        conn.rollback()
        cur.close()
        # Table may not exist yet - return None gracefully
        if "result_sources" in str(e) and "does not exist" in str(e).lower():
            return None
        raise


class _ReadOnlyBoatCursor:
    """
    Cursor wrapper that enforces read-only access to boat tables.
    Raises AssertionError if ANY write operation is attempted on protected tables.
    
    Protected tables: boats, boat_identifiers, boat_names, boat_associations
    
    Blocked operations:
    - DML: INSERT, UPDATE, DELETE, MERGE, UPSERT
    - DDL: CREATE, ALTER, DROP, TRUNCATE, RENAME
    - Bulk: COPY, executemany, copy_expert
    - Procedures: CALL on procedures that might modify protected tables
    
    This makes the ingestion layer TECHNICALLY INCAPABLE of modifying
    Boat Register data, not just conventionally prevented.
    """
    PROTECTED_TABLES = frozenset({"boats", "boat_identifiers", "boat_names", "boat_associations"})
    
    # DML patterns: INSERT, UPDATE, DELETE, MERGE, UPSERT
    DML_PATTERNS = re.compile(
        r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|UPSERT\s+INTO)\s+[\"']?(\w+)[\"']?",
        re.IGNORECASE
    )
    
    # DDL patterns: CREATE, ALTER, DROP, TRUNCATE, RENAME on tables/indexes
    DDL_PATTERNS = re.compile(
        r"\b(CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|TRUNCATE\s+TABLE?|TRUNCATE|RENAME\s+TABLE|"
        r"CREATE\s+INDEX\s+\w+\s+ON|DROP\s+INDEX\s+\w+\s+ON|REINDEX\s+TABLE)\s+"
        r"(?:IF\s+(?:NOT\s+)?EXISTS\s+)?[\"']?(\w+)[\"']?",
        re.IGNORECASE
    )
    
    # COPY pattern (bulk import)
    COPY_PATTERN = re.compile(
        r"\bCOPY\s+[\"']?(\w+)[\"']?\s+(?:FROM|TO)",
        re.IGNORECASE
    )
    
    # Stored procedure/function CALL pattern - catches CALL and SELECT function()
    CALL_PATTERN = re.compile(
        r"\b(CALL|SELECT)\s+[\"']?(\w*boat\w*)[\"']?\s*\(",
        re.IGNORECASE
    )
    
    # CTE (WITH) that contains writes to protected tables
    CTE_WRITE_PATTERN = re.compile(
        r"\bWITH\b.*?\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+[\"']?(\w+)[\"']?",
        re.IGNORECASE | re.DOTALL
    )
    
    # LOCK TABLE pattern
    LOCK_PATTERN = re.compile(
        r"\bLOCK\s+(?:TABLE\s+)?[\"']?(\w+)[\"']?",
        re.IGNORECASE
    )
    
    def __init__(self, cursor):
        self._cursor = cursor
    
    def _check_query(self, query: str, operation_name: str = "execute"):
        """
        Check query for any write operation on protected tables.
        Raises AssertionError if violation detected.
        """
        query_str = str(query) if query else ""
        
        # Check DML (INSERT, UPDATE, DELETE, MERGE, UPSERT)
        match = self.DML_PATTERNS.search(query_str)
        if match:
            operation = match.group(1).upper().replace("  ", " ")
            table_name = match.group(2).lower()
            if table_name in self.PROTECTED_TABLES:
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                    f"{operation} on '{table_name}' is forbidden. "
                    f"Boat creation/modification belongs to Boat Register/backfill workflow, not ingestion."
                )
        
        # Check DDL (CREATE, ALTER, DROP, TRUNCATE, RENAME)
        match = self.DDL_PATTERNS.search(query_str)
        if match:
            operation = match.group(1).upper().replace("  ", " ")
            table_name = match.group(2).lower()
            if table_name in self.PROTECTED_TABLES:
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                    f"{operation} on '{table_name}' is forbidden. "
                    f"DDL on Boat Register tables belongs to migration workflow, not ingestion."
                )
        
        # Check COPY (bulk import/export)
        match = self.COPY_PATTERN.search(query_str)
        if match:
            table_name = match.group(1).lower()
            if table_name in self.PROTECTED_TABLES:
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                    f"COPY on '{table_name}' is forbidden. "
                    f"Bulk operations on Boat Register tables belong to backfill workflow, not ingestion."
                )
        
        # Check for procedure calls that might modify boat tables
        match = self.CALL_PATTERN.search(query_str)
        if match:
            proc_name = match.group(2).lower()
            # Block any procedure with 'boat' in the name as a safety measure
            raise AssertionError(
                f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                f"Calling procedure/function '{proc_name}' is forbidden. "
                f"Procedures that may modify Boat Register data cannot be called from ingestion."
            )
        
        # Check for CTE (WITH) writes to protected tables
        match = self.CTE_WRITE_PATTERN.search(query_str)
        if match:
            operation = match.group(1).upper().replace("  ", " ")
            table_name = match.group(2).lower()
            if table_name in self.PROTECTED_TABLES:
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                    f"CTE with {operation} on '{table_name}' is forbidden. "
                    f"Boat Register modifications belong to dedicated workflow, not ingestion."
                )
        
        # Check for LOCK TABLE on protected tables
        match = self.LOCK_PATTERN.search(query_str)
        if match:
            table_name = match.group(1).lower()
            if table_name in self.PROTECTED_TABLES:
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                    f"LOCK TABLE on '{table_name}' is forbidden. "
                    f"Locking Boat Register tables is not allowed from ingestion."
                )
        
        # Check for any reference to protected tables in potentially dangerous contexts
        # This catches edge cases like: "SELECT modify_boat(...)" or dynamic SQL
        for table in self.PROTECTED_TABLES:
            # Check for function calls that include table name (e.g., insert_boat, update_boat_identifier)
            func_pattern = re.compile(
                rf"\b(insert|update|delete|create|drop|truncate|modify|add|remove|set)_?{table}s?\s*\(",
                re.IGNORECASE
            )
            if func_pattern.search(query_str):
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [{operation_name}]: "
                    f"Function call appears to modify '{table}'. "
                    f"Boat Register modifications belong to dedicated workflow, not ingestion."
                )
    
    def execute(self, query, params=None):
        """Execute a query after checking for write violations."""
        self._check_query(query, "execute")
        return self._cursor.execute(query, params) if params else self._cursor.execute(query)
    
    def executemany(self, query, params_seq):
        """Execute query with multiple parameter sets - blocked for protected tables."""
        self._check_query(query, "executemany")
        return self._cursor.executemany(query, params_seq)
    
    def copy_from(self, file, table, *args, **kwargs):
        """COPY FROM - blocked for protected tables."""
        if table.lower() in self.PROTECTED_TABLES:
            raise AssertionError(
                f"INGESTION READ-ONLY VIOLATION [copy_from]: "
                f"COPY FROM into '{table}' is forbidden. "
                f"Bulk import to Boat Register tables belongs to backfill workflow, not ingestion."
            )
        return self._cursor.copy_from(file, table, *args, **kwargs)
    
    def copy_to(self, file, table, *args, **kwargs):
        """COPY TO - allowed (read-only), but log for awareness."""
        return self._cursor.copy_to(file, table, *args, **kwargs)
    
    def copy_expert(self, sql, file, *args, **kwargs):
        """COPY with custom SQL - check for protected tables."""
        self._check_query(sql, "copy_expert")
        return self._cursor.copy_expert(sql, file, *args, **kwargs)
    
    def callproc(self, procname, params=None):
        """Call stored procedure - blocked if name suggests boat modification."""
        procname_lower = procname.lower()
        for table in self.PROTECTED_TABLES:
            if table in procname_lower:
                raise AssertionError(
                    f"INGESTION READ-ONLY VIOLATION [callproc]: "
                    f"Calling procedure '{procname}' is forbidden. "
                    f"Procedures that may modify Boat Register data cannot be called from ingestion."
                )
        return self._cursor.callproc(procname, params) if params else self._cursor.callproc(procname)
    
    def fetchone(self):
        return self._cursor.fetchone()
    
    def fetchall(self):
        return self._cursor.fetchall()
    
    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
    
    def close(self):
        return self._cursor.close()
    
    def __iter__(self):
        return iter(self._cursor)
    
    def __next__(self):
        return next(self._cursor)
    
    def __getattr__(self, name):
        # Block any method that might be used for writes
        blocked_methods = {'mogrify'}  # mogrify itself is safe, but log for awareness
        attr = getattr(self._cursor, name)
        return attr


def resolve_boat_id(
    cur,
    sail_number: str | None,
    class_id: int | None,
    class_family_id: int | None = None,
) -> int | None:
    """
    Resolve sail_number + class to boat_id via boat_identifiers.
    
    READ-ONLY ENFORCED: This function uses a protected cursor that will raise
    AssertionError if any INSERT, UPDATE, DELETE, or MERGE is attempted on
    boats, boat_identifiers, boat_names, or boat_associations tables.
    Creation, merges, and conflict resolution belong to the dedicated
    Boat Register/backfill workflow, not the ingestion path.
    
    Rules:
    - Exact normalized match only (no fuzzy)
    - Class-family aware: ILCA rigs (4.7, 6, 7) share hull identity
    - Returns boat_id only when exactly one active match found
    - Multiple matches or no match → returns None (review queue)
    - Never auto-creates boats or identifiers
    
    Args:
        cur: Database cursor (will be wrapped for read-only enforcement)
        sail_number: Sail number to match (e.g., "RSA 123", "123")
        class_id: Class ID from classes table
        class_family_id: Optional hull family ID (if known)
        
    Returns:
        boat_id (int) or None if no unique match
        
    Raises:
        AssertionError: If any write operation is attempted on boat tables
    """
    # Wrap cursor to enforce read-only access to boat tables
    safe_cur = _ReadOnlyBoatCursor(cur)
    if not sail_number or not str(sail_number).strip():
        return None
    
    # Normalize sail number: uppercase, strip, collapse whitespace
    sail_norm = re.sub(r"\s+", " ", str(sail_number).strip().upper())
    
    # If no class_family_id provided, try to get it from classes
    if class_family_id is None and class_id is not None:
        try:
            safe_cur.execute(
                "SELECT hull_family_id FROM classes WHERE class_id = %s",
                (class_id,),
            )
            row = safe_cur.fetchone()
            if row:
                class_family_id = row[0] if not isinstance(row, dict) else row.get("hull_family_id")
        except Exception:
            pass  # Column may not exist
    
    # Build query based on what we have
    candidates = []
    
    try:
        if class_family_id is not None:
            # Family-aware match: find boats where identifier class shares same family
            safe_cur.execute(
                """
                SELECT DISTINCT bi.boat_id
                FROM boat_identifiers bi
                JOIN classes c ON c.class_id = bi.class_id
                WHERE bi.sail_number_normalized = %s
                  AND bi.identifier_status = 'active'
                  AND (
                      bi.class_id = %s
                      OR c.hull_family_id = %s
                  )
                """,
                (sail_norm, class_id, class_family_id),
            )
        elif class_id is not None:
            # Exact class match only
            safe_cur.execute(
                """
                SELECT DISTINCT bi.boat_id
                FROM boat_identifiers bi
                WHERE bi.sail_number_normalized = %s
                  AND bi.class_id = %s
                  AND bi.identifier_status = 'active'
                """,
                (sail_norm, class_id),
            )
        else:
            # No class info - try to match by sail number alone (risky, may have conflicts)
            safe_cur.execute(
                """
                SELECT DISTINCT bi.boat_id
                FROM boat_identifiers bi
                WHERE bi.sail_number_normalized = %s
                  AND bi.identifier_status = 'active'
                """,
                (sail_norm,),
            )
        
        for row in safe_cur.fetchall() or []:
            boat_id = row[0] if not isinstance(row, dict) else row.get("boat_id")
            if boat_id is not None:
                candidates.append(boat_id)
                
    except Exception as e:
        # Table may not exist yet
        if "boat_identifiers" in str(e) and "does not exist" in str(e).lower():
            return None
        raise
    
    # Return boat_id only if exactly one match
    if len(candidates) == 1:
        return candidates[0]
    
    # Multiple matches = ambiguity → needs review
    # No matches = unknown boat → needs review or new boat creation
    return None


def update_artifact_status(
    conn,
    artifact_id: int,
    status: Literal["active", "archived", "corrupted", "deleted_source", "pending_retrieval"],
    parse_notes: str | None = None,
) -> bool:
    """
    Update artifact_status after parse/validation.
    
    Args:
        conn: Database connection
        artifact_id: Artifact to update
        status: New status
        parse_notes: Optional notes to append
        
    Returns:
        True if updated, False if artifact not found
    """
    cur = conn.cursor()
    try:
        if parse_notes:
            cur.execute(
                """
                UPDATE source_artifacts 
                SET artifact_status = %s, 
                    parse_notes = COALESCE(parse_notes || E'\n', '') || %s
                WHERE artifact_id = %s
                RETURNING artifact_id
                """,
                (status, parse_notes, artifact_id),
            )
        else:
            cur.execute(
                """
                UPDATE source_artifacts 
                SET artifact_status = %s
                WHERE artifact_id = %s
                RETURNING artifact_id
                """,
                (status, artifact_id),
            )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row is not None
    except Exception as e:
        conn.rollback()
        cur.close()
        if "source_artifacts" in str(e) and "does not exist" in str(e).lower():
            return False
        raise


def log_ambiguity_issue(
    conn,
    regatta_id: str,
    issue_type: str,
    issue_details: dict,
    source_file: str | None = None,
    created_by: str | None = None,
) -> int | None:
    """
    Log an ambiguity or unresolved match to ingestion_issues for admin review.
    
    Issue types:
    - 'boat_ambiguous': Multiple boats match sail_number + class
    - 'boat_not_found': No boat matches (candidate for new boat)
    - 'sailor_ambiguous': Multiple sailors match helm name
    - 'sailor_not_found': No sailor match
    - 'class_not_found': Unknown class label
    
    Args:
        conn: Database connection
        regatta_id: Regatta context
        issue_type: Type of ambiguity
        issue_details: Dict with context (sail_number, helm_name, class, etc.)
        source_file: Source file reference
        created_by: Who/what logged this
        
    Returns:
        Issue ID or None if table doesn't exist
    """
    cur = conn.cursor()
    try:
        # Ensure table exists with extended schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_issues (
                id SERIAL PRIMARY KEY,
                regatta_id TEXT NOT NULL,
                issue_type TEXT NOT NULL DEFAULT 'unknown_class',
                source_file TEXT,
                raw_class_label TEXT,
                issue_details JSONB,
                created_by TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                resolved_at TIMESTAMPTZ,
                resolved_by TEXT,
                resolution_notes TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN'
            )
        """)
        
        # Add issue_type column if missing (for existing tables)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'ingestion_issues' AND column_name = 'issue_type'
                ) THEN
                    ALTER TABLE ingestion_issues ADD COLUMN issue_type TEXT DEFAULT 'unknown_class';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'ingestion_issues' AND column_name = 'issue_details'
                ) THEN
                    ALTER TABLE ingestion_issues ADD COLUMN issue_details JSONB;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'ingestion_issues' AND column_name = 'created_by'
                ) THEN
                    ALTER TABLE ingestion_issues ADD COLUMN created_by TEXT;
                END IF;
            END $$;
        """)
        
        import json
        cur.execute(
            """
            INSERT INTO ingestion_issues 
            (regatta_id, issue_type, source_file, issue_details, created_by, status)
            VALUES (%s, %s, %s, %s::jsonb, %s, 'OPEN')
            RETURNING id
            """,
            (regatta_id, issue_type, source_file, json.dumps(issue_details), created_by),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row[0] if row else None
    except Exception as e:
        conn.rollback()
        cur.close()
        return None


def insert_result_with_provenance(
    conn,
    regatta_id: str,
    source_url: str,
    source_type: str | None = None,
    import_method: str = "manual_entry",  # Default to valid import_method from migration 210
    # Result data
    sail_number: str | None = None,
    helm_name: str | None = None,
    crew_name: str | None = None,
    class_id: int | None = None,
    raw_class_label: str | None = None,
    fleet_label: str | None = None,
    rank_overall: int | None = None,
    total_points: float | None = None,
    net_points: float | None = None,
    race_scores: dict | None = None,
    # Provenance options
    created_by: str | None = None,
    source_file: str | None = None,
    source_locator: str | None = None,
) -> dict:
    """
    Insert a result row with full provenance tracking.
    
    Order:
    1. Create/find source artifact
    2. Link regatta to artifact (if not already linked)
    3. Resolve class_id (if raw_class_label provided)
    4. Insert result row
    5. Link result to artifact
    6. Resolve boat_id (exact match only)
    7. Log ambiguity issues instead of guessing
    
    Args:
        conn: Database connection
        regatta_id: Target regatta
        source_url: Source URL for artifact
        source_type: Source type (auto-inferred if None)
        import_method: How the data was imported
        sail_number: Sail number from source
        helm_name: Helm name from source
        crew_name: Crew name from source
        class_id: Resolved class ID (or None to resolve from raw_class_label)
        raw_class_label: Raw class label to resolve
        fleet_label: Fleet/division label
        rank_overall: Overall rank
        total_points: Total points
        net_points: Net points after discards
        race_scores: Dict of race scores {race_num: points}
        created_by: Who/what is inserting
        source_file: Local file path reference
        source_locator: Specific location in source (page, row)
        
    Returns:
        Dict with:
        - success: bool
        - result_id: int or None
        - artifact_id: int or None
        - boat_id: int or None
        - helm_sa_sailing_id: str or None
        - issues: list of logged issues
        - error: str or None
    """
    result = {
        "success": False,
        "result_id": None,
        "artifact_id": None,
        "boat_id": None,
        "helm_sa_sailing_id": None,
        "issues": [],
        "error": None,
    }
    
    # Ensure clean transaction state
    try:
        conn.rollback()
    except Exception:
        pass
    
    cur = conn.cursor()
    try:
        # 1. CREATE/FIND ARTIFACT
        if source_type is None:
            source_type = _infer_source_type_from_url(source_url)
        
        try:
            artifact_id = create_source_artifact(
                conn, source_url, source_type, import_method,
                raw_file_path=source_file,
                captured_by=created_by,
                parse_notes=f"Result insert for {regatta_id}"
            )
            result["artifact_id"] = artifact_id
        except Exception as e:
            result["error"] = f"Step 1 (artifact): {e}"
            raise
        
        # 2. LINK REGATTA TO ARTIFACT (idempotent - won't duplicate)
        if artifact_id:
            try:
                link_regatta_to_artifact(
                    conn, regatta_id, artifact_id,
                    source_scope="regatta",
                    is_original=True,
                    is_primary=True,
                    validation_status="pending_review",  # NO auto-validation
                    created_by=created_by,
                    notes="Result insert - pending validation"
                )
            except Exception as e:
                result["error"] = f"Step 2 (link regatta): {e}"
                raise
        
        # Reset cursor after commits from helper functions
        cur.close()
        cur = conn.cursor()
        
        # 3. RESOLVE CLASS (if not provided)
        if class_id is None and raw_class_label:
            class_id = resolve_class_id(cur, raw_class_label)
            if class_id is None:
                # Log unknown class issue
                issue_id = log_ambiguity_issue(
                    conn, regatta_id, "class_not_found",
                    {"raw_class_label": raw_class_label, "sail_number": sail_number, "helm_name": helm_name},
                    source_file=source_file, created_by=created_by
                )
                result["issues"].append({"type": "class_not_found", "issue_id": issue_id})
                result["error"] = f"Unknown class: {raw_class_label}"
                cur.close()
                return result
        
        # Get class_canonical for result row
        class_canonical = get_class_name_by_id(cur, class_id) if class_id else None
        
        # Resolve helm to SA ID (no guessing - NULL if not found)
        try:
            helm_sa_sailing_id = resolve_helm_to_sa_id(cur, helm_name, sail_number, class_id)
        except Exception as e:
            # Sailor resolution failure is not fatal - just log and continue with NULL
            helm_sa_sailing_id = None
            conn.rollback()
            cur = conn.cursor()
        result["helm_sa_sailing_id"] = helm_sa_sailing_id
        
        if helm_name and helm_sa_sailing_id is None:
            # Log unresolved sailor (not blocking, just for review)
            try:
                issue_id = log_ambiguity_issue(
                    conn, regatta_id, "sailor_not_found",
                    {"helm_name": helm_name, "sail_number": sail_number, "class_id": class_id},
                    source_file=source_file, created_by=created_by
                )
                result["issues"].append({"type": "sailor_not_found", "issue_id": issue_id})
            except Exception:
                pass  # Logging failure is not fatal
        
        # Reset cursor after potential commits from logging functions
        try:
            cur.close()
        except Exception:
            pass
        cur = conn.cursor()
        
        # 4. RESOLVE BOAT_ID BEFORE INSERT (exact match only - NO guessing)
        # Resolve before insert so we can include boat_id in single INSERT (no UPDATE)
        boat_id = None
        if sail_number and class_id:
            boat_id = resolve_boat_id(cur, sail_number, class_id)
            result["boat_id"] = boat_id
        
        # 5. INSERT RESULT ROW (with boat_id if found, NULL otherwise)
        # Check which columns exist in results table
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'results' AND table_schema = 'public'
        """)
        existing_cols = {row[0] for row in cur.fetchall()}
        
        # Build dynamic INSERT
        import json
        insert_cols = ["regatta_id"]
        insert_vals = [regatta_id]
        
        if "sail_number" in existing_cols and sail_number:
            insert_cols.append("sail_number")
            insert_vals.append(sail_number)
        
        if "helm_name" in existing_cols and helm_name:
            insert_cols.append("helm_name")
            insert_vals.append(helm_name)
        
        if "crew_name" in existing_cols and crew_name:
            insert_cols.append("crew_name")
            insert_vals.append(crew_name)
        
        if "class_id" in existing_cols and class_id:
            insert_cols.append("class_id")
            insert_vals.append(class_id)
        
        if "class_canonical" in existing_cols and class_canonical:
            insert_cols.append("class_canonical")
            insert_vals.append(class_canonical)
        
        if "fleet_label" in existing_cols and fleet_label:
            insert_cols.append("fleet_label")
            insert_vals.append(fleet_label)
        
        if "rank_overall" in existing_cols and rank_overall is not None:
            insert_cols.append("rank_overall")
            insert_vals.append(rank_overall)
        
        if "total_points" in existing_cols and total_points is not None:
            insert_cols.append("total_points")
            insert_vals.append(total_points)
        
        if "net_points" in existing_cols and net_points is not None:
            insert_cols.append("net_points")
            insert_vals.append(net_points)
        
        if "race_scores" in existing_cols and race_scores:
            insert_cols.append("race_scores")
            insert_vals.append(json.dumps(race_scores))
        
        if "helm_sa_sailing_id" in existing_cols:
            insert_cols.append("helm_sa_sailing_id")
            insert_vals.append(helm_sa_sailing_id)
        
        # Include boat_id in INSERT (NULL if not found - no UPDATE needed)
        if "boat_id" in existing_cols:
            insert_cols.append("boat_id")
            insert_vals.append(boat_id)  # Will be None if not resolved
        
        # Provenance columns on result row
        if "original_artifact_id" in existing_cols and artifact_id:
            insert_cols.append("original_artifact_id")
            insert_vals.append(artifact_id)
        
        if "current_artifact_id" in existing_cols and artifact_id:
            insert_cols.append("current_artifact_id")
            insert_vals.append(artifact_id)
        
        if "row_validation_status" in existing_cols:
            insert_cols.append("row_validation_status")
            insert_vals.append("pending_review")  # NO auto-validation
        
        placeholders = ", ".join(["%s"] * len(insert_cols))
        cols_sql = ", ".join(insert_cols)
        
        cur.execute(
            f"INSERT INTO results ({cols_sql}) VALUES ({placeholders}) RETURNING result_id",
            tuple(insert_vals),
        )
        row = cur.fetchone()
        result_id = row[0] if row else None
        result["result_id"] = result_id
        
        # 6. LINK RESULT TO ARTIFACT
        if result_id and artifact_id:
            link_result_to_artifact(
                conn, result_id, artifact_id,
                is_original=True,
                is_current=True,
                source_locator=source_locator,
                fields_from_source=["sail_number", "helm_name", "rank_overall", "total_points", "net_points"],
                created_by=created_by,
                notes="Initial result insert"
            )
        
        # 7. LOG BOAT AMBIGUITY after insert (don't guess - boat_id already NULL in row)
        if sail_number and class_id and boat_id is None:
            try:
                issue_id = log_ambiguity_issue(
                    conn, regatta_id, "boat_not_found",
                    {"sail_number": sail_number, "class_id": class_id, "helm_name": helm_name},
                    source_file=source_file, created_by=created_by
                )
                result["issues"].append({"type": "boat_not_found", "issue_id": issue_id})
            except Exception:
                pass  # Logging failure is not fatal
        
        conn.commit()
        result["success"] = True
        cur.close()
        return result
        
    except Exception as e:
        conn.rollback()
        cur.close()
        result["error"] = str(e)
        return result


def stage_new_sas_results_with_local_pdfs(result_items, dry_run: bool = True, apply: bool = False):
    """
    Stage only new SAS result PDFs into results_staging and store them locally.

    Rules:
    - skip rows already in results_staging by source_url
    - skip rows that already exist in regattas by normalized name + year or source_url
    - download PDFs only for rows that will be staged
    - never overwrite an existing local file
    - no parsing and no imports
    """
    if apply:
        dry_run = False

    report = []
    new_rows = 0
    failures = 0
    db_url = _get_db_url()

    with psycopg2.connect(db_url) as conn:
        if not dry_run:
            ensure_results_staging_source_columns(conn)
            ensure_results_pdf_storage_schema(conn)

        with conn.cursor() as cur:
            club_phrases = _club_phrases_for_title_matching(cur)
            regatta_optional_cols = _regattas_optional_columns(cur)

            for item in result_items or []:
                source_url = (item.get("source_url") or "").strip()
                title_text = (item.get("title_text") or "").strip()
                file_name = _file_name_from_item(item)
                year = _extract_year_from_title(title_text or file_name)
                event_name_clean = _clean_event_name_from_result_title(title_text or file_name)
                slug = _slugify_event_name(event_name_clean) or "sas-result"
                pdf_path = _deterministic_results_pdf_path(source_url, title_text or file_name, year)

                row_report = {
                    "file_name": file_name,
                    "source_title_raw": title_text,
                    "source_url": source_url,
                    "event_name_clean": event_name_clean,
                    "year": year,
                    "pdf_local_path": str(pdf_path),
                    "created": "no",
                    "downloaded": "no",
                    "reason": "",
                }

                if not source_url or not title_text or year is None or not event_name_clean:
                    row_report["reason"] = "SKIP_MISSING_REQUIRED_METADATA"
                    report.append(row_report)
                    continue

                cur.execute(
                    """
                    SELECT staging_id
                    FROM public.results_staging
                    WHERE source_url = %s
                    LIMIT 1
                    """,
                    (source_url,),
                )
                if cur.fetchone():
                    row_report["reason"] = "SKIP_EXISTING_STAGING_SOURCE_URL"
                    report.append(row_report)
                    continue

                existing_regatta = _find_regatta_by_source_url(cur, source_url) if "source_url" in regatta_optional_cols else None
                if not existing_regatta:
                    existing_regatta = _find_existing_regatta_for_result(
                        cur,
                        event_name_clean,
                        year,
                        slug,
                        club_phrases,
                    )
                if existing_regatta:
                    row_report["reason"] = "SKIP_EXISTING_REGATTA"
                    report.append(row_report)
                    continue

                if not dry_run:
                    try:
                        download_status = _download_pdf_to_local_path(source_url, pdf_path)
                    except Exception as exc:
                        failures += 1
                        row_report["reason"] = f"DOWNLOAD_FAILED:{exc}"
                        report.append(row_report)
                        continue

                    cur.execute(
                        """
                        INSERT INTO public.results_staging (
                            regatta_id,
                            fleet_label,
                            race_scores,
                            source_url,
                            source_title_raw,
                            source_site,
                            validation_status,
                            pdf_local_path
                        )
                        VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                        """,
                        ("RAW:SAS", "", "{}", source_url, title_text, "SAS", "PENDING", str(pdf_path)),
                    )
                    row_report["downloaded"] = download_status
                    row_report["created"] = "yes"
                    row_report["reason"] = "STAGED_NEW_SAS_PDF"
                    new_rows += 1
                else:
                    row_report["downloaded"] = "planned"
                    row_report["created"] = "yes"
                    row_report["reason"] = "WOULD_STAGE_NEW_SAS_PDF"

                report.append(row_report)

            if dry_run:
                conn.rollback()
            else:
                record_ingestion_log(conn, new_regattas=0, new_results_rows=new_rows, parse_failures=0)
                conn.commit()

    return {
        "summary": {
            "new_regattas": 0,
            "new_results_rows": new_rows,
            "parse_failures": 0,
            "download_failures": failures,
        },
        "rows": report,
    }


def ingest_sas_pdf_sources_to_results_staging(result_items, dry_run: bool = True, apply: bool = False):
    """
    Store raw SAS PDF sources in results_staging without parsing PDFs.

    Rules:
    - source_url is the dedupe key
    - never modify existing rows
    - no regatta/event writes
    - no PDF parsing
    """
    if apply:
        dry_run = False

    report = []
    db_url = _get_db_url()

    with psycopg2.connect(db_url) as conn:
        if not dry_run:
            ensure_results_staging_source_columns(conn)

        with conn.cursor() as cur:
            for item in result_items or []:
                source_url = (item.get("source_url") or "").strip()
                source_title_raw = (item.get("title_text") or "").strip()
                file_name = _file_name_from_item(item)
                if not source_url or not source_title_raw:
                    continue

                cur.execute(
                    """
                    SELECT staging_id
                    FROM public.results_staging
                    WHERE source_url = %s
                    LIMIT 1
                    """,
                    (source_url,),
                )
                existing = cur.fetchone()
                if existing:
                    report.append(
                        {
                            "file_name": file_name,
                            "source_url": source_url,
                            "source_title_raw": source_title_raw,
                            "created": "no",
                        }
                    )
                    continue

                if not dry_run:
                    cur.execute(
                        """
                        INSERT INTO public.results_staging (
                            regatta_id,
                            fleet_label,
                            race_scores,
                            source_url,
                            source_title_raw,
                            source_site,
                            validation_status
                        )
                        VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s)
                        """,
                        ("RAW:SAS", "", "{}", source_url, source_title_raw, "SAS", "PENDING"),
                    )

                report.append(
                    {
                        "file_name": file_name,
                        "source_url": source_url,
                        "source_title_raw": source_title_raw,
                        "created": "yes",
                    }
                )

        if dry_run:
            conn.rollback()
        else:
            conn.commit()

    return report


def detect_new_regattas_from_results(result_items, dry_run: bool = True, apply: bool = False):
    """
    Detect result files that map to existing regattas or require a new pending regatta row.

    Rules:
    - dry_run=True by default
    - apply=False by default
    - no PDF parsing
    - no event matching
    - no updates to existing regattas
    - idempotent: skip existing source_url and existing year/name or year/slug matches
    """
    if apply:
        dry_run = False

    report = []
    db_url = _get_db_url()

    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            optional_cols = _regattas_optional_columns(cur)
            simulated_next = _next_regatta_number(cur)
            club_phrases = _club_phrases_for_title_matching(cur)

            for item in result_items or []:
                title_text = (item.get("title_text") or "").strip()
                source_url = (item.get("source_url") or "").strip()
                file_name = _file_name_from_item(item)

                if not source_url:
                    continue

                year = _extract_year_from_title(title_text or file_name)
                if year is None:
                    continue

                event_name_clean = _clean_event_name_from_result_title(title_text or file_name)
                if not event_name_clean:
                    continue

                existing_by_url = _find_regatta_by_source_url(cur, source_url)
                if existing_by_url:
                    continue

                matched_event_name = _find_matching_event_name(cur, event_name_clean, year, club_phrases)
                if matched_event_name:
                    matched_regatta = _find_existing_regatta_for_result(
                        cur,
                        matched_event_name,
                        year,
                        _slugify_event_name(matched_event_name),
                        club_phrases,
                    )
                    report.append(
                        {
                            "file_name": file_name,
                            "event_name_clean": event_name_clean,
                            "regatta_id": matched_regatta[0] if matched_regatta else "",
                            "created": "no",
                        }
                    )
                    continue

                slug = _slugify_event_name(event_name_clean)
                existing_regatta = _find_existing_regatta_for_result(cur, event_name_clean, year, slug, club_phrases)
                if existing_regatta:
                    report.append(
                        {
                            "file_name": file_name,
                            "event_name_clean": event_name_clean,
                            "regatta_id": existing_regatta[0],
                            "created": "no",
                        }
                    )
                    continue

                if dry_run:
                    regatta_number = simulated_next
                    simulated_next += 1
                    regatta_id = f"{regatta_number}-{year}-{slug}" if slug else f"{regatta_number}-{year}"
                else:
                    cur.execute("LOCK TABLE regattas IN EXCLUSIVE MODE")
                    regatta_number = _next_regatta_number(cur)
                    regatta_id = f"{regatta_number}-{year}-{slug}" if slug else f"{regatta_number}-{year}"

                    insert_cols = [
                        "regatta_id",
                        "regatta_number",
                        "event_name",
                        "year",
                        "source_url",
                        "file_type",
                        "import_status",
                    ]
                    insert_vals = [
                        regatta_id,
                        regatta_number,
                        _display_name_for_new_regatta(event_name_clean, club_phrases),
                        year,
                        source_url,
                        "PDF",
                        "pending",
                    ]
                    if "source_name_raw" in optional_cols:
                        insert_cols.append("source_name_raw")
                        insert_vals.append(title_text)
                    if "slug" in optional_cols:
                        insert_cols.append("slug")
                        insert_vals.append(slug)
                    if "header_status" in optional_cols:
                        insert_cols.append("header_status")
                        insert_vals.append("DRAFT")

                    placeholders = ", ".join(["%s"] * len(insert_cols))
                    cols_sql = ", ".join(insert_cols)
                    cur.execute(
                        f"INSERT INTO regattas ({cols_sql}) VALUES ({placeholders})",
                        tuple(insert_vals),
                    )
                    
                    # --- PROVENANCE TRACKING (graceful, no auto-validate, no auto-truth) ---
                    # Infer source_type from URL + file extension (not authority - that's in provenance layer)
                    inferred_source_type = _infer_source_type_from_url(source_url)
                    
                    # Create artifact (idempotent - won't duplicate if URL exists)
                    artifact_id = create_source_artifact(
                        conn, source_url, inferred_source_type, "scrape_auto",
                        captured_by="detect_new_regattas",
                        parse_notes=f"Auto-detected from {title_text or file_name}"
                    )
                    
                    if artifact_id:
                        # Link regatta to artifact - validation_status='pending_review' (NO auto-validate)
                        # is_original=True, is_primary=True only because this is first source
                        # Truth determination happens later in provenance layer
                        link_regatta_to_artifact(
                            conn, regatta_id, artifact_id,
                            source_scope="regatta",
                            is_original=True,
                            is_primary=True,  # First source is primary by default, can be changed later
                            validation_status="pending_review",  # NO auto-validation
                            created_by="detect_new_regattas",
                            notes="Initial source - pending validation"
                        )
                        
                        # Update regatta with artifact reference (if columns exist)
                        if "original_artifact_id" in optional_cols:
                            cur.execute(
                                "UPDATE regattas SET original_artifact_id = %s WHERE regatta_id = %s",
                                (artifact_id, regatta_id)
                            )
                        if "provenance_status" in optional_cols:
                            cur.execute(
                                "UPDATE regattas SET provenance_status = 'pending_review' WHERE regatta_id = %s",
                                (regatta_id,)
                            )
                    # --- END PROVENANCE TRACKING ---

                report.append(
                    {
                        "file_name": file_name,
                        "event_name_clean": event_name_clean,
                        "regatta_id": regatta_id,
                        "created": "yes",
                    }
                )

        if dry_run:
            conn.rollback()
        else:
            conn.commit()

    return report
