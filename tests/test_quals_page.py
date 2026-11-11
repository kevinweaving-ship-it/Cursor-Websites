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
        self.assertIn("Not recorded", html)
        self.assertIn("First issued", html)
        self.assertIn("Renewals", html)
        self.assertIn("Years left", html)
        self.assertIn("Months left", html)
        self.assertIn("Days left", html)
        self.assertIn('data-sort="years_left"', html)
        self.assertIn('data-years_left="2"', html)
        self.assertIn('data-days_left="17"', html)
        self.assertIn(">Current<", html)
        self.assertIn(">Expired<", html)
        self.assertIn(">No date<", html)
        self.assertIn('href="/sailor/elfie-holden"', html)
        self.assertIn('href="https://sailingsa.co.za/quals"', html)
        # Current row is rendered before the expired row inside the senior table.
        senior = html.split('id="qual-SENIOR_INSTR"', 1)[1]
        self.assertLess(senior.find("Elfie Holden"), senior.find("Robert Holden"))


if __name__ == "__main__":
    unittest.main()
