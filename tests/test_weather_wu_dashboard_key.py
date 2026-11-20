"""Dashboard HTML key order: PWS bootstrap API_KEY before ads apiKey=."""
import importlib.util
import unittest
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "sailingsa/deploy/club-weather/weather_wu_discover.py"
    spec = importlib.util.spec_from_file_location("weather_wu_discover", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DashboardKeyOrderTest(unittest.TestCase):
    def test_api_key_bootstrap_is_tried_before_ads_query_key(self):
        wu = _load()
        pws = "b" * 32
        ads = "a" * 32
        html = (
            '<script>(function(){const data = {"API_KEY":"%s","API_URL":"https://api.weather.com"};})();</script>'
            '<script>{"rulesUrl":"https://weather.com/api/v1/mew/entity/x?apiKey=%s"}</script>'
            % (pws, ads)
        )
        ordered, current, day = wu.extract_dashboard_keys(html)
        self.assertEqual(ordered[0], pws)
        self.assertIn(ads, ordered)
        self.assertLess(ordered.index(pws), ordered.index(ads))
        self.assertEqual(current, wu.CURRENT_PATH)
        self.assertEqual(day, wu.DAY_PATH)


if __name__ == "__main__":
    unittest.main()
