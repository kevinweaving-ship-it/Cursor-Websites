#!/usr/bin/env python3
"""
SAS ID scraper. Writes a row only when sailing.org.za returns a member card for that exact ID.

Empty pages are not inserted. After a few confirmed empties in a row, the run stops.
That last real ID is the end of the issued range. The next run starts at last real ID + 1.
A fetch error is not an empty page and does not move the cursor past that ID.

Sailors who raced with no SAS ID stay in identity_pending_sailors (status pending).
When this tool inserts one new real card, it checks that list. If exactly one
no-SAS sailor has the same full name, and no other SAS card has that name,
past helm/crew/crew2/crew3 seats are linked to the new ID and the no-SAS row
is removed. A second sailor row is never created.
"""
from __future__ import annotations

import os
import re
import sys
import time


def _norm_person(name: str) -> str:
    s = (name or "").replace("&#039;", "'").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def sync_sailed_no_sas(conn) -> int:
    """Record every helm/crew seat that has a name and no SAS ID.

    One row per name and role. Crew, crew2 and crew3 share the crew role
    so the same person is not stored three times. Club codes and combined
    names (Lucy & Andy) are not sailors. Existing admin_confirmed rows are
    kept; their counts are refreshed. Rows whose seats now have a SAS ID
    are removed.
    """
    cur = conn.cursor()
    cur.execute(
        """
        WITH seats AS (
            SELECT 'helm'::text AS role, btrim(helm_name) AS display_name, regatta_id::text AS regatta_id
            FROM results
            WHERE helm_sa_sailing_id IS NULL AND NULLIF(btrim(coalesce(helm_name, '')), '') IS NOT NULL
            UNION ALL
            SELECT 'crew', btrim(crew_name), regatta_id::text
            FROM results
            WHERE crew_sa_sailing_id IS NULL AND NULLIF(btrim(coalesce(crew_name, '')), '') IS NOT NULL
            UNION ALL
            SELECT 'crew', btrim(crew2_name), regatta_id::text
            FROM results
            WHERE crew2_sa_sailing_id IS NULL AND NULLIF(btrim(coalesce(crew2_name, '')), '') IS NOT NULL
            UNION ALL
            SELECT 'crew', btrim(crew3_name), regatta_id::text
            FROM results
            WHERE crew3_sa_sailing_id IS NULL AND NULLIF(btrim(coalesce(crew3_name, '')), '') IS NOT NULL
        ),
        clean AS (
            SELECT role, display_name, regatta_id,
                   lower(trim(regexp_replace(replace(replace(display_name, '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) AS normalized_name
            FROM seats
            WHERE position('&' IN display_name) = 0
              AND lower(trim(display_name)) NOT IN (
                    SELECT lower(trim(club_abbrev)) FROM clubs WHERE NULLIF(trim(club_abbrev), '') IS NOT NULL
                    UNION
                    SELECT lower(trim(club_fullname)) FROM clubs WHERE NULLIF(trim(club_fullname), '') IS NOT NULL
              )
        ),
        picked AS (
            SELECT DISTINCT ON (normalized_name, role)
                   normalized_name, role, display_name
            FROM (
                SELECT normalized_name, role, display_name, count(*) AS n
                FROM clean
                GROUP BY 1, 2, 3
            ) c
            ORDER BY normalized_name, role, n DESC, display_name
        ),
        agg AS (
            SELECT p.normalized_name, p.role, p.display_name,
                   (SELECT count(*) FROM clean c
                     WHERE c.normalized_name = p.normalized_name AND c.role = p.role) AS result_row_count,
                   (SELECT COALESCE(array_agg(DISTINCT c.regatta_id), '{}')
                      FROM clean c
                     WHERE c.normalized_name = p.normalized_name AND c.role = p.role) AS regatta_ids
            FROM picked p
        )
        INSERT INTO identity_pending_sailors
            (display_name, role, normalized_name, result_row_count, regatta_ids, status)
        SELECT display_name, role, normalized_name, result_row_count, regatta_ids, 'pending'
        FROM agg
        ON CONFLICT (normalized_name, role) DO UPDATE SET
            result_row_count = EXCLUDED.result_row_count,
            regatta_ids = EXCLUDED.regatta_ids,
            updated_at = now()
        WHERE identity_pending_sailors.status IN ('pending', 'admin_confirmed_no_sas')
        """
    )
    inserted = cur.rowcount
    cur.execute(
        """
        DELETE FROM identity_pending_sailors
        WHERE status IN ('pending', 'admin_confirmed_no_sas')
          AND normalized_name IN (
                SELECT lower(trim(club_abbrev)) FROM clubs WHERE NULLIF(trim(club_abbrev), '') IS NOT NULL
                UNION
                SELECT lower(trim(club_fullname)) FROM clubs WHERE NULLIF(trim(club_fullname), '') IS NOT NULL
          )
        """
    )
    # Same person, same role, no unmatched seat left: they are no longer on the no-SAS list.
    cur.execute(
        """
        DELETE FROM identity_pending_sailors p
        WHERE p.status IN ('pending', 'admin_confirmed_no_sas')
          AND NOT EXISTS (
                SELECT 1 FROM results r
                WHERE (
                    (p.role = 'helm' AND r.helm_sa_sailing_id IS NULL
                     AND lower(trim(regexp_replace(replace(replace(coalesce(r.helm_name, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = p.normalized_name)
                    OR
                    (p.role = 'crew' AND (
                        (r.crew_sa_sailing_id IS NULL AND lower(trim(regexp_replace(replace(replace(coalesce(r.crew_name, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = p.normalized_name)
                        OR (r.crew2_sa_sailing_id IS NULL AND lower(trim(regexp_replace(replace(replace(coalesce(r.crew2_name, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = p.normalized_name)
                        OR (r.crew3_sa_sailing_id IS NULL AND lower(trim(regexp_replace(replace(replace(coalesce(r.crew3_name, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = p.normalized_name)
                    ))
                )
          )
        """
    )
    conn.commit()
    promoted = promote_exact_no_sas(conn)
    renamed = apply_sas_names_on_linked_seats(conn)
    promoted += promote_nickname_no_sas(conn)
    renamed += apply_sas_names_on_linked_seats(conn)
    cur.close()
    print(f"[sas_member_scrape] sas-truth names rewritten={renamed}", file=sys.stderr)
    return inserted + promoted


