"""Public /quals page: one sortable table per accreditation.

SAS publishes an expiry (Accredited until / Expired). It does not publish the
first issue date or a renewal count. Term from is the current 4-year window
already stored on member_roles.awarded_date (expiry minus 4 years).
"""
from __future__ import annotations

import html as html_module
import re
from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

# Instructor tickets first; every other role still gets its own table.
_INSTRUCTOR_ORDER = ("ASSIST_INSTR", "INSTR_DINGHY", "INSTR_KEEL", "SENIOR_INSTR")

_PAGE_CSS = """
.quals-page { padding-top: 0.35rem; padding-bottom: 0.75rem; font-size: 14px; line-height: 1.3; }
.quals-page .card { background:#fff; border:2px solid #001f3f; border-radius:8px; box-shadow:0 1px 3px rgba(0,31,63,0.08); padding:0.4rem 0.5rem; margin-bottom:0.5rem; }
.quals-page .section-title { font-size:0.8rem; font-weight:700; text-transform:uppercase; letter-spacing:0.02em; color:#001f3f; border-bottom:2px solid #001f3f; margin:0 0 0.35rem 0; padding-bottom:0.2rem; line-height:1.2; }
.quals-page .quals-note { font-size:13px; line-height:1.35; color:#334155; margin:0; }
.quals-page .table-container { overflow-x:auto; -webkit-overflow-scrolling:touch; }
.quals-page .stats-table { width:100%; border-collapse:collapse; font-size:14px; line-height:1.25; }
.quals-page .stats-table th, .quals-page .stats-table td { padding:0.28rem 0.35rem; text-align:left; border-bottom:1px solid #e0e0e0; white-space:nowrap; }
.quals-page .stats-table th { height:44px; background:#f1f5f9; font-weight:600; color:#001f3f; border-bottom:2px solid #001f3f; }
.quals-page .stats-table th:first-child, .quals-page .stats-table td:first-child { position:sticky; left:0; z-index:1; }
.quals-page .stats-table td:first-child { background:#fff; }
.quals-page .stats-table th:first-child { z-index:2; }
.quals-page .stats-table a { color:#001f3f; font-weight:600; text-decoration:underline; }
.quals-page .stats-table th[data-sort] { cursor:pointer; user-select:none; }
.quals-page .stats-table th[data-sort]:hover { text-decoration:underline; }
.site-footer-about { text-align:center; padding:0.75rem 0.5rem; font-size:13px; color:#666; border-top:1px solid #e0e0e0; margin-top:0.75rem; }
@media (min-width: 769px) {
  .quals-page { padding-top: 0.75rem; padding-bottom: 1.5rem; }
  .quals-page .card { padding:0.5rem 0.75rem; margin-bottom:16px; }
  .quals-page .stats-table th, .quals-page .stats-table td { padding:0.35rem 0.5rem; }
}
"""

_HEADER = """<!DOCTYPE html>
<html lang="en-US">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Qualifications</title>
<meta name="description" content="SA Sailing instructor and official qualifications, expiry and time left.">
<link rel="canonical" href="https://sailingsa.co.za/quals">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">
<link rel="stylesheet" href="/css/main.css?v=13">
<style>""" + _PAGE_CSS + """</style>
</head>
<body>
<header class="site-header">
<div class="container">
<a href="/" class="logo js-go-home" id="headerLogoLink" title="Home"><img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>
<div class="header-auth" id="headerAuth"></div>
<button class="menu-btn" id="menuBtn" type="button" aria-label="Open menu"><span class="menu-icon"></span></button>
</div>
<nav id="navMenuOverlay" class="nav-menu-overlay" aria-hidden="true" style="display:none;">
<a href="/">Sailor</a>
<a href="/" data-mode="regatta">Regatta</a>
<a href="/about">About</a>
</nav>
</header>
<main class="main-content"><div class="container quals-page">
"""

