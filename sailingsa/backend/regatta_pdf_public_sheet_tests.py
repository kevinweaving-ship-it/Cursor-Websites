import unittest

from regatta_pdf_public_sheet import (
    apply_parent_truth_to_pdf,
    extract_parent_fleet_htmls,
    parent_event_logo,
    parent_page_left_logo,
    sanitize_public_fleet_html,
)


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

    def test_parent_dnc_is_the_cell_value(self):
        html = (
            "<table><thead><tr><th class=\"race-col\">R2</th><th class=\"nett-col\">Nett</th></tr></thead>"
            "<tbody><tr>"
            '<td class="code race-col" data-race-key="R2">'
            '<span class="code"><span class="wc-code">DNC</span></span></td>'
            '<td class="nett-col">18</td>'
            "</tr></tbody></table>"
        )
        out = sanitize_public_fleet_html(html)
        self.assertIn(">DNC<", out)
        self.assertNotIn("wc-code", out)

    def test_scored_cell_keeps_code_overlay(self):
        html = (
            "<table><thead><tr><th class=\"race-col\">R1</th></tr></thead><tbody><tr>"
            '<td class="race-col"><span class="wc-score">12</span>'
            '<span class="wc-code">OCS</span></td>'
            "</tr></tbody></table>"
        )
        out = sanitize_public_fleet_html(html)
        self.assertIn("wc-score", out)
        self.assertIn("wc-code", out)
        self.assertIn("OCS", out)

    def test_parent_left_logo_is_event_only(self):
        page = (
            '<img src="/artwork/Event%20Logo/Dam-Bottle-Sprints.png?v=20261010pt1" '
            'class="regatta-header-logo-img regatta-header-left-logo-img" />'
            '<div class="fleet-section"><div class="class-header">x</div>'
            "<table><tr><th>Rank</th></tr></table></div></div>"
        )
        self.assertIn("Dam-Bottle-Sprints", parent_page_left_logo(page))
        self.assertEqual(len(extract_parent_fleet_htmls(page)), 1)
        class_left = (
            '<img src="/artwork/Class Logo/420-Class-Logo.png" '
            'class="regatta-header-logo-img regatta-header-left-logo-img" />'
        )
        self.assertIn("420-Class-Logo", parent_page_left_logo(class_left))
        self.assertEqual(parent_event_logo(class_left), "")

    def test_pdf_packet_uses_parent_logos_and_public_table(self):
        page = (
            '<div class="regatta-name">Dam Bottle Sprints</div>'
            '<div class="host-club"><a href="/club/hmyc">HMYC - Henley Midmar Yacht Club</a></div>'
            '<div class="status-line">Results are Provisional as at 10 October 2026 at 10:14</div>'
            '<img src="/artwork/Event%20Logo/Dam-Bottle-Sprints.png?v=1" '
            'class="regatta-header-logo-img regatta-header-left-logo-img" />'
            '<img src="/artwork/Club Logo/HMYC.png" '
            'class="regatta-header-logo-img regatta-header-club-logo-img" />'
            '<div class="fleet-section"><div class="class-header">'
            '<img src="/artwork/Class Logo/Open-Class-Logo.png" class="class-header-logo-img" alt="Open">'
            "</div><table><thead><tr>"
            '<th>Rank</th><th>Helm</th><th>Elapsed</th><th>Nett</th>'
            "</tr></thead><tbody><tr><td>1</td><td>A</td><td>nope</td><td>5</td></tr>"
            "</table></div></div>"
        )
        packet = apply_parent_truth_to_pdf(
            "2026-10-10-hmyc-dam-bottle-sprints",
            fleets=[{"class_slug": "open", "html": "<table></table>"}],
            left_logo="/wrong.png",
            right_logo="/wrong-club.png",
            event_name="wrong",
            host="wrong",
            status_line="wrong",
            page_html=page,
        )
        self.assertEqual(packet["event_name"], "Dam Bottle Sprints")
        self.assertIn("HMYC", packet["host"])
        self.assertTrue(packet["status_line"].startswith("Results are"))
        self.assertIn("Dam-Bottle-Sprints", packet["left_logo"])
        self.assertIn("HMYC.png", packet["right_logo"])
        self.assertEqual(len(packet["fleets"]), 1)
        html = packet["fleets"][0]["html"]
        self.assertNotIn("Elapsed", html)
        self.assertNotIn("Open-Class-Logo", html)
        self.assertIn("Dam-Bottle-Sprints", html)


if __name__ == "__main__":
    unittest.main()
