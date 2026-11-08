#!/usr/bin/env python3
"""Inspect + patch boat passport helm links: SAS ID -> slug."""
from __future__ import annotations

import py_compile
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

API = Path("/var/www/sailingsa/api/api.py")
DB = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"

OLD = (
    "esc(r['class_name'] or '-'), "
    "(('<a href=\"/sailor/' + str(r['helm_sa_sailing_id']) + '\">' + esc(r['helm_name']) + '</a>') "
    "if r['helm_sa_sailing_id'] else esc(r['helm_name'] or '-')), "
    "(r['rank'] or '-'))"
)

# We'll replace a larger block: after results fetch, build slug map, then fix result_rows.


def inspect() -> None:
    t = API.read_text(encoding="utf-8")
    print("sas_href_count", t.count("str(r['helm_sa_sailing_id'])"))
    i = t.find("str(r['helm_sa_sailing_id'])")
    print("context:\n", t[i - 200 : i + 250])
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT r.helm_name, r.helm_sa_sailing_id::text AS sas, r.sail_number::text AS sail
        FROM results r
        WHERE r.boat_id IN (
          SELECT bi.boat_id FROM boat_identifiers bi
          WHERE regexp_replace(lower(trim(COALESCE(bi.identifier_value::text, ''))), '[^a-z0-9]+', '', 'g') = '1365'
        )
        ORDER BY r.result_id DESC
        LIMIT 8
        """
    )
    print("boat1365 helms:", cur.fetchall())
    conn.close()


def patch() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-boat-sailor-slug-{stamp}"))
    text = API.read_text(encoding="utf-8")
    if "helm_slug_map = _batch_sailor_slugs_for_sas_ids" in text and "boat_page" in text:
        # check if already using slug in boat passport helm link
        if "helm_slug_map.get(str(r.get('helm_sa_sailing_id')" in text or (
            "helm_slug_map" in text[text.find("def boat_page") : text.find("def boat_page") + 8000]
            and "/sailor/' + str(r['helm_sa_sailing_id'])" not in text[text.find("def boat_page") : text.find("def boat_page") + 8000]
        ):
            # still need to verify
            pass

    start = text.find("def boat_page(")
    if start < 0:
        raise SystemExit("boat_page not found")
    # next def after boat_page
    end = text.find("\n@app.get(\"/boats\"", start)
    if end < 0:
        end = text.find("\ndef boats_directory", start)
    chunk = text[start:end]
    if "str(r['helm_sa_sailing_id'])" not in chunk and "str(r.get('helm_sa_sailing_id')" not in chunk:
        if "helm_slug_map" in chunk:
            print("already patched")
            return
        raise SystemExit("helm sas href not in boat_page")

    # Insert slug map before result_rows assignment
    m = re.search(r'result_rows\s*=\s*""\.join\(\[', chunk)
    if not m:
        m = re.search(r"result_rows\s*=\s*''\.join\(\[", chunk)
    if not m:
        raise SystemExit("result_rows join not found")
    marker = m.group(0)

    insert = (
        "helm_sas_ids = [str(r.get('helm_sa_sailing_id')) for r in results "
        "if r.get('helm_sa_sailing_id') is not None]\n"
        "        helm_slug_map = _batch_sailor_slugs_for_sas_ids(helm_sas_ids) if helm_sas_ids else {}\n"
        "        "
    )
    if "helm_slug_map = _batch_sailor_slugs_for_sas_ids" not in chunk:
        chunk = chunk.replace(marker, insert + marker, 1)

    old_link = (
        "(('<a href=\"/sailor/' + str(r['helm_sa_sailing_id']) + '\">' + esc(r['helm_name']) + '</a>') "
        "if r['helm_sa_sailing_id'] else esc(r['helm_name'] or '-'))"
    )
    # Only link when we have a name slug; never emit numeric SAS URL (bot signal)
    new_link = (
        "(('<a href=\"/sailor/' + esc(str(helm_slug_map.get(str(r.get('helm_sa_sailing_id')) or ''))) + '\">' "
        "+ esc(r['helm_name']) + '</a>') "
        "if (r.get('helm_sa_sailing_id') is not None and helm_slug_map.get(str(r.get('helm_sa_sailing_id')))) "
        "else esc(r['helm_name'] or '-'))"
    )

    if old_link not in chunk:
        raise SystemExit("old helm link expression not found in boat_page")
    chunk = chunk.replace(old_link, new_link, 1)

    text2 = text[:start] + chunk + text[end:]
    if text2 == text:
        raise SystemExit("no change")
    API.write_text(text2, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK boat_page helm links use slug")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        inspect()
    else:
        inspect()
        patch()
