#!/usr/bin/env python3
"""Scrape full DOB from SASMS mobisearch and reconcile into sas_id_personal.

Source: https://sasms.sasailing.co.za/mobisearch
Result line example:
  SAS ID: 504, Name: Calvin Gibbs, DOB: 1999/03/20, License Status: Lapsed

License Status (incl. Lapsed) is ignored for DOB purposes.
Match: exact SAS ID + name verify. Never overwrite existing DOB.
Fill DOB when source year matches existing YOB (or YOB empty); update age.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
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

SASMS_URL = "https://sasms.sasailing.co.za/mobisearch"
UA = "SailingSA-SASMS-DOB/1.0 (+https://sailingsa.co.za)"
RESULT_RE = re.compile(
    r"SAS ID:\s*(\d+)\s*,\s*Name:\s*([^,]+?)\s*,\s*DOB:\s*([^,]+?)\s*,\s*License Status:\s*(\w+)",
    re.I,
)


def _inputs(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r"<input([^>]+)>", html, re.I):
        tag = m.group(1)
        nm = re.search(r'name="([^"]*)"', tag, re.I)
        val = re.search(r'value="([^"]*)"', tag, re.I)
        if nm:
            out[nm.group(1)] = val.group(1) if val else ""
    return out


class SasmsClient:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def _get(self) -> str:
        req = urllib.request.Request(SASMS_URL, headers={"User-Agent": UA})
        with self.opener.open(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")

    def search(self, sas_id: str, year: str = "") -> Optional[dict[str, Any]]:
        html = self._get()
        fields = _inputs(html)
        for k in list(fields):
            if k.endswith("$txtSASID"):
                fields[k] = str(sas_id)
            elif k.endswith("$txtFirstName"):
                fields[k] = ""
            elif k.endswith("$txtLastName"):
                fields[k] = ""
            elif k.endswith("$txtYear"):
                fields[k] = str(year)
            elif k.endswith("$btnSearchMember"):
                fields[k] = "Search"
        if not any(k.endswith("$btnSearchMember") for k in fields):
            fields[
                "ctl00$ctl00$ContentPlaceHolderDefault$ctl02$MobileSearchSASMember_2$btnSearchMember"
            ] = "Search"
        data = urllib.parse.urlencode(fields).encode()
        req = urllib.request.Request(
            SASMS_URL,
            data=data,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": SASMS_URL,
            },
        )
        with self.opener.open(req, timeout=40) as r:
            body = r.read().decode("utf-8", "replace")
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text)
        m = RESULT_RE.search(text)
        if not m:
            return None
        dob = parse_date(m.group(3).strip().replace("/", "-"))
        # parse_date may not like YYYY/MM/DD after replace — handle slash form
        if dob is None:
            raw = m.group(3).strip()
            for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    dob = datetime.strptime(raw, fmt).date()
                    break
                except ValueError:
                    pass
        return {
            "sas_id": normalize_sas_id(m.group(1)),
            "full_name": m.group(2).strip(),
            "date_of_birth": dob,
            "license_status": m.group(4).strip(),  # ignored for DOB decisions
            "raw": m.group(0),
        }


def db_connect(url: str):
    import psycopg2

    return psycopg2.connect(url)


def load_targets(cur, only_missing: bool, limit: int, start_after: str = "") -> list[dict]:
    where = ["sa_sailing_id ~ '^[0-9]+$'"]
    if only_missing:
        where.append("date_of_birth IS NULL")
    params: list[Any] = []
    if start_after:
        where.append("sa_sailing_id::int > %s")
        params.append(int(start_after))
    sql = f"""
        SELECT sa_sailing_id::text,
               COALESCE(first_name,''),
               COALESCE(last_name,''),
               COALESCE(full_name,''),
               date_of_birth,
               year_of_birth
        FROM public.sas_id_personal
        WHERE {' AND '.join(where)}
        ORDER BY sa_sailing_id::int
    """
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    cur.execute(sql, params)
    out = []
    for r in cur.fetchall():
        out.append(
            {
                "sas_id": normalize_sas_id(r[0]),
                "first_name": r[1],
                "last_name": r[2],
                "full_name": r[3],
                "date_of_birth": parse_date(r[4]),
                "year_of_birth": parse_year(r[5]),
            }
        )
    return out


def apply_fill(cur, sas_id: str, dob: date) -> int:
    cur.execute(
        """
        UPDATE public.sas_id_personal
        SET date_of_birth = %s,
            year_of_birth = COALESCE(year_of_birth, %s),
            age = EXTRACT(YEAR FROM AGE(%s::date))::int
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
    p.add_argument("--delay", type=float, default=0.2)
    p.add_argument("--year", default="", help="SASMS membership year filter (blank = all)")
    p.add_argument("--start-after", default="", help="Resume after this numeric SAS ID")
    p.add_argument("--all", action="store_true", help="Include sailors who already have DOB")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--audit", default="/tmp/sasms_dob_audit.jsonl")
    p.add_argument("--reconnect-every", type=int, default=50)
    args = p.parse_args(argv)
    if not args.db_url:
        print("DB_URL required", file=sys.stderr)
        return 2

    client = SasmsClient()
    conn = db_connect(args.db_url)
    cur = conn.cursor()
    targets = load_targets(cur, only_missing=not args.all, limit=args.limit, start_after=args.start_after)
    print(f"targets={len(targets)} apply={bool(args.apply)} year={args.year!r}")

    summary = {
        "fetched_ok": 0,
        "not_found": 0,
        "http_err": 0,
        "apply": 0,
        "flag": 0,
        "noop": 0,
        "skip": 0,
        "ignore": 0,
        "apply_rows": 0,
        "year_mismatch_status_ignored": 0,
    }

    with open(args.audit, "a", encoding="utf-8") as audit:
        audit.write(
            json.dumps(
                {
                    "event": "start",
                    "n": len(targets),
                    "apply": args.apply,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": SASMS_URL,
                }
            )
            + "\n"
        )
        for i, t in enumerate(targets, 1):
            if args.reconnect_every and i > 1 and (i - 1) % args.reconnect_every == 0:
                try:
                    cur.close()
                    conn.close()
                except Exception:
                    pass
                conn = db_connect(args.db_url)
                cur = conn.cursor()

            try:
                hit = client.search(t["sas_id"], year=args.year)
            except Exception as e:
                summary["http_err"] += 1
                audit.write(json.dumps({"event": "http_err", "sas_id": t["sas_id"], "error": str(e)}) + "\n")
                time.sleep(args.delay)
                continue

            if not hit or not hit.get("date_of_birth"):
                summary["not_found"] += 1
                audit.write(json.dumps({"event": "not_found", "sas_id": t["sas_id"]}) + "\n")
                time.sleep(args.delay)
                continue

            summary["fetched_ok"] += 1
            # Lapsed/Active ignored — DOB only.
            src = SourceRecord(
                sas_id=hit["sas_id"],
                full_name=hit["full_name"],
                date_of_birth=hit["date_of_birth"],
                year_of_birth=hit["date_of_birth"].year,
                membership_status="",  # intentionally blank so Lapsed is not ignored as a skip
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
            d = decide(src, sailor)
            summary[d.action] = summary.get(d.action, 0) + 1
            rec = d.to_dict()
            rec["sasms_name"] = hit["full_name"]
            rec["sasms_status"] = hit["license_status"]
            rec["sasms_raw"] = hit["raw"]
            audit.write(json.dumps(rec) + "\n")

            if args.apply and d.action == "apply" and d.set_date_of_birth is not None:
                try:
                    n = apply_fill(cur, t["sas_id"], d.set_date_of_birth)
                    if n == 1:
                        conn.commit()
                        summary["apply_rows"] += 1
                    else:
                        conn.rollback()
                        audit.write(json.dumps({"event": "apply_miss", "sas_id": t["sas_id"], "rowcount": n}) + "\n")
                except Exception as e:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    # reconnect and retry once
                    conn = db_connect(args.db_url)
                    cur = conn.cursor()
                    try:
                        n = apply_fill(cur, t["sas_id"], d.set_date_of_birth)
                        if n == 1:
                            conn.commit()
                            summary["apply_rows"] += 1
                        else:
                            conn.rollback()
                    except Exception as e2:
                        audit.write(json.dumps({"event": "apply_err", "sas_id": t["sas_id"], "error": str(e2)}) + "\n")
                        try:
                            conn.rollback()
                        except Exception:
                            pass

            if i % 25 == 0:
                print(f"progress {i}/{len(targets)} {summary}", flush=True)
            time.sleep(args.delay)

    try:
        cur.close()
        conn.close()
    except Exception:
        pass
    print(json.dumps({"summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
