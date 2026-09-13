"""Live-event product PDF: rebuild only when the Event URL data changed.

Cape Classic is the current live event; the same rule applies to every
live / fluid event (end_date or start_date on or after today in
Africa/Johannesburg).

Fingerprint covers fleets, boats, scores, and the Results-are line.
Stored next to the PDF as `.event-truth.sha`. No diff → keep the PDF.
Diff or missing PDF → generate a new one.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from sailingsa.backend.regatta_stored_pdf import pdf_abs_path, pdf_root

STAMP_NAME = ".event-truth.sha"
Query = Callable[..., list]


def today_za():
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Africa/Johannesburg")).date()
    except Exception:
        return datetime.utcnow().date()


def _as_date(raw):
    if raw is None:
        return None
    try:
        if isinstance(raw, datetime):
            return raw.date()
        if hasattr(raw, "year") and hasattr(raw, "month") and hasattr(raw, "day"):
            return raw
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def event_is_live(end_date=None, start_date=None, today=None) -> bool:
    """True while the event is still on (including race day)."""
    today = today or today_za()
    d = _as_date(end_date) or _as_date(start_date)
    if d is None:
        return False
    return d >= today


def _cell(row, key: str, idx: int = 0) -> str:
    if isinstance(row, dict):
        return str(row.get(key) if row.get(key) is not None else "")
    try:
        val = row[idx]
    except Exception:
        val = ""
    return str(val if val is not None else "")


def event_truth_fingerprint(q: Query, rid: str) -> str:
    """Stable hash of what Print/PDF must show for this Event URL.

    Call q(sql, rid) — never q(sql, (rid,)). Live api.q uses *args and
    passing a tuple made the old md5 query return empty forever.
    """
    rid = str(rid or "").strip()
    if not rid or q is None:
        return ""
    parts = [rid]
    try:
        meta = q(
            """
            SELECT COALESCE(result_status::text, '') AS rs,
                   COALESCE(as_at_time::text, '') AS at
            FROM regattas
            WHERE regatta_id::text = %s
            LIMIT 1
            """,
            rid,
        ) or []
        if meta:
            parts.append(_cell(meta[0], "rs", 0))
            parts.append(_cell(meta[0], "at", 1))
        blocks = q(
            """
            SELECT COALESCE(block_id::text, '') AS block_id
            FROM regatta_blocks
            WHERE regatta_id::text = %s
            ORDER BY block_id
            """,
            rid,
        ) or []
        parts.append(",".join(_cell(b, "block_id", 0) for b in blocks))
        rows = q(
            """
            SELECT result_id::text AS result_id,
                   COALESCE(sail_number, '') AS sail_number,
                   COALESCE(helm_name, '') AS helm_name,
                   COALESCE(crew_name, '') AS crew_name,
                   COALESCE(rank::text, '') AS rank,
                   COALESCE(total_points_raw::text, '') AS total_points_raw,
                   COALESCE(nett_points_raw::text, '') AS nett_points_raw,
                   COALESCE(races_sailed::text, '') AS races_sailed,
                   COALESCE(race_scores::text, '') AS race_scores,
                   COALESCE(block_id::text, '') AS block_id,
                   COALESCE(boat_name, '') AS boat_name
            FROM results
            WHERE regatta_id::text = %s
            ORDER BY result_id
            """,
            rid,
        ) or []
        for row in rows:
            parts.append(
                "|".join(
                    [
                        _cell(row, "result_id", 0),
                        _cell(row, "sail_number", 1),
                        _cell(row, "helm_name", 2),
                        _cell(row, "crew_name", 3),
                        _cell(row, "rank", 4),
                        _cell(row, "total_points_raw", 5),
                        _cell(row, "nett_points_raw", 6),
                        _cell(row, "races_sailed", 7),
                        _cell(row, "race_scores", 8),
                        _cell(row, "block_id", 9),
                        _cell(row, "boat_name", 10),
                    ]
                )
            )
    except Exception:
        return ""
    blob = "\n".join(parts).encode("utf-8", "replace")
    return hashlib.md5(blob).hexdigest()


def stamp_path(rid: str) -> Path:
    return pdf_root() / str(rid or "").strip() / STAMP_NAME


def read_stamp(rid: str) -> str:
    path = stamp_path(rid)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def write_stamp(rid: str, fingerprint: str) -> None:
    fp = (fingerprint or "").strip()
    if not fp:
        return
    path = stamp_path(rid)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".sha.tmp")
    tmp.write_text(fp + "\n", encoding="utf-8")
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o644)
    except Exception:
        pass


def parent_pdf_ok(rid: str) -> bool:
    path = pdf_abs_path(rid)
    try:
        return path.is_file() and path.stat().st_size >= 500
    except Exception:
        return False


def needs_rebuild(q: Query, rid: str) -> tuple[bool, str, str]:
    """Return (rebuild?, current_fp, stored_fp)."""
    fp = event_truth_fingerprint(q, rid)
    stored = read_stamp(rid)
    if not fp:
        return True, fp, stored
    if stored != fp:
        return True, fp, stored
    if not parent_pdf_ok(rid):
        return True, fp, stored
    return False, fp, stored


def list_live_parent_ids(q: Query, today=None) -> list[str]:
    """Parent events that are still live and have results rows."""
    today = today or today_za()
    rows = q(
        """
        SELECT r.regatta_id::text AS rid, r.end_date, r.start_date
        FROM regattas r
        WHERE POSITION(':' IN r.regatta_id::text) = 0
          AND EXISTS (
            SELECT 1 FROM results x
            WHERE x.regatta_id::text = r.regatta_id::text
          )
        """
    ) or []
    out = []
    for row in rows:
        rid = _cell(row, "rid", 0)
        if not rid:
            continue
        end_d = row.get("end_date") if isinstance(row, dict) else row[1]
        start_d = row.get("start_date") if isinstance(row, dict) else row[2]
        if event_is_live(end_d, start_d, today=today):
            out.append(rid)
    out.sort()
    return out
