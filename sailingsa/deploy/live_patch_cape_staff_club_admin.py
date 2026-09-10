#!/usr/bin/env python3
"""Cape Classic: Club Admin sees Staff list. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_toggle = """def _session_can_toggle_event_crew(request: Request) -> bool:
    return _session_role_is_super_admin(request) or _session_role_is_admin(request)
"""
new_toggle = """def _session_can_toggle_event_crew(request: Request) -> bool:
    if _session_role_is_super_admin(request) or _session_role_is_admin(request):
        return True
    return _session_can_edit_regatta_scores(request, "2026-09-13-zvyc-cape-classic")
"""
if "return _session_can_edit_regatta_scores(request, \"2026-09-13-zvyc-cape-classic\")" in src[
    src.find("def _session_can_toggle_event_crew") : src.find("def _session_can_toggle_event_crew") + 400
]:
    print("TOGGLE_ALREADY")
elif old_toggle not in src:
    raise SystemExit("ANCHOR_TOGGLE_MISSING")
else:
    src = src.replace(old_toggle, new_toggle, 1)
    print("TOGGLE_PATCHED")

repls = [
    (
        '    sailed = html_module.escape(note) if note else "Event crew"',
        '    sailed = html_module.escape(note) if note else "Event staff"',
    ),
    (
        'id="capeClassicCrew" aria-label="Crew">',
        'id="capeClassicCrew" aria-label="Staff">',
    ),
    (
        'f\'<a href="{html_module.escape(_CAPE_CLASSIC_CREW_HREF)}">Crew</a>\'',
        'f\'<a href="{html_module.escape(_CAPE_CLASSIC_CREW_HREF)}">Staff</a>\'',
    ),
    (
        """            if link_title
            else "Crew"
        )""",
        """            if link_title
            else "Staff"
        )""",
    ),
    (
        'f"Crew – {escaped_title} | SailingSA</title>"',
        'f"Staff – {escaped_title} | SailingSA</title>"',
    ),
    (
        """        if str(regatta_id) == "2026-09-13-zvyc-cape-classic":
            can_crew = _session_can_toggle_event_crew(request)
            crew_frag = _cape_classic_crew_table_html(
                is_editor=can_crew,
                always_show_button=_session_role_is_admin(request),
            )""",
        """        if str(regatta_id).startswith("2026-09-13-zvyc-cape-classic"):
            can_crew = _session_can_toggle_event_crew(request)
            crew_frag = _cape_classic_crew_table_html(
                is_editor=can_crew,
                always_show_button=can_crew,
                link_title=str(regatta_id) == "2026-09-13-zvyc-cape-classic",
            )""",
    ),
    (
        """        if str(regatta_id) == _CAPE_CLASSIC_MM_REGATTA_ID:
            can_crew = _session_can_toggle_event_crew(request)
            crew_frag = _cape_classic_crew_table_html(
                is_editor=can_crew,
                always_show_button=_session_role_is_admin(request),
            )""",
        """        if _cape_classic_event_id(regatta_id):
            can_crew = _session_can_toggle_event_crew(request)
            crew_frag = _cape_classic_crew_table_html(
                is_editor=can_crew,
                always_show_button=can_crew,
                link_title=str(regatta_id) == _CAPE_CLASSIC_MM_REGATTA_ID,
            )""",
    ),
    (
        """        always_show_button=_session_role_is_admin(request),
        link_title=False,""",
        """        always_show_button=can_crew,
        link_title=False,""",
    ),
]

for old, new in repls:
    if new in src and old not in src:
        print("SKIP_ALREADY", old[:40].replace("\n", " "))
        continue
    if old not in src:
        print("SKIP_ABSENT", old[:40].replace("\n", " "))
        continue
    src = src.replace(old, new, 1)
    print("OK", old[:40].replace("\n", " "))

if 'aria-label="Staff"' not in src:
    raise SystemExit("STAFF_LABEL_MISSING")
if "always_show_button=can_crew" not in src:
    raise SystemExit("ALWAYS_SHOW_MISSING")
if not (
    'str(regatta_id).startswith("2026-09-13-zvyc-cape-classic")' in src
    or "if _cape_classic_event_id(regatta_id):" in src
):
    raise SystemExit("FLEET_PAGES_MISSING")

old_js = "club-score-edit.js?v=ccr11"
new_js = "club-score-edit.js?v=ccr12"
if new_js in src:
    print("JS_ALREADY_CCR12")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR12")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("staff", 'aria-label="Staff"' in src)
print(
    "fleet_pages",
    "if _cape_classic_event_id(regatta_id):" in src
    or 'str(regatta_id).startswith("2026-09-13-zvyc-cape-classic")' in src,
)
print("club_see", "_session_can_edit_regatta_scores(request, \"2026-09-13-zvyc-cape-classic\")" in src)
print("ccr12", new_js in src)
