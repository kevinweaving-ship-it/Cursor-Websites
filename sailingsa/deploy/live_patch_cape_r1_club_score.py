#!/usr/bin/env python3
"""Surgical live insert: club-admin R1 scoring for Cape Classic. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

if "def _require_regatta_score_edit" in src and "club-score-edit.js?v=ccr1" in src:
    print("ALREADY_PATCHED")
    raise SystemExit(0)

HELPERS = '''
def _normalize_account_role(role) -> str:
    if not role:
        return ""
    return str(role).strip().lower().replace(" ", "_").replace("-", "_")


def _session_role_is_club_admin(request: Request) -> bool:
    """True for Club Admin (scoped to one host club)."""
    return _normalize_account_role(_get_session_role(request)) in ("club_admin", "clubadmin")


def _session_admin_club_id(request: Request):
    try:
        if not table_exists("user_accounts") or not column_exists("user_accounts", "admin_club_id"):
            return None
        token = request.cookies.get("session") or (
            request.query_params.get("session") if request.query_params else None
        )
        if not token:
            return None
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            where_extra = " AND s.logout_time IS NULL" if column_exists("user_sessions", "logout_time") else ""
            cur.execute(
                """
                SELECT ua.admin_club_id FROM public.user_sessions s
                JOIN public.user_accounts ua ON ua.account_id = s.account_id
                WHERE s.session_id = %s AND s.expires_at > NOW()
                """
                + where_extra,
                (token,),
            )
            row = cur.fetchone()
            if not row or row.get("admin_club_id") is None:
                return None
            return int(row["admin_club_id"])
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception:
        return None


def _regatta_host_club_id(regatta_id):
    rid = str(regatta_id or "").strip()
    if not rid or not table_exists("regattas") or not column_exists("regattas", "host_club_id"):
        return None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT host_club_id FROM public.regattas WHERE regatta_id = %s LIMIT 1",
                (rid,),
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                return None
            return int(row[0])
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception:
        return None


def _session_can_edit_regatta_scores(request: Request, regatta_id) -> bool:
    if _session_role_is_super_admin(request):
        return True
    if not _session_role_is_club_admin(request):
        return False
    club_id = _session_admin_club_id(request)
    host_id = _regatta_host_club_id(regatta_id)
    if club_id is None or host_id is None:
        return False
    return int(club_id) == int(host_id)


def _require_regatta_score_edit(request: Request, regatta_id) -> None:
    if not _session_can_edit_regatta_scores(request, regatta_id):
        raise HTTPException(
            status_code=403,
            detail="Club admin can only enter scores for events hosted by their club",
        )


_RACE_PENALTY_CODES = ("DNC", "DNS", "DNF", "RET", "DSQ", "UFD", "BFD", "DPI", "OCS", "NSC", "DNE")


def _normalize_race_score_value(raw) -> str:
    v = str(raw or "").strip()
    if not v:
        return ""
    bare = v.strip("()").strip()
    up = bare.upper()
    if up in _RACE_PENALTY_CODES:
        return up
    if re.fullmatch(r"\\d+", bare):
        return str(int(bare))
    return bare


def _race_score_is_code(value: str) -> bool:
    return _normalize_race_score_value(value) in _RACE_PENALTY_CODES


def _race_score_unique_place(value: str, entries: int):
    v = _normalize_race_score_value(value)
    if not v or _race_score_is_code(v):
        return None
    if not re.fullmatch(r"\\d+", v):
        return None
    n = int(v)
    entries_n = max(int(entries or 0), 0)
    if entries_n and n == entries_n + 1:
        return None
    if n >= 1 and (not entries_n or n <= entries_n):
        return n
    return None


def _validate_race_score_value(value: str, entries: int) -> str:
    v = _normalize_race_score_value(value)
    if not v:
        return ""
    entries_n = max(int(entries or 0), 0)
    max_pts = entries_n + 1 if entries_n else 0
    if _race_score_is_code(v):
        return v
    if re.fullmatch(r"\\d+", v):
        n = int(v)
        if entries_n and 1 <= n <= max_pts:
            return str(n)
        if not entries_n and n >= 1:
            return str(n)
        raise HTTPException(
            status_code=400,
            detail=f"Use 1–{entries_n} for a place, or {max_pts} / OCS / DSQ for a code",
        )
    codes = "/".join(_RACE_PENALTY_CODES)
    raise HTTPException(
        status_code=400,
        detail=f"Use a place 1–{entries_n or 'n'}, {max_pts or 'n+1'}, or a code ({codes})",
    )


'''

anchor = '''    raise HTTPException(status_code=403, detail="Super admin required")


def _weeks_between(as_of_date: date, event_date_iso: Optional[str]) -> Optional[int]:
'''
if anchor not in src:
    raise SystemExit("ANCHOR_HELPERS_MISSING")
if "def _require_regatta_score_edit" not in src:
    src = src.replace(anchor, '''    raise HTTPException(status_code=403, detail="Super admin required")

''' + HELPERS + '''
def _weeks_between(as_of_date: date, event_date_iso: Optional[str]) -> Optional[int]:
''', 1)

old_auth = '''def patch_race_score(request: Request, result_id: int, body: dict):
    """Update a race score and automatically recalculate total/nett/discards and re-rank fleet"""
    _require_super_admin(request)
    import json
    import re
'''
new_auth = '''def patch_race_score(request: Request, result_id: int, body: dict):
    """Update a race score and automatically recalculate total/nett/discards and re-rank fleet"""
    import json
    import re
'''
if old_auth not in src:
    raise SystemExit("ANCHOR_PATCH_AUTH_MISSING")
src = src.replace(old_auth, new_auth, 1)

old_found = '''            if not result:
                raise HTTPException(status_code=404, detail="Result not found")

            block_id = result["block_id"]
'''
new_found = '''            if not result:
                raise HTTPException(status_code=404, detail="Result not found")
            _require_regatta_score_edit(request, result.get("regatta_id"))

            block_id = result["block_id"]
'''
if old_found not in src:
    raise SystemExit("ANCHOR_RESULT_FOUND_MISSING")
src = src.replace(old_found, new_found, 1)

old_val = '''            value_in = (value or "").strip()
            value_to_store = value_in

            if _regatta_slug_is_sa_pilot_standalone(str(regatta_id)) and value_in:
'''
new_val = '''            value_in = (value or "").strip()
            value_to_store = value_in
            if not _regatta_slug_is_sa_pilot_standalone(str(regatta_id)):
                value_to_store = _validate_race_score_value(value_in, fleet_entries)
                value_in = value_to_store
                value = value_to_store

            if _regatta_slug_is_sa_pilot_standalone(str(regatta_id)) and value_in:
'''
if old_val not in src:
    raise SystemExit("ANCHOR_VALUE_IN_MISSING")
src = src.replace(old_val, new_val, 1)

old_unique = '''            elif value and not _regatta_slug_is_sa_pilot_standalone(str(regatta_id)):
                num_match = re.search(r"^(\\d+)", value.strip())
                if num_match and not value.strip().startswith("("):
                    position = int(num_match.group(1))
                    cur.execute(
                        """
                        SELECT r.result_id, r.race_scores
                        FROM results r
                        WHERE r.block_id = %s
                          AND r.result_id != %s
                          AND r.race_scores IS NOT NULL
                        """,
                        (block_id, result_id),
                    )
                    other_results = cur.fetchall()

                    for other_res in other_results:
                        other_scores = other_res["race_scores"] or {}
                        if isinstance(other_scores, str):
                            other_scores = json.loads(other_scores)

                        other_value = other_scores.get(race_key, "").strip()
                        if not other_value:
                            continue

                        other_num_match = re.search(r"^(\\d+)", other_value)
                        if other_num_match and not other_value.startswith("("):
                            other_position = int(other_num_match.group(1))
                            if other_position == position:
                                raise HTTPException(
                                    status_code=400,
                                    detail=(
                                        f"Position {position} is already taken by another sailor "
                                        "in this race. Each position can only be used once."
                                    ),
                                )
'''
new_unique = '''            elif value and not _regatta_slug_is_sa_pilot_standalone(str(regatta_id)):
                place = _race_score_unique_place(value, fleet_entries)
                if place is not None:
                    cur.execute(
                        """
                        SELECT r.result_id, r.race_scores
                        FROM results r
                        WHERE r.block_id = %s
                          AND r.result_id != %s
                          AND r.race_scores IS NOT NULL
                        """,
                        (block_id, result_id),
                    )
                    for other_res in cur.fetchall() or []:
                        other_scores = other_res["race_scores"] or {}
                        if isinstance(other_scores, str):
                            other_scores = json.loads(other_scores)
                        other_place = _race_score_unique_place(
                            other_scores.get(race_key, ""), fleet_entries
                        )
                        if other_place == place:
                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"Place {place} is already used in this race. "
                                    f"{fleet_entries + 1} or OCS/DSQ can be used more than once."
                                ),
                            )
'''
if old_unique not in src:
    raise SystemExit("ANCHOR_UNIQUE_MISSING")
src = src.replace(old_unique, new_unique, 1)

old_js = '''            mm_card_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr113" defer></script>'
'''
new_js = '''            mm_card_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr113" defer></script><script src="/js/club-score-edit.js?v=ccr1" defer></script>'
'''
if old_js not in src:
    raise SystemExit("ANCHOR_MM_SCRIPT_MISSING")
src = src.replace(old_js, new_js, 1)

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("helpers", "def _require_regatta_score_edit" in src)
print("js", "club-score-edit.js?v=ccr1" in src)
print("auth", "_require_super_admin(request)" not in src.split("def patch_race_score", 1)[1][:220])
