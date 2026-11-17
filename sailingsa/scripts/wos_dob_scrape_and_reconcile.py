#!/usr/bin/env python3
"""Scrape WorldOfSailors date_of_birth for linked SAS IDs and reconcile into sas_id_personal.

Source: https://worldofsailors.com/sailor/{ssl_profile_slug}
Match: exact sa_sailing_id + name verify.
Rules: never overwrite existing DOB; only fill when source year matches existing YOB
       (or YOB empty); flag conflicts; update age from DOB when filled.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from sasms_dob_reconcile_lib import (  # noqa: E402
    DbSailor,
    SourceRecord,
    decide,
    normalize_sas_id,
    parse_date,
    parse_year,
)

UA = "SailingSA-WoS-DOB/1.0 (+https://sailingsa.co.za)"
WOS = "https://worldofsailors.com/sailor/"


def fetch(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_wos_dob(html: str) -> tuple[Optional[date], Optional[str]]:
    """Return (date_of_birth, display_name) from WoS HTML / embedded JSON."""
    # WoS embeds escaped JSON: date_of_birth\":\"YYYY-MM-DD\"  or null
    m = re.search(r'date_of_birth\\":\\"(null|\d{4}-\d{2}-\d{2})\\"', html)
    if not m:
        m = re.search(r'"date_of_birth"\s*:\s*"(null|\d{4}-\d{2}-\d{2})"', html)
    dob = None
    if m and m.group(1) != "null":
        dob = parse_date(m.group(1))

    name = None
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html, re.I)
    if og:
        name = og.group(1).split("|")[0].strip()
    if not name:
        nm = re.search(r'og:title" content="([^"]+)"', html, re.I)
        if nm:
            name = nm.group(1).split("|")[0].strip()
    return dob, name


def db_connect(url: str):
    import psycopg2

    return psycopg2.connect(url)


def load_targets(cur, only_missing: bool, limit: int) -> list[dict[str, Any]]:
    where = [
        "ssl_profile_slug IS NOT NULL",
        "btrim(ssl_profile_slug) <> ''",
        "sa_sailing_id ~ '^[0-9]+$'",
    ]
    if only_missing:
        where.append("date_of_birth IS NULL")
    sql = f"""
        SELECT sa_sailing_id::text,
               COALESCE(first_name,''),
               COALESCE(last_name,''),
               COALESCE(full_name,''),
               date_of_birth,
               year_of_birth,
               btrim(ssl_profile_slug)
        FROM public.sas_id_personal
        WHERE {' AND '.join(where)}
        ORDER BY sa_sailing_id::int
    """
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    cur.execute(sql)
    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "sas_id": normalize_sas_id(r[0]),
                "first_name": r[1],
                "last_name": r[2],
                "full_name": r[3],
                "date_of_birth": parse_date(r[4]),
                "year_of_birth": parse_year(r[5]),
                "slug": r[6],
            }
        )
    return rows


def apply_fill(cur, sas_id: str, dob: date) -> int:
    cur.execute(
        """
        UPDATE public.sas_id_personal
        SET date_of_birth = %s,
            year_of_birth = COALESCE(year_of_birth, %s),
            age = EXTRACT(YEAR FROM AGE(%s))::int
        WHERE sa_sailing_id::text = %s
          AND date_of_birth IS NULL
          AND (year_of_birth IS NULL OR year_of_birth = %s)
        """,
        (dob, dob.year, dob, sas_id, dob.year),
    )
    return cur.rowcount


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db-url", default=os.environ.get("DB_URL") or os.environ.get("DATABASE_URL") or "")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delay", type=float, default=0.35)
    p.add_argument("--all-linked", action="store_true", help="Include sailors who already have DOB")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--audit", default="/tmp/wos_dob_audit.jsonl")
    args = p.parse_args(argv)
    if not args.db_url:
        print("DB_URL required", file=sys.stderr)
        return 2

    conn = db_connect(args.db_url)
    cur = conn.cursor()
    targets = load_targets(cur, only_missing=not args.all_linked, limit=args.limit)
    print(f"targets={len(targets)} apply={bool(args.apply)}")

    summary = {
        "fetched": 0,
        "wos_dob": 0,
        "wos_null": 0,
        "http_err": 0,
        "apply": 0,
        "flag": 0,
        "noop": 0,
        "skip": 0,
        "ignore": 0,
        "apply_rows": 0,
    }

    with open(args.audit, "a", encoding="utf-8") as audit:
        audit.write(json.dumps({"event": "start", "n": len(targets), "apply": args.apply, "ts": datetime.utcnow().isoformat() + "Z"}) + "\n")
        for i, t in enumerate(targets, 1):
            url = WOS + t["slug"]
            try:
                html = fetch(url)
                summary["fetched"] += 1
            except Exception as e:
                summary["http_err"] += 1
                audit.write(json.dumps({"event": "http_err", "sas_id": t["sas_id"], "slug": t["slug"], "error": str(e)}) + "\n")
                time.sleep(args.delay)
                continue

            dob, wos_name = parse_wos_dob(html)
            if dob is None:
                summary["wos_null"] += 1
                audit.write(json.dumps({"event": "wos_null", "sas_id": t["sas_id"], "slug": t["slug"], "wos_name": wos_name}) + "\n")
                time.sleep(args.delay)
                continue
            summary["wos_dob"] += 1

            src = SourceRecord(
                sas_id=t["sas_id"],
                first_name=t["first_name"],
                last_name=t["last_name"],
                full_name=wos_name or t["full_name"],
                date_of_birth=dob,
                year_of_birth=dob.year,
                source_row=i,
            )
            sailor = DbSailor(
                sas_id=t["sas_id"],
                first_name=t["first_name"],
                last_name=t["last_name"],
                full_name=t["full_name"],
                date_of_birth=t["date_of_birth"],
                year_of_birth=t["year_of_birth"],
            )
            # If WoS name empty, still verify against our stored name by feeding stored full_name as source too
            if not wos_name:
                src = SourceRecord(
                    sas_id=t["sas_id"],
                    first_name=t["first_name"],
                    last_name=t["last_name"],
                    full_name=t["full_name"],
                    date_of_birth=dob,
                    year_of_birth=dob.year,
                    source_row=i,
                )

            d = decide(src, sailor)
            summary[d.action] = summary.get(d.action, 0) + 1
            rec = d.to_dict()
            rec["slug"] = t["slug"]
            rec["wos_name"] = wos_name
            audit.write(json.dumps(rec) + "\n")

            if args.apply and d.action == "apply" and d.set_date_of_birth is not None:
                n = apply_fill(cur, t["sas_id"], d.set_date_of_birth)
                if n == 1:
                    conn.commit()
                    summary["apply_rows"] += 1
                else:
                    conn.rollback()
                    audit.write(json.dumps({"event": "apply_miss", "sas_id": t["sas_id"], "rowcount": n}) + "\n")

            if i % 25 == 0:
                print(f"progress {i}/{len(targets)} {summary}", flush=True)
            time.sleep(args.delay)

    cur.close()
    conn.close()
    print(json.dumps({"summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
