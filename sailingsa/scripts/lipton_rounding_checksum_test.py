#!/usr/bin/env python3
"""Rounding + checksum tests. No teleapi."""
from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from lipton_dev_checksum import build_checksum, one_pass
from lipton_dev_later_laps import rounding_candidates
from lipton_mark_rounding import COURSE_PASSES

SAST = ZoneInfo("Africa/Johannesburg")
GUN = int(datetime(2026, 8, 27, 13, 55, 1, tzinfo=SAST).timestamp() * 1000)


def pt(ts, lat, lon, heading=280):
    return {"ts": ts, "latitude": lat, "longitude": lon, "heading": heading, "sog": 4.6}


class RoundingChecksumTest(unittest.TestCase):
    def test_gap_then_close_cpa_counts(self):
        """FBYC-style: GPS hole, then appear in the zone and leave. Must count."""
        mk = [{"ts": GUN, "latitude": -33.8572, "longitude": 18.46115}]
        t0 = GUN + 3_600_000
        far = pt(t0, -33.8630, 18.46115, heading=0)
        near = pt(t0 + 316_000, -33.85722, 18.46115, heading=283)
        cpa = pt(t0 + 316_000 + 38_000, -33.85720, 18.46115, heading=283)
        leave = pt(t0 + 316_000 + 58_000, -33.85720, 18.46160, heading=272)
        got = rounding_candidates([far, near, cpa, leave], mk)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["ts"], cpa["ts"])
        self.assertLess(got[0]["closest_m"], 10)

    def test_reappear_far_past_mark_is_not_a_rounding(self):
        """WBYC-style: 400s hole, next ping is 300m past the mark. Do not invent."""
        mk = [{"ts": GUN, "latitude": -33.8572, "longitude": 18.46115}]
        t0 = GUN + 3_600_000
        far_before = pt(t0, -33.8620, 18.46115, heading=330)
        far_after = pt(t0 + 413_000, -33.8595, 18.4585, heading=250)
        got = rounding_candidates([far_before, far_after], mk)
        self.assertEqual(got, [])

    def test_checksum_17_and_gap(self):
        fleet = [f"B{i:02d}" for i in range(17)]
        st = [{"boat": s, "ts_ms": GUN + i} for i, s in enumerate(fleet)]
        m1 = [{"boat": s, "ts_ms": GUN + 1000 + i} for i, s in enumerate(fleet)]
        fin = [{"boat": s, "ts_ms": GUN + 9000 + i} for i, s in enumerate(fleet)]
        ok = build_checksum(
            fleet=fleet,
            st=st,
            mark_passes=[{"id": "L1-1", "boats": m1}],
            finish=fin,
            course_passes=[{"id": "L1-1", "lap": 1, "mark": "1"}],
        )
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["fleet_n"], 17)
        self.assertEqual(len(ok["passes"]), 3)

        gap = one_pass("L2-1", m1[4:], fleet)
        self.assertFalse(gap["ok"])
        self.assertEqual(gap["n"], 13)
        self.assertEqual(len(gap["missing"]), 4)

    def test_shortened_course_stops_before_empty_laps(self):
        fleet = [f"B{i:02d}" for i in range(17)]
        st = [{"boat": s, "ts_ms": GUN} for s in fleet]
        sailed = ["L1-1", "L1-2", "L1-3", "L1-4", "L2-1", "L2-2", "L2-3"]
        mark_passes = [{"id": i, "boats": [{"boat": s, "ts_ms": GUN + 1} for s in fleet]} for i in sailed]
        fin = [{"boat": s, "ts_ms": GUN + 9} for s in fleet]
        chk = build_checksum(
            fleet=fleet,
            st=st,
            mark_passes=mark_passes,
            finish=fin,
            course_passes=COURSE_PASSES,
        )
        ids = [p["id"] for p in chk["passes"]]
        self.assertEqual(ids, ["ST", *sailed, "FIN"])
        self.assertNotIn("L2-4", ids)
        self.assertNotIn("L3-1", ids)


if __name__ == "__main__":
    unittest.main()
