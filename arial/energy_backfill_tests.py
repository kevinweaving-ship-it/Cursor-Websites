import unittest

import energy_backfill as b
import sharing_live as sl


class SpreadTest(unittest.TestCase):
    def test_rejects_invented_spike(self):
        # 187 kWh in 2 minutes is not a real house load
        self.assertEqual(b.spread_register_delta(187.85, 1000, 1120), {})

    def test_spreads_real_delta(self):
        # 09 Sep 08:31 to 10:33 SAST, 2.69 kWh
        start = 1788935466.0  # 08:31:06
        end = 1788942832.0    # 10:33:52
        adds = b.spread_register_delta(2.69, start, end)
        self.assertIn("2026090909", adds)
        self.assertIn("2026090908", adds)
        self.assertIn("2026090910", adds)
        self.assertAlmostEqual(sum(adds.values()), 2.69, places=3)
        self.assertGreater(adds["2026090909"], adds["2026090908"])

    def test_empty_hour_capped_at_avg_leftover_on_partial(self):
        measured = {
            "2026090906": 1.172, "2026090907": 1.178, "2026090908": 0.612,
            "2026090909": None, "2026090910": 0.25,
        }
        adds = {"2026090908": 0.633, "2026090909": 1.315, "2026090910": 0.742}
        avg = b.neighbor_avg(measured, "2026090909")
        self.assertAlmostEqual(avg, 1.175, places=3)
        bins, est = b.apply_adds(measured, adds, avg)
        self.assertEqual(est, ["2026090909"])
        self.assertAlmostEqual(bins["2026090909"], 1.175, places=3)
        self.assertGreater(bins["2026090910"], 0.99)

    def test_empty_hour_is_est(self):
        adds = {"2026090908": 0.5, "2026090909": 1.15, "2026090910": 0.6}
        measured = {"2026090908": 0.612, "2026090909": None, "2026090910": 0.25}
        bins, est = b.apply_adds(measured, adds)
        self.assertEqual(est, ["2026090909"])
        self.assertAlmostEqual(bins["2026090908"], 1.112, places=3)
        self.assertAlmostEqual(bins["2026090909"], 1.15, places=3)
        self.assertAlmostEqual(bins["2026090910"], 0.85, places=3)


class SharingLiveTest(unittest.TestCase):
    def test_live_even_if_persist_behind(self):
        self.assertTrue(sl.health_says_live({
            "ok": True, "meterOnline": True, "meterStale": False, "mqttConnected": True,
        }))

    def test_stale_is_down(self):
        self.assertFalse(sl.health_says_live({
            "ok": True, "meterOnline": True, "meterStale": True, "mqttConnected": True,
        }))


if __name__ == "__main__":
    unittest.main()
