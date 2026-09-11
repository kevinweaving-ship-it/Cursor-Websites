"""Boat names directory — /boat-names list and /boat-name/{slug} detail pages."""
from __future__ import annotations

import html as html_module
import json
import re
from collections import defaultdict
from typing import Any, Callable, Optional

import psycopg2.extras

BOAT_SEARCH_SCRIPT = """
(function () {
  var input = document.getElementById('boat-names-filter');
  var list = document.getElementById('boat-names-list');
  var empty = document.getElementById('boat-names-empty');
  var countEl = document.getElementById('boat-names-count');
  if (!input || !list) return;
  function apply() {
    var q = (input.value || '').trim().toLowerCase();
    var shown = 0;
    list.querySelectorAll('.boat-class-group').forEach(function (grp) {
      var groupShown = 0;
      grp.querySelectorAll('.boat-card').forEach(function (card) {
        var hay = (card.getAttribute('data-search') || '').toLowerCase();
        var ok = !q || hay.indexOf(q) !== -1;
        card.style.display = ok ? '' : 'none';
        if (ok) { shown++; groupShown++; }
      });
      grp.style.display = groupShown ? '' : 'none';
    });
    if (empty) empty.style.display = shown ? 'none' : 'block';
    if (countEl) countEl.textContent = shown + ' boat' + (shown === 1 ? '' : 's');
  }
  input.addEventListener('input', apply);
  apply();
})();
"""


def boat_name_slug(display_name: str) -> str:
    if not display_name or not isinstance(display_name, str):
        return ""
    s = display_name.strip().lower().replace("&", " and ")
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _boat_name_sponsor_brands() -> list[tuple[str, str, str, str]]:
    """(pat, sponsor_slug, logo_path, alt) — longer / more specific first where needed."""
    return [
        (r"north\s+sails", "north-sails", "/artwork/Sponsor Logo/North-Sails.png", "North Sails"),
        (r"ullman\s+sails", "ullman", "/artwork/Sponsor Logo/Ullman-Sails.png", "Ullman Sails"),
        (r"ullman", "ullman", "/artwork/Sponsor Logo/Ullman-Sails.png", "Ullman Sails"),
        (r"cell\s*c\b", "cell-c", "/artwork/Sponsor Logo/Cell-C.png", "Cell C"),
        (r"\bamtec\b", "amtec", "/artwork/Sponsor Logo/AMTEC.png", "AMTEC"),
        (r"nitro", "nitro", "/artwork/Sponsor Logo/Nitro.png", "Nitro"),
        (r"\bh2[0o]\b", "h2o", "/artwork/Sponsor Logo/H2O.png", "H2O"),
    ]


def _boat_name_sponsor_brand(display_name: str) -> Optional[tuple[str, str, str, str]]:
    """If boat name contains a brand sponsor: (pat, sponsor_slug, logo_path, alt).

    Baby J / RCYC Academy: owner is RCYCA — not North Sails (event-only sponsor).
    """
    bn = (display_name or "").strip()
    if not bn:
        return None
    low = bn.casefold()
    if low in ("baby j", "babyj") or "rcyc academy" in low:
        return None
    for pat, slug, path, alt in _boat_name_sponsor_brands():
        if re.search(pat, bn, flags=re.I):
            return (pat, slug, path, alt)
    return None


def _boat_name_title_with_sponsor_html(display_name: str) -> tuple[str, Optional[tuple[str, str, str]]]:
    """Build h1 HTML with brand text → sponsor logo(s) (links to /sponsors/…).

    Returns (title_html, header_logo_or_none) where header_logo is
    (logo_url, logo_href, logo_alt) for the large title logo slot (first brand).
    Supports multi-sponsor names e.g. AMTEC NITRO.
    """
    bn = (display_name or "").strip()
    low = bn.casefold()
    # Baby J — RCYCA is the owner logo (not North Sails)
    if low in ("baby j", "babyj") or "rcyc academy" in low:
        return (
            html_module.escape("Baby J"),
            ("/artwork/Club Logo/RCYC.png", "/club/rcyc", "RCYCA"),
        )

    matches: list[tuple[int, int, str, str, str]] = []
    for pat, slug, path, alt in _boat_name_sponsor_brands():
        for m in re.finditer(pat, bn, flags=re.I):
            matches.append((m.start(), m.end(), slug, path, alt))
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    chosen: list[tuple[int, int, str, str, str]] = []
    for m in matches:
        if any(m[0] < c[1] and m[1] > c[0] for c in chosen):
            continue
        chosen.append(m)
    chosen.sort(key=lambda x: x[0])
    if not chosen:
        return html_module.escape(bn), None

    parts: list[str] = []
    pos = 0
    for start, end, slug, path, alt in chosen:
        if start > pos:
            parts.append(html_module.escape(bn[pos:start]))
        src = html_module.escape(path)
        alt_e = html_module.escape(alt)
        href = html_module.escape(f"/sponsors/{slug}")
        parts.append(
            f'<a href="{href}" class="boat-name-sponsor-inline" title="{alt_e}">'
            f'<img src="{src}" alt="{alt_e}" class="boat-name-sponsor-inline-img" '
            f'loading="lazy" decoding="async"></a>'
        )
        pos = end
    if pos < len(bn):
        parts.append(html_module.escape(bn[pos:]))
    first = chosen[0]
    return "".join(parts).strip(), (first[3], f"/sponsors/{first[2]}", first[4])


