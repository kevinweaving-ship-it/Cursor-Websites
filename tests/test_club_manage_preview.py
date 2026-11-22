"""Source checks for the /club-manage-preview rebuild. Does not import the full app."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "api.py").read_text(encoding="utf-8")
JS = (ROOT / "js" / "club-manage-preview.js").read_text(encoding="utf-8")
API_JS = (ROOT / "js" / "api.js").read_text(encoding="utf-8")


def test_preview_route_does_not_replace_club_manage():
    assert '@app.get("/club-manage"' in API
    assert '@app.get("/club-manage-preview"' in API
    assert "Does not replace /club-manage" in API
    assert "club-manage-preview.js" in API
    assert "returnTo=/club-manage-preview" in API


def test_preview_js_uses_master_layout_and_dropdowns():
    assert "function buildMasterPageLayout" in JS
    assert "club-manage-events" in JS
    assert "club-manage-fleets" in JS
    assert "club-manage-entries" in JS
    assert "club-manage-upload" in JS
    assert "club-manage-publish" in JS
    assert 'id="cm-create-class"' in JS
    assert "js-select-event" in JS
    assert "input name=\"regatta_id\"" not in JS
    assert "input name=\"event_id\"" not in JS


def test_preview_and_commit_are_separate():
    assert "id=\"cm-preview-btn\"" in JS
    assert "id=\"cm-commit-btn\"" in JS
    assert "/ingest/preview" in JS
    assert "/ingest/commit" in JS
    assert "preview_token" in JS
    assert "Commit stays off until preview succeeds" in JS or "disabled" in JS


def test_session_club_id_helper():
    assert "function sailingSessionClubId" in API_JS
    assert "window.sailingSessionClubId" in API_JS
