#!/usr/bin/env python3
"""Fetch WorldOfSailors / SSL sailor Rank + SSL Points into sas_id_personal + JSON sidecar.

Modes:
  --due          refresh due rows plus linked rows with ssl_fetched_at IS NULL (daily)
  --all-linked   refresh all with ssl_profile_slug set (monthly); duplicate slugs skipped
  --queue-due    set ssl_refresh_due_at = last_result_date + 7 days for linked sailors
  --link-slug    probe SSA slug → WoS URL for one sailor (or --sas-id)
  --slug=...     fetch one WoS slug
  --sas-id=...   fetch one SAS id (must be linked or use --link-slug)
  --batch-link   link+fetch sailors with >= --min-regattas distinct regattas (default 35)
  --batch-ladder walk thresholds 35→30→…→--floor until a non-empty batch is processed
  --next         find the next qualifying sailor (ladder) and link+fetch that one only
  --dry-run      list candidates only (with --batch-link / --batch-ladder / --next)
  --self-test    parser + due/duplicate helpers (Timothy skipper, Thomas crew); no HTTP/DB

Does not edit api.py. Writes deploy/data/ssl_sailor_profiles.json for profile UI.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
# Nginx root is often /var/www/sailingsa — publish JSON where /data/ is served.
SITE_DATA_CANDIDATES = [
    Path("/var/www/sailingsa/data"),
    ROOT / "data",
    ROOT / "static" / "data",
    DEPLOY / "data",
]
JSON_NAME = "ssl_sailor_profiles.json"
WOS_LOG_DIR = DEPLOY / "data" / "wos"
USER_AGENT = "SailingSA-SSL-Fetch/1.0 (+https://sailingsa.co.za)"
# Distinct-regatta thresholds for progressive batching (highest first).
DEFAULT_LADDER = (35, 30, 25, 20, 15, 10)
DEFAULT_DUE_LIMIT = 500
# Due list: already-queued rows, plus linked profiles never fetched.
DUE_WHERE_SQL = """
            ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
              AND (
                (ssl_refresh_due_at IS NOT NULL AND ssl_refresh_due_at <= now())
                OR ssl_fetched_at IS NULL
              )
