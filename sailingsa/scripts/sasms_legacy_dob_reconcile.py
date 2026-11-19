#!/usr/bin/env python3
"""Reconcile an authorised SAS DOB dataset into public.sas_id_personal.

AUDIT STATUS (2026-11-17)
-------------------------
This module was prepared because no checked-in `sasms_legacy_dob_reconcile.py`
existed on origin/main (cloud + GitHub search). It implements the safety rules
required before any authorised import.

DOES NOT:
- Run the legacy SASMS bulk scraper
- Modify api.py / race results / sailor URLs / landing page
- Write to production unless `--apply` AND `--i-understand-production` are set
- Overwrite existing full date_of_birth values
- Clobber existing year_of_birth on conflict

DOES:
- Match by exact SAS ID, then verify name
- Preserve existing DOB; preserve YOB when DOB unavailable / conflicted
- Flag birth-year and identity discrepancies
- Ignore legacy membership status "Lapsed"
- Dry-run by default; resume via checkpoint JSON
- Require source-file SHA-256 verification against --expected-sha256 when provided
- Write decisions to a local JSONL audit log (and optional staging table SQL)

Live schema (documented; verify with REA SELECT before --apply):
  public.sas_id_personal(
    sa_sailing_id, first_name, last_name, full_name,
    date_of_birth, year_of_birth, club_*_member_status, ...
  )

REA read-only probe (run from Mac / REA ops, not this cloud VM):
  /opt/rea/ops/bin/rea-admin sailingsa -- capabilities
  ops_db query:
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='sas_id_personal'
      AND column_name IN (
        'sa_sailing_id','first_name','last_name','full_name',
        'date_of_birth','year_of_birth'
      )
    ORDER BY ordinal_position;
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# Allow `python3 sailingsa/scripts/sasms_legacy_dob_reconcile.py` from repo root.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from sasms_dob_reconcile_lib import (  # noqa: E402
    DbSailor,
    Decision,
    decide,
    normalize_sas_id,
    parse_date,
    parse_year,
    sha256_file,
    source_from_mapping,
    summarize,
)


def _load_csv(path: Path) -> Iterator[Tuple[int, Dict[str, Any]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header = line 1
            yield i, dict(row)


def _load_json(path: Path) -> Iterator[Tuple[int, Dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    if not isinstance(data, list):
        raise ValueError("JSON dataset must be a list or {records: [...]}")
    for i, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"record {i} is not an object")
        yield i, row


def iter_source(path: Path) -> Iterator[Tuple[int, Dict[str, Any]]]:
    suf = path.suffix.lower()
    if suf == ".csv":
        yield from _load_csv(path)
    elif suf in (".json", ".jsonl"):
        if suf == ".jsonl":
            with path.open(encoding="utf-8") as f:
                for i, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    yield i, json.loads(line)
        else:
            yield from _load_json(path)
    else:
        raise ValueError(f"Unsupported dataset type: {suf} (use .csv / .json / .jsonl)")


def load_checkpoint(path: Optional[Path]) -> Dict[str, Any]:
    if not path or not path.exists():
        return {"completed_sas_ids": [], "last_source_row": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def fetch_sailor(cur, sas_id: str) -> Optional[DbSailor]:
    cur.execute(
        """
        SELECT sa_sailing_id::text,
               COALESCE(first_name, ''),
               COALESCE(last_name, ''),
               COALESCE(full_name, ''),
               date_of_birth,
               year_of_birth
        FROM public.sas_id_personal
        WHERE sa_sailing_id::text = %s
        LIMIT 1
        """,
        (sas_id,),
    )
    row = cur.fetchone()
    if not row:
        # Exact match only — do not fuzzy or zero-pad fall back.
        return None
    return DbSailor(
        sas_id=normalize_sas_id(row[0]),
        first_name=row[1] or "",
        last_name=row[2] or "",
        full_name=row[3] or "",
        date_of_birth=parse_date(row[4]),
        year_of_birth=parse_year(row[5]),
    )


def apply_decision(cur, decision: Decision) -> None:
    """Apply only DOB/YOB columns. Never touches names, clubs, results, or status.

    Defence in depth: SQL guards refuse overwrites even if a Decision were wrong.
    """
    if decision.action != "apply":
        return

    if decision.set_date_of_birth is not None:
        params: List[Any] = [decision.set_date_of_birth]
        sets = ["date_of_birth = %s"]
        # Only set YOB when currently NULL (never clobber a preserved YOB).
        if decision.set_year_of_birth is not None:
            sets.append("year_of_birth = COALESCE(year_of_birth, %s)")
            params.append(decision.set_year_of_birth)
        params.append(decision.sas_id)
        cur.execute(
            f"""
            UPDATE public.sas_id_personal
            SET {", ".join(sets)}
            WHERE sa_sailing_id::text = %s
              AND date_of_birth IS NULL
            """,
            tuple(params),
        )
        if cur.rowcount != 1:
            raise RuntimeError(
                f"refusing DOB apply for {decision.sas_id}: "
                f"expected 1 row with NULL dob, got {cur.rowcount}"
            )
        return

    if decision.set_year_of_birth is not None:
        cur.execute(
            """
            UPDATE public.sas_id_personal
            SET year_of_birth = %s
            WHERE sa_sailing_id::text = %s
              AND year_of_birth IS NULL
              AND date_of_birth IS NULL
            """,
            (decision.set_year_of_birth, decision.sas_id),
        )
        if cur.rowcount != 1:
            raise RuntimeError(
                f"refusing YOB apply for {decision.sas_id}: "
                f"expected 1 empty-birth row, got {cur.rowcount}"
            )


def connect(db_url: str):
    try:
        import psycopg2
    except ImportError as e:
        raise SystemExit("psycopg2 required for DB mode") from e
    return psycopg2.connect(db_url)


def run(args: argparse.Namespace) -> int:
    dataset = Path(args.dataset)
    if not dataset.is_file():
        print(f"ERROR: dataset not found: {dataset}", file=sys.stderr)
        return 2

    apply = bool(args.apply)
    # Refuse production writes before any hashing/IO side paths beyond existence check.
    if apply and not args.i_understand_production:
        print(
            "ERROR: --apply requires --i-understand-production "
            "(refusing production writes)",
            file=sys.stderr,
        )
        return 4
    if apply and not args.expected_sha256:
        print(
            "ERROR: --apply requires --expected-sha256 for source verification",
            file=sys.stderr,
        )
        return 5

    digest = sha256_file(str(dataset))
    print(f"source_sha256={digest}")
    if args.expected_sha256:
        exp = args.expected_sha256.strip().lower()
        if digest.lower() != exp:
            print(
                f"ERROR: source SHA-256 mismatch (expected {exp})",
                file=sys.stderr,
            )
            return 3
        print("source_sha256_verified=true")
    else:
        print("source_sha256_verified=false (pass --expected-sha256 to require)")

    checkpoint_path = Path(args.checkpoint) if args.checkpoint else None
    ckpt = load_checkpoint(checkpoint_path)
    done = set(ckpt.get("completed_sas_ids") or [])

    audit_path = Path(args.audit_log)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    db_url = args.db_url or os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    offline = bool(args.offline_db_json)
    conn = cur = None
    offline_index: Dict[str, DbSailor] = {}

    if offline:
        raw = json.loads(Path(args.offline_db_json).read_text(encoding="utf-8"))
        for item in raw:
            s = DbSailor(
                sas_id=normalize_sas_id(item.get("sa_sailing_id") or item.get("sas_id")),
                first_name=str(item.get("first_name") or ""),
                last_name=str(item.get("last_name") or ""),
                full_name=str(item.get("full_name") or ""),
                date_of_birth=parse_date(item.get("date_of_birth")),
                year_of_birth=parse_year(item.get("year_of_birth")),
            )
            offline_index[s.sas_id] = s
    else:
        if not db_url:
            print(
                "ERROR: DB_URL/DATABASE_URL or --offline-db-json required",
                file=sys.stderr,
            )
            return 6
        if apply:
            conn = connect(db_url)
        else:
            # Dry-run still reads live/dev DB when URL provided.
            conn = connect(db_url)
        cur = conn.cursor()

    decisions: List[Decision] = []
    with audit_path.open("a", encoding="utf-8") as audit_f:
        meta = {
            "event": "run_start",
            "dataset": str(dataset),
            "source_sha256": digest,
            "apply": apply,
            "offline": offline,
        }
        audit_f.write(json.dumps(meta) + "\n")

        for row_num, row in iter_source(dataset):
            if row_num <= int(ckpt.get("last_source_row") or 0) and args.resume:
                continue
            src = source_from_mapping(row, row_num=row_num)
            if not src.sas_id:
                continue
            if args.resume and src.sas_id in done:
                continue

            if offline:
                sailor = offline_index.get(src.sas_id)
            else:
                assert cur is not None
                sailor = fetch_sailor(cur, src.sas_id)

            decision = decide(src, sailor)
            decisions.append(decision)
            audit_f.write(json.dumps(decision.to_dict()) + "\n")

            if apply and decision.action == "apply":
                assert cur is not None and conn is not None
                try:
                    apply_decision(cur, decision)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"ERROR applying {decision.sas_id}: {e}", file=sys.stderr)
                    audit_f.write(
                        json.dumps(
                            {
                                "event": "apply_error",
                                "sas_id": decision.sas_id,
                                "error": str(e),
                            }
                        )
                        + "\n"
                    )
                    return 7

            done.add(src.sas_id)
            ckpt["completed_sas_ids"] = sorted(done)
            ckpt["last_source_row"] = row_num
            ckpt["source_sha256"] = digest
            if checkpoint_path:
                save_checkpoint(checkpoint_path, ckpt)

    if conn is not None:
        cur.close()
        conn.close()

    summary = summarize(decisions)
    print(json.dumps({"summary": summary, "rows": len(decisions), "apply": apply}, indent=2))
    print(
        "NOTE: production data was "
        + ("UPDATED for apply actions only" if apply else "NOT modified (dry-run)")
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Authorised SAS DOB reconcile (dry-run default; no scraper)"
    )
    p.add_argument("--dataset", required=True, help="Authorised CSV/JSON/JSONL dataset")
    p.add_argument("--expected-sha256", default="", help="Require this source digest")
    p.add_argument("--db-url", default="", help="Postgres URL (else DB_URL/DATABASE_URL)")
    p.add_argument(
        "--offline-db-json",
        default="",
        help="Fixture JSON of sas_id_personal rows (no live DB)",
    )
    p.add_argument(
        "--audit-log",
        default="sailingsa/scripts/.sasms_dob_audit.jsonl",
        help="Append-only JSONL decision log",
    )
    p.add_argument(
        "--checkpoint",
        default="sailingsa/scripts/.sasms_dob_checkpoint.json",
        help="Resume checkpoint path",
    )
    p.add_argument("--resume", action="store_true", help="Skip completed SAS IDs / rows")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write DOB/YOB fills (still never overwrites existing DOB)",
    )
    p.add_argument(
        "--i-understand-production",
        action="store_true",
        help="Required together with --apply",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