def _site_header_nav() -> str:
    return (
        '<header class="site-header"><div class="container" style="display:flex;align-items:center;flex-wrap:wrap;gap:0.75rem;">'
        '<a href="/" class="logo js-go-home" title="Home"><img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>'
        '<nav class="nav-inline" aria-label="Main" style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin-right:auto;">'
        '<a href="/">Home</a><a href="/sailors">Sailors</a><a href="/regattas">Regattas</a>'
        '<a href="/classes">Classes</a><a href="/clubs">Clubs</a><a href="/boat-names">Boats</a>'
        '<a href="https://sailingsa.co.za/events">Events</a><a href="/stats">Statistics</a><a href="/about">About</a>'
        "</nav><div class=\"header-auth\" style=\"margin-left:auto;\"></div></div></header>"
    )


def boat_name_link_html(boat_name: str, norm_slug_map: dict[str, str]) -> str:
    """Link to /boat-name/{slug} when boat exists in results directory."""
    bn = (boat_name or "").strip()
    if not bn:
        return ""
    esc = html_module.escape(bn)
    slug = norm_slug_map.get(bn.lower())
    if slug:
        return f'<a href="/boat-name/{html_module.escape(slug)}">{esc}</a>'
    return esc


def load_boat_norm_slug_map(
    *,
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> dict[str, str]:
    """norm(lower boat_name) -> canonical slug for boats in results."""
    if not table_exists("results"):
        return {}
    conn = get_db_connection()
    cur = conn.cursor()
    out: dict[str, str] = {}
    try:
        cur.execute(
            """
            SELECT norm, display_name FROM (
              SELECT lower(trim(boat_name)) AS norm,
                     trim(boat_name) AS display_name,
                     count(*)::int AS cnt,
                     row_number() OVER (
                       PARTITION BY lower(trim(boat_name))
                       ORDER BY count(*) DESC, trim(boat_name)
                     ) AS rn
              FROM results
              WHERE boat_name IS NOT NULL AND trim(boat_name) <> ''
              GROUP BY lower(trim(boat_name)), trim(boat_name)
            ) v WHERE rn = 1
            """
        )
        for norm, display in cur.fetchall() or []:
            n = (norm or "").strip()
            d = (display or "").strip()
            if not n or not d:
                continue
            slug = boat_name_slug(d)
            if slug:
                out[n] = slug
    finally:
        cur.close()
        return_db_connection(conn)
    return out


def load_boat_directory_entries(
    *,
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> list[dict[str, Any]]:
    """Rich boat rows: class, regattas, sailors — sorted class then name in Python."""
    if not table_exists("results"):
        return []

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    entries: list[dict[str, Any]] = []
    try:
        cur.execute(
            """
            WITH boat_display AS (
              SELECT norm, display_name FROM (
                SELECT lower(trim(boat_name)) AS norm,
                       trim(boat_name) AS display_name,
                       count(*)::int AS cnt,
                       row_number() OVER (
                         PARTITION BY lower(trim(boat_name))
                         ORDER BY count(*) DESC, trim(boat_name)
                       ) AS rn
                FROM results
                WHERE boat_name IS NOT NULL AND trim(boat_name) <> ''
                GROUP BY lower(trim(boat_name)), trim(boat_name)
              ) v WHERE rn = 1
            ),
            boat_class AS (
              SELECT norm, class_name, class_id FROM (
                SELECT lower(trim(res.boat_name)) AS norm,
                       COALESCE(
                         NULLIF(trim(res.class_canonical), ''),
                         NULLIF(trim(cl.class_name), ''),
                         'Class pending'
                       ) AS class_name,
                       res.class_id,
                       count(*)::int AS cnt,
                       row_number() OVER (
                         PARTITION BY lower(trim(res.boat_name))
                         ORDER BY count(*) DESC
                       ) AS rn
                FROM results res
                LEFT JOIN classes cl ON cl.class_id = res.class_id
                WHERE res.boat_name IS NOT NULL AND trim(res.boat_name) <> ''
                GROUP BY lower(trim(res.boat_name)),
                         COALESCE(
                           NULLIF(trim(res.class_canonical), ''),
                           NULLIF(trim(cl.class_name), ''),
                           'Class pending'
                         ),
                         res.class_id
              ) t WHERE rn = 1
            ),
            boat_regs AS (
              SELECT lower(trim(res.boat_name)) AS norm,
                     json_agg(
                       DISTINCT jsonb_build_object(
                         'regatta_id', res.regatta_id::text,
                         'event_name', reg.event_name
                       )
                     ) AS regattas
              FROM results res
              JOIN regattas reg ON reg.regatta_id = res.regatta_id
              WHERE res.boat_name IS NOT NULL AND trim(res.boat_name) <> ''
              GROUP BY lower(trim(res.boat_name))
            ),
            sailor_rows AS (
              SELECT lower(trim(boat_name)) AS norm, trim(helm_name) AS name,
                     'Helm' AS role, helm_sa_sailing_id::text AS sas_id
              FROM results
              WHERE boat_name IS NOT NULL AND trim(coalesce(helm_name, '')) <> ''
              UNION ALL
              SELECT lower(trim(boat_name)), trim(crew_name), 'Crew', crew_sa_sailing_id::text
              FROM results
              WHERE boat_name IS NOT NULL AND trim(coalesce(crew_name, '')) <> ''
              UNION ALL
              SELECT lower(trim(boat_name)), trim(crew2_name), 'Crew', crew2_sa_sailing_id::text
              FROM results
              WHERE boat_name IS NOT NULL AND trim(coalesce(crew2_name, '')) <> ''
              UNION ALL
              SELECT lower(trim(boat_name)), trim(crew3_name), 'Crew', crew3_sa_sailing_id::text
              FROM results
              WHERE boat_name IS NOT NULL AND trim(coalesce(crew3_name, '')) <> ''
            ),
            boat_sailors AS (
              SELECT norm,
                     json_agg(
                       jsonb_build_object('name', name, 'role', role, 'sas_id', sas_id)
                       ORDER BY role, name
                     ) AS sailors
              FROM (
                SELECT DISTINCT ON (norm, lower(name), role, coalesce(sas_id, ''))
                  norm, name, role, sas_id
                FROM sailor_rows
                WHERE name IS NOT NULL AND trim(name) <> ''
                ORDER BY norm, lower(name), role, coalesce(sas_id, '')
              ) d
              GROUP BY norm
            )
            SELECT
              d.norm,
              d.display_name,
              COALESCE(c.class_name, 'Class pending') AS class_name,
              c.class_id,
              COALESCE(r.regattas, '[]'::json) AS regattas,
              COALESCE(s.sailors, '[]'::json) AS sailors
            FROM boat_display d
            LEFT JOIN boat_class c ON c.norm = d.norm
            LEFT JOIN boat_regs r ON r.norm = d.norm
            LEFT JOIN boat_sailors s ON s.norm = d.norm
            """
        )
        for row in cur.fetchall() or []:
            display = (row.get("display_name") or "").strip()
            norm = (row.get("norm") or "").strip()
            if not display or not norm:
                continue
            slug = boat_name_slug(display)
            if not slug:
                continue
            regs_raw = row.get("regattas") or []
            if isinstance(regs_raw, str):
                regs_raw = json.loads(regs_raw)
            sailors_raw = row.get("sailors") or []
            if isinstance(sailors_raw, str):
                sailors_raw = json.loads(sailors_raw)
            regattas = []
            for item in regs_raw or []:
                if isinstance(item, str):
                    item = json.loads(item)
                rid = (item.get("regatta_id") or "").strip()
                en = (item.get("event_name") or "").strip()
                if rid and en:
                    regattas.append({"regatta_id": rid, "event_name": en})
            regattas.sort(key=lambda x: x["event_name"].lower())
            sailors = []
            seen_s: set[tuple[str, str]] = set()
            for item in sailors_raw or []:
                if isinstance(item, str):
                    item = json.loads(item)
                nm = (item.get("name") or "").strip()
                role = (item.get("role") or "").strip() or "Sailor"
                sid = (item.get("sas_id") or "").strip() or None
                key = (nm.lower(), role)
                if not nm or key in seen_s:
                    continue
                seen_s.add(key)
                sailors.append({"name": nm, "role": role, "sas_id": sid})
            entries.append(
                {
                    "display_name": display,
                    "slug": slug,
                    "norm": norm,
                    "class_name": (row.get("class_name") or "Class pending").strip(),
                    "class_id": row.get("class_id"),
                    "regattas": regattas,
                    "sailors": sailors,
                }
            )
    finally:
        cur.close()
        return_db_connection(conn)

    entries.sort(
        key=lambda e: (
            (e.get("class_name") or "Class pending").lower(),
            (e.get("display_name") or "").lower(),
        )
    )
    return entries


def load_boat_name_index(
    *,
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> list[tuple[str, str, str]]:
    return [
        (e["display_name"], e["slug"], e["norm"])
        for e in load_boat_directory_entries(
            table_exists=table_exists,
            get_db_connection=get_db_connection,
            return_db_connection=return_db_connection,
        )
    ]


def resolve_boat_name(slug: str, index: list[tuple[str, str, str]]) -> Optional[tuple[str, str]]:
    key = (slug or "").strip().lower()
    if not key:
        return None
    for display, s, norm in index:
        if s == key:
            return display, norm
    for display, _s, norm in index:
        if boat_name_slug(display) == key:
            return display, norm
    return None


def resolve_boat_name_from_db(
    slug: str,
    *,
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> Optional[tuple[str, str]]:
    """Fallback when slug not in index — match any results boat_name whose slug equals key."""
    key = (slug or "").strip().lower()
    if not key or not table_exists("results"):
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT trim(boat_name) AS display_name
            FROM results
            WHERE boat_name IS NOT NULL AND trim(boat_name) <> ''
            GROUP BY lower(trim(boat_name)), trim(boat_name)
            """
        )
        for (display,) in cur.fetchall() or []:
            d = (display or "").strip()
            if d and boat_name_slug(d) == key:
                return d, d.lower()
    finally:
        cur.close()
        return_db_connection(conn)
    return None


def _format_rank_display(rank: Any, entries: Any) -> str:
    try:
        rnk = int(rank)
    except (TypeError, ValueError):
        return "—"
    if rnk < 1:
        return "—"
    suffix = "st" if rnk == 1 else "nd" if rnk == 2 else "rd" if rnk == 3 else "th"
    try:
        ent = int(entries)
        if ent > 0:
            return f"{rnk}{suffix}/{ent}"
    except (TypeError, ValueError):
        pass
    return f"{rnk}{suffix}"


def _short_event_date(start_date: Any, end_date: Any) -> str:
    if not start_date:
        return "—"
    try:
        if hasattr(start_date, "strftime"):
            return start_date.strftime("%d %b %Y")
        s = str(start_date)[:10]
        if len(s) >= 10:
            from datetime import datetime as _dt
            return _dt.strptime(s, "%Y-%m-%d").strftime("%d %b %Y")
        return s
    except Exception:
        return str(start_date) if start_date else "—"


SNAPSHOT_TABLE_CSS = """
.snapshot-table{width:100%;border-collapse:collapse;font-size:14px;margin-top:0.5rem;}
.snapshot-table th{background:#1e3a8a;color:#fff;padding:8px 10px;text-align:left;font-weight:700;}
.snapshot-table td{padding:8px 10px;border-bottom:1px solid #e2e8f0;}
.snapshot-table td:first-child{width:3rem;text-align:center;}
.snapshot-table td:nth-child(2){min-width:12rem;font-weight:700;text-align:left;}
.snapshot-table tr.rank-1 td{background:#D4AF37;}
.snapshot-table tr.rank-2 td{background:#D7D7D7;}
.snapshot-table tr.rank-3 td{background:#CE8946;}
.snapshot-table tr.boat-result-row{cursor:pointer;}
.snapshot-table tr.boat-result-row:hover td{filter:brightness(0.97);}
.snapshot-table a{color:#0000ee;font-weight:600;text-decoration:underline;}
"""


def _compact_links(
    items: list[str],
    max_show: int = 4,
) -> str:
    if not items:
        return "—"
    shown = items[:max_show]
    rest = len(items) - len(shown)
    text = ", ".join(html_module.escape(x) for x in shown)
    if rest > 0:
        text += f' <span class="boat-more">+{rest} more</span>'
    return text


def _regatta_links(regs: list[dict[str, str]], max_show: int = 4) -> str:
    if not regs:
        return "—"
    bits = []
    for reg in regs[:max_show]:
        rid = html_module.escape(reg.get("regatta_id") or "")
        en = html_module.escape(reg.get("event_name") or "—")
        bits.append(f'<a href="/regatta/{rid}">{en}</a>')
    rest = len(regs) - len(bits)
    out = ", ".join(bits)
    if rest > 0:
        out += f' <span class="boat-more">+{rest} more</span>'
    return out


def _sailor_link(
    name: str,
    sas_id: Optional[str],
    slug_fn: Callable[[str, str, bool], str],
    dup_names: set[str],
) -> str:
    label = html_module.escape((name or "").strip() or "—")
    sid = str(sas_id or "").strip()
    if not sid:
        return label
    base_name = (name or "").strip()
    slug = slug_fn(base_name, sid, base_name.lower() in dup_names)
    if not slug:
        return label
    return f'<a href="/sailor/{html_module.escape(slug)}">{label}</a>'


def _sailor_links_inline(
    sailors: list[dict[str, Any]],
    slug_fn: Optional[Callable[[str, str, bool], str]],
    max_show: int = 5,
) -> str:
    if not sailors:
        return "—"
    dup_names: set[str] = set()
    counts: dict[str, int] = defaultdict(int)
    for s in sailors:
        k = (s.get("name") or "").strip().lower()
        if k:
            counts[k] += 1
    dup_names = {k for k, c in counts.items() if c > 1}
    bits = []
    for s in sailors[:max_show]:
        nm = s.get("name") or ""
        if slug_fn:
            bits.append(_sailor_link(nm, s.get("sas_id"), slug_fn, dup_names))
        else:
            bits.append(html_module.escape(nm))
    rest = len(sailors) - len(bits)
    out = ", ".join(bits)
    if rest > 0:
        out += f' <span class="boat-more">+{rest} more</span>'
    return out


def _class_href(class_id: Any, class_name: str) -> str:
    """Public class URL from class name/slug only. Never put class_id in the path."""
    _ = class_id  # internal FK only — not used in public URLs
    label = (class_name or "").strip().lower().replace(" ", "-")
    label = re.sub(r"[^a-z0-9.-]", "", label).strip("-")
    if not label or label == "class-pending":
        return ""
    return f"/class/{label}"


def _class_label(class_name: str, class_id: Any) -> str:
    cn = html_module.escape(class_name or "Class pending")
    href = _class_href(class_id, class_name)
    if href:
        return f'<a href="{html_module.escape(href)}">{cn}</a>'
    return cn


def list_page_html(
    entries: list[dict[str, Any]],
    seo_block: str = "",
    slug_fn: Optional[Callable[[str, str, bool], str]] = None,
) -> str:
    about = (
        "Browse South African sailing boats by class, then name. Search by boat, class, "
        "event, or sailor. Each boat links to full regatta and crew history."
    )
    footer = (
        '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;'
        'color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">'
        'SailingSA – South African Sailing Results Database © <span id="year"></span></footer>'
        '<script>document.getElementById("year").textContent=new Date().getFullYear();</script>'
    )
    css = (
        ".dir-page{max-width:1100px;margin:0 auto;padding:40px 20px;}"
        ".dir-page h1{font-size:1.5rem;color:#001f3f;margin-bottom:0.75rem;}"
        ".boat-search-row{display:flex;flex-wrap:wrap;gap:0.75rem;align-items:center;margin:0 0 1rem 0;}"
        ".boat-search-input{flex:1;min-width:220px;padding:0.55rem 1rem;border:2px solid #001f3f;"
        "border-radius:999px;font-size:1rem;box-sizing:border-box;min-height:44px;}"
        ".boat-search-count{font-size:0.9rem;color:#555;white-space:nowrap;}"
        ".boat-class-group{margin:1.25rem 0 0.5rem;}"
        ".boat-class-group h2{font-size:1.15rem;color:#001f3f;margin:0 0 0.65rem;padding-bottom:0.35rem;"
        "border-bottom:2px solid #dbe5ef;}"
        ".boat-card{border:1px solid #dbe5ef;border-radius:10px;padding:0.85rem 1rem;margin:0 0 0.65rem;"
        "background:#fff;}"
        ".boat-card h3{margin:0 0 0.45rem;font-size:1.05rem;}"
        ".boat-card h3 a{color:#001f3f;text-decoration:underline;}"
        ".boat-card h3 a:hover{color:#e65100;}"
        ".boat-meta{margin:0.3rem 0;font-size:0.92rem;line-height:1.45;color:#1e293b;}"
        ".boat-meta strong{color:#001f3f;}"
        ".boat-meta a{color:#001f3f;font-weight:600;text-decoration:underline;}"
        ".boat-more{color:#666;font-size:0.88rem;}"
        ".page-about-block{margin:0 0 1rem 0;padding:0.85rem 1rem;border:1px solid #dbe5ef;"
        "border-radius:8px;background:#f8fbff;color:#1e293b;line-height:1.45;font-size:0.95rem;}"
        "#boat-names-empty{display:none;margin:1rem 0;color:#555;}"
        ".sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;"
        "clip:rect(0,0,0,0);white-space:nowrap;border:0;}"
    )
    head = f"""<!DOCTYPE html>
<html lang="en-US">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Boat Names | SailingSA</title>
<link rel="canonical" href="https://sailingsa.co.za/boat-names">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/css/main.css">
<style>{css}</style>
</head>
<body>
{_site_header_nav()}
<main class="main-content"><div class="container"><div class="card dir-page">
<h1>Boat Names</h1>
<div class="page-about-block">{html_module.escape(about)}</div>
<div class="boat-search-row">
<label for="boat-names-filter" class="sr-only">Search boats</label>
<input type="search" id="boat-names-filter" class="boat-search-input"
  placeholder="Search boat, class, event, or sailor…" autocomplete="off">
<span id="boat-names-count" class="boat-search-count">{len(entries)} boats</span>
</div>
"""
    if not entries:
        return head + "<p>No boat names yet.</p>" + seo_block + "</div></div></main>" + footer + "</body></html>"

    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        by_class[e.get("class_name") or "Class pending"].append(e)

    parts = [head, '<div id="boat-names-list">']
    for class_name in sorted(by_class.keys(), key=lambda x: x.lower()):
        grp_entries = sorted(by_class[class_name], key=lambda e: (e.get("display_name") or "").lower())
        parts.append(
            f'<section class="boat-class-group" data-class="{html_module.escape(class_name, quote=True)}">'
            f"<h2>{_class_label(class_name, grp_entries[0].get('class_id') if grp_entries else None)}</h2>"
        )
        for e in grp_entries:
            display = e["display_name"]
            slug = e["slug"]
            regs = e.get("regattas") or []
            sailors = e.get("sailors") or []
            search_bits = [
                display,
                class_name,
                " ".join(r.get("event_name", "") for r in regs),
                " ".join(s.get("name", "") for s in sailors),
            ]
            data_search = html_module.escape(" ".join(search_bits).lower(), quote=True)
            sailor_names = [s.get("name", "") for s in sailors]
            parts.append(
                f'<article class="boat-card" data-search="{data_search}">'
                f'<h3><a href="/boat-name/{html_module.escape(slug)}">{html_module.escape(display)}</a></h3>'
                f'<p class="boat-meta"><strong>Class:</strong> {_class_label(class_name, e.get("class_id"))}</p>'
                f'<p class="boat-meta"><strong>Events ({len(regs)}):</strong> {_regatta_links(regs)}</p>'
                f'<p class="boat-meta"><strong>Sailors ({len(sailors)}):</strong> '
                f'{_sailor_links_inline(sailors, slug_fn)}</p>'
                "</article>"
            )
        parts.append("</section>")
    parts.append("</div>")
    parts.append('<p id="boat-names-empty" role="status">No boats match your search.</p>')
    parts.append(f"<script>{BOAT_SEARCH_SCRIPT}</script>")
    parts.append(seo_block)
    parts.append("</div></div></main>" + footer + "</body></html>")
    return "".join(parts)


def detail_page_html(
    display_name: str,
    norm: str,
    result_rows: list[dict[str, Any]],
    seo_block: str,
    slug_fn: Callable[[str, str, bool], str],
    class_name: str = "",
    class_id: Any = None,
    class_logo: str = "",
) -> str:
    """Boat profile — GOLD layout (same shell as /club/LDYC)."""
    from gold_entity_layout import (
        GOLD_ENTITY_CSS,
        section_heading,
        site_footer,
        site_header_nav,
        story_chip,
        story_header,
        story_logo_row,
        table_filter_script,
    )

    title = html_module.escape(display_name)
    canonical = html_module.escape(f"https://sailingsa.co.za/boat-name/{boat_name_slug(display_name)}")
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": display_name,
        "category": class_name or "Sailing yacht",
    }

    dup_helm_names: set[str] = set()
    helm_counts: dict[str, int] = {}
    for row in result_rows:
        hn = (row.get("helm_name") or "").strip().lower()
        if hn:
            helm_counts[hn] = helm_counts.get(hn, 0) + 1
    dup_helm_names = {k for k, c in helm_counts.items() if c > 1}

    # Unique clubs as chips
    club_order: list[str] = []
    club_seen: set[str] = set()
    for row in result_rows:
        ab = (row.get("club") or "").strip().upper()
        if ab and ab not in club_seen and ab not in {"—", "-"}:
            club_seen.add(ab)
            club_order.append(ab)
    club_order.sort()
    club_chips = "".join(
        story_chip(f"/club/{ab}", f"/api/club-logo/{ab}", ab, ab) for ab in club_order
    )
    strips = ""
    class_href = _class_href(class_id, class_name)
    if class_name and class_name.lower() != "class pending":
        strips += story_logo_row(
            "Class",
            story_chip(
                class_href,
                class_logo or "",
                class_name,
                f"{class_name} class page",
            ),
        )
    if club_chips:
        strips += story_logo_row("Clubs raced under", club_chips)

    logo_url = (class_logo or "").strip()
    class_logo_for_rows = logo_url
    logo_href = ""
    logo_alt = class_name or display_name
    title_html, sponsor_header = _boat_name_title_with_sponsor_html(display_name)
    if sponsor_header:
        # Sponsor/owner logo in the main slot; class stays in the Class strip below.
        logo_url, logo_href, logo_alt = sponsor_header
    meta_bits = [f"{len(result_rows)} result{'s' if len(result_rows) != 1 else ''}"]
    if class_name and class_name.lower() != "class pending":
        meta_bits.append(class_name)
    if club_order:
        meta_bits.append(f"{len(club_order)} club{'s' if len(club_order) != 1 else ''}")
    header = story_header(
        title=display_name,
        title_html=title_html,
        logo_url=logo_url,
        logo_alt=logo_alt,
        logo_href=logo_href,
        meta_line=" · ".join(meta_bits),
        strips_html=strips,
    )

    table_rows: list[str] = []
    for i, row in enumerate(result_rows, 1):
        rid = html_module.escape(str(row.get("regatta_id") or ""))
        en = html_module.escape(str(row.get("event_name") or "—"))
        dd = html_module.escape(str(row.get("date_display") or "—"))
        sail = html_module.escape(str(row.get("sail_number") or ""))
        club_ab = (row.get("club") or "").strip().upper()
        club_html = "—"
        if club_ab:
            club_esc = html_module.escape(club_ab)
            club_html = (
                f'<img src="/api/club-logo/{club_esc}" alt="" class="row-logo" '
                f'loading="lazy" onerror="this.style.display=\'none\'">'
                f'<a href="/club/{club_esc}">{club_esc}</a>'
            )
        helm_nm = (row.get("helm_name") or "").strip()
        helm_cell = (
            _sailor_link(helm_nm, row.get("helm_sa_sailing_id"), slug_fn, dup_helm_names)
            if helm_nm
            else "—"
        )
        crew_nm = (row.get("crew_name") or "").strip()
        crew_cell = (
            _sailor_link(crew_nm, row.get("crew_sa_sailing_id"), slug_fn, dup_helm_names)
            if crew_nm
            else "—"
        )
        rank_txt = html_module.escape(_format_rank_display(row.get("rank"), row.get("entries")))
        try:
            rnk = int(row.get("rank"))
        except (TypeError, ValueError):
            rnk = 0
        rank_class = "rank-1" if rnk == 1 else "rank-2" if rnk == 2 else "rank-3" if rnk == 3 else ""
        href = f"/regatta/{rid}"
        ev_logo = ""
        if class_logo_for_rows:
            src = html_module.escape(
                class_logo_for_rows if class_logo_for_rows.startswith("/") else "/" + class_logo_for_rows
            )
            ev_logo = (
                f'<img src="{src}" alt="" class="row-logo" loading="lazy" '
                f'onerror="this.style.display=\'none\'">'
            )
        search = html_module.escape(
            f"{row.get('event_name') or ''} {club_ab} {helm_nm} {crew_nm} {row.get('date_display') or ''}".lower()
        )
        table_rows.append(
            f'<tr class="boat-result-row {rank_class}" data-search="{search}" '
            f'onclick="window.location.href=\'{href}\'" title="View regatta results">'
            f"<td>{i}</td>"
            f'<td class="cell-left">{ev_logo}<a href="{href}" onclick="event.stopPropagation()">{en}</a></td>'
            f"<td>{dd}</td>"
            f"<td>{sail}</td>"
            f'<td class="cell-left">{helm_cell}</td>'
            f'<td class="cell-left">{crew_cell}</td>'
            f'<td class="cell-left">{club_html}</td>'
            f"<td><strong>{rank_txt}</strong></td>"
            f"</tr>"
        )

    reg_empty = '<tr><td colspan="8">No regatta results found for this boat.</td></tr>'
    table_html = (
        '<div class="table-container club-table-scroll">'
        '<table class="table" id="boat-results-table">'
        "<thead><tr>"
        "<th>#</th><th>Event</th><th>Date</th><th>Sail No</th>"
        "<th>Helm</th><th>Crew</th><th>Club</th><th>Rank</th>"
        "</tr></thead>"
        f"<tbody>{''.join(table_rows) if table_rows else reg_empty}</tbody>"
        "</table></div>"
    )
    results_section = (
        section_heading(
            f"Regatta results ({len(result_rows)})",
            "boat-results-table",
            "Search results…",
        )
        + table_html
    )

    body = (
        '<a href="/boat-names" class="back-to-home">← All boat names</a>'
        f"{header}{results_section}"
    )
    return (
        "<!DOCTYPE html><html lang=\"en-US\"><head><meta charset=\"UTF-8\">"
        f"<title>{title} | SailingSA</title>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="description" content="Boat {title} — regatta results and helms in South African sailing.">'
        f'<link rel="canonical" href="{canonical}">'
        '<link rel="icon" href="/favicon.ico" sizes="any">'
        '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">'
        '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">'
        '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">'
        '<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png">'
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
        f'<script type="application/ld+json">{json.dumps(json_ld)}</script>'
        '<link rel="stylesheet" href="/css/main.css">'
        f"<style>{GOLD_ENTITY_CSS}"
        ".boat-name-sponsor-inline{display:inline-flex;align-items:center;vertical-align:middle;"
        "line-height:0;text-decoration:none;margin:0 0.15em;}"
        ".boat-name-sponsor-inline-img{display:block;height:1.15em;width:auto;max-height:42px;"
        "max-width:7rem;object-fit:contain;}"
        ".club-page-logo-link{display:inline-flex;align-items:center;line-height:0;text-decoration:none;}"
        "</style></head><body>"
        f"{site_header_nav()}"
        f'<main class="main-content"><div class="container club-page">{body}</div></main>'
        f"{seo_block}{site_footer()}{table_filter_script()}</body></html>"
    )


def load_boat_result_rows(
    norm: str,
    *,
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> list[dict[str, Any]]:
    if not norm or not table_exists("results") or not table_exists("regattas"):
        return []
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rows: list[dict[str, Any]] = []
    try:
        cur.execute(
            """
            SELECT
              res.regatta_id::text AS regatta_id,
              reg.event_name,
              reg.start_date,
              reg.end_date,
              res.sail_number,
              res.rank,
              rb.entries_raced AS entries,
              res.helm_name,
              res.helm_sa_sailing_id::text AS helm_sa_sailing_id,
              res.crew_name,
              res.crew_sa_sailing_id::text AS crew_sa_sailing_id,
              COALESCE(c.club_abbrev, c.club_fullname, res.club_raw, '') AS club
            FROM results res
            JOIN regattas reg ON reg.regatta_id = res.regatta_id
            LEFT JOIN regatta_blocks rb ON rb.block_id = res.block_id
            LEFT JOIN clubs c ON c.club_id = res.club_id
            WHERE lower(trim(res.boat_name)) = %s
            ORDER BY COALESCE(reg.start_date, reg.end_date) DESC NULLS LAST, reg.event_name
            """,
            (norm,),
        )
        for row in cur.fetchall() or []:
            rows.append(
                {
                    "regatta_id": row.get("regatta_id"),
                    "event_name": row.get("event_name"),
                    "date_display": _short_event_date(row.get("start_date"), row.get("end_date")),
                    "sail_number": row.get("sail_number"),
                    "rank": row.get("rank"),
                    "entries": row.get("entries"),
                    "helm_name": row.get("helm_name"),
                    "helm_sa_sailing_id": row.get("helm_sa_sailing_id"),
                    "crew_name": row.get("crew_name"),
                    "crew_sa_sailing_id": row.get("crew_sa_sailing_id"),
                    "club": (row.get("club") or "").strip(),
                }
            )
    finally:
        cur.close()
        return_db_connection(conn)
    return rows


def load_boat_name_detail(
    norm: str,
    *,
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    format_date_range: Callable[..., str],
) -> tuple[list[dict[str, Any]], list[tuple[str, str, Optional[str]]], str, Any, str]:
    regattas: list[dict[str, Any]] = []
    sailors: list[tuple[str, str, Optional[str]]] = []
    class_name = "Class pending"
    class_id = None
    class_logo = ""
    if not norm or not table_exists("results") or not table_exists("regattas"):
        return regattas, sailors, class_name, class_id, class_logo

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
              COALESCE(
                NULLIF(trim(res.class_canonical), ''),
                NULLIF(trim(cl.class_name), ''),
                'Class pending'
              ) AS class_name,
              res.class_id,
              NULLIF(btrim(cl.logo_path), '') AS logo_path,
              count(*)::int AS cnt
            FROM results res
            LEFT JOIN classes cl ON cl.class_id = res.class_id
            WHERE lower(trim(res.boat_name)) = %s
            GROUP BY 1, res.class_id, cl.logo_path
            ORDER BY cnt DESC
            LIMIT 1
            """,
            (norm,),
        )
        crow = cur.fetchone()
        if crow:
            class_name = (crow.get("class_name") or "Class pending").strip()
            class_id = crow.get("class_id")
            class_logo = (crow.get("logo_path") or "").strip()

        cur.execute(
            """
            SELECT
                res.regatta_id::text AS regatta_id,
                reg.event_name,
                reg.start_date,
                reg.end_date,
                array_agg(DISTINCT NULLIF(trim(res.helm_name), '')) FILTER (WHERE trim(coalesce(res.helm_name, '')) <> '') AS helms,
                array_agg(DISTINCT NULLIF(trim(res.crew_name), '')) FILTER (WHERE trim(coalesce(res.crew_name, '')) <> '') AS crews
            FROM results res
            JOIN regattas reg ON reg.regatta_id = res.regatta_id
            WHERE lower(trim(res.boat_name)) = %s
            GROUP BY res.regatta_id, reg.event_name, reg.start_date, reg.end_date
            ORDER BY COALESCE(reg.start_date, reg.end_date) DESC NULLS LAST, reg.event_name
            """,
            (norm,),
        )
        for row in cur.fetchall() or []:
            regattas.append(
                {
                    "regatta_id": row.get("regatta_id"),
                    "event_name": row.get("event_name"),
                    "date_display": format_date_range(
                        row.get("start_date"),
                        row.get("end_date"),
                    ),
                    "helms": [x for x in (row.get("helms") or []) if x],
                    "crews": [x for x in (row.get("crews") or []) if x],
                }
            )

        cur.execute(
            """
            SELECT DISTINCT trim(helm_name) AS name, helm_sa_sailing_id::text AS sas_id, 'Helm' AS role
            FROM results
            WHERE lower(trim(boat_name)) = %s AND trim(coalesce(helm_name, '')) <> ''
            UNION
            SELECT DISTINCT trim(crew_name), crew_sa_sailing_id::text, 'Crew'
            FROM results
            WHERE lower(trim(boat_name)) = %s AND trim(coalesce(crew_name, '')) <> ''
            UNION
            SELECT DISTINCT trim(crew2_name), crew2_sa_sailing_id::text, 'Crew'
            FROM results
            WHERE lower(trim(boat_name)) = %s AND trim(coalesce(crew2_name, '')) <> ''
            UNION
            SELECT DISTINCT trim(crew3_name), crew3_sa_sailing_id::text, 'Crew'
            FROM results
            WHERE lower(trim(boat_name)) = %s AND trim(coalesce(crew3_name, '')) <> ''
            ORDER BY role, name
            """,
            (norm, norm, norm, norm),
        )
        seen: set[tuple[str, str, str]] = set()
        for row in cur.fetchall() or []:
            nm = (row.get("name") or "").strip()
            role = (row.get("role") or "").strip()
            sid = (row.get("sas_id") or "").strip() or None
            key = (nm.lower(), role, sid or "")
            if not nm or key in seen:
                continue
            seen.add(key)
            sailors.append((nm, sid or "", role))
    finally:
        cur.close()
        return_db_connection(conn)
    return regattas, sailors, class_name, class_id, class_logo


BOAT_404_HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Boat not found | SailingSA</title><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png"><link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><style>body{font-family:system-ui,sans-serif;margin:2rem;color:#1a2750;} a{color:#1a2750;}</style></head><body><h1>Boat not found</h1><p>There is no boat name at this address.</p><p><a href="/boat-names">Browse all boat names</a> · <a href="/">Home</a></p></body></html>"""
