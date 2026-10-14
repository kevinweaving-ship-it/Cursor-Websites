"""Phase A club-page wizard source checks. Does not import the full api app."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api.py"
JS = ROOT / "js" / "club-page-wizard.js"

ROUTES = (
    '@app.get("/api/club/me")',
    '@app.get("/api/club/me/events")',
    '@app.get("/api/club/events/match")',
    '@app.post("/api/club/season-items")',
    '@app.post("/api/club/events")',
    '@app.post("/api/club/events/{event_id}/claim")',
    '@app.get("/club-manage"',
)
PILOTS = (
    "2026-09-13-zvyc-cape-classic",
    "2026-09-24-hmyc-dart-18-nationals",
    "2026-10-10-hmyc-dam-bottle-sprints",
)


def test_api_parses_and_routes():
    src = API.read_text(encoding="utf-8")
    ast.parse(src)
    for route in ROUTES:
        assert route in src, route
    for slug in PILOTS:
        assert slug in src
    assert "can_manage_all_clubs" in src
    assert "_resolve_managed_club_id" in src
    assert "create_regatta" in src
    assert "assign_host" in src
    assert "club_season_items" in src
    assert "club-page-wizard.js" in src
    claim_i = src.find('@app.post("/api/club/events/{event_id}/claim")')
    window = src[claim_i : claim_i + 2800]
    assert "21172" not in window
    assert "create_regatta" in window
    assert "_phase2_bool(create_regatta, False)" in window
    create_i = src.find("def api_club_create_event")
    create_win = src[create_i : create_i + 2200]
    assert "_phase2_bool(body.get(\"create_regatta\"), False)" in create_win
    season_i = src.find("def api_club_season_item")
    assert "Never inserts regattas" in src[season_i : season_i + 400]
    host_i = src.find("def _phase2_host_is_claimable")
    host_win = src[host_i : host_i + 900]
    assert "return bool(is_super)" not in host_win


def test_wizard_js_and_public_slots():
    js = JS.read_text(encoding="utf-8")
    assert "Claim SAS Event" in js
    assert "Activate Club Event" in js
    assert "Add New Event" in js
    assert "can_manage_all_clubs" in js
    assert "create_regatta: true" in js
    assert "create_regatta: false" in js
    assert "create_regatta=" in js
    assert "/api/club/events/match" in js
    assert "sa-home-regatta-actions" in js
    assert "club-upcoming-events-section" in js
    src = API.read_text(encoding="utf-8")
    assert "data-club-abbrev" in src
    manage = src.find("def club_manage_page")
    assert manage > 0
    assert 'url="/clubs"' not in src[manage : manage + 800]
    assert "Club events" in src[manage : manage + 1200]
