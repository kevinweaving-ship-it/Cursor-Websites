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
from hashlib import sha256
from pathlib import Path
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
