"""TSL team racing — roster, matches, Appendix D scoring.

Slug-gated. Does not replace fleet racing, Appendix A, Dart 18, or Midmar Cup.
Teams/clubs/sailors reuse existing permanent IDs. No invented SAS IDs.

Match scoring (RRS Appendix D3, 3v3 positional):
  each boat scores her finishing place; DNS/DNF/DSQ/OCS/RET/NSC/DNE = 6;
  team total = sum of three boats + official team penalty; lowest total wins.
  Equal totals stay incomplete unless an official override names a winner.

Series ranking (RRS D4.2 round-robin):
  wins, then wins among tied teams, then points among tied teams (lower better),
  then the last race between two remaining teams, then average points vs common
  opponents. Remaining ties share a rank.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from fastapi import Body, Request

TSL_REGATTA_IDS = frozenset({"2026-10-17-mac-tsl-wc-team-sailing"})
TSL_BLOCK_SUFFIX = ":tsl"
CLASS_NAME = "TSL"
CLASS_ID = 148
BOATS_PER_TEAM = 3
BOATS_IN_RACE = 6
COLOURS = ("Blue", "Green")
PENALTY_CODES = frozenset({"DNS", "DNF", "DSQ", "OCS", "RET", "NSC", "DNE", "BFD"})
MAC_SEEDED_SAS = frozenset({"13516", "21052", "8612", "29414", "13517", "22974"})
MATIES_HELM_SAS = frozenset({"20389", "8178", "6497"})
EDEN_SAILOR_SAS = frozenset({"15711", "13488", "27609", "27610", "23531", "28588"})
CHAMPIONSHIP_TEAM_COUNT = 8
DEFAULT_PHYSICAL_BOATS = (
    ("Blue", 1),
    ("Blue", 2),
    ("Blue", 3),
    ("Green", 1),
    ("Green", 2),
    ("Green", 3),
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.tsl_event_teams (
  team_id bigserial PRIMARY KEY,
  regatta_id text NOT NULL,
  club_id integer NOT NULL REFERENCES public.clubs(club_id),
  team_name text NOT NULL,
  result_id bigint,
  sort_order integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (regatta_id, team_name)
);
CREATE TABLE IF NOT EXISTS public.tsl_event_team_boats (
  team_id bigint NOT NULL REFERENCES public.tsl_event_teams(team_id) ON DELETE CASCADE,
  boat_no smallint NOT NULL CHECK (boat_no BETWEEN 1 AND 3),
  helm_sas_id text,
  crew_sas_id text,
  PRIMARY KEY (team_id, boat_no)
);
CREATE TABLE IF NOT EXISTS public.tsl_event_matches (
  match_id bigserial PRIMARY KEY,
  regatta_id text NOT NULL,
  match_no integer NOT NULL,
  status text NOT NULL DEFAULT 'open',
  round_label text NOT NULL DEFAULT 'RR',
  team_a_id bigint REFERENCES public.tsl_event_teams(team_id),
  team_b_id bigint REFERENCES public.tsl_event_teams(team_id),
  colour_a text,
  colour_b text,
  score_a integer,
  score_b integer,
  winner_team_id bigint REFERENCES public.tsl_event_teams(team_id),
  loser_team_id bigint REFERENCES public.tsl_event_teams(team_id),
  override_winner_team_id bigint REFERENCES public.tsl_event_teams(team_id),
  override_reason text,
  override_by text,
  override_at timestamptz,
  completed_at timestamptz,
  team_penalty_a integer NOT NULL DEFAULT 0,
  team_penalty_b integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (regatta_id, match_no)
);
CREATE TABLE IF NOT EXISTS public.tsl_event_match_boats (
  match_id bigint NOT NULL REFERENCES public.tsl_event_matches(match_id) ON DELETE CASCADE,
  team_id bigint NOT NULL REFERENCES public.tsl_event_teams(team_id),
  pairing_no smallint NOT NULL CHECK (pairing_no BETWEEN 1 AND 3),
  bow_number text,
  sail_number text,
  helm_sas_id text,
  crew_sas_id text,
  finish_place smallint,
  penalty_status text,
  PRIMARY KEY (match_id, team_id, pairing_no)
);
CREATE TABLE IF NOT EXISTS public.tsl_event_boats (
  boat_id bigserial PRIMARY KEY,
  regatta_id text NOT NULL,
  colour text NOT NULL CHECK (colour IN ('Blue', 'Green')),
  boat_no smallint NOT NULL CHECK (boat_no BETWEEN 1 AND 3),
  bow_number text,
  sail_number text,
  UNIQUE (regatta_id, colour, boat_no)
);
CREATE TABLE IF NOT EXISTS public.tsl_event_settings (
  regatta_id text PRIMARY KEY,
  format text NOT NULL DEFAULT 'rr28',
  flight_a jsonb,
  flight_b jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.tsl_event_audit (
  audit_id bigserial PRIMARY KEY,
  regatta_id text NOT NULL,
  match_id bigint,
  team_id bigint,
  action text NOT NULL,
  reason text,
  actor text,
  payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
"""


def is_tsl_regatta(regatta_id: str) -> bool:
    return str(regatta_id or "").strip() in TSL_REGATTA_IDS


def require_championship_teams(team_ids) -> None:
    ids = [int(t) for t in (team_ids or [])]
    if len(ids) != CHAMPIONSHIP_TEAM_COUNT:
        raise ValueError("Do not generate an eight-team schedule until eight teams are registered")


