import unittest

from sailingsa.backend.card_left_logo import resolve_card_left_logo


class CardLeftLogoTests(unittest.TestCase):
    def test_easter_regatta_and_9_hour_uses_prior_year_hmyc_event_logo(self):
        src = resolve_card_left_logo("Easter Regatta and 9 Hour", host="HMYC")
        self.assertEqual(src, "/artwork/Event Logo/HMYC-6hr-9hr-Race.png")

    def test_9_6_hour_endurance_uses_same_hmyc_event_logo(self):
        src = resolve_card_left_logo("9/6 Hour Endurance Race", host="HMYC")
        self.assertEqual(src, "/artwork/Event Logo/HMYC-6hr-9hr-Race.png")

    def test_prior_year_hmyc_9hr_endurance(self):
        src = resolve_card_left_logo("2025 HMYC 9HR ENDURANCE RACE")
        self.assertEqual(src, "/artwork/Event Logo/HMYC-9hr.png")

    def test_tsc_9hr_does_not_steal_hmyc_logo(self):
        src = resolve_card_left_logo("2025 TSC 9hr", host="TSC")
        self.assertEqual(src, "/artwork/Event Logo/TSC-9hr.png")

    def test_grandslam_one_word_is_hmyc_prior_year(self):
        src = resolve_card_left_logo("Grandslam", host="HMYC")
        self.assertEqual(src, "/artwork/Event Logo/HMYC-Grand-Slam.png")

    def test_spaced_grand_slam_stays_kzn(self):
        src = resolve_card_left_logo("SA Sailing Grand Slam Regatta")
        self.assertEqual(src, "/artwork/Event Logo/KZN-Grand-Slam.png")

    def test_ussa_uses_team_sailing_event_logo(self):
        src = resolve_card_left_logo("2026 USSA Sailing Championships", host="HMYC")
        self.assertEqual(src, "/artwork/Event Logo/TSL-Team-Sailing.png")

    def test_team_sailing_landing_title(self):
        src = resolve_card_left_logo("WC Team Sailing")
        self.assertEqual(src, "/artwork/Event Logo/TSL-Team-Sailing.png")

    def test_hunter_falls_back_to_class_logo(self):
        src = resolve_card_left_logo("Hunter nationals")
        self.assertEqual(src, "/artwork/Class Logo/Hunter-19-Class-Logo.png")

    def test_keeps_existing_event_logo(self):
        src = resolve_card_left_logo(
            "Dam Bottle Sprints",
            current="/artwork/Event Logo/Dam-Bottle-Sprints.png",
        )
        self.assertEqual(src, "/artwork/Event Logo/Dam-Bottle-Sprints.png")

    def test_rejects_club_logo_as_current(self):
        src = resolve_card_left_logo(
            "Easter Regatta and 9 Hour",
            current="/artwork/Club Logo/HMYC.png",
        )
        self.assertEqual(src, "/artwork/Event Logo/HMYC-6hr-9hr-Race.png")


if __name__ == "__main__":
    unittest.main()
