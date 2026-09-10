import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import panel_user as p


class PanelUserNumberTest(unittest.TestCase):
    def test_user_7_text(self):
        self.assertEqual(p.panel_user_number("user 7"), "7")
        self.assertEqual(p.panel_user_number("User #7"), "7")
        self.assertEqual(p.panel_user_number("DISARMED · User 7 · Panel"), "7")

    def test_bare_digit(self):
        self.assertEqual(p.panel_user_number("7"), "7")
        self.assertEqual(p.panel_user_number(7), "7")

    def test_ignores_names(self):
        self.assertEqual(p.panel_user_number("Kevin"), "")
        self.assertEqual(p.panel_user_number(""), "")

    def test_from_event(self):
        self.assertEqual(p.panel_user_number_from_event({"userFullname": "User 7"}), "7")
        self.assertEqual(p.panel_user_number_from_event({"userName": "7"}), "7")
        self.assertEqual(p.panel_user_number_from_event({"userIndex": 7}), "7")

    def test_event_num_is_not_user(self):
        self.assertEqual(
            p.panel_user_number_from_event(
                {
                    "eventNum": 1,
                    "eventMsg": "DISARMED - Area 1 - Facility Building",
                    "userFullname": "",
                }
            ),
            "",
        )

    def test_override_by_event_time(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ov.json"
            path.write_text(json.dumps({"1789043689521": "7"}))
            with mock.patch.object(p, "PANEL_OVERRIDES_PATH", path):
                self.assertEqual(
                    p.panel_user_number_from_event(
                        {
                            "eventTime": 1789043689521,
                            "eventNum": 1,
                            "eventMsg": "DISARMED - Area 1 - Facility Building",
                            "userFullname": "",
                        }
                    ),
                    "7",
                )


class PanelUserLabelTest(unittest.TestCase):
    def test_unmapped(self):
        self.assertEqual(p.panel_user_label("7", {}), "User 7")

    def test_mapped(self):
        self.assertEqual(p.panel_user_label("7", {"7": "Jenny"}), "Jenny")

    def test_load_names(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "map.json"
            path.write_text(json.dumps({"7": "Jenny", "03": ""}))
            self.assertEqual(p.load_panel_names(path), {"7": "Jenny"})


class ResolveActorViaTest(unittest.TestCase):
    def test_web_keypad(self):
        self.assertEqual(
            p.resolve_area_actor_via(
                keypad_actor="Jenny",
                event={"eventState": "disarm", "userFullname": ""},
                keypad_actors={"Jenny"},
            ),
            ("Jenny", "Remote"),
        )

    def test_panel_user_number(self):
        self.assertEqual(
            p.resolve_area_actor_via(
                keypad_actor="",
                event={"eventState": "disarm", "userFullname": "User 7"},
                keypad_actors={"Jenny"},
            ),
            ("User 7", "Panel"),
        )

    def test_app_name_hidden(self):
        self.assertEqual(
            p.resolve_area_actor_via(
                keypad_actor="",
                event={"eventState": "disarm", "userFullname": "Kevin"},
                keypad_actors={"Jenny"},
            ),
            ("", "App"),
        )

    def test_empty_disarm_is_panel(self):
        self.assertEqual(
            p.resolve_area_actor_via(
                keypad_actor="",
                event={"eventState": "disarm", "userFullname": ""},
                keypad_actors=set(),
            ),
            ("", "Panel"),
        )

    def test_empty_arm_is_auto(self):
        self.assertEqual(
            p.resolve_area_actor_via(
                keypad_actor="",
                event={"eventState": "arm", "userFullname": ""},
                keypad_actors=set(),
            ),
            ("", "Auto"),
        )


if __name__ == "__main__":
    unittest.main()
