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
        st = [{"boat": s, "ts_ms": GUN + i} for i, s in enumerate(fleet)]
        sailed = ["L1-1", "L1-2", "L1-3", "L1-4", "L2-1", "L2-2", "L2-3"]
        mark_passes = [
            {
                "id": pid,
                "boats": [{"boat": s, "ts_ms": GUN + 1000 * (n + 1) + i} for i, s in enumerate(fleet)],
            }
            for n, pid in enumerate(sailed)
        ]
        fin = [{"boat": s, "ts_ms": GUN + 1000 * (len(sailed) + 1) + i} for i, s in enumerate(fleet)]
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
        self.assertTrue(chk["sanity"]["ok"])

    def test_tail_still_on_previous_leg_is_not_a_gap(self):
        """Leaders round L2-3 while five boats are still on the beat to L2-2."""
        fleet = [f"B{i:02d}" for i in range(17)]
        leaders, tail = fleet[:12], fleet[12:]
        st = [{"boat": s, "ts_ms": GUN + i} for i, s in enumerate(fleet)]
        l22 = [{"boat": s, "ts_ms": GUN + 2000 + i} for i, s in enumerate(leaders)]
        l22 += [{"boat": s, "ts_ms": GUN + 8000 + i} for i, s in enumerate(tail)]
        l23 = [{"boat": s, "ts_ms": GUN + 4000 + i} for i, s in enumerate(leaders)]
        fin = [{"boat": s, "ts_ms": GUN + 12000 + i} for i, s in enumerate(fleet)]
        chk = build_checksum(
            fleet=fleet,
            st=st,
            mark_passes=[
                {"id": "L2-2", "boats": l22},
                {"id": "L2-3", "boats": l23},
            ],
            finish=fin,
            course_passes=[{"id": "L2-2", "lap": 2, "mark": "2"}, {"id": "L2-3", "lap": 2, "mark": "3"}],
        )
        self.assertTrue(chk["ok"])
        l23p = next(p for p in chk["passes"] if p["id"] == "L2-3")
        self.assertEqual(l23p["fleet_n"], 12)
        self.assertEqual(l23p["missing"], [])

    def test_skipped_middle_mark_does_not_stop_later_laps(self):
        fleet = [f"B{i:02d}" for i in range(17)]
        st = [{"boat": s, "ts_ms": GUN + i} for i, s in enumerate(fleet)]
        m1 = [{"boat": s, "ts_ms": GUN + 1000 + i} for i, s in enumerate(fleet)]
        m3 = [{"boat": s, "ts_ms": GUN + 3000 + i} for i, s in enumerate(fleet)]
        fin = [{"boat": s, "ts_ms": GUN + 9000 + i} for i, s in enumerate(fleet)]
        chk = build_checksum(
            fleet=fleet,
            st=st,
            mark_passes=[{"id": "L1-1", "boats": m1}, {"id": "L1-3", "boats": m3}],
            finish=fin,
            course_passes=COURSE_PASSES,
        )
        ids = [p["id"] for p in chk["passes"]]
        self.assertEqual(ids, ["ST", "L1-1", "L1-3", "FIN"])
        self.assertTrue(chk["ok"])

    def test_place_delta_telescopes_to_start_minus_finish(self):
        fleet = ["A", "B", "C"]
        st = [{"boat": "A", "ts_ms": 1}, {"boat": "B", "ts_ms": 2}, {"boat": "C", "ts_ms": 3}]
        m1 = [{"boat": "B", "ts_ms": 10}, {"boat": "A", "ts_ms": 11}, {"boat": "C", "ts_ms": 12}]
        fin = [{"boat": "C", "ts_ms": 20}, {"boat": "B", "ts_ms": 21}, {"boat": "A", "ts_ms": 22}]
        chk = build_checksum(
            fleet=fleet,
            st=st,
            mark_passes=[{"id": "L1-1", "boats": m1}],
            finish=fin,
            course_passes=[{"id": "L1-1", "lap": 1, "mark": "1"}],
        )
        self.assertTrue(chk["ok"])
        self.assertTrue(chk["sanity"]["ok"])
        # A 1→3 expect −2; B 2→2 expect 0; C 3→1 expect +2

    def test_sanity_flags_non_increasing_times(self):
        fleet = ["A", "B"]
        st = [{"boat": "A", "ts_ms": 10}, {"boat": "B", "ts_ms": 11}]
        m1 = [{"boat": "A", "ts_ms": 9}, {"boat": "B", "ts_ms": 20}]
        fin = [{"boat": "A", "ts_ms": 30}, {"boat": "B", "ts_ms": 31}]
        chk = build_checksum(
            fleet=fleet,
            st=st,
            mark_passes=[{"id": "L1-1", "boats": m1}],
            finish=fin,
            course_passes=[{"id": "L1-1", "lap": 1, "mark": "1"}],
        )
        self.assertFalse(chk["sanity"]["ok"])
        self.assertEqual(chk["sanity"]["time_fail"][0]["boat"], "A")



class MarkMoveNearestTest(unittest.TestCase):
    def test_nearest_mark_switches_after_tow(self):
        """After RO tows weather ~200m, later boat times must use new station."""
        from lipton_dev_later_laps import nearest_mark, mark_move_events
        t0 = GUN
        before = {"ts": t0 + 1_000_000, "latitude": -33.8800, "longitude": 18.4820}
        after = {"ts": t0 + 1_200_000, "latitude": -33.8785, "longitude": 18.4805}
        marks = [before, after]
        # mid-window and later must prefer relocated buoy
        mid = nearest_mark(marks, t0 + 1_100_000)
        late = nearest_mark(marks, t0 + 1_500_000)
        early = nearest_mark(marks, t0 + 1_050_000)
        self.assertEqual(early["latitude"], before["latitude"])
        self.assertEqual(mid["latitude"], after["latitude"])
        self.assertEqual(late["latitude"], after["latitude"])
        ev = mark_move_events(marks, thresh_m=50.0, gun_ts_ms=GUN)
        self.assertEqual(len(ev), 1)
        self.assertGreater(ev[0]["moved_m"], 100)


class CourseCardTest(unittest.TestCase):
    def test_quadrangle_two_far_weathers(self):
        from lipton_dev_course import classify_course

        start = {"left": {"lat": -33.878, "lon": 18.467}, "right": {"lat": -33.877, "lon": 18.468}}
        finish = {"left": {"lat": -33.8765, "lon": 18.468}, "right": {"lat": -33.877, "lon": 18.4685}}
        got = classify_course(
            marks={
                "1": (-33.858, 18.460),
                "2": (-33.862, 18.450),
                "3": (-33.880, 18.461),
                "4": (-33.876, 18.468),
            },
            start_line=start,
            finish_line=finish,
            lap1_mark_ids=[1, 2, 3, 4],
        )
        self.assertEqual(got["id"], "quadrangle")

    def test_triangle_one_weather_near_wing(self):
        from lipton_dev_course import classify_course

        start = {"left": {"lat": -33.863, "lon": 18.478}, "right": {"lat": -33.864, "lon": 18.475}}
        finish = {"left": {"lat": -33.864, "lon": 18.475}, "right": {"lat": -33.864, "lon": 18.476}}
        got = classify_course(
            marks={
                "1": (-33.880, 18.482),
                "2": (-33.861, 18.473),
                "3": (-33.862, 18.478),
                "4": (-33.863, 18.479),
            },
            start_line=start,
            finish_line=finish,
            lap1_mark_ids=[1, 2, 3, 4],
        )
        self.assertEqual(got["id"], "triangle")


if __name__ == "__main__":
    unittest.main()