_FOOTER_SCRIPT = """
<script>
document.getElementById("year").textContent = new Date().getFullYear();
(function(){
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest && e.target.closest("a.js-go-home");
    if (!a) return;
    try { sessionStorage.setItem("sailingsa_home_from_logo", "1"); } catch (err) {}
  }, true);
  var logo = document.getElementById("headerLogoLink");
  if (logo) logo.setAttribute("href", "/");
  var menuBtn = document.getElementById("menuBtn");
  var overlay = document.getElementById("navMenuOverlay");
  if (menuBtn && overlay) {
    menuBtn.addEventListener("click", function() {
      var hidden = overlay.style.display === "none";
      overlay.style.display = hidden ? "flex" : "none";
      overlay.setAttribute("aria-hidden", hidden ? "false" : "true");
      menuBtn.setAttribute("aria-label", hidden ? "Close menu" : "Open menu");
    });
    overlay.addEventListener("click", function(e) {
      if (e.target.tagName === "A") overlay.style.display = "none";
    });
  }
  var regattaLink = overlay && overlay.querySelector('a[data-mode="regatta"]');
  if (regattaLink) {
    regattaLink.addEventListener("click", function(e) {
      e.preventDefault();
      window.location.href = "/?mode=regatta";
    });
  }
})();
(function(){
  function numOrStr(a){ var v = a; if (typeof v === "string" && /^-?\\d+$/.test(v)) return parseInt(v,10); return v; }
  function cmp(a,b,dir){ var aa = numOrStr(a), bb = numOrStr(b); if (aa < bb) return dir===1 ? -1 : 1; if (aa > bb) return dir===1 ? 1 : -1; return 0; }
  function parseISO(s){ var p = String(s).split("-"); return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2])); }
  function ymd(from, to){
    var sign = 1, a = from, b = to;
    if (b < a) { sign = -1; a = to; b = from; }
    var years = b.getFullYear() - a.getFullYear();
    var months = b.getMonth() - a.getMonth();
    var days = b.getDate() - a.getDate();
    if (days < 0) {
      months -= 1;
      var prev = new Date(b.getFullYear(), b.getMonth(), 0);
      days += prev.getDate();
    }
    if (months < 0) { years -= 1; months += 12; }
    return [sign * years, sign * months, sign * days];
  }
  function fmtLeft(parts){
    var neg = parts[0] < 0 || parts[1] < 0 || parts[2] < 0;
    var y = Math.abs(parts[0]), m = Math.abs(parts[1]), d = Math.abs(parts[2]);
    var s = "";
    if (y) s += y + "y";
    if (m) s += m + "m";
    if (d || !s) s += d + "d";
    return neg ? "-" + s : s;
  }
  function paint(){
    var today = new Date(); today.setHours(0,0,0,0);
    document.querySelectorAll('tr[data-expires]:not([data-expires=""])').forEach(function(tr){
      var exp = parseISO(tr.getAttribute("data-expires"));
      var parts = ymd(today, exp);
      var days = Math.round((exp.getTime() - today.getTime()) / 86400000);
      tr.setAttribute("data-left", String(days));
      var cell = tr.querySelector('[data-col="left"]');
      if (cell) cell.textContent = fmtLeft(parts);
      var status = days < 0 ? "Expired" : "Current";
      var rank = status === "Current" ? "2" : "0";
      tr.setAttribute("data-status", rank);
      var sc = tr.querySelector('[data-col="status"]');
      if (sc) sc.textContent = status;
    });
  }
  paint();
  setInterval(paint, 60000);
  document.querySelectorAll(".stats-table").forEach(function(tbl){
    var thead = tbl.querySelector("thead");
    if (!thead) return;
    thead.querySelectorAll("th[data-sort]").forEach(function(th){
      if (!th.getAttribute("data-label")) th.setAttribute("data-label", th.textContent);
    });
    var defaultSort = tbl.getAttribute("data-default-sort");
    var currentSort = defaultSort;
    var currentDir = (tbl.getAttribute("data-default-dir") || "desc").toLowerCase() === "asc" ? 1 : -1;
    function mark(){
      thead.querySelectorAll("th[data-sort]").forEach(function(h){
        var base = h.getAttribute("data-label");
        var on = h.getAttribute("data-sort") === currentSort;
        h.textContent = base + (on ? (currentDir === 1 ? " ↑" : " ↓") : "");
      });
    }
    thead.querySelectorAll("th[data-sort]").forEach(function(th){
      th.addEventListener("click", function(){
        var key = th.getAttribute("data-sort");
        if (currentSort === key) currentDir = -currentDir; else { currentSort = key; currentDir = -1; }
        var rows = [].slice.call(tbl.querySelectorAll("tbody tr"));
        rows.sort(function(ra, rb){
          var a = ra.getAttribute("data-" + key) || "";
          var b = rb.getAttribute("data-" + key) || "";
          return cmp(a, b, currentDir);
        });
        var tbody = tbl.querySelector("tbody");
        if (tbody) rows.forEach(function(r){ tbody.appendChild(r); });
        mark();
      });
    });
  });
})();
</script></body></html>"""


