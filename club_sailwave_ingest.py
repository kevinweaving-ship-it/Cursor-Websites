#!/usr/bin/env python3
"""Sailwave published HTML/CSV parser for club ingest. Wraps results_ingestion_common."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

def _ingest_common():
    from results_ingestion_common import (
        get_class_name_by_id,
        record_ingestion_issue,
        resolve_class_id,
        resolve_helm_to_sa_id,
    )
    return resolve_class_id, get_class_name_by_id, resolve_helm_to_sa_id, record_ingestion_issue

MAX_BYTES = 2 * 1024 * 1024
REJECT_EXT = {".blw", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".exe", ".dll", ".zip", ".bin"}
SCORE_CODES = {
    "DNC", "DNF", "DNS", "OCS", "BFD", "UFD", "DSQ", "RET", "RAF", "DPI", "RDG", "SCP", "ZFP", "NSC", "DNE",
}
HEADER_ALIASES = {
    "rank": "rank",
    "pos": "rank",
    "place": "rank",
    "sailno": "sail_number",
    "sail": "sail_number",
    "sail_number": "sail_number",
    "sail number": "sail_number",
    "helmname": "helm_name",
    "helm": "helm_name",
    "helm name": "helm_name",
    "skipper": "helm_name",
    "crewname": "crew_name",
    "crew": "crew_name",
    "class": "class_label",
    "fleet": "class_label",
    "club": "club_raw",
    "total": "total",
    "nett": "nett",
    "net": "nett",
    "pts": "total",
}


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_filename(name: str) -> str | None:
    ext = Path(name or "").suffix.lower()
    if ext in REJECT_EXT:
        return "Unsupported file type"
    return None


def sniff_kind(name: str, data: bytes) -> str:
    ext = Path(name or "").suffix.lower()
    head = data.lstrip()[:200].lower()
    if ext in (".html", ".htm") or head.startswith(b"<") or b"<html" in head or b"<table" in head:
        return "html"
    return "csv"


def format_race_score(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text or text in (".", "-", "—"):
        return None
    discarded = False
    if text.startswith("(") and text.endswith(")"):
        discarded = True
        text = text[1:-1].strip()
    elif text.startswith("-") and re.match(r"^-[\d.]+$", text):
        discarded = True
        text = text[1:]
    up = text.upper()
    if up in SCORE_CODES:
        out = up
    elif re.match(r"^-?\d+(\.\d+)?$", text):
        out = "%.1f" % float(text)
    else:
        out = text
    return "(%s)" % out if discarded else out


def score_numeric(raw: str | None):
    if raw is None:
        return None
    text = str(raw).strip().strip("()")
    try:
        return float(text)
    except ValueError:
        return None


def _norm_header(cell: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (cell or "").strip().lower())


def _map_header(cell: str):
    raw = (cell or "").strip()
    key = _norm_header(raw)
    if key in ("r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10",
               "r11", "r12", "r13", "r14", "r15", "r16", "r17", "r18", "r19", "r20"):
        return ("race", int(key[1:]))
    if re.fullmatch(r"r\d+", key):
        return ("race", int(key[1:]))
    if re.fullmatch(r"\d+", key) and 1 <= int(key) <= 30:
        return ("race", int(key))
    alias = HEADER_ALIASES.get(re.sub(r"\s+", " ", raw.lower()).strip()) or HEADER_ALIASES.get(key)
    if alias:
        return (alias, None)
    return None


def _looks_like_header(cells) -> bool:
    mapped = [_map_header(c) for c in cells]
    kinds = {m[0] for m in mapped if m}
    return "sail_number" in kinds and ("helm_name" in kinds or "rank" in kinds)


class _TableHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = ""
        self._heading_buf = []
        self._in_heading = False
        self._in_cell = False
        self._cell_buf = []
        self._row = []
        self._table = None
        self.tables = []  # list of {heading, rows}

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4", "caption"):
            self._in_heading = True
            self._heading_buf = []
        elif tag == "table":
            self._table = {"heading": self.heading, "rows": []}
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._table is not None:
            self._in_cell = True
            self._cell_buf = []
        elif tag == "br" and self._in_cell:
            self._cell_buf.append(" ")

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4", "caption") and self._in_heading:
            self.heading = re.sub(r"\s+", " ", "".join(self._heading_buf)).strip()
            self._in_heading = False
        elif tag in ("td", "th") and self._in_cell:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell_buf)).strip())
            self._in_cell = False
        elif tag == "tr" and self._table is not None:
            if any(self._row):
                self._table["rows"].append(self._row)
            self._row = []
        elif tag == "table" and self._table is not None:
            if self._table["rows"]:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._in_heading:
            self._heading_buf.append(data)
        elif self._in_cell:
            self._cell_buf.append(data)


def _class_candidates(label: str):
    raw = re.sub(r"\s+", " ", (label or "").strip())
    if not raw:
        return []
    out = [raw]
    stripped = re.sub(r"\s+(fleet|class|results)$", "", raw, flags=re.I).strip()
    if stripped and stripped not in out:
        out.append(stripped)
    return out


def _rows_from_table(heading: str, rows: list[list[str]]) -> list[dict]:
    header_i = None
    mapping = []
    for i, row in enumerate(rows[:8]):
        if _looks_like_header(row):
            header_i = i
            mapping = [_map_header(c) for c in row]
            break
    if header_i is None:
        return []
    parsed = []
    for row in rows[header_i + 1 :]:
        item = {
            "rank": None,
            "sail_number": "",
            "helm_name": "",
            "crew_name": "",
            "class_label": heading,
            "club_raw": "",
            "race_scores": {},
            "total": None,
            "nett": None,
        }
        races = {}
        for idx, cell in enumerate(row):
            if idx >= len(mapping) or mapping[idx] is None:
                continue
            kind, extra = mapping[idx]
            if kind == "race":
                score = format_race_score(cell)
                if score is not None:
                    races["R%s" % extra] = score
            elif kind == "rank":
                try:
                    item["rank"] = int(float(cell))
                except ValueError:
                    item["rank"] = None
            elif kind in ("sail_number", "helm_name", "crew_name", "class_label", "club_raw"):
                if cell:
                    item[kind] = cell
            elif kind == "total":
                item["total"] = score_numeric(cell)
            elif kind == "nett":
                item["nett"] = score_numeric(cell)
        if not item["helm_name"] and not item["sail_number"]:
            continue
        # sequential R keys
        if races:
            max_n = max(int(k[1:]) for k in races)
            item["race_scores"] = {"R%s" % n: races["R%s" % n] for n in range(1, max_n + 1) if "R%s" % n in races}
        parsed.append(item)
    return parsed


def parse_html(text: str) -> list[dict]:
    parser = _TableHTML()
    parser.feed(text)
    parser.close()
    rows = []
    for table in parser.tables:
        rows.extend(_rows_from_table(table.get("heading") or "", table.get("rows") or []))
    return rows


def parse_csv(text: str) -> list[dict]:
    sample = text.lstrip("\ufeff")
    try:
        dialect = csv.Sniffer().sniff(sample[:4000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(sample), dialect)
    rows = [list(r) for r in reader]
    return _rows_from_table("", rows)


def parse_upload(filename: str, data: bytes) -> tuple[str, list[dict]]:
    kind = sniff_kind(filename, data)
    text = data.decode("utf-8", "replace")
    if kind == "html":
        return kind, parse_html(text)
    return kind, parse_csv(text)


def sheet_as_at(text: str):
    match = re.search(
        r"as at\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})(?:\s+at\s+(\d{1,2}):(\d{2}))?",
        text,
        re.I,
    )
    if not match:
        return None
    day, month, year = int(match.group(1)), match.group(2), int(match.group(3))
    hour = int(match.group(4) or 12)
    minute = int(match.group(5) or 0)
    try:
        dt = datetime.strptime("%02d %s %04d %02d:%02d" % (day, month, year, hour, minute), "%d %B %Y %H:%M")
    except ValueError:
        try:
            dt = datetime.strptime("%02d %s %04d %02d:%02d" % (day, month, year, hour, minute), "%d %b %Y %H:%M")
        except ValueError:
            return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def checksum_row(row: dict) -> list[str]:
    warnings = []
    scores = [score_numeric(v) for v in (row.get("race_scores") or {}).values()]
    if any(v is None for v in scores) or not scores:
        return warnings
    total_sum = sum(scores)
    nett_sum = 0.0
    for raw in (row.get("race_scores") or {}).values():
        num = score_numeric(raw)
        if num is None:
            continue
        if str(raw).startswith("("):
            continue
        nett_sum += num
    if row.get("total") is not None and abs(total_sum - float(row["total"])) > 0.05:
        warnings.append("total mismatch")
    if row.get("nett") is not None and abs(nett_sum - float(row["nett"])) > 0.05:
        warnings.append("nett mismatch")
    return warnings


def resolve_label(cur, label: str):
    resolve_class_id, get_class_name_by_id, _helm, _issue = _ingest_common()
    for cand in _class_candidates(label):
        cid = resolve_class_id(cur, cand)
        if cid is not None:
            return cid, get_class_name_by_id(cur, cid) or cand, cand
    return None, None, label


def preview_payload(cur, rid: str, filename: str, data: bytes) -> dict:
    kind, rows = parse_upload(filename, data)
    fleets = {}
    unknown = []
    unmatched = []
    warnings = []
    out_rows = []
    as_at = sheet_as_at(data.decode("utf-8", "replace"))
    for row in rows:
        cid, cname, used = resolve_label(cur, row.get("class_label") or "")
        warn = checksum_row(row)
        warnings.extend("%s %s: %s" % (row.get("sail_number"), row.get("helm_name"), w) for w in warn)
        block_id = None
        result_id = None
        if cid is None:
            unknown.append(row.get("class_label") or "")
        else:
            cur.execute(
                """
                SELECT block_id FROM public.regatta_blocks
                WHERE regatta_id::text = %s AND class_id = %s
                LIMIT 1
                """,
                (rid, cid),
            )
            brow = cur.fetchone()
            if brow:
                block_id = brow["block_id"] if isinstance(brow, dict) else brow[0]
                cur.execute(
                    """
                    SELECT result_id FROM public.results
                    WHERE regatta_id::text = %s AND block_id = %s
                      AND LOWER(TRIM(COALESCE(sail_number,''))) = LOWER(TRIM(%s))
                      AND LOWER(TRIM(COALESCE(helm_name,''))) = LOWER(TRIM(%s))
                    LIMIT 1
                    """,
                    (rid, block_id, row.get("sail_number") or "", row.get("helm_name") or ""),
                )
                rrow = cur.fetchone()
                if rrow:
                    result_id = int(rrow["result_id"] if isinstance(rrow, dict) else rrow[0])
            key = cname or used
            fleets.setdefault(key, {"class_id": cid, "class_name": cname, "rows": 0, "matched": 0})
            fleets[key]["rows"] += 1
            if result_id:
                fleets[key]["matched"] += 1
            else:
                unmatched.append(
                    {"helm_name": row.get("helm_name"), "sail_number": row.get("sail_number"), "class": cname or used}
                )
        out_rows.append(
            {
                "rank": row.get("rank"),
                "sail_number": row.get("sail_number"),
                "helm_name": row.get("helm_name"),
                "class_label": row.get("class_label"),
                "class_id": cid,
                "block_id": block_id,
                "result_id": result_id,
                "race_scores": row.get("race_scores"),
                "total": row.get("total"),
                "nett": row.get("nett"),
            }
        )
    return {
        "ok": True,
        "file_type": kind,
        "doc_hash": file_sha256(data),
        "preview_token": file_sha256(data),
        "as_at_time": as_at,
        "fleets": list(fleets.values()),
        "rows": out_rows,
        "unknown_classes": sorted({u for u in unknown if u}),
        "unmatched_sailors": unmatched,
        "warnings": warnings,
        "count": len(out_rows),
    }


def _find_existing(cur, rid, block_id, row, helm_sas):
    cur.execute(
        """
        SELECT result_id FROM public.results
        WHERE regatta_id::text = %s AND block_id = %s
          AND LOWER(TRIM(COALESCE(sail_number,''))) = LOWER(TRIM(%s))
          AND LOWER(TRIM(COALESCE(helm_name,''))) = LOWER(TRIM(%s))
        LIMIT 1
        """,
        (rid, block_id, row.get("sail_number") or "", row.get("helm_name") or ""),
    )
    found = cur.fetchone()
    if found:
        return int(found["result_id"] if isinstance(found, dict) else found[0])
    if helm_sas is not None:
        cur.execute(
            """
            SELECT result_id FROM public.results
            WHERE regatta_id::text = %s AND block_id = %s
              AND helm_sa_sailing_id::text = %s
            LIMIT 1
            """,
            (rid, block_id, str(helm_sas)),
        )
        found = cur.fetchone()
        if found:
            return int(found["result_id"] if isinstance(found, dict) else found[0])
    return None


def commit_payload(conn, cur, *, rid, filename, data, preview_token, imported_by, as_at_fallback, insert_block):
    expected = file_sha256(data)
    if str(preview_token or "").strip() != expected:
        raise ValueError("preview_token does not match file")
    kind, rows = parse_upload(filename, data)
    if not rows:
        raise ValueError("No result rows in file")
    as_at = sheet_as_at(data.decode("utf-8", "replace")) or as_at_fallback
    added = 0
    updated = 0
    skipped_fleets = []
    applied = []
    by_label = {}
    for row in rows:
        by_label.setdefault(row.get("class_label") or "", []).append(row)

    for label, group in by_label.items():
        cid, cname, used = resolve_label(cur, label)
        if cid is None:
            _resolve, _name, _helm, record_ingestion_issue = _ingest_common()
            record_ingestion_issue(cur, rid, filename, label or "(blank)", {"rows": len(group)}, "OPEN")
            skipped_fleets.append(label or "(blank)")
            continue
        cur.execute("SELECT is_race_class FROM public.classes WHERE class_id = %s LIMIT 1", (cid,))
        crow = cur.fetchone()
        is_race = True
        if crow is not None:
            is_race = crow["is_race_class"] if isinstance(crow, dict) else crow[0]
        if is_race is False:
            _resolve, _name, _helm, record_ingestion_issue = _ingest_common()
            record_ingestion_issue(cur, rid, filename, label or used, {"class_id": cid}, "OPEN")
            skipped_fleets.append(label or used)
            continue
        cur.execute(
            """
            SELECT block_id FROM public.regatta_blocks
            WHERE regatta_id::text = %s AND class_id = %s
            LIMIT 1
            """,
            (rid, cid),
        )
        brow = cur.fetchone()
        if brow:
            block_id = brow["block_id"] if isinstance(brow, dict) else brow[0]
        else:
            block_id = insert_block(cur, rid, cid, cname or used)
        for row in group:
            # Do not call resolve_helm_to_sa_id here: live API role cannot read sailor_helm_aliases.
            helm_sas = None
            result_id = _find_existing(cur, rid, block_id, row, helm_sas)
            scores = json.dumps(row.get("race_scores") or {})
            if result_id:
                cur.execute(
                    """
                    UPDATE public.results
                    SET race_scores = %s::jsonb,
                        rank = %s,
                        total_points_raw = %s,
                        nett_points_raw = %s,
                        raced = TRUE,
                        as_at_time = %s,
                        entry_source = COALESCE(entry_source, 'sailwave_ingest')
                    WHERE result_id = %s AND regatta_id::text = %s
                    """,
                    (
                        scores,
                        row.get("rank"),
                        row.get("total"),
                        row.get("nett"),
                        as_at,
                        result_id,
                        rid,
                    ),
                )
                if helm_sas is not None:
                    cur.execute(
                        """
                        UPDATE public.results
                        SET helm_sa_sailing_id = COALESCE(helm_sa_sailing_id, %s)
                        WHERE result_id = %s
                        """,
                        (helm_sas, result_id),
                    )
                updated += 1
                action = "updated"
            else:
                cur.execute(
                    """
                    INSERT INTO public.results (
                        regatta_id, block_id, class_original, class_canonical, fleet_label, class_id,
                        sail_number, helm_name, helm_sa_sailing_id, crew_name, club_raw,
                        rank, raced, race_scores, total_points_raw, nett_points_raw,
                        as_at_time, entry_source
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, TRUE, %s::jsonb, %s, %s,
                        %s, 'sailwave_ingest'
                    )
                    RETURNING result_id
                    """,
                    (
                        rid,
                        block_id,
                        cname or used,
                        cname or used,
                        cname or used,
                        cid,
                        row.get("sail_number") or "",
                        row.get("helm_name") or "",
                        helm_sas,
                        row.get("crew_name") or "",
                        row.get("club_raw") or "",
                        row.get("rank"),
                        scores,
                        row.get("total"),
                        row.get("nett"),
                        as_at,
                    ),
                )
                nrow = cur.fetchone()
                result_id = int(nrow["result_id"] if isinstance(nrow, dict) else nrow[0])
                added += 1
                action = "inserted"
            applied.append({"result_id": result_id, "action": action, "sail_number": row.get("sail_number")})

    if not applied:
        raise ValueError("No fleets applied" + ("; unknown: %s" % ", ".join(skipped_fleets) if skipped_fleets else ""))

    cur.execute(
        """
        UPDATE public.regattas
        SET file_type = %s, doc_hash = %s, as_at_time = %s
        WHERE regatta_id = %s
        """,
        (kind, expected, as_at, rid),
    )
    cur.execute(
        """
        INSERT INTO public.imports_log
            (regatta_id, source_file, imported_by, rows_added, rows_updated, errors_found, version, notes)
        VALUES (%s, %s, %s, %s, %s, %s, 'club_sailwave', %s)
        """,
        (
            rid,
            filename,
            imported_by,
            added,
            updated,
            len(skipped_fleets),
            "skipped_fleets=%s" % ",".join(skipped_fleets) if skipped_fleets else None,
        ),
    )
    return {
        "ok": True,
        "regatta_id": rid,
        "file_type": kind,
        "doc_hash": expected,
        "as_at_time": as_at,
        "rows_added": added,
        "rows_updated": updated,
        "skipped_fleets": skipped_fleets,
        "applied": applied,
    }


def cli(argv=None):
    import argparse
    import os
    import psycopg2
    import psycopg2.extras

    parser = argparse.ArgumentParser(description="Preview a Sailwave HTML/CSV file")
    parser.add_argument("file")
    parser.add_argument("--regatta-id", default="")
    args = parser.parse_args(argv)
    data = Path(args.file).read_bytes()
    kind, rows = parse_upload(Path(args.file).name, data)
    print(json.dumps({"file_type": kind, "count": len(rows), "doc_hash": file_sha256(data)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
