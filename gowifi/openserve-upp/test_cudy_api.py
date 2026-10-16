#!/usr/bin/env python3
import os
import unittest
from pathlib import Path

import cudy_api


class CudyApi(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
