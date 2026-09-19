#!/usr/bin/env python3
"""
SAS ID scraper. Writes a row only when sailing.org.za returns a member card for that exact ID.

Empty pages are not inserted. After a few confirmed empties in a row, the run stops.
That last real ID is the end of the issued range. The next run starts at last real ID + 1.
A fetch error is not an empty page and does not move the cursor past that ID.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

def _get_db_url() -> str:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("sas_member_scrape: DB_URL or DATABASE_URL required", file=sys.stderr)
        sys.exit(1)
    return url

class MemberFetchError(Exception):
    """Transport or parse failure. Not the same as 'this SAS ID does not exist'."""


def parse_member_html(html: str, sas_id: int) -> dict | None:
    """Accept only the member card whose own SAS number is this ID.

    The finder page title always contains 'SA Sailing ID'. An empty result still
    echoes the probed number in the URL. Matching those strings stored 'No Record
    Found' and copies of other sailors. The real card is:

        <b>Surname, Given</b> ... SA Sailing ID: <b>12345</b> ... Born 1990
    """
    import re
    card = re.search(
        r"<b>\s*([^<]+?)\s*</b>\s*(?:<div[^>]*>\s*)?SA Sailing ID:\s*<b>\s*(\d+)\s*</b>(.{0,400})",
        html,
        re.I | re.S,
    )
    if not card or int(card.group(2)) != int(sas_id):
        return None
    name_text = card.group(1).replace(",,", ",").strip()
    if not name_text or name_text.lower() in {"no record found", "no results found", "not found"}:
        return None
    if "," in name_text:
        last_name, given = [p.strip() for p in name_text.split(",", 1)]
        first_name = given.split()[0] if given else ""
        full_name = f"{given} {last_name}".strip()
    else:
        parts = name_text.split()
        first_name = parts[0] if parts else ""
        last_name = parts[-1] if len(parts) >= 2 else ""
        full_name = name_text
    birth_year = None
    born = re.search(r"Born\s*(\d{4})", card.group(3))
    if born:
        birth_year = int(born.group(1))
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "year_of_birth": birth_year,
        "sas_display_name": name_text,
    }


def _fetch_member(sas_id: int) -> dict | None:
    """Fetch one member page.

    Returns the member dict, None if sailing.org.za has no card for this ID,
    or raises MemberFetchError on a transport failure (caller must not skip the ID).
    """
    import urllib.request
    url = f"https://www.sailing.org.za/member-finder?parentBodyID={sas_id}&firstname=&surname="
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SailingSA-scraper/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise MemberFetchError(str(e)) from e
    return parse_member_html(html, sas_id)

def main() -> None:
    db_url = _get_db_url()
    try:
        import psycopg2
    except ImportError:
        print("sas_member_scrape: psycopg2 required", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    # Next run starts at the last real member + 1. Blank / "No Record Found" rows are not real.
    cur.execute("""
        SELECT COALESCE(MAX(sa_sailing_id::int), 0)
        FROM sas_id_personal
        WHERE sa_sailing_id ~ '^[0-9]+$'
          AND NULLIF(TRIM(COALESCE(full_name, '')), '') IS NOT NULL
          AND LOWER(TRIM(full_name)) NOT IN ('no record found', 'no results found', 'not found')
          AND (NULLIF(TRIM(COALESCE(first_name, '')), '') IS NOT NULL
               OR NULLIF(TRIM(COALESCE(last_name, '')), '') IS NOT NULL)
    """)
    last_valid = int(cur.fetchone()[0] or 0)
    start_id = last_valid + 1
    env_start = os.environ.get("START_ID")
    if env_start and str(env_start).strip().isdigit():
        start_id = int(env_start.strip())
        last_valid = start_id - 1
    # A few confirmed empty IDs means the issued range has ended. Do not keep walking.
    consecutive_not_found = 0
    max_consecutive = 5
    delay_sec = 0.5
    added = 0
    current_id = start_id
    while consecutive_not_found < max_consecutive:
        data = None
        fetch_error = None
        for _attempt in range(3):
            try:
                data = _fetch_member(current_id)
                fetch_error = None
                break
            except MemberFetchError as e:
                fetch_error = e
                time.sleep(1.5)
        if fetch_error is not None:
            print(f"[sas_member_scrape] stop at {current_id}: fetch failed ({fetch_error})", file=sys.stderr)
            break
        if data and not (data.get("first_name") or data.get("last_name")):
            data = None
        if data:
            # Real card only. Empty pages never reach this insert.
            entity_key = str(current_id)
            run_id = os.environ.get("SCRAPE_RUN_ID")
            existed = False
            try:
                cur.execute("SELECT 1 FROM sas_id_personal WHERE sa_sailing_id = %s", (entity_key,))
                existed = cur.fetchone() is not None
            except Exception:
                pass
            try:
                cur.execute("""
                    INSERT INTO sas_id_personal (sa_sailing_id, first_name, last_name, full_name, year_of_birth)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sa_sailing_id) DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        full_name = EXCLUDED.full_name,
                        year_of_birth = EXCLUDED.year_of_birth
                """, (str(current_id), data["first_name"], data["last_name"], data["full_name"], data["year_of_birth"]))
                conn.commit()
                added += 1
                consecutive_not_found = 0
                last_valid = current_id
                action = "updated" if existed else "inserted"
                if run_id and run_id.isdigit():
                    try:
                        cur.execute(
                            "INSERT INTO scrape_row_audit (scrape_name, entity_key, action, run_id) VALUES ('sas_registry', %s, %s, %s)",
                            (entity_key, action, int(run_id)),
                        )
                        conn.commit()
                    except Exception:
                        conn.rollback()
                print(f"[sas_member_scrape] added {current_id} {data.get('full_name', '')}", file=sys.stderr)
            except Exception as e:
                # Try without year_of_birth if column missing
                try:
                    cur.execute("""
                        INSERT INTO sas_id_personal (sa_sailing_id, first_name, last_name, full_name)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (sa_sailing_id) DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            full_name = EXCLUDED.full_name
                    """, (str(current_id), data["first_name"], data["last_name"], data["full_name"]))
                    conn.commit()
                    added += 1
                    consecutive_not_found = 0
                    last_valid = current_id
                    action = "updated" if existed else "inserted"
                    if run_id and run_id.isdigit():
                        try:
                            cur.execute(
                                "INSERT INTO scrape_row_audit (scrape_name, entity_key, action, run_id) VALUES ('sas_registry', %s, %s, %s)",
                                (entity_key, action, int(run_id)),
                            )
                            conn.commit()
                        except Exception:
                            conn.rollback()
                except Exception as e2:
                    print(f"[sas_member_scrape] insert error {current_id}: {e2}", file=sys.stderr)
        else:
            consecutive_not_found += 1
        current_id += 1
        time.sleep(delay_sec)
    cur.close()
    conn.close()
    print(
        f"[sas_member_scrape] done: start={start_id} end={current_id-1} added={added} "
        f"last_valid={last_valid} next_start={last_valid + 1}",
        file=sys.stderr,
    )

if __name__ == "__main__":
    main()