def promote_exact_no_sas(conn) -> int:
    """Move a no-SAS sailor onto an existing card only when the full name is unique.

    Does not insert a sailor. Nickname-only or two-card names stay on the no-SAS list.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.normalized_name, min(s.sa_sailing_id::int)
        FROM identity_pending_sailors p
        JOIN sas_id_personal s
          ON lower(trim(regexp_replace(replace(replace(coalesce(s.full_name, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = p.normalized_name
        WHERE p.status IN ('pending', 'admin_confirmed_no_sas')
          AND array_length(regexp_split_to_array(p.normalized_name, ' '), 1) >= 2
        GROUP BY p.normalized_name
        HAVING count(DISTINCT s.sa_sailing_id) = 1
        """
    )
    pairs = cur.fetchall()
    cur.close()
    linked = 0
    for norm, sas_id in pairs:
        try:
            linked += attach_new_sas_to_sailed(conn, int(sas_id), norm)
        except Exception as e:
            conn.rollback()
            print(f"[sas_member_scrape] promote failed {norm}: {e}", file=sys.stderr)
    return linked


def _add_nickname(cur, sas_id: int, nick: str) -> None:
    nick = (nick or "").strip()
    if len(nick) < 2 or len(nick) > 40:
        return
    cur.execute(
        "SELECT first_name, nickname FROM sas_id_personal WHERE sa_sailing_id::text = %s",
        (str(sas_id),),
    )
    row = cur.fetchone()
    if not row:
        return
    if _norm_person(row[0] or "") == _norm_person(nick):
        return
    parts = [p.strip() for p in (row[1] or "").split(",") if p.strip()]
    if any(_norm_person(p) == _norm_person(nick) for p in parts):
        return
    merged = ", ".join(parts + [nick])
    if len(merged) > 100:
        return
    cur.execute(
        "UPDATE sas_id_personal SET nickname = %s WHERE sa_sailing_id::text = %s",
        (merged, str(sas_id)),
    )


