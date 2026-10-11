#!/usr/bin/env python3
"""SAS accreditation finder -> member_roles sync SQL.

Source: https://www.sailing.org.za/accreditation-finder/
Each framework is one GET (?accred_id=). Results are name + SAS ID cards.

Writes:
  member_roles_sync_YYYYMMDD.sql   INSERTs for pairs not already in member_roles
  new_quals_report_YYYYMMDD.txt
  quals_checksum_report_YYYYMMDD.txt   with --checksum-only

CSV fallback (--csv) columns: sas_id or "SA Sailing ID", and framework or
"Accreditation framework". Use that when the site returns 403.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_module
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

FINDER = "https://www.sailing.org.za/accreditation-finder"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# option value on the finder -> roles.role_code (live roles table)
FRAMEWORKS = {
    "1292": ("Appointed Examiners", "APPT_EXAM"),
    "1382": ("Appointed National Senior Examiner", "NAT_SE_EXAM"),
    "1383": ("Appointed National Senior Safety Officer", "NAT_SE_SAF"),
    "826": ("Appointed SA Sailing Vessel Safety Officers", "VSO"),
    "1291": ("Appointed SAMSA Vessel Surveyors", "SAMSA_SURV"),
    "790": ("Assistant Instructor", "ASSIST_INSTR"),
    "791": ("Assistant Race Coach", "ASST_COACH"),
    "792": ("Instructor - Dinghy & Multihull", "INSTR_DINGHY"),
    "838": ("Instructor - Keelboat", "INSTR_KEEL"),
    "834": ("Judge- District Level", "JUDGE_DIST"),
    "1033": ("Judge- International level (IJ)", "JUDGE_INT"),
    "833": ("Judge-Club Level", "JUDGE_CLUB"),
    "798": ("Judge-National Level (NJ)", "JUDGE_NAT"),
    "832": ("Judge-Regional Level", "JUDGE_REG"),
    "794": ("Race Coach", "RACE_COACH"),
    "787": ("Race Coach Developer", "COACH_DEV"),
    "803": ("Race Officer - Assistant", "RO_ASST"),
    "1625": ("Race Officer - Facilitator", "RO_FAC"),
    "829": ("Race Officer-Club/District", "RO_CLUB"),
    "797": ("Race Officer-National", "RO_NAT"),
    "796": ("Race Officer-Regional", "RO_REG"),
    "993": ("SA Sailing Return to Play Authorisation", "RTP_AUTH"),
    "1257": ("SA Sailing Safety Boat Instructor", "SBI"),
    "786": ("Safety Boat Operator", "SBO"),
    "793": ("Senior Instructor", "SENIOR_INSTR"),
    "795": ("Senior Race Coach", "SENIOR_COACH"),
    "1377": ("Umpire - National", "UMPIRE_NAT"),
}

LABEL_TO_CODE = {label.lower(): code for _id, (label, code) in FRAMEWORKS.items()}
# CSV exports sometimes use the doc examples
LABEL_TO_CODE["judge-club level"] = "JUDGE_CLUB"
LABEL_TO_CODE["race officer-national"] = "RO_NAT"
LABEL_TO_CODE["instructor - dinghy &amp; multihull"] = "INSTR_DINGHY"

PAIR_RE = re.compile(
    r"<b>([^<]{2,120})</b>\s*<div class=\"font-size-sm mt-2\">SA Sailing ID:\s*<b>(\d+)</b>",
    re.I,
)
EXPIRED_RE = re.compile(r"Expired\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", re.I)
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _get(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _parse_expired(chunk: str) -> str | None:
    m = EXPIRED_RE.search(chunk or "")
    if not m:
        return None
    parts = m.group(1).split()
    if len(parts) != 3:
        return None
    mon = MONTHS.get(parts[1][:3].lower())
    if not mon:
        return None
    try:
        return f"{int(parts[2]):04d}-{mon:02d}-{int(parts[0]):02d}"
    except ValueError:
        return None


def _role_for_label(label: str) -> str | None:
    key = html_module.unescape(label or "").strip().lower()
    key = re.sub(r"\s+", " ", key)
    return LABEL_TO_CODE.get(key)


def fetch_live() -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    unmapped: list[str] = []
    index = _get(FINDER + "/")
    # Safeguarding (3239) is on the finder and is not in public.roles — record it, do not insert.
    known = set(FRAMEWORKS)
    option_ids = re.findall(r'<option value="(\d+)"\s*>([^<]+)</option>', index)
    for accred_id, raw_label in option_ids:
        label = html_module.unescape(raw_label).strip()
        if accred_id not in known:
            unmapped.append(f"{accred_id} {label}")
            continue
        _label, code = FRAMEWORKS[accred_id]
        page = _get(f"{FINDER}?parentBodyID=&firstname=&surname=&accred_id={accred_id}")
        text = re.sub(r"<script[\s\S]*?</script>", " ", page, flags=re.I)
        matches = list(PAIR_RE.finditer(text))
        for i, match in enumerate(matches):
            name, sas_id = match.group(1), match.group(2)
            end = matches[i + 1].start() if i + 1 < len(matches) else match.end() + 2000
            expired = _parse_expired(text[match.end():end])
            rows.append({
                "sas_id": sas_id,
                "role_code": code,
                "framework": _label,
                "name": html_module.unescape(name).strip(),
                "status": "expired" if expired else "active",
                "expires_date": expired,
            })
    return rows, unmapped


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    unmapped: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return rows, unmapped
        fields = {name.strip().lower(): name for name in reader.fieldnames}
        id_key = fields.get("sas_id") or fields.get("sa sailing id")
        fw_key = fields.get("framework") or fields.get("accreditation") or fields.get("accreditation framework")
        if not id_key or not fw_key:
            raise SystemExit("CSV needs sas_id (or SA Sailing ID) and framework (or Accreditation framework)")
        for rec in reader:
            sas_id = re.sub(r"\D", "", (rec.get(id_key) or ""))
            label = (rec.get(fw_key) or "").strip()
            if not sas_id or not label:
                continue
            code = _role_for_label(label)
            if not code:
                unmapped.append(label)
                continue
            rows.append({
                "sas_id": sas_id,
                "role_code": code,
                "framework": label,
                "name": "",
                "status": "active",
                "expires_date": None,
            })
    return rows, sorted(set(unmapped))


def _existing_pairs(db_url: str) -> set[tuple[str, str]] | None:
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed; SQL will include every scraped pair", file=sys.stderr)
        return None
    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        cur.execute("SELECT person_key, role_code FROM member_roles")
        out = set()
        for person_key, role_code in cur.fetchall():
            out.add((str(person_key), str(role_code)))
        cur.close()
        return out
    finally:
        conn.close()


def _checksum(pairs: list[tuple[str, str]]) -> str:
    blob = "\n".join(f"{a}\t{b}" for a, b in sorted(pairs))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape SAS accreditation quals into member_roles SQL")
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--checksum-only", action="store_true")
    parser.add_argument("--db-url", type=str, default=None)
    args = parser.parse_args()
    out_dir = Path(args.output_dir or Path(__file__).resolve().parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    if args.csv:
        rows, unmapped = load_csv(Path(args.csv))
    else:
        rows, unmapped = fetch_live()

    # one row per person+role; keep expired if any copy says expired
    merged: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["sas_id"], row["role_code"])
        prev = merged.get(key)
        if prev is None or (row["status"] == "expired" and prev["status"] != "expired"):
            merged[key] = row
    rows = list(merged.values())

    db_url = args.db_url or os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    existing = _existing_pairs(db_url) if db_url else None
    new_rows = []
    for row in rows:
        person_key = f"SAS:{row['sas_id']}"
        if existing is not None and (person_key, row["role_code"]) in existing:
            continue
        new_rows.append(row)

    source_pairs = [(f"SAS:{r['sas_id']}", r["role_code"]) for r in rows]
    report_lines = [
        f"SAS accreditation scrape {stamp} UTC",
        f"source_rows={len(rows)} new_rows={len(new_rows)} unmapped={len(unmapped)}",
        f"source_sha256={_checksum(source_pairs)}",
    ]
    if existing is not None:
        report_lines.append(f"our_table_rows={len(existing)} our_sha256={_checksum(sorted(existing))}")
    else:
        report_lines.append("our_table=not compared (set DB_URL to diff)")
    if unmapped:
        report_lines.append("unmapped frameworks (not inserted):")
        report_lines.extend(f"  {item}" for item in unmapped)
    report_lines.append("NEW (we did not have):")
    for row in sorted(new_rows, key=lambda r: (int(r["sas_id"]), r["role_code"])):
        report_lines.append(f"{row['sas_id']}\t{row['role_code']}\t{row['status']}\t{row['framework']}")

    checksum_path = out_dir / f"quals_checksum_report_{stamp}.txt"
    checksum_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Wrote {checksum_path} source_rows={len(rows)} new_rows={len(new_rows)}")
    if args.checksum_only:
        return

    sql_lines = [
        "-- SAS accreditation finder sync. Safe to re-run.",
        "BEGIN;",
    ]
    for row in sorted(new_rows, key=lambda r: (int(r["sas_id"]), r["role_code"])):
        expires = "NULL" if not row["expires_date"] else _sql_str(row["expires_date"])
        sql_lines.append(
            "INSERT INTO member_roles (person_key, role_code, status, expires_date, source, updated_at) "
            f"VALUES ({_sql_str('SAS:' + row['sas_id'])}, {_sql_str(row['role_code'])}, {_sql_str(row['status'])}, "
            f"{expires}, 'sas_accreditation_finder', NOW()) "
            "ON CONFLICT (person_key, role_code) DO UPDATE SET "
            "status = EXCLUDED.status, expires_date = EXCLUDED.expires_date, "
            "source = EXCLUDED.source, updated_at = NOW();"
        )
    sql_lines.append("COMMIT;")
    sql_path = out_dir / f"member_roles_sync_{stamp}.sql"
    sql_path.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")
    new_path = out_dir / f"new_quals_report_{stamp}.txt"
    new_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Wrote {sql_path}")
    print(f"Wrote {new_path}")


if __name__ == "__main__":
    main()
