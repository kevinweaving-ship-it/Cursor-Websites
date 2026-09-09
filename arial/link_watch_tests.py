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
        text = w.compose_link(self.cfg, "down", "237.3 V / 5.59 A / 1156 W", "08:31", True, 81 * 60)
        self.assertIn("Link Loss : 08:31 > 1h21m", text)
        self.assertIn("Last Alarm AC =", text)
        self.assertIn("237.3 V / 5.59 A / 1156 W", text)
        self.assertNotIn("Alarm AC on", text)
        self.assertNotIn("Alarm AC off", text)

    def test_down_no_ac_claim(self):
        text = w.compose_link(self.cfg, "down", "237.3 V / 5.59 A / 1156 W", "08:31", False, 30 * 60)
        self.assertIn("Last Alarm AC =", text)
        self.assertNotIn("Power off confirmed by alarm", text)

    def test_restore(self):
        text = w.compose_link(self.cfg, "up", "230.1 V / 0.10 A / 22 W", "08:47", True)
        self.assertIn("Link restored", text)
        self.assertIn("Last Alarm AC =", text)
        self.assertIn("230.1 V / 0.10 A / 22 W", text)

    def test_elapsed_label(self):
        self.assertEqual(w.elapsed_label(90 * 60), "1h30m")
        self.assertEqual(w.elapsed_label(5 * 60), "5m")


class SendAdminRateCapTest(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "recipients": [
                {"name": "Kevin", "number": "111", "scope": "all"},
                {"name": "Pingoa", "number": "222", "scope": "all"},
            ]
        }
        self.calls = []
        now = __import__("time").time()
        self.full = [now - i for i in range(20)]

    def _post(self, url, body, timeout=40):
        self.calls.append(body)
        return {"ok": True, "id": "x"}

    def test_failed_send_does_not_count(self):
        def fail(url, body, timeout=40):
            return {"ok": False, "error": "down"}
        w.post = fail
        sent = list(self.full[:19])
        ok = w.send_admin(self.cfg, "x", sent, "hansekop", "nag")
        self.assertFalse(ok)
        self.assertEqual(len(sent), 19)

    def test_restore_exempt_from_cap(self):
        w.post = self._post
        sent = list(self.full)
        ok = w.send_admin(self.cfg, "Link restored", sent, "hansekop", "up")
        self.assertTrue(ok)
        self.assertEqual(len(self.calls), 2)

    def test_nag_blocked_at_cap(self):
        w.post = self._post
        sent = list(self.full)
        ok = w.send_admin(self.cfg, "nag", sent, "hansekop", "nag")
        self.assertFalse(ok)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