def johannesburg_today() -> date:
    return datetime.now(ZoneInfo("Africa/Johannesburg")).date()


def calendar_ymd(start: date, end: date) -> tuple[int, int, int]:
    """Signed calendar years, months and days from start to end."""
    sign = 1
    a, b = start, end
    if b < a:
        sign = -1
        a, b = b, a
    years = b.year - a.year
    months = b.month - a.month
    days = b.day - a.day
    if days < 0:
        months -= 1
        from datetime import timedelta
        prev_last = date(b.year, b.month, 1) - timedelta(days=1)
        days += prev_last.day
    if months < 0:
        years -= 1
        months += 12
    return sign * years, sign * months, sign * days


def _slug_from_name(full_name: str) -> str:
    if not full_name:
        return ""
    s = full_name.strip().lower().replace("&", " and ")
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _fmt_date(value) -> str:
    if not value:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%-d %b %Y")
    return str(value)[:10]


def _iso(value) -> str:
    if not value:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def _esc(value) -> str:
    return html_module.escape("" if value is None else str(value), quote=True)


def _status(expires, today: date) -> str:
    if not expires:
        return "No date"
    exp = expires if isinstance(expires, date) else date.fromisoformat(str(expires)[:10])
    if exp >= today:
        return "Current"
    return "Expired"


def _status_rank(status: str) -> str:
    return {"Current": "2", "No date": "1", "Expired": "0"}.get(status, "1")


def format_left(years: int, months: int, days: int) -> str:
    """Compact signed span, for example 2y4m7d. Zero units are left out."""
    negative = years < 0 or months < 0 or days < 0
    parts: list[str] = []
    if abs(years):
        parts.append(f"{abs(years)}y")
    if abs(months):
        parts.append(f"{abs(months)}m")
    if abs(days) or not parts:
        parts.append(f"{abs(days)}d")
    text = "".join(parts)
    return f"-{text}" if negative else text


def render_quals_html(rows: list, today: date | None = None, error: str | None = None) -> str:
    today = today or johannesburg_today()
    if error:
        body = (
            '<div class="card"><h2 class="section-title">Qualifications</h2>'
            '<p class="quals-note">The qualification list could not be loaded.</p></div>'
        )
        return _wrap(body)
    grouped = _group_rows(rows or [])
    parts = [
        '<div class="card"><h2 class="section-title">Qualifications</h2>'
        '<p class="quals-note">Time left is counted from today, for example 2y4m7d, and updates while this page is open. '
        'From is the start of this 4-year window. Click a column to sort.</p></div>'
    ]
    parts.append(_summary_table(grouped, today))
    for role_code, label, people in grouped:
        parts.append(_role_table(role_code, label, people, today))
    return _wrap("".join(parts))


