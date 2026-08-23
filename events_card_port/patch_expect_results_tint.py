#!/usr/bin/env python3
"""Upcoming racing events: light Upcoming-green wash (host + multi-day clues)."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")
changed = []

HELPER = '''
def _event_span_days(start_date, end_date) -> int:
    """Calendar days covered (1 = same-day)."""
    def _as_date(d):
        if not d:
            return None
        if hasattr(d, "toordinal"):
            return d
        if hasattr(d, "date") and callable(getattr(d, "date", None)):
            try:
                return d.date()
            except Exception:
                pass
        s = str(d)[:10]
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    s = _as_date(start_date)
    if not s:
        return 1
    e = _as_date(end_date) or s
    try:
        return max(1, (e - s).days + 1)
    except Exception:
        return 1


def _event_has_real_host(host_code: str | None, host_club: str | None = None, club_slug: str | None = None) -> bool:
    """True when card has usable host info (club code/name/slug), not blank/TBC/Unassigned."""
    for raw in (host_code, host_club, club_slug):
        s = (raw or "").strip()
        if not s:
            continue
        if s in ("—", "-", "–"):
            continue
        if s.lower() in ("tbc", "unk", "unknown", "unassigned", "teams", "online", "n/a", "na"):
            continue
        return True
    return False


def _event_expect_racing_results(
    category: str | None,
    event_name: str | None = None,
    *,
    host_code: str | None = None,
    host_club: str | None = None,
    club_slug: str | None = None,
    start_date=None,
    end_date=None,
) -> bool:
    """True for real regattas sailors enter (results expected).

    Clues: exclude AGM/course/training; most real events have host info;
    many span 2–3+ calendar days.
    """
    if _event_category_shows_times(category, event_name):
        return False
    cat = (category or "").strip().lower()
    if cat in ("meeting", "meetings", "training"):
        return False
    name = f" {(event_name or '').strip().lower()} "
    for token in (
        " agm",
        "agm ",
        " instructor ",
        " race officer ",
        " safeguarding ",
        " appointment ",
        " cruise ",
    ):
        if token in name:
            return False
    has_host = _event_has_real_host(host_code, host_club, club_slug)
    multi_day = _event_span_days(start_date, end_date) >= 2
    if has_host:
        return True
    if multi_day:
        return True
    for token in (
        " championship",
        " nationals",
        " regional",
        " provincials",
        " regatta",
        " open ",
        " classic",
        " series",
        " cup ",
        " trophy",
    ):
        if token in name:
            return True
    return False

'''

# Replace old simple helper if present
old_simple = '''def _event_expect_racing_results(category: str | None, event_name: str | None = None) -> bool:
    """True for real regattas sailors enter (results expected). False for AGM/course/training/etc."""
    if _event_category_shows_times(category, event_name):
        return False
    cat = (category or "").strip().lower()
    if cat in ("meeting", "meetings", "training"):
        return False
    name = f" {(event_name or '').strip().lower()} "
    for token in (
        " agm",
        "agm ",
        " instructor ",
        " race officer ",
        " safeguarding ",
        " appointment ",
        " cruise ",
    ):
        if token in name:
            return False
    return True
'''

if "def _event_has_real_host" in t and "multi_day = _event_span_days" in t:
    changed.append("helper_already_host_multiday")
elif old_simple in t:
    t = t.replace(old_simple, HELPER.strip() + "\n", 1)
    changed.append("helper_upgraded")
elif "def _event_expect_racing_results" not in t:
    anchor = "def _format_event_date_range(start_date, end_date, start_time=None, end_time=None):"
    if anchor not in t:
        # try after _event_category_shows_times
        marker = "def _event_category_shows_times"
        if marker not in t:
            raise SystemExit("cannot find insert point for expect helper")
        # insert before _format_event_date_range if present
        if "def _format_event_date_range" in t:
            t = t.replace(
                "def _format_event_date_range(start_date, end_date, start_time=None, end_time=None):",
                HELPER + "\ndef _format_event_date_range(start_date, end_date, start_time=None, end_time=None):",
                1,
            )
            changed.append("helper_inserted")
        else:
            raise SystemExit("format_event_date_range missing")
    else:
        t = t.replace(anchor, HELPER + "\n" + anchor, 1)
        changed.append("helper_inserted")
else:
    # Has expect helper but not host/multiday — replace whole function body by re-inserting after shows_times
    changed.append("helper_exists_manual_check")

# Card JSON — upgrade call site
old_json_simple = '"expect_results": _event_expect_racing_results(event_type, event_name),'
new_json = '''"expect_results": _event_expect_racing_results(
            event_type,
            event_name,
            host_code=host_code,
            host_club=host_club,
            club_slug=club_slug,
            start_date=start,
            end_date=end,
        ),'''

if "host_code=host_code" in t and "expect_results" in t:
    changed.append("json_already_rich")
elif old_json_simple in t:
    t = t.replace(old_json_simple, new_json, 1)
    changed.append("json_upgraded")
elif '"result_yes": result_yes,\n        "host_unmatched"' in t:
    t = t.replace(
        '"result_yes": result_yes,\n        "host_unmatched"',
        '"result_yes": result_yes,\n        ' + new_json + '\n        "host_unmatched"',
        1,
    )
    changed.append("json_added")
else:
    # try with host_unmatched already after expect
    if '"expect_results"' not in t:
        raise SystemExit("card json anchor missing")
    changed.append("json_partial")

# CSS
old_css = """.sa-home-regatta-card--has-results{background:#f6ecec;border-color:#e0c4c4;}
.sa-home-regatta-card--has-results .sa-home-regatta-btn{border-color:#c9a0a0;background:#faf4f4;color:#7f1d1d;}"""
new_css = """.sa-home-regatta-card--has-results{background:#f6ecec;border-color:#e0c4c4;}
.sa-home-regatta-card--has-results .sa-home-regatta-btn{border-color:#c9a0a0;background:#faf4f4;color:#7f1d1d;}
.sa-home-regatta-card--expect-results{background:#eaf8ef;border-color:#b8e6c8;}
.sa-home-regatta-card--expect-results .sa-home-regatta-btn{border-color:#7dcf9a;background:#f3fcf6;color:#166534;}"""

if "sa-home-regatta-card--expect-results" in t:
    changed.append("css_already")
elif old_css in t:
    t = t.replace(old_css, new_css, 1)
    changed.append("css")
else:
    changed.append("css_skip")

# JS
old_js = "    var cardCls = 'sa-home-regatta-card' + (hasRes ? ' sa-home-regatta-card--has-results' : '');"
new_js = """    var expect = !!e.expect_results && !hasRes && (panelId === 'upcoming' || panelId === 'live');
    var cardCls = 'sa-home-regatta-card' + (hasRes ? ' sa-home-regatta-card--has-results' : (expect ? ' sa-home-regatta-card--expect-results' : ''));"""
n_js = t.count(old_js)
if n_js:
    t = t.replace(old_js, new_js)
    changed.append(f"js_x{n_js}")
elif "expect ? ' sa-home-regatta-card--expect-results'" in t:
    changed.append("js_already")
else:
    changed.append("js_skip")

# SSR
old_ssr = '    card_cls = "sa-home-regatta-card" + (" sa-home-regatta-card--has-results" if result_yes else "")'
new_ssr = '''    expect = bool(e.get("expect_results")) and not result_yes and panel_id in ("upcoming", "live")
    card_cls = "sa-home-regatta-card"
    if result_yes:
        card_cls += " sa-home-regatta-card--has-results"
    elif expect:
        card_cls += " sa-home-regatta-card--expect-results"'''
n_ssr = t.count(old_ssr)
if n_ssr:
    t = t.replace(old_ssr, new_ssr)
    changed.append(f"ssr_x{n_ssr}")
elif "elif expect:" in t and "expect-results" in t:
    changed.append("ssr_already")
else:
    changed.append("ssr_skip")

path.write_text(t, encoding="utf-8")
print(path, "changed:", ",".join(changed))
