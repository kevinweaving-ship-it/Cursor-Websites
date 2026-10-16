#!/usr/bin/env python3
import os
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

import cudy_api


class CudyApi(unittest.TestCase):
    def tearDown(self):
        with cudy_api._LOCK:
            cudy_api._LIST_CACHE.clear()
            cudy_api._INFO_CACHE.clear()
            cudy_api._CLIENT_CACHE.clear()
            cudy_api._LAST_OK.clear()

    def test_self_test(self):
        self.assertEqual(cudy_api.self_test(), 0)

    def test_never_maps_wr1300(self):
        pack = cudy_api.device_status(cudy_api.FORBIDDEN_SN)
        self.assertFalse(pack.get("ok"))
        self.assertEqual(pack.get("error_class"), "not_pilot")
        self.assertIsNone((pack.get("device") or {}).get("serial"))

    def test_source_has_no_password(self):
        blob = Path(cudy_api.__file__).read_text()
        pw = os.environ.get("CUDY_PASSWORD") or ""
        if len(pw) >= 6:
            self.assertNotIn(pw, blob)
        self.assertIn("/root/secrets/cudy.env", blob)

    def test_cloud_failure_is_not_router_offline(self):
        self.assertEqual(cudy_api.classify_ret(cudy_api.RET_PASSWORD_ERROR), "cloud_auth_failed")
        self.assertEqual(cudy_api.classify_ret(cudy_api.RET_TEMP_LOCKED), "cloud_auth_locked")
        self.assertEqual(cudy_api.classify_ret(cudy_api.RET_DEVICE_TIMEOUT), "device_offline")
        self.assertNotEqual(
            cudy_api.classify_ret(cudy_api.RET_PASSWORD_ERROR),
            cudy_api.classify_ret(cudy_api.RET_DEVICE_TIMEOUT),
        )

    def test_as_at_is_iso_z(self):
        stamped = cudy_api._as_at(datetime(2026, 10, 16, 9, 24, 0, tzinfo=timezone.utc))
        self.assertEqual(stamped, "2026-10-16T09:24:00Z")

    def test_pack_failure_does_not_stamp_now(self):
        pack = cudy_api._pack(ok=False, live=False, error_class="cloud_unreachable", error="down")
        self.assertNotIn("as_at", pack)
        self.assertFalse(pack["live"])

    def test_list_cache_is_not_live(self):
        fetched = "2026-10-16T09:24:00Z"
        with cudy_api._LOCK:
            cudy_api._LIST_CACHE.clear()
            cudy_api._LIST_CACHE["ts"] = time.time()
            cudy_api._LIST_CACHE["pack"] = {
                "ok": True,
                "live": True,
                "devices": [{"sn": cudy_api.PILOT_SN}],
                "fetched_at": fetched,
                "as_at": fetched,
            }
        out = cudy_api._list_devices({})
        self.assertTrue(out["cached"])
        self.assertFalse(out["live"])
        self.assertEqual(out["as_at"], fetched)
        self.assertEqual(out["fetched_at"], fetched)

    def test_public_client_omits_unverified_fields(self):
        row = cudy_api._public_client(
            {
                "hostname": "e-linter",
                "ipaddr": "192.168.10.122",
                "macaddr": "348518CD05A8",
                "ssid": "Murray_2GEXT",
                "rssi": 42,
                "upspeed": 5,
                "downspeed": 5,
                "online": 41918,
            }
        )
        self.assertEqual(row["hostname"], "e-linter")
        self.assertEqual(row["ip"], "192.168.10.122")
        self.assertEqual(row["mac"], "34:85:18:CD:05:A8")
        self.assertEqual(row["ssid"], "Murray_2GEXT")
        self.assertEqual(row["online_s"], 41918)
        self.assertNotIn("rssi", row)
        self.assertNotIn("upspeed", row)
        self.assertNotIn("downspeed", row)


if __name__ == "__main__":
    unittest.main()
