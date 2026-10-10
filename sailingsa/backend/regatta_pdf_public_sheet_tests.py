import unittest

from regatta_pdf_public_sheet import sanitize_public_fleet_html


class PublicSheetSanitizeTests(unittest.TestCase):
    def test_drops_calc_cols_and_open_logo(self):
        html = (
            '<div class="fleet-section">'
            '<div class="class-header">'
            '<img src="/artwork/Class Logo/Open-Class-Logo-v20260913h.png" '
            'alt="Open" class="class-header-logo-img">'
            "</div>"
            "<table><thead><tr>"
            '<th class="rank-col">Rank</th><th class="sail-col">Sail No</th>'
            '<th class="wc-meta-col">Age</th><th class="helm-col">Helm</th>'
            '<th class="race-col">R1</th><th class="wc-meta-col">PY</th>'
            '<th class="wc-meta-col">Elapsed</th><th class="wc-meta-col">Corrected</th>'
            '<th class="nett-col">Nett</th>'
            "</tr></thead><tbody><tr>"
            "<td>1</td><td>5200</td><td></td><td>A</td><td>1</td>"
            '<td>1102</td><td>{"R1": "18:46"}</td>'
            '<td>{"R1": "16:53"}</td><td>5</td>'
            "</tr></tbody></table></div>"
        )
        out = sanitize_public_fleet_html(
            html, event_logo="/artwork/Event Logo/Dam-Bottle-Sprints.png?v=20261010pt1"
        )
        self.assertNotIn("Elapsed", out)
        self.assertNotIn("Corrected", out)
        self.assertNotIn(">PY<", out)
        self.assertNotIn("Age", out)
        self.assertNotIn("18:46", out)
        self.assertNotIn("Open-Class-Logo", out)
        self.assertIn("Dam-Bottle-Sprints.png", out)
        self.assertIn("Rank", out)
        self.assertIn("Helm", out)
        self.assertIn("Nett", out)


if __name__ == "__main__":
    unittest.main()