"""


def json_paths() -> list[Path]:
    paths: list[Path] = []
    for base in SITE_DATA_CANDIDATES:
        p = base / JSON_NAME
        if p not in paths:
            paths.append(p)
    return paths


def primary_json_path() -> Path:
    for base in SITE_DATA_CANDIDATES:
        if base.exists() or str(base).startswith("/var/www/sailingsa"):
            return base / JSON_NAME
    return DEPLOY / "data" / JSON_NAME


JSON_PATH = primary_json_path()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def db_connect():
    url = os.environ.get("DB_URL")
    if not url:
        raise SystemExit("Set DB_URL")
    if psycopg2 is None:
        raise SystemExit("psycopg2 required")
    return psycopg2.connect(url)


def fetch_html(url: str, timeout: int = 45, retries: int = 3) -> str:
    """GET HTML; retry briefly on WoS 5xx (common for some sailor pages)."""
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(1.2 * (attempt + 1))
                continue
            raise
        except Exception as e:
            last = e
            if attempt + 1 < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    raise last or RuntimeError(f"fetch failed: {url}")


def html_unescape(text: str) -> str:
    return html.unescape(text or "")


def _jsonish(html_text: str) -> str:
    """Unescape WoS Inertia JSON so ranking.type.skipper/crew can be regexed."""
    t = html_text or ""
    t = t.replace("\\u003c", "<").replace("\\u003e", ">")
    return t.replace('\\"', '"')


def _coerce_ssl_points(raw: str | None) -> int | float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        val = Decimal(str(raw).replace(",", ""))
    except Exception:
        return None
    if val == val.to_integral_value():
        return int(val)
    return float(val)


def parse_hero_rank(html_text: str) -> int | None:
    """Numeric hero Rank only. N/A / dash does not count as skipper-numeric."""
    m = re.search(r">Rank</p>\s*<p[^>]*>\s*([0-9][0-9,]*)\s*<", html_text or "", re.I)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def parse_role_ranking(html_text: str, role: str) -> tuple[int | None, int | float | None]:
    """First weekly ranking object for skipper or crew (position, points)."""
    role = (role or "").strip().lower()
    if role not in ("skipper", "crew"):
        return None, None
    text = _jsonish(html_text)
    tokens = (
        f'"type":"ranking.type.{role}","ranking":[',
        f'"type":"{role}","ranking":[',
    )
    chunk = ""
    for tok in tokens:
        i = text.find(tok)
        if i >= 0:
            chunk = text[i + len(tok) : i + len(tok) + 2500]
            break
    if not chunk:
        return None, None
    stripped = chunk.lstrip()
    if stripped.startswith("]"):
        return None, None
    first = chunk.split("},{", 1)[0]
    pm = re.search(r'"position"\s*:\s*(\d+)', first)
    pts = re.search(r'"points"\s*:\s*([0-9]+(?:\.[0-9]+)?)', first)
    rank = int(pm.group(1)) if pm else None
    points = _coerce_ssl_points(pts.group(1) if pts else None)
    return rank, points


def parse_ssl_points_boxes(html_text: str) -> int | float | None:
    """Digit boxes under SSL Points (skipper hero)."""
    m = re.search(r'class="rank-ssl-points[^"]*"[^>]*>', html_text or "", re.I)
    if m:
        chunk = html_text[m.end() : m.end() + 400]
        digits = re.findall(r'class="w-8[^"]*"[^>]*>\s*([0-9])\s*</div>', chunk)
        if not digits:
            digits = re.findall(r">\s*([0-9])\s*</div>", chunk)
        if digits:
            return int("".join(digits))
    m = re.search(r">SSL\s*Points?</p>\s*<p[^>]*>\s*([0-9][0-9,.]*)\s*<", html_text or "", re.I)
    if m:
        return _coerce_ssl_points(m.group(1))
    return None


def parse_ssl_profile(html_text: str, slug: str) -> dict[str, Any]:
    """Extract Rank + SSL Points (+ country) from WoS sailor HTML.

    Skipper when the hero Rank is numeric; otherwise crew ranking JSON.
    """
    out: dict[str, Any] = {
        "slug": slug,
        "rank": None,
        "points": None,
        "name": None,
        "country_code": None,
        "country_name": None,
        "selected_role": None,
        "skipper_rank": None,
        "crew_rank": None,
    }
    m = re.search(r'property="og:title"\s+content="([^"|]+)', html_text or "")
    if m:
        out["name"] = html_unescape(m.group(1).strip())
    hero_rank = parse_hero_rank(html_text)
    skipper_rank, skipper_points = parse_role_ranking(html_text, "skipper")
    crew_rank, crew_points = parse_role_ranking(html_text, "crew")
    box_points = parse_ssl_points_boxes(html_text)
    out["skipper_rank"] = hero_rank if hero_rank is not None else skipper_rank
    out["crew_rank"] = crew_rank
    if hero_rank is not None:
        out["rank"] = hero_rank
        out["points"] = box_points if box_points is not None else skipper_points
        out["selected_role"] = "skipper"
    elif crew_rank is not None:
        out["rank"] = crew_rank
        out["points"] = crew_points if crew_points is not None else box_points
        out["selected_role"] = "crew"
    else:
        out["points"] = box_points if box_points is not None else skipper_points
        out["selected_role"] = "skipper"
    # Nationality / country from embedded JSON (code_ssl e.g. GBR, RSA)
    m = re.search(
        r'"country"\s*:\s*\{[^{}]*?"code_ssl"\s*:\s*"([A-Z]{3})"[^{}]*?"name"\s*:\s*"([^"]+)"',
        html_text or "",
    )
    if not m:
        m = re.search(
            r'"country"\s*:\s*\{[^{}]*?"name"\s*:\s*"([^"]+)"[^{}]*?"code_ssl"\s*:\s*"([A-Z]{3})"',
            html_text or "",
        )
        if m:
            out["country_name"] = html_unescape(m.group(1))
            out["country_code"] = m.group(2)
    else:
        out["country_code"] = m.group(1)
        out["country_name"] = html_unescape(m.group(2))
    if not out["country_code"]:
        m = re.search(r"worldofsailors\.com/flags/[^\"']+/([a-z]{2})\.svg", html_text or "", re.I)
        if m:
            cc = m.group(1).upper()
            out["country_code"] = {"GB": "GBR", "ZA": "RSA", "AU": "AUS"}.get(cc, cc)
    return out


# Display club code for international sailors (WoS GBR → UK on SailingSA)
COUNTRY_CLUB_CODE = {
    "GBR": "UK",
    "GB": "UK",
    "RSA": "RSA",
    "ZA": "RSA",
    "AUS": "AUS",
}


def display_club_for_country(country_code: str | None) -> str | None:
    if not country_code:
        return None
    cc = country_code.strip().upper()
    return COUNTRY_CLUB_CODE.get(cc, cc)


def wos_url(slug: str) -> str:
    return f"https://worldofsailors.com/sailor/{slug.strip().strip('/')}"


def slugify_name(text: str) -> str:
    """WorldOfSailors-style slug: timothy-weaving, aydin-ohara."""
    s = unicodedata.normalize("NFKD", (text or "")).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = s.replace("'", "").replace("'", "").replace("`", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def candidate_slugs(full_name: str | None, first: str | None, last: str | None) -> list[str]:
    """Ordered unique slug guesses for a catalogue sailor."""
    full = (full_name or "").strip()
    first = (first or "").strip()
    last = (last or "").strip()
    bases: list[str] = []
    if full:
        bases.append(full)
    if first and last:
        bases.append(f"{first} {last}")
    # Apostrophe variants: O'Hara → ohara and o-hara
    extras: list[str] = []
    for b in list(bases):
        if "'" in b or "'" in b:
            extras.append(re.sub(r"['']", "", b))
            extras.append(re.sub(r"['']", "-", b))
            extras.append(re.sub(r"['']", " ", b))
    out: list[str] = []
    seen: set[str] = set()
    for b in bases + extras:
        slug = slugify_name(b)
        if slug and slug not in seen:
            seen.add(slug)
            out.append(slug)
    return out


def html_unescape(text: str) -> str:
    return html.unescape(text or "")


def names_match(ssa_name: str, wos_name: str | None) -> bool:
    """Require WoS og:title / name to align with catalogue name (avoid wrong John)."""
    if not wos_name:
        return False
    a = slugify_name(ssa_name)
    b = slugify_name(html_unescape(wos_name))
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = a.split("-"), b.split("-")
    sa, sb = set(ta), set(tb)
    if len(sa) >= 2 and sa == sb:
        return True
    if len(sa) >= 2 and sa.issubset(sb):
        return True
    # Rob ↔ Robert (same surname, first name prefix/stem)
    if len(ta) >= 2 and len(tb) >= 2 and ta[-1] == tb[-1]:
        fa, fb = ta[0], tb[0]
        if fa.startswith(fb) or fb.startswith(fa) or fa[:3] == fb[:3]:
            return True
    return False


def load_json_sidecar() -> dict[str, Any]:
    for p in json_paths():
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return {"updated_at": None, "sailors": {}}


def write_json_sidecar(data: dict[str, Any]) -> None:
    data["updated_at"] = utcnow().isoformat()
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    wrote = False
    for p in json_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(payload)
            wrote = True
        except Exception as e:
            print(f"WARN could not write {p}: {e}", file=sys.stderr)
    if not wrote:
        raise SystemExit("Failed to write ssl_sailor_profiles.json to any path")


def upsert_sidecar(sas_id: str, row: dict[str, Any]) -> None:
    data = load_json_sidecar()
    sailors = data.setdefault("sailors", {})
    sailors[str(sas_id)] = row
    write_json_sidecar(data)


def rebuild_sidecar_from_db(cur) -> int:
    has_country = True
    try:
        cur.execute(
            """
            SELECT sa_sailing_id, ssl_profile_slug, ssl_profile_url, ssl_rank, ssl_points,
                   ssl_fetched_at, ssl_match_status, full_name, ssl_country_code
            FROM sas_id_personal
            WHERE ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
            """
        )
    except Exception:
        has_country = False
        try:
            cur.connection.rollback()
        except Exception:
            pass
        cur.execute(
            """
            SELECT sa_sailing_id, ssl_profile_slug, ssl_profile_url, ssl_rank, ssl_points,
                   ssl_fetched_at, ssl_match_status, full_name
            FROM sas_id_personal
            WHERE ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
            """
        )
    data = load_json_sidecar()
    prev = data.get("sailors") or {}
    sailors: dict[str, Any] = {
        k: v
        for k, v in prev.items()
        if str(k).upper().startswith("NAME:") or str(k).upper().startswith("TMP:")
    }
    for row in cur.fetchall():
        if has_country:
            sid, slug, url, rank, points, fetched, status, name, country = row
        else:
            sid, slug, url, rank, points, fetched, status, name = row
            country = (prev.get(str(sid)) or {}).get("ssl_country_code")
        club = display_club_for_country(country)
        sailors[str(sid)] = {
            "sa_sailing_id": str(sid),
            "ssl_profile_slug": slug,
            "ssl_profile_url": url or wos_url(slug),
            "ssl_rank": int(rank) if rank is not None else None,
            "ssl_points": float(points) if points is not None else None,
            "ssl_fetched_at": fetched.isoformat() if fetched else None,
            "ssl_match_status": status,
            "name": name,
            "ssl_country_code": country,
            "ssl_display_club": club,
            "no_sas_id": False,
        }
    data["sailors"] = sailors
    write_json_sidecar(data)
    return len(sailors)


def apply_fetch(cur, sas_id: str, slug: str, parsed: dict[str, Any]) -> None:
    url = wos_url(slug)
    country = (parsed.get("country_code") or "").strip().upper() or None
    club = display_club_for_country(country)
    sid = str(sas_id)
    is_name_id = sid.upper().startswith("NAME:") or sid.upper().startswith("TMP:")

    if not is_name_id:
        # Best-effort country column (migration 163); ignore if not yet applied
        try:
            cur.execute(
                """
                UPDATE sas_id_personal
                SET ssl_profile_slug = %s,
                    ssl_profile_url = %s,
                    ssl_rank = %s,
                    ssl_points = %s,
                    ssl_fetched_at = now(),
                    ssl_refresh_due_at = NULL,
                    ssl_match_status = 'LINKED',
                    ssl_country_code = %s
                WHERE sa_sailing_id = %s
                """,
                (slug, url, parsed.get("rank"), parsed.get("points"), country, sid),
            )
        except Exception:
            try:
                cur.connection.rollback()
            except Exception:
                pass
            cur.execute(
                """
                UPDATE sas_id_personal
                SET ssl_profile_slug = %s,
                    ssl_profile_url = %s,
                    ssl_rank = %s,
                    ssl_points = %s,
                    ssl_fetched_at = now(),
                    ssl_refresh_due_at = NULL,
                    ssl_match_status = 'LINKED'
                WHERE sa_sailing_id = %s
                """,
                (slug, url, parsed.get("rank"), parsed.get("points"), sid),
            )

    upsert_sidecar(
        sid,
        {
            "sa_sailing_id": sid,
            "ssl_profile_slug": slug,
            "ssl_profile_url": url,
            "ssl_rank": parsed.get("rank"),
            "ssl_points": parsed.get("points"),
            "ssl_fetched_at": utcnow().isoformat(),
            "ssl_match_status": "LINKED",
            "name": parsed.get("name"),
            "ssl_country_code": country,
            "ssl_display_club": club,
            "no_sas_id": bool(is_name_id),
        },
    )


def probe_link(cur, sas_id: str, slug: str, *, ssa_name: str | None = None) -> bool:
    url = wos_url(slug)
    try:
        html = fetch_html(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            cur.execute(
                """
                UPDATE sas_id_personal
                SET ssl_match_status = 'UNMATCHED', ssl_profile_slug = NULL, ssl_profile_url = NULL
                WHERE sa_sailing_id = %s
                """,
                (str(sas_id),),
            )
            return False
        raise
    parsed = parse_ssl_profile(html, slug)
    if parsed.get("rank") is None and parsed.get("points") is None:
        # page may exist but not a sailor card
        if "Page not found" in html or "under construction" in html.lower():
            cur.execute(
                "UPDATE sas_id_personal SET ssl_match_status='UNMATCHED' WHERE sa_sailing_id=%s",
                (str(sas_id),),
            )
            return False
    if ssa_name and parsed.get("name") and not names_match(ssa_name, parsed.get("name")):
        cur.execute(
            """
            UPDATE sas_id_personal
            SET ssl_match_status = 'AMBIGUOUS', ssl_profile_slug = NULL, ssl_profile_url = NULL
            WHERE sa_sailing_id = %s
            """,
            (str(sas_id),),
        )
        print(
            f"AMBIGUOUS {sas_id}: SSA={ssa_name!r} WoS={parsed.get('name')!r} slug={slug}",
            file=sys.stderr,
        )
        return False
    apply_fetch(cur, sas_id, slug, parsed)
    return True


def probe_link_candidates(
    cur, sas_id: str, slugs: list[str], *, ssa_name: str | None = None, sleep_s: float = 0.4
) -> tuple[str, str | None]:
    """Try slugs in order. Returns (status, slug_or_none) where status is LINKED|UNMATCHED|ERROR|AMBIGUOUS."""
    last_err: Exception | None = None
    any_404 = False
    any_ambiguous = False
    for i, slug in enumerate(slugs):
        try:
            html = fetch_html(wos_url(slug))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                any_404 = True
                time.sleep(sleep_s)
                continue
            # 5xx — try next slug variant; do not mark UNMATCHED yet
            last_err = e
            time.sleep(sleep_s)
            continue
        except Exception as e:
            last_err = e
            time.sleep(sleep_s)
            continue
        parsed = parse_ssl_profile(html, slug)
        if "Page not found" in html or "under construction" in html.lower():
            any_404 = True
            time.sleep(sleep_s)
            continue
        if parsed.get("rank") is None and parsed.get("points") is None and not parsed.get("name"):
            any_404 = True
            time.sleep(sleep_s)
            continue
        if ssa_name and parsed.get("name") and not names_match(ssa_name, parsed.get("name")):
            any_ambiguous = True
            print(
                f"AMBIGUOUS {sas_id}: SSA={ssa_name!r} WoS={parsed.get('name')!r} slug={slug}",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
            continue
        apply_fetch(cur, sas_id, slug, parsed)
        return ("LINKED", slug)
    if any_ambiguous and not any_404:
        cur.execute(
            "UPDATE sas_id_personal SET ssl_match_status='AMBIGUOUS' WHERE sa_sailing_id=%s",
            (str(sas_id),),
        )
        return ("AMBIGUOUS", None)
    if any_404 and last_err is None:
        cur.execute(
            """
            UPDATE sas_id_personal
            SET ssl_match_status='UNMATCHED', ssl_profile_slug=NULL, ssl_profile_url=NULL
            WHERE sa_sailing_id=%s
            """,
            (str(sas_id),),
        )
        return ("UNMATCHED", None)
    if last_err is not None:
        cur.execute(
            "UPDATE sas_id_personal SET ssl_match_status='ERROR' WHERE sa_sailing_id=%s",
            (str(sas_id),),
        )
        return ("ERROR", None)
    cur.execute(
        "UPDATE sas_id_personal SET ssl_match_status='UNMATCHED' WHERE sa_sailing_id=%s",
        (str(sas_id),),
    )
    return ("UNMATCHED", None)


def sailor_regatta_counts_sql() -> str:
    """Distinct regattas per sailor (helm or crew)."""
    return """
        SELECT sid, count(DISTINCT regatta_id)::int AS n FROM (
          SELECT helm_sa_sailing_id::text AS sid, regatta_id
          FROM results WHERE helm_sa_sailing_id IS NOT NULL
          UNION
          SELECT crew_sa_sailing_id::text, regatta_id
          FROM results WHERE crew_sa_sailing_id IS NOT NULL
        ) x
        WHERE sid IS NOT NULL AND btrim(sid) <> ''
        GROUP BY sid
    """


def sync_ssl_link_queue(cur, *, min_regattas: int = 5) -> dict[str, int]:
    """Rebuild ssl_sailor_link_queue: PENDING (still to test) + PARKED (ERROR/AMBIGUOUS).

    LINKED / successfully matched sailors are dropped from the queue.
    """
    cur.execute(
        f"""
        WITH counts AS (
          {sailor_regatta_counts_sql()}
        ),
        src AS (
          SELECT
            c.sid AS sa_sailing_id,
            coalesce(
              nullif(btrim(s.full_name), ''),
              nullif(btrim(concat_ws(' ', s.first_name, s.last_name)), ''),
              c.sid
            ) AS full_name,
            c.n AS regatta_count,
            CASE
              WHEN s.ssl_match_status IN ('ERROR', 'AMBIGUOUS', 'UNMATCHED') THEN 'PARKED'
              ELSE 'PENDING'
            END AS queue_status,
            s.ssl_match_status,
            CASE
              WHEN s.ssl_match_status = 'ERROR' THEN 'WoS probe failed (parked for revisit)'
              WHEN s.ssl_match_status = 'AMBIGUOUS' THEN 'Name mismatch vs WoS (parked for revisit)'
              WHEN s.ssl_match_status = 'UNMATCHED' THEN 'No WoS profile found (parked for revisit)'
              ELSE 'Still to test'
            END AS notes,
            s.ssl_fetched_at AS last_attempt_at
          FROM counts c
          JOIN sas_id_personal s ON s.sa_sailing_id = c.sid
          WHERE c.n >= %s
            AND c.sid !~* '^(NAME:|TMP:)'
            AND (
              s.ssl_match_status IN ('ERROR', 'AMBIGUOUS', 'UNMATCHED')
              OR (
                (s.ssl_profile_slug IS NULL OR btrim(s.ssl_profile_slug) = '')
                AND (s.ssl_match_status IS NULL OR btrim(s.ssl_match_status) = '')
              )
            )
        ),
        upserted AS (
          INSERT INTO ssl_sailor_link_queue AS q (
            sa_sailing_id, full_name, regatta_count, queue_status,
            ssl_match_status, notes, updated_at, last_attempt_at
          )
          SELECT
            sa_sailing_id, full_name, regatta_count, queue_status,
            ssl_match_status, notes, now(), last_attempt_at
          FROM src
          ON CONFLICT (sa_sailing_id) DO UPDATE SET
            full_name = EXCLUDED.full_name,
            regatta_count = EXCLUDED.regatta_count,
            queue_status = EXCLUDED.queue_status,
            ssl_match_status = EXCLUDED.ssl_match_status,
            notes = EXCLUDED.notes,
            updated_at = now(),
            last_attempt_at = coalesce(EXCLUDED.last_attempt_at, q.last_attempt_at)
          RETURNING queue_status
        ),
        deleted AS (
          DELETE FROM ssl_sailor_link_queue q
          WHERE NOT EXISTS (SELECT 1 FROM src s WHERE s.sa_sailing_id = q.sa_sailing_id)
          RETURNING 1
        )
        SELECT
          (SELECT count(*) FROM upserted WHERE queue_status = 'PENDING') AS pending,
          (SELECT count(*) FROM upserted WHERE queue_status = 'PARKED') AS parked,
          (SELECT count(*) FROM deleted) AS removed
        """,
        (min_regattas,),
    )
    pending, parked, removed = cur.fetchone()
    return {
        "pending": int(pending or 0),
        "parked": int(parked or 0),
        "removed": int(removed or 0),
        "min_regattas": int(min_regattas),
    }


def list_batch_candidates(
    cur,
    min_regattas: int,
    *,
    max_regattas: int | None = None,
    limit: int | None = None,
    include_done: bool = False,
    retry_errors: bool = False,
) -> list[dict[str, Any]]:
    """Sailors with distinct regatta count in [min_regattas, max_regattas).

    Count = distinct regatta_id as helm or crew (same basis as profile “N regattas”).
    """
    where_extra = ""
    params: list[Any] = [min_regattas]
    if max_regattas is not None:
        where_extra += " AND c.n < %s"
        params.append(max_regattas)
    if not include_done:
        where_extra += " AND (s.ssl_profile_slug IS NULL OR btrim(s.ssl_profile_slug) = '')"
        if retry_errors:
            where_extra += """
              AND (
                s.ssl_match_status IS NULL
                OR btrim(s.ssl_match_status) = ''
                OR s.ssl_match_status IN ('ERROR', 'AMBIGUOUS')
              )
            """
        else:
            # Fresh only — skip ERROR/UNMATCHED/AMBIGUOUS/LINKED leftovers
            where_extra += """
              AND (s.ssl_match_status IS NULL OR btrim(s.ssl_match_status) = '')
            """
    lim = ""
    if limit is not None:
        lim = " LIMIT %s"
        params.append(limit)
    cur.execute(
        f"""
        WITH counts AS (
          {sailor_regatta_counts_sql()}
        )
        SELECT c.sid, c.n, s.full_name, s.first_name, s.last_name,
               s.ssl_match_status, s.ssl_profile_slug
        FROM counts c
        JOIN sas_id_personal s ON s.sa_sailing_id = c.sid
        WHERE c.n >= %s
        {where_extra}
        ORDER BY c.n DESC, s.full_name NULLS LAST, c.sid
        {lim}
        """,
        params,
    )
    rows = []
    for sid, n, full, first, last, status, slug in cur.fetchall():
        name = (full or f"{first or ''} {last or ''}").strip()
        rows.append(
            {
                "sa_sailing_id": str(sid),
                "regatta_count": int(n),
                "full_name": name,
                "first_name": first,
                "last_name": last,
                "ssl_match_status": status,
                "ssl_profile_slug": slug,
                "slugs": candidate_slugs(full, first, last),
            }
        )
    return rows


def pick_ladder_threshold(
    cur, start: int, floor: int, step: int, *, retry_errors: bool = False, limit: int | None = None
) -> tuple[int, list[dict[str, Any]]]:
    """Find highest threshold with pending candidates: start, start-step, … floor.

    Always uses count >= threshold (already-linked/parked are excluded), so lower
    bands are not skipped after the top band is finished.
    """
    t = start
    while t >= floor:
        cands = list_batch_candidates(cur, t, retry_errors=retry_errors, limit=limit)
        if cands:
            return t, cands
        t -= step
    return floor, []


def run_batch_link(
    cur,
    conn,
    candidates: list[dict[str, Any]],
    *,
    sleep_s: float,
    dry_run: bool,
) -> dict[str, int]:
    stats = {"LINKED": 0, "UNMATCHED": 0, "AMBIGUOUS": 0, "ERROR": 0, "SKIP": 0}
    if dry_run:
        for c in candidates:
            print(
                f"CANDIDATE regs={c['regatta_count']} id={c['sa_sailing_id']} "
                f"name={c['full_name']!r} slugs={c['slugs']}"
            )
        print(f"Dry-run: {len(candidates)} candidates (no writes)")
        return stats

    for c in candidates:
        sid = c["sa_sailing_id"]
        slugs = c["slugs"]
        if not slugs:
            cur.execute(
                "UPDATE sas_id_personal SET ssl_match_status='UNMATCHED' WHERE sa_sailing_id=%s",
                (sid,),
            )
            conn.commit()
            stats["UNMATCHED"] += 1
            print(f"UNMATCHED {sid} (no slug from name {c['full_name']!r})")
            continue
        try:
            status, slug = probe_link_candidates(
                cur, sid, slugs, ssa_name=c["full_name"], sleep_s=sleep_s
            )
            conn.commit()
            stats[status] = stats.get(status, 0) + 1
            print(f"{status} {sid} {c['full_name']!r} slug={slug} regs={c['regatta_count']}")
        except Exception as e:
            conn.rollback()
            stats["ERROR"] += 1
            print(f"ERROR {sid} {c['full_name']!r}: {e}", file=sys.stderr)
            try:
                cur.execute(
                    "UPDATE sas_id_personal SET ssl_match_status='ERROR' WHERE sa_sailing_id=%s",
                    (sid,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
        time.sleep(sleep_s)
    return stats


def queue_due_from_results(cur) -> int:
    """For LINKED sailors, set refresh due = last result calendar date + 7 days."""
    cur.execute(
        """
        WITH last_res AS (
          SELECT sid, max(d)::date AS last_d FROM (
            SELECT helm_sa_sailing_id::text AS sid,
                   coalesce(
                     rg.end_date,
                     rg.start_date,
                     CASE
                       WHEN r.as_at_time::text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                         THEN substring(r.as_at_time::text from 1 for 10)::date
                       ELSE NULL
                     END
                   ) AS d
            FROM results r
            JOIN regattas rg ON rg.regatta_id = r.regatta_id
            WHERE r.helm_sa_sailing_id IS NOT NULL
            UNION ALL
            SELECT crew_sa_sailing_id::text,
                   coalesce(
                     rg.end_date,
                     rg.start_date,
                     CASE
                       WHEN r.as_at_time::text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                         THEN substring(r.as_at_time::text from 1 for 10)::date
                       ELSE NULL
                     END
                   )
            FROM results r
            JOIN regattas rg ON rg.regatta_id = r.regatta_id
            WHERE r.crew_sa_sailing_id IS NOT NULL
          ) x
          WHERE sid IS NOT NULL AND d IS NOT NULL
          GROUP BY sid
        )
        UPDATE sas_id_personal s
        SET ssl_refresh_due_at = ((lr.last_d + 7)::timestamp AT TIME ZONE 'Africa/Johannesburg')
        FROM last_res lr
        WHERE s.sa_sailing_id = lr.sid
          AND s.ssl_profile_slug IS NOT NULL
          AND btrim(s.ssl_profile_slug) <> ''
        """
    )
    return cur.rowcount


def filter_unique_slug_targets(
    pairs: list[tuple[str, str]],
) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    """Drop slugs that map to more than one SAS id. Returns (unique_pairs, dupes)."""
    counts: dict[str, list[str]] = {}
    for sid, slug in pairs:
        key = (slug or "").strip()
        counts.setdefault(key, []).append(str(sid))
    dups = {slug: ids for slug, ids in counts.items() if slug and len(ids) > 1}
    unique = [(str(sid), slug) for sid, slug in pairs if (slug or "").strip() not in dups]
    return unique, dups


def audit_duplicate_slugs(dups: dict[str, list[str]]) -> None:
    for slug, ids in sorted(dups.items()):
        print(
            f"AUDIT duplicate_slug slug={slug} ids={','.join(ids)} excluded={len(ids)}",
            file=sys.stderr,
        )


def list_duplicate_slugs(cur) -> dict[str, list[str]]:
    cur.execute(
        """
        SELECT btrim(ssl_profile_slug) AS slug,
               array_agg(sa_sailing_id::text ORDER BY sa_sailing_id) AS ids
        FROM sas_id_personal
        WHERE ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
        GROUP BY 1
        HAVING count(*) > 1
        """
    )
    dups: dict[str, list[str]] = {}
    for slug, ids in cur.fetchall():
        dups[str(slug)] = [str(x) for x in (ids or [])]
    return dups


def fetch_targets(
    cur,
    mode: str,
    slug: str | None,
    sas_id: str | None,
    *,
    limit: int | None = None,
    audit_dups: bool = True,
) -> list[tuple[str, str]]:
    if sas_id and slug:
        return [(str(sas_id), slug)]
    if sas_id:
        sid = str(sas_id)
        is_name_id = sid.upper().startswith("NAME:") or sid.upper().startswith("TMP:")
        if is_name_id:
            # NAME:/TMP: identities live in the sidecar, not sas_id_personal
            prev = (load_json_sidecar().get("sailors") or {}).get(sid) or {}
            sc_slug = (prev.get("ssl_profile_slug") or "").strip()
            if not sc_slug:
                raise SystemExit(f"sas_id {sas_id} has no ssl_profile_slug — use --link-slug")
            return [(sid, sc_slug)]
        cur.execute(
            "SELECT sa_sailing_id, ssl_profile_slug FROM sas_id_personal WHERE sa_sailing_id=%s",
            (sid,),
        )
        row = cur.fetchone()
        if not row or not row[1]:
            raise SystemExit(f"sas_id {sas_id} has no ssl_profile_slug — use --link-slug")
        return [(str(row[0]), row[1])]
    if slug:
        cur.execute(
            "SELECT sa_sailing_id, ssl_profile_slug FROM sas_id_personal WHERE ssl_profile_slug=%s",
            (slug,),
        )
        rows = cur.fetchall()
        if not rows:
            raise SystemExit(f"No sas_id_personal linked to slug {slug}")
        pairs = [(str(r[0]), r[1]) for r in rows]
        unique, dups = filter_unique_slug_targets(pairs)
        if dups and audit_dups:
            audit_duplicate_slugs(dups)
        return unique
    due_limit = DEFAULT_DUE_LIMIT if limit is None else int(limit)
    if mode == "due":
        if audit_dups:
            audit_duplicate_slugs(list_duplicate_slugs(cur))
        cur.execute(
            f"""
            SELECT sa_sailing_id, ssl_profile_slug
            FROM sas_id_personal
            WHERE {DUE_WHERE_SQL}
              AND btrim(ssl_profile_slug) NOT IN (
                SELECT btrim(ssl_profile_slug)
                FROM sas_id_personal
                WHERE ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
                GROUP BY 1
                HAVING count(*) > 1
              )
            ORDER BY ssl_fetched_at NULLS FIRST, ssl_refresh_due_at NULLS LAST, sa_sailing_id
            LIMIT %s
            """,
            (due_limit,),
        )
        return [(str(a), b) for a, b in cur.fetchall()]
    if mode == "all-linked":
        if audit_dups:
            audit_duplicate_slugs(list_duplicate_slugs(cur))
        sql = f"""
            SELECT sa_sailing_id, ssl_profile_slug
            FROM sas_id_personal
            WHERE ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
              AND btrim(ssl_profile_slug) NOT IN (
                SELECT btrim(ssl_profile_slug)
                FROM sas_id_personal
                WHERE ssl_profile_slug IS NOT NULL AND btrim(ssl_profile_slug) <> ''
                GROUP BY 1
                HAVING count(*) > 1
              )
            ORDER BY sa_sailing_id
        """
        if limit is not None:
            cur.execute(sql + " LIMIT %s", (int(limit),))
        else:
            cur.execute(sql)
        return [(str(a), b) for a, b in cur.fetchall()]
    return []


TIMOTHY_HTML = """
<meta property="og:title" content="Timothy Weaving | STARSAILORS">
<div class="min-w-32"><p class="text-xs font-bold">Rank</p><p class="text-4xl lg:text-5xl font-medium text-gold leading-none">7875</p></div>
<div class="min-w-40 font-bold"><p class="text-xs mb-2">SSL Points</p>
<div class="rank-ssl-points text-gold font-bold"><div class="w-8">1</div><div class="w-8">2</div><div class="w-8">2</div></div></div>
<script>\\"type\\":\\"ranking.type.skipper\\",\\"ranking\\":[{\\"id\\":1604,\\"position\\":7875,\\"points\\":121.66}] \\"type\\":\\"ranking.type.crew\\",\\"ranking\\":[]</script>
"""

THOMAS_HTML = """
<meta property="og:title" content="Thomas Henshilwood | STARSAILORS">
<div class="min-w-32"><p class="text-xs font-bold">Rank</p><p class="text-5xl font-medium text-gold leading-none">N/A</p></div>
<div class="min-w-40 font-bold"><p class="text-xs mb-2">SSL Points</p>
<div class="rank-ssl-points text-gold font-bold"><div class="w-8">0</div></div></div>
<script>\\"type\\":\\"ranking.type.skipper\\",\\"ranking\\":[{\\"id\\":1604,\\"position\\":80528,\\"points\\":0}] \\"type\\":\\"ranking.type.crew\\",\\"ranking\\":[{\\"id\\":1605,\\"position\\":11463,\\"points\\":46.25}]</script>
"""


def run_self_test() -> bool:
    """Internal parser + due/duplicate dry-run. No HTTP, no DB, no writes."""
    ok = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        if cond:
            print(f"PASS {name} {detail}".rstrip())
        else:
            ok = False
            print(f"FAIL {name} {detail}".rstrip(), file=sys.stderr)

    tim = parse_ssl_profile(TIMOTHY_HTML, "timothy-weaving")
    check("timothy.rank", tim.get("rank") == 7875, f"got {tim.get('rank')}")
    check("timothy.points", tim.get("points") == 122, f"got {tim.get('points')}")
    check("timothy.role", tim.get("selected_role") == "skipper", f"got {tim.get('selected_role')}")
    check("timothy.skipper_json", parse_role_ranking(TIMOTHY_HTML, "skipper") == (7875, 121.66))

    tom = parse_ssl_profile(THOMAS_HTML, "thomas-henshilwood")
    check("thomas.rank", tom.get("rank") == 11463, f"got {tom.get('rank')}")
    check("thomas.points", tom.get("points") == 46.25, f"got {tom.get('points')}")
    check("thomas.role", tom.get("selected_role") == "crew", f"got {tom.get('selected_role')}")
    check("thomas.not_skipper_80528", tom.get("rank") != 80528)
    check("thomas.hero_none", parse_hero_rank(THOMAS_HTML) is None)
    check("thomas.crew_json", parse_role_ranking(THOMAS_HTML, "crew") == (11463, 46.25))

    unique, dups = filter_unique_slug_targets(
        [
            ("7352", "thomas-henshilwood"),
            ("9612", "thomas-henshilwood"),
            ("21172", "timothy-weaving"),
        ]
    )
    check("dup.excluded", unique == [("21172", "timothy-weaving")], f"got {unique}")
    check(
        "dup.audit",
        dups == {"thomas-henshilwood": ["7352", "9612"]},
        f"got {dups}",
    )

    check("due.sql_never_fetched", "ssl_fetched_at IS NULL" in DUE_WHERE_SQL)
    check("due.limit_default", DEFAULT_DUE_LIMIT == 500)
    check("due.limit_configurable", DEFAULT_DUE_LIMIT != 0)
    print("SELFTEST", "OK" if ok else "FAIL")
    return ok


def log_scrape_run(cur, name: str, ok: bool, detail: str) -> None:
    try:
        cur.execute(
            """
            INSERT INTO scrape_runs (scrape_name, started_at, finished_at, status, notes)
            VALUES (%s, now(), now(), %s, %s)
            """,
            (name, "ok" if ok else "error", detail[:2000]),
        )
    except Exception:
        pass  # table may differ


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--all-linked", action="store_true")
    ap.add_argument("--queue-due", action="store_true")
    ap.add_argument("--link-slug", action="store_true", help="Probe WoS URL for --sas-id using --slug or SSA slug")
    ap.add_argument("--slug")
    ap.add_argument("--sas-id")
    ap.add_argument("--rebuild-json-only", action="store_true")
    ap.add_argument(
        "--sync-queue",
        action="store_true",
        help="Rebuild ssl_sailor_link_queue (PENDING still-to-test + PARKED ERROR/AMBIGUOUS)",
    )
    ap.add_argument(
        "--batch-link",
        action="store_true",
        help="Link+fetch sailors with >= --min-regattas distinct regattas",
    )
    ap.add_argument(
        "--batch-ladder",
        action="store_true",
        help="Process highest pending threshold from --min-regattas down to --floor",
    )
    ap.add_argument("--min-regattas", type=int, default=35, help="Minimum distinct regattas (default 35)")
    ap.add_argument("--floor", type=int, default=10, help="Lowest ladder threshold (default 10)")
    ap.add_argument("--step", type=int, default=5, help="Ladder step (default 5)")
    ap.add_argument("--limit", type=int, default=None, help="Max sailors in this batch; --due default 500")
    ap.add_argument("--one", action="store_true", help="Process exactly one next qualifying sailor")
    ap.add_argument("--retry-errors", action="store_true", help="Include ERROR/AMBIGUOUS rows again")
    ap.add_argument("--dry-run", action="store_true", help="List batch candidates only")
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="Parser + duplicate/due helpers (Timothy skipper, Thomas crew); no HTTP/DB",
    )
    ap.add_argument("--sleep", type=float, default=0.5)
    args = ap.parse_args()

    if args.self_test:
        return 0 if run_self_test() else 1

    if args.one:
        args.limit = 1
        if not args.batch_link and not args.batch_ladder:
            args.batch_ladder = True

    conn = db_connect()
    cur = conn.cursor()

    if args.rebuild_json_only:
        n = rebuild_sidecar_from_db(cur)
        conn.commit()
        print(f"Rebuilt {JSON_PATH} with {n} sailors")
        return 0

    if args.sync_queue:
        q = sync_ssl_link_queue(cur, min_regattas=args.floor if args.floor else 5)
        conn.commit()
        print(
            f"ssl_sailor_link_queue synced min>={q['min_regattas']}: "
            f"PENDING={q['pending']} PARKED={q['parked']} removed={q['removed']}"
        )
        return 0

    if args.queue_due:
        n = queue_due_from_results(cur)
        conn.commit()
        print(f"Queued/updated ssl_refresh_due_at for {n} linked sailors")
        return 0

    if args.batch_link or args.batch_ladder:
        retry = bool(args.retry_errors)
        if args.batch_ladder:
            threshold, cands = pick_ladder_threshold(
                cur, args.min_regattas, args.floor, args.step, retry_errors=retry, limit=args.limit
            )
            print(f"Ladder picked threshold>={threshold} candidates={len(cands)}")
        else:
            cands = list_batch_candidates(
                cur, args.min_regattas, limit=args.limit, retry_errors=retry
            )
            threshold = args.min_regattas
            print(f"Batch min_regattas>={threshold} candidates={len(cands)}")
        if not cands:
            print("No pending candidates at this threshold")
            return 0
        stats = run_batch_link(cur, conn, cands, sleep_s=args.sleep, dry_run=args.dry_run)
        if not args.dry_run:
            rebuild_sidecar_from_db(cur)
            q = sync_ssl_link_queue(cur, min_regattas=args.floor if args.floor else 5)
            log_scrape_run(
                cur,
                "ssl_sailor_batch_link",
                stats.get("ERROR", 0) == 0,
                f"threshold>={threshold} {stats} queue={q}",
            )
            conn.commit()
            print(f"Batch done threshold>={threshold} {stats} → {JSON_PATH}")
            print(
                f"Queue PENDING={q['pending']} PARKED={q['parked']} removed={q['removed']}"
            )
        return 0 if stats.get("ERROR", 0) == 0 else 1

    if args.link_slug:
        if not args.sas_id:
            raise SystemExit("--link-slug requires --sas-id")
        sid = str(args.sas_id)
        is_name_id = sid.upper().startswith("NAME:") or sid.upper().startswith("TMP:")
        ssa_name = ""
        if not is_name_id:
            cur.execute(
                "SELECT full_name, first_name, last_name FROM sas_id_personal WHERE sa_sailing_id=%s",
                (sid,),
            )
            row = cur.fetchone()
            if not row:
                raise SystemExit("unknown sas_id")
            full, first, last = row
            ssa_name = (full or f"{first or ''} {last or ''}").strip()
            if args.slug:
                slugs = [args.slug]
            else:
                slugs = candidate_slugs(full, first, last)
        else:
            # NAME:rob-skinner → derive display name + allow explicit WoS slug (robert-skinner)
            bare = re.sub(r"^NAME:", "", sid, flags=re.I).replace("-", " ").strip()
            ssa_name = bare.title()
            if args.slug:
                slugs = [args.slug]
            else:
                parts = bare.split()
                slugs = candidate_slugs(bare, parts[0] if parts else None, parts[-1] if len(parts) > 1 else None)
                # common first-name expansions for short forms
                if parts and parts[0].lower() == "rob":
                    slugs = list(dict.fromkeys([slugify_name(f"robert {' '.join(parts[1:])}")] + slugs))
        status, slug = probe_link_candidates(
            cur, sid, slugs, ssa_name=ssa_name, sleep_s=args.sleep
        )
        conn.commit()
        if not is_name_id:
            rebuild_sidecar_from_db(cur)
            conn.commit()
        print(status, sid, slug or (slugs[0] if slugs else None))
        return 0 if status == "LINKED" else 1

    mode = "due" if args.due else ("all-linked" if args.all_linked else "one")
    targets = fetch_targets(cur, mode, args.slug, args.sas_id, limit=args.limit)
    if args.dry_run and (args.due or args.all_linked or args.slug or args.sas_id):
        print(f"Dry-run {mode}: {len(targets)} targets (no fetch)")
        for sid, slug in targets:
            print(f"TARGET {sid} {slug}")
        return 0
    if not targets:
        print("No targets")
        rebuild_sidecar_from_db(cur)
        conn.commit()
        return 0

    ok_n = fail_n = 0
    WOS_LOG_DIR.mkdir(parents=True, exist_ok=True)
    for sid, slug in targets:
        try:
            html = fetch_html(wos_url(slug))
            parsed = parse_ssl_profile(html, slug)
            apply_fetch(cur, sid, slug, parsed)
            conn.commit()
            ok_n += 1
            print(
                f"OK {sid} {slug} rank={parsed.get('rank')} points={parsed.get('points')}"
                f" role={parsed.get('selected_role')}"
            )
        except Exception as e:
            conn.rollback()
            fail_n += 1
            print(f"FAIL {sid} {slug}: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    rebuild_sidecar_from_db(cur)
    log_scrape_run(cur, "ssl_sailor_profiles", fail_n == 0, f"ok={ok_n} fail={fail_n} mode={mode}")
    conn.commit()
    print(f"Done ok={ok_n} fail={fail_n} → {JSON_PATH}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
