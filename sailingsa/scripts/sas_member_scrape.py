#!/usr/bin/env python3
"""
New SAS IDs scraper: probes member-finder from MAX(sa_sailing_id)+1, inserts into sas_id_personal.
Common SAS data tool – run daily (cron: sailingsa/deploy/sailingsa_sas_scrape.cron).
Uses same logic as api.py run_daily_scrape but targets sas_id_personal and needs no scrape_log.
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

def _fetch_member(sas_id: int) -> dict | None:
    """Fetch one member page. Returns dict with first_name, last_name, full_name, year_of_birth or None if not found."""
    try:
        import urllib.request
        url = f"https://www.sailing.org.za/member-finder?parentBodyID={sas_id}&firstname=&surname="
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SailingSA-scraper/1.0)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[sas_member_scrape] {sas_id} fetch error: {e}", file=sys.stderr)
        return None
    if "SA Sailing ID:" not in html or str(sas_id) not in html:
        return None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        # Fallback: simple name from <b>
        import re
        m = re.search(r"<b>([^<]+)</b>", html)
        if not m:
            return None
        name_text = m.group(1).strip()
        if not name_text or name_text == str(sas_id) or "SA Sailing ID:" in name_text:
            return None
        name_text = name_text.replace(",,", ",")
        if "," in name_text:
            parts = name_text.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip().split()[0] if parts[1].strip() else ""
        else:
            name_parts = name_text.split()
            first_name = name_parts[0] if name_parts else name_text
            last_name = name_parts[-1] if len(name_parts) >= 2 else ""
        birth_year = None
        for line in html.split("\n"):
            if "Born" in line:
                try:
                    birth_year = int(line.strip().split("Born")[-1].strip()[:4])
                    break
                except (ValueError, IndexError):
                    pass
        return {"first_name": first_name, "last_name": last_name, "full_name": name_text, "year_of_birth": birth_year}
    # With BeautifulSoup
    name_elements = soup.find_all("b")
    for elem in name_elements:
        name_text = (elem.get_text() or "").strip()
        if not name_text or name_text == str(sas_id) or "SA Sailing ID:" in name_text:
            continue
        name_text = name_text.replace(",,", ",")
        if "," in name_text:
            parts = name_text.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip().split()[0] if parts[1].strip() else ""
        else:
            name_parts = name_text.split()
            first_name = name_parts[0] if name_parts else name_text
            last_name = name_parts[-1] if len(name_parts) >= 2 else ""
        birth_year = None
        for t in soup.find_all(string=lambda s: s and "Born" in str(s)):
            try:
                birth_year = int(str(t).strip().split("Born")[-1].strip()[:4])
                break
            except (ValueError, IndexError):
                pass
        return {"first_name": first_name, "last_name": last_name, "full_name": name_text, "year_of_birth": birth_year}
    return None

def main() -> None:
    db_url = _get_db_url()
    try:
        import psycopg2
    except ImportError:
        print("sas_member_scrape: psycopg2 required", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    # Resolve max from sas_id_personal (sa_sailing_id can be text or int), or use START_ID env
    cur.execute("SELECT COALESCE(MAX(NULLIF(TRIM(sa_sailing_id), '')::int), 0) FROM sas_id_personal WHERE sa_sailing_id ~ '^[0-9]+$'")
    start_id = (cur.fetchone()[0] or 0) + 1
    env_start = os.environ.get("START_ID")
    if env_start and str(env_start).strip().isdigit():
        start_id = int(env_start.strip())
    consecutive_not_found = 0
    max_consecutive = 20
    delay_sec = 0.5
    added = 0
    current_id = start_id
    while consecutive_not_found < max_consecutive:
        data = _fetch_member(current_id)
        if data:
            # Upsert into sas_id_personal (columns may vary; use minimal set)
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
    print(f"[sas_member_scrape] done: start={start_id} end={current_id-1} added={added}", file=sys.stderr)

if __name__ == "__main__":
    main()
