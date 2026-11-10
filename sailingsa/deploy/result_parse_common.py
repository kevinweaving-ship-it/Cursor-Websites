#!/usr/bin/env python3
"""Shared helpers for Result Parse - Add (regatta stub + fleet pass scripts).

See docs/RESULT_PARSE_ADD.md for the full workflow.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

import psycopg2.extras

PEN = frozenset({"DNC", "OCS", "RET", "DNS", "DNF", "DSQ", "BFD", "UFD"})

_NAME_PARTICLES = frozenset(
    {"van", "de", "du", "der", "den", "le", "la", "von", "ter", "ten", "di", "da"}
)


def encode_score(raw: str, entries: int) -> str:
    """Sheet token → stored race score. Penalties = entries+1 (Appendix A)."""
    s = (raw or "").strip()
    discarded = s.startswith("(") and s.endswith(")")
    inner = s[1:-1].strip() if discarded else s
    up = inner.upper()
    if up in PEN:
        body = f"{entries + 1}.0 {up}"
        return f"({body})" if discarded else body
    if re.fullmatch(r"\d+", inner):
        body = f"{inner}.0"
    elif re.fullmatch(r"\d+\.0", inner):
        body = inner
    else:
        body = inner
    return f"({body})" if discarded else body


def score_value(encoded: str) -> Decimal:
    inner = encoded[1:-1] if encoded.startswith("(") and encoded.endswith(")") else encoded
    m = re.match(r"(-?\d+(?:\.\d+)?)", inner.strip())
    if not m:
        raise ValueError(encoded)
    return Decimal(m.group(1))


def checksum_row(raw_scores: list[str], entries: int, total: str, nett: str) -> dict[str, Any]:
    """Verify Total/Nett against encoded scores (one discard = worst/highest)."""
    enc = [encode_score(x, entries) for x in raw_scores]
    vals = [score_value(x) for x in enc]
    tot = sum(vals)
    disc = max(vals)
    net = tot - disc
    exp_t = Decimal(total)
    exp_n = Decimal(nett)
    ok = tot == exp_t and net == exp_n
    return {"ok": ok, "scores": enc, "total": tot, "nett": net, "exp_t": exp_t, "exp_n": exp_n}


def _cap_token(token: str) -> str:
    if not token:
        return token
    if "-" in token:
        return "-".join(_cap_token(t) for t in token.split("-"))
    if "'" in token:
        return "'".join(_cap_token(t) for t in token.split("'"))
    if token.islower() or token.isupper():
        return token[:1].upper() + token[1:].lower()
    return token


def _format_name_tokens(tokens: list[str], *, surname_mode: bool = False) -> str:
    out: list[str] = []
    for i, tok in enumerate(tokens):
        tl = tok.lower()
        if surname_mode and i < len(tokens) - 1 and tl in _NAME_PARTICLES:
            out.append(tl)
        else:
            out.append(_cap_token(tok))
    return " ".join(out)


def format_display_name(name: str) -> str:
    """Capitalise first/surname; particles (van, de, …) stay lowercase."""
    s = (name or "").strip()
    if not s:
        return s
    parts = s.split(None, 1)
    if len(parts) == 1:
        return _format_name_tokens(parts[0].split(), surname_mode=False)
    first, rest = parts
    return (
        f"{_format_name_tokens(first.split(), surname_mode=False)} "
        f"{_format_name_tokens(rest.split(), surname_mode=True)}"
    ).strip()


def sas_helm_name(first_name: str | None, last_name: str | None) -> str:
    """Truth from sas_id_personal: first_name + last_name only (ignore second_name / full_name)."""
    raw = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
    return format_display_name(raw) if raw else ""


def lookup_club(cur, code: str):
    c = (code or "").strip()
    cur.execute(
        """
        SELECT club_id, club_abbrev FROM clubs
        WHERE UPPER(TRIM(club_abbrev)) = UPPER(%s)
           OR LOWER(TRIM(club_fullname)) = LOWER(%s)
        LIMIT 1
        """,
        (c, c),
    )
    row = cur.fetchone()
    if row:
        return row[0], (row[1] or c)
    return None, c


def lookup_sailor(cur, name: str, sail: str | None = None, *, name_aliases: dict[str, str] | None = None):
    """Match sas_id_personal; return (sa_sailing_id, canonical helm_name)."""
    aliases_map = name_aliases or {}
    n = (name or "").strip()
    candidates = [n]
    alt = aliases_map.get(n.lower())
    if alt:
        candidates.append(alt)

    sail_clean = (sail or "").strip()
    if sail_clean and sail_clean.upper() != "TBA":
        cur.execute(
            """
            SELECT sa_sailing_id, first_name, last_name
            FROM sas_id_personal
            WHERE TRIM(COALESCE(primary_sailno, '')) = %s
            LIMIT 1
            """,
            (sail_clean,),
        )
        row = cur.fetchone()
        if row:
            return str(row[0]).strip(), sas_helm_name(row[1], row[2])

    for cand in candidates:
        cur.execute(
            """
            SELECT sa_sailing_id, first_name, last_name
            FROM sas_id_personal
            WHERE LOWER(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))) = LOWER(%s)
               OR LOWER(TRIM(COALESCE(full_name, ''))) = LOWER(%s)
            LIMIT 1
            """,
            (cand, cand),
        )
        row = cur.fetchone()
        if row:
            return str(row[0]).strip(), sas_helm_name(row[1], row[2])
    return None, format_display_name(n)


def class_id(cur, name: str) -> int:
    cur.execute(
        "SELECT class_id FROM classes WHERE TRIM(class_name) = %s LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"validated class not found: {name}")
    return int(row[0])


def table_cols(cur, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
        (table,),
    )
    return {r[0] for r in cur.fetchall() or []}


def ensure_gender_column(cur) -> None:
    if "gender" not in table_cols(cur, "results"):
        cur.execute("ALTER TABLE public.results ADD COLUMN gender TEXT")


def upsert_block(
    cur,
    *,
    regatta_id: str,
    fleet: dict,
    class_id_val: int,
) -> str:
    bid = f"{regatta_id}:{fleet['block_slug']}"
    cols = table_cols(cur, "regatta_blocks")
    wanted = {
        "block_id": bid,
        "regatta_id": regatta_id,
        "fleet_label": fleet["class_canonical"],
        "class_original": fleet["class_original"],
        "class_canonical": fleet["class_canonical"],
        "class_id": class_id_val,
        "races_sailed": fleet["races"],
        "discard_count": fleet["discards"],
        "to_count": fleet["races"] - fleet["discards"],
        "scoring_system": fleet.get("scoring_system") or "Appendix A",
    }
    insert_cols = [c for c in wanted if c in cols]
    placeholders = ", ".join(["%s"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in insert_cols if c != "block_id")
    cur.execute(
        f"""
        INSERT INTO public.regatta_blocks ({col_sql})
        VALUES ({placeholders})
        ON CONFLICT (block_id) DO UPDATE SET {updates}
        """,
        tuple(wanted[c] for c in insert_cols),
    )
    return bid


def insert_fleet(
    cur,
    *,
    regatta_id: str,
    fleet: dict,
    name_aliases: dict[str, str] | None = None,
) -> list[str]:
    """Insert one fleet; delete/replace rows for block. Returns unmatched helm list."""
    cid = class_id(cur, fleet["class_canonical"])
    bid = upsert_block(cur, regatta_id=regatta_id, fleet=fleet, class_id_val=cid)
    rcols = table_cols(cur, "results")
    cur.execute(
        "DELETE FROM public.results WHERE regatta_id=%s AND block_id=%s",
        (regatta_id, bid),
    )
    unmatched: list[str] = []
    for rank, sail, club_code, name, cat, gender, races, total, nett in fleet["rows"]:
        chk = checksum_row(races, fleet["entries"], total, nett)
        if not chk["ok"]:
            raise SystemExit(
                f"checksum fail {name}: got {chk['total']}/{chk['nett']} "
                f"expected {chk['exp_t']}/{chk['exp_n']}"
            )
        club_id, club_raw = lookup_club(cur, club_code)
        sas_id, canon = lookup_sailor(cur, name, sail, name_aliases=name_aliases)
        if not sas_id:
            unmatched.append(f"{name} | {club_code} | {sail}")
        helm_id: int | str | None = None
        if sas_id and str(sas_id).isdigit():
            helm_id = int(sas_id)
        elif sas_id:
            helm_id = sas_id
        scores = {f"R{i+1}": chk["scores"][i] for i in range(len(races))}
        row = {
            "regatta_id": regatta_id,
            "block_id": bid,
            "rank": rank,
            "fleet_label": fleet["class_canonical"],
            "class_original": fleet["class_original"],
            "class_canonical": fleet["class_canonical"],
            "class_id": cid,
            "sail_number": sail,
            "helm_name": canon,
            "club_raw": club_raw,
            "club_id": club_id,
            "helm_sa_sailing_id": helm_id,
            "race_scores": psycopg2.extras.Json(scores),
            "total_points_raw": Decimal(total),
            "nett_points_raw": Decimal(nett),
            "races_sailed": fleet["races"],
            "discard_count": fleet["discards"],
            "ranks_sailed": fleet["entries"],
            "raced": True,
            "age_category": cat,
            "gender": gender,
            "result_status": fleet.get("result_status") or "Provisional",
        }
        insert_cols = [c for c in row if c in rcols and row[c] is not None]
        placeholders = ", ".join(["%s"] * len(insert_cols))
        cur.execute(
            f"INSERT INTO public.results ({', '.join(insert_cols)}) VALUES ({placeholders})",
            tuple(row[c] for c in insert_cols),
        )
    return unmatched
