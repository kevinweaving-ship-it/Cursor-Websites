#!/usr/bin/env python3
"""
New SAS IDs scraper: probes member-finder from MAX(sa_sailing_id)+1, inserts into sas_id_personal.
Common SAS data tool – run daily (cron: sailingsa/deploy/sailingsa_sas_scrape.cron).
Uses same logic as api.py run_daily_scrape but targets sas_id_personal and needs no scrape_log.
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

def _get_db_url() -> str:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("sas_member_scrape: DB_URL or DATABASE_URL required", file=sys.stderr)
        sys.exit(1)
    return url

class _FetchError(Exception):
    """Member-finder request failed. Not the same as an empty ID."""


def _fetch_member(sas_id: int) -> dict | None:
    """Fetch one member page. Returns dict with first_name, last_name, full_name, year_of_birth or None if not found.

    Raises _FetchError when the request fails. Callers must not treat that as an empty ID.
    """
    try:
        import urllib.request
        url = f"https://www.sailing.org.za/member-finder?parentBodyID={sas_id}&firstname=&surname="
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise _FetchError(str(e)) from e
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

def _name_key(full_name: str, first_name: str = "", last_name: str = "") -> str:
    """Order-independent name key. 'de Clerk, Christoff' and 'Christoff de Clerk' match."""
    raw = (full_name or "").strip()
    if not raw:
        raw = f"{first_name or ''} {last_name or ''}"
    raw = raw.lower().replace(",", " ")
    raw = re.sub(r"[^a-z\s]+", " ", raw)
    tokens = [t for t in raw.split() if t]
    if len(tokens) < 2:
        return ""
    return " ".join(sorted(tokens))


def match_recent_sas_to_temps(conn, cur, lookback: int = 200) -> int:
    """When new SAS names were added, compare the last 200 named SAS IDs to temp sailors.

    A temp sailor has results and no SAS ID. Merge only when that name belongs to
    exactly one temp and exactly one SAS ID. Their result rows then carry the SAS ID.
    """
    cur.execute(
        """
        SELECT sa_sailing_id::text, COALESCE(full_name, ''), COALESCE(first_name, ''), COALESCE(last_name, '')
        FROM sas_id_personal
        WHERE sa_sailing_id ~ '^[0-9]+$'
          AND NULLIF(TRIM(COALESCE(full_name, '')), '') IS NOT NULL
        """
    )
    by_key: dict[str, list[str]] = {}
    ordered: list[tuple[int, str]] = []
    for sid, full_name, first_name, last_name in cur.fetchall():
        key = _name_key(full_name, first_name, last_name)
        if not key:
            continue
        by_key.setdefault(key, []).append(str(sid))
        ordered.append((int(sid), key))
    ordered.sort(reverse=True)
    recent = {key for _n, key in ordered[:lookback]}

    cur.execute(
        """
        SELECT t.temp_id::text, COALESCE(t.full_name, ''), COALESCE(t.first_name, ''), COALESCE(t.last_name, '')
        FROM temp_people t
        WHERE COALESCE(t.upgraded, false) = false
          AND NULLIF(TRIM(COALESCE(t.official_sa_sailing_id, '')), '') IS NULL
          AND EXISTS (
            SELECT 1 FROM results r
            WHERE r.helm_temp_id IN ('TMP:' || t.temp_id::text, t.temp_id::text)
               OR r.crew_temp_id IN ('TMP:' || t.temp_id::text, t.temp_id::text)
               OR r.crew2_temp_id IN ('TMP:' || t.temp_id::text, t.temp_id::text)
               OR r.crew3_temp_id IN ('TMP:' || t.temp_id::text, t.temp_id::text)
          )
        """
    )
    temps_by_key: dict[str, list[str]] = {}
    for temp_id, full_name, first_name, last_name in cur.fetchall():
        key = _name_key(full_name, first_name, last_name)
        if not key or key not in recent:
            continue
        temps_by_key.setdefault(key, []).append(str(temp_id))

    merged = 0
    for key, temp_ids in temps_by_key.items():
        sas_ids = by_key.get(key) or []
        recent_sas = [sid for n, k in ordered[:lookback] if k == key for sid in (str(n),) ]
        if len(temp_ids) != 1 or len(sas_ids) != 1 or len(recent_sas) != 1:
            print(
                f"[sas_member_scrape] temp match skipped (ambiguous) key={key} temps={temp_ids} sas={sas_ids}",
                file=sys.stderr,
            )
            continue
        sas_id = sas_ids[0]
        temp_id = temp_ids[0]
        labels = [f"TMP:{temp_id}", temp_id]
        cur.execute(
            """
            UPDATE temp_people
               SET official_sa_sailing_id = %s, upgraded = true, updated_at = NOW()
             WHERE temp_id::text = %s
               AND COALESCE(upgraded, false) = false
               AND NULLIF(TRIM(COALESCE(official_sa_sailing_id, '')), '') IS NULL
            """,
            (sas_id, temp_id),
        )
        if cur.rowcount != 1:
            conn.rollback()
            print(f"[sas_member_scrape] temp match skipped (already upgraded) TMP:{temp_id}", file=sys.stderr)
            continue
        for role, status_col in (
            ("helm", "match_status_helm"),
            ("crew", "match_status_crew"),
            ("crew2", "match_status_crew"),
            ("crew3", "match_status_crew"),
        ):
            cur.execute(
                f"""
                UPDATE results
                   SET {role}_sa_sailing_id = %s,
                       {role}_temp_id = NULL,
                       {status_col} = 'sas_scrape_merge'
                 WHERE {role}_temp_id = ANY(%s)
                """,
                (int(sas_id), labels),
            )
        conn.commit()
        merged += 1
        print(f"[sas_member_scrape] merged TMP:{temp_id} -> SAS {sas_id} ({key})", file=sys.stderr)
    return merged


def main() -> None:
    db_url = _get_db_url()
    try:
        import psycopg2
    except ImportError:
        print("sas_member_scrape: psycopg2 required", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    # Next search starts at the last ID we already have that has a name. Gaps are not people.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sas_id_gaps (
            sas_id integer PRIMARY KEY,
            first_seen_at timestamptz NOT NULL DEFAULT NOW(),
            last_seen_at timestamptz NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.execute("""
        SELECT COALESCE(MAX(NULLIF(TRIM(sa_sailing_id), '')::int), 0)
        FROM sas_id_personal
        WHERE sa_sailing_id ~ '^[0-9]+$'
          AND NULLIF(TRIM(COALESCE(full_name, '')), '') IS NOT NULL
    """)
    last_we_have = cur.fetchone()[0] or 0
    start_id = int(last_we_have) + 1
    env_start = os.environ.get("START_ID")
    if env_start and str(env_start).strip().isdigit():
        start_id = int(env_start.strip())
    consecutive_not_found = 0
    # Unused SAS numbers are their gaps. Record each one and keep going.
    # After 20 blanks in a row, the last ID that had a name is the last record.
    max_consecutive = 20
    max_fetch_errors = 5
    fetch_errors = 0
    gaps = 0
    delay_sec = 0.5
    added = 0
    last_valid = int(last_we_have)
    current_id = start_id
    while consecutive_not_found < max_consecutive:
        try:
            data = _fetch_member(current_id)
        except _FetchError as e:
            fetch_errors += 1
            print(f"[sas_member_scrape] {current_id} fetch error ({fetch_errors}/{max_fetch_errors}): {e}", file=sys.stderr)
            if fetch_errors >= max_fetch_errors:
                cur.close()
                conn.close()
                print(f"[sas_member_scrape] abort: member-finder failed {max_fetch_errors} times at {current_id}", file=sys.stderr)
                sys.exit(1)
            time.sleep(delay_sec)
            continue
        fetch_errors = 0
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
                cur.execute("DELETE FROM sas_id_gaps WHERE sas_id = %s", (current_id,))
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
                last_valid = current_id
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
                    cur.execute("DELETE FROM sas_id_gaps WHERE sas_id = %s", (current_id,))
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
            cur.execute(
                """
                INSERT INTO sas_id_gaps (sas_id) VALUES (%s)
                ON CONFLICT (sas_id) DO UPDATE SET last_seen_at = NOW()
                """,
                (current_id,),
            )
            conn.commit()
            gaps += 1
            consecutive_not_found += 1
            print(f"[sas_member_scrape] gap {current_id}", file=sys.stderr)
        current_id += 1
        time.sleep(delay_sec)
    merged = 0
    if added:
        try:
            merged = match_recent_sas_to_temps(conn, cur)
        except Exception as e:
            conn.rollback()
            print(f"[sas_member_scrape] temp match failed: {e}", file=sys.stderr)
    cur.close()
    conn.close()
    print(
        f"[sas_member_scrape] done: start={start_id} last_valid={last_valid} gaps={gaps} added={added} temp_merged={merged}",
        file=sys.stderr,
    )

if __name__ == "__main__":
    main()
