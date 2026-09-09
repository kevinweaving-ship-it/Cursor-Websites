import unittest

import restore_meter_hours as r


class BinsFromRegisterTest(unittest.TestCase):
    def test_hourly_deltas(self):
        import datetime
        sast = datetime.timezone(datetime.timedelta(hours=2))
        a = datetime.datetime(2026, 9, 8, 1, 50, tzinfo=sast).timestamp()
        b = datetime.datetime(2026, 9, 8, 2, 50, tzinfo=sast).timestamp()
        c = datetime.datetime(2026, 9, 8, 3, 50, tzinfo=sast).timestamp()
        out = r.bins_from_register([(a, 10.0), (b, 11.2), (c, 12.4)])
        self.assertEqual(out["2026090802"], 1.2)
        self.assertEqual(out["2026090803"], 1.2)
        self.assertNotIn("2026090801", out)

    def test_rejects_spike(self):
        sast = __import__("datetime").timezone(__import__("datetime").timedelta(hours=2))
        dt = __import__("datetime").datetime
        a = dt(2026, 9, 8, 1, 50, tzinfo=sast).timestamp()
        b = dt(2026, 9, 8, 2, 50, tzinfo=sast).timestamp()
        out = r.bins_from_register([(a, 10.0), (b, 90.0)])
        self.assertEqual(out, {})

    def test_merge_keeps_max(self):
        self.assertEqual(r.merge_hours({"2026090900": 1.0}, {"2026090900": 1.2, "2026090901": 0.5}),
                         {"2026090900": 1.2, "2026090901": 0.5})
