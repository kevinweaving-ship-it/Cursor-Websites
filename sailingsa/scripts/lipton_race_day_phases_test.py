#!/usr/bin/env python3
"""Unit tests for Lipton race-day phase machine. No network."""
from __future__ import annotations

import unittest

from lipton_race_day_phases import (
    BoatSample,
    MarkSample,
    Phase,
    PhaseInput,
    TrackerRace,
    advance_phase,
    expected_race_number,
    snapshot_marks,
)


def boats(n=17, sog=0.1):
    return [BoatSample(sail=f"B{i}", sog_ms=sog, lat=-33.92, lon=18.42) for i in range(n)]


def marks():
    return [
        MarkSample("1", -33.90, 18.45, 0.0),
        MarkSample("2", -33.91, 18.46, 0.0),
        MarkSample("3", -33.92, 18.44, 0.0),
        MarkSample("4", -33.921, 18.441, 0.0),
    ]


class RaceDayPhasesTest(unittest.TestCase):
    def test_expected_race_from_last_finished(self):
        self.assertEqual(expected_race_number(5, None), 6)
        self.assertEqual(expected_race_number(5, TrackerRace(6)), 6)
        self.assertEqual(expected_race_number(5, TrackerRace(7)), 7)

    def test_dock_when_idle(self):
        r = advance_phase(
            Phase.DOCK,
            PhaseInput(
                now_ms=1_000_000,
                boats=boats(sog=0.2),
                marks=marks(),
                last_finished_race=5,
                tracker_race=TrackerRace(6),
            ),
        )
        self.assertEqual(r.phase, Phase.DOCK)
        self.assertTrue(r.grab)
        self.assertFalse(r.race_mode)

    def test_course_set_commits_marks_when_fleet_moves(self):
        r = advance_phase(
            Phase.DOCK,
            PhaseInput(
                now_ms=1_000_000,
                boats=boats(sog=1.5),  # >1 kn
                marks=marks(),
                last_finished_race=5,
                tracker_race=TrackerRace(6, has_start_line=False),
            ),
        )
        self.assertEqual(r.phase, Phase.COURSE_SET)
        self.assertTrue(r.marks_committed)
        self.assertIn("1", r.committed_marks)
        self.assertIn("4", r.committed_marks)

    def test_prestart_when_near_pin(self):
        committed = snapshot_marks(marks())
        # boats near mark 4
        near = [BoatSample(sail=f"B{i}", sog_ms=0.8, lat=-33.921, lon=18.441) for i in range(17)]
        r = advance_phase(
            Phase.COURSE_SET,
            PhaseInput(
                now_ms=1_000_000,
                boats=near,
                marks=marks(),
                last_finished_race=5,
                tracker_race=TrackerRace(6, has_start_line=True),
                marks_committed=True,
                committed_marks=committed,
            ),
        )
        self.assertEqual(r.phase, Phase.PRESTART)
        self.assertEqual(r.race_number, 6)

    def test_t_minus_arms_race_mode(self):
        gun = 2_000_000
        r = advance_phase(
            Phase.PRESTART,
            PhaseInput(
                now_ms=gun - 120_000,
                boats=boats(sog=0.8),
                marks=marks(),
                last_finished_race=5,
                tracker_race=TrackerRace(6, gun_ts_ms=gun, has_start_line=True),
                marks_committed=True,
                committed_marks=snapshot_marks(marks()),
            ),
        )
        self.assertEqual(r.phase, Phase.T_MINUS)
        self.assertTrue(r.race_mode)
        self.assertAlmostEqual(r.t_minus_s or 0, 120.0, places=0)

    def test_racing_after_gun(self):
        gun = 2_000_000
        r = advance_phase(
            Phase.T_MINUS,
            PhaseInput(
                now_ms=gun + 5_000,
                boats=boats(sog=2.0),
                marks=marks(),
                last_finished_race=5,
                tracker_race=TrackerRace(6, gun_ts_ms=gun, finish_count=0),
                marks_committed=True,
                committed_marks=snapshot_marks(marks()),
            ),
        )
        self.assertEqual(r.phase, Phase.RACING)
        self.assertTrue(r.race_mode)
        self.assertIsNotNone(r.t_plus_s)

    def test_finished_when_finishes_arrive(self):
        gun = 2_000_000
        r = advance_phase(
            Phase.RACING,
            PhaseInput(
                now_ms=gun + 3_600_000,
                boats=boats(sog=0.5),
                marks=marks(),
                last_finished_race=5,
                tracker_race=TrackerRace(6, gun_ts_ms=gun, finish_count=17),
                marks_committed=True,
                committed_marks=snapshot_marks(marks()),
            ),
        )
        self.assertEqual(r.phase, Phase.FINISHED)
        self.assertFalse(r.race_mode)


if __name__ == "__main__":
    unittest.main()