def _sex_letter(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw.startswith("M"):
        return "M"
    if raw.startswith("F"):
        return "F"
    return ""


def _save_sailor_sex(cur, sas_id: str, sex: str) -> None:
    sid = str(sas_id or "").strip()
    letter = _sex_letter(sex)
    if not sid or letter not in ("M", "F"):
        return
    cur.execute(
        """
        UPDATE public.sas_id_personal
           SET gender = %s
         WHERE sa_sailing_id::text = %s
        """,
        (letter, sid),
    )


def _boat_sex(raw: dict, role: str) -> str:
    key = f"{role}_sex"
    person = raw.get(role) if isinstance(raw.get(role), dict) else {}
    return _sex_letter(raw.get(key) or (person or {}).get("sex") or (person or {}).get("gender"))


def display_name(row: dict) -> str:
    first = str(row.get("first_name") or "").strip()
    last = str(row.get("last_name") or "").strip()
    joined = f"{first} {last}".strip()
    if joined:
        return joined
    return str(row.get("full_name") or "").strip()


def _norm_club(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().upper())


def sailor_club_codes(row: dict) -> list[str]:
    out = []
    for key in ("primary_club", "club_1", "club"):
        code = _norm_club(row.get(key))
        if code and code not in out and code not in ("UNASSIGNED", "NULL", "NONE"):
            out.append(code)
    return out


def sailor_allowed_for_club(sailor: dict, club_abbrev: str, club_name: str = "") -> bool:
    """Include sailors with no membership; exclude only a verified other club."""
    codes = sailor_club_codes(sailor)
    if not codes:
        return True
    want = {_norm_club(club_abbrev), _norm_club(club_name)}
    want.discard("")
    return any(c in want for c in codes)


def roster_sas_ids(boats: list[dict]) -> list[str]:
    ids = []
    for b in boats or []:
        for key in ("helm_sas_id", "crew_sas_id"):
            sid = str((b.get(key) if not isinstance(b.get(key), dict) else b[key].get("sas_id")) or "").strip()
            if not sid and isinstance(b.get(key.replace("_sas_id", "")), dict):
                sid = str(b[key.replace("_sas_id", "")].get("sas_id") or "").strip()
            if sid:
                ids.append(sid)
        helm = b.get("helm") if isinstance(b.get("helm"), dict) else None
        crew = b.get("crew") if isinstance(b.get("crew"), dict) else None
        if helm and helm.get("sas_id"):
            ids.append(str(helm["sas_id"]).strip())
        if crew and crew.get("sas_id"):
            ids.append(str(crew["sas_id"]).strip())
    return [x for x in ids if x]


def validate_roster_boats(boats: list[dict]) -> list[str]:
    errors = []
    seen = {}
    for raw in boats or []:
        boat_no = int(raw.get("boat_no") or raw.get("pairing_no") or 0)
        helm = raw.get("helm") if isinstance(raw.get("helm"), dict) else {}
        crew = raw.get("crew") if isinstance(raw.get("crew"), dict) else {}
        helm_id = str(raw.get("helm_sas_id") or helm.get("sas_id") or "").strip()
        crew_id = str(raw.get("crew_sas_id") or crew.get("sas_id") or "").strip()
        if helm_id and crew_id and helm_id == crew_id:
            errors.append(f"Boat {boat_no or '?'}: helm and crew are the same sailor")
        for sid, role in ((helm_id, "helm"), (crew_id, "crew")):
            if not sid:
                continue
            if sid in seen:
                errors.append(f"Sailor {sid} is already {seen[sid]} — one position per team")
            else:
                seen[sid] = f"boat {boat_no} {role}"
    return errors


def boat_points(place: Optional[int], penalty: Optional[str], boats_in_race: int = BOATS_IN_RACE) -> Optional[int]:
    code = str(penalty or "").strip().upper()
    if code in PENALTY_CODES:
        return int(boats_in_race)
    if place is None or place == "":
        return None
    try:
        n = int(place)
    except (TypeError, ValueError):
        return None
    if n < 1 or n > boats_in_race:
        return None
    return n


def score_match(
    boats_a: list[dict],
    boats_b: list[dict],
    *,
    team_penalty_a: int = 0,
    team_penalty_b: int = 0,
    override_winner: Optional[str] = None,
) -> dict:
    """Score one 3v3 match. override_winner is 'A', 'B', or None."""
    errors = []
    all_boats = list(boats_a or []) + list(boats_b or [])
    if len(boats_a or []) != BOATS_PER_TEAM or len(boats_b or []) != BOATS_PER_TEAM:
        errors.append("Each team must have exactly three boats")

    places = []
    bows = []
    sails = []
    for i, b in enumerate(all_boats):
        pen = str(b.get("penalty_status") or "").strip().upper()
        pts = boat_points(b.get("finish_place"), pen)
        if pts is None:
            errors.append(f"Boat {i + 1} needs a finishing place or a penalty status")
        elif pen not in PENALTY_CODES:
            places.append(pts)
        bow = str(b.get("bow_number") or "").strip()
        sail = str(b.get("sail_number") or "").strip()
        if bow:
            if bow in bows:
                errors.append(f"Duplicate bow number {bow} in this match")
            bows.append(bow)
        if sail:
            if sail in sails:
                errors.append(f"Duplicate sail number {sail} in this match")
            sails.append(sail)

    if places and len(places) != len(set(places)):
        errors.append("Finishing places 1–6 must be unique among boats that finished")

    def _sum(side):
        total = 0
        for b in side or []:
            pts = boat_points(b.get("finish_place"), b.get("penalty_status"))
            if pts is None:
                return None
            total += pts
        return total

    score_a = _sum(boats_a)
    score_b = _sum(boats_b)
    if score_a is not None:
        score_a += int(team_penalty_a or 0)
    if score_b is not None:
        score_b += int(team_penalty_b or 0)

    winner = None
    loser = None
    ov = str(override_winner or "").strip().upper()
    if ov in ("A", "B"):
        winner = ov
        loser = "B" if ov == "A" else "A"
    elif score_a is not None and score_b is not None and score_a != score_b:
        winner = "A" if score_a < score_b else "B"
        loser = "B" if winner == "A" else "A"
    elif score_a is not None and score_b is not None and score_a == score_b:
        errors.append("Scores are tied — an official override with a reason is required")

    complete = winner is not None and not [
        e for e in errors if not e.startswith("Scores are tied")
    ]
    if ov in ("A", "B"):
        complete = winner is not None and not [
            e for e in errors if "tied" not in e.lower()
        ]
        errors = [e for e in errors if "tied" not in e.lower()]

    return {
        "score_a": score_a,
        "score_b": score_b,
        "winner": winner,
        "loser": loser,
        "complete": bool(complete and winner),
        "errors": errors,
    }


def _head_to_head(matches: list[dict], team_ids: set[int]) -> dict[int, dict]:
    stats = {tid: {"wins": 0, "points": 0, "races": 0, "last_win": None} for tid in team_ids}
    relevant = []
    for m in matches:
        a = m.get("winner_team_id")
        b = m.get("loser_team_id")
        ta = m.get("team_a_id")
        tb = m.get("team_b_id")
        if m.get("status") != "complete":
            continue
        if ta not in team_ids or tb not in team_ids:
            continue
        relevant.append(m)
        if a in stats:
            stats[a]["wins"] += 1
        sa = m.get("score_a")
        sb = m.get("score_b")
        if sa is not None:
            stats[ta]["points"] += int(sa)
            stats[ta]["races"] += 1
        if sb is not None:
            stats[tb]["points"] += int(sb)
            stats[tb]["races"] += 1
    if relevant:
        last = relevant[-1]
        if last.get("winner_team_id") in stats:
            stats[last["winner_team_id"]]["last_win"] = 1
            if last.get("loser_team_id") in stats:
                stats[last["loser_team_id"]]["last_win"] = 0
    return stats


def _avg_vs_common(matches: list[dict], team_ids: set[int], all_ids: list[int]) -> dict[int, float]:
    opponents = {tid: {} for tid in team_ids}
    for m in matches:
        if m.get("status") != "complete":
            continue
        ta, tb = m.get("team_a_id"), m.get("team_b_id")
        sa, sb = m.get("score_a"), m.get("score_b")
        if sa is None or sb is None:
            continue
        if ta in team_ids:
            opponents[ta].setdefault(tb, []).append(int(sa))
        if tb in team_ids:
            opponents[tb].setdefault(ta, []).append(int(sb))
    common = None
    for tid in team_ids:
        s = set(opponents[tid].keys()) - team_ids
        common = s if common is None else (common & s)
    common = common or set()
    out = {}
    for tid in team_ids:
        pts = []
        for opp in common:
            pts.extend(opponents[tid].get(opp) or [])
        out[tid] = (sum(pts) / len(pts)) if pts else 10**9
    return out


def rank_standings(teams: list[dict], matches: list[dict]) -> list[dict]:
    """Appendix D4.2 ranking. One row per team. Non-participants get — cells."""
    by_id = {int(t["team_id"]): dict(t) for t in teams}
    match_nos = sorted({int(m["match_no"]) for m in matches if m.get("match_no")})
    stats = {}
    for tid, team in by_id.items():
        cells = {f"M{n}": "—" for n in match_nos}
        stats[tid] = {
            **team,
            "wins": 0,
            "losses": 0,
            "points_for": 0,
            "points_against": 0,
            "cells": cells,
            "win_pct": 0.0,
        }

    complete = [m for m in matches if str(m.get("status") or "") == "complete"]
    for m in complete:
        label = f"M{int(m['match_no'])}"
        winner = m.get("winner_team_id")
        loser = m.get("loser_team_id")
        ta, tb = m.get("team_a_id"), m.get("team_b_id")
        sa, sb = m.get("score_a"), m.get("score_b")
        if winner in stats:
            stats[winner]["wins"] += 1
            stats[winner]["cells"][label] = "W"
        if loser in stats:
            stats[loser]["losses"] += 1
            stats[loser]["cells"][label] = "L"
        if ta in stats and sa is not None:
            stats[ta]["points_for"] += int(sa)
            stats[ta]["points_against"] += int(sb or 0)
        if tb in stats and sb is not None:
            stats[tb]["points_for"] += int(sb)
            stats[tb]["points_against"] += int(sa or 0)

    for row in stats.values():
        played = row["wins"] + row["losses"]
        row["win_pct"] = round(100.0 * row["wins"] / played, 1) if played else 0.0

    rows = list(stats.values())

    def split_group(group: list[dict], keyfn):
        buckets = {}
        for r in group:
            buckets.setdefault(keyfn(r), []).append(r)
        ordered = []
        for k in sorted(buckets):
            ordered.append(buckets[k])
        return ordered

    groups = [rows]
    # 1. wins (higher better) — invert via negative
    groups = [g for part in groups for g in split_group(part, lambda r: -r["wins"])]
    resolved = []
    for g in groups:
        if len(g) <= 1:
            resolved.append(g)
            continue
        ids = {int(r["team_id"]) for r in g}
        h2h = _head_to_head(complete, ids)
        # 2. wins among tied teams
        parts = split_group(g, lambda r: -h2h[int(r["team_id"])]["wins"])
        next_parts = []
        for p in parts:
            if len(p) <= 1:
                next_parts.append(p)
                continue
            # 3. points among tied teams (lower better)
            p2 = split_group(p, lambda r: h2h[int(r["team_id"])]["points"])
            for q in p2:
                if len(q) == 2:
                    # 4. last race between the two
                    last = {int(r["team_id"]): h2h[int(r["team_id"])].get("last_win") for r in q}
                    if None not in last.values() and len(set(last.values())) == 2:
                        q = sorted(q, key=lambda r: 0 if last[int(r["team_id"])] == 1 else 1)
                        next_parts.append([q[0]])
                        next_parts.append([q[1]])
                        continue
                if len(q) > 1:
                    avgs = _avg_vs_common(complete, {int(r["team_id"]) for r in q}, list(by_id))
                    q = sorted(q, key=lambda r: avgs.get(int(r["team_id"]), 10**9))
                    # keep equal avgs together
                    next_parts.extend(split_group(q, lambda r: avgs.get(int(r["team_id"]), 10**9)))
                else:
                    next_parts.append(q)
        resolved.extend(next_parts)

    ranked = []
    rank = 1
    for g in resolved:
        for r in g:
            row = dict(r)
            row["rank"] = rank
            ranked.append(row)
        rank += len(g)
    return ranked


def match_does_not_use_current_roster(match_boats: list[dict], roster_boats: list[dict]) -> bool:
    """True when historical allocations differ from the current master roster."""
    roster = {}
    for b in roster_boats or []:
        n = int(b.get("boat_no") or 0)
        roster[n] = (
            str(b.get("helm_sas_id") or (b.get("helm") or {}).get("sas_id") or ""),
            str(b.get("crew_sas_id") or (b.get("crew") or {}).get("sas_id") or ""),
        )
    for b in match_boats or []:
        n = int(b.get("pairing_no") or b.get("boat_no") or 0)
        pair = (
            str(b.get("helm_sas_id") or ""),
            str(b.get("crew_sas_id") or ""),
        )
        if n in roster and pair != roster[n] and any(pair):
            return True
    return False


def _escape_like(s: str) -> str:
    return str(s or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _block_id(regatta_id: str) -> str:
    return f"{regatta_id}{TSL_BLOCK_SUFFIX}"


def _json_payload(value: Any):
    try:
        from psycopg2.extras import Json
        return Json(value)
    except Exception:
        return json.dumps(value)


def ensure_schema(cur) -> None:
    cur.execute(SCHEMA_SQL)
    cur.execute(
        """
        ALTER TABLE public.tsl_event_teams
          ADD COLUMN IF NOT EXISTS team_abbrev text
        """
    )
    cur.execute(
        """
        ALTER TABLE public.tsl_event_team_boats
          ALTER COLUMN helm_sas_id DROP NOT NULL
        """
    )
    cur.execute(
        """
        ALTER TABLE public.tsl_event_team_boats
          ALTER COLUMN crew_sas_id DROP NOT NULL
        """
    )
    cur.execute(
        """
        ALTER TABLE public.tsl_event_team_boats
          ADD COLUMN IF NOT EXISTS helm_sex text
        """
    )
    cur.execute(
        """
        ALTER TABLE public.tsl_event_team_boats
          ADD COLUMN IF NOT EXISTS crew_sex text
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS tsl_event_teams_abbrev_uidx
          ON public.tsl_event_teams (regatta_id, team_abbrev)
          WHERE team_abbrev IS NOT NULL AND team_abbrev <> ''
        """
    )
    for col, typ in (
        ("phase", "text"),
        ("flight", "text"),
        ("sailoff_slot", "smallint"),
    ):
        cur.execute(f"ALTER TABLE public.tsl_event_matches ADD COLUMN IF NOT EXISTS {col} {typ}")
    cur.execute(
        "ALTER TABLE public.tsl_event_match_boats ADD COLUMN IF NOT EXISTS physical_boat_id bigint"
    )
    cur.execute(
        """
        INSERT INTO public.tsl_event_settings (regatta_id, format)
        SELECT %s, 'rr28'
        WHERE NOT EXISTS (SELECT 1 FROM public.tsl_event_settings WHERE regatta_id = %s)
        """,
        ("2026-10-17-mac-tsl-wc-team-sailing", "2026-10-17-mac-tsl-wc-team-sailing"),
    )


def _club_row(cur, club_id: int) -> Optional[dict]:
    cur.execute(
        """
        SELECT club_id,
               TRIM(COALESCE(club_abbrev, '')) AS club_abbrev,
               TRIM(COALESCE(club_fullname, '')) AS club_name
        FROM public.clubs
        WHERE club_id = %s
        LIMIT 1
        """,
        (int(club_id),),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _load_sailor(cur, sas_id: str) -> Optional[dict]:
    sid = str(sas_id or "").strip()
    if not sid:
        return None
    cur.execute(
        """
        SELECT sa_sailing_id::text AS sas_id,
               TRIM(COALESCE(full_name, '')) AS full_name,
               TRIM(COALESCE(first_name, '')) AS first_name,
               TRIM(COALESCE(last_name, '')) AS last_name,
               TRIM(COALESCE(primary_club, '')) AS primary_club,
               TRIM(COALESCE(club_1::text, '')) AS club_1,
               TRIM(COALESCE(gender, '')) AS gender
        FROM public.sas_id_personal
        WHERE sa_sailing_id::text = %s
        LIMIT 1
        """,
        (sid,),
    )
    row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    sex = _sex_letter(d.get("gender"))
    return {
        "sas_id": str(d.get("sas_id") or sid),
        "name": display_name(d),
        "full_name": d.get("full_name") or "",
        "club": (d.get("primary_club") or d.get("club_1") or "").strip() or None,
        "primary_club": d.get("primary_club") or "",
        "club_1": d.get("club_1") or "",
        "gender": d.get("gender") or "",
        "sex": sex,
    }


def _team_warnings(boats: list[dict]) -> list[str]:
    warnings = []
    filled = 0
    for b in boats:
        helm = b.get("helm") or {}
        crew = b.get("crew") or {}
        if helm.get("sas_id") or crew.get("sas_id"):
            filled += 1
        if (helm.get("name") or crew.get("name")) and not (helm.get("sas_id") and crew.get("sas_id")):
            warnings.append(f"Boat {b.get('boat_no')}: missing SAS ID — not invented")
    if filled < BOATS_PER_TEAM:
        warnings.append("Roster incomplete (need three helm/crew pairings)")
    return warnings


def _fetch_team_boats(cur, team_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT boat_no, helm_sas_id, crew_sas_id,
               TRIM(COALESCE(helm_sex, '')) AS helm_sex,
               TRIM(COALESCE(crew_sex, '')) AS crew_sex
        FROM public.tsl_event_team_boats
        WHERE team_id = %s
        ORDER BY boat_no
        """,
        (int(team_id),),
    )
    out = []
    by_no = {int(r["boat_no"]): dict(r) for r in (cur.fetchall() or [])}
    for n in range(1, BOATS_PER_TEAM + 1):
        row = by_no.get(n) or {"boat_no": n, "helm_sas_id": None, "crew_sas_id": None}
        helm = _load_sailor(cur, row.get("helm_sas_id")) if row.get("helm_sas_id") else None
        crew = _load_sailor(cur, row.get("crew_sas_id")) if row.get("crew_sas_id") else None
        helm_sex = _sex_letter(row.get("helm_sex"))
        crew_sex = _sex_letter(row.get("crew_sex"))
        if helm and helm_sex:
            helm["sex"] = helm_sex
        elif helm_sex:
            helm = {"sas_id": "", "name": "", "sex": helm_sex}
        if crew and crew_sex:
            crew["sex"] = crew_sex
        elif crew_sex:
            crew = {"sas_id": "", "name": "", "sex": crew_sex}
        out.append({"boat_no": n, "helm": helm, "crew": crew})
    return out


def _serialize_team(cur, team: dict) -> dict:
    club = _club_row(cur, int(team["club_id"])) or {}
    abbrev = (club.get("club_abbrev") or "").strip()
    boats = _fetch_team_boats(cur, int(team["team_id"]))
    team_abbrev = (team.get("team_abbrev") or abbrev or "").strip()
    return {
        "team_id": int(team["team_id"]),
        "club_id": int(team["club_id"]),
        "club_abbrev": abbrev,
        "club_name": (club.get("club_name") or "").strip(),
        "club_logo": f"/api/club-logo/{abbrev}" if abbrev else "",
        "team_name": (team.get("team_name") or "").strip(),
        "team_abbrev": team_abbrev,
        "result_id": int(team["result_id"]) if team.get("result_id") else None,
        "sort_order": int(team.get("sort_order") or 1),
        "boats": boats,
        "warnings": _team_warnings(boats),
    }


def load_teams(cur, regatta_id: str) -> list[dict]:
    cur.execute(
        """
        SELECT team_id, regatta_id, club_id, team_name, team_abbrev, result_id, sort_order
        FROM public.tsl_event_teams
        WHERE regatta_id = %s
        ORDER BY sort_order, team_id
        """,
        (regatta_id,),
    )
    return [_serialize_team(cur, dict(r)) for r in (cur.fetchall() or [])]


def load_matches(cur, regatta_id: str) -> list[dict]:
    cur.execute(
        """
        SELECT match_id, regatta_id, match_no, status, round_label,
               team_a_id, team_b_id, colour_a, colour_b, score_a, score_b,
               winner_team_id, loser_team_id, override_winner_team_id,
               override_reason, override_by, override_at, completed_at,
               team_penalty_a, team_penalty_b, phase, flight, sailoff_slot
        FROM public.tsl_event_matches
        WHERE regatta_id = %s
        ORDER BY match_no
        """,
        (regatta_id,),
    )
    rows = [dict(r) for r in (cur.fetchall() or [])]
    out = []
    for m in rows:
        cur.execute(
            """
            SELECT team_id, pairing_no, bow_number, sail_number,
                   helm_sas_id, crew_sas_id, finish_place, penalty_status,
                   physical_boat_id
            FROM public.tsl_event_match_boats
            WHERE match_id = %s
            ORDER BY team_id, pairing_no
            """,
            (int(m["match_id"]),),
        )
        boats = [dict(b) for b in (cur.fetchall() or [])]
        item = dict(m)
        item["label"] = f"M{int(m['match_no'])}"
        item["boats"] = boats
        out.append(item)
    return out


def _col_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def _sync_result_row(cur, team: dict, boats: list[dict]) -> int:
    """One public.results row per team. Reuse existing row. No duplicates."""
    rid = team["regatta_id"]
    block = _block_id(rid)
    names_h = []
    names_c = []
    first_h = None
    first_c = None
    for b in boats:
        helm = b.get("helm") or {}
        crew = b.get("crew") or {}
        if helm.get("name"):
            names_h.append(helm["name"])
        if crew.get("name"):
            names_c.append(crew["name"])
        if first_h is None and helm.get("sas_id"):
            first_h = helm["sas_id"]
        if first_c is None and crew.get("sas_id"):
            first_c = crew["sas_id"]
    club = _club_row(cur, int(team["club_id"])) or {}
    cols = {
        "regatta_id": rid,
        "block_id": block,
        "class_original": CLASS_NAME,
        "boat_name": team["team_name"],
        "club_id": int(team["club_id"]),
        "club_raw": club.get("club_abbrev") or "",
        "helm_name": "; ".join(names_h),
        "crew_name": "; ".join(names_c),
        "manually_parsed": False,
    }
    if _col_exists(cur, "results", "class_canonical"):
        cols["class_canonical"] = CLASS_NAME
    if _col_exists(cur, "results", "class_id"):
        cols["class_id"] = CLASS_ID
    if _col_exists(cur, "results", "raced"):
        cols["raced"] = False
    if first_h and str(first_h).isdigit():
        cols["helm_sa_sailing_id"] = int(first_h)
    if first_c and str(first_c).isdigit():
        cols["crew_sa_sailing_id"] = int(first_c)

    result_id = team.get("result_id")
    if result_id:
        cur.execute("SELECT result_id FROM results WHERE result_id = %s", (int(result_id),))
        if not cur.fetchone():
            result_id = None
    if not result_id:
        cur.execute(
            """
            SELECT result_id FROM results
            WHERE regatta_id = %s AND block_id = %s AND boat_name = %s
            ORDER BY result_id LIMIT 1
            """,
            (rid, block, team["team_name"]),
        )
        found = cur.fetchone()
        result_id = int(found["result_id"]) if found else None

    if result_id:
        sets = ", ".join(f"{k} = %s" for k in cols)
        cur.execute(f"UPDATE results SET {sets} WHERE result_id = %s", list(cols.values()) + [int(result_id)])
        return int(result_id)

    if "race_scores" in _existing_result_cols(cur):
        cols["race_scores"] = _json_payload({})
    names = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    cur.execute(f"INSERT INTO results ({names}) VALUES ({placeholders}) RETURNING result_id", list(cols.values()))
    return int(cur.fetchone()["result_id"])


def _existing_result_cols(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'results'
        """
    )
    return {r["column_name"] for r in (cur.fetchall() or [])}


def _write_standings_to_results(cur, regatta_id: str, standings: list[dict], matches: list[dict]) -> None:
    complete_n = len([m for m in matches if m.get("status") == "complete"])
    block = _block_id(regatta_id)
    cur.execute(
        "UPDATE public.regatta_blocks SET races_sailed = %s WHERE block_id = %s",
        (len(matches), block),
    )
    for row in standings:
        scores = {}
        for m in matches:
            label_r = f"R{int(m['match_no'])}"
            scores[label_r] = row["cells"].get(f"M{int(m['match_no'])}", "—")
        result_id = row.get("result_id")
        if not result_id:
            continue
        sets = ["rank = %s"]
        args: list[Any] = [row.get("rank")]
        if _col_exists(cur, "results", "race_scores"):
            sets.append("race_scores = %s")
            args.append(_json_payload(scores))
        if _col_exists(cur, "results", "races_sailed"):
            sets.append("races_sailed = %s")
            args.append(complete_n)
        if _col_exists(cur, "results", "total_points_raw"):
            sets.append("total_points_raw = %s")
            args.append(row.get("wins") or 0)
        if _col_exists(cur, "results", "nett_points_raw"):
            sets.append("nett_points_raw = %s")
            args.append(row.get("wins") or 0)
        args.append(int(result_id))
        cur.execute(f"UPDATE results SET {', '.join(sets)} WHERE result_id = %s", args)


def _audit(cur, regatta_id: str, action: str, *, match_id=None, team_id=None, reason=None, actor=None, payload=None):
    cur.execute(
        """
        INSERT INTO public.tsl_event_audit
          (regatta_id, match_id, team_id, action, reason, actor, payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (regatta_id, match_id, team_id, action, reason, actor or "super_admin", _json_payload(payload or {})),
    )


def _unique_team_identity(cur, regatta_id: str, team_name: str, team_abbrev: str, exclude_id: Optional[int] = None) -> Optional[str]:
    name = (team_name or "").strip()
    abbrev = (team_abbrev or "").strip()
    if not name:
        return "Team name is required"
    cur.execute(
        """
        SELECT team_id FROM tsl_event_teams
        WHERE regatta_id = %s AND lower(team_name) = lower(%s)
          AND (%s IS NULL OR team_id <> %s)
        LIMIT 1
        """,
        (regatta_id, name, exclude_id, exclude_id),
    )
    if cur.fetchone():
        return f"Team name {name!r} is already used at this event"
    if abbrev:
        cur.execute(
            """
            SELECT team_id FROM tsl_event_teams
            WHERE regatta_id = %s AND lower(coalesce(team_abbrev, '')) = lower(%s)
              AND (%s IS NULL OR team_id <> %s)
            LIMIT 1
            """,
            (regatta_id, abbrev, exclude_id, exclude_id),
        )
        if cur.fetchone():
            return f"Team abbreviation {abbrev!r} is already used at this event"
    return None


def upsert_team(cur, regatta_id: str, body: dict, *, actor: str = "super_admin") -> dict:
    ensure_schema(cur)
    club_id = int(body.get("club_id") or 0)
    club = _club_row(cur, club_id)
    if not club:
        raise ValueError("Club not found — use an existing SailingSA club")
    team_name = str(body.get("team_name") or club.get("club_abbrev") or club.get("club_name") or "").strip()
    team_abbrev = str(body.get("team_abbrev") or club.get("club_abbrev") or "").strip()
    team_id = body.get("team_id")
    boats_in = body.get("boats") or []
    err = validate_roster_boats(boats_in)
    if err:
        raise ValueError("; ".join(err))
    ident = _unique_team_identity(cur, regatta_id, team_name, team_abbrev, int(team_id) if team_id else None)
    if ident:
        raise ValueError(ident)

    existing_sex = {}
    if team_id:
        cur.execute(
            """
            SELECT boat_no,
                   TRIM(COALESCE(helm_sex, '')) AS helm_sex,
                   TRIM(COALESCE(crew_sex, '')) AS crew_sex
              FROM public.tsl_event_team_boats
             WHERE team_id = %s
            """,
            (int(team_id),),
        )
        existing_sex = {int(r["boat_no"]): dict(r) for r in (cur.fetchall() or [])}

    resolved_boats = []
    for n in range(1, BOATS_PER_TEAM + 1):
        raw = next((b for b in boats_in if int(b.get("boat_no") or 0) == n), {}) or {}
        helm_id = str(raw.get("helm_sas_id") or (raw.get("helm") or {}).get("sas_id") or "").strip()
        crew_id = str(raw.get("crew_sas_id") or (raw.get("crew") or {}).get("sas_id") or "").strip()
        helm = _load_sailor(cur, helm_id) if helm_id else None
        crew = _load_sailor(cur, crew_id) if crew_id else None
        if helm_id and not helm:
            raise ValueError(f"Helm SAS {helm_id} is not an existing sailor — SAS IDs are never invented")
        if crew_id and not crew:
            raise ValueError(f"Crew SAS {crew_id} is not an existing sailor — SAS IDs are never invented")
        prev = existing_sex.get(n) or {}
        helm_sex = _boat_sex(raw, "helm") or _sex_letter(prev.get("helm_sex"))
        crew_sex = _boat_sex(raw, "crew") or _sex_letter(prev.get("crew_sex"))
        if helm and helm_sex:
            helm["sex"] = helm_sex
        if crew and crew_sex:
            crew["sex"] = crew_sex
        _save_sailor_sex(cur, helm_id, helm_sex)
        _save_sailor_sex(cur, crew_id, crew_sex)
        resolved_boats.append({
            "boat_no": n,
            "helm": helm,
            "crew": crew,
            "helm_sas_id": helm_id or None,
            "crew_sas_id": crew_id or None,
            "helm_sex": helm_sex or None,
            "crew_sex": crew_sex or None,
        })

    if team_id:
        cur.execute(
            """
            UPDATE tsl_event_teams
               SET club_id = %s, team_name = %s, team_abbrev = %s
             WHERE team_id = %s AND regatta_id = %s
            RETURNING team_id, club_id, team_name, team_abbrev, result_id, sort_order
            """,
            (club_id, team_name, team_abbrev or None, int(team_id), regatta_id),
        )
        team = cur.fetchone()
        if not team:
            raise ValueError("Team not found")
        team = dict(team)
        team["regatta_id"] = regatta_id
    else:
        cur.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM tsl_event_teams WHERE regatta_id = %s",
            (regatta_id,),
        )
        sort_n = int((cur.fetchone() or {}).get("n") or 1)
        cur.execute(
            """
            INSERT INTO tsl_event_teams (regatta_id, club_id, team_name, team_abbrev, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (regatta_id, team_name)
            DO UPDATE SET club_id = EXCLUDED.club_id, team_abbrev = COALESCE(EXCLUDED.team_abbrev, tsl_event_teams.team_abbrev)
            RETURNING team_id, club_id, team_name, team_abbrev, result_id, sort_order
            """,
            (regatta_id, club_id, team_name, team_abbrev or None, sort_n),
        )
        team = dict(cur.fetchone())
        team["regatta_id"] = regatta_id

    for b in resolved_boats:
        cur.execute(
            """
            INSERT INTO tsl_event_team_boats (team_id, boat_no, helm_sas_id, crew_sas_id, helm_sex, crew_sex)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (team_id, boat_no)
            DO UPDATE SET helm_sas_id = EXCLUDED.helm_sas_id,
                          crew_sas_id = EXCLUDED.crew_sas_id,
                          helm_sex = EXCLUDED.helm_sex,
                          crew_sex = EXCLUDED.crew_sex
            """,
            (int(team["team_id"]), b["boat_no"], b["helm_sas_id"], b["crew_sas_id"], b.get("helm_sex"), b.get("crew_sex")),
        )

    result_id = _sync_result_row(cur, team, resolved_boats)
    cur.execute("UPDATE tsl_event_teams SET result_id = %s WHERE team_id = %s", (result_id, int(team["team_id"])))
    team["result_id"] = result_id
    _audit(cur, regatta_id, "team_upsert", team_id=int(team["team_id"]), actor=actor, payload={"team_name": team_name})
    return _serialize_team(cur, team)


def delete_team(cur, regatta_id: str, team_id: int, *, actor: str = "super_admin") -> None:
    cur.execute(
        """
        SELECT match_id FROM tsl_event_matches
        WHERE regatta_id = %s AND status = 'complete'
          AND (team_a_id = %s OR team_b_id = %s)
        LIMIT 1
        """,
        (regatta_id, int(team_id), int(team_id)),
    )
    if cur.fetchone():
        raise ValueError("Cannot delete a team that has a completed match")
    cur.execute(
        "SELECT result_id FROM tsl_event_teams WHERE team_id = %s AND regatta_id = %s",
        (int(team_id), regatta_id),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Team not found")
    result_id = row.get("result_id")
    cur.execute("DELETE FROM tsl_event_matches WHERE regatta_id = %s AND (team_a_id = %s OR team_b_id = %s) AND status <> 'complete'", (regatta_id, int(team_id), int(team_id)))
    cur.execute("DELETE FROM tsl_event_teams WHERE team_id = %s AND regatta_id = %s", (int(team_id), regatta_id))
    if result_id:
        cur.execute("DELETE FROM results WHERE result_id = %s AND regatta_id = %s", (int(result_id), regatta_id))
    _audit(cur, regatta_id, "team_delete", team_id=int(team_id), actor=actor)


def create_match(cur, regatta_id: str, *, actor: str = "super_admin", round_label: str = "RR") -> dict:
    ensure_schema(cur)
    cur.execute(
        "SELECT COALESCE(MAX(match_no), 0) + 1 AS n FROM tsl_event_matches WHERE regatta_id = %s",
        (regatta_id,),
    )
    n = int((cur.fetchone() or {}).get("n") or 1)
    cur.execute(
        """
        INSERT INTO tsl_event_matches (regatta_id, match_no, status, round_label, colour_a, colour_b, phase)
        VALUES (%s, %s, 'open', %s, 'Blue', 'Green', 'rr')
        ON CONFLICT (regatta_id, match_no) DO NOTHING
        RETURNING match_id, match_no, status, round_label
        """,
        (regatta_id, n, round_label or "RR"),
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "SELECT match_id, match_no, status, round_label FROM tsl_event_matches WHERE regatta_id = %s AND match_no = %s",
            (regatta_id, n),
        )
        row = cur.fetchone()
    cur.execute(
        "UPDATE public.regatta_blocks SET races_sailed = %s WHERE block_id = %s",
        (n, _block_id(regatta_id)),
    )
    _audit(cur, regatta_id, "match_create", match_id=int(row["match_id"]), actor=actor)
    item = dict(row)
    item["label"] = f"M{int(item['match_no'])}"
    item["boats"] = []
    return item


def delete_last_match(cur, regatta_id: str, *, confirm: bool = False, actor: str = "super_admin") -> dict:
    ensure_schema(cur)
    cur.execute(
        """
        SELECT match_id, match_no, status FROM tsl_event_matches
        WHERE regatta_id = %s
        ORDER BY match_no DESC
        LIMIT 1
        """,
        (regatta_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("No match to remove")
    if str(row["status"]) == "complete":
        raise ValueError("Last match has a recorded result — it is protected")
    cur.execute(
        "SELECT 1 FROM tsl_event_match_boats WHERE match_id = %s AND finish_place IS NOT NULL LIMIT 1",
        (int(row["match_id"]),),
    )
    has_places = bool(cur.fetchone())
    if has_places and not confirm:
        raise ValueError("Last match has entered places — confirm to remove")
    cur.execute("DELETE FROM tsl_event_matches WHERE match_id = %s", (int(row["match_id"]),))
    cur.execute(
        "SELECT COALESCE(MAX(match_no), 0) AS n FROM tsl_event_matches WHERE regatta_id = %s",
        (regatta_id,),
    )
    left = int((cur.fetchone() or {}).get("n") or 0)
    cur.execute(
        "UPDATE public.regatta_blocks SET races_sailed = %s WHERE block_id = %s",
        (left, _block_id(regatta_id)),
    )
    _audit(cur, regatta_id, "match_delete", match_id=int(row["match_id"]), actor=actor, payload={"match_no": int(row["match_no"])})
    return {"removed": int(row["match_no"]), "remaining": left}


def _boats_for_side(body_boats: list[dict], team_id: int) -> list[dict]:
    return [b for b in (body_boats or []) if int(b.get("team_id") or 0) == int(team_id)]


def save_match(cur, regatta_id: str, match_id: int, body: dict, *, actor: str = "super_admin") -> dict:
    ensure_schema(cur)
    cur.execute(
        "SELECT * FROM tsl_event_matches WHERE match_id = %s AND regatta_id = %s",
        (int(match_id), regatta_id),
    )
    match = cur.fetchone()
    if not match:
        raise ValueError("Match not found")
    match = dict(match)
    teams = {int(t["team_id"]): t for t in load_teams(cur, regatta_id)}
    team_a = int(body.get("team_a_id") or body.get("team_blue_id") or 0) or None
    team_b = int(body.get("team_b_id") or body.get("team_green_id") or 0) or None
    if body.get("colour_a") in (None, "", "Blue") and body.get("colour_b") in (None, "", "Green"):
        body["colour_a"] = "Blue"
        body["colour_b"] = "Green"
    if team_a and team_a not in teams:
        raise ValueError("Team A is not a registered event team")
    if team_b and team_b not in teams:
        raise ValueError("Team B is not a registered event team")
    if team_a and team_b and team_a == team_b:
        raise ValueError("Team B must be different from Team A")
    colour_a = str(body.get("colour_a") or "").strip()
    colour_b = str(body.get("colour_b") or "").strip()
    if colour_a and colour_a not in COLOURS:
        raise ValueError("Unknown colour for Team A")
    if colour_b and colour_b not in COLOURS:
        raise ValueError("Unknown colour for Team B")
    if colour_a and colour_b and colour_a == colour_b:
        raise ValueError("Team B colour must differ from Team A")

    boats_in = body.get("boats") or []
    phys_ids = []
    for b in boats_in:
        tid = int(b.get("team_id") or 0)
        if tid not in (team_a, team_b):
            raise ValueError("Match boat is not assigned to Blue or Green")
        pid = b.get("physical_boat_id")
        if pid:
            if int(pid) in phys_ids:
                raise ValueError("The same physical boat cannot be used twice in a match")
            phys_ids.append(int(pid))
        roster_ids = set()
        for rb in (teams.get(tid) or {}).get("boats") or []:
            if rb.get("helm") and rb["helm"].get("sas_id"):
                roster_ids.add(str(rb["helm"]["sas_id"]))
            if rb.get("crew") and rb["crew"].get("sas_id"):
                roster_ids.add(str(rb["crew"]["sas_id"]))
        for key in ("helm_sas_id", "crew_sas_id"):
            sid = str(b.get(key) or "").strip()
            if sid and roster_ids and sid not in roster_ids:
                raise ValueError(f"Sailor {sid} is not on that team's registered roster")

    want_complete = bool(body.get("complete"))
    override_side = None
    ov_winner = body.get("override_winner_team_id")
    ov_reason = str(body.get("override_reason") or "").strip()
    if ov_winner:
        if not ov_reason:
            raise ValueError("Official override requires a reason")
        if int(ov_winner) == team_a:
            override_side = "A"
        elif int(ov_winner) == team_b:
            override_side = "B"
        else:
            raise ValueError("Override winner must be Team A or Team B")

    scored = None
    if team_a and team_b:
        scored = score_match(
            _boats_for_side(boats_in, team_a),
            _boats_for_side(boats_in, team_b),
            team_penalty_a=int(body.get("team_penalty_a") or 0),
            team_penalty_b=int(body.get("team_penalty_b") or 0),
            override_winner=override_side,
        )
        if want_complete and not scored["complete"]:
            raise ValueError("; ".join(scored["errors"]) or "Match is incomplete")

    winner_id = loser_id = None
    score_a = score_b = None
    status = "open"
    if scored and scored.get("complete") and want_complete:
        status = "complete"
        score_a, score_b = scored["score_a"], scored["score_b"]
        winner_id = team_a if scored["winner"] == "A" else team_b
        loser_id = team_b if scored["winner"] == "A" else team_a

    cur.execute(
        """
        UPDATE tsl_event_matches SET
          team_a_id = %s, team_b_id = %s, colour_a = %s, colour_b = %s,
          score_a = %s, score_b = %s, winner_team_id = %s, loser_team_id = %s,
          override_winner_team_id = %s, override_reason = %s,
          override_by = CASE WHEN %s THEN %s ELSE override_by END,
          override_at = CASE WHEN %s THEN now() ELSE override_at END,
          team_penalty_a = %s, team_penalty_b = %s,
          status = %s,
          completed_at = CASE WHEN %s = 'complete' THEN now() ELSE NULL END,
          round_label = COALESCE(NULLIF(%s, ''), round_label)
        WHERE match_id = %s
        """,
        (
            team_a, team_b, colour_a or None, colour_b or None,
            score_a, score_b, winner_id, loser_id,
            int(ov_winner) if ov_winner else None, ov_reason or None,
            bool(override_side), actor,
            bool(override_side),
            int(body.get("team_penalty_a") or 0), int(body.get("team_penalty_b") or 0),
            status, status, str(body.get("round_label") or ""),
            int(match_id),
        ),
    )
    cur.execute("DELETE FROM tsl_event_match_boats WHERE match_id = %s", (int(match_id),))
    for b in boats_in:
        cur.execute(
            """
            INSERT INTO tsl_event_match_boats (
              match_id, team_id, pairing_no, bow_number, sail_number,
              helm_sas_id, crew_sas_id, finish_place, penalty_status, physical_boat_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(match_id),
                int(b.get("team_id")),
                int(b.get("pairing_no") or b.get("boat_no") or 0),
                str(b.get("bow_number") or "").strip() or None,
                str(b.get("sail_number") or "").strip() or None,
                str(b.get("helm_sas_id") or "").strip() or None,
                str(b.get("crew_sas_id") or "").strip() or None,
                int(b["finish_place"]) if str(b.get("finish_place") or "").strip() else None,
                str(b.get("penalty_status") or "").strip().upper() or None,
                int(b["physical_boat_id"]) if str(b.get("physical_boat_id") or "").strip() else None,
            ),
        )

    action = "match_complete" if status == "complete" else "match_save"
    _audit(
        cur, regatta_id, action, match_id=int(match_id), actor=actor,
        reason=ov_reason or None,
        payload={"status": status, "score_a": score_a, "score_b": score_b, "winner": winner_id},
    )
    teams_now = load_teams(cur, regatta_id)
    matches_now = load_matches(cur, regatta_id)
    settings = load_settings(cur, regatta_id)
    _resolve_sailoffs(cur, regatta_id, teams_now, matches_now, settings)
    matches_now = load_matches(cur, regatta_id)
    standings = championship_standings(teams_now, matches_now, settings)
    _write_standings_to_results(cur, regatta_id, standings, matches_now)
    return next(m for m in matches_now if int(m["match_id"]) == int(match_id))


def search_clubs(cur, q: str, limit: int = 40) -> list[dict]:
    qn = (q or "").strip()
    lim = max(1, min(80, int(limit)))
    if len(qn) < 1:
        cur.execute(
            """
            SELECT club_id, TRIM(COALESCE(club_abbrev, '')) AS code,
                   TRIM(COALESCE(club_fullname, '')) AS name
            FROM public.clubs
            WHERE COALESCE(TRIM(COALESCE(club_abbrev, club_fullname, '')), '') <> ''
              AND lower(trim(COALESCE(club_abbrev, ''))) <> 'unassigned'
            ORDER BY UPPER(TRIM(COALESCE(club_abbrev, club_fullname, '')))
            LIMIT %s
            """,
            (lim,),
        )
    else:
        pat = f"%{_escape_like(qn.lower())}%"
        cur.execute(
            """
            SELECT club_id, TRIM(COALESCE(club_abbrev, '')) AS code,
                   TRIM(COALESCE(club_fullname, '')) AS name
            FROM public.clubs
            WHERE COALESCE(TRIM(COALESCE(club_abbrev, club_fullname, '')), '') <> ''
              AND lower(trim(COALESCE(club_abbrev, ''))) <> 'unassigned'
              AND (
                LOWER(COALESCE(club_abbrev::text, '')) LIKE %s
                OR LOWER(COALESCE(club_fullname::text, '')) LIKE %s
              )
            ORDER BY club_abbrev NULLS LAST, club_fullname NULLS LAST
            LIMIT %s
            """,
            (pat, pat, lim),
        )
    out = []
    for r in cur.fetchall() or []:
        code = (r.get("code") or "").strip()
        out.append({
            "club_id": int(r["club_id"]),
            "code": code,
            "name": (r.get("name") or "").strip(),
            "logo": f"/api/club-logo/{code}" if code else "",
        })
    return out


def search_sailors(cur, q: str, *, club_abbrev: str = "", club_name: str = "", limit: int = 35) -> list[dict]:
    qn = (q or "").strip()
    if len(qn) < 1:
        return []
    lim = max(1, min(60, int(limit)))
    pat = f"%{_escape_like(qn.lower())}%"
    cur.execute(
        """
        SELECT sa_sailing_id::text AS sas_id,
               TRIM(COALESCE(full_name, '')) AS full_name,
               TRIM(COALESCE(first_name, '')) AS first_name,
               TRIM(COALESCE(last_name, '')) AS last_name,
               TRIM(COALESCE(primary_club, '')) AS primary_club,
               TRIM(COALESCE(club_1::text, '')) AS club_1
        FROM public.sas_id_personal
        WHERE (
            sa_sailing_id::text = %s
            OR sa_sailing_id::text LIKE %s
            OR LOWER(TRIM(COALESCE(full_name, ''))) LIKE %s
            OR LOWER(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))) LIKE %s
            OR LOWER(TRIM(COALESCE(last_name, '') || ', ' || COALESCE(first_name, ''))) LIKE %s
        )
        ORDER BY full_name NULLS LAST
        LIMIT %s
        """,
        (qn, pat, pat, pat, pat, lim * 3),
    )
    out = []
    for r in cur.fetchall() or []:
        d = dict(r)
        sailor = {
            "sas_id": str(d.get("sas_id") or ""),
            "name": display_name(d),
            "full_name": d.get("full_name") or "",
            "club": (d.get("primary_club") or d.get("club_1") or "").strip() or None,
            "primary_club": d.get("primary_club") or "",
            "club_1": d.get("club_1") or "",
        }
        if club_abbrev or club_name:
            if not sailor_allowed_for_club(sailor, club_abbrev, club_name):
                continue
        out.append(sailor)
        if len(out) >= lim:
            break
    if club_abbrev:
        want = _norm_club(club_abbrev)

        def _key(s):
            codes = sailor_club_codes(s)
            return (0 if want in codes else 1, s.get("name") or "")

        out.sort(key=_key)
    return out


def ensure_physical_boats(cur, regatta_id: str) -> None:
    cur.execute("SELECT COUNT(*) AS n FROM tsl_event_boats WHERE regatta_id = %s", (regatta_id,))
    n = int((cur.fetchone() or {}).get("n") or 0)
    if n >= 6:
        return
    for colour, boat_no in DEFAULT_PHYSICAL_BOATS:
        cur.execute(
            """
            INSERT INTO tsl_event_boats (regatta_id, colour, boat_no, bow_number, sail_number)
            VALUES (%s, %s, %s, NULL, NULL)
            ON CONFLICT (regatta_id, colour, boat_no) DO NOTHING
            """,
            (regatta_id, colour, boat_no),
        )


def load_physical_boats(cur, regatta_id: str) -> list[dict]:
    ensure_physical_boats(cur, regatta_id)
    cur.execute(
        """
        SELECT boat_id, colour, boat_no, bow_number, sail_number
        FROM tsl_event_boats
        WHERE regatta_id = %s
        ORDER BY colour, boat_no
        """,
        (regatta_id,),
    )
    return [dict(r) for r in (cur.fetchall() or [])]


def save_physical_boats(cur, regatta_id: str, boats: list[dict], *, actor: str = "super_admin") -> list[dict]:
    ensure_physical_boats(cur, regatta_id)
    for b in boats or []:
        bid = int(b.get("boat_id") or 0)
        if not bid:
            continue
        cur.execute(
            """
            UPDATE tsl_event_boats
               SET bow_number = %s, sail_number = %s
             WHERE boat_id = %s AND regatta_id = %s
            """,
            (
                str(b.get("bow_number") or "").strip() or None,
                str(b.get("sail_number") or "").strip() or None,
                bid,
                regatta_id,
            ),
        )
    _audit(cur, regatta_id, "boats_save", actor=actor, payload={"n": len(boats or [])})
    return load_physical_boats(cur, regatta_id)


def load_settings(cur, regatta_id: str) -> dict:
    cur.execute(
        "SELECT format, flight_a, flight_b FROM tsl_event_settings WHERE regatta_id = %s",
        (regatta_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO tsl_event_settings (regatta_id, format) VALUES (%s, 'rr28')",
            (regatta_id,),
        )
        return {"format": "rr28", "flight_a": [], "flight_b": []}
    fa = row.get("flight_a") or []
    fb = row.get("flight_b") or []
    if isinstance(fa, str):
        fa = json.loads(fa)
    if isinstance(fb, str):
        fb = json.loads(fb)
    return {"format": (row.get("format") or "rr28"), "flight_a": fa or [], "flight_b": fb or []}


def championship_standings(teams: list[dict], matches: list[dict], settings: dict) -> list[dict]:
    from sailingsa.backend.tsl_schedule import FORMAT_FLIGHTS16, championship_from_sailoffs

    base = rank_standings(teams, matches)
    if (settings or {}).get("format") != FORMAT_FLIGHTS16:
        for r in base:
            r["championship_rank"] = r.get("rank")
            r["matches_played"] = r.get("wins", 0) + r.get("losses", 0)
        return base
    fa_ids = {int(x) for x in (settings.get("flight_a") or [])}
    fb_ids = {int(x) for x in (settings.get("flight_b") or [])}
    fa_matches = [m for m in matches if m.get("phase") == "flight_a"]
    fb_matches = [m for m in matches if m.get("phase") == "flight_b"]
    fa_teams = [t for t in teams if int(t["team_id"]) in fa_ids] or [t for t in teams if any(int(m.get("team_a_id") or 0) == int(t["team_id"]) or int(m.get("team_b_id") or 0) == int(t["team_id"]) for m in fa_matches)]
    fb_teams = [t for t in teams if int(t["team_id"]) in fb_ids] or [t for t in teams if any(int(m.get("team_a_id") or 0) == int(t["team_id"]) or int(m.get("team_b_id") or 0) == int(t["team_id"]) for m in fb_matches)]
    fa_rank = rank_standings(fa_teams, fa_matches) if fa_teams else []
    fb_rank = rank_standings(fb_teams, fb_matches) if fb_teams else []
    places = championship_from_sailoffs([m for m in matches if m.get("phase") == "sailoff"])
    by = {int(r["team_id"]): r for r in base}
    for r in fa_rank:
        if int(r["team_id"]) in by:
            by[int(r["team_id"])]["flight"] = "A"
            by[int(r["team_id"])]["flight_rank"] = r.get("rank")
    for r in fb_rank:
        if int(r["team_id"]) in by:
            by[int(r["team_id"])]["flight"] = "B"
            by[int(r["team_id"])]["flight_rank"] = r.get("rank")
    rows = list(by.values())
    for r in rows:
        r["matches_played"] = r.get("wins", 0) + r.get("losses", 0)
        if int(r["team_id"]) in places:
            r["championship_rank"] = places[int(r["team_id"])]
            r["rank"] = places[int(r["team_id"])]
        else:
            r["championship_rank"] = None
    rows.sort(key=lambda r: (r.get("rank") is None, r.get("rank") or 99, r.get("team_name") or ""))
    return rows


def _resolve_sailoffs(cur, regatta_id: str, teams: list[dict], matches: list[dict], settings: dict) -> None:
    from sailingsa.backend.tsl_schedule import resolve_sailoff_teams

    if (settings or {}).get("format") != "flights16":
        return
    fa_ids = {int(x) for x in (settings.get("flight_a") or [])}
    fb_ids = {int(x) for x in (settings.get("flight_b") or [])}
    fa_m = [m for m in matches if m.get("phase") == "flight_a"]
    fb_m = [m for m in matches if m.get("phase") == "flight_b"]
    if any(m.get("status") != "complete" for m in fa_m) or any(m.get("status") != "complete" for m in fb_m):
        return
    if len(fa_m) < 6 or len(fb_m) < 6:
        return
    fa_teams = [t for t in teams if int(t["team_id"]) in fa_ids]
    fb_teams = [t for t in teams if int(t["team_id"]) in fb_ids]
    slots = resolve_sailoff_teams(rank_standings(fa_teams, fa_m), rank_standings(fb_teams, fb_m))
    for m in matches:
        if m.get("phase") != "sailoff" or m.get("status") == "complete":
            continue
        slot = int(m.get("sailoff_slot") or 0)
        if slot not in slots:
            continue
        ta, tb = slots[slot]
        cur.execute(
            """
            UPDATE tsl_event_matches
               SET team_a_id = %s, team_b_id = %s, colour_a = 'Blue', colour_b = 'Green'
             WHERE match_id = %s AND status <> 'complete'
            """,
            (ta, tb, int(m["match_id"])),
        )


def apply_generated_schedule(
    cur,
    regatta_id: str,
    incoming: list[dict],
    *,
    fmt: str,
    flight_a: list = None,
    flight_b: list = None,
    confirm: bool = False,
    actor: str = "super_admin",
) -> dict:
    from sailingsa.backend.tsl_schedule import preview_format_switch, validate_schedule

    existing = load_matches(cur, regatta_id)
    preview = preview_format_switch(existing, incoming)
    if preview["blocked_completed_not_in_new_format"] and confirm:
        raise ValueError(
            "Completed matches "
            + ", ".join(preview["blocked_completed_not_in_new_format"])
            + " are not in the new format — they were kept, not deleted"
        )
    if preview["needs_confirm"] and not confirm:
        return {"ok": False, "preview": preview, "needs_confirm": True}
    completed_ids = {int(m["match_id"]) for m in existing if m.get("status") == "complete"}
    cur.execute(
        "DELETE FROM tsl_event_matches WHERE regatta_id = %s AND status <> 'complete'",
        (regatta_id,),
    )
    used_nos = {int(m["match_no"]) for m in existing if m.get("status") == "complete"}
    for spec in incoming:
        pair = frozenset((int(spec.get("blue_team_id") or 0), int(spec.get("green_team_id") or 0)))
        already = False
        for m in existing:
            if m.get("status") != "complete":
                continue
            if frozenset((int(m.get("team_a_id") or 0), int(m.get("team_b_id") or 0))) == pair and pair != frozenset((0, 0)):
                already = True
                break
        if already:
            continue
        n = int(spec["match_no"])
        while n in used_nos:
            n += 1
        used_nos.add(n)
        cur.execute(
            """
            INSERT INTO tsl_event_matches (
              regatta_id, match_no, status, round_label, team_a_id, team_b_id,
              colour_a, colour_b, phase, flight, sailoff_slot
            ) VALUES (%s, %s, 'scheduled', %s, %s, %s, 'Blue', 'Green', %s, %s, %s)
            """,
            (
                regatta_id,
                n,
                spec.get("round_label") or "RR",
                spec.get("blue_team_id"),
                spec.get("green_team_id"),
                spec.get("phase") or "rr",
                spec.get("flight") or "",
                spec.get("sailoff_slot"),
            ),
        )
    cur.execute(
        """
        INSERT INTO tsl_event_settings (regatta_id, format, flight_a, flight_b)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (regatta_id) DO UPDATE SET
          format = EXCLUDED.format,
          flight_a = EXCLUDED.flight_a,
          flight_b = EXCLUDED.flight_b,
          updated_at = now()
        """,
        (regatta_id, fmt, _json_payload(flight_a or []), _json_payload(flight_b or [])),
    )
    teams = load_teams(cur, regatta_id)
    matches = load_matches(cur, regatta_id)
    warnings = validate_schedule(
        [
            {
                **m,
                "blue_team_id": m.get("team_a_id"),
                "green_team_id": m.get("team_b_id"),
            }
            for m in matches
        ],
        [t["team_id"] for t in teams],
        fmt,
    )
    _write_standings_to_results(cur, regatta_id, championship_standings(teams, matches, {"format": fmt, "flight_a": flight_a or [], "flight_b": flight_b or []}), matches)
    _audit(cur, regatta_id, "schedule_generate", actor=actor, payload={"format": fmt, "n": len(incoming)})
    return {"ok": True, "preview": preview, "warnings": warnings, "matches": matches}


def event_state(cur, regatta_id: str) -> dict:
    ensure_schema(cur)
    ensure_physical_boats(cur, regatta_id)
    from sailingsa.backend.tsl_schedule import color_counts, changeover_stays, validate_schedule

    teams = load_teams(cur, regatta_id)
    matches = load_matches(cur, regatta_id)
    settings = load_settings(cur, regatta_id)
    _resolve_sailoffs(cur, regatta_id, teams, matches, settings)
    matches = load_matches(cur, regatta_id)
    standings = championship_standings(teams, matches, settings)
    mapped = [{**m, "blue_team_id": m.get("team_a_id"), "green_team_id": m.get("team_b_id")} for m in matches]
    boats = load_physical_boats(cur, regatta_id)
    return {
        "ok": True,
        "regatta_id": regatta_id,
        "format": settings.get("format") or "rr28",
        "settings": settings,
        "teams": teams,
        "matches": matches,
        "standings": standings,
        "boats": boats,
        "colours": list(COLOURS),
        "seeded_mac_sas": sorted(MAC_SEEDED_SAS),
        "schedule": {
            "warnings": validate_schedule(mapped, [t["team_id"] for t in teams], settings.get("format") or "rr28"),
            "color_balance": color_counts(mapped, [t["team_id"] for t in teams]),
            "stays": changeover_stays(mapped),
        },
    }


def register_tsl_routes(
    app,
    *,
    get_db_connection: Callable,
    return_db_connection: Callable,
    is_super_admin: Callable,
    table_exists: Optional[Callable] = None,
    column_exists: Optional[Callable] = None,
) -> None:
    """Mount TSL endpoints on the existing FastAPI app. Live-safe extra routes only."""
    from fastapi import Body, HTTPException as _HTTP, Request
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None  # type: ignore

    def _rid(regatta_id: str) -> str:
        rid = str(regatta_id or "").strip()
        if not is_tsl_regatta(rid):
            raise _HTTP(status_code=404, detail="not a TSL event")
        return rid

    def _cur(conn):
        if RealDictCursor:
            return conn.cursor(cursor_factory=RealDictCursor)
        return conn.cursor()

    def _sa(request) -> None:
        if not is_super_admin(request):
            raise _HTTP(status_code=403, detail="super_admin only")

    def _actor(request) -> str:
        try:
            role = getattr(request, "session", {}) or {}
            return str(role.get("email") or role.get("user") or "super_admin")
        except Exception:
            return "super_admin"

    @app.get("/api/tsl/{regatta_id}/state")
    def api_tsl_state(regatta_id: str):
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            out = event_state(cur, rid)
            conn.commit()
            return out
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.get("/api/tsl/{regatta_id}/clubs-search")
    def api_tsl_clubs_search(request: Request, regatta_id: str, q: str = "", limit: int = 40):
        _sa(request)
        _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            return {"clubs": search_clubs(cur, q, limit)}
        finally:
            cur.close()
            return_db_connection(conn)

    @app.get("/api/tsl/{regatta_id}/sailors-search")
    def api_tsl_sailors_search(
        request: Request,
        regatta_id: str,
        q: str = "",
        club: str = "",
        club_id: int = 0,
        limit: int = 35,
    ):
        _sa(request)
        _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            club_abbrev = (club or "").strip()
            club_name = ""
            if club_id:
                row = _club_row(cur, int(club_id))
                if row:
                    club_abbrev = club_abbrev or (row.get("club_abbrev") or "")
                    club_name = row.get("club_name") or ""
            sailors = search_sailors(
                cur, q, club_abbrev=club_abbrev, club_name=club_name, limit=limit
            )
            return {"sailors": sailors}
        finally:
            cur.close()
            return_db_connection(conn)

    @app.post("/api/tsl/{regatta_id}/teams")
    def api_tsl_team_create(request: Request, regatta_id: str, body: dict = Body(default={})):
        _sa(request)
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            ensure_schema(cur)
            team = upsert_team(cur, rid, body or {}, actor=_actor(request))
            conn.commit()
            return {"ok": True, "team": team}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.patch("/api/tsl/{regatta_id}/teams/{team_id}")
    def api_tsl_team_patch(request: Request, regatta_id: str, team_id: int, body: dict = Body(default={})):
        _sa(request)
        rid = _rid(regatta_id)
        payload = dict(body or {})
        payload["team_id"] = int(team_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            ensure_schema(cur)
            team = upsert_team(cur, rid, payload, actor=_actor(request))
            conn.commit()
            return {"ok": True, "team": team}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.patch("/api/tsl/{regatta_id}/teams/{team_id}/slot-sex")
    def api_tsl_slot_sex(request: Request, regatta_id: str, team_id: int, body: dict = Body(default={})):
        _sa(request)
        _rid(regatta_id)
        payload = dict(body or {})
        boat = int(payload.get("boat") or 0)
        role = str(payload.get("role") or "").strip().lower()
        sex = _sex_letter(payload.get("sex"))
        if boat < 1 or boat > BOATS_PER_TEAM or role not in ("helm", "crew") or sex not in ("M", "F"):
            raise _HTTP(status_code=400, detail="boat, role, and sex required")
        col = "helm_sex" if role == "helm" else "crew_sex"
        sas_col = "helm_sas_id" if role == "helm" else "crew_sas_id"
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            ensure_schema(cur)
            cur.execute(
                "SELECT team_id FROM public.tsl_event_teams WHERE team_id = %s AND regatta_id = %s",
                (int(team_id), str(regatta_id)),
            )
            if not cur.fetchone():
                raise ValueError("Team not found")
            cur.execute(
                f"""
                INSERT INTO public.tsl_event_team_boats (team_id, boat_no, {col})
                VALUES (%s, %s, %s)
                ON CONFLICT (team_id, boat_no)
                DO UPDATE SET {col} = EXCLUDED.{col}
                RETURNING {sas_col} AS sas_id
                """,
                (int(team_id), boat, sex),
            )
            row = cur.fetchone() or {}
            sas_id = str((row.get("sas_id") if isinstance(row, dict) else "") or "")
            _save_sailor_sex(cur, sas_id, sex)
            conn.commit()
            return {"ok": True, "boat": boat, "role": role, "sex": sex}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.delete("/api/tsl/{regatta_id}/teams/{team_id}")
    def api_tsl_team_delete(request: Request, regatta_id: str, team_id: int):
        _sa(request)
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            delete_team(cur, rid, int(team_id), actor=_actor(request))
            conn.commit()
            return {"ok": True}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.post("/api/tsl/{regatta_id}/matches")
    def api_tsl_match_create(request: Request, regatta_id: str, body: dict = Body(default={})):
        _sa(request)
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            ensure_schema(cur)
            match = create_match(cur, rid, actor=_actor(request), round_label=str((body or {}).get("round_label") or "RR"))
            conn.commit()
            return {"ok": True, "match": match}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.delete("/api/tsl/{regatta_id}/matches/last")
    def api_tsl_match_delete_last(request: Request, regatta_id: str, confirm: bool = False):
        _sa(request)
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            out = delete_last_match(cur, rid, confirm=bool(confirm), actor=_actor(request))
            teams = load_teams(cur, rid)
            matches = load_matches(cur, rid)
            _write_standings_to_results(cur, rid, rank_standings(teams, matches), matches)
            conn.commit()
            return {"ok": True, **out}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.patch("/api/tsl/{regatta_id}/matches/{match_id}")
    def api_tsl_match_save(request: Request, regatta_id: str, match_id: int, body: dict = Body(default={})):
        _sa(request)
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            match = save_match(cur, rid, int(match_id), body or {}, actor=_actor(request))
            conn.commit()
            return {"ok": True, "match": match, "state": event_state(cur, rid)}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.patch("/api/tsl/{regatta_id}/boats")
    def api_tsl_boats_save(request: Request, regatta_id: str, body: dict = Body(default={})):
        _sa(request)
        rid = _rid(regatta_id)
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            ensure_schema(cur)
            boats = save_physical_boats(cur, rid, (body or {}).get("boats") or [], actor=_actor(request))
            conn.commit()
            return {"ok": True, "boats": boats}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)

    @app.post("/api/tsl/{regatta_id}/schedule")
    def api_tsl_schedule(request: Request, regatta_id: str, body: dict = Body(default={})):
        _sa(request)
        rid = _rid(regatta_id)
        from sailingsa.backend.tsl_schedule import FORMAT_FLIGHTS16, FORMAT_RR28, generate_flights16, generate_rr_matches

        fmt = str((body or {}).get("format") or "rr28")
        confirm = bool((body or {}).get("confirm"))
        conn = get_db_connection()
        cur = _cur(conn)
        try:
            ensure_schema(cur)
            teams = load_teams(cur, rid)
            ids = [int(t["team_id"]) for t in teams]
            require_championship_teams(ids)
            if fmt == FORMAT_FLIGHTS16:
                fa = [int(x) for x in (body.get("flight_a") or [])]
                fb = [int(x) for x in (body.get("flight_b") or [])]
                incoming = generate_flights16(fa, fb)
            else:
                incoming = generate_rr_matches(ids)
                fa, fb = [], []
                fmt = FORMAT_RR28
            out = apply_generated_schedule(
                cur, rid, incoming, fmt=fmt, flight_a=fa, flight_b=fb, confirm=confirm, actor=_actor(request)
            )
            conn.commit()
            if not out.get("ok"):
                return out
            return {**out, "state": event_state(cur, rid)}
        except ValueError as e:
            conn.rollback()
            raise _HTTP(status_code=400, detail=str(e))
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            return_db_connection(conn)
