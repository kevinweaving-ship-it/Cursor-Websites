#!/usr/bin/env python3
"""HYC NVR producer is isolated from Voelklip hikpoc camera fetch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HYC = ROOT / "sailingsa/deploy/hycnvr"


def test_hycnvr_producer_is_isolated():
    bridge = (HYC / "bridge_hyc.py").read_text(encoding="utf-8")
    wait = (HYC / "wait_hevc_vps.py").read_text(encoding="utf-8")
    install = (HYC / "install-hycnvr-live.sh").read_text(encoding="utf-8")
    example = (HYC / "env.example").read_text(encoding="utf-8")
    assert "D23413606" in bridge
    assert "camera 5@D23413606" in bridge
    assert 'SESSION_CACHE = str(ROOT / ".session_cache.json")' in bridge
    assert 'ENV_PATH = ROOT / ".env"' in bridge
    assert "/opt/hikpoc/.env" not in bridge
    assert "/opt/hikpoc/.session_cache.json" not in bridge
    assert "HIK_MEDIA_KEY" in bridge
    assert "YachtC1897" not in bridge
    assert "YachtC1897" not in install
    assert "wait_hevc_vps" in wait or "VPS" in wait
    assert "D49460413" in install
    assert "bak.psclear" in install
    assert "hycnvr" in install
    assert "HYC_NVR_SERIAL=D23413606" in example
    assert "HYC_NVR_CHANNEL=5" in example


def test_club_cam_hyc_points_at_isolated_producer():
    src = (ROOT / "sailingsa/backend/club_cam_hyc.py").read_text(encoding="utf-8")
    assert "/opt/hycnvr" in src
    assert "D23413606" in src
    assert "Do not patch the Voelklip" in src
    js = (ROOT / "js/live-cam-sources.js").read_text(encoding="utf-8")
    assert "camera 5@D23413606" in js
    assert "/opt/hycnvr" in js
    frontend = ROOT / "sailingsa/frontend/js/live-cam-sources.js"
    assert frontend.read_text(encoding="utf-8") == js


if __name__ == "__main__":
    test_hycnvr_producer_is_isolated()
    test_club_cam_hyc_points_at_isolated_producer()
    print("hycnvr_isolated_min_tests: ok")