def _wrap(body: str) -> str:
    footer = (
        '</div></main><footer class="site-footer-about">'
        'SailingSA – South African Sailing Results Database © <span id="year"></span></footer>'
    )
    return _HEADER + body + footer + _FOOTER_SCRIPT


def _group_rows(rows: list) -> list:
    buckets: dict[str, dict] = {}
    for row in rows:
        code = (row.get("role_code") or "").strip()
        if not code:
            continue
        bucket = buckets.setdefault(code, {"label": row.get("role_label") or code, "people": []})
        if row.get("role_label"):
            bucket["label"] = row["role_label"]
        bucket["people"].append(row)
    ordered = []
    seen = set()
    for code in _INSTRUCTOR_ORDER:
        if code in buckets:
            ordered.append((code, buckets[code]["label"], buckets[code]["people"]))
            seen.add(code)
    rest = [c for c in buckets if c not in seen]
    rest.sort(key=lambda c: (buckets[c]["label"] or c).lower())
    for code in rest:
        ordered.append((code, buckets[code]["label"], buckets[code]["people"]))
    return ordered


def _name_counts(people: list) -> dict:
    counts: dict[str, int] = {}
    for row in people:
        name = (row.get("full_name") or "").strip().lower()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


def _summary_table(grouped, today: date) -> str:
    head = (
        '<div class="card"><h2 class="section-title">Who is current</h2>'
        '<div class="table-container"><table class="table stats-table" data-default-sort="current" data-default-dir="desc">'
        '<thead><tr>'
        '<th data-sort="qual">Qualification</th>'
        '<th data-sort="people">People</th>'
        '<th data-sort="current">Current</th>'
        '<th data-sort="expired">Expired</th>'
        '<th data-sort="nodate">No date</th>'
        '</tr></thead><tbody>'
    )
    body = []
    for code, label, people in grouped:
        current = expired = nodate = 0
        for row in people:
            status = _status(row.get("expires_date"), today)
            if status == "Current":
                current += 1
            elif status == "Expired":
                expired += 1
            else:
                nodate += 1
        anchor = "qual-" + re.sub(r"[^A-Za-z0-9_-]", "", code)
        body.append(
            f'<tr data-qual="{_esc(label)}" data-people="{len(people)}" data-current="{current}" '
            f'data-expired="{expired}" data-nodate="{nodate}">'
            f'<td><a href="#{anchor}">{_esc(label)}</a></td>'
            f'<td>{len(people)}</td><td>{current}</td><td>{expired}</td><td>{nodate}</td></tr>'
        )
    if not body:
        body.append('<tr data-qual="" data-people="0" data-current="0" data-expired="0" data-nodate="0"><td colspan="5">No qualifications recorded.</td></tr>')
    return head + "".join(body) + "</tbody></table></div></div>"


def _role_table(code: str, label: str, people: list, today: date) -> str:
    anchor = "qual-" + re.sub(r"[^A-Za-z0-9_-]", "", code)
    names = _name_counts(people)
    # Current first, then soonest expiry, then name.
    def sort_key(row):
        status = _status(row.get("expires_date"), today)
        rank = {"Current": 0, "No date": 1, "Expired": 2}[status]
        exp = row.get("expires_date") or date.max
        if not isinstance(exp, date):
            try:
                exp = date.fromisoformat(str(exp)[:10])
            except ValueError:
                exp = date.max
        # Current: soonest expiry first. Expired: most recently expired first.
        exp_ord = exp.toordinal() if status == "Current" else -exp.toordinal()
        return (rank, exp_ord, (row.get("full_name") or "").lower())

    ordered = sorted(people, key=sort_key)
    current = sum(1 for row in people if _status(row.get("expires_date"), today) == "Current")
    title = f"{label} ({len(people)}, {current} current)"
    head = (
        f'<div class="card" id="{anchor}"><h2 class="section-title">{_esc(title)}</h2>'
        '<div class="table-container"><table class="table stats-table" data-default-sort="status" data-default-dir="desc">'
        "<thead><tr>"
        '<th data-sort="name">Name</th>'
        '<th data-sort="left">Left</th>'
        '<th data-sort="status">Status</th>'
        '<th data-sort="expires">Expires</th>'
        '<th data-sort="sas_id">SAS</th>'
        '<th data-sort="club">Club</th>'
        '<th data-sort="term_from">From</th>'
        "</tr></thead><tbody>"
    )
    body = []
    for row in ordered:
        body.append(_person_row(row, names, today))
    if not body:
        body.append('<tr><td colspan="7">No one on this qualification.</td></tr>')
    return head + "".join(body) + "</tbody></table></div></div>"


