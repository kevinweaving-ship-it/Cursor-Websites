"""Qualifications page: validity arithmetic and sortable table markup."""
import importlib.util
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "quals_page", ROOT / "sailingsa/backend/quals_page.py"
)
quals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quals)

TODAY = date(2026, 11, 11)


class QualsPageTests(unittest.TestCase):
    def test_calendar_window_for_known_people(self):
        self.assertEqual(quals.calendar_ymd(TODAY, date(2028, 11, 28)), (2, 0, 17))
        self.assertEqual(quals.calendar_ymd(TODAY, date(2025, 12, 31)), (0, -10, -11))
        self.assertEqual(quals.calendar_ymd(TODAY, date(2029, 6, 3)), (2, 6, 23))

    def test_format_left_drops_zero_units(self):
        self.assertEqual(quals.format_left(2, 4, 7), "2y4m7d")
        self.assertEqual(quals.format_left(2, 0, 17), "2y17d")
        self.assertEqual(quals.format_left(0, -10, -11), "-10m11d")
        self.assertEqual(quals.format_left(2, 6, 23), "2y6m23d")

    def test_tables_mark_unknown_first_issue_and_sort_columns(self):
        rows = [
            {
                "role_code": "SENIOR_INSTR",
                "role_label": "Senior Instructor",
                "sas_id": "28",
                "full_name": "Elfie Holden",
                "club": "",
                "awarded_date": date(2024, 11, 28),
                "expires_date": date(2028, 11, 28),
            },
            {
                "role_code": "SENIOR_INSTR",
                "role_label": "Senior Instructor",
                "sas_id": "27",
                "full_name": "Robert Holden",
                "club": "MBSC",
                "awarded_date": date(2021, 12, 31),
                "expires_date": date(2025, 12, 31),
            },
            {
                "role_code": "ASSIST_INSTR",
                "role_label": "Assistant Instructor",
                "sas_id": "9050",
                "full_name": "Oliver Holden",
                "club": "MBSC",
                "awarded_date": None,
                "expires_date": None,
            },
        ]
        html = quals.render_quals_html(rows, today=TODAY)
        self.assertNotIn("Not recorded", html)
        self.assertNotIn("First issued", html)
        self.assertNotIn("Renewals", html)
        self.assertNotIn("Years left", html)
        self.assertIn(">2y17d<", html)
        self.assertIn(">-10m11d<", html)
        self.assertIn('data-sort="left"', html)
        elfie_days = str((date(2028, 11, 28) - TODAY).days)
        self.assertIn(f'data-left="{elfie_days}"', html)
        self.assertIn(">Current<", html)
        self.assertIn(">Expired<", html)
        self.assertIn(">No date<", html)
        self.assertIn('href="/sailor/elfie-holden"', html)
        self.assertIn('href="https://sailingsa.co.za/quals"', html)
        self.assertIn('id="menuBtn"', html)
        self.assertIn('class="nav-menu-overlay"', html)
        self.assertIn('href="/about"', html)
        self.assertNotIn("https://sailingsa.co.za/events", html)
        self.assertNotIn("nav-inline", html)
        self.assertNotIn("/sailingsa/quals", html)
        # Current row is rendered before the expired row inside the senior table.
        senior = html.split('id="qual-SENIOR_INSTR"', 1)[1]
        self.assertLess(senior.find("Elfie Holden"), senior.find("Robert Holden"))


if __name__ == "__main__":
    unittest.main()