def _sheet_first_if_nickname(sheet_name: str, first_name: str, last_name: str) -> str | None:
    """Sheet first name is a nickname only when the surname already matches SAS."""
    if not sheet_name or "&" in sheet_name or "," in sheet_name:
        return None
    parts = _norm_person(sheet_name).split()
    if len(parts) < 2:
        return None
    if parts[-1] != _norm_person(last_name or ""):
        return None
    if parts[0] == _norm_person(first_name or ""):
        return None
    raw = sheet_name.strip().split()[0]
    return raw if raw else None


def apply_sas_names_on_linked_seats(conn) -> int:
    """Published result names are SAS first name + surname. Sheet nicknames are stored, not shown."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sa_sailing_id::text, first_name, last_name
        FROM sas_id_personal
        WHERE sa_sailing_id ~ '^[0-9]+$'
          AND NULLIF(TRIM(first_name), '') IS NOT NULL
          AND NULLIF(TRIM(last_name), '') IS NOT NULL
        """
    )
    people = {str(r[0]): (r[1], r[2]) for r in cur.fetchall()}
    renamed = 0
    for name_col, id_col in (
        ("helm_name", "helm_sa_sailing_id"),
        ("crew_name", "crew_sa_sailing_id"),
        ("crew2_name", "crew2_sa_sailing_id"),
        ("crew3_name", "crew3_sa_sailing_id"),
    ):
        cur.execute(
            f"""
            SELECT {id_col}::text, {name_col}
            FROM results
            WHERE {id_col} IS NOT NULL AND NULLIF(TRIM({name_col}), '') IS NOT NULL
            """
        )
        seen = set()
        for sid, sheet in cur.fetchall():
            person = people.get(str(sid))
            if not person:
                continue
            nick = _sheet_first_if_nickname(sheet, person[0], person[1])
            if nick and (str(sid), _norm_person(nick)) not in seen:
                seen.add((str(sid), _norm_person(nick)))
                _add_nickname(cur, int(sid), nick)
        truth = "TRIM(s.first_name) || ' ' || TRIM(s.last_name)"
        cur.execute(
            f"""
            UPDATE results r
            SET {name_col} = {truth}
            FROM sas_id_personal s
            WHERE r.{id_col}::text = s.sa_sailing_id::text
              AND NULLIF(TRIM(s.first_name), '') IS NOT NULL
              AND NULLIF(TRIM(s.last_name), '') IS NOT NULL
              AND POSITION('&' IN COALESCE(r.{name_col}, '')) = 0
              AND BTRIM(r.{name_col}) IS DISTINCT FROM ({truth})
            """
        )
        renamed += cur.rowcount
    conn.commit()
    cur.close()
    return renamed