def _person_row(row: dict, names: dict, today: date) -> str:
    sas_id = str(row.get("sas_id") or "").strip()
    full_name = (row.get("full_name") or "").strip()
    club = (row.get("club") or "").strip()
    awarded = row.get("awarded_date")
    expires = row.get("expires_date")
    if expires and not isinstance(expires, date):
        expires = date.fromisoformat(str(expires)[:10])
    if awarded and not isinstance(awarded, date):
        awarded = date.fromisoformat(str(awarded)[:10])
    status = _status(expires, today)
    if expires:
        years, months, days = calendar_ymd(today, expires)
        left_txt = format_left(years, months, days)
        left_sort = str((expires - today).days)
    else:
        left_txt = "—"
        left_sort = ""
    slug = _slug_from_name(full_name)
    if slug and names.get(full_name.lower(), 0) > 1 and sas_id:
        slug = f"{slug}-{sas_id}"
    if full_name and slug:
        name_html = f'<a href="/sailor/{quote(slug, safe="")}">{_esc(full_name)}</a>'
    else:
        name_html = _esc(full_name or sas_id or "—")
    return (
        f'<tr data-name="{_esc(full_name.lower())}" data-sas_id="{_esc(sas_id)}" '
        f'data-club="{_esc(club.lower())}" '
        f'data-term_from="{_esc(_iso(awarded))}" data-expires="{_esc(_iso(expires))}" '
        f'data-status="{_status_rank(status)}" data-left="{left_sort}">'
        f"<td>{name_html}</td>"
        f'<td data-col="left">{_esc(left_txt)}</td>'
        f'<td data-col="status">{_esc(status)}</td>'
        f"<td>{_esc(_fmt_date(expires))}</td>"
        f"<td>{_esc(sas_id or '—')}</td>"
        f"<td>{_esc(club or '—')}</td>"
        f"<td>{_esc(_fmt_date(awarded))}</td>"
        "</tr>"
    )


def fetch_qual_rows(conn) -> list:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT r.role_code,
                   r.role_label,
                   replace(mr.person_key, 'SAS:', '') AS sas_id,
                   COALESCE(NULLIF(TRIM(s.full_name), ''),
                            TRIM(COALESCE(s.first_name, '') || ' ' || COALESCE(s.last_name, ''))) AS full_name,
                   COALESCE(NULLIF(TRIM(s.primary_club), ''), NULLIF(TRIM(s.club_1), ''), '') AS club,
                   mr.awarded_date,
                   mr.expires_date
            FROM member_roles mr
            JOIN roles r ON r.role_code = mr.role_code
            LEFT JOIN sas_id_personal s
              ON s.sa_sailing_id::text = replace(mr.person_key, 'SAS:', '')
            ORDER BY r.role_label, full_name
            """
        )
        return list(cur.fetchall() or [])
    finally:
        cur.close()


def render_quals_page(conn, error: str | None = None) -> str:
    if error or conn is None:
        return render_quals_html([], error=error or "unavailable")
    rows = fetch_qual_rows(conn)
    return render_quals_html(rows)
