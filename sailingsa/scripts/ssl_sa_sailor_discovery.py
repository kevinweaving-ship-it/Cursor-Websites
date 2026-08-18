#!/usr/bin/env python3
"""Weekly SSL South African sailor discovery.

Fetches every page of the World of Sailors RSA skipper and crew lists,
deduplicates by immutable SSL user id then slug, matches to existing
sas_id_personal rows, and writes SSL identity fields only for confirmed
unique matches.

Does not modify api.py. Does not invent SAS IDs. Does not merge people
because names look similar.

Usage:
  python3 sailingsa/scripts/ssl_sa_sailor_discovery.py --dry-run
  python3 sailingsa/scripts/ssl_sa_sailor_discovery.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database" / "migrations" / "183_sas_id_personal_ssl_identity.sql"
WOS_RANKING = "https://worldofsailors.com/ranking"
WOS_API = "https://platform.worldofsailors.com/api/rankings/sailors"
WOS_PROFILE = "https://worldofsailors.com/sailor/{slug}"
SAS_SEARCH = "https://sailingsa.co.za/api/search"
SAS_RESOLVE = "https://sailingsa.co.za/api/sailor/resolve"
UA = "SailingSA-ssl-sa-sailor-discovery/1.0 (+https://sailingsa.co.za)"
TYPE_SKIPPER = "ranking.type.skipper"
TYPE_CREW = "ranking.type.crew"
SLEEP_S = 0.8
MAX_RETRIES = 5

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(ts: datetime | None = None) -> str:
    return (ts or utc_now()).isoformat()


def http_get(url: str, accept: str = "text/html,application/json", timeout: int = 90) -> tuple[int, bytes, str | None]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept,
            "Origin": "https://worldofsailors.com",
            "Referer": "https://worldofsailors.com/ranking?main=individual&country=south-africa",
        },
    )
    last_err = None
    delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return int(resp.status), resp.read(), None
        except urllib.error.HTTPError as e:
            body = e.read() if e.fp else b""
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                last_err = f"HTTP {e.code}"
                continue
            return int(e.code), body, f"HTTP {e.code}"
        except Exception as e:
            last_err = repr(e)
            if attempt < MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            return 0, b"", last_err
    return 0, b"", last_err


# ---------------------------------------------------------------------------
# Names / slugs
# ---------------------------------------------------------------------------


def normalize_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("'", "").replace("`", "")
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"[\s-]+", " ", text).strip()
    return text


def displayed_name(sailor: dict) -> str:
    first = str(sailor.get("first_name") or "").strip()
    last = str(sailor.get("name") or "").strip()
    return " ".join(p for p in (first, last) if p)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------------------
# World of Sailors fetch
# ---------------------------------------------------------------------------


_SAILOR_RE = re.compile(
    r'\\"sailor\\":\{\\"id\\":(\d+),\\"username\\":\\"([^\\"]+)\\",\\"first_name\\":\\"([^\\"]*)\\",\\"name\\":\\"([^\\"]*)\\"'
)
_META_RE = re.compile(
    r'\\"lines\\":\{\\"current_page\\":(\d+),\\"data\\":\[.*?'
    r'\\"first_page_url\\":\\"[^\\"]*\\",\\"from\\":(\d+),\\"last_page\\":(\d+),.*?'
    r'\\"per_page\\":(\d+),.*?"to\\":(\d+),\\"total\\":(\d+)',
    re.DOTALL,
)


def _ranking_section(html: str, ranking_type: str) -> str:
    """Slice the escaped RSC ranking object for one skipper/crew type."""
    marker = f'\\"type\\":\\"{ranking_type}\\"'
    start = html.find(marker)
    if start < 0:
        marker = f'"type":"{ranking_type}"'
        start = html.find(marker)
        if start < 0:
            raise RuntimeError(f"ranking payload not found for {ranking_type}")
        # Rare unescaped payload: take a bounded window.
        return html[start : start + 2_000_000]
    nxt = html.find('\\"type\\":\\"ranking.type.', start + 10)
    end = nxt if nxt > start else start + 2_000_000
    return html[start:end]


def extract_ranking_lines(html: str, ranking_type: str) -> dict:
    """Parse one ranking paginator from SSR HTML without json.loads on biographies."""
    section = _ranking_section(html, ranking_type)
    meta = _META_RE.search(section)
    if not meta:
        # Fallback: first pagination numbers in this section.
        current = re.search(r'\\"current_page\\":(\d+)', section)
        last = re.search(r'\\"last_page\\":(\d+)', section)
        per = re.search(r'\\"per_page\\":(\d+)', section)
        total = re.search(r'\\"total\\":(\d+)', section)
        if not (current and last and per and total):
            raise RuntimeError(f"paginator meta not found for {ranking_type}")
        current_page, last_page, per_page, total_n = (
            int(current.group(1)),
            int(last.group(1)),
            int(per.group(1)),
            int(total.group(1)),
        )
    else:
        current_page = int(meta.group(1))
        last_page = int(meta.group(3))
        per_page = int(meta.group(4))
        total_n = int(meta.group(6))

    data = []
    for m in _SAILOR_RE.finditer(section):
        ssl_id = int(m.group(1))
        data.append(
            {
                "id": None,
                "user_id": ssl_id,
                "sailor": {
                    "id": ssl_id,
                    "username": m.group(2),
                    "first_name": m.group(3),
                    "name": m.group(4),
                },
            }
        )
    if not data:
        raise RuntimeError(f"no sailor rows parsed for {ranking_type}")
    return {
        "current_page": current_page,
        "last_page": last_page,
        "per_page": per_page,
        "total": total_n,
        "data": data,
    }


def row_from_ranking_item(item: dict, source_role: str, fetched_at: str, source_url: str) -> dict:
    sailor = item.get("sailor") if isinstance(item.get("sailor"), dict) else {}
    ssl_id = sailor.get("id") if sailor.get("id") is not None else item.get("user_id")
    slug = str(sailor.get("username") or "").strip() or None
    name = displayed_name(sailor)
    if not name:
        name = slug or ""
    return {
        "ssl_id": int(ssl_id) if ssl_id is not None else None,
        "slug": slug,
        "profile_url": WOS_PROFILE.format(slug=slug) if slug else None,
        "displayed_name": name,
        "normalized_name": normalize_name(name),
        "source_role": source_role,
        "fetched_at": fetched_at,
        "source_url": source_url,
        "ranking_line_id": item.get("id"),
        "raw_user_id": item.get("user_id"),
    }


def try_structured_api(ranking_type: str, page: int) -> dict | None:
    params = {
        "type": ranking_type,
        "country": "south-africa",
        "page": str(page),
        "per_page": "100",
    }
    if ranking_type == TYPE_CREW:
        params["page_crew"] = str(page)
    url = WOS_API + "?" + urllib.parse.urlencode(params)
    status, body, err = http_get(url, accept="application/json")
    if status != 200:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict) and ("data" in payload or "lines" in payload):
        return payload.get("lines") if "data" not in payload else payload
    return None


def fetch_ranking_page(ranking_type: str, page: int) -> tuple[dict, str, str]:
    api = try_structured_api(ranking_type, page)
    if isinstance(api, dict) and api.get("data") is not None:
        return api, "api", WOS_API

    q = {
        "main": "individual",
        "country": "south-africa",
        "type": ranking_type,
    }
    if ranking_type == TYPE_CREW:
        q["page_crew"] = str(page)
    else:
        q["page"] = str(page)
    url = WOS_RANKING + "?" + urllib.parse.urlencode(q)
    status, body, err = http_get(url)
    if status != 200 or not body:
        raise RuntimeError(f"ranking fetch failed page={page} type={ranking_type} status={status} err={err}")
    lines = extract_ranking_lines(body.decode("utf-8", "replace"), ranking_type)
    return lines, "html", url


def fetch_role_list(ranking_type: str, source_role: str, failures: list) -> list[dict]:
    fetched_at = iso()
    try:
        first, mode, url = fetch_ranking_page(ranking_type, 1)
    except Exception as e:
        failures.append({"stage": f"fetch_{source_role}_page_1", "error": str(e)})
        return []
    last_page = int(first.get("last_page") or 1)
    per_page = int(first.get("per_page") or 0)
    total = first.get("total")
    print(
        f"[fetch] {source_role} page 1/{last_page} mode={mode} "
        f"per_page={per_page} payload_total={total} rows={len(first.get('data') or [])}",
        flush=True,
    )
    pages = [first]
    for page in range(2, last_page + 1):
        time.sleep(SLEEP_S)
        try:
            lines, mode, url = fetch_ranking_page(ranking_type, page)
        except Exception as e:
            failures.append({"stage": f"fetch_{source_role}_page_{page}", "error": str(e)})
            continue
        got_page = int(lines.get("current_page") or 0)
        n = len(lines.get("data") or [])
        print(f"[fetch] {source_role} page {page}/{last_page} mode={mode} current_page={got_page} rows={n}", flush=True)
        if got_page and got_page != page:
            failures.append(
                {
                    "stage": f"fetch_{source_role}_page_{page}",
                    "error": f"current_page mismatch: wanted {page} got {got_page}",
                }
            )
        pages.append(lines)

    rows = []
    for lines in pages:
        source_url = WOS_RANKING + "?" + urllib.parse.urlencode(
            {
                "main": "individual",
                "country": "south-africa",
                "type": ranking_type,
            }
        )
        for item in lines.get("data") or []:
            if not isinstance(item, dict):
                continue
            rows.append(row_from_ranking_item(item, source_role, fetched_at, source_url))
    return rows


# ---------------------------------------------------------------------------
# Dedup / alias detection
# ---------------------------------------------------------------------------


def dedupe_sailors(skipper_rows: list[dict], crew_rows: list[dict]) -> tuple[list[dict], dict]:
    by_id: dict[int, dict] = {}
    by_slug: dict[str, dict] = {}
    unique = []

    def absorb(row: dict) -> None:
        ssl_id = row.get("ssl_id")
        slug = row.get("slug")
        existing = None
        if ssl_id is not None:
            existing = by_id.get(ssl_id)
        if existing is None and slug:
            existing = by_slug.get(slug)
            # Never glue two SSL ids together via slug if both ids exist and differ.
            if existing and existing.get("ssl_id") and ssl_id and existing["ssl_id"] != ssl_id:
                person = {
                    "ssl_id": ssl_id,
                    "slug": slug,
                    "profile_url": row.get("profile_url"),
                    "displayed_name": row.get("displayed_name"),
                    "normalized_name": row.get("normalized_name"),
                    "source_roles": [row["source_role"]],
                    "fetched_at": row.get("fetched_at"),
                    "source_urls": [row.get("source_url")],
                }
                unique.append(person)
                if ssl_id is not None:
                    by_id[ssl_id] = person
                if slug and slug not in by_slug:
                    by_slug[slug] = person
                return
        if existing is None:
            person = {
                "ssl_id": ssl_id,
                "slug": slug,
                "profile_url": row.get("profile_url"),
                "displayed_name": row.get("displayed_name"),
                "normalized_name": row.get("normalized_name"),
                "source_roles": [row["source_role"]],
                "fetched_at": row.get("fetched_at"),
                "source_urls": [row.get("source_url")],
            }
            unique.append(person)
            if ssl_id is not None:
                by_id[ssl_id] = person
            if slug:
                by_slug[slug] = person
            return
        if row["source_role"] not in existing["source_roles"]:
            existing["source_roles"].append(row["source_role"])
        if row.get("source_url") and row["source_url"] not in existing["source_urls"]:
            existing["source_urls"].append(row["source_url"])
        if not existing.get("ssl_id") and ssl_id is not None:
            existing["ssl_id"] = ssl_id
            by_id[ssl_id] = existing
        if not existing.get("slug") and slug:
            existing["slug"] = slug
            existing["profile_url"] = row.get("profile_url")
            by_slug[slug] = existing

    for row in skipper_rows + crew_rows:
        absorb(row)

    overlap_ids = set()
    skipper_ids = {r["ssl_id"] for r in skipper_rows if r.get("ssl_id") is not None}
    crew_ids = {r["ssl_id"] for r in crew_rows if r.get("ssl_id") is not None}
    overlap_ids = skipper_ids & crew_ids
    skipper_slugs = {r["slug"] for r in skipper_rows if r.get("slug")}
    crew_slugs = {r["slug"] for r in crew_rows if r.get("slug")}

    stats = {
        "skipper_rows_fetched": len(skipper_rows),
        "crew_rows_fetched": len(crew_rows),
        "unique_ssl_ids": len({p["ssl_id"] for p in unique if p.get("ssl_id") is not None}),
        "unique_slugs": len({p["slug"] for p in unique if p.get("slug")}),
        "unique_people": len(unique),
        "exact_overlap_ssl_ids": len(overlap_ids),
        "exact_overlap_slugs": len(skipper_slugs & crew_slugs),
        "people_with_both_roles": sum(1 for p in unique if set(p["source_roles"]) >= {"skipper", "crew"}),
    }
    return unique, stats


def alias_candidates(people: list[dict]) -> list[dict]:
    """Flag probable typos/aliases. Never merge."""
    out = []
    for i, a in enumerate(people):
        for b in people[i + 1 :]:
            if a.get("ssl_id") and b.get("ssl_id") and a["ssl_id"] == b["ssl_id"]:
                continue
            if a.get("slug") and b.get("slug") and a["slug"] == b["slug"]:
                continue
            na, nb = a.get("normalized_name") or "", b.get("normalized_name") or ""
            if not na or not nb:
                continue
            reason = None
            dist = levenshtein(na, nb)
            if na == nb:
                reason = "same_normalized_name_distinct_ssl_identity"
            elif dist <= 2 and min(len(na), len(nb)) >= 8:
                reason = f"normalized_name_edit_distance_{dist}"
            else:
                a_parts, b_parts = na.split(), nb.split()
                if len(a_parts) >= 2 and len(b_parts) >= 2 and a_parts[-1] == b_parts[-1]:
                    fd = levenshtein(a_parts[0], b_parts[0])
                    if fd == 1 and a_parts[0] != b_parts[0]:
                        reason = "same_surname_first_name_edit_distance_1"
            if reason:
                out.append(
                    {
                        "reason": reason,
                        "a": {
                            "ssl_id": a.get("ssl_id"),
                            "slug": a.get("slug"),
                            "displayed_name": a.get("displayed_name"),
                        },
                        "b": {
                            "ssl_id": b.get("ssl_id"),
                            "slug": b.get("slug"),
                            "displayed_name": b.get("displayed_name"),
                        },
                    }
                )
    return out


# ---------------------------------------------------------------------------
# SAS matching
# ---------------------------------------------------------------------------


def db_connect(db_url: str):
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn, psycopg2.extras.RealDictCursor


def table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (name,),
    )
    return cur.fetchone() is not None


def ensure_sailor_table(conn, cur) -> None:
    if not table_exists(cur, "sas_id_personal"):
        cur.execute(
            """
            CREATE TABLE public.sas_id_personal (
                id SERIAL PRIMARY KEY,
                sa_sailing_id VARCHAR NOT NULL UNIQUE,
                full_name VARCHAR,
                first_name VARCHAR,
                last_name VARCHAR
            )
            """
        )
        conn.commit()
        print("[db] created public.sas_id_personal (minimal local identity table)", flush=True)
    sql = MIGRATION.read_text(encoding="utf-8")
    cur.execute(sql)
    conn.commit()
    print(f"[db] applied {MIGRATION.relative_to(ROOT)}", flush=True)


def load_sas_index(cur) -> dict:
    cur.execute(
        """
        SELECT sa_sailing_id::text AS sa_sailing_id,
               full_name, first_name, last_name,
               ssl_id, ssl_slug, ssl_profile_url, ssl_match_status
        FROM public.sas_id_personal
        """
    )
    rows = list(cur.fetchall() or [])
    by_ssl_id = {}
    by_slug = {}
    by_norm = defaultdict(list)
    for row in rows:
        if row.get("ssl_id") is not None:
            by_ssl_id[int(row["ssl_id"])] = row
        slug = (row.get("ssl_slug") or "").strip()
        if slug:
            by_slug[slug] = row
        full = row.get("full_name") or ""
        if not full:
            full = " ".join(p for p in (row.get("first_name") or "", row.get("last_name") or "") if p)
        norm = normalize_name(full)
        if norm:
            by_norm[norm].append(row)
        # SAS public slugs are typically first-last; also index that form.
        built = normalize_name(f"{row.get('first_name') or ''} {row.get('last_name') or ''}")
        if built and built != norm:
            by_norm[built].append(row)
    return {"rows": rows, "by_ssl_id": by_ssl_id, "by_slug": by_slug, "by_norm": by_norm}


def sas_search_live(name: str, slug: str | None, failures: list) -> list[dict]:
    found = []
    seen = set()

    def add_hits(payload) -> None:
        rows = payload if isinstance(payload, list) else []
        if isinstance(payload, dict):
            for key in ("results", "sailors", "data", "items"):
                if isinstance(payload.get(key), list):
                    rows = payload[key]
                    break
        for row in rows:
            if not isinstance(row, dict):
                continue
            sas_id = str(row.get("sas_id") or row.get("sa_sailing_id") or "").strip()
            if not sas_id or sas_id in seen:
                continue
            seen.add(sas_id)
            first = str(row.get("first_names") or row.get("first_name") or "").strip()
            last = str(row.get("surname") or row.get("last_name") or "").strip()
            full = str(row.get("name") or row.get("full_name") or "").strip()
            if not full:
                full = " ".join(p for p in (first, last) if p)
            found.append(
                {
                    "sa_sailing_id": sas_id,
                    "full_name": full,
                    "first_name": first,
                    "last_name": last,
                    "source": "live_search",
                }
            )

    q = urllib.parse.urlencode({"q": name, "limit": "200"})
    status, body, err = http_get(f"{SAS_SEARCH}?{q}", accept="application/json", timeout=30)
    if status == 200 and body:
        try:
            add_hits(json.loads(body.decode("utf-8")))
        except Exception as e:
            failures.append({"stage": "sas_search_parse", "name": name, "error": str(e)})
    elif status != 200:
        failures.append({"stage": "sas_search", "name": name, "error": err or f"status {status}"})

    if slug:
        q2 = urllib.parse.urlencode({"slug": slug})
        status, body, err = http_get(f"{SAS_RESOLVE}?{q2}", accept="application/json", timeout=30)
        if status == 200 and body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as e:
                failures.append({"stage": "sas_resolve_parse", "slug": slug, "error": str(e)})
                payload = None
            if isinstance(payload, dict) and payload.get("sas_id"):
                sas_id = str(payload["sas_id"]).strip()
                if sas_id not in seen:
                    full = str(payload.get("name") or "").strip()
                    parts = full.split(None, 1)
                    found.append(
                        {
                            "sa_sailing_id": sas_id,
                            "full_name": full,
                            "first_name": parts[0] if parts else "",
                            "last_name": parts[1] if len(parts) > 1 else "",
                            "source": "live_slug_resolve",
                            "resolved_slug": slug,
                        }
                    )
        elif status not in (200, 404):
            failures.append({"stage": "sas_resolve", "slug": slug, "error": err or f"status {status}"})
    return found


def match_person(person: dict, index: dict, live_hits: list[dict]) -> dict:
    ssl_id = person.get("ssl_id")
    slug = person.get("slug")
    norm = person.get("normalized_name") or ""

    exact_id = index["by_ssl_id"].get(ssl_id) if ssl_id is not None else None
    exact_slug = index["by_slug"].get(slug) if slug else None
    # Also treat live slug-resolve as exact slug when SAS slug equals SSL slug.
    live_slug_hits = [h for h in live_hits if h.get("source") == "live_slug_resolve"]
    name_hits_db = list(index["by_norm"].get(norm) or [])
    name_hits_live = [h for h in live_hits if normalize_name(h.get("full_name") or "") == norm]
    # Unique by sa_sailing_id
    def uniq(rows: list[dict]) -> list[dict]:
        seen = {}
        for r in rows:
            seen[str(r.get("sa_sailing_id"))] = r
        return list(seen.values())

    name_hits = uniq(name_hits_db + name_hits_live)

    decision = {
        "ssl_id": ssl_id,
        "slug": slug,
        "displayed_name": person.get("displayed_name"),
        "source_roles": person.get("source_roles"),
        "status": "manual_review",
        "reason": None,
        "sa_sailing_id": None,
        "match_via": None,
        "candidates": [],
    }

    if exact_id:
        decision.update(
            {
                "status": "confirmed",
                "match_via": "exact_ssl_id",
                "sa_sailing_id": str(exact_id["sa_sailing_id"]),
                "reason": "existing ssl_id on sas_id_personal",
            }
        )
        return decision

    slug_sas = None
    if exact_slug:
        slug_sas = str(exact_slug["sa_sailing_id"])
    elif len(live_slug_hits) == 1:
        slug_sas = str(live_slug_hits[0]["sa_sailing_id"])
    elif len(live_slug_hits) > 1:
        decision.update(
            {
                "status": "manual_review",
                "reason": "ssl slug resolved to multiple SAS ids",
                "candidates": [h["sa_sailing_id"] for h in live_slug_hits],
            }
        )
        return decision

    unique_name = name_hits[0] if len(name_hits) == 1 else None

    if slug_sas and unique_name and str(unique_name["sa_sailing_id"]) != slug_sas:
        decision.update(
            {
                "status": "manual_review",
                "reason": "exact slug and unique name point at different SAS ids",
                "candidates": [slug_sas, str(unique_name["sa_sailing_id"])],
            }
        )
        return decision

    if slug_sas:
        decision.update(
            {
                "status": "confirmed",
                "match_via": "exact_ssl_slug" if exact_slug else "exact_ssl_slug_live_resolve",
                "sa_sailing_id": slug_sas,
                "reason": "SSL slug uniquely maps to one SAS sailor",
            }
        )
        return decision

    if unique_name:
        decision.update(
            {
                "status": "confirmed",
                "match_via": "unique_normalized_full_name",
                "sa_sailing_id": str(unique_name["sa_sailing_id"]),
                "reason": "exactly one SAS sailor with this normalized full name",
            }
        )
        return decision

    if len(name_hits) > 1:
        decision.update(
            {
                "status": "manual_review",
                "reason": "normalized full name matches multiple SAS sailors",
                "candidates": [str(r["sa_sailing_id"]) for r in name_hits],
            }
        )
        return decision

    decision.update(
        {
            "status": "unmatched",
            "reason": "no exact ssl_id, exact slug, or unique normalized name match",
            "candidates": [str(r["sa_sailing_id"]) for r in live_hits],
        }
    )
    return decision


def apply_confirmed(conn, cur, decision: dict, person: dict, live_hits: list[dict], allow_seed: bool) -> str:
    """Update ssl_* on an existing SAS row. Never invent SAS IDs. Never overwrite a different ssl_id."""
    sas_id = decision.get("sa_sailing_id")
    ssl_id = person.get("ssl_id")
    slug = person.get("slug")
    url = person.get("profile_url")
    if not sas_id:
        return "skipped_no_sas_id"

    cur.execute(
        "SELECT sa_sailing_id::text AS sa_sailing_id, ssl_id, ssl_slug FROM public.sas_id_personal WHERE sa_sailing_id::text = %s",
        (str(sas_id),),
    )
    existing = cur.fetchone()
    if existing is None:
        if not allow_seed:
            return "skipped_sas_row_missing"
        hit = next((h for h in live_hits if str(h.get("sa_sailing_id")) == str(sas_id)), None)
        if hit is None:
            return "skipped_sas_row_missing"
        cur.execute(
            """
            INSERT INTO public.sas_id_personal (sa_sailing_id, full_name, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (sa_sailing_id) DO NOTHING
            """,
            (str(sas_id), hit.get("full_name"), hit.get("first_name"), hit.get("last_name")),
        )
        existing = {"sa_sailing_id": str(sas_id), "ssl_id": None, "ssl_slug": None}

    if existing.get("ssl_id") is not None and ssl_id is not None and int(existing["ssl_id"]) != int(ssl_id):
        return "conflict_existing_ssl_id"
    if existing.get("ssl_slug") and slug and existing["ssl_slug"] != slug:
        return "conflict_existing_ssl_slug"

    cur.execute(
        """
        UPDATE public.sas_id_personal
        SET ssl_id = COALESCE(ssl_id, %s),
            ssl_slug = COALESCE(ssl_slug, %s),
            ssl_profile_url = COALESCE(ssl_profile_url, %s),
            ssl_match_status = 'confirmed',
            ssl_last_checked_at = NOW()
        WHERE sa_sailing_id::text = %s
          AND (ssl_id IS NULL OR ssl_id = %s)
          AND (ssl_slug IS NULL OR ssl_slug = %s)
        """,
        (ssl_id, slug, url, str(sas_id), ssl_id, slug),
    )
    return "updated" if cur.rowcount else "unchanged"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def verification_queries() -> list[str]:
    return [
        "SELECT COUNT(*) AS sailor_rows FROM public.sas_id_personal;",
        "SELECT COUNT(*) AS ssl_id_populated FROM public.sas_id_personal WHERE ssl_id IS NOT NULL;",
        "SELECT COUNT(*) AS ssl_slug_populated FROM public.sas_id_personal WHERE ssl_slug IS NOT NULL;",
        "SELECT COUNT(*) AS ssl_confirmed FROM public.sas_id_personal WHERE ssl_match_status = 'confirmed';",
        "SELECT sa_sailing_id, full_name, ssl_id, ssl_slug, ssl_match_status, ssl_last_checked_at FROM public.sas_id_personal WHERE ssl_id IS NOT NULL ORDER BY ssl_last_checked_at DESC NULLS LAST, sa_sailing_id LIMIT 20;",
        "SELECT ssl_id, COUNT(*) FROM public.sas_id_personal WHERE ssl_id IS NOT NULL GROUP BY ssl_id HAVING COUNT(*) > 1;",
    ]


def run_verification(cur) -> list[dict]:
    out = []
    for sql in verification_queries():
        cur.execute(sql)
        rows = cur.fetchall() or []
        out.append({"sql": sql, "rows": [dict(r) for r in rows]})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SSL SA sailor discovery (weekly, idempotent)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Fetch and match; do not write ssl_* columns (default)")
    mode.add_argument("--apply", action="store_true", help="Write confirmed unique matches to sas_id_personal")
    parser.add_argument("--db-url", default=os.environ.get("DB_URL") or os.environ.get("DATABASE_URL") or "")
    parser.add_argument(
        "--audit-dir",
        default=str(ROOT / "var" / "ssl_sa_sailor_discovery"),
    )
    parser.add_argument(
        "--allow-seed-missing-sas-rows",
        action="store_true",
        help="If a confirmed SAS id is missing locally, copy that existing SAS identity then set SSL fields. Never invent IDs.",
    )
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    dry_run = not apply

    failures: list[dict] = []
    started = utc_now()
    print(f"[start] {iso(started)} dry_run={dry_run} apply={apply}", flush=True)

    skipper_rows = fetch_role_list(TYPE_SKIPPER, "skipper", failures)
    time.sleep(SLEEP_S)
    crew_rows = fetch_role_list(TYPE_CREW, "crew", failures)
    people, dedup_stats = dedupe_sailors(skipper_rows, crew_rows)
    aliases = alias_candidates(people)
    print(
        f"[dedupe] skipper={dedup_stats['skipper_rows_fetched']} "
        f"crew={dedup_stats['crew_rows_fetched']} unique_people={dedup_stats['unique_people']} "
        f"unique_ssl_ids={dedup_stats['unique_ssl_ids']} unique_slugs={dedup_stats['unique_slugs']}",
        flush=True,
    )
    print(f"[alias] candidates={len(aliases)} (not merged)", flush=True)

    db_url = args.db_url or "postgresql://ubuntu@/sailors_master?host=/var/run/postgresql"
    conn = None
    index = {"rows": [], "by_ssl_id": {}, "by_slug": {}, "by_norm": defaultdict(list)}
    local_row_count = 0
    allow_seed = bool(args.allow_seed_missing_sas_rows)
    try:
        conn, factory = db_connect(db_url)
        cur = conn.cursor(cursor_factory=factory)
        ensure_sailor_table(conn, cur)
        index = load_sas_index(cur)
        local_row_count = len(index["rows"])
        if local_row_count == 0:
            allow_seed = True
            print("[db] sas_id_personal is empty locally; confirmed matches may seed existing SAS ids from live lookup", flush=True)
        else:
            print(f"[db] sas_id_personal rows={local_row_count}", flush=True)
    except Exception as e:
        failures.append({"stage": "db_connect", "error": str(e)})
        print(f"[db] unavailable: {e}", flush=True)
        cur = None

    decisions = []
    for i, person in enumerate(people, 1):
        live_hits = []
        try:
            live_hits = sas_search_live(person.get("displayed_name") or "", person.get("slug"), failures)
        except Exception as e:
            failures.append({"stage": "sas_lookup", "slug": person.get("slug"), "error": str(e)})
        decision = match_person(person, index, live_hits)
        decision["live_hits"] = live_hits
        decisions.append(decision)
        if i % 25 == 0:
            print(f"[match] {i}/{len(people)}", flush=True)
        time.sleep(0.15)

    confirmed = [d for d in decisions if d["status"] == "confirmed"]
    unmatched = [d for d in decisions if d["status"] == "unmatched"]
    review = [d for d in decisions if d["status"] == "manual_review"]

    apply_counts = {"updated": 0, "unchanged": 0, "skipped_sas_row_missing": 0, "conflict_existing_ssl_id": 0, "conflict_existing_ssl_slug": 0, "skipped_no_sas_id": 0}
    if apply and cur is not None:
        for decision in confirmed:
            person = next(p for p in people if p.get("ssl_id") == decision.get("ssl_id") and p.get("slug") == decision.get("slug"))
            try:
                result = apply_confirmed(conn, cur, decision, person, decision.get("live_hits") or [], allow_seed)
                apply_counts[result] = apply_counts.get(result, 0) + 1
            except Exception as e:
                failures.append({"stage": "apply", "ssl_id": decision.get("ssl_id"), "error": str(e)})
                conn.rollback()
                continue
        conn.commit()
        print(f"[apply] {apply_counts}", flush=True)
    elif dry_run:
        print("[dry-run] no ssl_* columns written", flush=True)

    verify = []
    if cur is not None:
        verify = run_verification(cur)

    ended = utc_now()
    report = {
        "started_at": iso(started),
        "ended_at": iso(ended),
        "dry_run": dry_run,
        "apply": apply,
        "source": {
            "skipper_url": f"{WOS_RANKING}?main=individual&country=south-africa&type={TYPE_SKIPPER}",
            "crew_url": f"{WOS_RANKING}?main=individual&country=south-africa&type={TYPE_CREW}",
            "structured_api": WOS_API,
        },
        "skipper_rows_fetched": dedup_stats["skipper_rows_fetched"],
        "crew_rows_fetched": dedup_stats["crew_rows_fetched"],
        "unique_ssl_ids": dedup_stats["unique_ssl_ids"],
        "unique_slugs": dedup_stats["unique_slugs"],
        "unique_people": dedup_stats["unique_people"],
        "exact_overlap_ssl_ids": dedup_stats["exact_overlap_ssl_ids"],
        "exact_overlap_slugs": dedup_stats["exact_overlap_slugs"],
        "people_with_both_roles": dedup_stats["people_with_both_roles"],
        "duplicate_alias_candidates": len(aliases),
        "confirmed_sas_matches": len(confirmed),
        "unmatched_ssl_sailors": len(unmatched),
        "ambiguous_manual_review": len(review),
        "database_rows_updated": apply_counts["updated"] if apply else 0,
        "apply_counts": apply_counts if apply else None,
        "failures": failures,
        "alias_candidates": aliases,
        "confirmed": [
            {k: d[k] for k in ("ssl_id", "slug", "displayed_name", "sa_sailing_id", "match_via", "source_roles")}
            for d in confirmed
        ],
        "unmatched": [
            {k: d[k] for k in ("ssl_id", "slug", "displayed_name", "reason", "source_roles")}
            for d in unmatched
        ],
        "manual_review": [
            {k: d[k] for k in ("ssl_id", "slug", "displayed_name", "reason", "candidates", "source_roles")}
            for d in review
        ],
        "verification_queries": verify,
        "verification_sql": verification_queries(),
    }

    audit_dir = Path(args.audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    mode_name = "apply" if apply else "dry-run"
    report_path = audit_dir / f"ssl-sa-sailor-discovery-{mode_name}-{stamp}.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    summary_lines = [
        f"mode={'apply' if apply else 'dry-run'}",
        f"skipper_rows_fetched={report['skipper_rows_fetched']}",
        f"crew_rows_fetched={report['crew_rows_fetched']}",
        f"unique_ssl_ids={report['unique_ssl_ids']}",
        f"unique_slugs={report['unique_slugs']}",
        f"exact_overlap_ssl_ids={report['exact_overlap_ssl_ids']}",
        f"duplicate_alias_candidates={report['duplicate_alias_candidates']}",
        f"confirmed_sas_matches={report['confirmed_sas_matches']}",
        f"unmatched_ssl_sailors={report['unmatched_ssl_sailors']}",
        f"ambiguous_manual_review={report['ambiguous_manual_review']}",
        f"database_rows_updated={report['database_rows_updated']}",
        f"failures={len(failures)}",
        f"report_path={report_path}",
    ]
    print("\n=== SSL SA sailor discovery ===")
    print("\n".join(summary_lines))
    if verify:
        print("\n=== database verification ===")
        for item in verify:
            print(item["sql"])
            print(json.dumps(item["rows"], indent=2, default=str))
    if conn is not None:
        conn.close()
    return 1 if failures and report["skipper_rows_fetched"] == 0 and report["crew_rows_fetched"] == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
