#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apply_gsc_nginx_fixes import patch  # noqa: E402


LIVE_SHAPED = """
# SailingSA Configuration
server {
    listen [::]:443 ssl;
    listen 443 ssl;
    server_name sailingsa.co.za www.sailingsa.co.za;
    root /var/www/sailingsa;
    location ~ ^/sailor/ {
        proxy_pass http://127.0.0.1:8000;
    }
    location ~ ^/regatta/ {
        proxy_pass http://127.0.0.1:8000;
    }
    location / {
        try_files $uri $uri/ /index.html;
    }
}
"""


class GscNginxFixTests(unittest.TestCase):
    def test_splits_www_and_adds_home_podium(self) -> None:
        out = patch(LIVE_SHAPED)
        self.assertIn("server_name www.sailingsa.co.za;", out)
        self.assertIn("return 301 https://sailingsa.co.za$request_uri;", out)
        self.assertRegex(out, r"server_name\s+sailingsa\.co\.za\s*;")
        self.assertNotIn("server_name sailingsa.co.za www.sailingsa.co.za;", out)
        self.assertIn("location = /home {", out)
        self.assertIn("location = /home/ {", out)
        self.assertIn("location = /regatta/class/podium/podium.html", out)
        self.assertIn("$arg_regatta_id", out)
        www_block = out.split("server {")[1]
        self.assertIn("server_name www.sailingsa.co.za;", www_block)
        self.assertIn("return 301 https://sailingsa.co.za$request_uri;", www_block)
        self.assertNotIn("root /var/www/sailingsa;", www_block)

    def test_idempotent(self) -> None:
        once = patch(LIVE_SHAPED)
        twice = patch(once)
        self.assertEqual(once.count("server_name www.sailingsa.co.za;"), 1)
        self.assertEqual(twice.count("location = /home {"), 1)
        self.assertEqual(twice.count("location = /regatta/class/podium/podium.html"), 1)


if __name__ == "__main__":
    unittest.main()
