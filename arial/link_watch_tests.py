"""Unit tests for Hansekop breaker no-link WhatsApp helpers."""
import unittest

import alert_watcher as w


class AdminTargetsTest(unittest.TestCase):
    def test_scope_all_only(self):
        cfg = {
            "recipients": [
                {"name": "Kevin", "number": "111", "scope": "all"},
                {"name": "Pingoa", "number": "222", "scope": "all"},
                {"name": "Amoroc", "number": "333", "scope": "own"},
                {"name": "Onguard", "number": "444", "scope": "own"},
            ]
        }
        names = [n for n, _ in w.admin_targets(cfg)]
        self.assertEqual(names, ["Kevin", "Pingoa"])


class MeterReadingTest(unittest.TestCase):
    def test_scales(self):
        p = {"status": [
            {"code": "cur_voltage", "value": 23170},
            {"code": "cur_current", "value": 305},
            {"code": "cur_power", "value": 6660},
        ]}
        self.assertEqual(w.meter_reading(p), "231.7 V / 0.30 A / 67 W")

    def test_last_report(self):
        now = __import__("datetime").datetime(2026, 9, 9, 8, 32, tzinfo=w.SAST)
        p = {"sharing": {"meterLastReportAgeS": 13 * 60}}
        self.assertEqual(w.last_report_hhmm(p, now), "08:19")


class ComposeLinkTest(unittest.TestCase):
    cfg = {"label": "Hansekop", "url": "https://sailingsa.co.za/arial/"}

    def test_down_keeps_snapshot(self):
        text = w.compose_link(self.cfg, "down", "231.7 V / 0.30 A / 67 W", "08:19", "Power OK")
        self.assertIn("Main breaker NO LINK", text)
        self.assertIn("Last report 08:19", text)
        self.assertIn("last reading 231.7 V / 0.30 A / 67 W", text)
        self.assertIn("Alarm mains: Power OK", text)
        self.assertNotIn("readings 0 V", text)

    def test_down_alarm_fail_zeros(self):
        text = w.compose_link(self.cfg, "down", "", "08:19", "A/C FAILURE (alarm on battery)")
        self.assertIn("Power off confirmed by alarm — readings 0 V / 0 A / 0 W", text)

    def test_restore(self):
        text = w.compose_link(self.cfg, "up", "230.1 V / 0.10 A / 22 W", "08:47", "Power OK")
        self.assertIn("LINK RESTORED", text)
        self.assertIn("230.1 V / 0.10 A / 22 W", text)


if __name__ == "__main__":
    unittest.main()