def attach_new_sas_to_sailed(conn, sas_id: int, full_name: str) -> int:
    """Link past results only when this new card is the one no-SAS sailor.

    Requires a surname (two name tokens), one matching no-SAS name, and no
    second SAS card with that full name. Does not insert another sailor.
    """
    norm = _norm_person(full_name)
    if len(norm.split()) < 2:
        return 0
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM sas_id_personal
        WHERE lower(trim(regexp_replace(replace(replace(coalesce(full_name, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = %s
          AND sa_sailing_id::text <> %s
        """,
        (norm, str(sas_id)),
    )
    if int(cur.fetchone()[0] or 0) > 0:
        cur.close()
        return 0
    cur.execute(
        """
        SELECT COUNT(*) FROM identity_pending_sailors
        WHERE normalized_name = %s
          AND status IN ('pending', 'admin_confirmed_no_sas')
        """,
        (norm,),
    )
    if int(cur.fetchone()[0] or 0) < 1:
        cur.close()
        return 0
    linked = 0
    for seat, name_col, id_col, temp_col in (
        ("helm", "helm_name", "helm_sa_sailing_id", "helm_temp_id"),
        ("crew", "crew_name", "crew_sa_sailing_id", "crew_temp_id"),
        ("crew2", "crew2_name", "crew2_sa_sailing_id", "crew2_temp_id"),
        ("crew3", "crew3_name", "crew3_sa_sailing_id", "crew3_temp_id"),
    ):
        cur.execute(
            f"""
            SELECT DISTINCT {name_col}
            FROM results
            WHERE {id_col} IS NULL
              AND lower(trim(regexp_replace(replace(replace(coalesce({name_col}, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = %s
            """,
            (norm,),
        )
        sheets = [r[0] for r in cur.fetchall() if r and r[0]]
        cur.execute(
            "SELECT first_name, last_name FROM sas_id_personal WHERE sa_sailing_id::text = %s",
            (str(sas_id),),
        )
        person = cur.fetchone()
        if person:
            for sheet in sheets:
                nick = _sheet_first_if_nickname(sheet, person[0] or "", person[1] or "")
                if nick:
                    _add_nickname(cur, int(sas_id), nick)
        cur.execute(
            f"""
            UPDATE results r
            SET {id_col} = %s,
                {temp_col} = NULL,
                {name_col} = CASE
                    WHEN POSITION('&' IN COALESCE(r.{name_col}, '')) = 0
                     AND NULLIF(TRIM(s.first_name), '') IS NOT NULL
                     AND NULLIF(TRIM(s.last_name), '') IS NOT NULL
                    THEN TRIM(s.first_name) || ' ' || TRIM(s.last_name)
                    ELSE r.{name_col}
                END
            FROM sas_id_personal s
            WHERE s.sa_sailing_id::text = %s
              AND r.{id_col} IS NULL
              AND lower(trim(regexp_replace(replace(replace(coalesce(r.{name_col}, ''), '&#039;', ''''), '’', ''''), '\\s+', ' ', 'g'))) = %s
            """,
            (int(sas_id), str(sas_id), norm),
        )
        linked += cur.rowcount
    if linked < 1:
        conn.rollback()
        cur.close()
        return 0
    cur.execute(
        """
        DELETE FROM identity_pending_sailors
        WHERE normalized_name = %s
          AND status IN ('pending', 'admin_confirmed_no_sas')
        """,
        (norm,),
    )
    conn.commit()
    cur.close()
    print(
        f"[sas_member_scrape] linked sailed-no-sas {full_name} -> {sas_id} seats={linked}",
        file=sys.stderr,
    )
    return linked


def promote_nickname_no_sas(conn) -> int:
    """Match a sheet nickname only when the SAS surname matches and only one card has that nickname."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.normalized_name, min(s.sa_sailing_id::int)
        FROM identity_pending_sailors p
        JOIN sas_id_personal s
          ON lower(trim(s.last_name)) = regexp_replace(p.normalized_name, '^.* ', '')
         AND EXISTS (
              SELECT 1
              FROM unnest(string_to_array(lower(coalesce(s.nickname, '')), ',')) AS nick
              WHERE trim(nick) = split_part(p.normalized_name, ' ', 1)
         )
        WHERE p.status IN ('pending', 'admin_confirmed_no_sas')
          AND array_length(regexp_split_to_array(p.normalized_name, ' '), 1) >= 2
        GROUP BY p.normalized_name
        HAVING count(DISTINCT s.sa_sailing_id) = 1
        """
    )
    pairs = cur.fetchall()
    cur.close()
    linked = 0
    for norm, sas_id in pairs:
        try:
            linked += attach_new_sas_to_sailed(conn, int(sas_id), norm)
        except Exception as e:
            conn.rollback()
            print(f"[sas_member_scrape] nickname promote failed {norm}: {e}", file=sys.stderr)
    return linked


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
    try:
        recorded = sync_sailed_no_sas(conn)
        print(f"[sas_member_scrape] sailed-no-sas recorded/updated={recorded}", file=sys.stderr)
    except Exception as e:
        conn.rollback()
        print(f"[sas_member_scrape] sailed-no-sas sync failed: {e}", file=sys.stderr)
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
                if not existed:
                    try:
                        attach_new_sas_to_sailed(conn, current_id, data.get("full_name") or "")
                    except Exception as link_err:
                        conn.rollback()
                        print(f"[sas_member_scrape] no-sas link failed {current_id}: {link_err}", file=sys.stderr)
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
                    print(f"[sas_member_scrape] added {current_id} {data.get('full_name', '')}", file=sys.stderr)
                    if not existed:
                        try:
                            attach_new_sas_to_sailed(conn, current_id, data.get("full_name") or "")
                        except Exception as link_err:
                            conn.rollback()
                            print(f"[sas_member_scrape] no-sas link failed {current_id}: {link_err}", file=sys.stderr)
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
