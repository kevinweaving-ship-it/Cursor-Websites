"""Contract tests: stored /regatta results PDFs + Print viewer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_FILES = (ROOT / "api.py", ROOT / "api" / "api.py")


def test_print_share_helper_wired_on_standalone_sheets():
    for path in API_FILES:
        text = path.read_text(encoding="utf-8")
        assert "def _regatta_print_share_buttons_html" in text, path
        assert "print_share_bar_html" in text, path
        assert text.count("print_btn = _regatta_print_share_buttons_html()") == 2, path
        assert "def _rebuild_regatta_stored_pdfs" in text, path
        assert "def _serve_regatta_stored_pdf" in text, path
        assert '@app.get("/regatta/{slug}/results.pdf")' in text, path
        assert '@app.get("/regatta/{slug}/class-{class_slug}/results.pdf")' in text, path
        assert "_schedule_regatta_pdf_rebuild" in text, path
        assert (
            '<div class="action-buttons"><button class="action-button" onclick="window.print()">Print</button></div>'
            not in text
        ), path


def test_print_button_opens_stored_pdf_not_screen():
    from sailingsa.backend.regatta_print_compact_css import print_share_bar_html

    bar = print_share_bar_html()
    assert "ssaPdfFrame" in bar
    assert "results.pdf" in bar
    assert "ssaPdfDownload" in bar
    assert "data-ssa-print=\"printer\"" in bar
    assert "data-ssa-print=\"share\"" in bar
    assert "buildPrintDoc" not in bar
    assert "window.print()" not in bar
    assert "html2canvas" not in bar


def test_stored_pdf_urls_and_orientation():
    from sailingsa.backend.regatta_stored_pdf import (
        kinds_from_fleet_html,
        orientation_from_fleet_htmls,
        pdf_abs_path,
        pdf_rel_url,
        paginate_fleet_htmls,
    )

    assert pdf_rel_url("2025-12-19-hyc-youth-nationals") == (
        "/regatta/2025-12-19-hyc-youth-nationals/results.pdf"
    )
    assert pdf_rel_url("2025-12-19-hyc-youth-nationals", "dabchick") == (
        "/regatta/2025-12-19-hyc-youth-nationals/class-dabchick/results.pdf"
    )
    assert pdf_abs_path("2025-12-19-hyc-youth-nationals").name == "results.pdf"
    assert pdf_abs_path("2025-12-19-hyc-youth-nationals", "mirror").name == "class-mirror.pdf"

    yn = (
        '<table><thead><tr>'
        '<th class="rank-col">Rank</th><th class="class-col">Class</th>'
        '<th class="sail-col">Sail No</th><th class="club-col">Club</th>'
        '<th class="wc-meta-col">Age</th><th class="helm-col">Helm</th>'
        + "".join(f'<th class="race-col">R{i}</th>' for i in range(1, 13))
        + '<th class="total-col">Total</th><th class="nett-col">Nett</th>'
        "</tr></thead></table>"
    )
    short = (
        '<table><thead><tr>'
        '<th class="rank-col">Rank</th><th class="class-col">Class</th>'
        '<th class="sail-col">Sail No</th><th class="club-col">Club</th>'
        '<th class="helm-col">Helm</th>'
        '<th class="race-col">R1</th><th class="race-col">R2</th>'
        '<th class="race-col">R3</th><th class="race-col">R4</th>'
        '<th class="total-col">Total</th><th class="nett-col">Nett</th>'
        "</tr></thead></table>"
    )
    assert kinds_from_fleet_html(yn).count("race") == 12
    assert orientation_from_fleet_htmls([yn]) == "landscape"
    assert orientation_from_fleet_htmls([short]) == "portrait"

    fleets = [
        {"html": '<div class="fleet-section">A</div>', "n_rows": 10, "class_slug": "a"},
        {"html": '<div class="fleet-section">B</div>', "n_rows": 30, "class_slug": "b"},
    ]
    paged = paginate_fleet_htmls(fleets, "landscape")
    assert "ssa-print-new-page" in paged[1]["html"]


def test_live_patch_replaces_print_only_markup():
    patch = (ROOT / "sailingsa" / "deploy" / "live_patch_zvyc_cc_print_share.py").read_text(
        encoding="utf-8"
    )
    assert "print_share_bar_html" in patch
    assert "print_btn = _regatta_print_share_buttons_html()" in patch
    stored = (ROOT / "sailingsa" / "deploy" / "live_patch_regatta_stored_pdf.py").read_text(
        encoding="utf-8"
    )
    assert "results.pdf" in stored
    assert "_rebuild_regatta_stored_pdfs" in stored


if __name__ == "__main__":
    test_print_share_helper_wired_on_standalone_sheets()
    test_print_button_opens_stored_pdf_not_screen()
    test_stored_pdf_urls_and_orientation()
    test_live_patch_replaces_print_only_markup()
    print("ok")
